from django.shortcuts import render, redirect ,  get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .forms import ActivityForm
from .models import Activity
from .decorators import role_required
from django.contrib import messages

from django.contrib.auth import get_user_model

from .models import CustomUser
from .forms import NotificationForm
import openpyxl
import csv
from .forms import ProfileForm
from .forms import WorkScheduleForm
from .models import CustomUser, Assignment, MentorProfile, WorkSchedule, Activity, Notification
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST


User = get_user_model()
@role_required(allowed_roles=['admin'])
def edit_user_view(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        role = request.POST.get("role")

        if not (first_name and last_name and email and phone and role):
            messages.error(request, "⚠️ All fields are required.")
            return redirect("edit_user", user_id=user.id)

        # update fields
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.username = email
        user.phone = phone
        user.role = role
        user.save()

        messages.success(request, "✅ User updated successfully.")
        return redirect("manage_user")

    return render(request, "core/edit_user.html", {"user": user})


@role_required(allowed_roles=['admin'])
def delete_user_view(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.delete()
    messages.success(request, "🗑️ User deleted successfully.")
    return redirect("manage_user")



# -------------------- Dashboards --------------------
def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")

        try:
            user = CustomUser.objects.get(email=email)
            login(request, user)  # <-- THIS sets request.user
            return redirect("role-redirect")
        except CustomUser.DoesNotExist:
            messages.error(request, "User with this email does not exist.")
            return redirect("login")
    return render(request, "core/login.html")


@role_required(allowed_roles=['admin'])
def admin_dashboard_view(request):
    total_mentors = CustomUser.objects.filter(role='mentor').count()
    total_endorsers = CustomUser.objects.filter(role='endorser').count()

    # Assigned/Unassigned Endorsers
    assigned_endorsers = CustomUser.objects.filter(role='endorser', mentors__isnull=False).distinct().count()
    unassigned_endorsers = total_endorsers - assigned_endorsers

    # Assigned/Unassigned Mentors
    assigned_mentors = CustomUser.objects.filter(role='mentor', assigned_endorsers__isnull=False).distinct().count()
    unassigned_mentors = total_mentors - assigned_mentors

    context = {
        'total_mentors': total_mentors,
        'total_endorsers': total_endorsers,
        'assigned_endorsers': assigned_endorsers,
        'unassigned_endorsers': unassigned_endorsers,
        'assigned_mentors': assigned_mentors,
        'unassigned_mentors': unassigned_mentors,
    }
    return render(request, "core/admin_dashboard.html", context)



@role_required(allowed_roles=['endorser'])
def endorser_dashboard(request):
    return render(request, 'core/endorser_dashboard.html')

@role_required(allowed_roles=['mentor'])
def dashboard_view(request):  # mentee dashboard
    return render(request, "core/dashboard.html")


# -------------------- Authentication Redirect --------------------

@login_required
def role_redirect_view(request):
    user = request.user

    if user.is_superuser or user.role == "admin":
        return redirect("admin_dashboard")
    elif user.role == "mentor":
        return redirect("dashboard")  # mentee dashboard
    elif user.role == "endorser":
        return redirect("endorser_dashboard")
    else:
        # Fallback if role not set
        return redirect("profile")



# -------------------- Core Pages (mentee-related) --------------------

@login_required
@role_required(allowed_roles=['mentor'])
def dip_yclp_view(request):
    form = ActivityForm()   # <-- ADD THIS
    recent_activities = Activity.objects.filter(user=request.user).order_by("-date")[:6]

    return render(request, "core/dip_yclp.html", {
        "form": form,
        "recent_activities": recent_activities
    })

@login_required
@csrf_exempt  # only needed if CSRF issues persist, ideally handle via headers in AJAX
def new_activity(request):
    if request.method == "GET":
        return redirect("dip_yclp") 
    if request.method == "POST":
        form = ActivityForm(request.POST, request.FILES)
        
        if form.is_valid():
            exists = Activity.objects.filter(
                user=request.user,
                date=form.cleaned_data["date"],
                activity=form.cleaned_data["activity"],
                duration=form.cleaned_data["duration"]
            ).exists()

            if exists:
                return JsonResponse({
                    "status": "error",
                    "message": "Duplicate entry detected. You already submitted this activity."
                })
            activity_obj = form.save(commit=False)
            activity_obj.user = request.user
            activity_obj.save()
            
            return JsonResponse({
                "status": "success",
                "message": "Activity submitted successfully!",
                "new_activity": {
                    "activity_name": activity_obj.other_activity if activity_obj.activity == "Others" else activity_obj.activity,
                    "date": activity_obj.date.strftime("%b %d, %Y"),
                    "duration": str(activity_obj.duration)
                }
            })
        else:
            # Send form errors back
            errors = {field: error.get_json_data() for field, error in form.errors.items()}
            return JsonResponse({
                "status": "error",
                "message": "Form validation failed. Please check the inputs.",
                "errors": errors
            })
    return JsonResponse({"status": "error", "message": "Invalid request method"})



@login_required
@role_required(allowed_roles=['mentor'])
def my_activities_view(request):
    # Fetch all activities of the logged-in mentor
    activities = Activity.objects.filter(user=request.user).order_by('-date')

    return render(request, 'core/my_activities.html', {
        'activities': activities
    })




# -------------------- Other Placeholder Pages --------------------

def dip_mentee_view(request):
    return HttpResponse("DIP - Mentee Page")
@login_required
def profile_view(request):
    return render(request, "core/profile.html", {"user": request.user})
@login_required
def profile_edit(request):
    user = request.user
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect("profile")
    else:
        form = ProfileUpdateForm(instance=user)
    return render(request, "core/profile_edit.html", {"form": form})

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

@role_required(allowed_roles=["admin"])
def manage_user_view(request):
    users = User.objects.exclude(role='admin').order_by("id")  # fetch all users
    return render(request, "core/manage_user.html", {"users": users})

User = get_user_model()
User = get_user_model()

@role_required(allowed_roles=["admin"])
def add_user_view(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        role = request.POST.get("role")

        if not all([first_name, last_name, email, phone, role]):
            messages.error(request, "⚠️ All fields are required.")
            return redirect("add_user")

        if User.objects.filter(email=email).exists():
            messages.error(request, "⚠️ User with this email already exists.")
            return redirect("add_user")
        role = request.POST.get("role")
        user = CustomUser.objects.create(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,    # Must be 'mentee', 'endorser', or 'admin'
            phone=phone
        )
        user.set_unusable_password()
        user.save()

        messages.success(request, "✅ User added successfully.")
        return redirect("manage_user")

    return render(request, "core/add_user.html")
@login_required
def manage_user(request):
    role_filter = request.GET.get('role')
    if role_filter:
        users = User.objects.filter(role__iexact=role_filter)
    else:
        users = User.objects.all()
    return render(request, 'manage-user.html', {'users': users})
# views.py
def dashboard(request):
    total_mentors = Mentor.objects.count()
    total_endorsers = Endorser.objects.count()
    unassigned_endorsers = Endorser.objects.filter(assigned_mentor__isnull=True).count()
    assigned_endorsers = total_endorsers - unassigned_endorsers

    context = {
        'total_mentors': total_mentors,
        'total_endorsers': total_endorsers,
        'assigned_endorsers': assigned_endorsers,
        'unassigned_endorsers': unassigned_endorsers,
    }
    return render(request, 'dashboard.html', context)
@role_required(allowed_roles=["admin"])
def view_user(request, user_id):
    viewed_user = get_object_or_404(CustomUser, id=user_id)
    activities = Activity.objects.filter(user=viewed_user).order_by('-date')
    return render(request, 'core/view_user.html', {
        'viewed_user': viewed_user,
        'activities': activities
    })
def export_user_activities_excel(request, user_id):
    viewed_user = get_object_or_404(CustomUser, id=user_id)
    activities = Activity.objects.filter(user=viewed_user).order_by('-date')

    # Create workbook and sheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Activities"

    # Header row
    ws.append(["Activity", "Duration", "Date", "Feedback", "Learnings", "Other Activity"])

    # Data rows
    for activity in activities:
        ws.append([
            activity.activity,
            activity.duration,
            activity.date.strftime("%Y-%m-%d") if activity.date else "",
            activity.feedback or "",
            activity.learnings or "",
            activity.other_activity or "",
        ])

    # Response with Excel file
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    filename = f"{viewed_user.username}_activities.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    wb.save(response)
    return response

@login_required
def profile_edit(request):
    user = request.user

    if request.method == 'POST':
        # Example: saving fields
        user.gender = request.POST.get('gender')
        user.date_of_birth = request.POST.get('date_of_birth') or None
        user.religion = request.POST.get('religion')
        user.phone_number = request.POST.get('phone_number')
        user.permanent_address = request.POST.get('permanent_address')
        user.institution = request.POST.get('institution')
        user.designation = request.POST.get('designation')
        profile_pic = request.FILES.get('profile_pic')
        if profile_pic:
            user.profile_pic = profile_pic
        user.save()
        if request.FILES.get('profile_pic'):
            user.profile_pic = request.FILES['profile_pic']

        user.save()
        return redirect('profile')  # redirect back to profile view

    return render(request, 'core/profile_edit.html', {'user': user})

@login_required
@role_required(allowed_roles=['aendorser'])
def endorser_work_schedule(request):
    endorser = request.user  # The logged-in endorser

    if endorser.role != 'endorser':
        messages.error(request, "You do not have permission to access this page.")
        return redirect('endorser_dashboard')

    if request.method == 'POST':
        form = WorkScheduleForm(request.POST, endorser=endorser)
        if form.is_valid():
            work_schedule = form.save(commit=False)
            work_schedule.endorser = endorser
            work_schedule.save()
            form.save_m2m()  # Save many-to-many mentors

            # (Optional) You can loop and create notifications for each mentor here
            for mentor in form.cleaned_data['mentors']:
                Notification.objects.create(
                    message=f"New work schedule: {work_schedule.role} (Due {work_schedule.due_date})",
                    target_group='mentor',
                    created_by=endorser
                 )

            messages.success(request, "Work schedule sent successfully.",extra_tags='work_schedule')
            return redirect('endorser_work_schedule')
    else:
        form = WorkScheduleForm(endorser=request.user)

    return render(request, 'core/work_schedule.html', {'form': form})

@login_required
@role_required(allowed_roles=['endorser'])
def endorser_profile(request):
    if request.user.role != 'endorser':
        return redirect('role-redirect')
    return render(request, 'core/endorser_profile.html')

@login_required
@role_required(allowed_roles=['endorser'])
def endorser_edit_profile(request):
    if request.user.role != 'endorser':
        return redirect('role-redirect')

    user = request.user

    if request.method == 'POST':
        user.gender = request.POST.get('gender', user.gender)
        user.date_of_birth = request.POST.get('date_of_birth') or user.date_of_birth
        user.religion = request.POST.get('religion', user.religion)
        user.permanent_address = request.POST.get('permanent_address', user.permanent_address)
        user.institution = request.POST.get('institution', user.institution)
        user.designation = request.POST.get('designation', user.designation)

        if 'profile_pic' in request.FILES:
            user.profile_pic = request.FILES['profile_pic']

        # NEVER change role here
        user.save()
        return redirect('endorser_profile')

    # Always pass 'user' context
    return render(request, 'core/endorser_edit_profile.html', {'user': user})
def download_user_template(request):
    # Create the HttpResponse object with CSV header
    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="user_template.csv"'},
    )

    writer = csv.writer(response)
    # Write header row
    writer.writerow(['FIRST_NAME', 'LAST_NAME', 'EMAIL', 'PHONENO', 'ROLE'])
    return response




REQUIRED_COLUMNS = ["First Name", "Last Name", "Email", "Phone Number", "Role"]
@login_required
def bulk_upload_users_view(request):
    if request.method == "POST":
        csv_file = request.FILES.get('file')
        
        # Check if file uploaded
        if not csv_file:
            messages.error(request, "⚠️ No file uploaded.")
            return redirect('manage_user')

        # Check file extension
        if not csv_file.name.endswith('.csv'):
            messages.error(request, "⚠️ Uploaded file is not a CSV.")
            return redirect('manage_user')

        # Read CSV
        try:
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
        except Exception:
            messages.error(request, "⚠️ Error reading the CSV. Ensure it is properly formatted.")
            return redirect('manage_user')

        # Strip whitespace from header keys
        reader = [{k.strip(): v for k, v in row.items()} for row in reader]

        required_fields = ['FIRST_NAME', 'LAST_NAME', 'EMAIL', 'PHONENO', 'ROLE']
        added_count = 0
        skipped_rows = []

        for i, row in enumerate(reader, start=2):  # start=2 to match CSV row numbers
            # Strip whitespace from values
            row = {k: (v or '').strip() for k, v in row.items()}

            # Check for empty required fields
            if not all(row.get(field) for field in required_fields):
                skipped_rows.append(f"Row {i}: One or more required fields are empty.")
                continue

            first_name = row['FIRST_NAME']
            last_name = row['LAST_NAME']
            email = row['EMAIL']
            phone = row['PHONENO']
            role = row['ROLE'].lower()

            # Validate role
            if role not in ['endorser', 'mentor']:
                skipped_rows.append(f"Row {i}: Invalid role '{row['ROLE']}'. Must be 'endorser' or 'mentor'.")
                continue

            # Check for duplicate email
            if CustomUser.objects.filter(email=email).exists():
                skipped_rows.append(f"Row {i}: Email '{email}' already exists.")
                continue

            # Generate unique username from first.last
            username_base = f"{first_name.lower()}.{last_name.lower()}"
            username = username_base
            counter = 1
            while CustomUser.objects.filter(username=username).exists():
                username = f"{username_base}{counter}"
                counter += 1

            # Create user
            CustomUser.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                role=role,
                password='DefaultPass123'  # Or generate a random password
            )
            added_count += 1

        # Success message
        if added_count:
            messages.success(request, f"✅ {added_count} users added successfully.")

        # Skipped rows message
        if skipped_rows:
            skipped_msg = "<br>".join(skipped_rows)
            messages.warning(request, mark_safe(f"⚠️ Some rows were skipped:<br>{skipped_msg}"))

    return redirect('manage_user')
@role_required(allowed_roles=['admin'])
def manage_assignment(request):
    all_endorsers = CustomUser.objects.filter(role='endorser')
    all_mentors = CustomUser.objects.filter(role='mentor')

    # Count how many are unassigned
    unassigned_endorsers = all_endorsers.filter(mentors__isnull=True)
    unassigned_mentors = all_mentors.exclude(assigned_endorsers__isnull=False)

    # Prepare mentor counts
    endorsers_with_counts = [
        {
            'endorser': e,
            'mentor_count': e.mentors.count(),
            'mentors': e.mentors.all()
        }
        for e in all_endorsers
    ]

    context = {
        'endorsers_with_counts': endorsers_with_counts,
        'unassigned_endorsers': unassigned_endorsers,
        'unassigned_mentors': unassigned_mentors,
        'total_endorsers': all_endorsers.count(),
        'total_mentors': all_mentors.count(),
    }
    return render(request, 'core/manage_assignment.html', context)


@csrf_exempt
@require_POST
def assign_mentors(request):
    try:
        endorser_id = request.POST.get('endorser_id')
        mentor_ids = request.POST.getlist('mentor_ids[]')

        if not endorser_id or not mentor_ids:
            return JsonResponse({'status': 'failed', 'message': 'Missing data'})

        endorser = User.objects.get(id=endorser_id)
        mentors = User.objects.filter(id__in=mentor_ids)

        # Add mentors to ManyToMany field
        endorser.mentors.add(*mentors)

        return JsonResponse({'status': 'success', 'message': 'Mentors assigned successfully'})

    except Exception as e:
        print("Assign error:", e)
        return JsonResponse({'status': 'failed', 'message': str(e)})



@csrf_exempt
def unassign_mentor(request):
    if request.method == 'POST':
        endorser_id = request.POST.get('endorser_id')
        mentor_ids = request.POST.getlist('mentor_ids[]')

        try:
            endorser = CustomUser.objects.get(id=endorser_id)
            mentors = CustomUser.objects.filter(id__in=mentor_ids)

            # ✅ Remove mentors from this endorser’s ManyToMany field
            for mentor in mentors:
                endorser.mentors.remove(mentor)

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'invalid method'}, status=405)

