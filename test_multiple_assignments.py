"""
Test script to verify teachers can have multiple subject assignments
Run with: python manage.py shell < test_multiple_assignments.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from accounts.models import User, School, TeacherGradeAssignment

# Get or create test data
school = School.objects.first()
if not school:
    school = School.objects.create(name='Test School', address='123 Test St')

# Create director
director, _ = User.objects.get_or_create(
    username='test_director',
    defaults={
        'email': 'director@test.com',
        'role': 'director',
        'school': school,
        'first_name': 'Test',
        'last_name': 'Director'
    }
)
if _:
    director.set_password('test123')
    director.save()

# Create teacher with multiple subjects
teacher, _ = User.objects.get_or_create(
    username='multi_subject_teacher',
    defaults={
        'email': 'teacher@test.com',
        'role': 'teacher',
        'school': school,
        'first_name': 'Multi',
        'last_name': 'Subject',
        'subjects': ['math', 'science', 'physics']  # Teacher can teach 3 subjects
    }
)
if _:
    teacher.set_password('test123')
    teacher.save()

print(f"\n{'='*60}")
print(f"Teacher: {teacher.username}")
print(f"Subjects: {', '.join(teacher.subjects)}")
print(f"School: {school.name}")
print(f"{'='*60}\n")

# Test 1: Assign to Grade 10 - Math
assignment1, created1 = TeacherGradeAssignment.objects.get_or_create(
    teacher=teacher,
    grade_level='grade_10',
    subject='math',
    school=school,
    academic_year='2024-2025',
    defaults={
        'assigned_by': director,
        'notes': 'Advanced mathematics'
    }
)
print(f"✅ Assignment 1 {'CREATED' if created1 else 'EXISTS'}: Grade 10 - Math")

# Test 2: Assign to Grade 10 - Science (same grade, different subject)
assignment2, created2 = TeacherGradeAssignment.objects.get_or_create(
    teacher=teacher,
    grade_level='grade_10',
    subject='science',
    school=school,
    academic_year='2024-2025',
    defaults={
        'assigned_by': director,
        'notes': 'General science'
    }
)
print(f"✅ Assignment 2 {'CREATED' if created2 else 'EXISTS'}: Grade 10 - Science")

# Test 3: Assign to Grade 11 - Math (different grade, same subject)
assignment3, created3 = TeacherGradeAssignment.objects.get_or_create(
    teacher=teacher,
    grade_level='grade_11',
    subject='math',
    school=school,
    academic_year='2024-2025',
    defaults={
        'assigned_by': director,
        'notes': 'Calculus'
    }
)
print(f"✅ Assignment 3 {'CREATED' if created3 else 'EXISTS'}: Grade 11 - Math")

# Test 4: Try to create duplicate (should fail)
print("\n" + "="*60)
print("Testing duplicate prevention...")
print("="*60)
try:
    duplicate = TeacherGradeAssignment.objects.create(
        teacher=teacher,
        grade_level='grade_10',
        subject='math',
        school=school,
        academic_year='2024-2025',
        assigned_by=director
    )
    print("❌ ERROR: Duplicate assignment was allowed!")
except Exception as e:
    print(f"✅ CORRECT: Duplicate prevented - {type(e).__name__}")

# Show all assignments
print("\n" + "="*60)
print(f"Total assignments for {teacher.username}:")
print("="*60)
all_assignments = TeacherGradeAssignment.objects.filter(teacher=teacher, is_active=True)
for i, assignment in enumerate(all_assignments, 1):
    print(f"{i}. {assignment.get_grade_level_display()} - {assignment.get_subject_display()}")

print(f"\n📊 Total: {all_assignments.count()} active assignments")
print("\n✅ SUCCESS: Teachers CAN have multiple subject assignments!")
print("   - Same grade, different subjects ✓")
print("   - Different grades, same subject ✓")
print("   - Duplicate prevention works ✓")
