from datetime import date

from django import forms
from django.utils.safestring import mark_safe


class CycleWidget(forms.Widget):
    """
    Widget que divide el campo 'cycle' (CharField con formato YYYY-A o YYYY-B)
    en dos selectores visuales: Año y Período (A / B).

    Al hacer submit, value_from_datadict combina ambos selectores y devuelve
    el string "YYYY-A" o "YYYY-B" que el RegexValidator del campo sigue validando
    exactamente igual que con un TextInput.

    Renderiza dos <select> independientes con nombres:
      - {name}_year  → selector de año
      - {name}_period → selector de período (A o B)
    """

    def render(self, name, value, attrs=None, renderer=None):
        current_year = date.today().year

        # Parsear valor existente
        year = str(current_year)
        period = "A"
        if value and len(value) == 6 and value[4] == "-":
            year = value[:4]
            period = value[5]

        # Opciones de año: 5 años atrás, 2 años adelante
        year_options = "".join(
            f'<option value="{y}" {"selected" if str(y) == year else ""}>{y}</option>'
            for y in range(current_year - 5, current_year + 3)
        )

        html = (
            f'<div style="display:flex;gap:10px;align-items:center">'
            f'  <select name="{name}_year" style="width:95px">{year_options}</select>'
            f'  <select name="{name}_period" style="width:65px">'
            f'    <option value="A" {"selected" if period == "A" else ""}>A</option>'
            f'    <option value="B" {"selected" if period == "B" else ""}>B</option>'
            f'  </select>'
            f'  <span style="color:#666;font-size:12px">'
            f'    → resultado: <strong>{year}-{period}</strong>'
            f'    &nbsp;(ciclo agrícola: A = primer semestre, B = segundo semestre)'
            f'  </span>'
            f'</div>'
        )
        return mark_safe(html)

    def value_from_datadict(self, data, files, name):
        """Combina los dos selectores en el valor final 'YYYY-A' o 'YYYY-B'."""
        year = data.get(f"{name}_year", "")
        period = data.get(f"{name}_period", "A")
        if year:
            return f"{year}-{period}"
        return ""

    def use_required_attribute(self, initial_value):
        """Evitar que Django añada 'required' al HTML (el campo puede ser null/blank)."""
        return False
