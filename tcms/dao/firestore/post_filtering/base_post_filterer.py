from datetime import datetime


class BasePostFilterer:
    """
    Applies Django ORM-style filter criteria to an in-memory list of dicts.

    Supports:
    - Exact match:        {'name': 'foo', 'product': 61}
    - icontains:          {'name__icontains': 'foo'}
    - contains:           {'name__contains': 'foo'}
    - in:                 {'type__in': [1, 2]}
    - startswith:         {'name__startswith': 'Test'}
    - istartswith:        {'name__istartswith': 'test'}
    - gt / gte / lt / lte: {'id__gt': 10}
    - isnull:             {'parent__isnull': True}

    For stored cross-table fields like 'product__name', an exact match is tried
    first before attempting to split into field + lookup operator.
    """

    _LOOKUP_HANDLERS = {
        'icontains': lambda val, arg: isinstance(val, str) and arg.lower() in val.lower(),
        'contains': lambda val, arg: arg in (val or ''),
        'in': lambda val, arg: val in arg,
        'startswith': lambda val, arg: isinstance(val, str) and val.startswith(arg),
        'istartswith': lambda val, arg: isinstance(val, str) and val.lower().startswith(arg.lower()),
        'gt': lambda val, arg: val is not None and val > arg,
        'gte': lambda val, arg: val is not None and val >= arg,
        'lt': lambda val, arg: val is not None and val < arg,
        'lte': lambda val, arg: val is not None and val <= arg,
        'isnull': lambda val, arg: (val is None) == arg,
    }

    def filter(self, documents: list, criteria: dict) -> list:
        documents = [self._normalize_doc(doc) for doc in documents]
        criteria = self._normalize_criteria(criteria)
        result = documents
        for key, value in criteria.items():
            result = [doc for doc in result if self._matches(doc, key, value)]
        return result

    def _normalize_criteria(self, criteria: dict) -> dict:
        """Convert string filter values to int where possible.

        HTML select elements always produce string values, but Firestore stores
        FK IDs as integers. Without this, '5' in [5] is False.
        """
        return {k: self._coerce_value(v) for k, v in criteria.items()}

    def _coerce_value(self, value):
        if isinstance(value, str):
            try:
                return int(value)
            except (ValueError, TypeError):
                return value
        if isinstance(value, list):
            return [self._coerce_value(v) for v in value]
        return value

    def _normalize_doc(self, doc: dict) -> dict:
        return {k: self._normalize_value(v) for k, v in doc.items()}

    def _normalize_value(self, v):
        if isinstance(v, datetime) and type(v) is not datetime:
            return datetime(v.year, v.month, v.day, v.hour, v.minute, v.second, v.microsecond, v.tzinfo)
        return v

    def _matches(self, doc: dict, key: str, value) -> bool:
        # Django uses 'pk' as an alias for the primary key field 'id'.
        # Translate 'pk' and 'pk__<lookup>' to 'id' / 'id__<lookup>'.
        if key == 'pk' or key.startswith('pk__'):
            key = 'id' + key[2:]

        # If the full key is a stored field, do an exact match on it.
        # This handles cross-table fields like 'product__name' that _to_dict()
        # stores directly in the document.
        if key in doc:
            return doc[key] == value

        # Django FK fields: filter(product=X) == filter(product_id=X).
        # Firestore documents store FK values as '<field>_id', so try that.
        if key + '_id' in doc:
            return doc[key + '_id'] == value

        # Otherwise split on the rightmost '__' to get field + lookup operator.
        if '__' in key:
            field, lookup = key.rsplit('__', 1)
            handler = self._LOOKUP_HANDLERS.get(lookup)
            if handler:
                # Resolve FK alias: 'product' → 'product_id' if needed.
                if field in doc:
                    val = doc[field]
                elif field + '_id' in doc:
                    val = doc[field + '_id']
                else:
                    val = None
                return handler(val, value)

        # Fall back to exact match (field simply not present → no match).
        return doc.get(key) == value
