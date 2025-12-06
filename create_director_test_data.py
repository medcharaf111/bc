"""
Create a test director user for testing the Director Dashboard
"""
from accounts.models import User, School

# Get or create a school
school, created = School.objects.get_or_create(
    name='Test School',
    defaults={'address': '123 Test Street'}
)

# Create a director user
director, created = User.objects.get_or_create(
    username='director_test',
    defaults={
        'email': 'director@test.com',
        'first_name': 'Test',
        'last_name': 'Director',
        'role': 'director',
        'school': school,
    }
)

if created:
    director.set_password('password123')
    director.save()
    print(f"✅ Created director user: {director.username}")
    print(f"   School: {school.name}")
    print(f"   Password: password123")
    print(f"   Login URL: http://localhost:5173/login")
else:
    print(f"ℹ️ Director user already exists: {director.username}")

# Create some test teachers for the school
subjects_list = [
    ['math', 'physics'],
    ['science', 'computer_science'],
    ['english', 'art'],
    ['arabic'],
    ['social_studies', 'religious_studies'],
]

for i, subjects in enumerate(subjects_list, 1):
    teacher, created = User.objects.get_or_create(
        username=f'teacher{i}',
        defaults={
            'email': f'teacher{i}@test.com',
            'first_name': f'Teacher',
            'last_name': f'{i}',
            'role': 'teacher',
            'school': school,
            'subjects': subjects,
        }
    )
    if created:
        teacher.set_password('password123')
        teacher.save()
        print(f"✅ Created teacher: {teacher.username} (subjects: {', '.join(subjects)})")
    else:
        print(f"ℹ️ Teacher already exists: {teacher.username}")

print("\n" + "="*60)
print("🎉 Test data created successfully!")
print("="*60)
print("\nDirector Login:")
print("  Username: director_test")
print("  Password: password123")
print("\nTeacher Logins (all use password: password123):")
for i in range(1, len(subjects_list) + 1):
    print(f"  - teacher{i}")
