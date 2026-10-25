from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView

from core.forms.tasks_questions import (
    QuestionResponseForm,
    QuestionResponseReviewForm,
    TaskSubmissionForm,
    TaskSubmissionReviewForm,
    TermQuestionForm,
    TermTaskForm,
)
from core.models import (
    ChangeHistory,
    Cohort,
    CohortMembership,
    QuestionResponse,
    TaskSubmission,
    Term,
    TermQuestion,
    TermTask,
    log_change,
)
from core.permissions import (
    RoleAccessRequiredMixin,
    can_user_view_member_data,
    get_mentor_assigned_mentee_ids,
    get_senior_mentor_scoped_user_ids,
    has_role_permission,
)


# ==============================================================================
# Tasks
# ==============================================================================

class CohortTermTaskCreateView(RoleAccessRequiredMixin, CreateView):
    model = TermTask
    form_class = TermTaskForm
    template_name = "core/admin/form.html"
    permission_resource = "tasks"
    permission_action = "create"

    def dispatch(self, request, *args, **kwargs):
        self.cohort = get_object_or_404(
            Cohort.objects.select_related("chapter", "chapter__location", "chapter__location__program"),
            pk=kwargs["cohort_id"],
        )
        self.term = get_object_or_404(Term, pk=kwargs["term_id"], cohort=self.cohort)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["term"] = self.term
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        task = form.save()
        log_change(
            actor=self.request.user,
            action=ChangeHistory.Action.CREATE,
            entity_type="Task",
            entity_name=task.title,
            entity_id=task.pk,
            cohort=self.cohort,
            description=f"Created task '{task.title}' under {self.term.name} (accepts: {task.allowed_types_display}).",
            details={
                "term": self.term.name,
                "points": task.points,
                "due_date": str(task.due_date) if task.due_date else None,
                "audience": task.target_audience,
                "allow_text": task.allow_text,
                "allow_file": task.allow_file,
                "allow_url": task.allow_url,
                "allow_image": task.allow_image,
            },
        )
        messages.success(self.request, f"Task '{task.title}' created successfully.")
        return redirect("cohort_term_task_detail", cohort_id=self.cohort.pk, term_id=self.term.pk, task_id=task.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            title=f"Add Task to {self.term.name}",
            eyebrow=f"{self.cohort.name} · {self.term.name}",
            description="Create a task or assignment. Specify accepted submission formats (text, file, url, image), audience, and deadline.",
            submit_label="Create task",
            form_layout="grid",
            cancel_url=reverse("cohort_term_detail", args=[self.cohort.pk, self.term.pk]),
        )
        return context


