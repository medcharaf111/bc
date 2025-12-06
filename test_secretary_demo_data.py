"""
Demo script to create Secretary General user and sample admin workflow data.
Run with: python manage.py shell < backend/test_secretary_demo_data.py
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "native_os.settings")
django.setup()

from accounts.models import User, School

# 1) get or create a school (reuse pattern from other test scripts)
school = School.objects.first()
if not school:
    school = School.objects.create(
        name="Demo Secretary School",
        address="Demo Address 123",
    )

# 2) create secretary general user
secretary, created = User.objects.get_or_create(
    username="demo_secretary",
    defaults={
        "email": "secretary@example.com",
        "role": "secretary_general",
        "school": school,
        "first_name": "Demo",
        "last_name": "Secretary",
    },
)
if created:
    secretary.set_password("test123")
    secretary.save()

print("\n" + "=" * 60)
print("Secretary General demo user")
print("=" * 60)
print(f"Username: {secretary.username}")
print(f"Role: {secretary.role}")
print(f"School: {school.name}")
print("=" * 60 + "\n")

# 3) here you later add:
#    - MinisterialDecision objects
#    - Meetings
#    - Priority tasks
# using the models file where you decide to place them (e.g. core/models.py)

print("✅ Secretary General demo user created. Now implement models/endpoints for:")
print("   - decisions, documents, meetings, priority tasks")