"""
apps/datalayers/widgets.py

Widgets personalizados para los campos JSONB de DataLayer.
Usan Alpine.js (CDN) para la interfaz reactiva y FileReader para lectura de CSV.

Cada widget tiene dos modos:
  - Modo Visual: UI guiada (columnas, niveles, ejes)
  - Modo Raw JSON: textarea editable directamente (para usuarios experimentados)

Orden critico en cada render():
  1. <script> que DEFINE la funcion Alpine + carga el CDN (antes del div)
  2. <div x-data="..."> aparece DESPUES de que la funcion existe

Integracion con Django:
  - render()              -> HTML + Alpine.js
  - value_from_datadict() -> JSON string del <textarea hidden>
  - JSONField             -> parsea el string a dict antes de guardar
  - formfield_for_dbfield -> aplica widget distinto por nombre de campo
"""

import json
import html as html_lib
from django import forms
from django.utils.safestring import mark_safe

_ALPINE_LOADER = """
if (!window.__schemeAlpineLoaded) {
    window.__schemeAlpineLoaded = true;
    var __al = document.createElement('script');
    __al.src = 'https://cdn.jsdelivr.net/npm/alpinejs@3.14.9/dist/cdn.min.js';
    document.head.appendChild(__al);
}"""

# Barra de advertencia + boton de toggle (igual en ambos widgets)
_RAW_TOGGLE_BAR = """
    <!-- Barra de advertencia / toggle Raw -->
    <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;
                padding:8px 12px; background:#fff3e0; border:1px solid #ffb74d;
                border-radius:6px;">
        <span style="font-size:0.85em; color:#bf360c;">
            ⚠️ <strong>Modo Raw JSON</strong> &mdash; Para usuarios experimentados
        </span>
        <button type="button" @click="toggleRaw()"
                style="margin-left:auto; border:none; padding:5px 14px; border-radius:4px;
                       cursor:pointer; font-size:0.85em; font-weight:bold;
                       background:#e65100; color:white;">
            <span x-text="rawMode ? '&larr; Volver al modo visual' : 'Editar JSON directamente &rarr;'"></span>
        </button>
    </div>
"""

# Raw textarea (igual en ambos widgets)
_RAW_PANEL = """
    <!-- Panel Raw (solo visible en rawMode) -->
    <div x-show="rawMode">
        <textarea :value="rawText"
                  @input="rawText = $event.target.value; $refs.hidden.value = $event.target.value;"
                  rows="18"
                  spellcheck="false"
                  style="width:100%; font-family:monospace; font-size:0.85em;
                         padding:10px; border:2px solid #e65100; border-radius:6px;
                         background:#fffde7; box-sizing:border-box; resize:vertical;">
        </textarea>
        <p style="margin-top:6px; font-size:0.8em; color:#bf360c;">
            Edita el JSON directamente. Al volver al modo visual se intentara parsear automaticamente.
            Si el JSON es invalido, el sistema mostrara un aviso.
        </p>
    </div>
"""


class BaseSchemeWidget(forms.Widget):

    def use_required_attribute(self, initial_value):
        return False

    def value_from_datadict(self, data, files, name):
        return data.get(name)

    def _normalize_value(self, value):
        if value is None or value == "":
            return {}
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, ValueError):
                return {}
        if isinstance(value, dict):
            return value
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# Widget 1: definition_scheme
# ─────────────────────────────────────────────────────────────────────────────

