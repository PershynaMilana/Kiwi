"""
Custom Django test runner that clears all Firestore collections before
the test suite runs, preventing stale data from prior test runs from
causing assertion failures.

Usage (in settings or on the command line):
    python manage.py test --testrunner=tcms.dao.firestore.test_runner.FirestoreDiscoverRunner ...
"""

from django.test.runner import DiscoverRunner

_ALL_COLLECTIONS = [
    'bugs',
    'bug_systems',
    'builds',
    'categories',
    'classifications',
    'components',
    'environments',
    'environment_properties',
    'plan_types',
    'priorities',
    'products',
    'tags',
    'templates',
    'test_case_notification_cc',
    'test_case_components',
    'test_case_statuses',
    'test_cases',
    'test_execution_statuses',
    'test_executions',
    'test_plan_cases',
    'test_plans',
    'test_run_cases',
    'test_run_cc',
    'test_runs',
    'users',
    'versions',
]


def _delete_collection(col_ref, batch_size=100):
    docs = col_ref.list_documents(page_size=batch_size)
    deleted = 0
    for doc in docs:
        doc.delete()
        deleted += 1
    return deleted


class FirestoreDiscoverRunner(DiscoverRunner):
    """DiscoverRunner that wipes all Firestore test collections before running."""

    def setup_databases(self, **kwargs):
        result = super().setup_databases(**kwargs)
        self._clear_firestore()
        return result

    def _clear_firestore(self):
        try:
            from tcms.dao.firestore.client import get_firestore_client
            db = get_firestore_client()
            for name in _ALL_COLLECTIONS:
                _delete_collection(db.collection(name))
            if self.verbosity >= 1:
                print(f"Firestore: cleared {len(_ALL_COLLECTIONS)} collections.")
        except Exception as exc:  # pylint: disable=broad-except
            print(f"Warning: could not clear Firestore collections: {exc}")
