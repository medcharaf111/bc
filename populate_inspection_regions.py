#!/usr/bin/env python
"""
Populate regions for the inspection system

This script creates regions based on Tunisian governorates and assigns schools to regions
based on their delegation field.

Run with: python backend/populate_inspection_regions.py
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from accounts.models import School
from core.inspection_models import Region

# Tunisian governorates (wilayas) - 24 regions
TUNISIAN_REGIONS = [
    {'code': 'TUN', 'name': 'Tunis', 'description': 'Capital governorate'},
    {'code': 'ARI', 'name': 'Ariana', 'description': 'Northern governorate'},
    {'code': 'BEN', 'name': 'Ben Arous', 'description': 'Northern governorate'},
    {'code': 'MAN', 'name': 'Manouba', 'description': 'Northern governorate'},
    {'code': 'NAB', 'name': 'Nabeul', 'description': 'Northeastern governorate'},
    {'code': 'ZAG', 'name': 'Zaghouan', 'description': 'Northern governorate'},
    {'code': 'BIZ', 'name': 'Bizerte', 'description': 'Northern governorate'},
    {'code': 'BEJ', 'name': 'Béja', 'description': 'Northern governorate'},
    {'code': 'JEN', 'name': 'Jendouba', 'description': 'Northwestern governorate'},
    {'code': 'KEF', 'name': 'Kef', 'description': 'Northwestern governorate'},
    {'code': 'SIL', 'name': 'Siliana', 'description': 'Northern governorate'},
    {'code': 'SOU', 'name': 'Sousse', 'description': 'Eastern governorate'},
    {'code': 'MON', 'name': 'Monastir', 'description': 'Eastern governorate'},
    {'code': 'MAH', 'name': 'Mahdia', 'description': 'Eastern governorate'},
    {'code': 'SFA', 'name': 'Sfax', 'description': 'Eastern governorate'},
    {'code': 'KAI', 'name': 'Kairouan', 'description': 'Central governorate'},
    {'code': 'KAS', 'name': 'Kasserine', 'description': 'Western governorate'},
    {'code': 'SID', 'name': 'Sidi Bouzid', 'description': 'Central governorate'},
    {'code': 'GAB', 'name': 'Gabès', 'description': 'Southern governorate'},
    {'code': 'MED', 'name': 'Médenine', 'description': 'Southern governorate'},
    {'code': 'TAT', 'name': 'Tataouine', 'description': 'Southern governorate'},
    {'code': 'GFR', 'name': 'Gafsa', 'description': 'Southern governorate'},
    {'code': 'TOZ', 'name': 'Tozeur', 'description': 'Southern governorate'},
    {'code': 'KEB', 'name': 'Kebili', 'description': 'Southern governorate'},
]

# Delegation to Region mapping (based on Tunisian administrative divisions)
DELEGATION_TO_REGION = {
    # Tunis delegations
    'TUNIS': 'TUN', 'TUNIS EL MADINA': 'TUN', 'TUNIS BAB BHAR': 'TUN', 'TUNIS SIDI EL BECHIR': 'TUN',
    'EL KHADRA': 'TUN', 'BAB SOUIKA': 'TUN', 'KABBARIA': 'TUN', 'EL OUERDIA': 'TUN',
    'CARTHAGE': 'TUN', 'LA GOULETTE': 'TUN', 'EL MARSA': 'TUN', 'SIDI BOU SAID': 'TUN',
    'EZZOUHOUR': 'TUN', 'HRAIRIA': 'TUN', 'SIDI HASSINE': 'TUN',
    
    # Ariana delegations
    'ARIANA': 'ARI', 'ARIANA VILLE': 'ARI', 'SOUKRA': 'ARI', 'RAOUED': 'ARI',
    'KALAAT EL ANDALOUS': 'ARI', 'SIDI THABET': 'ARI', 'ETTADHAMEN': 'ARI',
    
    # Ben Arous delegations
    'BEN AROUS': 'BEN', 'HAMMAM-LIF': 'BEN', 'HAMMAM LIF': 'BEN', 'RADES': 'BEN',
    'EL MOUROUJ': 'BEN', 'MEGRINE': 'BEN', 'FOUCHANA': 'BEN', 'MORNAG': 'BEN',
    'EZZAHRA': 'BEN', 'MEDINA JEDIDA': 'BEN', 'BOUMHEL EL BASSATINE': 'BEN',
    
    # Manouba delegations
    'MANOUBA': 'MAN', 'OUED ELLIL': 'MAN', 'TEBOURBA': 'MAN', 'EL BATTAN': 'MAN',
    'DOUAR HICHER': 'MAN', 'DEN DEN': 'MAN', 'JEDAIDA': 'MAN', 'MORNAGUIA': 'MAN',
    
    # Nabeul delegations
    'NABEUL': 'NAB', 'GROMBALIA': 'NAB', 'KELIBIA': 'NAB', 'HAMMAMET': 'NAB',
    'KORBA': 'NAB', 'MENZEL TEMIME': 'NAB', 'DAR CHAABANE': 'NAB', 'BENI KHIAR': 'NAB',
    'SOLIMAN': 'NAB', 'EL MIDA': 'NAB', 'ELMIDA': 'NAB', 'MENZEL BOUZELFA': 'NAB',
    'TAKELSA': 'NAB', 'BOU ARGOUB': 'NAB', 'EL HAOUARIA': 'NAB', 'ZARAMDINE': 'NAB',
    
    # Zaghouan delegations
    'ZAGHOUAN': 'ZAG', 'ZRIBA': 'ZAG', 'FAHS': 'ZAG', 'NADHOUR': 'ZAG',
    'SAOUAF': 'ZAG', 'ENNADHOUR': 'ZAG',
    
    # Bizerte delegations
    'BIZERTE': 'BIZ', 'MENZEL BOURGUIBA': 'BIZ', 'MENZEL JEMIL': 'BIZ', 'MATEUR': 'BIZ',
    'SEJNANE': 'BIZ', 'JOUMINE': 'BIZ', 'GHAR EL MELH': 'BIZ', 'TINJA': 'BIZ',
    'UTIQUE': 'BIZ', 'RAS JEBEL': 'BIZ', 'ZARZOUNA': 'BIZ', 'EL ALIA': 'BIZ',
    'MENZEL ABDERRAHMAN': 'BIZ', 'GHEZALA': 'BIZ',
    
    # Béja delegations
    'BEJA': 'BEJ', 'MEJEZ EL BAB': 'BEJ', 'TESTOUR': 'BEJ', 'TEBOURSOUK': 'BEJ',
    'GOUBELLAT': 'BEJ', 'NEFZA': 'BEJ', 'AMDOUN': 'BEJ', 'TIBAR': 'BEJ',
    
    # Jendouba delegations
    'JENDOUBA': 'JEN', 'TABARKA': 'JEN', 'AIN DRAHAM': 'JEN', 'BALTA BOUAOUENE': 'JEN',
    'BALTA BOUOUENE': 'JEN', 'GHARDIMAOU': 'JEN', 'FERNANA': 'JEN', 'BOU SALEM': 'JEN',
    'OUED MELIZ': 'JEN',
    
    # Kef delegations
    'KEF': 'KEF', 'DAHMANI': 'KEF', 'TAJEROUINE': 'KEF', 'SAKIET SIDI YOUSSEF': 'KEF',
    'KALAAT SENAN': 'KEF', 'KALAA KHASBA': 'KEF', 'KALAAT KHASBA': 'KEF', 'NEBEUR': 'KEF',
    'SERS': 'KEF', 'TOUIREF': 'KEF', 'EL KSOUR': 'KEF', 'JERISSA': 'KEF',
    
    # Siliana delegations
    'SILIANA': 'SIL', 'SILIANA NORD': 'SIL', 'SILIANA SUD': 'SIL', 'BOU ARADA': 'SIL',
    'GAAFOUR': 'SIL', 'EL AROUSSA': 'SIL', 'ROUHIA': 'SIL', 'KESRA': 'SIL',
    'BARGOU': 'SIL', 'EL KRIB': 'SIL', 'MAKTHER': 'SIL',
    
    # Sousse delegations
    'SOUSSE': 'SOU', 'SOUSSE VILLE': 'SOU', 'SOUSSE JAWHARA': 'SOU', 'SOUSSE SIDI ABDELHAMID': 'SOU',
    'MSAKEN': 'SOU', 'KALAA KEBIRA': 'SOU', 'KALAA SEGHIRA': 'SOU', 'AKOUDA': 'SOU',
    'HAMMAM SOUSSE': 'SOU', 'ENFIDHA': 'SOU', 'SID BOU ALI': 'SOU', 'SIDI EL HANI': 'SOU',
    'BOUFICHA': 'SOU', 'KONDAR': 'SOU', 'HERGLA': 'SOU',
    
    # Monastir delegations
    'MONASTIR': 'MON', 'JEMMAL': 'MON', 'MOKNINE': 'MON', 'KSAR HELAL': 'MON',
    'BEKALTA': 'MON', 'KSIBET EL MEDIOUNI': 'MON', 'BEMBLA': 'MON', 'ZERAMDINE': 'MON',
    'OUERDANINE': 'MON', 'SAHLINE': 'MON', 'TEBOULBA': 'MON', 'BENI HASSEN': 'MON',
    
    # Mahdia delegations
    'MAHDIA': 'MAH', 'KSOUR ESSEF': 'MAH', 'EL JEM': 'MAH', 'CHORBANE': 'MAH',
    'HEBIRA': 'MAH', 'CHEBBA': 'MAH', 'MELLOULECH': 'MAH', 'SIDI ALOUANE': 'MAH',
    'OULED CHAMEKH': 'MAH', 'BOUOUANE': 'MAH', 'EL BRADAA': 'MAH',
    
    # Sfax delegations
    'SFAX': 'SFA', 'SFAX VILLE': 'SFA', 'SFAX SUD': 'SFA', 'SFAX OUEST': 'SFA',
    'SAKIET EZZIT': 'SFA', 'SAKIET EDDAIER': 'SFA', 'THYNA': 'SFA', 'AGAREB': 'SFA',
    'EL AMRA': 'SFA', 'EL HENCHA': 'SFA', 'MENZEL CHAKER': 'SFA', 'MAHRES': 'SFA',
    'KERKENNAH': 'SFA', 'SKHIRA': 'SFA', 'GRAIBA': 'SFA', 'BIR ALI BEN KHALIFA': 'SFA',
    
    # Kairouan delegations
    'KAIROUAN': 'KAI', 'KAIROUAN NORD': 'KAI', 'KAIROUAN SUD': 'KAI', 'ECHBIKA': 'KAI',
    'SBIKHA': 'KAI', 'HAFFOUZ': 'KAI', 'EL ALAA': 'KAI', 'HAJEB EL AYOUN': 'KAI',
    'NASRALLAH': 'KAI', 'CHERARDA': 'KAI', 'BOUHAJLA': 'KAI', 'OUESLATIA': 'KAI',
    
    # Kasserine delegations
    'KASSERINE': 'KAS', 'KASSERINE NORD': 'KAS', 'KASSERINE SUD': 'KAS', 'SBEITLA': 'KAS',
    'SBIBA': 'KAS', 'THALA': 'KAS', 'HIDRA': 'KAS', 'FOUSSANA': 'KAS',
    'FERIANA': 'KAS', 'MEJEL BEL ABBES': 'KAS', 'HASSI EL FRID': 'KAS', 'JEDILIANE': 'KAS',
    'EL AYOUN': 'KAS',
    
    # Sidi Bouzid delegations
    'SIDI BOUZID': 'SID', 'SIDI BOUZID EST': 'SID', 'SIDI BOUZID OUEST': 'SID',
    'REGUEB': 'SID', 'JELMA': 'SID', 'MEZZOUNA': 'SID', 'MENZEL BOUZAIENE': 'SID',
    'MEKNASSY': 'SID', 'SOUK JEDID': 'SID', 'BIR EL HAFFEY': 'SID', 'CEBBALA': 'SID',
    
    # Gabès delegations
    'GABES': 'GAB', 'GABES VILLE': 'GAB', 'GABES OUEST': 'GAB', 'GABES SUD': 'GAB',
    'MARETH': 'GAB', 'MATMATA': 'GAB', 'NOUVELLE MATMATA': 'GAB', 'METOUIA': 'GAB',
    'EL HAMMA': 'GAB', 'MENZEL EL HABIB': 'GAB',
    
    # Médenine delegations
    'MEDENINE': 'MED', 'MEDENINE NORD': 'MED', 'MEDENINE SUD': 'MED', 'BEN GUERDANE': 'MED',
    'ZARZIS': 'MED', 'BENI KHEDACHE': 'MED', 'HOUMT SOUK': 'MED', 'MIDOUN': 'MED',
    'AJIM': 'MED', 'SIDI MAKHLOUF': 'MED',
    
    # Tataouine delegations
    'TATAOUINE': 'TAT', 'TATAOUINE NORD': 'TAT', 'TATAOUINE SUD': 'TAT', 'GHOMRASSEN': 'TAT',
    'DHEHIBA': 'TAT', 'REMADA': 'TAT', 'SMAAR': 'TAT', 'BIR LAHMAR': 'TAT',
    
    # Gafsa delegations
    'GAFSA': 'GFR', 'GAFSA NORD': 'GFR', 'GAFSA SUD': 'GFR', 'SENED': 'GFR',
    'EL KSAR': 'GFR', 'METLAOUI': 'GFR', 'MDHILA': 'GFR', 'EL GUETTAR': 'GFR',
    'REDEYEF': 'GFR', 'OM EL ARAIES': 'GFR', 'BELKHIR': 'GFR',
    
    # Tozeur delegations
    'TOZEUR': 'TOZ', 'DEGACHE': 'TOZ', 'TAMAGHZA': 'TOZ', 'NEFTA': 'TOZ',
    'HEZOUA': 'TOZ', 'TAMEGHZA': 'TOZ',
    
    # Kebili delegations
    'KEBILI': 'KEB', 'KEBILI NORD': 'KEB', 'KEBILI SUD': 'KEB', 'DOUZ': 'KEB',
    'SOUK LAHAD': 'KEB', 'FAOUAR': 'KEB', 'JEMNA': 'KEB',
}


def create_regions():
    """Create all Tunisian regions"""
    print("📍 Creating Tunisian regions...\n")
    created_count = 0
    existing_count = 0
    updated_count = 0
    
    for region_data in TUNISIAN_REGIONS:
        # Try to find by name first (in case code is different)
        try:
            region = Region.objects.get(name=region_data['name'])
            # Update code if different
            if region.code != region_data['code']:
                region.code = region_data['code']
                region.description = region_data['description']
                region.save()
                print(f"🔄 Updated: {region.name} ({region.code})")
                updated_count += 1
            else:
                existing_count += 1
        except Region.DoesNotExist:
            # Create new region
            region = Region.objects.create(
                code=region_data['code'],
                name=region_data['name'],
                description=region_data['description']
            )
            print(f"✅ Created: {region.name} ({region.code})")
            created_count += 1
        except Region.MultipleObjectsReturned:
            # If multiple exist with same name, use first one
            region = Region.objects.filter(name=region_data['name']).first()
            existing_count += 1
    
    print(f"\n📊 Summary: {created_count} created, {existing_count} already existed, {updated_count} updated")
    return Region.objects.count()


def assign_schools_to_regions():
    """Assign schools to regions based on their delegation"""
    print("\n🏫 Assigning schools to regions...\n")
    
    schools = School.objects.all()
    assigned_count = 0
    unmatched_count = 0
    already_assigned_count = 0
    unmatched_delegations = set()
    
    for school in schools:
        # Skip if already assigned
        if school.region:
            already_assigned_count += 1
            continue
        
        delegation = school.delegation.strip().upper() if school.delegation else ''
        
        if delegation and delegation in DELEGATION_TO_REGION:
            region_code = DELEGATION_TO_REGION[delegation]
            try:
                region = Region.objects.get(code=region_code)
                school.region = region
                school.save()
                assigned_count += 1
                if assigned_count % 100 == 0:
                    print(f"  ... assigned {assigned_count} schools")
            except Region.DoesNotExist:
                unmatched_count += 1
                unmatched_delegations.add(delegation)
        else:
            unmatched_count += 1
            if delegation:
                unmatched_delegations.add(delegation)
    
    print(f"\n📊 Assignment Summary:")
    print(f"  ✅ Assigned: {assigned_count}")
    print(f"  ⏭️  Already assigned: {already_assigned_count}")
    print(f"  ❌ Unmatched: {unmatched_count}")
    
    if unmatched_delegations:
        print(f"\n⚠️  Unmatched delegations (first 10):")
        for delegation in list(unmatched_delegations)[:10]:
            count = School.objects.filter(delegation=delegation).count()
            print(f"  - {delegation}: {count} schools")
    
    return assigned_count


def print_statistics():
    """Print final statistics"""
    print("\n" + "=" * 60)
    print("📊 FINAL STATISTICS")
    print("=" * 60)
    
    from accounts.models import User
    
    regions = Region.objects.all()
    print(f"\n🌍 Total Regions: {regions.count()}")
    
    for region in regions[:5]:  # Show first 5
        school_count = School.objects.filter(region=region).count()
        teacher_count = User.objects.filter(role='teacher', school__region=region).count()
        print(f"  - {region.name}: {school_count} schools, {teacher_count} teachers")
    
    if regions.count() > 5:
        print(f"  ... and {regions.count() - 5} more regions")
    
    schools_with_regions = School.objects.filter(region__isnull=False).count()
    schools_without_regions = School.objects.filter(region__isnull=True).count()
    total_schools = School.objects.count()
    
    print(f"\n🏫 Schools:")
    print(f"  - With regions: {schools_with_regions} ({schools_with_regions/total_schools*100:.1f}%)")
    print(f"  - Without regions: {schools_without_regions} ({schools_without_regions/total_schools*100:.1f}%)")
    
    teachers = User.objects.filter(role='teacher')
    teachers_with_regions = teachers.filter(school__region__isnull=False).count()
    teachers_without_regions = teachers.filter(school__region__isnull=True).count()
    
    print(f"\n👨‍🏫 Teachers:")
    print(f"  - With region access: {teachers_with_regions} ({teachers_with_regions/teachers.count()*100:.1f}%)")
    print(f"  - Without region access: {teachers_without_regions}")
    
    print("\n✅ Region population complete!")
    print("\n💡 Next steps:")
    print("  1. Create inspector accounts")
    print("  2. Assign inspectors to regions using InspectorRegionAssignment")
    print("  3. Inspectors can now schedule visits for teachers in their regions\n")


def main():
    """Main execution"""
    print("\n" + "=" * 60)
    print("   INSPECTION SYSTEM - REGION POPULATION")
    print("=" * 60 + "\n")
    
    try:
        # Step 1: Create regions
        total_regions = create_regions()
        
        # Step 2: Assign schools to regions
        assigned_schools = assign_schools_to_regions()
        
        # Step 3: Print statistics
        print_statistics()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
