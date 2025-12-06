import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from django.core.cache import cache

print("Clearing all cache...")
cache.clear()
print("Cache cleared successfully!")
