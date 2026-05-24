from tcms.dao.firestore.post_filtering.base_post_filterer import BasePostFilterer


class BuildPostFilterer(BasePostFilterer):
    """
    Post-filterer for Build Firestore documents.

    Handles the cross-table 'version__plans' lookup used by the new-run page JS:
    Build.filter({ version__plans: planId }) → resolve planId → product_version_id
    → filter builds by version_id.
    """

    def filter(self, documents: list, criteria: dict) -> list:
        criteria = self._resolve_version_plans(criteria)
        return super().filter(documents, criteria)

    def _resolve_version_plans(self, criteria: dict) -> dict:
        """Convert 'version__plans' cross-table lookup to a plain 'version_id' match."""
        if 'version__plans' not in criteria:
            return criteria

        from tcms.testplans.models import TestPlan

        criteria = dict(criteria)
        plan_id = criteria.pop('version__plans')
        try:
            plan_id = int(plan_id)
        except (ValueError, TypeError):
            pass

        try:
            version_id = TestPlan.objects.values_list('product_version_id', flat=True).get(pk=plan_id)
            criteria['version_id'] = version_id
        except TestPlan.DoesNotExist:
            criteria['version_id'] = -1

        return criteria
