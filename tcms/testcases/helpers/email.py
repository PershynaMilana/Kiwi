# -*- coding: utf-8 -*-
from django.utils.translation import gettext_lazy as _

from tcms.core.history import history_email_for
from tcms.core.utils.mailto import mailto


def email_case_created(case):
    recipients = get_case_notification_recipients(case)
    if not recipients:
        return
    cc_list = case.emailing.get_cc_list()

    subject = _("NEW: TestCase #%(pk)d - %(summary)s") % {
        "pk": case.pk,
        "summary": case.summary,
    }

    body = (
        _(
            """Test case %(pk)d has been created.

### Basic information ###
Summary: %(summary)s

Product: %(product)s
Category: %(category)s
Priority: %(priority)s

Default tester: %(default_tester)s
Text:
%(text)s"""
        )
        % {
            "pk": case.pk,
            "summary": case.summary,
            "product": case.category.product.name,
            "category": case.category.name,
            "priority": case.priority.value,
            "default_tester": case.default_tester,
            "text": case.text,
        }
    )

    mailto(None, subject, recipients, body, cc=cc_list)


def email_case_update(case):
    recipients = get_case_notification_recipients(case)
    if not recipients:
        return
    cc_list = case.emailing.get_cc_list()
    subject, body = history_email_for(case, case.summary)
    mailto(None, subject, recipients, body, cc=cc_list)


def email_case_deletion(case):
    recipients = get_case_notification_recipients(case)
    cc_list = case.emailing.get_cc_list()
    if not recipients:
        return
    subject = _("DELETED: TestCase #%(pk)d - %(summary)s") % {
        "pk": case.pk,
        "summary": case.summary,
    }
    context = {"case": case}
    mailto("email/post_case_delete/email.txt", subject, recipients, context, cc=cc_list)


def get_case_notification_recipients(case):
    from django.contrib.auth import get_user_model
    from tcms.testruns.models import TestRun

    User = get_user_model()
    recipients = set()

    if case.emailing.auto_to_case_author and case.author.is_active:
        recipients.add(case.author.email)

    if (
        case.emailing.auto_to_case_tester
        and case.default_tester
        and case.default_tester.is_active
    ):
        recipients.add(case.default_tester.email)

    need_runs = case.emailing.auto_to_run_manager or case.emailing.auto_to_run_tester
    need_assignees = case.emailing.auto_to_execution_assignee

    if need_runs or need_assignees:
        executions = list(case.executions.values("run_id", "assignee_id"))

        if need_runs:
            run_ids = list({e["run_id"] for e in executions if e["run_id"] is not None})
            if run_ids:
                runs = list(TestRun.objects.filter(pk__in=run_ids).values("manager_id", "default_tester_id"))

                if case.emailing.auto_to_run_manager:
                    manager_ids = [r["manager_id"] for r in runs if r["manager_id"] is not None]
                    if manager_ids:
                        recipients.update(
                            User.objects.filter(pk__in=manager_ids, is_active=True).values_list("email", flat=True)
                        )

                if case.emailing.auto_to_run_tester:
                    tester_ids = [r["default_tester_id"] for r in runs if r["default_tester_id"] is not None]
                    if tester_ids:
                        recipients.update(
                            User.objects.filter(pk__in=tester_ids, is_active=True).values_list("email", flat=True)
                        )

        if need_assignees:
            assignee_ids = [e["assignee_id"] for e in executions if e["assignee_id"] is not None]
            if assignee_ids:
                recipients.update(
                    User.objects.filter(pk__in=assignee_ids, is_active=True).values_list("email", flat=True)
                )

    # don't email author of last change
    try:
        recipients.discard(getattr(case.history.latest().history_user, "email", ""))
    except Exception:
        pass
    return list(filter(None, recipients))
