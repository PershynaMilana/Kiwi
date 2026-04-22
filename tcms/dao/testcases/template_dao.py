from tcms.testcases.models import Template

_FIELDS = ("id", "name", "text")


class TemplateDAO:
    def __init__(self):
        self._store = {}

    def _to_dict(self, template):
        return {field: getattr(template, field) for field in _FIELDS}

    def _compare(self, old, new, operation):
        if old != new:
            print(f"[TemplateDAO] MISMATCH in '{operation}':")
            print(f"  OLD: {old}")
            print(f"  NEW: {new}")
        else:
            print(f"[TemplateDAO] OK '{operation}': results match")

    def filter(self, query):
        old_result = list(
            Template.objects.filter(**query)
            .values(*_FIELDS)
            .order_by("id")
            .distinct()
        )

        new_result = [self._store[t["id"]] for t in old_result if t["id"] in self._store]
        if new_result:
            old_subset = [t for t in old_result if t["id"] in self._store]
            self._compare(old_subset, new_result, "filter")
        else:
            print("[TemplateDAO] filter: no data in new storage yet - skipping comparison")

        return old_result

    def get_by_id(self, template_id):
        old_result = Template.objects.get(pk=template_id)

        new_result = self._store.get(template_id)
        if new_result is not None:
            self._compare(self._to_dict(old_result), new_result, "get_by_id")
        else:
            print(f"[TemplateDAO] get_by_id: template id={template_id} not in new storage yet - skipping comparison")

        return old_result

    def save(self, template):
        template.save()
        self._store[template.pk] = self._to_dict(template)
        print(f"[TemplateDAO] save: synced template id={template.pk} to new storage")
        return template


template_dao = TemplateDAO()