import os
import django
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from accounts.models import User, School

print("\n" + "="*60)
print("ASSIGNING STUDENTS TO SCHOOLS WITH DELEGATIONS")
print("="*60 + "\n")

# Get schools with delegations (not N/A or empty)
schools_with_delegations = School.objects.exclude(delegation__isnull=True).exclude(delegation='')
print(f"Found {schools_with_delegations.count()} schools with delegations")

# Get unique delegations
delegations = schools_with_delegations.values_list('delegation', flat=True).distinct()
print(f"Found {len(delegations)} unique delegations")

# Show sample delegations
print("\nSample delegations:")
for delegation in list(delegations)[:20]:
    count = schools_with_delegations.filter(delegation=delegation).count()
    print(f"  - {delegation}: {count} schools")

# Get all students
students = User.objects.filter(role='student', is_active=True)
print(f"\nTotal students to assign: {students.count()}\n")

random.seed(42)

# Randomly assign students to schools with delegations
updated_count = 0
for student in students:
    # Pick a random delegation
    random_delegation = random.choice(list(delegations))
    
    # Pick a random school from that delegation
    schools_in_delegation = schools_with_delegations.filter(delegation=random_delegation)
    random_school = random.choice(list(schools_in_delegation))
    
    student.school = random_school
    student.save()
    updated_count += 1
    
    if updated_count <= 10:
        print(f"{student.username}: {random_school.name} ({random_school.delegation})")

print(f"\n✓ Updated {updated_count} students with schools!")

# Show delegation distribution
print("\n" + "="*60)
print("STUDENT DISTRIBUTION BY DELEGATION")
print("="*60 + "\n")

from collections import defaultdict
delegation_dist = defaultdict(int)

for student in students:
    if student.school and student.school.delegation:
        delegation_dist[student.school.delegation] += 1

for delegation in sorted(delegation_dist.keys(), key=lambda x: delegation_dist[x], reverse=True)[:20]:
    print(f"{delegation}: {delegation_dist[delegation]} students")

print(f"\n✓ Complete! Students now distributed across {len(delegation_dist)} delegations")
