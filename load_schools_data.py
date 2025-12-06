"""
Script to load Tunisia schools geodata from CSV into the database
"""
import csv
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'native_os.settings')
django.setup()

from accounts.models import School

def load_schools_from_csv():
    csv_file = 'SchoolsGeoData.csv'
    
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        schools_created = 0
        schools_updated = 0
        skipped = 0
        
        for row in reader:
            try:
                code = row['code_etablissement']
                name = row['nom_etablissement']
                name_ar = row.get('nom_etablissement_ar', '')
                school_type = row.get('Type', '')
                delegation = row.get('delegation', '')
                cre = row.get('CRE', '')
                
                # Parse coordinates with error handling
                latitude = None
                longitude = None
                
                if row.get('Latitude initiale'):
                    try:
                        lat_str = row['Latitude initiale'].strip()
                        # Handle malformed data like "10.1195369.15" by taking first valid float
                        if lat_str.count('.') > 1:
                            # Split on dots and reconstruct valid float
                            parts = lat_str.split('.')
                            if len(parts) >= 2:
                                lat_str = f"{parts[0]}.{parts[1]}"
                        latitude = float(lat_str)
                    except (ValueError, AttributeError):
                        pass
                
                if row.get('Longitude initiale'):
                    try:
                        lon_str = row['Longitude initiale'].strip()
                        # Handle malformed data
                        if lon_str.count('.') > 1:
                            parts = lon_str.split('.')
                            if len(parts) >= 2:
                                lon_str = f"{parts[0]}.{parts[1]}"
                        longitude = float(lon_str)
                    except (ValueError, AttributeError):
                        pass
                
                # Create full address
                address = f"{delegation}, {cre}, Tunisia"
                
                # Check if school already exists by name
                school, created = School.objects.update_or_create(
                    name=name,
                    defaults={
                        'address': address,
                        'latitude': latitude,
                        'longitude': longitude,
                        'school_code': code,
                        'school_type': school_type,
                        'delegation': delegation,
                        'cre': cre,
                        'name_ar': name_ar,
                    }
                )
                
                if created:
                    schools_created += 1
                else:
                    schools_updated += 1
                
                if (schools_created + schools_updated) % 100 == 0:
                    print(f"Processed {schools_created + schools_updated} schools...")
            
            except Exception as e:
                skipped += 1
                if skipped <= 10:  # Only show first 10 errors
                    print(f"⚠️  Skipped row (error: {str(e)[:50]}...)")
        
        print(f"\n✅ Import complete!")
        print(f"   Created: {schools_created} schools")
        print(f"   Updated: {schools_updated} schools")
        print(f"   Skipped: {skipped} schools (due to errors)")
        print(f"   Total processed: {schools_created + schools_updated} schools")

if __name__ == '__main__':
    print("Loading Tunisia schools data from CSV...")
    load_schools_from_csv()
