"""
Seed configuration data for the LUD Suite.

Usage:
    python manage.py seed_config_data

All records use get_or_create / update_or_create so the command is
idempotent – running it multiple times will never create duplicates.
"""

from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import (
    AcademicCycle,
    Chapter,
    DomainIndicator,
    Location,
    MoodCategory,
    Programme,
    RatingDomain,
    RatingScaleDefinition,
    ReferenceContent,
    School,
    SessionType,
    StatusConfig,
    TemplateConfig,
)


class Command(BaseCommand):
    help = "Populate configuration seed data (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        self._seed_schools()
        self._seed_locations()
        self._seed_chapters()
        self._seed_academic_cycles()
        self._seed_programmes()
        self._seed_statuses()
        self._seed_session_types()
        self._seed_rating_domains()
        self._seed_domain_indicators()
        self._seed_rating_scales()
        self._seed_mood_categories()
        self._seed_reference_content()
        self._seed_template_configs()
        self.stdout.write(self.style.SUCCESS("Seed data populated successfully."))

    # ------------------------------------------------------------------
    # 1) Schools
    # ------------------------------------------------------------------
    def _seed_schools(self):
        names = ["Christ Vidyalaya", "Christ CBSE"]
        for name in names:
            School.objects.get_or_create(name=name)
        self.stdout.write(f"  Schools: {len(names)}")

    # ------------------------------------------------------------------
    # 2) Locations
    # ------------------------------------------------------------------
    def _seed_locations(self):
        items = [
            ("Pune", "LUD-PUN"),
            ("Bengaluru", "LUD-BLR"),
            ("Lavasa", "LUD-LAV"),
            ("Mumbai", "LUD-MUM"),
            ("Delhi", "LUD-DEL"),
            ("Hyderabad", "LUD-HYD"),
            ("Chennai", "LUD-CHE"),
        ]
        for name, code in items:
            Location.objects.update_or_create(
                code=code,
                defaults={"name": name, "is_active": True},
            )
        self.stdout.write(f"  Locations: {len(items)}")

    # ------------------------------------------------------------------
    # 3) Chapters
    # ------------------------------------------------------------------
    def _seed_chapters(self):
        chapter_map = {
            "Christ Vidyalaya": [
                ("Christ Vidyalaya \u2013 Chapter 1", "CV-01"),
                ("Christ Vidyalaya \u2013 Chapter 2", "CV-02"),
                ("Christ Vidyalaya \u2013 Chapter 3", "CV-03"),
            ],
            "Christ CBSE": [
                ("Christ CBSE \u2013 Chapter 1", "CBSE-01"),
                ("Christ CBSE \u2013 Chapter 2", "CBSE-02"),
                ("Christ CBSE \u2013 Chapter 3", "CBSE-03"),
            ],
        }
        count = 0
        for school_name, chapters in chapter_map.items():
            school = School.objects.filter(name=school_name).first()
            if not school:
                continue
            for ch_name, ch_code in chapters:
                Chapter.objects.update_or_create(
                    school=school,
                    name=ch_name,
                    defaults={"code": ch_code, "is_active": True},
                )
                count += 1
        self.stdout.write(f"  Chapters: {count}")

    # ------------------------------------------------------------------
    # 4) Academic Cycles
    # ------------------------------------------------------------------
    def _seed_academic_cycles(self):
        cycles = [
            ("2025\u20132026", date(2025, 6, 1), date(2026, 5, 31), True),
            ("2026\u20132027", date(2026, 6, 1), date(2027, 5, 31), True),
            ("2027\u20132028", date(2027, 6, 1), date(2028, 5, 31), False),
        ]
        for label, start, end, active in cycles:
            AcademicCycle.objects.update_or_create(
                year_label=label,
                defaults={"start_date": start, "end_date": end, "is_active": active},
            )
        self.stdout.write(f"  Academic Cycles: {len(cycles)}")

    # ------------------------------------------------------------------
    # 5) Programmes
    # ------------------------------------------------------------------
    def _seed_programmes(self):
        items = [
            ("Let Us Dream", "LUD", "Core mentoring programme for holistic student development."),
            ("DREAMS Intervention Program (DIP)", "DIP", "Structured intervention programme for mentee empowerment."),
            ("YCLP", "YCLP", "Youth Community Leadership Programme."),
            ("DIP\u2013LUD Integrated Mentoring", "DIP-LUD", "Integrated programme combining DIP and LUD methodologies."),
            ("DIP\u2013YCLP Reflective Reporting", "DIP-YCLP", "Combined reflective reporting for DIP and YCLP activities."),
        ]
        for name, code, desc in items:
            Programme.objects.update_or_create(
                name=name,
                defaults={"code": code, "description": desc, "is_active": True},
            )
        self.stdout.write(f"  Programmes: {len(items)}")

    # ------------------------------------------------------------------
    # 6) Statuses
    # ------------------------------------------------------------------
    def _seed_statuses(self):
        items = [
            # Record / Assessment statuses
            ("Draft", "secondary", 1),
            ("Submitted", "info", 2),
            ("Under Community Leader Review", "warning", 3),
            ("Under Faculty Leader Review", "warning", 4),
            ("Approved", "success", 5),
            ("Returned for Revision", "danger", 6),
            ("Rejected", "danger", 7),
            ("Locked", "dark", 8),
            ("Archived", "secondary", 9),
            # Action statuses
            ("Not Started", "secondary", 10),
            ("In Progress", "primary", 11),
            ("Partial", "info", 12),
            ("Completed", "success", 13),
            ("Overdue", "danger", 14),
            # User statuses
            ("Active", "success", 15),
            ("Inactive", "secondary", 16),
            ("Suspended", "danger", 17),
            # Legacy (keep existing)
            ("On Hold", "warning", 18),
            ("Delayed", "danger", 19),
        ]
        for name, color, ordering in items:
            StatusConfig.objects.update_or_create(
                name=name,
                defaults={"color": color, "ordering": ordering, "is_active": True},
            )
        self.stdout.write(f"  Statuses: {len(items)}")

    # ------------------------------------------------------------------
    # 7) Session Types
    # ------------------------------------------------------------------
    def _seed_session_types(self):
        names = [
            "Summer Camp",
            "Follow Up Session",
            "Mentoring Session",
            "Group Session",
            "One-to-One Session",
            "Review Session",
            "Reflection Session",
            "Leadership Session",
            "Community Session",
        ]
        for name in names:
            SessionType.objects.get_or_create(name=name, defaults={"is_active": True})
        self.stdout.write(f"  Session Types: {len(names)}")

    # ------------------------------------------------------------------
    # 8) Rating Domains
    # ------------------------------------------------------------------
    def _seed_rating_domains(self):
        tracker_domains = {
            1: [
                "Session Engagement",
                "Self-Awareness and Growth",
                "Emotional and Behavioral Regulation",
                "Initiative and Responsibility",
                "Mentorship and Reflection",
            ],
            2: [
                "Receiving Feedback",
                "Help-Seeking Behavior",
                "Team Work",
                "Respect",
                "Accountability",
            ],
            3: [
                "Leadership Management",
                "Decision Making",
                "Time Management",
                "Value-Based Action",
                "Conflict Navigation",
            ],
        }
        count = 0
        for year, names in tracker_domains.items():
            for idx, name in enumerate(names, start=1):
                RatingDomain.objects.update_or_create(
                    year=year,
                    name=name,
                    defaults={"source": "tracker", "sort_order": idx, "is_active": True},
                )
                count += 1
        self.stdout.write(f"  Rating Domains: {count}")

    # ------------------------------------------------------------------
    # 9) Domain Indicators
    # ------------------------------------------------------------------
    def _seed_domain_indicators(self):
        indicators_map = {
            # Year 1
            (1, "Session Engagement"): [
                "Participates actively in discussions",
                "Listens attentively during sessions",
                "Responds to mentor prompts",
                "Shows interest in activities",
            ],
            (1, "Self-Awareness and Growth"): [
                "Can reflect on personal strengths",
                "Identifies areas for self-improvement",
                "Shows awareness of behaviour and choices",
            ],
            (1, "Emotional and Behavioral Regulation"): [
                "Manages emotions appropriately",
                "Responds calmly to situations",
                "Demonstrates self-control",
            ],
            (1, "Initiative and Responsibility"): [
                "Takes ownership of assigned tasks",
                "Follows through on commitments",
                "Shows willingness to contribute",
            ],
            (1, "Mentorship and Reflection"): [
                "Responds thoughtfully to mentor guidance",
                "Reflects on session learning",
                "Demonstrates openness to growth",
            ],
            # Year 2
            (2, "Receiving Feedback"): [
                "Accepts feedback without defensiveness",
                "Applies suggestions constructively",
            ],
            (2, "Help-Seeking Behavior"): [
                "Asks for guidance when needed",
                "Reaches out appropriately for support",
            ],
            (2, "Team Work"): [
                "Collaborates respectfully with peers",
                "Contributes to group tasks",
            ],
            (2, "Respect"): [
                "Shows respect to mentors and peers",
                "Demonstrates appropriate conduct",
            ],
            (2, "Accountability"): [
                "Takes responsibility for actions",
                "Completes agreed responsibilities",
            ],
            # Year 3
            (3, "Leadership Management"): [
                "Takes initiative in leading tasks",
                "Supports peers positively",
            ],
            (3, "Decision Making"): [
                "Makes thoughtful choices",
                "Considers consequences before acting",
            ],
            (3, "Time Management"): [
                "Completes work on time",
                "Prioritizes tasks effectively",
            ],
            (3, "Value-Based Action"): [
                "Demonstrates integrity in actions",
                "Applies programme values consistently",
            ],
            (3, "Conflict Navigation"): [
                "Handles disagreements constructively",
                "Seeks peaceful resolution",
            ],
        }
        count = 0
        for (year, domain_name), descs in indicators_map.items():
            domain = RatingDomain.objects.filter(year=year, name=domain_name).first()
            if not domain:
                continue
            for idx, desc in enumerate(descs, start=1):
                _, created = DomainIndicator.objects.get_or_create(
                    domain=domain,
                    sort_order=idx,
                    defaults={"description": desc},
                )
                if not created:
                    # Update description if record already exists
                    DomainIndicator.objects.filter(domain=domain, sort_order=idx).update(description=desc)
                count += 1
        self.stdout.write(f"  Domain Indicators: {count}")

    # ------------------------------------------------------------------
    # 10) Rating Scales (per-domain Likert definitions)
    # ------------------------------------------------------------------
    def _seed_rating_scales(self):
        scale = [
            (1, "Strongly Disagree"),
            (2, "Disagree"),
            (3, "Neutral"),
            (4, "Agree"),
            (5, "Strongly Agree"),
        ]
        count = 0
        for domain in RatingDomain.objects.filter(is_active=True):
            for score, desc in scale:
                RatingScaleDefinition.objects.update_or_create(
                    domain=domain,
                    score=score,
                    defaults={"description": desc},
                )
                count += 1
        self.stdout.write(f"  Rating Scale Definitions: {count}")

    # ------------------------------------------------------------------
    # 11) Mood Categories
    # ------------------------------------------------------------------
    def _seed_mood_categories(self):
        items = [
            ("Happy", "Positive", "positive", 1),
            ("Calm", "Feeling relaxed and at ease", "positive", 2),
            ("Excited", "Enthusiastic and energised", "positive", 3),
            ("Motivated", "Driven and determined", "positive", 4),
            ("Hopeful", "Optimistic about the future", "positive", 5),
            ("Neutral", "Neither positive nor negative", "neutral", 6),
            ("Tired", "Low energy or fatigued", "concern", 7),
            ("Anxious", "Feeling worried or uneasy", "concern", 8),
            ("Confused", "Uncertain or unclear", "concern", 9),
            ("Sad", "Feeling down or unhappy", "distress", 10),
            ("Frustrated", "Feeling blocked or annoyed", "distress", 11),
            ("Withdrawn", "Disengaged or pulling back", "distress", 12),
        ]
        for name, desc, mood_type, order in items:
            MoodCategory.objects.update_or_create(
                name=name,
                defaults={
                    "description": desc,
                    "mood_types": mood_type,
                    "sort_order": order,
                },
            )
        self.stdout.write(f"  Mood Categories: {len(items)}")

    # ------------------------------------------------------------------
    # 12) Reference Content
    # ------------------------------------------------------------------
    def _seed_reference_content(self):
        items = [
            # Topic Materials
            ("Topic Materials", "Leader of Your Life", "Empowering mentees to take charge of their personal growth and development.", 1),
            ("Topic Materials", "You & Your Community", "Understanding the role of community involvement and social responsibility.", 2),
            ("Topic Materials", "Self-Awareness", "Developing self-knowledge, recognising strengths and areas for growth.", 3),
            ("Topic Materials", "Emotional Regulation", "Strategies for managing emotions and responding constructively.", 4),
            ("Topic Materials", "Teamwork and Respect", "Building collaborative skills and mutual respect within groups.", 5),
            ("Topic Materials", "Leadership and Responsibility", "Developing leadership qualities and taking initiative.", 6),
            ("Topic Materials", "Decision Making", "Making thoughtful, informed decisions and considering consequences.", 7),
            ("Topic Materials", "Time Management", "Prioritising tasks and managing time effectively.", 8),
            ("Topic Materials", "Conflict Navigation", "Handling disagreements constructively and seeking resolution.", 9),
            # Orientation Content
            ("Orientation", "What is Mentoring?", "An overview of the mentoring relationship, its purpose, and expected benefits.", 10),
            ("Orientation", "What to Expect from Mentoring", "Setting expectations for both mentors and mentees in the programme.", 11),
            ("Orientation", "Roles of Mentor and Mentee", "Defining responsibilities and boundaries for effective mentoring.", 12),
            ("Orientation", "Session Participation Guidelines", "Guidelines for active, respectful participation in sessions.", 13),
            ("Orientation", "Reflection Writing Guide", "How to write meaningful reflections on session experiences.", 14),
            # Volunteer Guidance
            ("Volunteer Guidance", "Reflective Reporting Guide", "Instructions for completing reflective reports after activities.", 15),
            ("Volunteer Guidance", "Work Diary Instructions", "How to maintain an accurate and useful work diary.", 16),
            ("Volunteer Guidance", "Volunteer Transcript Criteria", "Criteria and standards for volunteer transcript evaluation.", 17),
        ]
        for section, title, content, order in items:
            ReferenceContent.objects.update_or_create(
                section=section,
                title=title,
                defaults={"content": content, "sort_order": order},
            )
        self.stdout.write(f"  Reference Content: {len(items)}")

    # ------------------------------------------------------------------
    # 13) Template Configs
    # ------------------------------------------------------------------
    def _seed_template_configs(self):
        templates = [
            # Mentee Tracker templates
            (
                "Year 1 Mentee Tracker",
                "year_plan",
                1,
                {
                    "fields": [
                        "mentee_name", "mentor_name", "grade", "school",
                        "session_type", "date", "theme_topic",
                        "beginning_mood", "end_mood",
                        "session_engagement", "self_awareness_and_growth",
                        "emotional_and_behavioral_regulation",
                        "initiative_and_responsibility",
                        "mentorship_and_reflection",
                        "average", "mentor_remarks", "action_plan",
                    ],
                },
            ),
            (
                "Year 2 Mentee Tracker",
                "year_plan",
                2,
                {
                    "fields": [
                        "mentee_name", "mentor_name", "grade", "school",
                        "session_type", "date", "theme_topic",
                        "beginning_mood", "end_mood",
                        "receiving_feedback", "help_seeking_behavior",
                        "team_work", "respect", "accountability",
                        "average", "mentor_remarks", "action_plan",
                    ],
                },
            ),
            (
                "Year 3 Mentee Tracker",
                "year_plan",
                3,
                {
                    "fields": [
                        "mentee_name", "mentor_name", "grade", "school",
                        "session_type", "date", "theme_topic",
                        "beginning_mood", "end_mood",
                        "leadership_management", "decision_making",
                        "time_management", "value_based_action",
                        "conflict_navigation",
                        "average", "mentor_remarks", "action_plan",
                    ],
                },
            ),
            # Objective templates
            (
                "DIP Reflective Report",
                "objective",
                None,
                {
                    "fields": [
                        "name", "email", "register_number", "class", "date",
                        "duration", "activity_event", "programme",
                        "reflection_learning", "evidence_upload",
                        "endorser_name", "endorser_remarks",
                        "suggestions_feedback",
                    ],
                },
            ),
            (
                "YCLP Reflective Report",
                "objective",
                None,
                {
                    "fields": [
                        "name", "email", "register_number", "class", "date",
                        "duration", "activity_event", "programme",
                        "reflection_learning", "evidence_upload",
                        "endorser_name", "endorser_remarks",
                        "suggestions_feedback",
                    ],
                },
            ),
            (
                "Volunteer Transcript Template",
                "objective",
                None,
                {
                    "fields": [
                        "volunteer_name", "template_choice",
                        "generated_summary", "reviewer_notes",
                        "approval_status",
                    ],
                },
            ),
            (
                "Work Diary Template",
                "objective",
                None,
                {
                    "fields": [
                        "date", "duration", "location", "linked_activity",
                        "narrative_entry", "review_status",
                    ],
                },
            ),
        ]
        count = 0
        for name, scope, year, fields_config in templates:
            TemplateConfig.objects.update_or_create(
                scope=scope,
                year=year,
                name=name,
                defaults={"fields_config": fields_config, "is_active": True},
            )
            count += 1
        self.stdout.write(f"  Template Configs: {count}")
