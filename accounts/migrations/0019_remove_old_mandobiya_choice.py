# Final migration to remove old 'mandobiya' role choice
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0018_update_role_data'),
    ]

    operations = [
        # Remove the old 'mandobiya' choice from role field
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
                    ('delegation', 'Inspector/Advisor (Delegation)'),
                ],
                max_length=10
            ),
        ),
    ]