class DefinitionSchemeWidget(BaseSchemeWidget):

    def render(self, name, value, attrs=None, renderer=None):
        data = self._normalize_value(value)
        data_initial_escaped = html_lib.escape(
            json.dumps(data, ensure_ascii=False), quote=True
        )
        fn = f"defWidget_{name}"

        widget_html = f"""
<script>
{_ALPINE_LOADER}
window.{fn} = function() {{
    return {{
        jsonValue: '{{}}',
        rawMode: false,
        rawText: '{{}}',
        required: [],
        optional: [],
        unassigned: [],
        csvStatus: '',

        init() {{
            const raw = this.$el.getAttribute('data-initial') || '{{}}';
            this.jsonValue = raw;
            this.rawText   = raw;
            this.$refs.hidden.value = raw;
            this._parse(raw);
        }},

        toggleRaw() {{
            if (!this.rawMode) {{
                this.sync();
                this.rawText = this.jsonValue;
                this.rawMode = true;
            }} else {{
                try {{
                    JSON.parse(this.rawText);
                    this._parse(this.rawText);
                    this.jsonValue = this.rawText;
                    this.$refs.hidden.value = this.rawText;
                    this.rawMode = false;
                }} catch(e) {{
                    alert('JSON invalido: ' + e.message + '\\n\\nCorrige el error antes de volver al modo visual.');
                }}
            }}
        }},

        _parse(raw) {{
            let data = {{}};
            try {{ data = JSON.parse(raw || '{{}}'); }} catch(e) {{}}
            const req = data.required || [];
            const opt = data.optional || [];
            const ali = data.aliases  || {{}};
            const unt = data.units    || {{}};
            this.required = req.map(n => ({{ name: n, type: '', aliases: ali[n] || [], unit: unt[n] || '' }}));
            this.optional = opt.map(n => ({{ name: n, type: '', aliases: ali[n] || [], unit: unt[n] || '' }}));
        }},

        sync() {{
            const req = this.required.filter(c => c.name.trim());
            const opt = this.optional.filter(c => c.name.trim());
            const aliases = {{}};
            const units   = {{}};
            [...req, ...opt].forEach(c => {{
                const a = c.aliases.filter(x => x.trim());
                if (a.length) aliases[c.name] = a;
                if (c.unit.trim()) units[c.name] = c.unit.trim();
            }});
            const obj = {{
                required: req.map(c => c.name),
                optional: opt.map(c => c.name),
            }};
            if (Object.keys(aliases).length) obj.aliases = aliases;
            if (Object.keys(units).length)   obj.units   = units;
            this.jsonValue = JSON.stringify(obj, null, 2);
            this.$refs.hidden.value = this.jsonValue;
        }},

        addManual(list) {{
            this[list].push({{ name: '', type: '', aliases: [], unit: '' }});
        }},

        remove(list, i) {{
            this[list].splice(i, 1);
            this.sync();
        }},

        assign(i, list) {{
            const col = this.unassigned.splice(i, 1)[0];
            this[list].push(col);
            this.sync();
        }},

        loadCSV(event) {{
            const file = event.target.files[0];
            if (!file) return;
            this.csvStatus = 'Leyendo...';
            const reader = new FileReader();
            reader.onload = (e) => {{
                const text = e.target.result;
                const line = text.split('\\n')[0];
                const sep  = line.includes(';') ? ';' : ',';
                const hdrs = line.split(sep).map(h => h.trim().replace(/^"|"$/g, ''));
                const existing = [...this.required, ...this.optional].map(c => c.name);
                this.unassigned = hdrs
                    .filter(h => h && !existing.includes(h))
                    .map(h => ({{ name: h, type: '', aliases: [], unit: '' }}));
                this.csvStatus = `${{hdrs.length}} columnas detectadas.`;
            }};
            reader.readAsText(file);
        }}
    }};
}};
</script>

<div x-data="{fn}()"
     data-initial="{data_initial_escaped}"
     style="font-family:sans-serif; max-width:960px; font-size:14px;">

    <textarea name="{name}" hidden x-ref="hidden"></textarea>

    {_RAW_TOGGLE_BAR}
    {_RAW_PANEL}

    <!-- Modo Visual -->
    <div x-show="!rawMode">

        <!-- Carga CSV -->
        <div style="margin-bottom:12px; padding:10px; background:#f0f4f8;
                    border-radius:6px; border:1px solid #d0d8e0;">
            <label style="font-weight:bold; display:block; margin-bottom:6px;">
                📂 Importar columnas desde CSV
            </label>
            <input type="file" accept=".csv" @change="loadCSV($event)">
            <span x-text="csvStatus" style="margin-left:10px; color:#555; font-size:0.85em;"></span>
        </div>

        <!-- Columnas sin asignar -->
        <template x-if="unassigned.length > 0">
            <div style="margin-bottom:12px; padding:8px; background:#fff8e1;
                        border:1px solid #ffe082; border-radius:6px;">
                <strong style="font-size:0.9em;">Columnas detectadas (sin asignar):</strong>
                <div style="display:flex; flex-wrap:wrap; gap:6px; margin-top:6px;">
                    <template x-for="(col, i) in unassigned" :key="i">
                        <div style="display:flex; gap:4px; align-items:center;
                                    background:#fff; border:1px solid #ccc;
                                    padding:4px 8px; border-radius:4px;">
                            <span x-text="col.name" style="font-size:0.85em;"></span>
                            <button type="button" @click="assign(i, 'required')"
                                    title="Marcar como required"
                                    style="background:#2e7d32; color:white; border:none;
                                           padding:2px 7px; border-radius:3px; cursor:pointer; font-size:0.8em;">R</button>
                            <button type="button" @click="assign(i, 'optional')"
                                    title="Marcar como optional"
                                    style="background:#1565c0; color:white; border:none;
                                           padding:2px 7px; border-radius:3px; cursor:pointer; font-size:0.8em;">O</button>
                        </div>
                    </template>
                </div>
            </div>
        </template>

        <!-- Required / Optional -->
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">

            <!-- REQUIRED -->
            <div>
                <div style="display:flex; align-items:center;
                            justify-content:space-between; margin-bottom:8px;">
                    <strong style="color:#2e7d32;">✅ Required</strong>
                    <button type="button" @click="addManual('required')"
                            style="background:#2e7d32; color:white; border:none;
                                   padding:4px 12px; border-radius:4px; cursor:pointer; font-size:0.85em;">
                        + Agregar
                    </button>
                </div>
                <template x-for="(col, i) in required" :key="i">
                    <div style="border:1px solid #c8e6c9; background:#f9fbe7;
                                border-radius:6px; padding:8px; margin-bottom:8px;">
                        <div style="display:flex; gap:6px; align-items:center; margin-bottom:6px;">
                            <input x-model="col.name" placeholder="nombre columna" @input="sync()"
                                   style="flex:1; padding:4px 6px; border:1px solid #ccc; border-radius:4px; font-size:0.9em;">
                            <select x-model="col.type" @change="sync()"
                                    style="padding:4px; border:1px solid #ccc; border-radius:4px; font-size:0.85em;">
                                <option value="">tipo</option>
                                <option value="float">Float</option>
                                <option value="integer">Integer</option>
                                <option value="string">String</option>
                                <option value="date">Date</option>
                            </select>
                            <button type="button" @click="remove('required', i)"
                                    style="background:#c62828; color:white; border:none;
                                           padding:4px 8px; border-radius:4px; cursor:pointer; font-size:0.85em;">✕</button>
                        </div>
                        <input x-model="col.unit" placeholder="Unidad (ej. ppm, %)" @input="sync()"
                               style="width:100%; padding:4px 6px; border:1px solid #ccc; border-radius:4px;
                                      margin-bottom:6px; box-sizing:border-box; font-size:0.85em;">
                        <div>
                            <small style="color:#555;">Aliases:</small>
                            <template x-for="(alias, j) in col.aliases" :key="j">
                                <div style="display:flex; gap:4px; margin-top:4px;">
                                    <input :value="alias"
                                           @input="col.aliases[j] = $event.target.value; sync()"
                                           placeholder="alias"
                                           style="flex:1; padding:3px 6px; border:1px solid #ccc; border-radius:4px; font-size:0.85em;">
                                    <button type="button" @click="col.aliases.splice(j, 1); sync()"
                                            style="background:#e53935; color:white; border:none;
                                                   padding:2px 7px; border-radius:3px; cursor:pointer; font-size:0.8em;">✕</button>
                                </div>
                            </template>
                            <button type="button" @click="col.aliases.push(''); sync()"
                                    style="margin-top:4px; background:#546e7a; color:white; border:none;
                                           padding:2px 10px; border-radius:3px; cursor:pointer; font-size:0.8em;">
                                + Alias
                            </button>
                        </div>
                    </div>
                </template>
            </div>

            <!-- OPTIONAL -->
            <div>
                <div style="display:flex; align-items:center;
                            justify-content:space-between; margin-bottom:8px;">
                    <strong style="color:#1565c0;">📋 Optional</strong>
                    <button type="button" @click="addManual('optional')"
                            style="background:#1565c0; color:white; border:none;
                                   padding:4px 12px; border-radius:4px; cursor:pointer; font-size:0.85em;">
                        + Agregar
                    </button>
                </div>
                <template x-for="(col, i) in optional" :key="i">
                    <div style="border:1px solid #bbdefb; background:#e3f2fd;
                                border-radius:6px; padding:8px; margin-bottom:8px;">
                        <div style="display:flex; gap:6px; align-items:center; margin-bottom:6px;">
                            <input x-model="col.name" placeholder="nombre columna" @input="sync()"
                                   style="flex:1; padding:4px 6px; border:1px solid #ccc; border-radius:4px; font-size:0.9em;">
                            <select x-model="col.type" @change="sync()"
                                    style="padding:4px; border:1px solid #ccc; border-radius:4px; font-size:0.85em;">
                                <option value="">tipo</option>
                                <option value="float">Float</option>
                                <option value="integer">Integer</option>
                                <option value="string">String</option>
                                <option value="date">Date</option>
                            </select>
                            <button type="button" @click="remove('optional', i)"
                                    style="background:#c62828; color:white; border:none;
                                           padding:4px 8px; border-radius:4px; cursor:pointer; font-size:0.85em;">✕</button>
                        </div>
                        <input x-model="col.unit" placeholder="Unidad (ej. ppm, %)" @input="sync()"
                               style="width:100%; padding:4px 6px; border:1px solid #ccc; border-radius:4px;
                                      margin-bottom:6px; box-sizing:border-box; font-size:0.85em;">
                        <div>
                            <small style="color:#555;">Aliases:</small>
                            <template x-for="(alias, j) in col.aliases" :key="j">
                                <div style="display:flex; gap:4px; margin-top:4px;">
                                    <input :value="alias"
                                           @input="col.aliases[j] = $event.target.value; sync()"
                                           placeholder="alias"
                                           style="flex:1; padding:3px 6px; border:1px solid #ccc; border-radius:4px; font-size:0.85em;">
                                    <button type="button" @click="col.aliases.splice(j, 1); sync()"
                                            style="background:#e53935; color:white; border:none;
                                                   padding:2px 7px; border-radius:3px; cursor:pointer; font-size:0.8em;">✕</button>
                                </div>
                            </template>
                            <button type="button" @click="col.aliases.push(''); sync()"
                                    style="margin-top:4px; background:#546e7a; color:white; border:none;
                                           padding:2px 10px; border-radius:3px; cursor:pointer; font-size:0.8em;">
                                + Alias
                            </button>
                        </div>
                    </div>
                </template>
            </div>

        </div>

        <!-- Preview JSON -->
        <details style="margin-top:12px;">
            <summary style="cursor:pointer; color:#555; font-size:0.85em;">🔍 Ver JSON generado</summary>
            <pre style="background:#f5f5f5; padding:10px; border-radius:6px;
                        font-size:0.8em; overflow-x:auto;" x-text="jsonValue"></pre>
        </details>

    </div><!-- /Modo Visual -->

</div>
"""
        return mark_safe(widget_html)


