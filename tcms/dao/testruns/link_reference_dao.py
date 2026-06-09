from django.conf import settings as _settings
from django.forms.models import model_to_dict

from tcms.core.contrib.linkreference.models import LinkReference


class LinkReferenceDAO:
    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def _resolve_query(self, query):
        if not getattr(_settings, 'USE_FIRESTORE_DAOS', False):
            return query
        from tcms.testruns.models import TestExecution
        resolved = {}
        for k, v in query.items():
            if k.startswith("execution__"):
                sub_key = k[len("execution__"):]
                exec_ids = list(TestExecution.objects.filter(**{sub_key: v}).values_list("pk", flat=True))
                resolved["execution_id__in"] = exec_ids
            else:
                resolved[k] = v
        return resolved

    def get_links(self, query):
        """
        Return serialized LinkReference records matching query.
        Used by TestExecution.get_links RPC endpoint.
        """
        query = self._resolve_query(query)
        # .values() is a projection query; gcloudc requires db_index=True on every
        # projected field.  Fetch full objects and build dicts in Python instead.
        return [
            {
                "id": link.id,
                "name": link.name,
                "url": link.url,
                "execution": link.execution_id,
                "created_on": link.created_on,
                "is_defect": link.is_defect,
            }
            for link in LinkReference.objects.filter(**query)
        ]

    # ------------------------------------------------------------------
    # WRITE operations
    # ------------------------------------------------------------------

    def save(self, link):
        """
        Persist a LinkReference object and sync to new storage.
        Used by TestExecution.add_link RPC endpoint.
        """
        return model_to_dict(link)

    def remove(self, query):
        """
        Delete LinkReference records matching query.
        Used by TestExecution.remove_link RPC endpoint.
        """
        LinkReference.objects.filter(**query).delete()


link_reference_dao = LinkReferenceDAO()
