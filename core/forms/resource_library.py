from django import forms
from django.conf import settings

from core.forms.base import StyledModelForm
from core.services.resources import scope_key, scope_label


def validate_resource_upload(upload):
    if upload.size > settings.RESOURCE_UPLOAD_MAX_BYTES:
        limit = settings.RESOURCE_UPLOAD_MAX_BYTES // (1024 * 1024)
        raise forms.ValidationError(f"Each file must be no larger than {limit} MB.")
    return upload


class ResourceMultipleInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class ResourceMultipleField(forms.FileField):
    def clean(self, data, initial=None):
        if not data:
            return super().clean(data, initial) or []
        items = data if isinstance(data, (list, tuple)) else [data]
        return [validate_resource_upload(super(ResourceMultipleField, self).clean(item, initial)) for item in items]


class ResourceAttachmentsForm(StyledModelForm):
    resource_files = ResourceMultipleField(
        required=False, widget=ResourceMultipleInput,
        label="Add resources (images, videos and files)",
        help_text="Optional. Select multiple files, up to 100 MB each. Members of this group and its child groups can access them.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.field_wrapper_classes = {**self.field_wrapper_classes, "resource_files": "form-field--full"}


class ResourceUploadForm(forms.Form):
    scope = forms.ChoiceField(label="Add to")
    title = forms.CharField(max_length=200, required=False, help_text="Optional. Leave blank to use each file's name.")
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    files = ResourceMultipleField(widget=ResourceMultipleInput, label="Images, videos or files",
                                  help_text="Select one or more files, up to 100 MB each.")

    def __init__(self, *args, scopes, selected_scope=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.scopes = {scope_key(scope): scope for scope in scopes}
        self.fields["scope"].choices = [(key, scope_label(scope)) for key, scope in self.scopes.items()]
        if selected_scope:
            self.initial["scope"] = scope_key(selected_scope)
            self.fields["scope"].disabled = True
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