# ─────────────────────────────────────────────────────────────────────────────
# Widget 2: evaluation_scheme
# ─────────────────────────────────────────────────────────────────────────────

class EvaluationSchemeWidget(BaseSchemeWidget):

    def render(self, name, value, attrs=None, renderer=None):
        data = self._normalize_value(value)
        data_initial_escaped = html_lib.escape(
            json.dumps(data, ensure_ascii=False), quote=True
        )
        fn = f"evalWidget_{name}"

        widget_html = f"""
<script>
{_ALPINE_LOADER}
window.{fn} = function() {{
    return {{
        jsonValue: '{{}}',
        rawMode: false,
        rawText: '{{}}',
        levels: [],
        colorError: '',
        kiviatMin: 0,
        kiviatMax: 10,
        axes: [],

        init() {{
            const raw = this.$el.getAttribute('data-initial') || '{{}}';
            this.jsonValue = raw;
            this.rawText   = raw;
            this.$refs.hidden.value = raw;
            this._parse(raw);
        }},

        toggleRaw() {{
            if (!this.rawMode) {{
                this.sync();
                this.rawText = this.jsonValue;
                this.rawMode = true;
            }} else {{
                try {{
                    JSON.parse(this.rawText);
                    this._parse(this.rawText);
                    this.jsonValue = this.rawText;
                    this.$refs.hidden.value = this.rawText;
                    this.rawMode = false;
                }} catch(e) {{
                    alert('JSON invalido: ' + e.message + '\\n\\nCorrige el error antes de volver al modo visual.');
                }}
            }}
        }},

        _parse(raw) {{
            let data = {{}};
            try {{ data = JSON.parse(raw || '{{}}'); }} catch(e) {{}}
            const cLevels = (data.colorimetry && data.colorimetry.levels) || [];
            this.levels = cLevels.map(l => ({{ min: l.min ?? 0, max: l.max ?? 0 }}));
            const kv = data.kiviat || {{}};
            this.kiviatMin = kv.global_min ?? 0;
            this.kiviatMax = kv.global_max ?? 10;
            this.axes = (kv.axes || []).slice();
        }},

        validateLevels() {{
            for (let i = 1; i < this.levels.length; i++) {{
                if (this.levels[i].min <= this.levels[i-1].max) {{
                    this.colorError = `Nivel ${{i+1}}: min (${{this.levels[i].min}}) debe ser mayor al max del nivel anterior (${{this.levels[i-1].max}}).`;
                    return false;
                }}
            }}
            for (let i = 0; i < this.levels.length; i++) {{
                if (this.levels[i].min >= this.levels[i].max) {{
                    this.colorError = `Nivel ${{i+1}}: min debe ser menor que max.`;
                    return false;
                }}
            }}
            this.colorError = '';
            return true;
        }},

        addLevel() {{
            const last = this.levels[this.levels.length - 1];
            const newMin = last ? last.max + 0.01 : 0;
            const newMax = newMin + 0.10;
            this.levels.push({{ min: parseFloat(newMin.toFixed(2)), max: parseFloat(newMax.toFixed(2)) }});
            this.sync();
        }},

        removeLevel(i) {{
            this.levels.splice(i, 1);
            this.validateLevels();
            this.sync();
        }},

        sync() {{
            const obj = {{
                colorimetry: {{
                    levels: this.levels.map((l, i) => ({{ level: i + 1, min: l.min, max: l.max }}))
                }},
                kiviat: {{
                    global_min: this.kiviatMin,
                    global_max: this.kiviatMax,
                    axes: this.axes.filter(a => a.trim())
                }}
            }};
            this.jsonValue = JSON.stringify(obj, null, 2);
            this.$refs.hidden.value = this.jsonValue;
        }}
    }};
}};
</script>

<div x-data="{fn}()"
     data-initial="{data_initial_escaped}"
     style="font-family:sans-serif; max-width:800px; font-size:14px;">

    <textarea name="{name}" hidden x-ref="hidden"></textarea>

    {_RAW_TOGGLE_BAR}
    {_RAW_PANEL}

    <!-- Modo Visual -->
    <div x-show="!rawMode">

        <!-- SECCIÓN 1: COLORIMETRÍA -->
        <div style="margin-bottom:20px; border:1px solid #e0e0e0; border-radius:8px; overflow:hidden;">
            <div style="background:#37474f; color:white; padding:10px 14px;
                        display:flex; align-items:center; justify-content:space-between;">
                <strong>🎨 Colorimetria — Niveles</strong>
                <button type="button" @click="addLevel()"
                        style="background:#4caf50; color:white; border:none;
                               padding:4px 12px; border-radius:4px; cursor:pointer; font-size:0.85em;">
                    + Nivel
                </button>
            </div>
            <div style="padding:12px;">
                <template x-if="colorError">
                    <div style="background:#ffebee; color:#c62828; padding:8px 12px;
                                border-radius:4px; margin-bottom:10px; font-size:0.9em;"
                         x-text="colorError"></div>
                </template>
                <div style="display:grid; grid-template-columns:60px 1fr 1fr 40px;
                            gap:8px; margin-bottom:6px; padding:0 4px;">
                    <span style="font-weight:bold; font-size:0.85em; color:#555;">Nivel</span>
                    <span style="font-weight:bold; font-size:0.85em; color:#555;">Min</span>
                    <span style="font-weight:bold; font-size:0.85em; color:#555;">Max</span>
                    <span></span>
                </div>
                <template x-for="(lvl, i) in levels" :key="i">
                    <div style="display:grid; grid-template-columns:60px 1fr 1fr 40px;
                                gap:8px; margin-bottom:6px; align-items:center;">
                        <span style="text-align:center; font-weight:bold; color:#37474f;" x-text="i + 1"></span>
                        <input type="number" step="any" x-model.number="lvl.min"
                               @input="validateLevels(); sync()"
                               style="padding:5px 8px; border:1px solid #ccc; border-radius:4px;">
                        <input type="number" step="any" x-model.number="lvl.max"
                               @input="validateLevels(); sync()"
                               style="padding:5px 8px; border:1px solid #ccc; border-radius:4px;">
                        <button type="button" @click="removeLevel(i)"
                                style="background:#e53935; color:white; border:none;
                                       padding:4px 8px; border-radius:4px; cursor:pointer;">✕</button>
                    </div>
                </template>
                <template x-if="levels.length === 0">
                    <p style="color:#aaa; font-size:0.9em; text-align:center; padding:10px 0;">
                        Sin niveles. Usa "+ Nivel" para agregar.
                    </p>
                </template>
            </div>
        </div>

        <!-- SECCIÓN 2: KIVIAT -->
        <div style="border:1px solid #e0e0e0; border-radius:8px; overflow:hidden;">
            <div style="background:#1a237e; color:white; padding:10px 14px;
                        display:flex; align-items:center; justify-content:space-between;">
                <strong>🕸️ Kiviat — Ejes del Radar</strong>
                <span style="font-size:0.85em; opacity:0.8;" x-text="`${{axes.length}} / 20 ejes`"></span>
            </div>
            <div style="padding:12px;">
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:14px;">
                    <div>
                        <label style="display:block; font-size:0.85em; font-weight:bold;
                                      margin-bottom:4px; color:#555;">Min global (todos los ejes)</label>
                        <input type="number" step="any" x-model.number="kiviatMin" @input="sync()"
                               style="width:100%; padding:6px 8px; border:1px solid #ccc;
                                      border-radius:4px; box-sizing:border-box;">
                    </div>
                    <div>
                        <label style="display:block; font-size:0.85em; font-weight:bold;
                                      margin-bottom:4px; color:#555;">Max global (todos los ejes)</label>
                        <input type="number" step="any" x-model.number="kiviatMax" @input="sync()"
                               style="width:100%; padding:6px 8px; border:1px solid #ccc;
                                      border-radius:4px; box-sizing:border-box;">
                    </div>
                </div>
                <div style="display:flex; align-items:center;
                            justify-content:space-between; margin-bottom:8px;">
                    <label style="font-weight:bold; font-size:0.85em; color:#555;">Ejes:</label>
                    <button type="button"
                            @click="if (axes.length < 20) {{ axes.push(''); sync(); }}"
                            style="background:#3949ab; color:white; border:none;
                                   padding:4px 12px; border-radius:4px; cursor:pointer; font-size:0.85em;">
                        + Eje
                    </button>
                </div>
                <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(180px, 1fr)); gap:6px;">
                    <template x-for="(eje, i) in axes" :key="i">
                        <div style="display:flex; gap:4px; align-items:center;">
                            <input :value="eje"
                                   @input="axes[i] = $event.target.value; sync()"
                                   :placeholder="`Eje ${{i + 1}}`"
                                   style="flex:1; padding:5px 8px; border:1px solid #ccc;
                                          border-radius:4px; font-size:0.9em;">
                            <button type="button" @click="axes.splice(i, 1); sync()"
                                    style="background:#e53935; color:white; border:none;
                                           padding:4px 8px; border-radius:4px; cursor:pointer; font-size:0.8em;">✕</button>
                        </div>
                    </template>
                </div>
                <template x-if="axes.length === 0">
                    <p style="color:#aaa; font-size:0.9em; text-align:center; padding:10px 0;">
                        Sin ejes. Usa "+ Eje" para agregar (max 20).
                    </p>
                </template>
            </div>
        </div>

        <!-- Preview JSON -->
        <details style="margin-top:12px;">
            <summary style="cursor:pointer; color:#555; font-size:0.85em;">🔍 Ver JSON generado</summary>
            <pre style="background:#f5f5f5; padding:10px; border-radius:6px;
                        font-size:0.8em; overflow-x:auto;" x-text="jsonValue"></pre>
        </details>

    </div><!-- /Modo Visual -->

</div>
"""
        return mark_safe(widget_html)
