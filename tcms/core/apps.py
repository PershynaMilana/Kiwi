from django.apps import AppConfig
from django.db import router, DEFAULT_DB_ALIAS
from django.db.models.signals import post_migrate


def _safe_create_permissions(
    app_config,
    verbosity=2,
    interactive=True,
    using=DEFAULT_DB_ALIAS,
    apps=None,
    **kwargs,
):
    """
    Firestore-safe replacement for django.contrib.auth.management.create_permissions.
    Uses get_or_create per permission instead of bulk_create so that gcloudc's
    in-memory unique-constraint checker never sees duplicates in a single batch.
    """
    from django.apps import apps as global_apps
    from django.contrib.auth import get_permission_codename
    from django.contrib.contenttypes.management import create_contenttypes

    if apps is None:
        apps = global_apps

    if not app_config.models_module:
        return

    create_contenttypes(
        app_config,
        verbosity=verbosity,
        interactive=interactive,
        using=using,
        apps=apps,
    )

    try:
        ContentType = apps.get_model("contenttypes", "ContentType")
        Permission = apps.get_model("auth", "Permission")
    except LookupError:
        return

    if not router.allow_migrate_model(using, Permission):
        return

    for klass in app_config.get_models():
        ct = ContentType.objects.db_manager(using).get_for_model(
            klass, for_concrete_model=False
        )
        for action in klass._meta.default_permissions:
            codename = get_permission_codename(action, klass._meta)
            name = f"Can {action} {klass._meta.verbose_name_raw}"
            _, created = Permission.objects.using(using).get_or_create(
                codename=codename,
                content_type=ct,
                defaults={"name": name},
            )
            if created and verbosity >= 2:
                print(f"Adding permission '{codename}'")
        for codename, name in klass._meta.permissions:
            _, created = Permission.objects.using(using).get_or_create(
                codename=codename,
                content_type=ct,
                defaults={"name": name},
            )
            if created and verbosity >= 2:
                print(f"Adding permission '{codename}'")


def _patch_gcloudc_duration_converter():
    """
    Monkey-patch gcloudc's Firestore DatabaseOperations so that DurationField
    values synced as strings (e.g. "0:00:00" or "12345") are safely coerced to
    int microseconds before being passed to timedelta().

    Django's base convert_durationfield_value does:
        timedelta(0, 0, value)   # 3rd positional arg = microseconds
    which crashes with TypeError when `value` is a string.  gcloudc does not
    override this method, so we patch it here.
    """
    import datetime
    import re

    def _str_to_us(value):
        """Convert a string duration to integer microseconds."""
        try:
            return int(value)
        except (ValueError, TypeError):
            pass
        # "H:MM:SS[.ffffff]" or "-H:MM:SS[.ffffff]"
        m = re.match(r'(-?)(\d+):(\d{2}):(\d{2})(?:\.(\d+))?$', str(value))
        if m:
            sign = -1 if m.group(1) else 1
            h, mn, s = int(m.group(2)), int(m.group(3)), int(m.group(4))
            us = int(m.group(5).ljust(6, '0')[:6]) if m.group(5) else 0
            td = datetime.timedelta(hours=h, minutes=mn, seconds=s, microseconds=us)
            return int(sign * td.total_seconds() * 1_000_000)
        return 0

    def _safe_convert_durationfield_value(self, value, expression, connection):
        if value is None:
            return None
        if isinstance(value, datetime.timedelta):
            return value
        if isinstance(value, str):
            value = _str_to_us(value)
        return datetime.timedelta(0, 0, int(value))

    try:
        from gcloudc.db.backends.firestore.base import DatabaseOperations
        DatabaseOperations.convert_durationfield_value = _safe_convert_durationfield_value
    except ImportError:
        pass  # gcloudc not installed — running with plain Postgres, nothing to patch


def _patch_boolean_field_from_db():
    """
    Add from_db_value() to Django's BooleanField so that Firestore documents
    where boolean fields were synced as the field-name string (e.g. 'is_staff')
    are coerced to a proper Python bool instead of crashing Django admin's
    _boolean_icon() template tag with a KeyError.

    Django only calls from_db_value() when the method is defined on the field;
    adding it here is safe for all backends because proper booleans pass through
    the isinstance(value, bool) fast-path unchanged.
    """
    from django.db.models import BooleanField

    def _bool_from_db_value(self, value, expression, connection):
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            # coerce truthy strings; anything else (corrupted field names, etc.) → False
            return value.lower() in ('true', '1', 't', 'yes')
        return bool(value)

    BooleanField.from_db_value = _bool_from_db_value


