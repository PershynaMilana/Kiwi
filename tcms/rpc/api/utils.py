# Copyright (c) 2019-2020 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 2.0: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html

from django.utils.module_loading import import_string

from tcms.dao.testcases.bug_system_dao import bug_system_dao


def tracker_from_url(url, request):
    """
    Return the IssueTrackerType object for the system
    where ``base_url`` is part of ``url``. Usually we pass
    URLs to pre-existing defects to this method.
    """
    for bug_system in bug_system_dao.filter_objects({}):
        if bug_system.base_url and url.startswith(bug_system.base_url):
            return import_string(bug_system.tracker_type)(bug_system, request)

    return None
