import os
import django
import random
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import (
    Lesson, Test, TestSubmission, QATest,
    Portfolio
)
from accounts.models import TeacherStudentRelationship, School

User = get_user_model()

def create_mock_evolution_data():
    """
    Create mock data showing platform evolution over time for ministerial demo.
    
    Initial Setup:
    - Advisors: Neila Mersny, Wided Meddeb
    - English Teachers: Souha, Sarah, Teyma
    """
    
    print("=" * 60)
    print("CREATING MOCK EVOLUTION DATA FOR MINISTERIAL DEMO")
    print("=" * 60)
    
    # Get or create school
    school, _ = School.objects.get_or_create(
        name="Demo High School",
        defaults={
            'address': 'Tunis, Tunisia',
            'delegation': 'Tunis',
        }
    )
    print(f"✓ School: {school.name}")
    
    # =====================
    # ADVISORS
    # =====================
    print("\n--- Creating Advisors ---")
    
    advisors_data = [
        {
            'username': 'neila.mersny',
            'email': 'neila.mersny@education.tn',
            'first_name': 'Neila',
            'last_name': 'Mersny',
            'subjects': ['english']
        },
        {
            'username': 'wided.meddeb',
            'email': 'wided.meddeb@education.tn',
            'first_name': 'Wided',
            'last_name': 'Meddeb',
            'subjects': ['english']
        }
    ]
    
    advisors = []
    for data in advisors_data:
        advisor, created = User.objects.get_or_create(
            username=data['username'],
            defaults={
                'email': data['email'],
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'role': 'advisor',
                'school': school,
                'subjects': data['subjects']
            }
        )
        if created:
            advisor.set_password('demo123')
            advisor.save()
        advisors.append(advisor)
        print(f"✓ Advisor: {advisor.first_name} {advisor.last_name}")
    
    # =====================
    # TEACHERS
    # =====================
    print("\n--- Creating English Teachers ---")
    
    teachers_data = [
        {
            'username': 'souha.teacher',
            'email': 'souha@school.tn',
            'first_name': 'Souha',
            'last_name': 'Ahmed',
            'subjects': ['english']
        },
        {
            'username': 'sarah.teacher',
            'email': 'sarah@school.tn',
            'first_name': 'Sarah',
            'last_name': 'Ben Ali',
            'subjects': ['english']
        },
        {
            'username': 'teyma.teacher',
            'email': 'teyma@school.tn',
            'first_name': 'Teyma',
            'last_name': 'Mansour',
            'subjects': ['english']
        }
    ]
    
    teachers = []
    for data in teachers_data:
        teacher, created = User.objects.get_or_create(
            username=data['username'],
            defaults={
                'email': data['email'],
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'role': 'teacher',
                'school': school,
                'subjects': data['subjects']
            }
        )
        if created:
            teacher.set_password('demo123')
            teacher.save()
        teachers.append(teacher)
        print(f"✓ Teacher: {teacher.first_name} {teacher.last_name}")
    
    # =====================
    # STUDENTS (20 students)
    # =====================
    print("\n--- Creating Students ---")
    
    student_first_names = [
        'Mohamed', 'Aya', 'Youssef', 'Salma', 'Ahmed',
        'Fatima', 'Ali', 'Mariem', 'Hamza', 'Nour',
        'Omar', 'Rania', 'Karim', 'Sarra', 'Bilel',
        'Amira', 'Mehdi', 'Yasmine', 'Sofiane', 'Ines'
    ]
    
    student_last_names = [
        'Ben Salem', 'Gharbi', 'Trabelsi', 'Jlassi', 'Karoui',
        'Hamdi', 'Bouzid', 'Chebbi', 'Dridi', 'Messaoudi'
    ]
    
    students = []
    for i, first_name in enumerate(student_first_names):
        last_name = random.choice(student_last_names)
        username = f"{first_name.lower()}.{last_name.lower().replace(' ', '')}{i}"
        
        student, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f"{username}@student.tn",
                'first_name': first_name,
                'last_name': last_name,
                'role': 'student',
                'school': school
            }
        )
        if created:
            student.set_password('demo123')
            student.save()
        students.append(student)
    
    print(f"✓ Created {len(students)} students")
    
    # =====================
    # TEACHER-STUDENT RELATIONSHIPS
    # =====================
    print("\n--- Creating Teacher-Student Relationships ---")
    
    relationships_count = 0
    for student in students:
        # Assign 2-3 teachers per student
        assigned_teachers = random.sample(teachers, k=random.randint(2, 3))
        for teacher in assigned_teachers:
            rel, created = TeacherStudentRelationship.objects.get_or_create(
                teacher=teacher,
                student=student
            )
            if created:
                relationships_count += 1
    
    print(f"✓ Created {relationships_count} teacher-student relationships")
    
    # =====================
    # HISTORICAL DATA (Last 3 months)
    # =====================
    print("\n--- Creating Historical Evolution Data ---")
    
    base_date = datetime.now() - timedelta(days=90)
    
    # Month 1: Low activity (weeks 1-4)
    print("\nMonth 1 (Weeks 1-4): Initial Adoption")
    lessons_month1 = create_lessons_for_period(teachers[:1], base_date, days=30, count_range=(2, 4))
    tests_month1 = create_tests_for_period(teachers[:1], base_date, days=30, count_range=(1, 2))
    submissions_month1 = create_submissions(tests_month1, students[:10], success_rate=0.60)
    
    print(f"  ✓ Lessons: {len(lessons_month1)}")
    print(f"  ✓ Tests: {len(tests_month1)}")
    print(f"  ✓ Submissions: {len(submissions_month1)}")
    
    # Month 2: Medium activity (weeks 5-8)
    print("\nMonth 2 (Weeks 5-8): Growth Phase")
    base_date_m2 = base_date + timedelta(days=30)
    lessons_month2 = create_lessons_for_period(teachers[:2], base_date_m2, days=30, count_range=(3, 6))
    tests_month2 = create_tests_for_period(teachers[:2], base_date_m2, days=30, count_range=(2, 4))
    submissions_month2 = create_submissions(tests_month2, students[:15], success_rate=0.72)
    
    print(f"  ✓ Lessons: {len(lessons_month2)}")
    print(f"  ✓ Tests: {len(tests_month2)}")
    print(f"  ✓ Submissions: {len(submissions_month2)}")
    
    # Month 3: High activity (weeks 9-12)
    print("\nMonth 3 (Weeks 9-12): Full Adoption")
    base_date_m3 = base_date + timedelta(days=60)
    lessons_month3 = create_lessons_for_period(teachers, base_date_m3, days=30, count_range=(5, 8))
    tests_month3 = create_tests_for_period(teachers, base_date_m3, days=30, count_range=(3, 5))
    submissions_month3 = create_submissions(tests_month3, students, success_rate=0.85)
    
    print(f"  ✓ Lessons: {len(lessons_month3)}")
    print(f"  ✓ Tests: {len(tests_month3)}")
    print(f"  ✓ Submissions: {len(submissions_month3)}")
    
    # =====================
    # CREATE PORTFOLIOS
    # =====================
    print("\n--- Creating Student Portfolios ---")
    portfolios_count = 0
    for student in students:
        portfolio, created = Portfolio.objects.get_or_create(
            student=student,
            defaults={
                'summary': f"Portfolio showcasing {student.first_name}'s progress in English",
                'achievements': [],
                'test_results': []
            }
        )
        if created:
            portfolios_count += 1
    
    print(f"✓ Created {portfolios_count} portfolios")
    
    # =====================
    # SUMMARY
    # =====================
    print("\n" + "=" * 60)
    print("MOCK DATA CREATION COMPLETE!")
    print("=" * 60)
    print(f"\nUsers Created:")
    print(f"  • Advisors: {len(advisors)}")
    print(f"  • Teachers: {len(teachers)}")
    print(f"  • Students: {len(students)}")
    print(f"\nContent Evolution:")
    print(f"  • Total Lessons: {len(lessons_month1) + len(lessons_month2) + len(lessons_month3)}")
    print(f"  • Total Tests: {len(tests_month1) + len(tests_month2) + len(tests_month3)}")
    print(f"  • Total Submissions: {len(submissions_month1) + len(submissions_month2) + len(submissions_month3)}")
    print(f"\nGrowth Trend:")
    print(f"  • Month 1: Low activity (1 teacher, 10 students)")
    print(f"  • Month 2: Medium activity (2 teachers, 15 students)")
    print(f"  • Month 3: High activity (3 teachers, 20 students)")
    print(f"\nLogin Credentials (all users):")
    print(f"  Password: demo123")
    print("=" * 60)


