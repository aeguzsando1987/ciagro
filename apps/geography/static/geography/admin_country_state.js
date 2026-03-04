/**
 * admin_country_state.js
 * Cascade País → Estado en el admin Django.
 * Compatible con Jazzmin (select2 vía django.jQuery) y admin stock.
 * Endpoint: /admin/geography/country/states-for-country/?country_id=<pk>
 *
 * Comportamiento:
 *  - Al cargar la página: filtra estados del país ya seleccionado y
 *    re-selecciona el estado guardado (formulario de edición).
 *  - Al cambiar de país: filtra estados del nuevo país y limpia la selección.
 */
document.addEventListener("DOMContentLoaded", function () {
    // Jazzmin carga jQuery dos veces: django.jQuery (admin scripts) y window.jQuery
    // (Bootstrap/AdminLTE). select2 se instala sobre window.jQuery, no sobre django.jQuery.
    // Priorizar window.jQuery para que $(el).data("select2") y .select2() funcionen.
    var $ = window.jQuery || (window.django && window.django.jQuery) || window.$;

    var countrySelect = document.getElementById("id_country");
    var stateSelect   = document.getElementById("id_state");
    if (!countrySelect || !stateSelect) return;

    /**
     * Repobla el dropdown de estado con la lista recibida del endpoint.
     * @param {Array}  states          [{id, name}, ...]
     * @param {string} selectedStateId ID del estado a pre-seleccionar (null = ninguno)
     */
    function setStateOptions(states, selectedStateId) {
        var hasMatch = Boolean(
            selectedStateId &&
            states.some(function (s) { return String(s.id) === String(selectedStateId); })
        );

        // Construir HTML del select nativo
        var html = "<option value=''>---------</option>" +
            states.map(function (s) {
                var sel = hasMatch && String(s.id) === String(selectedStateId) ? " selected" : "";
                return "<option value='" + String(s.id) + "'" + sel + ">" + s.name + "</option>";
            }).join("");

        if ($ && $(stateSelect).data("select2")) {
            // select2 activo (Jazzmin): destroy → update DOM → reinit
            // Manipular el DOM de un select2 ya inicializado deja su caché
            // interno en estado inconsistente. destroy+reinit garantiza que
            // select2 lea las nuevas opciones desde el DOM limpio.
            var s2opts = { allowClear: true, placeholder: "---------", width: "100%" };
            try {
                var captured = $(stateSelect).data("select2").options.options;
                if (captured && typeof captured === "object") { s2opts = captured; }
            } catch (e) {}
            $(stateSelect).select2("destroy");
            stateSelect.innerHTML = html;
            $(stateSelect).select2(s2opts);
            if (hasMatch) {
                $(stateSelect).val(String(selectedStateId)).trigger("change");
            }
        } else {
            // Fallback: select nativo sin select2
            stateSelect.innerHTML = html;
        }
    }

    /**
     * Llama al endpoint y actualiza las opciones de estado.
     * @param {string} countryId       ID del país seleccionado
     * @param {string} preserveStateId Estado a conservar seleccionado (null = limpiar)
     */
    function fetchStates(countryId, preserveStateId) {
        if (!countryId) {
            setStateOptions([], null);
            return;
        }
        fetch("/admin/geography/country/states-for-country/?country_id=" + countryId)
            .then(function (r) { return r.json(); })
            .then(function (data) { setStateOptions(data.states, preserveStateId); });
    }

    // ── 1. Cascade inicial al cargar la página ──────────────────────────────
    // Si el formulario ya tiene un país seleccionado (modo edición), filtra los
    // estados correspondientes y re-selecciona el estado guardado.
    var initialCountry = $ ? $(countrySelect).val() : countrySelect.value;
    var initialState   = $ ? $(stateSelect).val()   : stateSelect.value;
    if (initialCountry) {
        fetchStates(initialCountry, initialState);
    }

    // ── 2. Cascade al cambiar de país ───────────────────────────────────────
    // Cuando el usuario cambia el país, filtra los estados del nuevo país
    // y limpia la selección de estado (debe elegir uno nuevo).
    if ($) {
        $(countrySelect).on("change", function () {
            fetchStates($(this).val(), null);
        });
    } else {
        countrySelect.addEventListener("change", function () {
            fetchStates(this.value, null);
        });
    }
});
