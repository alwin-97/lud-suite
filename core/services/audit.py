"""Stable scope identifiers and field values for configuration audit records."""


def scope_ids(scope):
    kind = scope._meta.model_name
    result = {kind: scope.pk}
    if kind == "cohort":
        scope = scope.chapter
        result["chapter"] = scope.pk
        kind = "chapter"
    if kind == "chapter":
        scope = scope.location
        result["location"] = scope.pk
        kind = "location"
    if kind == "location":
        result["program"] = scope.program_id
    return result


def configuration_values(obj, field_names):
    result = {}
    for name in field_names:
        field = obj._meta.get_field(name)
        value = getattr(obj, field.attname)
        result[name] = value.isoformat() if hasattr(value, "isoformat") else value
    return result
