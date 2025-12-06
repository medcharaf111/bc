"""
Populate grade_level and gender fields for existing students
- Assigns random grade levels (1-12)
- Within each grade, assigns 50% male, 50% female (matching your example: 6th grade = 50% male, rest female)
"""
import os
import django
import random

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from accounts.models import User

def populate_student_data():
    """Populate grade_level and gender for all students"""
    students = User.objects.filter(role='student')
    total_students = students.count()
    
    if total_students == 0:
        print("No students found.")
        return
    
    print(f"Found {total_students} students.")
    
    # Step 1: Assign random grade levels
    print("\nStep 1: Assigning grade levels...")
    grade_levels = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']
    
    for student in students:
        if not student.grade_level:
            student.grade_level = random.choice(grade_levels)
            student.save()
    
    print("Grade levels assigned!")
    
    # Step 2: Assign gender 50/50 within each grade
    print("\nStep 2: Assigning gender (50% male, 50% female per grade)...")
    
    for grade in grade_levels:
        grade_students = list(User.objects.filter(role='student', grade_level=grade, gender__isnull=True))
        count = len(grade_students)
        
        if count == 0:
            continue
        
        # Calculate 50/50 split
        male_count = count // 2
        female_count = count - male_count
        
        # Create shuffled list of genders
        genders = ['M'] * male_count + ['F'] * female_count
        random.shuffle(genders)
        
        # Assign genders
        for student, gender in zip(grade_students, genders):
            student.gender = gender
            student.save()
        
        print(f"Grade {grade}: {count} students ({male_count} male, {female_count} female)")
    
    # Show final statistics by grade
    print("\n" + "="*60)
    print("FINAL STATISTICS BY GRADE")
    print("="*60)
    
    for grade in grade_levels:
        total = User.objects.filter(role='student', grade_level=grade).count()
        male = User.objects.filter(role='student', grade_level=grade, gender='M').count()
        female = User.objects.filter(role='student', grade_level=grade, gender='F').count()
        
        if total > 0:
            print(f"\nGrade {grade}:")
            print(f"  Total: {total}")
            print(f"  Male: {male} ({male/total*100:.1f}%)")
            print(f"  Female: {female} ({female/total*100:.1f}%)")
    
    # Overall statistics
    print("\n" + "="*60)
    print("OVERALL STATISTICS")
    print("="*60)
    total_all = User.objects.filter(role='student').count()
    male_all = User.objects.filter(role='student', gender='M').count()
    female_all = User.objects.filter(role='student', gender='F').count()
    print(f"Total Students: {total_all}")
    print(f"Male: {male_all} ({male_all/total_all*100:.1f}%)")
    print(f"Female: {female_all} ({female_all/total_all*100:.1f}%)")

if __name__ == '__main__':
    populate_student_data()
