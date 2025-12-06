# Data migration to update role values from 'mandobiya' to 'delegation'
from django.db import migrations


def update_role_values(apps, schema_editor):
    """Update all 'mandobiya' role values to 'delegation'"""
    User = apps.get_model('accounts', 'User')
    updated_count = User.objects.filter(role='mandobiya').update(role='delegation')
    print(f"Updated {updated_count} users from 'mandobiya' to 'delegation' role")


def reverse_role_values(apps, schema_editor):
    """Reverse: Update all 'delegation' role values back to 'mandobiya'"""
    User = apps.get_model('accounts', 'User')
    updated_count = User.objects.filter(role='delegation').update(role='mandobiya')
    print(f"Reverted {updated_count} users from 'delegation' to 'mandobiya' role")


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0017_rename_mandobiya_to_delegation'),
    ]

    operations = [
        migrations.RunPython(update_role_values, reverse_role_values),
    ]
