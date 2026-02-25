import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.geography.models import Country, State


FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"


class Command(BaseCommand):
    help = "Carga datos iniciales de países y estados desde archivos JSON en fixtures/"

    def add_arguments(self, parser):
        parser.add_argument(
            "--countries-file",
            default=str(FIXTURES_DIR / "countries.json"),
            help="Ruta al archivo JSON de países (default: fixtures/countries.json)",
        )
        parser.add_argument(
            "--states-file",
            default=str(FIXTURES_DIR / "states.json"),
            help="Ruta al archivo JSON de estados (default: fixtures/states.json)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Elimina todos los datos existentes antes de cargar (¡destructivo!)",
        )
        parser.add_argument(
            "--only-countries",
            action="store_true",
            help="Solo carga países, omite estados",
        )
        parser.add_argument(
            "--only-states",
            action="store_true",
            help="Solo carga estados (requiere que los países ya existan)",
        )

    def handle(self, *args, **options):
        countries_file = Path(options["countries_file"])
        states_file = Path(options["states_file"])
        reset = options["reset"]
        only_countries = options["only_countries"]
        only_states = options["only_states"]

        if reset:
            self.stdout.write(self.style.WARNING("Eliminando datos existentes..."))
            State.objects.all().delete()
            Country.objects.all().delete()
            self.stdout.write(self.style.WARNING("Datos eliminados."))

        with transaction.atomic():
            if not only_states:
                self._load_countries(countries_file)

            if not only_countries:
                self._load_states(states_file)

        self.stdout.write(self.style.SUCCESS("Seed de geografía completado."))

    def _load_countries(self, filepath):
        if not filepath.exists():
            raise CommandError(f"Archivo no encontrado: {filepath}")

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        created = 0
        skipped = 0

        for item in data:
            _, was_created = Country.objects.get_or_create(
                iso_2=item["iso_2"],
                defaults={
                    "name": item["name"],
                    "iso_3": item["iso_3"],
                },
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        self.stdout.write(
            f"  Países: {created} creados, {skipped} ya existían."
        )

    def _load_states(self, filepath):
        if not filepath.exists():
            raise CommandError(f"Archivo no encontrado: {filepath}")

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        created = 0
        skipped = 0
        errors = 0

        for item in data:
            try:
                country = Country.objects.get(iso_2=item["country_iso2"])
            except Country.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"  País no encontrado para iso_2='{item['country_iso2']}' "
                        f"(estado: {item['name']}). Omitido."
                    )
                )
                errors += 1
                continue

            _, was_created = State.objects.get_or_create(
                country=country,
                code=item["code"],
                defaults={"name": item["name"]},
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        self.stdout.write(
            f"  Estados: {created} creados, {skipped} ya existían, {errors} omitidos."
        )
