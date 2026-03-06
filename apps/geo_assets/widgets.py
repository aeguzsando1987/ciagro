"""
LeafletPolygonWidget
====================
Widget para el campo `geom` (PolygonField) del modelo Plot en el admin de Django.

Resuelve D2, D3 y D4 del roadmap de forma conjunta:
  D2 — El mapa Leaflet se sincroniza bidireccionalmente con el campo WKT oculto.
  D3 — Inputs Lat/Lon permiten centrar el mapa antes de dibujar el polígono.
  D4 — Al dibujar/editar el polígono se calculan área (ha) y perímetro (km) en tiempo real.

Dependencias (CDN, sin paquetes pip adicionales):
  - Leaflet.js 1.9.4  → unpkg.com
  - Leaflet.draw 1.0.4 → cdnjs.cloudflare.com

El campo geom viaja al servidor como WKT (POLYGON((lon lat, ...))) en un <textarea>
oculto, exactamente lo que Django espera para un PolygonField sin GISModelAdmin.
El cálculo preciso de centroide y área se hace server-side en Plot.save() con PostGIS.
"""

from django import forms
from django.utils.html import format_html

# ── URLs de CDN ────────────────────────────────────────────────────────────────
_LEAFLET_CSS  = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
_LEAFLET_JS   = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
_DRAW_CSS     = "https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.css"
_DRAW_JS      = "https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.js"

# ── Template HTML del widget ───────────────────────────────────────────────────
# Se usa un <script> único por instancia (map_id) para evitar colisiones si
# el admin renderizara varios mapas en la misma página.

