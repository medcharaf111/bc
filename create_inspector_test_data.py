#!/usr/bin/env python
"""
Create test schools and teachers for charafinspector's regions
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from accounts.models import User, School
from core.inspection_models import Region

def create_test_data():
    inspector = User.objects.get(username='charafinspector')
    regions = Region.objects.filter(code__in=['TUN-01', 'SFA-01', 'ARI-01'])
    
    print("Creating test schools and teachers for charafinspector\n")
    
    for region in regions:
        print(f"\n{'='*60}")
        print(f"REGION: {region.name} ({region.code})")
        print('='*60)
        
        # Create 3 schools per region
        for i in range(1, 4):
            school_name = f"{region.name} Primary School #{i}"
            school, created = School.objects.get_or_create(
                name=school_name,
                defaults={
                    'address': f'{i}0 Main Street, {region.name}',
                    'region': region,
                    'school_type': 'primary',
                    'school_code': f'{region.code}-SCH-{i:02d}',
                    'delegation': region.name,
                }
            )
            status = "Created" if created else "Found"
            print(f"\n{status} School: {school_name}")
            
            # Create 2-3 teachers per school
            for j in range(1, 3 if i == 1 else 4):
                username = f"teacher_{region.code.lower().replace('-', '')}_{i}_{j}"
                
                subject = ['math', 'science', 'english'][j % 3]
                
                teacher, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'password': 'pbkdf2_sha256$600000$test$test',  # Will be overridden
                        'first_name': f'Teacher{j}',
                        'last_name': f'{region.name}{i}',
                        'email': f'{username}@school.tn',
                        'role': 'teacher',
                        'school': school,
                        'subjects': [subject],
                        'grade_level': str((i + j) % 6 + 1),
                    }
                )
                
                # Set proper password
                if created:
                    teacher.set_password('teacher123')
                    teacher.save()
                
                status = "Created" if created else "Found"
                subject_display = teacher.subjects[0] if teacher.subjects else 'N/A'
                print(f"  {status} Teacher: {teacher.username} ({subject_display}, Grade {teacher.grade_level})")
        
        # Summary
        school_count = School.objects.filter(region=region).count()
        teacher_count = User.objects.filter(role='teacher', school__region=region).count()
        print(f"\n✓ Region Summary: {school_count} schools, {teacher_count} teachers")
    
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    
    total_schools = School.objects.filter(region__in=regions).count()
    total_teachers = User.objects.filter(role='teacher', school__region__in=regions).count()
    
    print(f"Total Schools: {total_schools}")
    print(f"Total Teachers: {total_teachers}")
    print(f"Inspector: {inspector.username}")
    print(f"Regions: {', '.join([r.name for r in regions])}")
    print("\n✅ Test data created successfully!")
    print("\nTeachers can log in with:")
    print("  Username: teacher_tunXX_X_X (e.g., teacher_tun01_1_1)")
    print("  Password: teacher123")

if __name__ == '__main__':
    create_test_data()
