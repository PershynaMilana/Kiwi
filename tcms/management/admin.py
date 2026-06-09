# -*- coding: utf-8 -*-

from django import forms
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from tcms.core.history import ReadOnlyHistoryAdmin
from tcms.management.models import (
    Build,
    Classification,
    Component,
    Priority,
    Product,
    Tag,
    Version,
)


_SAFE_PK = 2**31


def _assign_safe_pk(obj):
    """Assign a safe PK (< 2^31) when running on Firestore to avoid large auto-generated IDs."""
    from django.conf import settings
    if getattr(settings, "USE_FIRESTORE_DAOS", False):
        from tcms.dao.firestore.utils import generate_safe_pk
        obj.pk = generate_safe_pk(obj.__class__)


class SafePkAdminMixin:
    """Mixin that assigns a safe PK on new object creation in Firestore mode."""

    def save_model(self, request, obj, form, change):
        if not change and obj.pk is None:
            _assign_safe_pk(obj)
        super().save_model(request, obj, form, change)


class ClassificationAdmin(SafePkAdminMixin, admin.ModelAdmin):
    search_fields = ("name", "id")
    list_display = ("id", "name")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(pk__lt=_SAFE_PK)


class ProductsAdmin(SafePkAdminMixin, ReadOnlyHistoryAdmin):
    def get_readonly_fields(self, request, obj=None):
        return ()

    search_fields = ("name", "id")
    view_on_site = False
    list_display = ("id", "name", "classification", "description")
    list_filter = ("id", "name", "classification")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(pk__lt=_SAFE_PK)


class PriorityAdmin(SafePkAdminMixin, admin.ModelAdmin):
    search_fields = ("value", "id")
    list_display = ("id", "value", "is_active")
    list_filter = ("is_active",)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(pk__lt=_SAFE_PK)


class ComponentAdmin(SafePkAdminMixin, admin.ModelAdmin):
    search_fields = ("name", "id")
    list_display = ("id", "name", "product", "initial_owner", "description")
    list_filter = ("product",)

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .filter(pk__lt=_SAFE_PK)
            .select_related("product", "initial_owner")
        )


class VersionAdmin(SafePkAdminMixin, ReadOnlyHistoryAdmin):
    def get_readonly_fields(self, request, obj=None):
        return ()

    search_fields = ("value", "id")
    view_on_site = False
    list_display = ("id", "product", "value")
    list_filter = ("product",)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(pk__lt=_SAFE_PK)


class BuildAdminForm(forms.ModelForm):
    class Meta:
        model = Build
        fields = "__all__"

    class Media:
        js = [
            "js/bundle.js",
        ]

    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        empty_label="---------",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # POST request for add|change view
        if args:
            post = args[0]
            self.populate(post.get("product", -1))
        # GET request for change view
        elif self.instance.pk:
            self.fields["product"].initial = self.instance.version.product_id
            self.populate(self.instance.version.product_id)
        # GET request for add view
        else:
            self.populate(-1)

    def populate(self, product_id):
        if product_id:
            self.fields["version"].queryset = Version.objects.filter(
                product_id=product_id
            )
        else:
            self.fields["version"].queryset = Version.objects.all()


class BuildAdmin(SafePkAdminMixin, ReadOnlyHistoryAdmin):
    def get_readonly_fields(self, request, obj=None):
        return ()

    search_fields = ("name", "id")
    view_on_site = False
    list_display = ("id", "name", "version", "product_name", "is_active")
    list_filter = ("version__product", "version", "is_active")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(pk__lt=_SAFE_PK)

    form = BuildAdminForm
    fieldsets = [
        (
            "",
            {
                "fields": ("product", "version", "name", "is_active"),
            },
        ),
    ]

    def product_name(self, obj):  # pylint: disable=no-self-use
        if obj.version is None:
            return None
        return obj.version.product

    product_name.short_description = _("Product")


class AttachmentAdmin(admin.ModelAdmin):
    search_fields = ("file_name", "attachment_id")
    list_display = (
        "attachment_id",
        "file_name",
        "submitter",
        "description",
        "create_date",
        "mime_type",
    )


class TagAdmin(SafePkAdminMixin, admin.ModelAdmin):
    search_fields = ("name", "id")
    list_display = ("pk", "name")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(pk__lt=_SAFE_PK)


admin.site.register(Classification, ClassificationAdmin)
admin.site.register(Product, ProductsAdmin)
admin.site.register(Priority, PriorityAdmin)
admin.site.register(Component, ComponentAdmin)
admin.site.register(Version, VersionAdmin)
admin.site.register(Build, BuildAdmin)
admin.site.register(Tag, TagAdmin)