_WIDGET_TEMPLATE = """
<div style="font-family:sans-serif; font-size:13px;">

  <!-- D3: Inputs para centrar el mapa antes de dibujar -->
  <div style="display:flex; gap:8px; align-items:center; margin-bottom:6px; flex-wrap:wrap;">
    <label style="font-weight:bold;">Centrar mapa:</label>
    <input id="{map_id}_lat" type="number" step="0.000001" placeholder="Latitud (ej. 18.9261)"
           style="width:160px; padding:3px 6px; border:1px solid #ccc; border-radius:3px;">
    <input id="{map_id}_lon" type="number" step="0.000001" placeholder="Longitud (ej. -99.2351)"
           style="width:170px; padding:3px 6px; border:1px solid #ccc; border-radius:3px;">
    <button type="button" onclick="centerMap_{map_id}()"
            style="padding:4px 10px; background:#417690; color:#fff; border:none;
                   border-radius:3px; cursor:pointer;">
      Centrar mapa
    </button>
    <span style="color:#888; font-size:11px;">
      &nbsp;Ingresa las coordenadas de referencia para navegar al sitio.
    </span>
  </div>

  <!-- Mapa Leaflet -->
  <div id="{map_id}" style="height:420px; border:1px solid #ccc; border-radius:4px;
                             margin-bottom:6px;"></div>

  <!-- D4: Panel de información (solo lectura en UI; la BD se actualiza en save()) -->
  <div id="{map_id}_info"
       style="display:none; background:#f0f7ee; border:1px solid #b2d8a8;
              border-radius:4px; padding:6px 12px; margin-bottom:6px; font-size:12px;">
    <strong>Polígono detectado —</strong>
    Área aprox.: <strong><span id="{map_id}_area">—</span> ha</strong>
    &nbsp;|&nbsp;
    Perímetro aprox.: <strong><span id="{map_id}_perim">—</span> km</strong>
    <span style="color:#888; margin-left:8px;">
      (valores precisos se recalculan en el servidor al guardar)
    </span>
  </div>

  <!-- WKT oculto — Django lo lee como valor del campo geom -->
  <textarea id="{map_id}_wkt" name="{field_name}"
            style="display:none;">{current_wkt}</textarea>

  <div style="color:#888; font-size:11px; margin-top:2px;">
    Dibuja el polígono con la herramienta
    <strong>&#9646; Polígono</strong> del panel derecho del mapa.
    Puedes editarlo con <strong>✎ Editar capas</strong> o borrarlo con
    <strong>&#128465; Eliminar capas</strong>.
  </div>

</div>

<script>
(function() {{
  // ── Conversión WKT ↔ Leaflet ─────────────────────────────────────────────
  function wktToLatLngs(wkt) {{
    if (!wkt) return null;
    // Soporte básico: POLYGON((lon lat, lon lat, ...))
    var m = wkt.match(/POLYGON\s*\(\(\s*([^)]+)\s*\)\)/i);
    if (!m) return null;
    return m[1].split(',').map(function(pair) {{
      var parts = pair.trim().split(/\s+/);
      return L.latLng(parseFloat(parts[1]), parseFloat(parts[0]));
    }});
  }}

  function latLngsToWkt(latLngs) {{
    var coords = latLngs.map(function(ll) {{
      return ll.lng.toFixed(8) + ' ' + ll.lat.toFixed(8);
    }});
    // Cerrar el anillo: el último punto == el primero
    coords.push(coords[0]);
    return 'POLYGON((' + coords.join(', ') + '))';
  }}

  // ── Cálculo aproximado de área (ha) y perímetro (km) ────────────────────
  // Área usando la fórmula del exceso esférico (Girard).
  // Suficientemente precisa para parcelas agrícolas de hasta ~1000 ha.
  function calcAreaHa(latLngs) {{
    var n = latLngs.length;
    if (n < 3) return 0;
    var R = 6371000; // radio terrestre en metros
    var area = 0;
    for (var i = 0; i < n; i++) {{
      var j = (i + 1) % n;
      var dLon = (latLngs[j].lng - latLngs[i].lng) * Math.PI / 180;
      var lat1 = latLngs[i].lat * Math.PI / 180;
      var lat2 = latLngs[j].lat * Math.PI / 180;
      area += dLon * (2 + Math.sin(lat1) + Math.sin(lat2));
    }}
    area = Math.abs(area * R * R / 2);
    return (area / 10000).toFixed(2); // m² → ha
  }}

  function calcPerimKm(latLngs) {{
    var total = 0;
    var n = latLngs.length;
    for (var i = 0; i < n; i++) {{
      total += latLngs[i].distanceTo(latLngs[(i + 1) % n]);
    }}
    return (total / 1000).toFixed(3); // m → km
  }}

  // ── Actualizar panel de info y textarea WKT ───────────────────────────────
  function updateWidget(latLngs) {{
    var wktEl   = document.getElementById('{map_id}_wkt');
    var infoEl  = document.getElementById('{map_id}_info');
    var areaEl  = document.getElementById('{map_id}_area');
    var perimEl = document.getElementById('{map_id}_perim');

    if (!latLngs || latLngs.length < 3) {{
      wktEl.value = '';
      infoEl.style.display = 'none';
      return;
    }}
    wktEl.value = latLngsToWkt(latLngs);
    areaEl.textContent  = calcAreaHa(latLngs);
    perimEl.textContent = calcPerimKm(latLngs);
    infoEl.style.display = 'block';
  }}

  // ── Inicialización del mapa ───────────────────────────────────────────────
  // Se corre cuando el DOM está listo. Leaflet.draw debe estar cargado.
  function initMap() {{
    var map = L.map('{map_id}').setView([23.0, -102.0], 5); // Centro de México

    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      attribution: '&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a>',
      maxZoom: 20,
    }}).addTo(map);

    // Capa editable: almacena el polígono activo
    var drawnItems = new L.FeatureGroup();
    map.addLayer(drawnItems);

    // ── Cargar polígono existente desde WKT ──────────────────────────────
    var existingWkt = document.getElementById('{map_id}_wkt').value.trim();
    var existingLatLngs = wktToLatLngs(existingWkt);
    if (existingLatLngs && existingLatLngs.length >= 3) {{
      var poly = L.polygon(existingLatLngs, {{color: '#417690'}}).addTo(drawnItems);
      map.fitBounds(poly.getBounds(), {{padding: [30, 30]}});
      updateWidget(existingLatLngs);
    }}

    // ── Controles de dibujo ──────────────────────────────────────────────
    var drawControl = new L.Control.Draw({{
      edit: {{ featureGroup: drawnItems }},
      draw: {{
        polygon: {{
          allowIntersection: false,
          showArea: true,
          shapeOptions: {{ color: '#417690' }}
        }},
        // Desactivar herramientas no necesarias
        polyline: false, rectangle: false,
        circle: false, circlemarker: false, marker: false,
      }},
    }});
    map.addControl(drawControl);

    // ── Evento: dibujo completado ────────────────────────────────────────
    map.on(L.Draw.Event.CREATED, function(e) {{
      drawnItems.clearLayers(); // solo un polígono a la vez
      drawnItems.addLayer(e.layer);
      updateWidget(e.layer.getLatLngs()[0]);
    }});

    // ── Evento: edición finalizada ───────────────────────────────────────
    map.on(L.Draw.Event.EDITED, function() {{
      drawnItems.eachLayer(function(layer) {{
        updateWidget(layer.getLatLngs()[0]);
      }});
    }});

    // ── Evento: capa eliminada ───────────────────────────────────────────
    map.on(L.Draw.Event.DELETED, function() {{
      updateWidget(null);
    }});

    // ── Función global para centrar el mapa (D3) ─────────────────────────
    window['centerMap_{map_id}'] = function() {{
      var lat = parseFloat(document.getElementById('{map_id}_lat').value);
      var lon = parseFloat(document.getElementById('{map_id}_lon').value);
      if (!isNaN(lat) && !isNaN(lon)) {{
        map.setView([lat, lon], 15);
      }} else {{
        alert('Ingresa coordenadas numéricas válidas (Lat y Lon).');
      }}
    }};
  }} // fin initMap

  // Ejecutar cuando Leaflet.draw esté disponible
  if (typeof L !== 'undefined' && typeof L.Control.Draw !== 'undefined') {{
    initMap();
  }} else {{
    // CDN aún cargando — esperar al evento load de la ventana
    window.addEventListener('load', function() {{
      if (typeof L !== 'undefined' && typeof L.Control.Draw !== 'undefined') {{
        initMap();
      }} else {{
        // Fallback: mostrar textarea para edición WKT manual
        var wkt = document.getElementById('{map_id}_wkt');
        if (wkt) {{ wkt.style.display = 'block'; wkt.style.width = '100%'; wkt.rows = 4; }}
      }}
    }});
  }}
}})();
</script>
"""


