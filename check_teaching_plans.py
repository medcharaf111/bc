"""
Quick script to check teaching plans data
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from accounts.models import User
from core.models import TeachingPlan

print("\n=== ADVISORS ===")
advisors = User.objects.filter(role='advisor')
for advisor in advisors:
    print(f"- {advisor.username} | School: {advisor.school} | Subject: {advisor.subjects}")

print("\n=== TEACHERS ===")
teachers = User.objects.filter(role='teacher')
for teacher in teachers:
    print(f"- {teacher.username} | School: {teacher.school} | Subjects: {teacher.subjects}")

print("\n=== TEACHING PLANS ===")
plans = TeachingPlan.objects.all()
print(f"Total plans: {plans.count()}")
for plan in plans:
    print(f"- {plan.title} | Subject: {plan.subject} | Teacher: {plan.teacher.username} | Date: {plan.date} | Time: {plan.time}")

print("\n=== MATCHING LOGIC FOR ADVISORS ===")
for advisor in advisors:
    advisor_subject = advisor.subjects[0] if advisor.subjects and len(advisor.subjects) > 0 else None
    print(f"\nAdvisor: {advisor.username}")
    print(f"  Subject: {advisor_subject}")
    print(f"  School: {advisor.school}")
    
    if advisor_subject:
        # Get teachers with matching subject and school
        all_teachers = User.objects.filter(
            role='teacher',
            school=advisor.school
        )
        # Filter teachers who have the advisor's subject in their subjects list
        matching_teachers = [t for t in all_teachers if advisor_subject in (t.subjects or [])]
        print(f"  Matching teachers: {len(matching_teachers)}")
        for teacher in matching_teachers:
            print(f"    - {teacher.username} (subjects: {teacher.subjects})")
            teacher_plans = TeachingPlan.objects.filter(teacher=teacher).count()
            print(f"      Plans: {teacher_plans}")
