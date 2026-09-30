from django.forms.renderers import TemplatesSetting


class ProjectFormRenderer(TemplatesSetting):
    """Looks templates up through TEMPLATES (so project DIRS are searched) and
    renders every field group with components/forms/field.html."""

    field_template_name = "components/forms/field.html"
