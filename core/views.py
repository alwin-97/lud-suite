from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .forms import ActivityForm
from .models import Activity

def login_view(request):
    return render(request, "core/login.html")

@login_required
def dashboard_view(request):
    if not request.user.is_authenticated:   # check here
        return redirect("account_login")
    
    return render(request, "core/dashboard.html")

@login_required
def dip_yclp_view(request):
    if not request.user.is_authenticated:   # check here
        return redirect("account_login")
    recent_activities = Activity.objects.filter(user=request.user).order_by("-date")[:6]
    return render(request, "core/dip_yclp.html", {
        "recent_activities": recent_activities
    })

def dip_mentee_view(request):
    """Dummy view for DIP - Mentee Page."""
    return HttpResponse("DIP - Mentee Page")

def profile_view(request):
    """Dummy view for Public Profile Page."""
    return HttpResponse("Public Profile Page")

def work_diary_view(request):
    """Dummy view for Work Diary Page."""
    return HttpResponse("Work Diary Page")

def repository_view(request):
    """Dummy view for Data Repository Page."""
    return HttpResponse("Data Repository Page")

def notification_view(request):
    """Dummy view for Notification Page."""
    return HttpResponse("Notification Page")

def transcript_view(request):
    """Dummy view for Transcript Page."""
    return HttpResponse("Transcript Page")

def settings_view(request):
    """Dummy view for Settings Page."""
    return HttpResponse("Settings Page")

@login_required
def new_activity(request):
    if not request.user.is_authenticated:   # check here
        return redirect("account_login")
    if request.method == 'POST':
        form = ActivityForm(request.POST, request.FILES)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.user = request.user
            activity.save()
            return redirect('my-activities')
    else:
        form = ActivityForm()
    return render(request, 'core/new_activity.html', {'form': form})



@login_required
def my_activities_view(request):
    if not request.user.is_authenticated:   # check here
        return redirect("account_login")
    activities = Activity.objects.filter(user=request.user).order_by('-date')
    return render(request, 'core/my_activities.html', {'activities': activities})