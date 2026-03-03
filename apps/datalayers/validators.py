from rest_framework.exceptions import ValidationError


def validate_raw_data_against_scheme(raw_data: dict, definition_scheme: dict) -> None:
    '''
    Funcion para validar los datos del csv contra la definicion dada en el definition_scheme de un datalayer
    Sigue estas reglas:
    - Si el definition_scheme es None, no se hace ninguna validacion (pasa por que no hay definicion aun)
    - Si no hay campos "required", entonces pasa
    - Si resuelven alias de campos. Ejemplo: "pH" se trata como "ph" si esta declarado en definition_scheme como alias
    - Si falta un campo "required" --> ValidationError con la lista de campos faltantes
    
    args:
        raw_data: diccionario con los datos del csv
        definition_scheme: diccionario con la definicion del datalayer (required, optional, aliases, units)
    '''
    if not definition_scheme:
        return
    
    required = definition_scheme.get("required", [])
    if not required:
        return

    aliases = definition_scheme.get("aliases", {})
    
    # Mapeo inverso: alias >> nombre canonico
    # p. ej. {"pH": "ph", "PH": "ph", "OM": "om", "MO": "om"}
    alias_to_canonical = {}
    for canonical, alias_list in aliases.items():
        for alias in alias_list:
            alias_to_canonical[alias] = canonical
            
    # REsolver las keys de raw_data a nombres canonicos
    resolved_keys = {alias_to_canonical.get(key, key) for key in raw_data.keys()}
    
    # Verificar campos requeridos
    missing = [field for field in required if field not in resolved_keys]
    if missing:
        raise ValidationError(
            f"Campos requeridos faltantes segun la definicion del analisis: {', '.join(missing)}\nRevisar esquema de definicion."
            )
        
