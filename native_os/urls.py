"""
URL configuration for native_os project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from accounts.views import (
    SchoolViewSet, UserViewSet, TeacherStudentRelationshipViewSet,
    AdvisorReviewViewSet, GroupChatViewSet, ChatMessageViewSet,
    ParentStudentRelationshipViewSet, ParentDashboardViewSet,
    ParentTeacherChatViewSet, ParentTeacherMessageViewSet,
    TeacherProgressViewSet, ChapterProgressNotificationViewSet, TeacherAnalyticsViewSet,
    AdministratorViewSet, TeacherGradeAssignmentViewSet, TeacherTimetableViewSet,
    InspectorAssignmentViewSet
)
from accounts.mandobiya_views import (
    DelegationTeacherViewSet, DelegationAdvisorViewSet,
    TeacherAdvisorAssignmentViewSet, TeacherInspectionViewSet,
    InspectionReviewViewSet, DelegationDashboardViewSet
)
from accounts.notification_views import NotificationViewSet
from accounts.advisor_views import AdvisorInspectionViewSet, AdvisorDashboardViewSet
from accounts.attendance_views import (
    TeacherAttendanceViewSet, StudentAttendanceViewSet, AttendanceSummaryViewSet
)
from core.views import (
    LessonViewSet, TestViewSet, ProgressViewSet, PortfolioViewSet, 
    QATestViewSet, QASubmissionViewSet, TeachingPlanViewSet,
    VaultLessonPlanViewSet, VaultLessonPlanUsageViewSet, VaultCommentViewSet,
    VaultExerciseViewSet, VaultMaterialViewSet,
    minister_analytics, lesson_performance,
    StudentNotebookViewSet, NotebookPageViewSet,
    hr_overview, hr_all_users, hr_teacher_performance, hr_student_performance,
    ministry_hr_by_region, regional_education_search
)
from core.cnp_views import CNPTeacherGuideViewSet
from core.inspection_views import (
    RegionViewSet, InspectorDashboardViewSet, GPIDashboardViewSet,
    TeacherComplaintViewSet, InspectionVisitViewSet, InspectionReportViewSet,
    MonthlyReportViewSet, TeacherRatingHistoryViewSet
)
from accounts.secretary_views import TaskViewSet, MeetingViewSet, DecisionViewSet, DocumentViewSet

router = DefaultRouter()
router.register(r'schools', SchoolViewSet)
router.register(r'users', UserViewSet)
router.register(r'relationships', TeacherStudentRelationshipViewSet, basename='relationship')
router.register(r'advisor-reviews', AdvisorReviewViewSet, basename='advisor-review')
router.register(r'group-chats', GroupChatViewSet, basename='group-chat')
router.register(r'chat-messages', ChatMessageViewSet, basename='chat-message')
router.register(r'parent-students', ParentStudentRelationshipViewSet, basename='parent-student')
router.register(r'parent-dashboard', ParentDashboardViewSet, basename='parent-dashboard')
router.register(r'parent-teacher-chats', ParentTeacherChatViewSet, basename='parent-teacher-chat')
router.register(r'parent-teacher-messages', ParentTeacherMessageViewSet, basename='parent-teacher-message')
router.register(r'teacher-progress', TeacherProgressViewSet, basename='teacher-progress')
router.register(r'chapter-notifications', ChapterProgressNotificationViewSet, basename='chapter-notification')
router.register(r'teacher-analytics', TeacherAnalyticsViewSet, basename='teacher-analytics')
router.register(r'teacher-grade-assignments', TeacherGradeAssignmentViewSet, basename='teacher-grade-assignment')
router.register(r'teacher-timetables', TeacherTimetableViewSet, basename='teacher-timetable')
router.register(r'administrator', AdministratorViewSet, basename='administrator')
router.register(r'lessons', LessonViewSet)
router.register(r'tests', TestViewSet)
router.register(r'progress', ProgressViewSet)
router.register(r'portfolios', PortfolioViewSet)
router.register(r'qa-tests', QATestViewSet)
router.register(r'qa-submissions', QASubmissionViewSet)
router.register(r'teaching-plans', TeachingPlanViewSet, basename='teaching-plan')
router.register(r'vault-lesson-plans', VaultLessonPlanViewSet, basename='vault-lesson-plan')
router.register(r'vault-usage', VaultLessonPlanUsageViewSet, basename='vault-usage')
router.register(r'vault-comments', VaultCommentViewSet, basename='vault-comment')
router.register(r'vault-exercises', VaultExerciseViewSet, basename='vault-exercise')
router.register(r'vault-materials', VaultMaterialViewSet, basename='vault-material')
router.register(r'student-notebooks', StudentNotebookViewSet, basename='student-notebook')
router.register(r'notebook-pages', NotebookPageViewSet, basename='notebook-page')
router.register(r'cnp-teacher-guides', CNPTeacherGuideViewSet, basename='cnp-teacher-guide')

# Inspection System routes (Inspector & GPI)
router.register(r'inspection/regions', RegionViewSet, basename='inspection-region')
router.register(r'inspection/inspector-dashboard', InspectorDashboardViewSet, basename='inspector-dashboard')
router.register(r'inspection/gpi-dashboard', GPIDashboardViewSet, basename='gpi-dashboard')
router.register(r'inspection/complaints', TeacherComplaintViewSet, basename='teacher-complaint')
router.register(r'inspection/visits', InspectionVisitViewSet, basename='inspection-visit')
router.register(r'inspection/reports', InspectionReportViewSet, basename='inspection-report')
router.register(r'inspection/monthly-reports', MonthlyReportViewSet, basename='monthly-report')
router.register(r'inspection/rating-history', TeacherRatingHistoryViewSet, basename='rating-history')

# Delegation (Inspector/Advisor) routes
router.register(r'delegation-teachers', DelegationTeacherViewSet, basename='delegation-teacher')
router.register(r'delegation-advisors', DelegationAdvisorViewSet, basename='delegation-advisor')
router.register(r'teacher-advisor-assignments', TeacherAdvisorAssignmentViewSet, basename='teacher-advisor-assignment')
router.register(r'teacher-inspections', TeacherInspectionViewSet, basename='teacher-inspection')
router.register(r'inspection-reviews', InspectionReviewViewSet, basename='inspection-review')
router.register(r'delegation-dashboard', DelegationDashboardViewSet, basename='delegation-dashboard')

# Notification routes
router.register(r'notifications', NotificationViewSet, basename='notification')

# Advisor routes
router.register(r'advisor-inspections', AdvisorInspectionViewSet, basename='advisor-inspection')
router.register(r'advisor-dashboard', AdvisorDashboardViewSet, basename='advisor-dashboard')

# Attendance routes
router.register(r'teacher-attendance', TeacherAttendanceViewSet, basename='teacher-attendance')
router.register(r'student-attendance', StudentAttendanceViewSet, basename='student-attendance')
router.register(r'attendance-summaries', AttendanceSummaryViewSet, basename='attendance-summary')
router.register(r'secretary/tasks', TaskViewSet, basename='secretary-tasks')
router.register(r'secretary/meetings', MeetingViewSet, basename='secretary-meetings')
router.register(r'secretary/decisions', DecisionViewSet, basename='secretary-decisions')
router.register(r'secretary/documents', DocumentViewSet, basename='secretary-documents')



# Inspector Assignment routes
router.register(r'inspector-assignments', InspectorAssignmentViewSet, basename='inspector-assignment')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/minister-analytics/', minister_analytics, name='minister-analytics'),
    path('api/lesson-performance/<int:lesson_id>/', lesson_performance, name='lesson-performance'),
    path('api/analytics/hr-overview/', hr_overview, name='hr-overview'),
    path('api/analytics/hr-users/', hr_all_users, name='hr-all-users'),
    path('api/analytics/hr-teacher-performance/', hr_teacher_performance, name='hr-teacher-performance'),
    path('api/analytics/hr-student-performance/', hr_student_performance, name='hr-student-performance'),
    path('api/analytics/ministry-hr-by-region/', ministry_hr_by_region, name='ministry-hr-by-region'),
    path('api/regional-education-search/', regional_education_search, name='regional-education-search'),
    path('api/forum/', include('core.forum_urls')),  # Forum URLs
    path('api/chatbot/', include('core.chat_urls')),  # AI Chat URLs
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
