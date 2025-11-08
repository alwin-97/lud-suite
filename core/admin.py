from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Activity


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


# ✅ Register only once
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Activity, ActivityAdmin)
