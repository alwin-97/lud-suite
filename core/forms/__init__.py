from core.forms.base import StyledModelForm
from core.forms.configuration import (
    ChapterForm,
    CohortActivityForm,
    CohortForm,
    CohortMemberForm,
    CohortMemberReallocateForm,
    LocationForm,
    MentorAssignmentForm,
    ProgramForm,
    TermForm,
    TermResourceForm,
)
from core.forms.reports import UserActivityReportForm, UserActivityReportReviewForm
from core.forms.tasks_questions import (
    QuestionResponseForm,
    QuestionResponseReviewForm,
    TaskSubmissionForm,
    TaskSubmissionReviewForm,
    TermQuestionForm,
    TermTaskForm,
)
from core.forms.users import PlatformUserForm

__all__ = [
    "ChapterForm",
    "CohortActivityForm",
    "CohortForm",
    "CohortMemberForm",
    "CohortMemberReallocateForm",
    "LocationForm",
    "MentorAssignmentForm",
    "PlatformUserForm",
    "ProgramForm",
    "QuestionResponseForm",
    "QuestionResponseReviewForm",
    "StyledModelForm",
    "TaskSubmissionForm",
    "TaskSubmissionReviewForm",
    "TermForm",
    "TermQuestionForm",
    "TermResourceForm",
    "TermTaskForm",
    "UserActivityReportForm",
    "UserActivityReportReviewForm",
]