class CohortTermTaskDetailView(DetailView):
    model = TermTask
    pk_url_kwarg = "task_id"
    template_name = "core/admin/configuration/task_detail.html"

    def dispatch(self, request, *args, **kwargs):
        self.cohort = get_object_or_404(
            Cohort.objects.select_related("chapter", "chapter__location", "chapter__location__program"),
            pk=kwargs["cohort_id"],
        )
        self.term = get_object_or_404(Term, pk=kwargs["term_id"], cohort=self.cohort)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return TermTask.objects.filter(term=self.term)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task = self.object
        user = self.request.user

        can_manage = has_role_permission(user, "tasks", "update", cohort=self.cohort)
        can_delete = has_role_permission(user, "tasks", "delete", cohort=self.cohort)

        my_submission = None
        if user.is_authenticated:
            my_submission = task.submissions.filter(user=user).first()

        context["cohort"] = self.cohort
        context["term"] = self.term
        context["can_manage"] = can_manage
        context["can_delete"] = can_delete
        context["my_submission"] = my_submission
        context["submission_form"] = kwargs.get("submission_form") or TaskSubmissionForm(
            instance=my_submission, task=task, user=user
        )

        if can_manage:
            submissions_qs = task.submissions.select_related("user", "reviewed_by").order_by("-submitted_at")
            if not user.is_platform_admin:
                cohort_roles = set(
                    user.cohort_memberships.filter(cohort=self.cohort, is_active=True).values_list("role", flat=True)
                )
                if CohortMembership.COMMUNITY_LEADER in cohort_roles:
                    pass
                elif CohortMembership.SENIOR_MEMBER in cohort_roles:
                    scoped_ids = get_senior_mentor_scoped_user_ids(user, cohort=self.cohort)
                    submissions_qs = submissions_qs.filter(user_id__in=scoped_ids)
                elif CohortMembership.MENTOR in cohort_roles:
                    mentee_ids = get_mentor_assigned_mentee_ids(user, cohort=self.cohort)
                    submissions_qs = submissions_qs.filter(user_id__in=mentee_ids)
                else:
                    submissions_qs = submissions_qs.none()
            context["submissions"] = list(submissions_qs)
            context["review_form"] = TaskSubmissionReviewForm()

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        user = request.user
        if not user.is_authenticated:
            raise PermissionDenied("Authentication required to submit work.")

        my_submission = self.object.submissions.filter(user=user).first()
        form = TaskSubmissionForm(
            request.POST,
            request.FILES,
            instance=my_submission,
            task=self.object,
            user=user,
        )

        if form.is_valid():
            submission = form.save(commit=False)
            submission.status = TaskSubmission.Status.SUBMITTED
            submission.save()

            log_change(
                actor=user,
                action=ChangeHistory.Action.UPDATE if my_submission else ChangeHistory.Action.CREATE,
                entity_type="TaskSubmission",
                entity_name=f"{self.object.title} Submission",
                entity_id=submission.pk,
                cohort=self.cohort,
                description=f"User {user.get_full_name() or user.username} submitted work for task '{self.object.title}'.",
                details={
                    "task": self.object.title,
                    "has_text": bool(submission.text_response),
                    "has_file": bool(submission.file_submission),
                    "has_image": bool(submission.image_submission),
                    "has_url": bool(submission.url_submission),
                },
            )
            messages.success(request, f"Your submission for '{self.object.title}' has been recorded.")
            return redirect(
                "cohort_term_task_detail",
                cohort_id=self.cohort.pk,
                term_id=self.term.pk,
                task_id=self.object.pk,
            )

        return self.render_to_response(self.get_context_data(submission_form=form))


class CohortTermTaskUpdateView(RoleAccessRequiredMixin, UpdateView):
    model = TermTask
    pk_url_kwarg = "task_id"
    form_class = TermTaskForm
    template_name = "core/admin/form.html"
    permission_resource = "tasks"
    permission_action = "update"

    def dispatch(self, request, *args, **kwargs):
        self.cohort = get_object_or_404(
            Cohort.objects.select_related("chapter", "chapter__location", "chapter__location__program"),
            pk=kwargs["cohort_id"],
        )
        self.term = get_object_or_404(Term, pk=kwargs["term_id"], cohort=self.cohort)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return TermTask.objects.filter(term=self.term)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["term"] = self.term
        return kwargs

    def form_valid(self, form):
        task = form.save()
        log_change(
            actor=self.request.user,
            action=ChangeHistory.Action.UPDATE,
            entity_type="Task",
            entity_name=task.title,
            entity_id=task.pk,
            cohort=self.cohort,
            description=f"Updated task '{task.title}' under {self.term.name}.",
            details={
                "points": task.points,
                "due_date": str(task.due_date) if task.due_date else None,
                "audience": task.target_audience,
            },
        )
        messages.success(self.request, f"Task '{task.title}' updated successfully.")
        return redirect("cohort_term_task_detail", cohort_id=self.cohort.pk, term_id=self.term.pk, task_id=task.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            title=f"Edit Task: {self.object.title}",
            eyebrow=f"{self.cohort.name} · {self.term.name}",
            description="Update task deliverables, accepted formats, audience, or deadline.",
            submit_label="Update task",
            form_layout="grid",
            cancel_url=reverse("cohort_term_task_detail", args=[self.cohort.pk, self.term.pk, self.object.pk]),
        )
        return context


class CohortTermTaskDeleteView(RoleAccessRequiredMixin, DeleteView):
    model = TermTask
    pk_url_kwarg = "task_id"
    http_method_names = ["post"]
    permission_resource = "tasks"
    permission_action = "delete"

    def dispatch(self, request, *args, **kwargs):
        self.cohort = get_object_or_404(Cohort, pk=kwargs["cohort_id"])
        self.term = get_object_or_404(Term, pk=kwargs["term_id"], cohort=self.cohort)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return TermTask.objects.filter(term=self.term)

    def form_valid(self, form):
        title = self.object.title
        log_change(
            actor=self.request.user,
            action=ChangeHistory.Action.DELETE,
            entity_type="Task",
            entity_name=title,
            entity_id=self.object.pk,
            cohort=self.cohort,
            description=f"Deleted task '{title}' from {self.term.name}.",
        )
        self.object.delete()
        messages.success(self.request, f"Task '{title}' deleted successfully.")
        return redirect("cohort_term_detail", cohort_id=self.cohort.pk, term_id=self.term.pk)


