"""
Management command: sync_to_firestore

Performs a one-time full sync of all existing ORM data to Firestore.
Run this after adding the Firestore DAO layer to an existing database so that
the read layer (filter() calls) returns correct results immediately.

Usage:
    python manage.py sync_to_firestore [--settings=tcms.settings.devel]
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = 'Sync all ORM data to Firestore (one-time migration).'

    def handle(self, *args, **options):
        verbosity = options.get('verbosity', 1)

        def log(msg):
            if verbosity >= 1:
                self.stdout.write(msg)

        # Import DAOs lazily so Firestore credentials are resolved at runtime.
        from tcms.bugs.models import Bug
        from tcms.dao.firestore.firestore_bug_dao import firestore_bug_dao
        from tcms.dao.firestore.firestore_bug_system_dao import firestore_bug_system_dao
        from tcms.dao.firestore.firestore_build_dao import firestore_build_dao
        from tcms.dao.firestore.firestore_category_dao import firestore_category_dao
        from tcms.dao.firestore.firestore_classification_dao import firestore_classification_dao
        from tcms.dao.firestore.firestore_component_dao import firestore_component_dao
        from tcms.dao.firestore.firestore_environment_dao import (
            firestore_environment_dao,
            firestore_environment_property_dao,
        )
        from tcms.dao.firestore.firestore_plan_type_dao import firestore_plan_type_dao
        from tcms.dao.firestore.firestore_priority_dao import firestore_priority_dao
        from tcms.dao.firestore.firestore_product_dao import firestore_product_dao
        from tcms.dao.firestore.firestore_tag_dao import firestore_tag_dao
        from tcms.dao.firestore.firestore_template_dao import firestore_template_dao
        from tcms.dao.firestore.firestore_test_case_dao import firestore_test_case_dao
        from tcms.dao.firestore.firestore_test_case_status_dao import firestore_test_case_status_dao
        from tcms.dao.firestore.firestore_test_execution_dao import firestore_test_execution_dao
        from tcms.dao.firestore.firestore_test_execution_status_dao import firestore_test_execution_status_dao
        from tcms.dao.firestore.firestore_test_plan_dao import firestore_test_plan_dao
        from tcms.dao.firestore.firestore_test_run_dao import firestore_test_run_dao
        from tcms.dao.firestore.firestore_user_dao import firestore_user_dao
        from tcms.dao.firestore.firestore_version_dao import firestore_version_dao
        from tcms.management.models import Build, Classification, Component, Priority, Product, Tag, Version
        from tcms.testcases.models import BugSystem, Category, Template, TestCase, TestCaseStatus
        from tcms.testplans.models import PlanType, TestPlan
        from tcms.testruns.models import Environment, EnvironmentProperty, TestExecution, TestExecutionStatus, TestRun

        steps = [
            ('Classifications',      Classification.objects.all(),       lambda o: firestore_classification_dao.save(o)),
            ('Products',             Product.objects.all(),               lambda o: firestore_product_dao.save(o)),
            ('Versions',             Version.objects.all(),               lambda o: firestore_version_dao.save(o)),
            ('Builds',               Build.objects.all(),                 lambda o: firestore_build_dao.save(o)),
            ('Components',           Component.objects.all(),             lambda o: firestore_component_dao.save(o)),
            ('Tags',                 Tag.objects.all(),                   lambda o: firestore_tag_dao.save(o)),
            ('Priorities',           Priority.objects.all(),              lambda o: firestore_priority_dao.save(o)),
            ('PlanTypes',            PlanType.objects.all(),              lambda o: firestore_plan_type_dao.save(o)),
            ('Templates',            Template.objects.all(),              lambda o: firestore_template_dao.save(o)),
            ('TestCaseStatuses',     TestCaseStatus.objects.all(),        lambda o: firestore_test_case_status_dao.save(o)),
            ('TestExecutionStatuses', TestExecutionStatus.objects.all(), lambda o: firestore_test_execution_status_dao.save(o)),
            ('Users',                User.objects.all(),                  lambda o: firestore_user_dao.save(o)),
            ('Categories',           Category.objects.all(),              lambda o: firestore_category_dao.save(o)),
            ('BugSystems',           BugSystem.objects.all(),             lambda o: firestore_bug_system_dao.save(o)),
            ('Environments',         Environment.objects.all(),           lambda o: firestore_environment_dao.save(o)),
            ('EnvironmentProperties', EnvironmentProperty.objects.all(), lambda o: _sync_env_prop(firestore_environment_property_dao, o)),
            ('TestPlans',            TestPlan.objects.all(),              lambda o: firestore_test_plan_dao.save(o)),
            ('TestCases',            TestCase.objects.all(),              lambda o: firestore_test_case_dao.save(o)),
            ('TestRuns',             TestRun.objects.all(),               lambda o: firestore_test_run_dao.save(o)),
            ('TestExecutions',       TestExecution.objects.all(),         lambda o: firestore_test_execution_dao.save(o)),
            ('Bugs',                 Bug.objects.all(),                   lambda o: firestore_bug_dao.save(o)),
        ]

        total_synced = 0
        for label, queryset, sync_fn in steps:
            count = 0
            for obj in queryset.iterator():
                try:
                    sync_fn(obj)
                    count += 1
                except Exception as exc:  # pylint: disable=broad-except
                    self.stderr.write(f'  ERROR syncing {label} id={obj.pk}: {exc}')
            log(f'  {label}: {count} synced')
            total_synced += count

        log(self.style.SUCCESS(f'\nDone. {total_synced} objects synced to Firestore.'))


def _sync_env_prop(dao, prop):
    """EnvironmentPropertyDAO uses get_or_create; bypass it and write directly."""
    dao._doc_ref(prop.pk).set(dao._to_dict(prop))
