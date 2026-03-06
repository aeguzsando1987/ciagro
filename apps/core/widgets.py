"""
apps/core/widgets.py

AdditionalParamsWidget: editor visual K-V para campos additional_params (JSONField).
Reutiliza BaseSchemeWidget, _ALPINE_LOADER, _RAW_TOGGLE_BAR y _RAW_PANEL de
apps/datalayers/widgets.py.

Tipos soportados:
  string  → text input   → JSON: "valor"
  number  → number input → JSON: 42 / 3.14
  boolean → select       → JSON: true / false
  array   → texto CSV    → JSON: ["a", "b", "c"]
"""
import json
import html as html_lib
from django.utils.safestring import mark_safe
from apps.datalayers.widgets import (
    BaseSchemeWidget, _ALPINE_LOADER, _RAW_TOGGLE_BAR, _RAW_PANEL,
)


class AdditionalParamsWidget(BaseSchemeWidget):
    """
    Widget reutilizable para JSONField additional_params.
    Aplicado via formfield_for_dbfield() en los admins de:
      CropCatalog, PestCatalog, AgroUnit, Ranch, Plot
    """

    def render(self, name, value, attrs=None, renderer=None):
        data = self._normalize_value(value)
        data_initial_escaped = html_lib.escape(
            json.dumps(data, ensure_ascii=False), quote=True
        )
        fn = f"extraParams_{name}"

        widget_html = f"""
<script>
{_ALPINE_LOADER}
window.{fn} = function() {{
    return {{
        rows: [],
        rawMode: false,
        rawText: '{{}}',

        init() {{
            const raw = this.$el.getAttribute('data-initial') || '{{}}';
            this.rawText = raw;
            this.$refs.hidden.value = raw;
            this._parse(raw);
        }},

        _parse(raw) {{
            let data = {{}};
            try {{ data = JSON.parse(raw || '{{}}'); }} catch(e) {{}}
            this.rows = Object.entries(data).map(([k, v]) => {{
                let type = typeof v;
                if (Array.isArray(v)) type = 'array';
                return {{
                    key: k,
                    type: type === 'boolean' ? 'boolean' :
                          type === 'number'  ? 'number'  :
                          type === 'array'   ? 'array'   : 'string',
                    strVal: type === 'array'   ? v.join(', ') :
                            type === 'boolean' ? String(v)    : String(v),
                }};
            }});
        }},

        sync() {{
            const obj = {{}};
            for (const r of this.rows) {{
                const k = r.key.trim();
                if (!k) continue;
                if (r.type === 'number')       obj[k] = parseFloat(r.strVal) || 0;
                else if (r.type === 'boolean') obj[k] = r.strVal === 'true';
                else if (r.type === 'array')   obj[k] = r.strVal.split(',').map(x => x.trim()).filter(Boolean);
                else                           obj[k] = r.strVal;
            }}
            const out = JSON.stringify(obj, null, 2);
            this.$refs.hidden.value = out;
            this.rawText = out;
        }},

        addRow() {{
            this.rows.push({{ key: '', type: 'string', strVal: '' }});
        }},

        removeRow(i) {{
            this.rows.splice(i, 1);
            this.sync();
        }},

        toggleRaw() {{
            if (!this.rawMode) {{
                this.sync();
                this.rawMode = true;
            }} else {{
                try {{
                    JSON.parse(this.rawText);
                    this._parse(this.rawText);
                    this.$refs.hidden.value = this.rawText;
                    this.rawMode = false;
                }} catch(e) {{
                    alert('JSON invalido: ' + e.message + '\\n\\nCorrige el error antes de volver al modo visual.');
                }}
            }}
        }},
    }};
}};
</script>

<div x-data="{fn}()"
     data-initial="{data_initial_escaped}"
     style="font-family:sans-serif; max-width:800px; font-size:14px;">

    <textarea name="{name}" hidden x-ref="hidden"></textarea>

    {_RAW_TOGGLE_BAR}
    {_RAW_PANEL}

    <!-- Modo visual K-V -->
    <div x-show="!rawMode">

        <table style="width:100%; border-collapse:collapse; margin-bottom:10px;">
            <thead>
                <tr style="background:#f5f5f5; font-size:0.85em; text-align:left;">
                    <th style="padding:6px 8px; border:1px solid #ddd; width:35%;">Clave</th>
                    <th style="padding:6px 8px; border:1px solid #ddd; width:18%;">Tipo</th>
                    <th style="padding:6px 8px; border:1px solid #ddd;">Valor</th>
                    <th style="padding:6px 8px; border:1px solid #ddd; width:36px;"></th>
                </tr>
            </thead>
            <tbody>
                <template x-for="(row, i) in rows" :key="i">
                    <tr>
                        <!-- Clave -->
                        <td style="padding:4px 6px; border:1px solid #eee;">
                            <input type="text" x-model="row.key" @input="sync()"
                                   placeholder="nombre_clave"
                                   style="width:100%; border:1px solid #ccc; padding:4px 6px;
                                          border-radius:3px; font-family:monospace; font-size:0.9em;
                                          box-sizing:border-box;">
                        </td>
                        <!-- Tipo -->
                        <td style="padding:4px 6px; border:1px solid #eee;">
                            <select x-model="row.type" @change="sync()"
                                    style="width:100%; border:1px solid #ccc; padding:4px 5px;
                                           border-radius:3px; font-size:0.9em;">
                                <option value="string">string</option>
                                <option value="number">number</option>
                                <option value="boolean">boolean</option>
                                <option value="array">array</option>
                            </select>
                        </td>
                        <!-- Valor (input dinámico según tipo) -->
                        <td style="padding:4px 6px; border:1px solid #eee;">
                            <template x-if="row.type !== 'boolean'">
                                <input :type="row.type === 'number' ? 'number' : 'text'"
                                       x-model="row.strVal" @input="sync()"
                                       :placeholder="row.type === 'array'  ? 'val1, val2, val3' :
                                                     row.type === 'number' ? '0' : 'valor'"
                                       style="width:100%; border:1px solid #ccc; padding:4px 6px;
                                              border-radius:3px; font-size:0.9em; box-sizing:border-box;">
                            </template>
                            <template x-if="row.type === 'boolean'">
                                <select x-model="row.strVal" @change="sync()"
                                        style="width:100%; border:1px solid #ccc; padding:4px 5px;
                                               border-radius:3px; font-size:0.9em;">
                                    <option value="true">true</option>
                                    <option value="false">false</option>
                                </select>
                            </template>
                        </td>
                        <!-- Borrar -->
                        <td style="padding:4px 6px; border:1px solid #eee; text-align:center;">
                            <button type="button" @click="removeRow(i)"
                                    title="Eliminar fila"
                                    style="background:#c62828; color:white; border:none;
                                           border-radius:4px; width:24px; height:24px;
                                           cursor:pointer; font-size:14px; line-height:1;">&#x00D7;</button>
                        </td>
                    </tr>
                </template>
                <!-- Fila vacía placeholder -->
                <template x-if="rows.length === 0">
                    <tr>
                        <td colspan="4" style="padding:12px; text-align:center; color:#888;
                                               border:1px solid #eee; font-style:italic; font-size:0.9em;">
                            Sin parámetros. Haz clic en &ldquo;+ Agregar&rdquo; para añadir uno.
                        </td>
                    </tr>
                </template>
            </tbody>
        </table>

        <button type="button" @click="addRow()"
                style="background:#2e7d32; color:white; border:none; padding:7px 16px;
                       border-radius:4px; cursor:pointer; font-size:0.9em; font-weight:bold;">
            + Agregar parámetro
        </button>

        <!-- Preview JSON compacto -->
        <div x-show="rows.length > 0"
             style="margin-top:10px; padding:8px 12px; background:#f9f9f9;
                    border:1px solid #e0e0e0; border-radius:4px; overflow:auto; max-height:120px;">
            <pre style="margin:0; font-size:0.75em; color:#555;" x-text="$refs.hidden.value"></pre>
        </div>

    </div>
</div>"""
        return mark_safe(widget_html)
