"""
Populate mock data for Secretary Dashboard (tasks, meetings, decisions, documents).
Run:
  python manage.py shell < backend/create_secretary_mock_data.py
"""
import os
import django
from datetime import date, datetime, timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "native_os.settings")
django.setup()

from accounts.models import User, School, Task, Meeting, Decision, Document

# Ensure a school exists
school = School.objects.first() or School.objects.create(name="Central School", address="HQ")

# Get or create secretary
secretary, _ = User.objects.get_or_create(
    username="demo_secretary",
    defaults={
        "email": "secretary@example.com",
        "role": "secretary",
        "school": school,
        "first_name": "Demo",
        "last_name": "Secretary",
    },
)
if not secretary.password:
    secretary.set_password("test123")
    secretary.save()

# Clear previous mock data (optional)
Task.objects.filter(created_by=secretary).delete()
Meeting.objects.filter(created_by=secretary).delete()
Decision.objects.filter(created_by=secretary).delete()
Document.objects.filter(created_by=secretary).delete()

# Tasks
Task.objects.bulk_create([
    Task(title="Approve 2025 digitization roadmap", owner="IT Directorate", priority="high", status="in_progress", due_date=date.today()+timedelta(days=3), tags=["roadmap","2025"], created_by=secretary),
    Task(title="Remind delegations about safety reports", owner="Minister's Office", priority="medium", status="not_started", due_date=date.today()+timedelta(days=1), tags=["safety"], created_by=secretary),
    Task(title="Finalize ISP agreement for rural connectivity", owner="Partnerships", priority="high", status="overdue", due_date=date.today()-timedelta(days=5), tags=["connectivity"], created_by=secretary),
])

# Meetings
Meeting.objects.bulk_create([
    Meeting(title="Weekly coordination", organizer="Secretary General", meeting_type="Coordination", meeting_date=datetime.now()+timedelta(days=2, hours=2), status="scheduled", followup_completed=False, created_by=secretary),
    Meeting(title="Exam readiness follow-up", organizer="Minister", meeting_type="Strategic", meeting_date=datetime.now()-timedelta(days=1), status="followup_pending", followup_completed=False, created_by=secretary),
    Meeting(title="Digital transformation review", organizer="Secretary General", meeting_type="Project", meeting_date=datetime.now()-timedelta(days=4), status="completed", followup_completed=True, created_by=secretary),
])

# Decisions
Decision.objects.bulk_create([
    Decision(ref="D-2025-001", title="Nationwide student file digitization", sector="Secondary Education", unit="IT Directorate", deadline=date(2025,12,31), status="in_implementation", progress=60, created_by=secretary),
    Decision(ref="D-2025-015", title="AI pedagogy teacher training", sector="Primary Education", unit="Training Directorate", deadline=date(2025,7,15), status="overdue", progress=40, created_by=secretary),
    Decision(ref="D-2024-099", title="National exam system review", sector="Secondary Education", unit="Exams Directorate", deadline=date(2024,9,30), status="completed", progress=100, created_by=secretary),
])

# Documents
Document.objects.bulk_create([
    Document(ref="DOC-2025-1001", document_type="Complaint", origin="Tunis Delegation 1", stage="processing", deadline=date.today()+timedelta(days=5), is_urgent=True, created_by=secretary),
    Document(ref="DOC-2025-1002", document_type="Funding Request", origin="Ariana Primary School", stage="waiting_signature", deadline=date.today()+timedelta(days=3), is_urgent=False, created_by=secretary),
    Document(ref="DOC-2025-1003", document_type="Inspection Report", origin="Sfax Inspection Service", stage="received", deadline=date.today()+timedelta(days=8), is_urgent=False, created_by=secretary),
])

print("\n✅ Secretary mock data created for user demo_secretary (password: test123)")
print("   - Tasks, Meetings, Decisions, Documents ready to test API.")
