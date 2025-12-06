"""
Django management command to automatically check teacher attendance against timetables.

This command should be run periodically (e.g., via cron job or Celery beat) to:
1. Check if teachers have checked in according to their assigned timetables
2. Mark teachers as absent if they haven't checked in within the grace period
3. Mark teachers as late if they checked in after the expected time

Usage:
    python manage.py check_teacher_attendance
    python manage.py check_teacher_attendance --grace-period 15
    python manage.py check_teacher_attendance --date 2025-01-15
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta, time
from accounts.models import TeacherTimetable, TeacherAttendance, User
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check teacher attendance against timetables and mark absent/late automatically'

    def add_arguments(self, parser):
        parser.add_argument(
            '--grace-period',
            type=int,
            default=15,
            help='Grace period in minutes for late arrivals (default: 15)'
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Date to check in YYYY-MM-DD format (default: today)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )

    def handle(self, *args, **options):
        grace_period_minutes = options['grace_period']
        dry_run = options['dry_run']
        
        # Determine the date to check
        if options['date']:
            try:
                check_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(self.style.ERROR('Invalid date format. Use YYYY-MM-DD'))
                return
        else:
            check_date = timezone.now().date()
        
        day_of_week = check_date.weekday()  # Monday=0, Sunday=6
        
        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*70}\n'
            f'Checking Teacher Attendance for {check_date} ({["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][day_of_week]})\n'
            f'Grace Period: {grace_period_minutes} minutes\n'
            f'Mode: {"DRY RUN" if dry_run else "LIVE"}\n'
            f'{"="*70}\n'
        ))
        
        # Get all active timetables for this day of week
        timetables = TeacherTimetable.objects.filter(
            day_of_week=day_of_week,
            is_active=True
        ).select_related('teacher', 'teacher__school')
        
        if not timetables.exists():
            self.stdout.write(self.style.WARNING(
                f'No active timetables found for {["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][day_of_week]}'
            ))
            return
        
        self.stdout.write(f'Found {timetables.count()} teachers with schedules for this day\n')
        
        stats = {
            'total_checked': 0,
            'marked_absent': 0,
            'marked_late': 0,
            'already_present': 0,
            'already_absent': 0,
            'no_action': 0,
        }
        
        current_time = timezone.now().time()
        
        for timetable in timetables:
            teacher = timetable.teacher
            stats['total_checked'] += 1
            
            # Get or create attendance record for this teacher and date
            attendance, created = TeacherAttendance.objects.get_or_create(
                teacher=teacher,
                date=check_date,
                defaults={
                    'status': 'absent',
                    'reason': 'No check-in recorded within scheduled hours'
                }
            )
            
            # Calculate grace period deadline
            expected_time = timetable.start_time
            grace_deadline = (
                datetime.combine(check_date, expected_time) + 
                timedelta(minutes=grace_period_minutes)
            ).time()
            
            # Determine what action to take
            action = None
            new_status = None
            reason = None
            
            if attendance.check_in_time:
                # Teacher has checked in
                if attendance.status == 'present':
                    stats['already_present'] += 1
                    action = 'SKIP'
                    self.stdout.write(
                        f'  ✓ {teacher.get_full_name() or teacher.username}: '
                        f'Already marked present (checked in at {attendance.check_in_time})'
                    )
                elif attendance.check_in_time <= grace_deadline:
                    # Checked in on time or within grace period
                    if attendance.status != 'present':
                        action = 'UPDATE_PRESENT'
                        new_status = 'present'
                        reason = f'Checked in at {attendance.check_in_time}'
                        stats['already_present'] += 1
                        self.stdout.write(self.style.SUCCESS(
                            f'  ✓ {teacher.get_full_name() or teacher.username}: '
                            f'Present (checked in at {attendance.check_in_time}, expected {expected_time})'
                        ))
                else:
                    # Checked in after grace period
                    if attendance.status != 'late':
                        action = 'MARK_LATE'
                        new_status = 'late'
                        minutes_late = int((
                            datetime.combine(check_date, attendance.check_in_time) -
                            datetime.combine(check_date, grace_deadline)
                        ).total_seconds() / 60)
                        reason = f'Checked in {minutes_late} minutes after grace period (at {attendance.check_in_time}, expected {expected_time})'
                        stats['marked_late'] += 1
                        self.stdout.write(self.style.WARNING(
                            f'  ⚠ {teacher.get_full_name() or teacher.username}: '
                            f'Late by {minutes_late} min (checked in at {attendance.check_in_time}, grace deadline {grace_deadline})'
                        ))
            else:
                # No check-in recorded
                # Only mark absent if we're past the grace period
                if current_time > grace_deadline or check_date < timezone.now().date():
                    if attendance.status == 'absent':
                        stats['already_absent'] += 1
                        action = 'SKIP'
                        self.stdout.write(
                            f'  ✗ {teacher.get_full_name() or teacher.username}: '
                            f'Already marked absent (no check-in by {grace_deadline})'
                        )
                    elif attendance.status not in ['planned_absence']:
                        action = 'MARK_ABSENT'
                        new_status = 'absent'
                        reason = f'No check-in recorded by grace deadline {grace_deadline} (expected {expected_time})'
                        stats['marked_absent'] += 1
                        self.stdout.write(self.style.ERROR(
                            f'  ✗ {teacher.get_full_name() or teacher.username}: '
                            f'Marking absent (no check-in by {grace_deadline}, expected {expected_time})'
                        ))
                else:
                    # Still within grace period, don't mark anything yet
                    stats['no_action'] += 1
                    time_remaining = int((
                        datetime.combine(check_date, grace_deadline) -
                        datetime.combine(check_date, current_time)
                    ).total_seconds() / 60)
                    self.stdout.write(
                        f'  ⏳ {teacher.get_full_name() or teacher.username}: '
                        f'Waiting (grace period ends in {time_remaining} min at {grace_deadline})'
                    )
            
            # Apply the action if not dry run
            if action in ['MARK_ABSENT', 'MARK_LATE', 'UPDATE_PRESENT'] and not dry_run:
                attendance.status = new_status
                if reason:
                    attendance.reason = reason
                attendance.save()
        
        # Print summary
        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*70}\n'
            f'Summary:\n'
            f'  Total teachers checked: {stats["total_checked"]}\n'
            f'  Marked absent: {stats["marked_absent"]}\n'
            f'  Marked late: {stats["marked_late"]}\n'
            f'  Already present: {stats["already_present"]}\n'
            f'  Already absent: {stats["already_absent"]}\n'
            f'  No action (within grace period): {stats["no_action"]}\n'
            f'{"="*70}\n'
        ))
        
        if dry_run:
            self.stdout.write(self.style.WARNING(
                '\nDRY RUN MODE: No changes were made to the database.\n'
                'Run without --dry-run to apply changes.\n'
            ))
