_CHUNK_SIZE = 90


def chunked_queryset(model_class, id_field, ids, **extra_filter):
    """Fetch model instances in chunks to stay under the 100-OR-branch Firestore limit."""
    ids = list(ids)
    result = []
    for i in range(0, len(ids), _CHUNK_SIZE):
        chunk = ids[i:i + _CHUNK_SIZE]
        result.extend(model_class.objects.filter(**{f"{id_field}__in": chunk}, **extra_filter))
    return result


def chunked_values(model_class, id_field, ids, *value_fields, **extra_filter):
    """Like chunked_queryset but returns .values() dicts."""
    ids = list(ids)
    result = []
    for i in range(0, len(ids), _CHUNK_SIZE):
        chunk = ids[i:i + _CHUNK_SIZE]
        result.extend(
            model_class.objects.filter(**{f"{id_field}__in": chunk}, **extra_filter)
            .values(*value_fields)
        )
    return result