class TaskSubmissionReviewView(RoleAccessRequiredMixin, View):
    http_method_names = ["post"]
    permission_resource = "tasks"
    permission_action = "update"

    def dispatch(self, request, *args, **kwargs):
        self.cohort = get_object_or_404(Cohort, pk=kwargs["cohort_id"])
        self.term = get_object_or_404(Term, pk=kwargs["term_id"], cohort=self.cohort)
        self.task = get_object_or_404(TermTask, pk=kwargs["task_id"], term=self.term)
        self.submission = get_object_or_404(TaskSubmission, pk=kwargs["submission_id"], task=self.task)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not can_user_view_member_data(request.user, self.submission.user, cohort=self.cohort):
            raise PermissionDenied("You do not have permission to review this participant's submission.")

        form = TaskSubmissionReviewForm(request.POST, instance=self.submission)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.reviewed_by = request.user
            sub.reviewed_at = timezone.now()
            sub.save()

            log_change(
                actor=request.user,
                action=ChangeHistory.Action.REVIEW,
                entity_type="TaskSubmission",
                entity_name=f"{self.task.title} submission by {sub.user}",
                entity_id=sub.pk,
                cohort=self.cohort,
                description=f"Reviewed {sub.user.get_full_name() or sub.user.username}'s submission for '{self.task.title}' (Status: {sub.get_status_display()}, Score: {sub.score or 'N/A'}).",
                details={
                    "status": sub.status,
                    "score": str(sub.score) if sub.score is not None else None,
                    "feedback": sub.feedback,
                },
            )
            messages.success(request, f"Review for {sub.user.get_full_name() or sub.user.username} saved.")
        else:
            errors = "; ".join([f"{f}: {e[0]}" for f, e in form.errors.items()])
            messages.error(request, f"Failed to save review: {errors}")

        return redirect(
            "cohort_term_task_detail",
            cohort_id=self.cohort.pk,
            term_id=self.term.pk,
            task_id=self.task.pk,
        )


# ==============================================================================
# Questions
# ==============================================================================

class CohortTermQuestionCreateView(RoleAccessRequiredMixin, CreateView):
    model = TermQuestion
    form_class = TermQuestionForm
    template_name = "core/admin/form.html"
    permission_resource = "questions"
    permission_action = "create"

    def dispatch(self, request, *args, **kwargs):
        self.cohort = get_object_or_404(
            Cohort.objects.select_related("chapter", "chapter__location", "chapter__location__program"),
            pk=kwargs["cohort_id"],
        )
        self.term = get_object_or_404(Term, pk=kwargs["term_id"], cohort=self.cohort)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["term"] = self.term
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        question = form.save()
        log_change(
            actor=self.request.user,
            action=ChangeHistory.Action.CREATE,
            entity_type="Question",
            entity_name=question.title,
            entity_id=question.pk,
            cohort=self.cohort,
            description=f"Created question '{question.title}' under {self.term.name} (accepts: {question.allowed_types_display}).",
            details={
                "term": self.term.name,
                "is_required": question.is_required,
                "due_date": str(question.due_date) if question.due_date else None,
                "audience": question.target_audience,
                "allow_text": question.allow_text,
                "allow_file": question.allow_file,
                "allow_url": question.allow_url,
                "allow_image": question.allow_image,
            },
        )
        messages.success(self.request, f"Question '{question.title}' created successfully.")
        return redirect(
            "cohort_term_question_detail",
            cohort_id=self.cohort.pk,
            term_id=self.term.pk,
            question_id=question.pk,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            title=f"Add Question to {self.term.name}",
            eyebrow=f"{self.cohort.name} · {self.term.name}",
            description="Create a question or reflection inquiry. Specify accepted answer formats, audience, and requirement.",
            submit_label="Create question",
            form_layout="grid",
            cancel_url=reverse("cohort_term_detail", args=[self.cohort.pk, self.term.pk]),
        )
        return context


