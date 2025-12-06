#!/usr/bin/env python
"""
Script to create a test inspector assignment
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from accounts.models import User, InspectorAssignment

def create_test_assignment():
    # Get first inspector
    inspector = User.objects.filter(role='inspector').first()
    
    if not inspector:
        print("❌ No inspector user found in the database")
        return
    
    print(f"✓ Found inspector: {inspector.username} ({inspector.first_name} {inspector.last_name})")
    
    # Check if assignment already exists
    existing = InspectorAssignment.objects.filter(
        inspector=inspector,
        assignment_type='region',
        school_level='primary',
        assigned_region='Tunis 1'
    ).first()
    
    if existing:
        print(f"✓ Assignment already exists (ID: {existing.id})")
        assignment = existing
    else:
        # Create assignment
        assignment = InspectorAssignment.objects.create(
            inspector=inspector,
            assignment_type='region',
            school_level='primary',
            assigned_region='Tunis 1',
            notes='Test assignment for primary schools in Tunis 1'
        )
        print(f"✓ Created new assignment (ID: {assignment.id})")
    
    # Get schools count
    schools = assignment.get_assigned_schools()
    schools_count = schools.count()
    print(f"✓ Total schools in this assignment: {schools_count}")
    
    if schools_count > 0:
        print("\n✅ Success! The inspector can now view the school map.")
    else:
        print("\n⚠️  Warning: No schools found for this assignment. The region might not have primary schools with geodata.")

if __name__ == '__main__':
    create_test_assignment()