@csrf_exempt
def get_assigned_mentors(request):
    """Return mentors assigned to a given endorser (via M2M)"""
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

    endorser_id = request.GET.get('endorser_id')
    if not endorser_id:
        return JsonResponse({'status': 'error', 'message': 'endorser_id missing'}, status=400)

    try:
        endorser = CustomUser.objects.get(id=endorser_id)
        mentors_qs = endorser.mentors.all().values('id', 'first_name', 'last_name', 'email')

        return JsonResponse({'status': 'success', 'mentors': list(mentors_qs)})

    except CustomUser.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': f'Endorser with id={endorser_id} not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e), 'trace': traceback.format_exc()}, status=500)
def update_assigned_mentors(request):
    if request.method == 'POST':
        endorser_id = request.POST.get('endorser_id')
        mentor_ids = request.POST.getlist('mentor_ids[]')

        try:
            endorser = CustomUser.objects.get(id=endorser_id)
            endorser.mentors.set(mentor_ids)  # Replace all existing mentors
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'invalid method'}, status=405)
@login_required
def activity_log(request):
    # Use the M2M relation on CustomUser instead of Assignment model
    assigned_mentors = request.user.mentors.all()

    context = {
        'assigned_mentors': assigned_mentors
    }
    return render(request, 'core/endorser_activity_log.html', context)
