from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponseForbidden
from django.test import TestCase, modify_settings

from tcms.tests import LoggedInTestCase

User = get_user_model()


@modify_settings(
    AUTHENTICATION_BACKENDS={"append": "tcms.kiwi_auth.backends.AnonymousViewBackend"}
)
class TestAnonymousViewBackend(TestCase):
    """Test AnonymousViewBackend.has_perm method"""

    def test_has_perm(self):
        user, _ = User.objects.get_or_create(username=settings.ANONYMOUS_USER_NAME)
        self.assertTrue(user.has_perm("testruns.view_testrun"))

    def test_not_has_perm(self):
        user, _ = User.objects.get_or_create(username=settings.ANONYMOUS_USER_NAME)
        self.assertFalse(user.has_perm("testruns.add_testrun"))

    def test_is_anonymous_has_perm(self):
        user = AnonymousUser()
        self.assertTrue(user.has_perm("testruns.view_testrun"))

    def test_is_anonymous_not_has_perm(self):
        user = AnonymousUser()
        self.assertFalse(user.has_perm("testruns.add_testrun"))


@modify_settings(
    AUTHENTICATION_BACKENDS={"append": "tcms.kiwi_auth.backends.AnonymousViewBackend"}
)
class TestUserAdmin(LoggedInTestCase):
    def test_regular_user_cant_view_list_of_all_users(self):
        response = self.client.get("/admin/auth/user/")
        self.assertIsInstance(response, HttpResponseForbidden)
        self.assertEqual(HTTPStatus.FORBIDDEN, response.status_code)
