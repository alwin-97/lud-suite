from django.contrib import messages
from django.db.models import Count, Prefetch, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.decorators import admin_required
from core.forms import ChapterForm, CohortForm, LocationForm, PlatformUserForm
from core.models import Chapter, Cohort, CohortMembership, CustomUser, Location


@admin_required
def admin_dashboard_view(request):
    context = {
        "location_count": Location.objects.filter(is_active=True).count(),
        "chapter_count": Chapter.objects.filter(is_active=True).count(),
        "cohort_count": Cohort.objects.filter(is_active=True).count(),
        "user_count": CustomUser.objects.filter(
            is_active=True,
            cohort_memberships__is_active=True,
        ).distinct().count(),
    }
    return render(request, "core/admin/dashboard.html", context)


@admin_required
def configuration_home_view(request):
    return render(
        request,
        "core/admin/configuration/index.html",
        {
            "location_count": Location.objects.count(),
            "chapter_count": Chapter.objects.count(),
            "cohort_count": Cohort.objects.count(),
        },
    )


@admin_required
def location_list_view(request):
    locations = Location.objects.annotate(chapter_count=Count("chapters"))
    return render(
        request,
        "core/admin/configuration/location_list.html",
        {"locations": locations},
    )


@admin_required
def location_create_view(request):
    return _configuration_form(
        request,
        form_class=LocationForm,
        title="Add location",
        success_message="Location created successfully.",
        success_url="location_list",
    )


@admin_required
def location_edit_view(request, location_id):
    return _configuration_form(
        request,
        form_class=LocationForm,
        instance=get_object_or_404(Location, pk=location_id),
        title="Edit location",
        success_message="Location updated successfully.",
        success_url="location_list",
    )


@admin_required
@require_POST
def location_delete_view(request, location_id):
    location = get_object_or_404(Location, pk=location_id)
    try:
        location.delete()
        messages.success(request, "Location deleted successfully.")
    except ProtectedError:
        messages.error(
            request,
            "This location is in use by a chapter. Deactivate it instead.",
        )
    return redirect("location_list")


@admin_required
def chapter_list_view(request):
    chapters = Chapter.objects.select_related("location").annotate(
        cohort_count=Count("cohorts")
    )
    return render(
        request,
        "core/admin/configuration/chapter_list.html",
        {"chapters": chapters},
    )


@admin_required
def chapter_create_view(request):
    return _configuration_form(
        request,
        form_class=ChapterForm,
        title="Add chapter",
        success_message="Chapter created successfully.",
        success_url="chapter_list",
    )


@admin_required
def chapter_edit_view(request, chapter_id):
    return _configuration_form(
        request,
        form_class=ChapterForm,
        instance=get_object_or_404(Chapter, pk=chapter_id),
        title="Edit chapter",
        success_message="Chapter updated successfully.",
        success_url="chapter_list",
    )


@admin_required
@require_POST
def chapter_delete_view(request, chapter_id):
    chapter = get_object_or_404(Chapter, pk=chapter_id)
    try:
        chapter.delete()
        messages.success(request, "Chapter deleted successfully.")
    except ProtectedError:
        messages.error(
            request,
            "This chapter has cohorts. Deactivate it instead.",
        )
    return redirect("chapter_list")


@admin_required
def cohort_list_view(request):
    cohorts = Cohort.objects.select_related("chapter", "chapter__location").annotate(
        user_count=Count(
            "memberships__user",
            filter=Q(memberships__is_active=True),
            distinct=True,
        )
    )
    return render(
        request,
        "core/admin/configuration/cohort_list.html",
        {"cohorts": cohorts},
    )


@admin_required
def cohort_create_view(request):
    return _configuration_form(
        request,
        form_class=CohortForm,
        title="Add cohort",
        success_message="Cohort created successfully.",
        success_url="cohort_list",
    )


@admin_required
def cohort_edit_view(request, cohort_id):
    return _configuration_form(
        request,
        form_class=CohortForm,
        instance=get_object_or_404(Cohort, pk=cohort_id),
        title="Edit cohort",
        success_message="Cohort updated successfully.",
        success_url="cohort_list",
    )


@admin_required
@require_POST
def cohort_delete_view(request, cohort_id):
    cohort = get_object_or_404(Cohort, pk=cohort_id)
    cohort.delete()
    messages.success(request, "Cohort deleted successfully.")
    return redirect("cohort_list")


@admin_required
def platform_user_list_view(request):
    users = (
        CustomUser.objects.exclude(role=CustomUser.ADMIN)
        .filter(is_superuser=False)
        .prefetch_related(
            Prefetch(
                "cohort_memberships",
                queryset=CohortMembership.objects.filter(is_active=True).select_related(
                    "cohort", "cohort__chapter"
                ),
            )
        )
        .order_by("first_name", "last_name", "email")
    )
    return render(request, "core/admin/users/list.html", {"platform_users": users})


@admin_required
def platform_user_create_view(request):
    return _platform_user_form(
        request,
        title="Add user",
        success_message="User provisioned successfully. They can now sign in with Google.",
    )


@admin_required
def platform_user_edit_view(request, user_id):
    user = get_object_or_404(
        CustomUser.objects.exclude(role=CustomUser.ADMIN).filter(is_superuser=False),
        pk=user_id,
    )
    return _platform_user_form(
        request,
        instance=user,
        title="Edit user",
        success_message="User access updated successfully.",
    )


def _configuration_form(
    request,
    *,
    form_class,
    title,
    success_message,
    success_url,
    instance=None,
):
    form = form_class(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, success_message)
        return redirect(success_url)
    return render(
        request,
        "core/admin/configuration/form.html",
        {"form": form, "title": title, "cancel_url": success_url},
    )


def _platform_user_form(request, *, title, success_message, instance=None):
    form = PlatformUserForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, success_message)
        return redirect("platform_user_list")
    return render(
        request,
        "core/admin/users/form.html",
        {"form": form, "title": title},
    )
