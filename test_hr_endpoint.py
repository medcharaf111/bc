import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from accounts.models import User
from rest_framework.test import APIRequestFactory
from core.views import hr_student_performance
import json

factory = APIRequestFactory()
request = factory.get('/api/analytics/hr-student-performance/')
gdhr_user = User.objects.filter(role='gdhr').first()

if not gdhr_user:
    print("No GDHR user found!")
else:
    print(f"Testing with GDHR user: {gdhr_user.email} (role: {gdhr_user.role})")
    
    # Force authenticate the request
    from rest_framework.test import force_authenticate
    force_authenticate(request, user=gdhr_user)
    
    response = hr_student_performance(request)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.data  # Use .data instead of parsing content
        print(f"\nTotal students: {data.get('total_students')}")
        print(f"Age groups: {len(data.get('by_age', []))}")
        print(f"Regions: {len(data.get('by_region', []))}")
        print(f"Gender groups: {len(data.get('by_gender', []))}")
        print(f"Grade groups: {len(data.get('by_grade', []))}")
        
        print("\n=== Age Distribution ===")
        for item in data.get('by_age', [])[:3]:
            print(item)
        
        print("\n=== Region Distribution ===")
        for item in data.get('by_region', [])[:3]:
            print(item)
        
        print("\n=== Gender Distribution ===")
        print(data.get('by_gender', []))
        
        print("\n=== Grade Distribution ===")
        for item in data.get('by_grade', [])[:3]:
            print(item)
    else:
        print(f"Error: {response.data if hasattr(response, 'data') else 'Unknown error'}")
