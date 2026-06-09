# -*- coding: utf-8 -*-
from tcms.core.history import history_email_for
from tcms.core.utils.mailto import mailto

_CHUNK = 90


def email_plan_update(plan):
    recipients = get_plan_notification_recipients(plan)
    if not recipients:
        return
    subject, body = history_email_for(plan, plan.name)
    mailto(None, subject, recipients, body)


def get_plan_notification_recipients(plan):  # pylint: disable=invalid-name
    recipients = set()

    if plan.author and plan.author.is_active and plan.emailing.auto_to_plan_author:
        recipients.add(plan.author.email)

    if plan.emailing.auto_to_case_owner:
        try:
            case_authors = plan.cases.filter(author__is_active=True).values_list(
                "author__email", flat=True
            )
            recipients.update(case_authors)  # pylint: disable=objects-update-used
        except Exception:
            # Firestore: cross-collection join not supported — use multi-step query
            _collect_user_emails_for_plan_cases(plan, "author_id", recipients)

    if plan.emailing.auto_to_case_default_tester:
        try:
            case_testers = plan.cases.filter(default_tester__is_active=True).values_list(
                "default_tester__email", flat=True
            )
            recipients.update(case_testers)  # pylint: disable=objects-update-used
        except Exception:
            # Firestore: cross-collection join not supported — use multi-step query
            _collect_user_emails_for_plan_cases(plan, "default_tester_id", recipients)

    # don't email author of last change
    try:
        recipients.discard(getattr(plan.history.latest().history_user, "email", ""))
    except Exception:
        pass

    return list(filter(bool, recipients))


def _collect_user_emails_for_plan_cases(plan, user_id_field, recipients):
    """
    Firestore-compatible fallback: collect user emails for a FK field on
    this plan's test cases using explicit single-collection queries.

    gcloudc cannot traverse FK joins across collections
    (e.g. testcases_testcase → auth_user) in a single .values_list() call.
    We break the work into three cheap single-collection IN queries instead.
    """
    from django.contrib.auth import get_user_model
    from tcms.testcases.models import TestCase, TestCasePlan

    User = get_user_model()

    # Step 1: case IDs for this plan (junction table — single-collection query)
    case_ids = [
        cid for cid in
        TestCasePlan.objects.filter(plan_id=plan.pk).values_list("case_id", flat=True)
        if isinstance(cid, int)
    ]
    if not case_ids:
        return

    # Step 2: user IDs from test cases (chunked IN query on testcases_testcase)
    user_ids = []
    for i in range(0, len(case_ids), _CHUNK):
        user_ids.extend(
            uid for uid in
            TestCase.objects.filter(pk__in=case_ids[i:i + _CHUNK])
            .values_list(user_id_field, flat=True)
            if isinstance(uid, int)
        )
    if not user_ids:
        return

    # Step 3: emails of active users (chunked IN query on auth_user)
    for i in range(0, len(user_ids), _CHUNK):
        for email in (
            User.objects.filter(pk__in=user_ids[i:i + _CHUNK], is_active=True)
            .values_list("email", flat=True)
        ):
            recipients.add(email)
