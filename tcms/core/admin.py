# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_permission_codename
from django.contrib.sites.admin import SiteAdmin
from django.contrib.sites.models import Site
from django.http import HttpResponseRedirect
from django.urls import reverse
from django_comments.models import Comment

class KiwiSiteAdmin(SiteAdmin):
    """
    Does not allow adding new or deleting sites.
    Redirects to the edit form for the default object!
    """

    def add_view(self, request, form_url="", extra_context=None):
        return HttpResponseRedirect(
            reverse("admin:sites_site_change", args=[settings.SITE_ID])
        )

    def delete_view(self, request, object_id, extra_context=None):
        return HttpResponseRedirect(
            reverse("admin:sites_site_change", args=[settings.SITE_ID])
        )


# we don't want comments to be accessible via the admin interface
admin.site.unregister(Comment)
# site admin with limited functionality
admin.site.unregister(Site)
admin.site.register(Site, KiwiSiteAdmin)

# globally disable the 'Delete selected' action
# see https://github.com/kiwitcms/Kiwi/issues/221 and
# https://docs.djangoproject.com/en/2.0/ref/contrib/admin/actions/#disabling-actions
admin.site.disable_action("delete_selected")


class SafePkAdminMixin:
    """
    Assigns a Firestore-safe PK (< 2^31) when creating new objects via admin.
    Prevents gcloudc from assigning large auto-IDs that then get filtered out
    by get_queryset() overrides.
    """

    def save_model(self, request, obj, form, change):
        if not change and obj.pk is None:
            from django.conf import settings as _s
            if getattr(_s, "USE_FIRESTORE_DAOS", False):
                from tcms.dao.firestore.utils import generate_safe_pk
                obj.pk = generate_safe_pk(obj.__class__)
        super().save_model(request, obj, form, change)


class ObjectPermissionsAdminMixin(admin.ModelAdmin):
    """
    This class should be used in conjunction with admin.ModelAdmin or
    its descendants and teaches Django to respect object-level permissions!

    The trouble with ModelAdmin is that it doesn't pass the obj argument
    to user.has_perm() and if it does (without doing an `or`) then
    django.contrib.auth.backends.ModelBackend will return False and
    cause all sort of things to fail.

    For more information see:
    https://github.com/django/django/pull/13418
    https://code.djangoproject.com/ticket/13539#comment:21
    """

    def has_change_permission(self, request, obj=None):
        opts = self.opts
        codename = get_permission_codename("change", opts)
        return (
            request.user.has_perm(f"{opts.app_label}.{codename}")
            or
            # vvv this is the added bit
            request.user.has_perm(f"{opts.app_label}.{codename}", obj=obj)
        )

    def has_delete_permission(self, request, obj=None):
        opts = self.opts
        codename = get_permission_codename("delete", opts)
        return (
            request.user.has_perm(f"{opts.app_label}.{codename}")
            or
            # vvv this is the added bit
            request.user.has_perm(f"{opts.app_label}.{codename}", obj=obj)
        )

    def has_view_permission(self, request, obj=None):
        opts = self.opts
        codename_view = get_permission_codename("view", opts)
        codename_change = get_permission_codename("change", opts)
        return (
            request.user.has_perm(f"{opts.app_label}.{codename_view}")
            or request.user.has_perm(f"{opts.app_label}.{codename_change}")
            or
            # vvv these are the added bits
            request.user.has_perm(f"{opts.app_label}.{codename_view}", obj=obj)
            or request.user.has_perm(f"{opts.app_label}.{codename_change}", obj=obj)
        )
