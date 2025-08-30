from django.contrib import admin
from .models import Activity

@admin.register(Activity)

class ActivityAdmin(admin.ModelAdmin):
    list_display = ('date', 'activity', 'other_activity', 'duration', 'learnings', 'feedback') 
    list_filter = ('activity', 'date') 
    search_fields = ('activity', 'other_activity', 'learnings','feedback') 