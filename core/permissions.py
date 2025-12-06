"""
Custom permissions for CNP dashboard
"""
from rest_framework.permissions import BasePermission


class IsCNPAgent(BasePermission):
    """
    Permission class to check if user is a CNP agent
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'cnp'


class IsAdminOrCNP(BasePermission):
    """
    Permission class to check if user is admin or CNP agent
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['admin', 'cnp']


class IsCNPAgentOrAdmin(BasePermission):
    """
    Allows access to CNP agents and admins
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['cnp', 'admin']


# ============================================================
# INSPECTION SYSTEM PERMISSIONS
# ============================================================

class IsInspector(BasePermission):
    """
    Permission class to check if user is an inspector
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'inspector'


class IsGPI(BasePermission):
    """
    Permission class to check if user is a GPI (General Pedagogical Inspectorate) member
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'gpi'


class IsInspectorOrGPI(BasePermission):
    """
    Permission class to check if user is an inspector or GPI member
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['inspector', 'gpi']


class IsInspectorOrGPIOrAdmin(BasePermission):
    """
    Allows access to inspectors, GPI members, and admins
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['inspector', 'gpi', 'admin']


class IsInspectorOfRegion(BasePermission):
    """
    Check if inspector is assigned to the region related to the resource
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.role == 'admin' or request.user.role == 'gpi':
            return True
        
        if request.user.role != 'inspector':
            return False
        
        # Check if inspector is assigned to the region
        from .models import InspectorRegionAssignment
        
        # Get the region from the object (works for Visit, Report, Teacher, etc.)
        region = None
        if hasattr(obj, 'school') and hasattr(obj.school, 'region'):
            region = obj.school.region
        elif hasattr(obj, 'region'):
            region = obj.region
        elif hasattr(obj, 'teacher') and hasattr(obj.teacher, 'school') and hasattr(obj.teacher.school, 'region'):
            region = obj.teacher.school.region
        
        if not region:
            return False
        
        return InspectorRegionAssignment.objects.filter(
            inspector=request.user,
            region=region
        ).exists()


class CanReviewReport(BasePermission):
    """
    Check if GPI member can review the report
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Only GPI and admin can review
        if request.user.role not in ['gpi', 'admin']:
            return False
        
        # Report must be submitted (not draft)
        if hasattr(obj, 'gpi_status'):
            return obj.gpi_status in ['pending', 'revision_needed']
        
        return True
