import mimetypes
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import content_disposition_header
from django.views.decorators.http import require_http_methods, require_POST

from core.forms.resource_library import ResourceUploadForm
from core.models import ChangeHistory, Cohort, ScopeResource, log_change
from core.services.audit import scope_ids
from core.services.resources import (
    RESOURCE_RELATED, SCOPE_MODELS, ResourceAccess, add_resource, scope_chain, scope_label,
)


@login_required
@require_http_methods(["GET", "POST"])
def resource_library(request, scope_type=None, scope_id=None):
    if not request.user.is_active:
        raise PermissionDenied
    access = ResourceAccess(request.user)
    drawer = request.headers.get("X-Form-Drawer") == "true"
    scope = None
    if scope_type:
        model = SCOPE_MODELS.get(scope_type)
        if not model:
            raise Http404
        scope = get_object_or_404(model, pk=scope_id)
        if not access.allows(scope):
            raise PermissionDenied("You do not have access to resources at this level.")
    uploads = access.scopes("create")
    if scope:
        uploads = [scope] if access.allows(scope, "create") else []
    form = ResourceUploadForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
        scopes=uploads, selected_scope=scope,
    )
    if request.method == "POST":
        if not uploads:
            raise PermissionDenied("You do not have permission to add resources here.")
        if form.is_valid():
            target = form.scopes[form.cleaned_data["scope"]]
            with transaction.atomic():
                for uploaded in form.cleaned_data["files"]:
                    add_resource(target, uploaded, request.user, form.cleaned_data["title"], form.cleaned_data["description"])
            messages.success(request, "Resources added successfully.")
            if drawer:
                return JsonResponse({"saved": True, "resource_url": reverse("scope_resources", args=[target._meta.model_name, target.pk])})
            return redirect("scope_resources", scope_type=target._meta.model_name, scope_id=target.pk)

    resources = ScopeResource.objects.filter(access.query(), is_active=True).select_related(*RESOURCE_RELATED)
    if scope:
        group_filter = Q(pk__in=[])
        for parent in scope_chain(scope):
            group_filter |= Q(**{parent._meta.model_name: parent})
        resources = resources.filter(group_filter)
    query = request.GET.get("q", "").strip()
    kind = request.GET.get("kind", "")
    if query:
        resources = resources.filter(Q(title__icontains=query) | Q(description__icontains=query) | Q(original_name__icontains=query))
    if kind in dict(ScopeResource.RESOURCE_TYPES):
        resources = resources.filter(resource_type=kind)
    else:
        kind = ""
    page = Paginator(resources, 12).get_page(request.GET.get("page"))
    for resource in page:
        resource.can_remove = access.allows(resource.scope, "delete")
        resource.origin_label = scope_label(resource.scope)
    return render(request, "core/resources/library.html", {
        "resource_layout": "layouts/resource_drawer.html" if drawer else "layouts/admin.html" if request.user.is_platform_admin else "layouts/member_resources.html",
        "in_drawer": drawer, "library_url": request.path,
        "scope": scope, "scope_label": scope_label(scope) if scope else "All your groups",
        "scope_type": scope._meta.verbose_name if scope else "",
        "detail_url": reverse(f"{scope._meta.model_name}_detail", args=[scope.pk]) if scope else "",
        "resource_page": page, "upload_form": form, "can_upload": bool(uploads),
        "resource_types": ScopeResource.RESOURCE_TYPES, "search_query": query, "selected_kind": kind,
        "available_scopes": [{"label": scope_label(item), "url": reverse("scope_resources", args=[item._meta.model_name, item.pk])}
                             for item in access.scopes()],
    })


@login_required
@require_POST
@transaction.atomic
def resource_remove(request, resource_id):
    resource = get_object_or_404(ScopeResource.objects.select_related(*RESOURCE_RELATED), pk=resource_id, is_active=True)
    access = ResourceAccess(request.user)
    scope = resource.scope
    if not access.allows(scope, "delete"):
        raise PermissionDenied("You do not have permission to remove this resource.")
    resource.is_active = False
    resource.save(update_fields=["is_active"])
    log_change(request.user, ChangeHistory.Action.REMOVE, "Resource", resource.title,
               f"Removed resource '{resource.title}' from {scope_label(scope)}.", entity_id=resource.pk,
               cohort=scope if isinstance(scope, Cohort) else None,
               details={"scope_ids": scope_ids(scope), "resource_model": "scope_resource", "is_active": False})
    messages.success(request, "Resource removed. Its audit history has been retained.")
    if request.headers.get("X-Form-Drawer") == "true":
        return JsonResponse({"saved": True, "resource_url": reverse("scope_resources", args=[scope._meta.model_name, scope.pk])})
    return redirect("scope_resources", scope_type=scope._meta.model_name, scope_id=scope.pk)


@login_required
@require_http_methods(["GET", "HEAD"])
def resource_file(request, resource_id):
    resource = get_object_or_404(ScopeResource.objects.select_related(*RESOURCE_RELATED), pk=resource_id, is_active=True)
    if not ResourceAccess(request.user).allows(resource.scope):
        raise PermissionDenied("You do not have access to this resource.")
    try:
        size = resource.file.size
        handle = resource.file.open("rb")
    except (FileNotFoundError, OSError):
        raise Http404("This file is no longer available.")
    inline = resource.resource_type in {ScopeResource.IMAGE, ScopeResource.VIDEO} and request.GET.get("download") != "1"
    media_type = mimetypes.guess_type(resource.file.name)[0] if inline else "application/octet-stream"
    media_type = media_type or "application/octet-stream"
    range_header = request.headers.get("Range") if request.method == "GET" else None
    if range_header:
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header) if len(range_header) <= 128 else None
        start, end = 0, size - 1
        valid = bool(match and any(match.groups()))
        if valid:
            first, last = match.groups()
            if not first:
                length = int(last)
                start = max(0, size - length)
                valid = length > 0
            else:
                start = int(first)
                end = min(int(last), size - 1) if last else size - 1
            valid = valid and 0 <= start <= end < size
        if not valid:
            handle.close()
            response = HttpResponse(status=416)
            response["Content-Range"] = f"bytes */{size}"
        else:
            handle.seek(start)

            def chunks():
                remaining = end - start + 1
                try:
                    while remaining:
                        chunk = handle.read(min(64 * 1024, remaining))
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        yield chunk
                finally:
                    handle.close()

            response = StreamingHttpResponse(chunks(), status=206, content_type=media_type)
            response["Content-Range"] = f"bytes {start}-{end}/{size}"
            response["Content-Length"] = str(end - start + 1)
    elif request.method == "HEAD":
        handle.close()
        response = HttpResponse(content_type=media_type)
        response["Content-Length"] = str(size)
    else:
        response = FileResponse(handle, content_type=media_type)
    response["Accept-Ranges"] = "bytes"
    response["Content-Disposition"] = content_disposition_header(not inline, resource.original_name)
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
