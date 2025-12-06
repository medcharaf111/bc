"""
Management command to initialize forum categories with bilingual support
"""
from django.core.management.base import BaseCommand
from core.models import ForumCategory


class Command(BaseCommand):
    help = 'Initialize forum categories with English and Arabic names'

    def handle(self, *args, **options):
        categories = [
            {
                'name': 'Teaching Methods',
                'name_ar': 'طرق التدريس',
                'description': 'Share and discuss effective teaching methodologies and classroom strategies',
                'description_ar': 'مشاركة ومناقشة منهجيات التدريس الفعالة واستراتيجيات الفصل الدراسي',
                'category_type': 'teaching_methods',
                'icon': 'BookOpen',
                'order': 1
            },
            {
                'name': 'Lesson Sharing',
                'name_ar': 'مشاركة الدروس',
                'description': 'Exchange lesson plans, materials, and educational resources',
                'description_ar': 'تبادل خطط الدروس والمواد والموارد التعليمية',
                'category_type': 'lesson_sharing',
                'icon': 'FileText',
                'order': 2
            },
            {
                'name': 'Subject Discussion',
                'name_ar': 'مناقشة المواد',
                'description': 'Discuss specific subject areas: Math, Science, Languages, etc.',
                'description_ar': 'مناقشة مجالات مواضيع محددة: الرياضيات، العلوم، اللغات، إلخ',
                'category_type': 'subject_discussion',
                'icon': 'GraduationCap',
                'order': 3
            },
            {
                'name': 'Best Practices',
                'name_ar': 'أفضل الممارسات',
                'description': 'Share proven strategies and success stories from the classroom',
                'description_ar': 'مشاركة الاستراتيجيات المثبتة وقصص النجاح من الفصل الدراسي',
                'category_type': 'best_practices',
                'icon': 'Award',
                'order': 4
            },
            {
                'name': 'Technology & Tools',
                'name_ar': 'التكنولوجيا والأدوات',
                'description': 'Discuss educational technology, digital tools, and platform features',
                'description_ar': 'مناقشة التكنولوجيا التعليمية والأدوات الرقمية وميزات المنصة',
                'category_type': 'technology',
                'icon': 'Laptop',
                'order': 5
            },
            {
                'name': 'Regional Exchange',
                'name_ar': 'التبادل الإقليمي',
                'description': 'Connect with educators from different regions and share local experiences',
                'description_ar': 'التواصل مع المعلمين من مناطق مختلفة ومشاركة التجارب المحلية',
                'category_type': 'regional_exchange',
                'icon': 'MapPin',
                'order': 6
            },
            {
                'name': 'General Discussion',
                'name_ar': 'نقاش عام',
                'description': 'General topics related to education and professional development',
                'description_ar': 'مواضيع عامة تتعلق بالتعليم والتطوير المهني',
                'category_type': 'general',
                'icon': 'MessageSquare',
                'order': 7
            }
        ]

        created_count = 0
        updated_count = 0

        for cat_data in categories:
            category, created = ForumCategory.objects.update_or_create(
                category_type=cat_data['category_type'],
                defaults={
                    'name': cat_data['name'],
                    'name_ar': cat_data['name_ar'],
                    'description': cat_data['description'],
                    'description_ar': cat_data['description_ar'],
                    'icon': cat_data['icon'],
                    'order': cat_data['order'],
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created category: {category.name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'↻ Updated category: {category.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Forum categories initialized!\n'
                f'   Created: {created_count}\n'
                f'   Updated: {updated_count}\n'
                f'   Total: {created_count + updated_count}'
            )
        )
