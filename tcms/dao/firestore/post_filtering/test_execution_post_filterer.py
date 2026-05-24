from tcms.dao.firestore.post_filtering.base_post_filterer import BasePostFilterer


class TestExecutionPostFilterer(BasePostFilterer):
    """
    Post-filterer for TestExecution Firestore documents.

    Normalises JS-issued filter keys before delegating to BasePostFilterer:
    - run_id  → run        (JS initial load uses run_id; doc stores 'run')
    - status_id__in → status__in  (URL ?status_id=4 filter; doc stores 'status')
    """

    def filter(self, documents: list, criteria: dict) -> list:
        criteria = self._normalize_execution_criteria(criteria)
        return super().filter(documents, criteria)

    def _normalize_execution_criteria(self, criteria: dict) -> dict:
        criteria = dict(criteria)
        if 'run_id' in criteria:
            criteria['run'] = criteria.pop('run_id')
        if 'status_id__in' in criteria:
            criteria['status__in'] = criteria.pop('status_id__in')
        return criteria
