"""
Management command to create initial data for the application
"""
from django.core.management.base import BaseCommand
from accounts.models import School, User
from core.models import Lesson, Test, TestSubmission
from django.utils import timezone
from datetime import timedelta
import random


class Command(BaseCommand):
    help = 'Creates initial data (schools, users, lessons, tests) for the application'

    def handle(self, *args, **options):
        self.stdout.write('Creating initial data...')
        
        # Create test schools if they don't exist
        schools_data = [
            {'id': 1, 'name': 'Primary School 1', 'address': 'Tunis', 'school_code': 'SCH001'},
            {'id': 2, 'name': 'Primary School 2', 'address': 'Sfax', 'school_code': 'SCH002'},
            {'id': 3, 'name': 'Secondary School 1', 'address': 'Sousse', 'school_code': 'SCH003'},
            {'id': 4, 'name': 'Secondary School 2', 'address': 'Bizerte', 'school_code': 'SCH004'},
            {'id': 5, 'name': 'High School 1', 'address': 'Gabes', 'school_code': 'SCH005'},
        ]
        
        schools = []
        for school_data in schools_data:
            school, created = School.objects.get_or_create(
                id=school_data['id'],
                defaults={
                    'name': school_data['name'],
                    'address': school_data['address'],
                    'school_code': school_data['school_code']
                }
            )
            schools.append(school)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created school: {school.name}'))
        
        # Available subjects (stored as strings in JSONField)
        subjects = ['math', 'english', 'arabic', 'science', 'social_studies']
        
        # Create teachers (5 teachers)
        teachers = []
        for i in range(1, 6):
            teacher, created = User.objects.get_or_create(
                username=f'teacher{i}',
                defaults={
                    'email': f'teacher{i}@demo.com',
                    'first_name': f'Teacher',
                    'last_name': f'{i}',
                    'role': 'teacher',
                    'school': schools[i % len(schools)],
                    'subjects': [subjects[i % len(subjects)]]
                }
            )
            if created:
                teacher.set_password('demo123')
                teacher.save()
                self.stdout.write(self.style.SUCCESS(f'Created teacher: {teacher.username}'))
            teachers.append(teacher)
        
        # Create students (20 students)
        students = []
        for i in range(1, 21):
            student, created = User.objects.get_or_create(
                username=f'student{i}',
                defaults={
                    'email': f'student{i}@demo.com',
                    'first_name': f'Student',
                    'last_name': f'{i}',
                    'role': 'student',
                    'school': schools[i % len(schools)]
                }
            )
            if created:
                student.set_password('demo123')
                student.save()
                self.stdout.write(self.style.SUCCESS(f'Created student: {student.username}'))
            students.append(student)
        
        # Create lessons (10 lessons)
        lessons = []
        lesson_titles = [
            'Introduction to Algebra', 'Grammar Basics', 'Arabic Reading',
            'Basic Science', 'History Lesson', 'Math Fundamentals',
            'English Writing', 'Arabic Grammar', 'Science Experiments',
            'Social Studies'
        ]
        for i, title in enumerate(lesson_titles):
            teacher = teachers[i % len(teachers)]
            lesson, created = Lesson.objects.get_or_create(
                title=title,
                defaults={
                    'content': f'This is the content for {title}.',
                    'subject': subjects[i % len(subjects)],
                    'created_by': teacher,
                    'school': teacher.school,
                    'grade_level': str((i % 6) + 1)
                }
            )
            lessons.append(lesson)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created lesson: {lesson.title}'))
        
        # Create tests (15 tests)
        tests = []
        for i in range(1, 16):
            test, created = Test.objects.get_or_create(
                title=f'Test {i}',
                defaults={
                    'lesson': lessons[i % len(lessons)],
                    'created_by': teachers[i % len(teachers)],
                    'questions': [
                        {'question': f'Question {j+1}', 'options': ['A', 'B', 'C', 'D'], 'correct': 'A'}
                        for j in range(random.randint(5, 10))
                    ],
                    'duration_minutes': random.choice([30, 45, 60]),
                    'passing_score': 60
                }
            )
            tests.append(test)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created test: {test.title}'))
        
        # Create test submissions (50-100 submissions)
        submission_count = 0
        for student in students:
            # Each student takes 3-5 tests
            num_tests = random.randint(3, 5)
            student_tests = random.sample(tests, min(num_tests, len(tests)))
            
            for test in student_tests:
                score = random.randint(40, 100)
                submission, created = TestSubmission.objects.get_or_create(
                    student=student,
                    test=test,
                    defaults={
                        'answers': {},
                        'score': score,
                        'completed': True,
                        'submitted_at': timezone.now() - timedelta(days=random.randint(1, 30))
                    }
                )
                if created:
                    submission_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {submission_count} test submissions'))
        self.stdout.write(self.style.SUCCESS('Initial data creation complete!'))
