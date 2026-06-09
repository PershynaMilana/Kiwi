# -*- coding: utf-8 -*-

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin, UserAdmin, sensitive_post_parameters_m
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _

from tcms.utils import user as user_utils

User = get_user_model()  # pylint: disable=invalid-name


def _modifying_myself(request, object_id):
    return request.user.pk == int(object_id)


def _assign_safe_pk(obj):
    """Assign a safe PK (< 2^31) when running on Firestore."""
    from django.conf import settings
    if getattr(settings, "USE_FIRESTORE_DAOS", False):
        from tcms.dao.firestore.utils import generate_safe_pk
        obj.pk = generate_safe_pk(obj.__class__)


def _set_m2m_via_junction(ThroughModel, item_field, group_field, new_items, group_pk):
    """
    Replace all junction-table rows for a given group without reading back the
    current set (which would generate a cross-join query in Firestore).

    Deletes existing rows, then bulk-creates new ones.
    """
    ThroughModel.objects.filter(**{group_field: group_pk}).delete()
    ThroughModel.objects.bulk_create([
        ThroughModel(**{group_field: group_pk, item_field: item.pk})
        for item in new_items
    ])


class GroupAdminForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ["name", "permissions"]

    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=FilteredSelectMultiple("users", False),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["users"].label = _("Users")
        if self.instance.pk:
            try:
                # Avoid M2M cross-join: query junction table directly, then filter by pk__in.
                user_ids = list(
                    User.groups.through.objects
                    .filter(group_id=self.instance.pk)
                    .values_list("user_id", flat=True)
                )
                self.fields["users"].initial = User.objects.filter(pk__in=user_ids)
            except Exception:
                self.fields["users"].initial = []

            try:
                # Same fix for permissions M2M — avoid cross-join via junction table.
                perm_ids = list(
                    Group.permissions.through.objects
                    .filter(group_id=self.instance.pk)
                    .values_list("permission_id", flat=True)
                )
                self.fields["permissions"].initial = Permission.objects.filter(pk__in=perm_ids)
            except Exception:
                self.fields["permissions"].initial = []

    def save(self, commit=True):
        # Use commit=False to prevent ModelForm._save_m2m() from calling
        # group.permissions.set() / user_set.set() — both read back current
        # members via cross-join queries that gcloudc doesn't support.
        instance = super().save(commit=False)
        if instance.pk is None:
            _assign_safe_pk(instance)
        instance.save()

        # Replace M2M sets via junction table (delete + bulk_create) to avoid
        # cross-join reads in Firestore.
        _set_m2m_via_junction(
            User.groups.through, "user_id", "group_id",
            self.cleaned_data["users"], instance.pk,
        )
        _set_m2m_via_junction(
            Group.permissions.through, "permission_id", "group_id",
            self.cleaned_data["permissions"], instance.pk,
        )

        # commit=False causes Django to set self.save_m2m = self._save_m2m so
        # the admin's save_related() can call it later.  We've already handled
        # M2M above, so replace it with a no-op to prevent a second (broken)
        # cross-join attempt.
        self.save_m2m = lambda: None

        return instance


