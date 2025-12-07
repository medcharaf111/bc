"""
Management command to create initial data for the application
"""
from django.core.management.base import BaseCommand
from accounts.models import School


class Command(BaseCommand):
    help = 'Creates initial data (schools, etc.) for the application'

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
        
        created_count = 0
        for school_data in schools_data:
            school, created = School.objects.get_or_create(
                id=school_data['id'],
                defaults={
                    'name': school_data['name'],
                    'address': school_data['address'],
                    'school_code': school_data['school_code']
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created school: {school.name}'))
            else:
                self.stdout.write(f'School already exists: {school.name}')
        
        self.stdout.write(self.style.SUCCESS(f'Initial data creation complete. Created {created_count} schools.'))
