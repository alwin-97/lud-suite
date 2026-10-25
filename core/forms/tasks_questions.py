from django import forms
from django.core.exceptions import ValidationError

from core.forms.base import StyledModelForm
from core.models import (
    QuestionResponse,
    TaskSubmission,
    TermQuestion,
    TermTask,
)


class TermTaskForm(StyledModelForm):
    field_wrapper_classes = {
        "description": "form-field--full",
    }

    class Meta:
        model = TermTask
        fields = (
            "title",
            "description",
            "target_audience",
            "due_date",
            "points",
            "allow_text",
            "allow_file",
            "allow_url",
            "allow_image",
            "sequence",
            "is_active",
        )
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Describe the task deliverables, guidelines, and expectations...",
                }
            ),
        }

    def __init__(self, *args, term=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.term = term
        if not self.instance.pk and term:
            next_seq = (
                term.tasks.order_by("-sequence").values_list("sequence", flat=True).first()
                or 0
            ) + 1
            self.initial.setdefault("sequence", next_seq)

    def clean(self):
        cleaned = super().clean()
        allow_text = cleaned.get("allow_text")
        allow_file = cleaned.get("allow_file")
        allow_url = cleaned.get("allow_url")
        allow_image = cleaned.get("allow_image")

        if not any([allow_text, allow_file, allow_url, allow_image]):
            raise ValidationError(
                "You must allow at least one form of submission (Text, File, URL, or Image)."
            )

        return cleaned

    def save(self, commit=True):
        if self.term and not self.instance.term_id:
            self.instance.term = self.term
        return super().save(commit=commit)


class TaskSubmissionForm(StyledModelForm):
    field_wrapper_classes = {
        "text_response": "form-field--full",
        "url_submission": "form-field--full",
        "file_submission": "form-field--full",
        "image_submission": "form-field--full",
    }

    class Meta:
        model = TaskSubmission
        fields = (
            "text_response",
            "file_submission",
            "image_submission",
            "url_submission",
        )
        widgets = {
            "text_response": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Enter your answer, explanation, or notes here...",
                }
            ),
            "url_submission": forms.URLInput(
                attrs={"placeholder": "https://docs.google.com/... or https://github.com/..."}
            ),
        }

    def __init__(self, *args, task=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.task = task or getattr(self.instance, "task", None)
        self.user = user

        if self.task:
            if not self.task.allow_text:
                self.fields.pop("text_response", None)
            if not self.task.allow_file:
                self.fields.pop("file_submission", None)
            if not self.task.allow_image:
                self.fields.pop("image_submission", None)
            if not self.task.allow_url:
                self.fields.pop("url_submission", None)

    def clean(self):
        cleaned = super().clean()
        text = cleaned.get("text_response")
        file_sub = cleaned.get("file_submission")
        img_sub = cleaned.get("image_submission")
        url_sub = cleaned.get("url_submission")

        has_any = bool(
            (text and text.strip())
            or file_sub
            or img_sub
            or (url_sub and url_sub.strip())
        )
        if not has_any:
            raise ValidationError(
                "Please provide at least one required submission item (text, file, image, or link)."
            )

        return cleaned

    def save(self, commit=True):
        if self.task and not self.instance.task_id:
            self.instance.task = self.task
        if self.user and not self.instance.user_id:
            self.instance.user = self.user
        return super().save(commit=commit)


class TaskSubmissionReviewForm(StyledModelForm):
    field_wrapper_classes = {
        "feedback": "form-field--full",
    }

    class Meta:
        model = TaskSubmission
        fields = ("status", "score", "feedback")
        widgets = {
            "feedback": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Feedback, remarks, or revision instructions for the participant...",
                }
            ),
        }

    def clean_score(self):
        score = self.cleaned_data.get("score")
        if (
            score is not None
            and self.instance
            and self.instance.task
            and self.instance.task.points is not None
        ):
            if score > self.instance.task.points:
                raise ValidationError(
                    f"Score cannot exceed maximum points ({self.instance.task.points})."
                )
            if score < 0:
                raise ValidationError("Score cannot be negative.")
        return score


class TermQuestionForm(StyledModelForm):
    field_wrapper_classes = {
        "prompt": "form-field--full",
        "help_text": "form-field--full",
    }

    class Meta:
        model = TermQuestion
        fields = (
            "title",
            "prompt",
            "help_text",
            "target_audience",
            "due_date",
            "is_required",
            "allow_text",
            "allow_file",
            "allow_url",
            "allow_image",
            "sequence",
            "is_active",
        )
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "prompt": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Enter the question prompt, reflection question, or problem statement...",
                }
            ),
            "help_text": forms.Textarea(
                attrs={"rows": 2, "placeholder": "Guidance, tips, or criteria for answering..."}
            ),
        }

    def __init__(self, *args, term=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.term = term
        if not self.instance.pk and term:
            next_seq = (
                term.questions.order_by("-sequence").values_list("sequence", flat=True).first()
                or 0
            ) + 1
            self.initial.setdefault("sequence", next_seq)

    def clean(self):
        cleaned = super().clean()
        allow_text = cleaned.get("allow_text")
        allow_file = cleaned.get("allow_file")
        allow_url = cleaned.get("allow_url")
        allow_image = cleaned.get("allow_image")

        if not any([allow_text, allow_file, allow_url, allow_image]):
            raise ValidationError(
                "You must allow at least one form of answer (Text, File, URL, or Image)."
            )

        return cleaned

    def save(self, commit=True):
        if self.term and not self.instance.term_id:
            self.instance.term = self.term
        return super().save(commit=commit)


class QuestionResponseForm(StyledModelForm):
    field_wrapper_classes = {
        "text_response": "form-field--full",
        "url_submission": "form-field--full",
        "file_submission": "form-field--full",
        "image_submission": "form-field--full",
    }

    class Meta:
        model = QuestionResponse
        fields = (
            "text_response",
            "file_submission",
            "image_submission",
            "url_submission",
        )
        widgets = {
            "text_response": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Write your response here...",
                }
            ),
            "url_submission": forms.URLInput(attrs={"placeholder": "https://..."}),
        }

    def __init__(self, *args, question=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.question = question or getattr(self.instance, "question", None)
        self.user = user

        if self.question:
            if not self.question.allow_text:
                self.fields.pop("text_response", None)
            if not self.question.allow_file:
                self.fields.pop("file_submission", None)
            if not self.question.allow_image:
                self.fields.pop("image_submission", None)
            if not self.question.allow_url:
                self.fields.pop("url_submission", None)

    def clean(self):
        cleaned = super().clean()
        text = cleaned.get("text_response")
        file_sub = cleaned.get("file_submission")
        img_sub = cleaned.get("image_submission")
        url_sub = cleaned.get("url_submission")

        has_any = bool(
            (text and text.strip())
            or file_sub
            or img_sub
            or (url_sub and url_sub.strip())
        )
        if not has_any:
            raise ValidationError(
                "Please provide an answer using at least one allowed format."
            )

        return cleaned

    def save(self, commit=True):
        if self.question and not self.instance.question_id:
            self.instance.question = self.question
        if self.user and not self.instance.user_id:
            self.instance.user = self.user
        return super().save(commit=commit)


class QuestionResponseReviewForm(StyledModelForm):
    field_wrapper_classes = {
        "feedback": "form-field--full",
    }

    class Meta:
        model = QuestionResponse
        fields = ("status", "feedback")
        widgets = {
            "feedback": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Feedback or remarks for the participant..."}
            ),
        }
