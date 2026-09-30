from django import forms

from core.forms.renderers import ProjectFormRenderer


class StyledModelForm(forms.ModelForm):
    """Base for every project form.

    - widget CSS classes are added here, never in templates;
    - field_wrapper_classes maps a field name to extra classes for its
      .form-field wrapper (e.g. full-width fields in the grid layout).
    """

    default_renderer = ProjectFormRenderer()
    field_wrapper_classes = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "checkbox-input"
            else:
                field.widget.attrs["class"] = "form-control"
