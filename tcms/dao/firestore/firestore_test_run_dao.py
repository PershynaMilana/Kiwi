from django.forms.models import model_to_dict

from tcms.dao.firestore.client import get_firestore_client
from tcms.dao.firestore.post_filtering.test_run_post_filterer import TestRunPostFilterer
from tcms.testcases.models import TestCase
from tcms.testruns.models import TestExecution, TestRun

_COLLECTION = 'test_runs'
_RUN_CASES_COLLECTION = 'test_run_cases'
_RUN_CC_COLLECTION = 'test_run_cc'

_TEST_RUN_FIELDS = (
    'id', 'start_date', 'stop_date', 'planned_start', 'planned_stop',
    'summary', 'notes', 'plan', 'build', 'manager', 'default_tester',
)


class FirestoreTestRunDAO:
    """
    Firestore-backed DAO for TestRun.

    filter()  — reads from Firestore, applies post-filtering in Python.
    save()    — dual-write: persists via ORM then syncs the document to Firestore.

    filter_objects() and get_by_id() are not implemented here because they
    return Django ORM objects required by the view layer.
    """

    def __init__(self):
        db = get_firestore_client()
        self._collection = db.collection(_COLLECTION)
        self._run_cases_collection = db.collection(_RUN_CASES_COLLECTION)
        self._run_cc_collection = db.collection(_RUN_CC_COLLECTION)
        self._post_filterer = TestRunPostFilterer()

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _to_dict(self, run):
        result = {field: getattr(run, field) for field in _TEST_RUN_FIELDS}
        result['plan'] = run.plan_id
        result['build'] = run.build_id
        result['manager'] = run.manager_id
        result['default_tester'] = run.default_tester_id
        extra = TestRun.objects.filter(pk=run.pk).values(
            'plan__name', 'build__name', 'build__version', 'build__version__value',
            'build__version__product', 'manager__username', 'default_tester__username',
        ).first() or {}
        result.update(extra)
        return result

    def _doc_ref(self, run_id):
        return self._collection.document(str(run_id))

    @staticmethod
    def _annotate_executions(executions_iterable):
        result = []
        for execution in executions_iterable:
            serialized = model_to_dict(execution)
            serialized['properties'] = list(
                execution.properties().values('name', 'value')
            )
            result.append(serialized)
        return result

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def filter(self, query):
        """
        Fetch all TestRun documents from Firestore and apply criteria
        on the application side (post-filtering).
        """
        all_docs = [doc.to_dict() for doc in self._collection.stream()]
        return self._post_filterer.filter(all_docs, query)

    # ------------------------------------------------------------------
    # WRITE
    # ------------------------------------------------------------------

    def save(self, run, update_fields=None):
        """Persist a TestRun: ORM save first, then sync to Firestore."""
        if update_fields:
            run.save(update_fields=update_fields)
        else:
            run.save()

        self._doc_ref(run.pk).set(self._to_dict(run))
        return run

    def remove(self, query):
        """Delete TestRun objects matching query in ORM and Firestore."""
        run_ids = list(TestRun.objects.filter(**query).values_list('pk', flat=True))
        deleted = TestRun.objects.filter(**query).delete()

        for run_id in run_ids:
            self._doc_ref(run_id).delete()

        return deleted

    def add_case(self, run, case):
        """Add a TestCase to a TestRun (creates TestExecution) in ORM and Firestore."""
        if run.executions.filter(case=case).exists():
            return self._annotate_executions(run.executions.filter(case=case))

        if not case.case_status.is_confirmed:
            raise RuntimeError(f'TC-{case.pk} status is not confirmed')

        sortkey = 10
        last_te = run.executions.order_by('sortkey').last()
        if last_te:
            sortkey += last_te.sortkey

        result = self._annotate_executions(
            run.create_execution(case=case, sortkey=sortkey)
        )

        self._run_cases_collection.document(f'{run.pk}_{case.pk}').set({
            'run_id': run.pk,
            'case_id': case.pk,
            'sortkey': sortkey,
        })

        return result

    def remove_case(self, run_id, case_id):
        """Remove a TestCase from a TestRun in ORM and Firestore."""
        TestExecution.objects.filter(run=run_id, case=case_id).delete()
        self._run_cases_collection.document(f'{run_id}_{case_id}').delete()

    def get_cases(self, run_id):
        """Return test cases attached to the given run with execution info."""
        result = list(
            TestCase.objects.filter(executions__run_id=run_id).values(
                'id', 'create_date', 'is_automated', 'script', 'arguments',
                'extra_link', 'summary', 'requirement', 'notes', 'text',
                'case_status', 'category', 'priority', 'author',
                'default_tester', 'reviewer',
            )
        )

        executions = TestExecution.objects.filter(run_id=run_id).values('case', 'pk', 'status__name')
        extra_info = {row['case']: row for row in executions.iterator()}
        for case in result:
            info = extra_info[case['id']]
            case['execution_id'] = info['pk']
            case['status'] = info['status__name']

        return result

    def add_cc(self, run, user):
        """Add a user to run CC list in ORM and Firestore."""
        run.add_cc(user)
        self._run_cc_collection.document(f'{run.pk}_{user.pk}').set({
            'run_id': run.pk,
            'email': user.email,
        })

    def remove_cc(self, run, user):
        """Remove a user from run CC list in ORM and Firestore."""
        run.remove_cc(user)
        self._run_cc_collection.document(f'{run.pk}_{user.pk}').delete()

    def get_cc(self, run):
        """Return CC email list for the given run."""
        return list(run.cc.values_list('email', flat=True))


firestore_test_run_dao = FirestoreTestRunDAO()
