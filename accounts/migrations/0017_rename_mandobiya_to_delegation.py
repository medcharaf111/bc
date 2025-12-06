# Manual migration to rename mandobiya to delegation
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0016_teacherinspection_advisor_completed_at_and_more'),
    ]

    operations = [
        # First, update the role choices to include 'delegation'
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('teacher', 'Teacher'),
                    ('student', 'Student'),
                    ('parent', 'Parent'),
                    ('admin', 'Administrator'),
                    ('advisor', 'Advisor'),
                    ('director', 'School Director'),
                    ('cnp', 'CNP Agent'),
                    ('mandobiya', 'Inspector/Advisor (Mandobiya)'),  # Keep old value temporarily
                    ('delegation', 'Inspector/Advisor (Delegation)'),  # Add new value
                ],
                max_length=10
            ),
        ),
        
        # Remove the old index on mandobiya field before renaming
        migrations.RemoveIndex(
            model_name='teacherinspection',
            name='accounts_te_mandobi_e6fb83_idx',
        ),
        
        # Rename the mandobiya field to delegator in TeacherInspection
        migrations.RenameField(
            model_name='teacherinspection',
            old_name='mandobiya',
            new_name='delegator',
        ),
        
        # Rename verification fields
        migrations.RenameField(
            model_name='teacherinspection',
            old_name='start_verified_by_mandobiya',
            new_name='start_verified_by_delegator',
        ),
        migrations.RenameField(
            model_name='teacherinspection',
            old_name='completion_verified_by_mandobiya',
            new_name='completion_verified_by_delegator',
        ),
        
        # Rename MandobiyaTeacherMetrics to DelegationTeacherMetrics
        migrations.RenameModel(
            old_name='MandobiyaTeacherMetrics',
            new_name='DelegationTeacherMetrics',
        ),
        
        # Rename MandobiyaDashboardStats to DelegationDashboardStats  
        migrations.RenameModel(
            old_name='MandobiyaDashboardStats',
            new_name='DelegationDashboardStats',
        ),
        
        # Rename the mandobiya field to delegator in DelegationDashboardStats
        migrations.RenameField(
            model_name='delegationdashboardstats',
            old_name='mandobiya',
            new_name='delegator',
        ),
        
        # Update the FK limit_choices in TeacherInspection
        migrations.AlterField(
            model_name='teacherinspection',
            name='delegator',
            field=models.ForeignKey(
                limit_choices_to={'role': 'delegation'},
                on_delete=django.db.models.deletion.CASCADE,
                related_name='conducted_inspections',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        
        # Update the FK limit_choices in DelegationDashboardStats
        migrations.AlterField(
            model_name='delegationdashboardstats',
            name='delegator',
            field=models.OneToOneField(
                limit_choices_to={'role': 'delegation'},
                on_delete=django.db.models.deletion.CASCADE,
                related_name='dashboard_stats',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        
        # Update the FK limit_choices in TeacherAdvisorAssignment
        migrations.AlterField(
            model_name='teacheradvisorassignment',
            name='assigned_by',
            field=models.ForeignKey(
                limit_choices_to={'role': 'delegation'},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='advisor_assignments_made',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        
        # Add new index on delegator field
        migrations.AddIndex(
            model_name='teacherinspection',
            index=models.Index(fields=['delegator', 'status'], name='accounts_te_delegat_26805d_idx'),
        ),
    ]