def _patch_m2m_value_from_object():
    """
    Patch ManyToManyField.value_from_object to avoid cross-join queries in Firestore.

    Django's standard M2M manager .all() generates a JOIN between the junction
    table and the target table.  gcloudc raises NotSupportedError for cross-joins.
    We intercept that error and fall back to an explicit two-step query:

        1. Query the junction table for target IDs  (single-collection = OK)
        2. Query the target collection by pk__in    (single-collection IN = OK)

    This is used, e.g., by Django admin's model_to_dict() when rendering the
    User change form (groups + user_permissions M2M fields).
    """
    from django.db.utils import DatabaseError
    from django.db.models.fields.related import ManyToManyField

    original_value_from_object = ManyToManyField.value_from_object

    def _safe_value_from_object(self, obj):
        if not obj._is_pk_set():
            return []
        try:
            return original_value_from_object(self, obj)
        except (DatabaseError, Exception):
            # Cross-join not supported by gcloudc: fall back to two-step query.
            try:
                through = getattr(obj, self.name).through
                # Locate the source FK (→ obj model) and target FK (→ related model)
                # from the junction model's concrete local fields.
                source_attname = None
                target_attname = None
                for f in through._meta.local_fields:
                    rel = getattr(f, 'related_model', None)
                    if rel is None:
                        continue
                    if issubclass(type(obj), rel):
                        source_attname = f.attname   # e.g. 'user_id'
                    elif rel == self.related_model:
                        target_attname = f.attname   # e.g. 'group_id'
                if source_attname and target_attname:
                    target_ids = list(
                        through.objects
                        .filter(**{source_attname: obj.pk})
                        .values_list(target_attname, flat=True)
                    )
                    return list(self.related_model.objects.filter(pk__in=target_ids))
            except Exception:
                pass
            return []

    ManyToManyField.value_from_object = _safe_value_from_object


