"""
Quick script to check advisor/teacher/lesson data
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from accounts.models import User
from core.models import Lesson

print("\n=== ADVISORS ===")
advisors = User.objects.filter(role='advisor')
for advisor in advisors:
    print(f"- {advisor.username} | School: {advisor.school} | Subject: {advisor.subjects}")

print("\n=== TEACHERS ===")
teachers = User.objects.filter(role='teacher')
for teacher in teachers:
    print(f"- {teacher.username} | School: {teacher.school} | Subjects: {teacher.subjects}")

print("\n=== LESSONS ===")
lessons = Lesson.objects.all()
for lesson in lessons:
    print(f"- {lesson.title} | Subject: {lesson.subject} | School: {lesson.school} | Created by: {lesson.created_by.username} ({lesson.created_by.role})")

print("\n=== MATCHING LOGIC ===")
for advisor in advisors:
    advisor_subject = advisor.subjects[0] if advisor.subjects else None
    print(f"\nAdvisor: {advisor.username}")
    print(f"  Subject: {advisor_subject}")
    print(f"  School: {advisor.school}")
    
    if advisor_subject:
        matching_lessons = Lesson.objects.filter(
            school=advisor.school,
            subject=advisor_subject,
            created_by__role='teacher'
        )
        print(f"  Matching lessons: {matching_lessons.count()}")
        for lesson in matching_lessons:
            print(f"    - {lesson.title} by {lesson.created_by.username}")
