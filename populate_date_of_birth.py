import os
import django
import random
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from accounts.models import User

def calculate_birth_year_from_grade(grade_level):
    """
    Calculate typical birth year based on grade level.
    In Tunisia, school year 2025-2026:
    - Grade 1 (6-7 years old): born 2018-2019
    - Grade 2 (7-8 years old): born 2017-2018
    - ...
    - Grade 12 (17-18 years old): born 2007-2008
    """
    current_year = 2025
    grade_num = int(grade_level)
    typical_age = 5 + grade_num  # Grade 1 = 6 years old, Grade 12 = 17 years old
    birth_year = current_year - typical_age
    return birth_year

def generate_date_of_birth(grade_level):
    """Generate a random date of birth appropriate for the grade level."""
    birth_year = calculate_birth_year_from_grade(grade_level)
    
    # Add some variance (+/- 1 year)
    birth_year += random.choice([-1, 0, 1])
    
    # Random month and day
    month = random.randint(1, 12)
    if month in [1, 3, 5, 7, 8, 10, 12]:
        day = random.randint(1, 31)
    elif month in [4, 6, 9, 11]:
        day = random.randint(1, 30)
    else:  # February
        day = random.randint(1, 28)
    
    return date(birth_year, month, day)

print("\n" + "="*60)
print("POPULATING DATE OF BIRTH FOR STUDENTS")
print("="*60 + "\n")

# Get all students with grade_level
students = User.objects.filter(role='student', is_active=True, grade_level__isnull=False)
print(f"Found {students.count()} students with grade levels.\n")

random.seed(42)  # For reproducibility

updated_count = 0
for student in students:
    dob = generate_date_of_birth(student.grade_level)
    student.date_of_birth = dob
    student.save()
    updated_count += 1
    
    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    
    if updated_count <= 10:  # Show first 10 as samples
        print(f"{student.username}: Grade {student.grade_level} → Age {age} (DOB: {dob})")

print(f"\n✓ Updated {updated_count} students with date_of_birth!")

# Show age distribution
print("\n" + "="*60)
print("AGE DISTRIBUTION")
print("="*60 + "\n")

from collections import defaultdict
age_dist = defaultdict(int)

for student in students:
    if student.date_of_birth:
        today = date.today()
        age = today.year - student.date_of_birth.year - ((today.month, today.day) < (student.date_of_birth.month, student.date_of_birth.day))
        age_dist[age] += 1

for age in sorted(age_dist.keys()):
    print(f"Age {age}: {age_dist[age]} students")

print(f"\n✓ Complete!")
