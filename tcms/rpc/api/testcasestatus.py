# -*- coding: utf-8 -*-

from django.forms.models import model_to_dict
from modernrpc.core import rpc_method

from tcms.dao.firestore.firestore_test_case_status_dao import firestore_test_case_status_dao
from tcms.dao.testcases.test_case_status_dao import test_case_status_dao
from tcms.rpc.api.forms.testcase import TestCaseStatusForm
from tcms.rpc.decorators import permissions_required


@permissions_required("testcases.view_testcasestatus")
@rpc_method(name="TestCaseStatus.filter")
def filter(query):  # pylint: disable=redefined-builtin
    """
    .. function:: RPC TestCaseStatus.filter(query)

        Search and return the list of test case statuses.

        :param query: Field lookups for :class:`tcms.testcases.models.TestCaseStatus`
        :type query: dict
        :return: Serialized list of :class:`tcms.testcases.models.TestCaseStatus` objects
        :rtype: list(dict)
    """
    return firestore_test_case_status_dao.filter(query)


@permissions_required("testcases.add_testcasestatus")
@rpc_method(name="TestCaseStatus.create")
def create(values):
    """
    .. function:: RPC TestCaseStatus.create(values)

        Create a new TestCaseStatus object and store it in the database.

        :param values: Field values for :class:`tcms.testcases.models.TestCaseStatus`
        :type values: dict
        :return: Serialized :class:`tcms.testcases.models.TestCaseStatus` object
        :rtype: dict
        :raises ValueError: if input values don't validate
        :raises PermissionDenied: if missing *testcases.add_testcasestatus* permission

    .. versionadded:: 15.2
    """
    form = TestCaseStatusForm(values)

    if form.is_valid():
        status = form.save()
        test_case_status_dao.save(status)
        firestore_test_case_status_dao.save(status)
        return model_to_dict(status)

    raise ValueError(list(form.errors.items()))