class KiwiUserAdmin(UserAdmin):
    actions = ["deactivate_selected"]
    list_display = UserAdmin.list_display + (
        "is_active",
        "is_superuser",
        "date_joined",
        "last_login",
    )
    ordering = ["-pk"]  # same as -date_joined

    def get_queryset(self, request):
        # Exclude users with Firestore auto-generated large PKs (data corruption).
        return super().get_queryset(request).filter(pk__lt=2**31)

    def save_model(self, request, obj, form, change):
        if not change and obj.pk is None:
            _assign_safe_pk(obj)
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        # Handle User M2M (groups, user_permissions) via junction tables to
        # avoid cross-join reads that gcloudc doesn't support.
        if "groups" in form.cleaned_data:
            _set_m2m_via_junction(
                User.groups.through, "group_id", "user_id",
                form.cleaned_data["groups"], form.instance.pk,
            )
        if "user_permissions" in form.cleaned_data:
            _set_m2m_via_junction(
                User.user_permissions.through, "permission_id", "user_id",
                form.cleaned_data["user_permissions"], form.instance.pk,
            )
        form.save_m2m = lambda: None  # already handled above; prevent cross-join
        super().save_related(request, form, formsets, change)

    @admin.action(
        permissions=["change"],
        description=_("Deactivate selected accounts"),
    )
    def deactivate_selected(self, request, queryset):
        for user in queryset:
            user_utils.deactivate(user)
            self.message_user(
                request,
                _("Account '%s' was deactivated") % user,
                messages.SUCCESS,
            )

    def response_change(self, request, obj):
        if "_deactivate" in request.POST:
            self.deactivate_selected(request, [obj])
            return HttpResponseRedirect(reverse("admin:auth_user_changelist"))

        return super().response_change(request, obj)

    def has_view_permission(self, request, obj=None):
        return _modifying_myself(
            request, getattr(obj, "pk", 0)
        ) or super().has_view_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return _modifying_myself(
            request, getattr(obj, "pk", 0)
        ) or super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return _modifying_myself(
            request, getattr(obj, "pk", 0)
        ) or super().has_delete_permission(request, obj)

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def render_change_form(
        self, request, context, add=False, change=False, form_url="", obj=None
    ):
        if obj:
            if not context["adminform"].form._meta.help_texts:
                context["adminform"].form._meta.help_texts = {}

            label = _("Reset email address")
            url = reverse_lazy("reset-user-email", args=[obj.pk])
            context["adminform"].form._meta.help_texts[
                "email"
            ] = f"<a href='{url}'>{label}</a>"

        if not self.has_change_permission(request, obj):
            context.update(
                {
                    "show_save": False,
                    "show_save_and_continue": False,
                }
            )
        context.update(
            {
                "show_save_and_add_another": self.has_add_permission(request),
            }
        )
        return super().render_change_form(
            request, context, add=add, change=change, form_url=form_url, obj=obj
        )

    def get_readonly_fields(self, request, obj=None):
        # adding new user
        if not obj:
            return super().get_readonly_fields(request, obj)

        readonly_fields = [
            "username",
            "last_login",
            "date_joined",
            "email",
        ]

        # only other superusers can set the is_superuser flag
        if not request.user.is_superuser:
            readonly_fields.append("is_superuser")

        # if you have explicit change_user permission you can modify these fields
        # however users are not able to give themselves elevated permissions
        if not self.has_change_permission(request, None):
            readonly_fields.extend(
                [
                    "is_staff",
                    "is_active",
                    "groups",
                    "user_permissions",
                ]
            )

            # lastly users can't modify others unless they have the expolicit permission
            if not _modifying_myself(request, obj.pk):
                readonly_fields.extend(["first_name", "last_name", "email"])

        return readonly_fields

    def get_fieldsets(self, request, obj=None):
        # adding new account b/c we have permissions
        if not obj and self.has_add_permission(request):
            return super().get_fieldsets(request, obj)

        first_fieldset_fields = ("username",)
        if obj and _modifying_myself(request, obj.pk):
            first_fieldset_fields += ("password",)

        remaining_fieldsets = (
            (_("Personal info"), {"fields": ("first_name", "last_name", "email")}),
            (
                _("Permissions"),
                {
                    "fields": (
                        "is_active",
                        "is_staff",
                        "is_superuser",
                        "groups",
                        "user_permissions",
                    )
                },
            ),
        )

        if request.user.is_superuser:
            field_sets = super().get_fieldsets(request, obj)
            if field_sets[0][0] is None and "password" in field_sets[0][1]["fields"]:
                remaining_fieldsets = field_sets[1:]

        return ((None, {"fields": first_fieldset_fields}),) + remaining_fieldsets

    @sensitive_post_parameters_m
    def user_change_password(
        self, request, id, form_url=""
    ):  # pylint: disable=redefined-builtin
        if _modifying_myself(request, id):
            return HttpResponseRedirect(reverse("admin:password_change"))

        raise PermissionDenied

    @admin.options.csrf_protect_m
    def delete_view(self, request, object_id, extra_context=None):
        user = User.objects.get(pk=object_id)
        # check whether the last superuser is being deleted
        if user.is_superuser and User.objects.filter(is_superuser=True).count() == 1:
            messages.add_message(
                request,
                messages.ERROR,
                _("This is the last superuser, it cannot be deleted!"),
            )
            return HttpResponseRedirect(
                reverse("admin:auth_user_change", args=[user.pk])
            )

        if not _modifying_myself(request, object_id):
            return super().delete_view(request, object_id, extra_context)

        # allow deletion of the user own account
        permission = Permission.objects.get(
            content_type__app_label="auth", codename="delete_user"
        )
        try:
            request.user.user_permissions.add(permission)
            return super().delete_view(request, object_id, extra_context)
        finally:
            request.user.user_permissions.remove(permission)

    def response_delete(self, request, obj_display, obj_id):
        result = super().response_delete(request, obj_display, obj_id)

        if not _modifying_myself(request, obj_id):
            return result

        # user doesn't exist anymore so go to the login page
        return HttpResponseRedirect(reverse("tcms-login"))

    def delete_model(self, request, obj):
        user_utils.delete_user(obj)


class KiwiGroupAdmin(GroupAdmin):
    form = GroupAdminForm

    def get_queryset(self, request):
        # Exclude groups with Firestore auto-generated large PKs (data corruption).
        # Safe PKs are in [1, 2^31-1]; corrupted ones exceed 2^53.
        return super().get_queryset(request).filter(pk__lt=2**31)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.name in ["Tester", "Administrator"]:
            return False
        return super().has_delete_permission(request, obj)

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj=obj)
        name_index = fields.index("name")

        # make sure Name is always the first field
        if name_index > 0:
            del fields[name_index]
            fields.insert(0, "name")

        return fields

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj and obj.name in ["Tester", "Administrator"]:
            readonly_fields += ("name",)

        return readonly_fields


# user admin extended functionality
admin.site.unregister(User)
admin.site.register(User, KiwiUserAdmin)
admin.site.unregister(Group)
admin.site.register(Group, KiwiGroupAdmin)
