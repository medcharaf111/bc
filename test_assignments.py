import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from accounts.models import TeacherGradeAssignment, User

# Find a teacher with assignments
teachers = User.objects.filter(role='teacher')
print(f"\n{'='*60}")
print("CHECKING TEACHER ASSIGNMENTS")
print(f"{'='*60}\n")

for teacher in teachers[:3]:  # Check first 3 teachers
    print(f"Teacher: {teacher.username} ({teacher.first_name} {teacher.last_name})")
    
    assignments = TeacherGradeAssignment.objects.filter(
        teacher=teacher,
        is_active=True
    )
    
    if assignments.exists():
        print(f"  Has {assignments.count()} assignment(s):")
        
        subject_grades = {}
        all_grade_levels = set()
        
        for assignment in assignments:
            subject = assignment.subject
            grade_level = assignment.grade_level
            all_grade_levels.add(grade_level)
            
            if subject not in subject_grades:
                subject_grades[subject] = {
                    'subject': subject,
                    'subject_display': assignment.get_subject_display(),
                    'grades': []
                }
            subject_grades[subject]['grades'].append({
                'grade_level': grade_level,
                'grade_display': assignment.get_grade_level_display()
            })
        
        print(f"  Subject codes: {list(subject_grades.keys())}")
        print(f"  Grade codes: {list(all_grade_levels)}")
        print(f"  Full data: {subject_grades}")
    else:
        print("  No assignments")
    print()
