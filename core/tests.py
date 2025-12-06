from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Lesson, Test, Portfolio, TestSubmission
from accounts.models import School

User = get_user_model()


class PortfolioTestResultsTestCase(TestCase):
    """Test that test results are saved to student portfolios"""
    
    def setUp(self):
        """Create test data"""
        # Create school
        self.school = School.objects.create(
            name='Test School',
            address='123 Test St'
        )
        
        # Create users
        self.teacher = User.objects.create_user(
            username='teacher',
            password='testpass123',
            email='teacher@test.com',
            role='teacher',
            school=self.school
        )
        
        self.student = User.objects.create_user(
            username='student',
            password='testpass123',
            email='student@test.com',
            role='student',
            school=self.school
        )
        
        # Create lesson
        self.lesson = Lesson.objects.create(
            title='Python Basics',
            content='Learn Python fundamentals',
            created_by=self.teacher,
            school=self.school
        )
        
        # Create test
        self.test = Test.objects.create(
            lesson=self.lesson,
            title='Python Quiz 1',
            questions=[
                {
                    'question': 'What is 2+2?',
                    'options': ['3', '4', '5', '6'],
                    'correct_answer': 1
                }
            ],
            status='approved',
            created_by=self.teacher
        )
    
    def test_portfolio_created_on_first_approval(self):
        """Test that portfolio is auto-created when first test is approved"""
        # Create test submission
        submission = TestSubmission.objects.create(
            test=self.test,
            student=self.student,
            answers=[{'question_index': 0, 'selected_answer': 1, 'is_correct': True}],
            score=100.0,
            status='submitted'
        )
        
        # Approve submission (simulate the view logic)
        submission.status = 'approved'
        submission.is_final = True
        submission.reviewed_by = self.teacher
        submission.save()
        
        # Create portfolio and add result
        portfolio, created = Portfolio.objects.get_or_create(
            student=self.student,
            defaults={
                'summary': f'Portfolio for {self.student.username}',
                'achievements': [],
                'test_results': []
            }
        )
        portfolio.add_test_result(
            lesson_name=self.lesson.title,
            test_title=self.test.title,
            test_type='MCQ',
            score=submission.score,
            attempt=submission.attempt_number
        )
        
        # Verify portfolio exists
        self.assertTrue(Portfolio.objects.filter(student=self.student).exists())
        
        # Verify test result was added
        portfolio.refresh_from_db()
        self.assertEqual(len(portfolio.test_results), 1)
        
        # Verify result structure
        result = portfolio.test_results[0]
        self.assertEqual(result['lesson_name'], 'Python Basics')
        self.assertEqual(result['test_title'], 'Python Quiz 1')
        self.assertEqual(result['test_type'], 'MCQ')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['attempt'], 1)
        self.assertIn('date', result)
    
    def test_multiple_test_results_saved(self):
        """Test that multiple test results accumulate in portfolio"""
        # Create portfolio
        portfolio = Portfolio.objects.create(
            student=self.student,
            summary='Test portfolio',
            achievements=[],
            test_results=[]
        )
        
        # Add first test result
        portfolio.add_test_result(
            lesson_name='Python Basics',
            test_title='Quiz 1',
            test_type='MCQ',
            score=85.0,
            attempt=1
        )
        
        # Add second test result
        portfolio.add_test_result(
            lesson_name='Data Structures',
            test_title='Arrays Test',
            test_type='QA',
            score=92.0,
            attempt=1
        )
        
        # Verify both results exist
        portfolio.refresh_from_db()
        self.assertEqual(len(portfolio.test_results), 2)
        
        # Verify order (latest should be last)
        self.assertEqual(portfolio.test_results[0]['lesson_name'], 'Python Basics')
        self.assertEqual(portfolio.test_results[1]['lesson_name'], 'Data Structures')
    
    def test_attempt_number_tracked(self):
        """Test that retake attempts are tracked correctly"""
        portfolio = Portfolio.objects.create(
            student=self.student,
            summary='Test portfolio',
            achievements=[],
            test_results=[]
        )
        
        # First attempt
        portfolio.add_test_result(
            lesson_name='Python Basics',
            test_title='Quiz 1',
            test_type='MCQ',
            score=70.0,
            attempt=1
        )
        
        # Second attempt (retake)
        portfolio.add_test_result(
            lesson_name='Python Basics',
            test_title='Quiz 1',
            test_type='MCQ',
            score=90.0,
            attempt=2
        )
        
        portfolio.refresh_from_db()
        self.assertEqual(len(portfolio.test_results), 2)
        self.assertEqual(portfolio.test_results[0]['attempt'], 1)
        self.assertEqual(portfolio.test_results[1]['attempt'], 2)
        
        # Verify improvement
        self.assertGreater(
            portfolio.test_results[1]['score'],
            portfolio.test_results[0]['score']
        )
