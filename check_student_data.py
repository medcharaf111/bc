import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from accounts.models import User
from datetime import date

# Get all students
students = User.objects.filter(role='student', is_active=True).select_related('school')
print(f"\n{'='*60}")
print(f"STUDENT DATA CHECK")
print(f"{'='*60}\n")

print(f"Total Students: {students.count()}\n")

# Check date_of_birth
students_with_dob = students.filter(date_of_birth__isnull=False)
students_without_dob = students.filter(date_of_birth__isnull=True)

print(f"Students WITH date_of_birth: {students_with_dob.count()}")
print(f"Students WITHOUT date_of_birth: {students_without_dob.count()}\n")

# Check gender
students_with_gender = students.exclude(gender__isnull=True)
students_without_gender = students.filter(gender__isnull=True)

print(f"Students WITH gender: {students_with_gender.count()}")
print(f"Students WITHOUT gender: {students_without_gender.count()}\n")

# Check grade_level
students_with_grade = students.exclude(grade_level__isnull=True)
students_without_grade = students.filter(grade_level__isnull=True)

print(f"Students WITH grade_level: {students_with_grade.count()}")
print(f"Students WITHOUT grade_level: {students_without_grade.count()}\n")

# Sample students with all data
print(f"{'='*60}")
print(f"SAMPLE STUDENTS (First 5 with complete data)")
print(f"{'='*60}\n")

complete_students = students.filter(
    date_of_birth__isnull=False,
    gender__isnull=False,
    grade_level__isnull=False
)[:5]

for student in complete_students:
    today = date.today()
    age = today.year - student.date_of_birth.year - ((today.month, today.day) < (student.date_of_birth.month, student.date_of_birth.day))
    gender_display = 'Male' if student.gender == 'M' else 'Female'
    region = student.school.delegation if student.school and student.school.delegation else 'N/A'
    
    print(f"Username: {student.username}")
    print(f"  Age: {age} years (DOB: {student.date_of_birth})")
    print(f"  Gender: {gender_display}")
    print(f"  Grade: {student.grade_level}")
    print(f"  Region: {region}")
    print(f"  School: {student.school.name if student.school else 'N/A'}")
    print()

# Check regions
print(f"{'='*60}")
print(f"REGIONS/DELEGATIONS")
print(f"{'='*60}\n")

regions = {}
for student in students:
    region = student.school.delegation if student.school and student.school.delegation else 'N/A'
    if region not in regions:
        regions[region] = 0
    regions[region] += 1

for region, count in sorted(regions.items(), key=lambda x: x[1], reverse=True):
    print(f"{region}: {count} students")