class LeafletPolygonWidget(forms.Widget):
    """
    Widget Django para el campo PolygonField en el admin de Plot.

    Renderiza un mapa interactivo Leaflet con Leaflet.draw para que el usuario
    dibuje el polígono de la parcela. El valor se sincroniza con un <textarea>
    oculto en formato WKT (POLYGON((lon lat, ...))), que es el formato que Django
    espera para un PolygonField.

    Uso en admin:
        def formfield_for_dbfield(self, db_field, request, **kwargs):
            if db_field.name == "geom":
                kwargs["widget"] = LeafletPolygonWidget()
            return super().formfield_for_dbfield(db_field, request, **kwargs)
    """

    class Media:
        css = {
            "all": [_LEAFLET_CSS, _DRAW_CSS],
        }
        js = [_LEAFLET_JS, _DRAW_JS]

    def render(self, name, value, attrs=None, renderer=None):
        # Extraer WKT del valor actual (puede ser GEOSGeometry o str)
        current_wkt = ""
        if value:
            current_wkt = str(value)  # GEOSGeometry.__str__() devuelve WKT

        # ID único para el contenedor del mapa (evita colisiones si hubiera varios)
        map_id = (attrs or {}).get("id", f"leaflet_{name}").replace("-", "_")

        return format_html(
            _WIDGET_TEMPLATE,
            map_id=map_id,
            field_name=name,
            current_wkt=current_wkt,
        )

    def value_from_datadict(self, data, files, name):
        """Django llama a este método para extraer el valor del POST."""
        return data.get(name, "") or None

    def use_required_attribute(self, initial_value):
        return False
