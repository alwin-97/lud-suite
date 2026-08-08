from django.shortcuts import render

from core.decorators import admin_required


@admin_required
def admin_dashboard_view(request):
    return render(request, "core/admin/dashboard.html")
