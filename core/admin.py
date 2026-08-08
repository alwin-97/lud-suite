from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from core.models import Chapter, Cohort, CohortMembership, CustomUser, Location


class CohortMembershipInline(admin.TabularInline):
    model = CohortMembership
    extra = 0


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "role",
        "is_active",
        "is_superuser",
    )
    list_filter = ("role", "is_active", "is_superuser")
    search_fields = ("username", "email", "first_name", "last_name")
    inlines = (CohortMembershipInline,)

    fieldsets = UserAdmin.fieldsets + (
        ("Platform access", {"fields": ("role",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Platform access", {"fields": ("email", "role")}),
    )


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "is_active")
    list_filter = ("location", "is_active")
    search_fields = ("name", "location__name")


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ("name", "chapter", "start_date", "end_date", "is_active")
    list_filter = ("chapter", "is_active")
    search_fields = ("name", "chapter__name", "chapter__location__name")


@admin.register(CohortMembership)
class CohortMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "cohort", "role", "is_active")
    list_filter = ("role", "is_active", "cohort__chapter")
    search_fields = ("user__email", "user__first_name", "user__last_name")
