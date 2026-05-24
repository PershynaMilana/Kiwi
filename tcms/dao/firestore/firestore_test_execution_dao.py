from datetime import timedelta

from django.db.models import F

from tcms.dao.firestore.client import get_firestore_client
from tcms.dao.firestore.post_filtering.test_execution_post_filterer import TestExecutionPostFilterer
from tcms.testruns.models import TestExecution

_COLLECTION = 'test_executions'

_TEST_EXECUTION_FIELDS = (
    'id', 'assignee', 'tested_by', 'case_text_version', 'start_date',
    'stop_date', 'sortkey', 'run', 'case', 'status', 'build',
)


class FirestoreTestExecutionDAO:
    """
    Firestore-backed DAO for TestExecution.

    filter()  — reads from Firestore, applies post-filtering in Python.
    save()    — dual-write: persists via ORM then syncs the document to Firestore.

    get_by_id() is not implemented here because it returns a Django ORM object
    required by the view layer.
    """

    def __init__(self):
        db = get_firestore_client()
        self._collection = db.collection(_COLLECTION)
        self._post_filterer = TestExecutionPostFilterer()

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _to_dict(self, execution):
        result = {field: getattr(execution, field) for field in _TEST_EXECUTION_FIELDS}
        result['assignee'] = execution.assignee_id
        result['tested_by'] = execution.tested_by_id
        result['run'] = execution.run_id
        result['case'] = execution.case_id
        result['status'] = execution.status_id
        result['build'] = execution.build_id
        result['expected_duration'] = int((
            (execution.case.setup_duration or timedelta(0))
            + (execution.case.testing_duration or timedelta(0))
        ).total_seconds())
        extra = TestExecution.objects.filter(pk=execution.pk).annotate(
            actual_duration=F('stop_date') - F('start_date'),
        ).values(
            'assignee__username', 'tested_by__username', 'case__summary',
            'build__name', 'status__name', 'status__icon', 'status__color',
            'actual_duration',
        ).first() or {}
        actual = extra.pop('actual_duration', None)
        result['actual_duration'] = int(actual.total_seconds()) if actual else None
        result.update(extra)
        return result

    def _doc_ref(self, execution_id):
        return self._collection.document(str(execution_id))

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def filter(self, query):
        """
        Fetch all TestExecution documents from Firestore and apply criteria
        on the application side (post-filtering).
        """
        all_docs = [doc.to_dict() for doc in self._collection.stream()]
        return self._post_filterer.filter(all_docs, query)

    # ------------------------------------------------------------------
    # WRITE
    # ------------------------------------------------------------------

    def save(self, execution, update_fields=None):
        """Persist a TestExecution: ORM save first, then sync to Firestore."""
        if update_fields:
            execution.save(update_fields=update_fields)
        else:
            execution.save()

        self._doc_ref(execution.pk).set(self._to_dict(execution))
        return execution

    def remove(self, query):
        """Delete TestExecution objects matching query in ORM and Firestore."""
        execution_ids = list(TestExecution.objects.filter(**query).values_list('pk', flat=True))
        deleted = TestExecution.objects.filter(**query).delete()

        for execution_id in execution_ids:
            self._doc_ref(execution_id).delete()

        return deleted


firestore_test_execution_dao = FirestoreTestExecutionDAO()
