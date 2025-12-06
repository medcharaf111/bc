import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from accounts.models import TeacherGradeAssignment, User

# Find the teacher
try:
    teacher = User.objects.get(username='charafenglish')
    print(f"\n{'='*60}")
    print(f"Teacher: {teacher.username} ({teacher.first_name} {teacher.last_name})")
    print(f"Role: {teacher.role}")
    print(f"School: {teacher.school}")
    print(f"{'='*60}\n")
    
    # Get assignments
    assignments = TeacherGradeAssignment.objects.filter(teacher=teacher)
    
    print(f"Total assignments (all): {assignments.count()}")
    print(f"Active assignments: {assignments.filter(is_active=True).count()}\n")
    
    for assignment in assignments:
        print(f"Assignment ID: {assignment.id}")
        print(f"  Grade Level: {assignment.grade_level} ({assignment.get_grade_level_display()})")
        print(f"  Subject: {assignment.subject} ({assignment.get_subject_display()})")
        print(f"  School: {assignment.school}")
        print(f"  Is Active: {assignment.is_active}")
        print(f"  Assigned By: {assignment.assigned_by}")
        print(f"  Academic Year: {assignment.academic_year}")
        print()
    
    # Test the API endpoint logic
    print(f"\n{'='*60}")
    print("SIMULATING API ENDPOINT RESPONSE:")
    print(f"{'='*60}\n")
    
    assignments = TeacherGradeAssignment.objects.filter(
        teacher=teacher,
        is_active=True
    ).select_related('teacher').distinct()
    
    # Get unique subjects with their grade levels
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
    
    print(f"Subject codes: {list(subject_grades.keys())}")
    print(f"Grade codes: {list(all_grade_levels)}")
    print(f"Has assignments: {len(subject_grades) > 0}")
    print(f"\nFull response data:")
    print({
        'assigned_subjects': list(subject_grades.values()),
        'subject_codes': list(subject_grades.keys()),
        'grade_codes': list(all_grade_levels),
        'has_assignments': len(subject_grades) > 0
    })
    
except User.DoesNotExist:
    print("Teacher 'charafenglish' not found")
