from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from core.models import (
    ChangeHistory,
    Chapter,
    Cohort,
    CohortActivity,
    CohortMembership,
    CustomUser,
    Location,
    MentorAssignment,
    Program,
    QuestionResponse,
    RolePermission,
    TaskSubmission,
    Term,
    TermQuestion,
    TermResource,
    TermTask,
    UserActivityReport,
)


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


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "duration_months", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "program", "is_active")
    list_filter = ("program", "is_active")
    search_fields = ("name",)


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "is_active")
    list_filter = ("location__program", "location", "is_active")
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


class TermResourceInline(admin.TabularInline):
    model = TermResource
    extra = 1


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ("name", "cohort", "sequence", "start_date", "end_date", "is_active")
    list_filter = ("is_active", "cohort__chapter")
    search_fields = ("name", "cohort__name")
    inlines = (TermResourceInline,)


@admin.register(TermResource)
class TermResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "term", "resource_type", "created_at")
    list_filter = ("resource_type", "term__cohort")
    search_fields = ("title", "term__name", "description")


@admin.register(ChangeHistory)
class ChangeHistoryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "entity_type", "entity_name", "cohort")
    list_filter = ("action", "entity_type", "created_at")
    search_fields = ("entity_name", "description", "actor__email", "actor__first_name", "actor__last_name")
    readonly_fields = ("created_at", "actor", "action", "entity_type", "entity_id", "entity_name", "cohort", "description", "details")


@admin.register(CohortActivity)
class CohortActivityAdmin(admin.ModelAdmin):
    list_display = ("title", "cohort", "term", "status", "target_audience", "start_date", "end_date")
    list_filter = ("status", "target_audience", "term__cohort")
    search_fields = ("title", "description", "cohort__name", "term__name")


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ("role", "resource", "can_create", "can_read", "can_update", "can_delete")
    list_filter = ("role", "resource")
    list_editable = ("can_create", "can_read", "can_update", "can_delete")


@admin.register(UserActivityReport)
class UserActivityReportAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "cohort", "term", "status", "hours_spent", "report_date")
    list_filter = ("status", "progress_status", "cohort")
    search_fields = ("title", "summary", "user__email", "user__first_name", "user__last_name")


class TaskSubmissionInline(admin.TabularInline):
    model = TaskSubmission
    extra = 0
    readonly_fields = ("user", "submitted_at", "updated_at")


@admin.register(TermTask)
class TermTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "term", "target_audience", "due_date", "points", "is_active")
    list_filter = ("target_audience", "is_active", "term__cohort")
    search_fields = ("title", "description", "term__name")
    inlines = (TaskSubmissionInline,)


@admin.register(TaskSubmission)
class TaskSubmissionAdmin(admin.ModelAdmin):
    list_display = ("task", "user", "status", "score", "submitted_at", "reviewed_by")
    list_filter = ("status", "task__term__cohort")
    search_fields = ("user__email", "user__first_name", "task__title")


class QuestionResponseInline(admin.TabularInline):
    model = QuestionResponse
    extra = 0
    readonly_fields = ("user", "submitted_at", "updated_at")


@admin.register(TermQuestion)
class TermQuestionAdmin(admin.ModelAdmin):
    list_display = ("title", "term", "target_audience", "is_required", "due_date", "is_active")
    list_filter = ("target_audience", "is_required", "is_active", "term__cohort")
    search_fields = ("title", "prompt", "term__name")
    inlines = (QuestionResponseInline,)


@admin.register(QuestionResponse)
class QuestionResponseAdmin(admin.ModelAdmin):
    list_display = ("question", "user", "status", "submitted_at", "reviewed_by")
    list_filter = ("status", "question__term__cohort")
    search_fields = ("user__email", "user__first_name", "question__title")


@admin.register(MentorAssignment)
class MentorAssignmentAdmin(admin.ModelAdmin):
    list_display = ("mentor", "mentee", "cohort", "is_active", "created_at", "assigned_by")
    list_filter = ("is_active", "cohort")
    search_fields = ("mentor__email", "mentor__first_name", "mentee__email", "mentee__first_name")





