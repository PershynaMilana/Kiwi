# -*- coding: utf-8 -*-
from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from tcms.core.forms.fields import UserField
from tcms.management.models import Build, Product, Version
from tcms.rpc.api.forms import DateTimeField
from tcms.testcases.models import TestCase, TestCaseStatus
from tcms.testruns.models import Environment, TestRun

User = get_user_model()  # pylint: disable=invalid-name


class NewRunForm(forms.ModelForm):
    class Meta:
        model = TestRun
        exclude = ("tag", "cc")  # pylint: disable=modelform-uses-exclude

    manager = UserField()
    default_tester = UserField(required=False)
    start_date = DateTimeField(required=False)
    stop_date = DateTimeField(required=False)
    planned_start = DateTimeField(required=False)
    planned_stop = DateTimeField(required=False)

    case = forms.ModelMultipleChoiceField(
        queryset=TestCase.objects.none(),
        required=False,
    )

    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        required=False,
    )

    matrix_type = forms.ChoiceField(
        choices=(
            ("full", _("Full")),
            ("pairwise", _("Pairwise")),
        ),
        required=False,
    )

    environment = forms.ModelMultipleChoiceField(
        queryset=Environment.objects.all(),
        required=False,
    )

    def populate(self, plan_id):
        if plan_id:
            # plan is ModelChoiceField which contains all the plans
            # as we need only the plan for current run we filter the queryset
            self.fields["plan"].queryset = self.fields["plan"].queryset.filter(
                pk=plan_id
            )
            plan = self.fields["plan"].queryset.first()
            self.fields["product"].queryset = Product.objects.filter(pk=plan.product_id)
            # Python post-filter avoids needing (version_id, is_active, name) composite index
            active_build_ids = [
                b.pk for b in Build.objects.filter(version_id=plan.product_version_id)
                if b.is_active
            ]
            self.fields["build"].queryset = Build.objects.filter(pk__in=active_build_ids)
        else:
            # these are dynamically filtered via JavaScript
            self.fields["plan"].queryset = self.fields["plan"].queryset.none()
            self.fields["build"].queryset = Build.objects.none()

        # Decompose cross-collection filter: TestCase → TestCaseStatus (no JOINs in Firestore)
        confirmed_status_ids = list(
            TestCaseStatus.objects.filter(is_confirmed=True).values_list("pk", flat=True)
        )
        self.fields["case"].queryset = TestCase.objects.filter(
            case_status_id__in=confirmed_status_ids
        )


class SearchRunForm(forms.ModelForm):
    class Meta:
        model = TestRun
        fields = "__all__"

    # overriden widget
    manager = UserField()
    default_tester = UserField()

    # extra fields
    product = forms.ModelChoiceField(queryset=Product.objects.all(), required=False)
    version = forms.ModelChoiceField(queryset=Version.objects.none(), required=False)
    running = forms.IntegerField(required=False)

    def populate(self, product_id=None):
        if product_id:
            self.fields["version"].queryset = Version.objects.filter(product_id=product_id)
            # Decompose two-hop FK Build→Version→Product (no cross-join support in Firestore)
            version_ids = list(
                Version.objects.filter(product_id=product_id).values_list("pk", flat=True)
            )
            self.fields["build"].queryset = Build.objects.filter(version_id__in=version_ids)