def create_lessons_for_period(teachers, base_date, days, count_range):
    """Create lessons distributed over a period"""
    lessons = []
    for teacher in teachers:
        num_lessons = random.randint(*count_range)
        for i in range(num_lessons):
            days_offset = random.randint(0, days)
            created_at = base_date + timedelta(days=days_offset)
            
            lesson = Lesson.objects.create(
                created_by=teacher,
                school=teacher.school,
                title=f"English Lesson {i+1} - {teacher.first_name}",
                content=f"# Lesson Content\n\nThis is a detailed lesson about English language concepts.\n\n## Topics Covered\n- Grammar\n- Vocabulary\n- Reading comprehension",
                subject='english',
                created_at=created_at
            )
            lesson.created_at = created_at
            lesson.save(update_fields=['created_at'])
            lessons.append(lesson)
    
    return lessons


def create_tests_for_period(teachers, base_date, days, count_range):
    """Create tests distributed over a period"""
    tests = []
    for teacher in teachers:
        num_tests = random.randint(*count_range)
        for i in range(num_tests):
            days_offset = random.randint(0, days)
            created_at = base_date + timedelta(days=days_offset)
            
            # Create lesson first
            lesson = Lesson.objects.create(
                created_by=teacher,
                school=teacher.school,
                title=f"English Lesson for Test {i+1}",
                content="Test lesson content",
                subject='english',
                created_at=created_at
            )
            lesson.created_at = created_at
            lesson.save(update_fields=['created_at'])
            
            # Create Test (mix of MCQ-style and essay questions)
            test = Test.objects.create(
                lesson=lesson,
                created_by=teacher,
                title=f"English Test {i+1} - {teacher.first_name}",
                questions=[
                    {
                        'question': 'What is the past tense of "go"?',
                        'options': ['goed', 'went', 'gone', 'going'],
                        'correct_answer': 1
                    },
                    {
                        'question': 'Which word is a noun?',
                        'options': ['quickly', 'run', 'happiness', 'beautiful'],
                        'correct_answer': 2
                    }
                ],
                status='approved',
                num_questions=2,
                created_at=created_at
            )
            
            test.created_at = created_at
            test.save(update_fields=['created_at'])
            tests.append(test)
    
    return tests


def create_submissions(tests, students, success_rate):
    """Create test submissions with given success rate"""
    submissions = []
    for test in tests:
        # Random subset of students submit
        num_submissions = random.randint(len(students) // 2, len(students))
        submitting_students = random.sample(students, num_submissions)
        
        for student in submitting_students:
            # Determine if submission is successful based on success_rate
            is_successful = random.random() < success_rate
            score = random.randint(70, 100) if is_successful else random.randint(40, 69)
            
            answers = [random.randint(0, 3) for _ in range(len(test.questions))]
            submission = TestSubmission.objects.create(
                test=test,
                student=student,
                answers=answers,
                score=score
            )
            submissions.append(submission)
    
    return submissions




if __name__ == '__main__':
    create_mock_evolution_data()
