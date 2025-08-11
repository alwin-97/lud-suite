from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .forms import ActivityForm
from .models import Activity



def login_view(request):
    return render(request, "core/login.html")


def dashboard_view(request):
    return render(request, "core/dashboard.html")


def dip_yclp_view(request):
    return render(request, "core/dip_yclp.html")


def dip_mentee_view(request):
    return HttpResponse("DIP - Mentee Page")


def profile_view(request):
    return HttpResponse("Public Profile Page")


def work_diary_view(request):
    return HttpResponse("Work Diary Page")


def repository_view(request):
    return HttpResponse("Data Repository Page")


def notification_view(request):
    return HttpResponse("Notification Page")


def transcript_view(request):
    return HttpResponse("Transcript Page")


def settings_view(request):
    return HttpResponse("Settings Page")

def new_activity(request):
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
    activities = Activity.objects.filter(user=request.user).order_by('-date')
    return render(request, 'core/my_activities.html', {'activities': activities})
