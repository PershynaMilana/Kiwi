"""
PropertyDAO wraps property CRUD for TestCase, TestRun, and TestExecution.

Each model has its own Property model:
  - tcms.testcases.models.Property  (FK: case)
  - tcms.testruns.models.Property   (FK: run)
  - tcms.testruns.models.TestExecutionProperty  (FK: execution)

The DAO is parameterized per model type via static factory methods.
"""
from django.forms.models import model_to_dict


class PropertyDAO:
    def __init__(self, model_class, fk_field, label):
        """
        :param model_class: The Django model class for properties (e.g. testcases.Property)
        :param fk_field: The FK field name on the property model (e.g. "case_id", "run_id")
        :param label: Human-readable label for logging (e.g. "TestCaseProperty")
        """
        self._model = model_class
        self._fk_field = fk_field
        self._label = label

    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def filter(self, query, value_fields, order_by):
        """
        Return serialized property records matching query.
        value_fields: tuple of field names to include in .values()
        order_by: tuple of order-by fields
        """
        return list(
            self._model.objects.filter(**query)
            .values(*value_fields)
            .order_by(*order_by)
            .distinct()
        )

    # ------------------------------------------------------------------
    # WRITE operations
    # ------------------------------------------------------------------

    def get_or_create(self, obj_id, name, value):
        """
        Create a property if it doesn't exist (duplicates skipped).
        Returns serialized property dict.
        """
        kwargs = {self._fk_field: obj_id, "name": name, "value": value}
        prop, created = self._model.objects.get_or_create(**kwargs)
        return model_to_dict(prop)

    def remove(self, query):
        """
        Delete property records matching query.
        """
        self._model.objects.filter(**query).delete()


# Per-model singleton instances
def _make_testcase_property_dao():
    from tcms.testcases.models import Property
    return PropertyDAO(Property, "case_id", "TestCasePropertyDAO")


def _make_testrun_property_dao():
    from tcms.testruns.models import Property
    return PropertyDAO(Property, "run_id", "TestRunPropertyDAO")


def _make_testexecution_property_dao():
    from tcms.testruns.models import TestExecutionProperty
    return PropertyDAO(TestExecutionProperty, "execution_id", "TestExecutionPropertyDAO")


testcase_property_dao = _make_testcase_property_dao()
testrun_property_dao = _make_testrun_property_dao()
testexecution_property_dao = _make_testexecution_property_dao()


from django.conf import settings as _settings  # noqa: E402
if getattr(_settings, 'USE_FIRESTORE_DAOS', False):
    from tcms.dao.firestore.shared.property_dao import (  # noqa: F401, F811
        testcase_property_dao,
        testrun_property_dao,
        testexecution_property_dao,
    )