def _patch_model_backend_permissions():
    """
    Patch Django's ModelBackend._get_permissions to avoid cross-collection JOIN queries.

    Django's default implementation does:
        Permission.objects.filter(...).values_list('content_type__app_label', 'codename')

    The 'content_type__app_label' traversal is a JOIN between auth_permission and
    django_content_type — two separate Firestore collections — which gcloudc rejects
    with NotSupportedError.

    This replacement does the same work with three single-collection queries:
        1. junction table  → permission PKs
        2. Permission      → Permission objects (batch by PK)
        3. ContentType     → ContentType objects (batch by PK)
    then builds the 'app_label.codename' strings in Python.
    """
    import logging
    from django.contrib.auth.backends import ModelBackend
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth.models import Permission, Group

    _log = logging.getLogger(__name__)
    _CHUNK = 90

    def _chunked_pks(qs_class, pk_list):
        result = []
        for i in range(0, len(pk_list), _CHUNK):
            result.extend(qs_class.objects.filter(pk__in=pk_list[i:i + _CHUNK]).order_by())
        return result

    def _through_fk_attnames(through_model, source_model, target_model):
        """
        Return (source_attname, target_attname) for a M2M through model by
        introspecting its local FK fields.  Works for auto-created and explicit
        through models regardless of custom field naming.
        """
        src, tgt = None, None
        for field in through_model._meta.local_fields:
            rel = getattr(field, 'related_model', None)
            if rel is None:
                continue
            if rel is source_model or (isinstance(rel, type) and issubclass(source_model, rel)):
                src = field.attname
            elif rel is target_model:
                tgt = field.attname
        return src, tgt

    def _safe_get_permissions(self, user_obj, obj, from_name):
        if not user_obj.is_active or user_obj.is_anonymous or obj is not None:
            return set()

        perm_cache_name = f'_{from_name}_perm_cache'
        if hasattr(user_obj, perm_cache_name):
            return getattr(user_obj, perm_cache_name)

        User = type(user_obj)

        try:
            if user_obj.is_superuser:
                perms = list(Permission.objects.all().order_by())
            elif from_name == 'user':
                # User → user_permissions junction → Permission
                up_through = User._meta.get_field('user_permissions').remote_field.through
                u_att, p_att = _through_fk_attnames(up_through, User, Permission)
                if not u_att or not p_att:
                    perms = []
                else:
                    rows = list(up_through.objects.filter(**{u_att: user_obj.pk}).order_by())
                    perms = _chunked_pks(Permission, [getattr(r, p_att) for r in rows])
            elif from_name == 'group':
                # User → groups junction → Group → permissions junction → Permission
                ug_through = User._meta.get_field('groups').remote_field.through
                u_att, g_att = _through_fk_attnames(ug_through, User, Group)
                if not u_att or not g_att:
                    perms = []
                else:
                    g_rows = list(ug_through.objects.filter(**{u_att: user_obj.pk}).order_by())
                    group_ids = [getattr(r, g_att) for r in g_rows]
                    if not group_ids:
                        perms = []
                    else:
                        gp_through = Group._meta.get_field('permissions').remote_field.through
                        g_att2, p_att = _through_fk_attnames(gp_through, Group, Permission)
                        if not g_att2 or not p_att:
                            perms = []
                        else:
                            perm_ids = []
                            for i in range(0, len(group_ids), _CHUNK):
                                gp_rows = list(
                                    gp_through.objects
                                    .filter(**{f'{g_att2}__in': group_ids[i:i + _CHUNK]})
                                    .order_by()
                                )
                                perm_ids.extend(getattr(r, p_att) for r in gp_rows)
                            perms = _chunked_pks(Permission, perm_ids)
            else:
                perms = []

            ct_ids = list({p.content_type_id for p in perms if p.content_type_id})
            ct_map = {ct.pk: ct.app_label for ct in _chunked_pks(ContentType, ct_ids)}

            result = {
                f'{ct_map[p.content_type_id]}.{p.codename}'
                for p in perms
                if p.content_type_id in ct_map
            }
        except Exception:
            _log.exception('_safe_get_permissions failed for user %s (from_name=%s)', user_obj, from_name)
            result = set()

        setattr(user_obj, perm_cache_name, result)
        return result

    ModelBackend._get_permissions = _safe_get_permissions


def _patch_fk_descriptor_for_corrupted_ids():
    """
    Patch Django's ForwardManyToOneDescriptor so that Firestore data-corruption
    in FK id fields never crashes template rendering.  Two corruption variants
    are handled:

    1. FK id stored as the field-name string ('version_id') → ValueError when
       Django tries Version.objects.get(pk='version_id').
    2. FK id is a valid-looking integer but the related object was never synced
       to Firestore → RelatedObjectDoesNotExist (subclass of ObjectDoesNotExist).

    Both variants now return None (the admin renders an empty cell) instead of
    a 500 error.
    """
    from django.core.exceptions import ObjectDoesNotExist
    from django.db.models.fields.related_descriptors import ForwardManyToOneDescriptor

    original_get = ForwardManyToOneDescriptor.__get__

    def _safe_fk_get(self, instance, cls=None):
        if instance is None:
            return self
        try:
            return original_get(self, instance, cls)
        except (ValueError, TypeError, ObjectDoesNotExist):
            # Cache None so the descriptor isn't re-attempted on every attribute access.
            try:
                self.field.set_cached_value(instance, None)
            except Exception:
                pass
            return None

    ForwardManyToOneDescriptor.__get__ = _safe_fk_get


class CoreConfig(AppConfig):
    name = "tcms.core"

    def ready(self):
        from django.conf import settings
        from django.contrib.auth.management import create_permissions

        if getattr(settings, 'USE_FIRESTORE_DAOS', False):
            _patch_gcloudc_duration_converter()
            _patch_boolean_field_from_db()
            _patch_fk_descriptor_for_corrupted_ids()
            _patch_m2m_value_from_object()
            _patch_model_backend_permissions()

        post_migrate.disconnect(
            create_permissions,
            dispatch_uid="django.contrib.auth.management.create_permissions",
        )
        post_migrate.connect(
            _safe_create_permissions,
            dispatch_uid="django.contrib.auth.management.create_permissions",
        )
