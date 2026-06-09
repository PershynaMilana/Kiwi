from tcms.dao.utils import chunked_queryset, chunked_values  # noqa: F401

# JavaScript's Number.MAX_SAFE_INTEGER = 2^53 - 1
_JS_MAX_SAFE_INT = (1 << 53) - 1


def ensure_safe_json_integers(obj):
    """
    Recursively convert integers that exceed JavaScript's Number.MAX_SAFE_INTEGER
    (2^53 - 1) to strings.

    Firestore auto-generates very large integer document IDs.  When these are
    serialized as JSON numbers and parsed by JavaScript, floating-point rounding
    changes the value (e.g. 4366006222669711641 → 4366006222669712000), causing
    the frontend to construct wrong URLs that return 404.

    Converting large IDs to strings avoids the precision loss because JS string
    concatenation / template literals preserve the exact digits.
    """
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int) and abs(obj) > _JS_MAX_SAFE_INT:
        return str(obj)
    if isinstance(obj, dict):
        return {k: ensure_safe_json_integers(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [ensure_safe_json_integers(v) for v in obj]
    return obj


def generate_safe_pk(model_class, max_attempts=20):
    """
    Generate a unique integer PK within [2^20, 2^31-1] for a new model instance.

    Prevents gcloudc from assigning a Firestore auto-generated document ID
    (which exceeds JS Number.MAX_SAFE_INTEGER) as the model PK.

    A random PK in [1_048_576, 2_147_483_647] is chosen and verified not to
    conflict with an existing row before being returned.
    """
    import random

    _MIN = 1 << 20          # 1 048 576
    _MAX = (1 << 31) - 1   # 2 147 483 647

    for _ in range(max_attempts):
        pk = random.randint(_MIN, _MAX)
        if not model_class.objects.filter(pk=pk).exists():
            return pk

    raise RuntimeError(
        f"Could not generate a unique safe PK for {model_class.__name__} "
        f"in [{_MIN}, {_MAX}] after {max_attempts} attempts."
    )


def normalize_datetimes(instance):
    """
    Convert any DatetimeWithNanoseconds fields on a model instance to plain
    Python datetime objects before writing back to Firestore.

    gcloudc returns DatetimeWithNanoseconds when reading datetime fields from
    Firestore, but google-api-core's timestamp_pb() accesses ._nanosecond which
    does not exist on the google.cloud.firestore variant of that class.
    """
    import datetime
    from django.db.models.fields import DateTimeField
    for field in instance._meta.get_fields():
        if not isinstance(field, DateTimeField):
            continue
        val = getattr(instance, field.attname, None)
        if val is None:
            continue
        # DatetimeWithNanoseconds is a subclass of datetime.datetime; convert
        # any non-plain datetime to a plain datetime to avoid the _nanosecond bug.
        if type(val) is not datetime.datetime:
            try:
                plain = datetime.datetime(
                    val.year, val.month, val.day,
                    val.hour, val.minute, val.second,
                    val.microsecond, val.tzinfo,
                )
                setattr(instance, field.attname, plain)
            except Exception:
                pass


_STRING_OPS = frozenset({
    'startswith', 'istartswith', 'icontains', 'contains',
    'iexact', 'endswith', 'iendswith',
})


def resolve_string_field_ids(model_class, field, operator, value):
    """
    Resolve a string-operator filter (icontains, startswith, …) on a model
    text field by fetching all ``(pk, field_value)`` pairs and filtering in
    Python.

    gcloudc implements string operators by writing a computed field
    (``_idx_icontains_summary`` etc.) to every document **at save time**.
    Pre-existing Firestore documents synced via firebase_admin were never
    saved through gcloudc, so they don't have those computed fields and any
    gcloudc special-index query returns zero results.

    For non-string operators (exact, gt, lt, …) we fall through to a normal
    ORM filter so behaviour is unchanged.
    """
    if operator not in _STRING_OPS:
        return list(
            model_class.objects.filter(**{f"{field}__{operator}": value})
            .values_list("pk", flat=True)
        )

    try:
        all_pairs = list(model_class.objects.all().values_list('pk', field))
    except Exception:
        all_pairs = [(obj.pk, getattr(obj, field, None)) for obj in model_class.objects.all()]

    sv = str(value)
    sv_lower = sv.lower()

    def _match(val):
        if val is None:
            return False
        s = str(val)
        if operator == 'startswith':   return s.startswith(sv)
        if operator == 'istartswith':  return s.lower().startswith(sv_lower)
        if operator == 'icontains':    return sv_lower in s.lower()
        if operator == 'contains':     return sv in s
        if operator == 'iexact':       return s.lower() == sv_lower
        if operator == 'endswith':     return s.endswith(sv)
        if operator == 'iendswith':    return s.lower().endswith(sv_lower)
        return False

    return [pk for pk, val in all_pairs if _match(val)]


def resolve_ids_by_lookup(model_class, lookup_key, value):
    """
    Return a list of PKs matching ``model_class.objects.filter(**{lookup_key: value})``.

    When ``lookup_key`` ends with a string operator (icontains, startswith, …)
    the filter is applied in Python via :func:`resolve_string_field_ids` to
    bypass gcloudc's special-index mechanism.  For all other operators a normal
    ORM filter is used.
    """
    if '__' in lookup_key:
        field, op = lookup_key.rsplit('__', 1)
        if op in _STRING_OPS:
            return resolve_string_field_ids(model_class, field, op, value)
    return list(model_class.objects.filter(**{lookup_key: value}).values_list("pk", flat=True))


def resolve_user_ids(lookup_key, value):
    """
    Translate a user field lookup (e.g. ``'username__startswith'``) to a list
    of matching user PKs without hitting gcloudc's special-index mechanism.

    gcloudc implements ``startswith``/``icontains`` by writing an extra
    computed field (``_idx_startswith_username``) to every document **at save
    time**.  Pre-existing Firestore documents synced via firebase_admin were
    never saved through gcloudc, so they don't have that computed field and
    any gcloudc special-index query returns zero results.

    Instead we fetch all user rows and apply the string operator in Python.
    For an average TCMS installation the user table is small (< a few
    thousand rows), so this is perfectly acceptable.

    For non-string operators (exact, pk, in, …) we fall through to a normal
    ORM filter so behaviour is unchanged.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    _PYTHON_OPS = {'startswith', 'istartswith', 'icontains', 'contains',
                   'iexact', 'endswith', 'iendswith'}

    if '__' in lookup_key:
        field, operator = lookup_key.rsplit('__', 1)
    else:
        field, operator = lookup_key, 'exact'

    if operator not in _PYTHON_OPS:
        # Exact / pk / __in / gt / lt … — safe to push to Firestore
        return list(User.objects.filter(**{lookup_key: value}).values_list("pk", flat=True))

    # Fetch all (pk, field_value) pairs and filter in Python
    all_users = list(User.objects.all().values_list('pk', field))
    sv = str(value)
    sv_lower = sv.lower()

    def _match(val):
        if val is None:
            return False
        s = str(val)
        if operator == 'startswith':
            return s.startswith(sv)
        if operator == 'istartswith':
            return s.lower().startswith(sv_lower)
        if operator == 'icontains':
            return sv_lower in s.lower()
        if operator == 'contains':
            return sv in s
        if operator == 'iexact':
            return s.lower() == sv_lower
        if operator == 'endswith':
            return s.endswith(sv)
        if operator == 'iendswith':
            return s.lower().endswith(sv_lower)
        return False

    return [pk for pk, val in all_users if _match(val)]


def int_pk_only(instances):
    """
    Return only instances whose primary key is a real integer.

    Firestore data-corruption guard: the firebase_admin sync occasionally
    stores documents where the PK field contains the field name as a string
    (e.g. 'id') or a zero-padded Firestore document-ID string
    (e.g. '000000000000000000id').  gcloudc reads these back and creates model
    instances with non-integer PKs.  Passing such PKs to downstream
    ``Model.objects.filter(pk__in=…)`` calls raises ValueError.
    """
    return [obj for obj in instances if isinstance(obj.pk, int)]
