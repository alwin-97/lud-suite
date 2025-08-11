from django.contrib import admin
from .models import Activity

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('date', 'activity', 'other_activity', 'duration', 'learnings', 'feedback')  # Customize columns as needed
    list_filter = ('activity', 'date')  # Optional: adds filters in the sidebar
    search_fields = ('activity', 'other_activity', 'learnings','feedback')  # Optional: search bar in admin

