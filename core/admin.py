from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser,
    Activity,
    School,
    Mentee,
    MentorMenteeAssignment,
    SessionType,
    RatingDomain,
    MenteeAssessment,
    AssessmentRating,
    StatusConfig,
    TemplateConfig,
    ObjectiveItem,
    YearPlanItem,
    DomainIndicator,
    RatingScaleDefinition,
    MoodCategory,
    ReferenceContent,
)


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("username", "email", "role", "is_staff", "is_superuser")
    fieldsets = UserAdmin.fieldsets + (
        (None, {"fields": ("role",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {"fields": ("role",)}),
    )


class ActivityAdmin(admin.ModelAdmin):
    list_display = ("date", "activity", "other_activity", "duration", "learnings", "feedback")
    list_filter = ("activity", "date")
    search_fields = ("activity", "other_activity", "learnings", "feedback")


class SchoolAdmin(admin.ModelAdmin):
    search_fields = ("name",)


class MenteeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "grade", "school", "current_year", "assigned_mentor", "is_active")
    list_filter = ("current_year", "is_active", "school")
    search_fields = ("full_name",)


class SessionTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


class MentorMenteeAssignmentAdmin(admin.ModelAdmin):
    list_display = ("mentor", "mentee", "start_date", "end_date", "is_active")
    list_filter = ("is_active", "start_date")
    search_fields = ("mentor__username", "mentor__email", "mentee__full_name")


class StatusConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "ordering", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


class TemplateConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "scope", "year", "is_active")
    list_filter = ("scope", "year", "is_active")
    search_fields = ("name",)


class RatingDomainAdmin(admin.ModelAdmin):
    list_display = ("name", "year", "source", "sort_order", "is_active")
    list_filter = ("year", "source", "is_active")
    search_fields = ("name",)
    ordering = ("year", "sort_order", "name")


class RatingScaleDefinitionAdmin(admin.ModelAdmin):
    list_display = ("domain", "score")
    list_filter = ("domain__year",)
    search_fields = ("domain__name", "description")


class DomainIndicatorAdmin(admin.ModelAdmin):
    list_display = ("domain", "sort_order")
    list_filter = ("domain__year",)
    search_fields = ("domain__name", "description")


class MoodCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order")
    search_fields = ("name",)


class ReferenceContentAdmin(admin.ModelAdmin):
    list_display = ("section", "title", "sort_order")
    list_filter = ("section",)
    search_fields = ("title", "content")


class AssessmentRatingInline(admin.TabularInline):
    model = AssessmentRating
    extra = 0


class MenteeAssessmentAdmin(admin.ModelAdmin):
    list_display = ("mentee", "mentor", "year", "date", "session_type", "average_score_display")
    list_filter = ("year", "session_type", "date")
    search_fields = ("mentee__full_name", "mentor__username", "mentor__email")
    inlines = [AssessmentRatingInline]

    def average_score_display(self, obj):
        return obj.average_score()

    average_score_display.short_description = "Average"


class ObjectiveItemAdmin(admin.ModelAdmin):
    list_display = ("mentee", "objective_title", "status", "progress_percent", "updated_at")
    list_filter = ("status",)
    search_fields = ("mentee__full_name", "objective_title", "objective_text")


class YearPlanItemAdmin(admin.ModelAdmin):
    list_display = ("mentee", "year", "milestone", "status", "updated_at")
    list_filter = ("year", "status")
    search_fields = ("mentee__full_name", "milestone")


# Register only once
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Activity, ActivityAdmin)
admin.site.register(School, SchoolAdmin)
admin.site.register(Mentee, MenteeAdmin)
admin.site.register(MentorMenteeAssignment, MentorMenteeAssignmentAdmin)
admin.site.register(SessionType, SessionTypeAdmin)
admin.site.register(StatusConfig, StatusConfigAdmin)
admin.site.register(TemplateConfig, TemplateConfigAdmin)
admin.site.register(RatingDomain, RatingDomainAdmin)
admin.site.register(DomainIndicator, DomainIndicatorAdmin)
admin.site.register(RatingScaleDefinition, RatingScaleDefinitionAdmin)
admin.site.register(MoodCategory, MoodCategoryAdmin)
admin.site.register(ReferenceContent, ReferenceContentAdmin)
admin.site.register(MenteeAssessment, MenteeAssessmentAdmin)
admin.site.register(ObjectiveItem, ObjectiveItemAdmin)
admin.site.register(YearPlanItem, YearPlanItemAdmin)
