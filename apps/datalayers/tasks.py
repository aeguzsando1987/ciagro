# apps/datalayers/tasks.py
import csv
import os
import logging
from celery import shared_task
from django.contrib.gis.geos import Point

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def import_csv_to_datalayer(self, header_id, csv_path):
    """
    Tarea Celery: lee un CSV temporal y crea DataLayerPoints en bulk.

    Args:
        header_id (str): UUID del DataLayerHeader ya creado.
        csv_path (str): Ruta absoluta al archivo CSV temporal.

    Columnas esperadas en el CSV:
        - lat, lon       → geom (PointField WGS84). lon va primero en GIS.
        - captured_at    → timestamp (opcional)
        - resto          → raw_data (JSONField, validado contra definition_scheme)

    Returns:
        dict: { status, header_id, created, errors }
    """
    # Imports dentro de la función para evitar AppRegistryNotReady al arrancar Celery
    from apps.datalayers.models import DataLayerHeader, DataLayerPoints
    from apps.datalayers.validators import validate_raw_data_against_scheme
    from rest_framework.exceptions import ValidationError

    # 1. Cargar el header
    try:
        header = DataLayerHeader.objects.select_related(
            "datalayer", "plot"
        ).get(id=header_id)
    except DataLayerHeader.DoesNotExist:
        logger.error(f"DataLayerHeader {header_id} no encontrado.")
        return {"status": "error", "detail": f"Header {header_id} no encontrado."}

    definition_scheme = header.datalayer.definition_scheme if header.datalayer else None
    # Denormalización explícita: bulk_create no llama save(), así que asignamos plot_id aquí
    plot_id = header.plot_id

    points = []
    errors = []

    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, start=1):
                row = dict(row)

                # a. lat/lon → geom
                try:
                    lat = float(row.pop("lat"))
                    lon = float(row.pop("lon"))
                except (KeyError, ValueError) as e:
                    errors.append(f"Fila {i}: lat/lon inválido — {e}")
                    continue

                # b. captured_at (opcional; string vacío → None)
                captured_at = row.pop("captured_at", None) or None

                # c. El resto es raw_data
                raw_data = row

                # d. Validar contra definition_scheme (alias resolution incluida)
                try:
                    validate_raw_data_against_scheme(raw_data, definition_scheme)
                except ValidationError as e:
                    errors.append(f"Fila {i}: {e.detail}")
                    continue

                # e. Construir objeto (sin llamar save())
                points.append(
                    DataLayerPoints(
                        header=header,
                        plot_id=plot_id,                    # Explícito: bulk_create no ejecuta save()
                        geom=Point(lon, lat, srid=4326),   # lon primero (convención GIS x,y)
                        captured_at=captured_at,
                        raw_data=raw_data,
                    )
                )

    except FileNotFoundError:
        return {"status": "error", "detail": f"Archivo CSV no encontrado: {csv_path}"}

    finally:
        # Limpieza del archivo temporal (siempre, haya error o no)
        if os.path.exists(csv_path):
            os.remove(csv_path)

    # 3. Inserción masiva en lotes de 500
    if points:
        DataLayerPoints.objects.bulk_create(points, batch_size=500)

    # 4. Transición automática de FieldTask → "completed"
    #    Solo si hubo puntos importados y el header está ligado a una tarea de campo.
    #    Se usa update() para evitar cargar el objeto y pisar estado más avanzado.
    if points and header.task_id:
        from apps.field_ops.models import FieldTask
        FieldTask.objects.filter(
            id=header.task_id,
            status__in=[FieldTask.STATUS_OPEN, FieldTask.STATUS_PROCESSING],
        ).update(status=FieldTask.STATUS_COMPLETED)

    result = {
        "status": "ok" if not errors else "partial",
        "header_id": str(header_id),
        "created": len(points),
        "errors": errors,
    }
    logger.info(f"import_csv_to_datalayer: {result}")
    return result
