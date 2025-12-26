# Excel-to-App Field Mapping (DIP Mentee Tracker)

Source file: `docs/DIP Mentee Tracker.xlsx`

This document maps every Excel column/section to a database field and UI surface. Items that are narrative/reference content are stored as admin-configured reference records.

## Objective sheet

| Excel section | Excel content | Database field/model | UI surface |
| --- | --- | --- | --- |
| Objective | Program objective statement text | `ReferenceContent.section="Objective"` + `ReferenceContent.content` | Django admin (Reference Content) |
| Goal | Goal statements (2 rows) | `ReferenceContent.section="Goal"` + `ReferenceContent.content` | Django admin (Reference Content) |
| Year/Topics | Year 1–3 domain names | `RatingDomain.year` + `RatingDomain.name` | Django admin (Rating Domains) |
| Year/Topics (parameters) | Indicators under each domain (1–3) | `DomainIndicator.domain` + `DomainIndicator.description` | Django admin (Domain Indicators) |
| Rating Scales | 1–5 definitions per domain | `RatingScaleDefinition.domain` + `RatingScaleDefinition.score` + `RatingScaleDefinition.description` | Django admin (Rating Scale Definitions) |
| Mood Assessment | Mood categories + descriptions + types | `MoodCategory.name` + `MoodCategory.description` + `MoodCategory.mood_types` | Django admin (Mood Categories) |
| Resources / References | Narrative resources and links | `ReferenceContent.section="Resources"`/`"References"` + `ReferenceContent.content` | Django admin (Reference Content) |

Note: The Objective sheet is narrative/reference data. It is represented in admin-configurable reference tables (not per-mentee records).

## Year 1–3 tracker sheets (per-session ratings)

These map to `Mentee`, `MenteeAssessment`, and `AssessmentRating` records.

| Excel column | Database field/model | UI surface |
| --- | --- | --- |
| Mentee Name | `Mentee.full_name` | Admin → Mentees |
| Mentor Name | `MenteeAssessment.mentor` | Mentor Assessments |
| Grade | `Mentee.grade` | Admin → Mentees |
| School | `Mentee.school` → `School.name` | Admin → Schools/Mentees |
| Summer Camp/Follow Up session | `MenteeAssessment.session_type` → `SessionType.name` | Mentor Assessments |
| Date | `MenteeAssessment.date` | Mentor Assessments |
| Theme/Topic | `MenteeAssessment.theme_topic` | Mentor Assessments |
| Beginning Mood | `MenteeAssessment.beginning_mood` | Mentor Assessments |
| End Mood | `MenteeAssessment.end_mood` | Mentor Assessments |
| Domain columns (Year-specific) | `AssessmentRating.domain` + `AssessmentRating.value` | Mentor Assessments |
| Average | Computed via `MenteeAssessment.average_score()` | Mentor/Mentee assessments list |
| Mentor Remarks | `MenteeAssessment.mentor_remarks` | Mentor Assessments |
| Action Plan | `MenteeAssessment.action_plan` | Mentor Assessments |

## Year 4

There is no Year 4 sheet in the source Excel file. The application supports Year 4 via `ProgramYear` choices and admin-configurable domains/templates. Admin must add Year 4 domains and templates in the UI.

## Objective tracking (per-mentee)

The project requirements include per-mentee objective tracking, which is not present as structured columns in the Excel file. This is implemented via `ObjectiveItem` and exposed in the mentee/mentor dashboards:

| Requirement field | Database field/model | UI surface |
| --- | --- | --- |
| Objective title/text | `ObjectiveItem.objective_title` / `ObjectiveItem.objective_text` | Mentee Objectives |
| Action items | `ObjectiveItem.action_items` | Mentee Objectives |
| Timeline | `ObjectiveItem.start_date`, `ObjectiveItem.end_date` | Mentee Objectives |
| Expected outcome | `ObjectiveItem.expected_outcome` | Mentee Objectives |
| Progress status | `ObjectiveItem.status` → `StatusConfig` | Mentee Objectives |
| Progress percent | `ObjectiveItem.progress_percent` | Mentee Objectives |
| Evidence | `ObjectiveItem.evidence` | Mentee Objectives |
| Mentee remarks | `ObjectiveItem.mentee_remarks` | Mentee Objectives |
| Mentor comments | `ObjectiveItem.mentor_comments` | Mentor Objectives |
| Approval | `ObjectiveItem.mentor_approved` + `ObjectiveItem.approved_at` | Mentor Objectives |
| Audit | `ObjectiveItem.created_by`/`updated_by` + timestamps | System |

## Year plan tracking (per-mentee)

Year plan milestones are implemented via `YearPlanItem` and exposed in the mentee/mentor dashboards:

| Requirement field | Database field/model | UI surface |
| --- | --- | --- |
| Year number | `YearPlanItem.year` | Mentee Year Plans |
| Milestone / deliverable | `YearPlanItem.milestone` / `YearPlanItem.deliverable` | Mentee Year Plans |
| Target date / period | `YearPlanItem.target_date` / `YearPlanItem.target_period` | Mentee Year Plans |
| Status | `YearPlanItem.status` → `StatusConfig` | Mentee Year Plans |
| Remarks | `YearPlanItem.remarks` | Mentee Year Plans |
| Mentor comments | `YearPlanItem.mentor_comments` | Mentor Year Plans |
| Review date | `YearPlanItem.review_date` | Mentor Year Plans |
| Audit | `YearPlanItem.created_by`/`updated_by` + timestamps | System |
