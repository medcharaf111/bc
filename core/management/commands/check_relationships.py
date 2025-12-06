"""
Management command to check teacher-student relationships
"""
from django.core.management.base import BaseCommand
from accounts.models import User, TeacherStudentRelationship
from core.models import Portfolio

class Command(BaseCommand):
    help = 'Check teacher-student relationships and portfolios'

    def handle(self, *args, **options):
        # Get the teacher
        try:
            teacher = User.objects.get(username='charafenglish')
            self.stdout.write(self.style.SUCCESS(f'\n=== Teacher: {teacher.get_full_name()} ({teacher.username}) ===\n'))
            
            # Get all relationships
            relationships = TeacherStudentRelationship.objects.filter(
                teacher=teacher,
                is_active=True
            )
            
            self.stdout.write(f'Total active relationships: {relationships.count()}\n')
            
            for rel in relationships:
                student = rel.student
                self.stdout.write(f'\n--- Student: {student.get_full_name()} ({student.username}) ---')
                self.stdout.write(f'Email: {student.email}')
                
                # Check portfolio
                try:
                    portfolio = Portfolio.objects.get(student=student)
                    self.stdout.write(self.style.SUCCESS('✓ Portfolio exists'))
                    
                    # Get subject stats
                    subject_stats = portfolio.get_subject_statistics()
                    if subject_stats:
                        self.stdout.write('Subject Statistics:')
                        for subj, stats in subject_stats.items():
                            self.stdout.write(f'  - {stats["subject_display"]}: {stats["average_score"]}% ({stats["test_count"]} tests)')
                    else:
                        self.stdout.write(self.style.WARNING('  No subject statistics found'))
                        
                except Portfolio.DoesNotExist:
                    self.stdout.write(self.style.ERROR('✗ No portfolio'))
                    
            self.stdout.write(self.style.SUCCESS('\n\nDone!'))
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('Teacher "charafenglish" not found'))