class CohortTermQuestionDetailView(DetailView):
    model = TermQuestion
    pk_url_kwarg = "question_id"
    template_name = "core/admin/configuration/question_detail.html"

    def dispatch(self, request, *args, **kwargs):
        self.cohort = get_object_or_404(
            Cohort.objects.select_related("chapter", "chapter__location", "chapter__location__program"),
            pk=kwargs["cohort_id"],
        )
        self.term = get_object_or_404(Term, pk=kwargs["term_id"], cohort=self.cohort)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return TermQuestion.objects.filter(term=self.term)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        question = self.object
        user = self.request.user

        can_manage = has_role_permission(user, "questions", "update", cohort=self.cohort)
        can_delete = has_role_permission(user, "questions", "delete", cohort=self.cohort)

        my_response = None
        if user.is_authenticated:
            my_response = question.responses.filter(user=user).first()

        context["cohort"] = self.cohort
        context["term"] = self.term
        context["can_manage"] = can_manage
        context["can_delete"] = can_delete
        context["my_response"] = my_response
        context["response_form"] = kwargs.get("response_form") or QuestionResponseForm(
            instance=my_response, question=question, user=user
        )

        if can_manage:
            responses_qs = question.responses.select_related("user", "reviewed_by").order_by("-submitted_at")
            if not user.is_platform_admin:
                cohort_roles = set(
                    user.cohort_memberships.filter(cohort=self.cohort, is_active=True).values_list("role", flat=True)
                )
                if CohortMembership.COMMUNITY_LEADER in cohort_roles:
                    pass
                elif CohortMembership.SENIOR_MEMBER in cohort_roles:
                    scoped_ids = get_senior_mentor_scoped_user_ids(user, cohort=self.cohort)
                    responses_qs = responses_qs.filter(user_id__in=scoped_ids)
                elif CohortMembership.MENTOR in cohort_roles:
                    mentee_ids = get_mentor_assigned_mentee_ids(user, cohort=self.cohort)
                    responses_qs = responses_qs.filter(user_id__in=mentee_ids)
                else:
                    responses_qs = responses_qs.none()
            context["responses"] = list(responses_qs)
            context["review_form"] = QuestionResponseReviewForm()

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        user = request.user
        if not user.is_authenticated:
            raise PermissionDenied("Authentication required to submit answer.")

        my_response = self.object.responses.filter(user=user).first()
        form = QuestionResponseForm(
            request.POST,
            request.FILES,
            instance=my_response,
            question=self.object,
            user=user,
        )

        if form.is_valid():
            response_obj = form.save(commit=False)
            response_obj.status = QuestionResponse.Status.SUBMITTED
            response_obj.save()

            log_change(
                actor=user,
                action=ChangeHistory.Action.UPDATE if my_response else ChangeHistory.Action.CREATE,
                entity_type="QuestionResponse",
                entity_name=f"{self.object.title} Response",
                entity_id=response_obj.pk,
                cohort=self.cohort,
                description=f"User {user.get_full_name() or user.username} answered question '{self.object.title}'.",
                details={
                    "question": self.object.title,
                    "has_text": bool(response_obj.text_response),
                    "has_file": bool(response_obj.file_submission),
                    "has_image": bool(response_obj.image_submission),
                    "has_url": bool(response_obj.url_submission),
                },
            )
            messages.success(request, f"Your answer for '{self.object.title}' has been submitted.")
            return redirect(
                "cohort_term_question_detail",
                cohort_id=self.cohort.pk,
                term_id=self.term.pk,
                question_id=self.object.pk,
            )

        return self.render_to_response(self.get_context_data(response_form=form))


