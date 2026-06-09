from django.contrib.auth import get_user_model

from tcms.bugs.models import Bug, Severity
from tcms.dao.firestore.utils import (
    chunked_queryset, ensure_safe_json_integers,
    generate_safe_pk, int_pk_only, resolve_string_field_ids,
    resolve_user_ids, _STRING_OPS,
)
from tcms.management.models import Build, Product, Version

_CHUNK = 90

# Bug text fields that require Python-side string-operator filtering.
_BUG_TEXT_FIELDS = frozenset({'summary', 'notes'})

_BUG_FIELDS = (
    "id",
    "summary",
    "created_at",
    "status",
    "reporter_id",
    "assignee_id",
    "product_id",
    "version_id",
    "build_id",
    "severity_id",
)


class BugDAO:
    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _resolve_bug_query(self, query):
        """Pre-resolve FK traversals and text-field string operators in a Bug filter query."""
        resolved = {}
        bug_id_constraints = []
        for k, v in query.items():
            if k.startswith("reporter__"):
                user_ids = resolve_user_ids(k[len("reporter__"):], v)
                resolved["reporter_id__in"] = user_ids
            elif k.startswith("assignee__"):
                user_ids = resolve_user_ids(k[len("assignee__"):], v)
                resolved["assignee_id__in"] = user_ids
            else:
                # Detect string operators on text fields and filter in Python
                # to bypass gcloudc's special-index mechanism.
                if '__' in k:
                    field, op = k.rsplit('__', 1)
                    if field in _BUG_TEXT_FIELDS and op in _STRING_OPS:
                        matched_ids = resolve_string_field_ids(Bug, field, op, v)
                        bug_id_constraints.append(set(matched_ids))
                        continue
                resolved[k] = v

        if bug_id_constraints:
            final_ids = bug_id_constraints[0]
            for s in bug_id_constraints[1:]:
                final_ids = final_ids & s
            resolved["pk__in"] = list(final_ids)

        return resolved

    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def filter(self, query):
        """
        Return a list of bug dicts matching query.
        Used internally and by Bug.filter_canonical RPC endpoint.
        """
        query = self._resolve_bug_query(query)
        result = [
            {
                "id": b.id,
                "summary": b.summary,
                "created_at": b.created_at,
                "status": b.status,
                "reporter_id": b.reporter_id,
                "assignee_id": b.assignee_id,
                "product_id": b.product_id,
                "version_id": b.version_id,
                "build_id": b.build_id,
                "severity_id": b.severity_id,
            }
            for b in Bug.objects.filter(**query).order_by("id")
        ]
        return [ensure_safe_json_integers(d) for d in result]

    def filter_with_names(self, query):
        """
        Return a list of bug dicts with related field names.
        Used by the Bug.filter RPC endpoint.
        Batch-fetches related objects to avoid cross-collection joins in Firestore.
        """
        User = get_user_model()
        query = self._resolve_bug_query(query)

        bugs = int_pk_only(list(Bug.objects.filter(**query).order_by("id")))
        if not bugs:
            return []

        product_ids = list({b.product_id for b in bugs if b.product_id and isinstance(b.product_id, int)})
        version_ids = list({b.version_id for b in bugs if b.version_id and isinstance(b.version_id, int)})
        build_ids = list({b.build_id for b in bugs if b.build_id and isinstance(b.build_id, int)})
        user_ids = list({uid for b in bugs for uid in (b.reporter_id, b.assignee_id) if uid and isinstance(uid, int)})
        severity_ids = list({b.severity_id for b in bugs if b.severity_id and isinstance(b.severity_id, int)})

        products = {p.pk: p.name for p in chunked_queryset(Product, "pk", product_ids)}
        versions = {v.pk: v.value for v in chunked_queryset(Version, "pk", version_ids)}
        builds = {b.pk: b.name for b in chunked_queryset(Build, "pk", build_ids)}
        users = {u.pk: u.username for u in chunked_queryset(User, "pk", user_ids)}
        severities = {s.pk: s for s in chunked_queryset(Severity, "pk", severity_ids)}

        result = []
        for b in bugs:
            sev = severities.get(b.severity_id)
            result.append({
                "pk": b.pk,
                "summary": b.summary,
                "created_at": b.created_at,
                "product__name": products.get(b.product_id),
                "version__value": versions.get(b.version_id),
                "build__name": builds.get(b.build_id),
                "reporter__username": users.get(b.reporter_id),
                "assignee__username": users.get(b.assignee_id),
                "severity__name": sev.name if sev else None,
                "severity__color": sev.color if sev else None,
                "severity__icon": sev.icon if sev else None,
            })

        return [ensure_safe_json_integers(d) for d in result]

    def filter_canonical(self, query):
        """
        Return a list of bug dicts with FK IDs.
        Used by the Bug.filter_canonical RPC endpoint.
        """
        query = self._resolve_bug_query(query)
        result = [
            {
                "id": b.id,
                "summary": b.summary,
                "created_at": b.created_at,
                "status": b.status,
                "reporter": b.reporter_id,
                "assignee": b.assignee_id,
                "product": b.product_id,
                "version": b.version_id,
                "build": b.build_id,
                "severity": b.severity_id,
            }
            for b in Bug.objects.filter(**query).order_by("id")
        ]
        return [ensure_safe_json_integers(d) for d in result]

    def get_by_id(self, bug_id):
        """
        Return a single Bug object by primary key.
        """
        return Bug.objects.get(pk=bug_id)

    # ------------------------------------------------------------------
    # WRITE operations
    # ------------------------------------------------------------------

    def save(self, bug, update_fields=None):
        """
        Persist a Bug object.
        Used by Bug.create and Bug.update RPC endpoints.
        """
        if bug.pk is None:
            bug.pk = generate_safe_pk(Bug)
        if update_fields:
            bug.save(update_fields=update_fields)
        else:
            bug.save()
        return bug

    def remove(self, query):
        """
        Delete Bug objects matching query.
        Used by Bug.remove RPC endpoint.
        """
        return Bug.objects.filter(**query).delete()


bug_dao = BugDAO()
