"""UI components that need Python: slots, csrf or computed markup.
Plain-markup components are includes in templates/components/ (see docs)."""
from django import template
from django.template.loader import render_to_string
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()


def _slot(content):
    # Block content always carries whitespace; treat whitespace-only as empty.
    return mark_safe(content.strip())


@register.simple_block_tag
def page_header(content, title, eyebrow="", description=""):
    """{% page_header title=… eyebrow=… description=… %}<actions>{% endpage_header %}"""
    return render_to_string(
        "components/page_header.html",
        {
            "title": title,
            "eyebrow": eyebrow,
            "description": description,
            "actions": _slot(content),
        },
    )


@register.simple_block_tag
def data_table(content, empty="No records yet.", id=""):
    """{% data_table id="x-table" empty="No x yet." %}<thead>…</thead><tbody>…</tbody>{% enddata_table %}

    The id is required when the page adds components/table_filters.html.
    """
    return render_to_string(
        "components/data_table.html",
        {"content": _slot(content), "empty": empty, "id": id},
    )


@register.simple_block_tag
def status_card(content, title, code="", icon="info", tone="brand", action_url="", action_label="", action_icon=""):
    """Centered status card for 403/404/500 and sign-in errors; the body is the message."""
    return render_to_string(
        "components/status_card.html",
        {
            "title": title,
            "code": code,
            "icon": icon,
            "tone": tone,
            "action_url": action_url,
            "action_label": action_label,
            "action_icon": action_icon,
            "body": _slot(content),
        },
    )


@register.simple_tag
def status_badge(active, on="Active", off="Inactive"):
    return format_html(
        '<span class="status-badge{}">{}</span>',
        " status-badge--active" if active else "",
        on if active else off,
    )


@register.inclusion_tag("components/row_actions.html", takes_context=True)
def row_actions(context, edit_url, delete_url="", confirm="Delete this item?", edit_label="Edit"):
    """Renders the actions <td>: an Edit link and, optionally, a confirmed POST delete."""
    return {
        "edit_url": edit_url,
        "edit_label": edit_label,
        "delete_url": delete_url,
        "confirm": confirm,
        "csrf_token": context.get("csrf_token"),
    }
