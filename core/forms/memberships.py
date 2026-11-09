import csv
from io import StringIO

from django import forms
from django.db.models import Q

from core.models import ChangeHistory, CustomUser, CohortMembership, log_change
from core.services.memberships import add_membership, set_membership_active


class MemberChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, user):
        name = user.get_full_name() or user.username
        return f"{name} · {user.email}" + (" (account inactive)" if not user.is_active else "")


class ResourceMembersForm(forms.Form):
    """Optional additions, plus explicit status controls for existing memberships."""

    active_memberships = forms.MultipleChoiceField(
        required=False, label="Current memberships", widget=forms.CheckboxSelectMultiple,
        help_text="Checked memberships are active. Uncheck to mark someone as having left; check again when they return. History is retained.",
    )
    users = MemberChoiceField(
        queryset=CustomUser.objects.none(), required=False, label="Add existing users",
        widget=forms.SelectMultiple(attrs={"size": 7}),
        help_text="Select one or more users. Existing inactive memberships will be reactivated.",
    )
    role = forms.ChoiceField(choices=CohortMembership.ROLE_CHOICES, initial=CohortMembership.MENTEE,
                             required=False, label="Role for people being added")
    new_people = forms.CharField(
        required=False, label="Add new people",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "asha@example.com, Asha, Nair"}),
        help_text="One person per line: email, first name, last name. Names are optional. New people can sign in with their Google account.",
    )
    reactivate_accounts = forms.BooleanField(
        required=False, label="Reactivate inactive accounts chosen in Add existing users",
        help_text="This restores their account access, including any other active memberships they already have.",
    )

    def __init__(self, *args, scope=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.scope = scope
        self.memberships = list(scope.memberships.select_related("user").order_by("user__email", "role")) if scope and scope.pk else []
        self.fields["active_memberships"].choices = [
            (str(m.pk), f"{m.user} · {m.user.email} — {m.get_role_display()}"
             + (" (membership inactive)" if not m.is_active else "")
             + (" (account inactive)" if not m.user.is_active else "")) for m in self.memberships
        ]
        self.initial["active_memberships"] = [str(m.pk) for m in self.memberships if m.is_active]
        self.fields["users"].queryset = CustomUser.objects.order_by("first_name", "last_name", "email")
        for field in self.fields.values():
            field.widget.attrs["class"] = "checkbox-input" if isinstance(field.widget, forms.CheckboxInput) else "form-control"

    def clean_new_people(self):
        rows = []
        seen = set()
        try:
            reader = csv.reader(StringIO(self.cleaned_data["new_people"]), strict=True)
            for row in reader:
                if not row or not any(part.strip() for part in row):
                    continue
                if len(row) > 3:
                    raise forms.ValidationError("Use email, first name, last name on each line.")
                email = forms.EmailField(max_length=150).clean(row[0].strip()).lower()
                if email in seen:
                    raise forms.ValidationError(f"{email} is listed more than once.")
                if CustomUser.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).exists():
                    raise forms.ValidationError(f"{email} already exists. Select them under existing users.")
                names = [part.strip() for part in row[1:]] + ["", ""]
                if any(len(part) > 150 for part in names):
                    raise forms.ValidationError("Names cannot exceed 150 characters.")
                seen.add(email)
                rows.append((email, names[0], names[1]))
        except csv.Error:
            raise forms.ValidationError("Use email, first name, last name on each line.")
        return rows

    def clean(self):
        data = super().clean()
        if (data.get("users") or data.get("new_people")) and not data.get("role"):
            self.add_error("role", "Choose a role for the people being added.")
        return data

    def save(self, scope, actor):
        selected = set(self.cleaned_data["active_memberships"])
        for membership in self.memberships:
            set_membership_active(membership, str(membership.pk) in selected, actor)
        users = list(self.cleaned_data["users"])
        for email, first, last in self.cleaned_data["new_people"]:
            user = CustomUser(username=email, email=email, first_name=first, last_name=last)
            user.set_unusable_password()
            user.save()
            log_change(actor, ChangeHistory.Action.CREATE, "User", str(user),
                       f"Created {user.email} while adding members to {scope.name}.",
                       entity_id=user.pk, details={"user_id": user.pk, "email": user.email,
                                                  "scope_type": scope._meta.model_name, "scope_id": scope.pk})
            users.append(user)
        for user in users:
            if not user.is_active and self.cleaned_data["reactivate_accounts"]:
                user.is_active = True
                user.save(update_fields=["is_active"])
                log_change(actor, ChangeHistory.Action.ACTIVATE, "User", str(user),
                           f"Reactivated account {user.email}.", entity_id=user.pk,
                           details={"user_id": user.pk, "before_active": False, "is_active": True})
            add_membership(scope, user, self.cleaned_data["role"], actor)