class CohortTermQuestionUpdateView(RoleAccessRequiredMixin, UpdateView):
    model = TermQuestion
    pk_url_kwarg = "question_id"
    form_class = TermQuestionForm
    template_name = "core/admin/form.html"
    permission_resource = "questions"
    permission_action = "update"

    def dispatch(self, request, *args, **kwargs):
        self.cohort = get_object_or_404(
            Cohort.objects.select_related("chapter", "chapter__location", "chapter__location__program"),
            pk=kwargs["cohort_id"],
        )
        self.term = get_object_or_404(Term, pk=kwargs["term_id"], cohort=self.cohort)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return TermQuestion.objects.filter(term=self.term)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["term"] = self.term
        return kwargs

    def form_valid(self, form):
        question = form.save()
        log_change(
            actor=self.request.user,
            action=ChangeHistory.Action.UPDATE,
            entity_type="Question",
            entity_name=question.title,
            entity_id=question.pk,
            cohort=self.cohort,
            description=f"Updated question '{question.title}' under {self.term.name}.",
            details={
                "is_required": question.is_required,
                "due_date": str(question.due_date) if question.due_date else None,
                "audience": question.target_audience,
            },
        )
        messages.success(self.request, f"Question '{question.title}' updated successfully.")
        return redirect(
            "cohort_term_question_detail",
            cohort_id=self.cohort.pk,
            term_id=self.term.pk,
            question_id=question.pk,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            title=f"Edit Question: {self.object.title}",
            eyebrow=f"{self.cohort.name} · {self.term.name}",
            description="Update question prompt, accepted answer formats, audience, or deadline.",
            submit_label="Update question",
            form_layout="grid",
            cancel_url=reverse("cohort_term_question_detail", args=[self.cohort.pk, self.term.pk, self.object.pk]),
        )
        return context


class CohortTermQuestionDeleteView(RoleAccessRequiredMixin, DeleteView):
    model = TermQuestion
    pk_url_kwarg = "question_id"
    http_method_names = ["post"]
    permission_resource = "questions"
    permission_action = "delete"

    def dispatch(self, request, *args, **kwargs):
        self.cohort = get_object_or_404(Cohort, pk=kwargs["cohort_id"])
        self.term = get_object_or_404(Term, pk=kwargs["term_id"], cohort=self.cohort)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return TermQuestion.objects.filter(term=self.term)

    def form_valid(self, form):
        title = self.object.title
        log_change(
            actor=self.request.user,
            action=ChangeHistory.Action.DELETE,
            entity_type="Question",
            entity_name=title,
            entity_id=self.object.pk,
            cohort=self.cohort,
            description=f"Deleted question '{title}' from {self.term.name}.",
        )
        self.object.delete()
        messages.success(self.request, f"Question '{title}' deleted successfully.")
        return redirect("cohort_term_detail", cohort_id=self.cohort.pk, term_id=self.term.pk)


class QuestionResponseReviewView(RoleAccessRequiredMixin, View):
    http_method_names = ["post"]
    permission_resource = "questions"
    permission_action = "update"

    def dispatch(self, request, *args, **kwargs):
        self.cohort = get_object_or_404(Cohort, pk=kwargs["cohort_id"])
        self.term = get_object_or_404(Term, pk=kwargs["term_id"], cohort=self.cohort)
        self.question = get_object_or_404(TermQuestion, pk=kwargs["question_id"], term=self.term)
        self.response_obj = get_object_or_404(QuestionResponse, pk=kwargs["response_id"], question=self.question)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not can_user_view_member_data(request.user, self.response_obj.user, cohort=self.cohort):
            raise PermissionDenied("You do not have permission to review this participant's answer.")

        form = QuestionResponseReviewForm(request.POST, instance=self.response_obj)
        if form.is_valid():
            resp = form.save(commit=False)
            resp.reviewed_by = request.user
            resp.save()

            log_change(
                actor=request.user,
                action=ChangeHistory.Action.REVIEW,
                entity_type="QuestionResponse",
                entity_name=f"{self.question.title} response by {resp.user}",
                entity_id=resp.pk,
                cohort=self.cohort,
                description=f"Reviewed {resp.user.get_full_name() or resp.user.username}'s response for question '{self.question.title}' (Status: {resp.get_status_display()}).",
                details={
                    "status": resp.status,
                    "feedback": resp.feedback,
                },
            )
            messages.success(request, f"Review for {resp.user.get_full_name() or resp.user.username} saved.")
        else:
            errors = "; ".join([f"{f}: {e[0]}" for f, e in form.errors.items()])
            messages.error(request, f"Failed to save review: {errors}")

        return redirect(
            "cohort_term_question_detail",
            cohort_id=self.cohort.pk,
            term_id=self.term.pk,
            question_id=self.question.pk,
        )
