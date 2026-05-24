# -*- coding: utf-8 -*-

from django.forms.models import model_to_dict
from modernrpc.core import rpc_method

from tcms.dao.firestore.firestore_environment_dao import (
    firestore_environment_dao,
    firestore_environment_property_dao,
)
from tcms.dao.testruns.environment_dao import environment_dao, environment_property_dao
from tcms.rpc.api.forms.testrun import EnvironmentForm
from tcms.rpc.decorators import permissions_required


@permissions_required("testruns.view_environmentproperty")
@rpc_method(name="Environment.properties")
def properties(query=None):
    """
    .. function:: Environment.properties(query)

        Return all properties for the specified environment(s).

        :param query: Field lookups for :class:`tcms.testruns.models.EnvironmentProperty`
        :type query: dict
        :return: Serialized list of :class:`tcms.testruns.models.EnvironmentProperty` objects.
        :rtype: list(dict)
        :raises PermissionDenied: if missing *testruns.view_environmentproperty* permission
    """
    if query is None:
        query = {}

    return firestore_environment_property_dao.filter(query)


@permissions_required("testruns.delete_environmentproperty")
@rpc_method(name="Environment.remove_property")
def remove_property(query):
    """
    .. function:: Environment.remove_property(query)

        Remove selected properties.

        :param query: Field lookups for :class:`tcms.testruns.models.EnvironmentProperty`
        :type query: dict
        :raises PermissionDenied: if missing *testruns.delete_environmentproperty* permission
    """
    firestore_environment_property_dao.remove(query)


@permissions_required("testruns.add_environmentproperty")
@rpc_method(name="Environment.add_property")
def add_property(environment_id, name, value):
    """
    .. function:: Environment.add_property(environment_id, name, value)

        Add property to environment! Duplicates are skipped without errors.

        :param environment_id: Primary key for :class:`tcms.testruns.models.Environment`
        :type environment_id: int
        :param name: Name of the property
        :type name: str
        :param value: Value of the property
        :type value: str
        :return: Serialized :class:`tcms.testruns.models.EnvironmentProperty` object.
        :rtype: dict
        :raises PermissionDenied: if missing *testruns.add_environmentproperty* permission
    """
    prop, _ = firestore_environment_property_dao.get_or_create(environment_id, name, value)
    return model_to_dict(prop)


@permissions_required("testruns.view_environment")
@rpc_method(name="Environment.filter")
def filter(query=None):  # pylint: disable=redefined-builtin
    """
    .. function:: Environment.filter(query)

        Return environment for the specified query.

        :param query: Field lookups for :class:`tcms.testruns.models.Environment`
        :type query: dict
        :return: Serialized list of :class:`tcms.testruns.models.Environment` objects.
        :rtype: list(dict)
        :raises PermissionDenied: if missing *testruns.view_environment* permission
    """
    if query is None:
        query = {}

    return firestore_environment_dao.filter(query)


@permissions_required("testruns.add_environment")
@rpc_method(name="Environment.create")
def create(values):
    """
    .. function:: RPC Environment.create(values)

        Create a new environment object and store it in the database.

        :param values: Field values for :class:`tcms.testruns.models.Environment`
        :type values: dict
        :return: Serialized :class:`tcms.testruns.models.Environment` object
        :rtype: dict
        :raises ValueError: if input values don't validate
        :raises PermissionDenied: if missing *testruns.add_environment* permission
    """
    form = EnvironmentForm(values)
    if form.is_valid():
        environment = form.save()
        environment_dao.save(environment)
        firestore_environment_dao.save(environment)
        return model_to_dict(environment)

    raise ValueError(list(form.errors.items()))
