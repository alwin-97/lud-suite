from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

def login_view(request):
    return render(request, 'login.html')
def dashboard_view(request):
    return render(request, 'dashboard.html')
def dip_yclp_view(request):
    return HttpResponse("DIP - YCLP Page")

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