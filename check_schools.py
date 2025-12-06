import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from accounts.models import School

# Check schools with CRE "Tunis 1"
t1 = School.objects.filter(cre__iexact='Tunis 1')
print(f'\n{"="*60}')
print(f'Schools with CRE "Tunis 1"')
print(f'{"="*60}')
print(f'Total: {t1.count()}')

geo = t1.filter(latitude__isnull=False, longitude__isnull=False)
print(f'With geodata: {geo.count()}')

if geo.exists():
    sample = geo.first()
    print(f'\nSample school:')
    print(f'  Name: {sample.name}')
    print(f'  Delegation: {sample.delegation}')
    print(f'  CRE: {sample.cre}')
    print(f'  Lat/Long: {sample.latitude}, {sample.longitude}')
    
    print(f'\nAll delegations within Tunis 1 CRE:')
    delegations = t1.exclude(delegation__isnull=True).exclude(delegation='').values_list('delegation', flat=True).distinct()
    for d in delegations[:10]:
        count = t1.filter(delegation=d).count()
        print(f'  - {d}: {count} schools')
else:
    print('\nNo schools found with geodata for CRE "Tunis 1"')
    print('\nChecking all CRE values in database...')
    all_cres = School.objects.exclude(cre__isnull=True).exclude(cre='').values_list('cre', flat=True).distinct()
    print(f'Available CREs (first 20): {list(all_cres)[:20]}')