@login_required
def mentor_activity_list(request, mentor_id):
    mentor = get_object_or_404(User, id=mentor_id)
    activities = Activity.objects.filter(user=mentor).order_by('-date')  # assuming `user` FK in Activity

    context = {
        'mentor': mentor,
        'activities': activities,
    }
    return render(request, 'core/activity_list.html', context)
def add_remark(request):
    if request.method == "POST":
        activity_id = request.POST.get("activity_id")
        remark = request.POST.get("remark")
        activity = Activity.objects.get(id=activity_id)
        activity.remark = remark
        activity.save()
        return JsonResponse({
            "activity_id": activity_id,
            "remark": remark,
            "status": "success"
        })
    
@login_required
def mentor_profile(request):
    user = request.user

    # Only allow mentors to access this page
    if user.role != "mentor":
        return redirect("role-redirect")

    # The mentor is simply the logged-in user
    mentor = user

    return render(request, "core/mentor_profile.html", {
        "mentor": mentor
    })
def dip_home(request):
    user = request.user
    form = ActivityForm()

    if request.method == "POST":
        form = ActivityForm(request.POST, request.FILES)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.user = request.user
            activity.save()
            return redirect("dashboard")  # or your DIP page URL

    recent_activities = Activity.objects.filter(user=user).order_by("-date")[:5]

    return render(request, "core/dip_yclp.html", {
        "form": form,
        "recent_activities": recent_activities,
    })
