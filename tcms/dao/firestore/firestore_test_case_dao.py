from datetime import timedelta

from django.forms.models import model_to_dict

from tcms.dao.firestore.client import get_firestore_client
from tcms.dao.firestore.post_filtering.test_case_post_filterer import TestCasePostFilterer
from tcms.testcases.models import TestCase

_COLLECTION = 'test_cases'
_COMPONENTS_COLLECTION = 'test_case_components'
_CC_COLLECTION = 'test_case_notification_cc'

_TEST_CASE_FIELDS = (
    'id', 'create_date', 'is_automated', 'script', 'arguments', 'extra_link',
    'summary', 'requirement', 'notes', 'text', 'case_status', 'category',
    'priority', 'author', 'default_tester', 'reviewer',
)


def _td_seconds(td):
    return int(td.total_seconds()) if td is not None else None


class FirestoreTestCaseDAO:
    """
    Firestore-backed DAO for TestCase.

    filter()  — reads from Firestore, applies post-filtering in Python.
    save()    — dual-write: persists via ORM then syncs the document to Firestore.

    filter_objects() and get_by_id() are not implemented here because they
    return Django ORM objects required by the view layer.
    """

    def __init__(self):
        db = get_firestore_client()
        self._collection = db.collection(_COLLECTION)
        self._components_collection = db.collection(_COMPONENTS_COLLECTION)
        self._cc_collection = db.collection(_CC_COLLECTION)
        self._post_filterer = TestCasePostFilterer()

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _to_dict(self, case):
        result = {field: getattr(case, field) for field in _TEST_CASE_FIELDS}
        result['case_status'] = case.case_status_id
        result['category'] = case.category_id
        result['priority'] = case.priority_id
        result['author'] = case.author_id
        result['default_tester'] = case.default_tester_id
        result['reviewer'] = case.reviewer_id
        result['setup_duration'] = _td_seconds(case.setup_duration)
        result['testing_duration'] = _td_seconds(case.testing_duration)
        result['expected_duration'] = _td_seconds(
            (case.setup_duration or timedelta(0)) + (case.testing_duration or timedelta(0))
        )
        extra = TestCase.objects.filter(pk=case.pk).values(
            'case_status__name', 'category__name', 'priority__value',
            'author__username', 'default_tester__username', 'reviewer__username',
        ).first() or {}
        result.update(extra)
        return result

    def _doc_ref(self, case_id):
        return self._collection.document(str(case_id))

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def filter(self, query):
        """
        Fetch all TestCase documents from Firestore and apply criteria
        on the application side (post-filtering).
        """
        all_docs = [doc.to_dict() for doc in self._collection.stream()]
        return self._post_filterer.filter(all_docs, query)

    # ------------------------------------------------------------------
    # WRITE
    # ------------------------------------------------------------------

    def save(self, case, update_fields=None):
        """Persist a TestCase: ORM save first, then sync to Firestore."""
        if update_fields:
            case.save(update_fields=update_fields)
        else:
            case.save()

        self._doc_ref(case.pk).set(self._to_dict(case))
        return case

    def remove(self, query):
        """Delete TestCase objects matching query in ORM; remove docs from Firestore."""
        cases = list(TestCase.objects.filter(**query).values_list('pk', flat=True))
        deleted = TestCase.objects.filter(**query).delete()

        for case_id in cases:
            self._doc_ref(case_id).delete()

        return deleted

    def add_component(self, case, component_obj):
        """Link a component to a test case in ORM and Firestore."""
        case.add_component(component_obj)

        self._components_collection.document(f'{case.pk}_{component_obj.pk}').set({
            'case_id': case.pk,
            'component_id': component_obj.pk,
        })

        return model_to_dict(component_obj)

    def remove_component(self, case, component_obj):
        """Remove a component from a test case in ORM and Firestore."""
        case.remove_component(component_obj)
        self._components_collection.document(f'{case.pk}_{component_obj.pk}').delete()

    def add_notification_cc(self, case, cc_list):
        """Add emails to notification CC in ORM and Firestore."""
        case.emailing.add_cc(cc_list)

        for email in cc_list:
            self._cc_collection.document(f'{case.pk}_{email}').set({
                'case_id': case.pk,
                'email': email,
            })

    def remove_notification_cc(self, case, cc_list):
        """Remove emails from notification CC in ORM and Firestore."""
        case.emailing.remove_cc(cc_list)

        for email in cc_list:
            self._cc_collection.document(f'{case.pk}_{email}').delete()


firestore_test_case_dao = FirestoreTestCaseDAO()
