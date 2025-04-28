# from rest_framework import permissions

# class IsAdminUser(permissions.BasePermission):
#     """
#     Custom permission to allow only admins to create courses.
#     """
#     def has_permission(self, request, view):
#         return request.user.is_authenticated and request.user.is_staff  # Only admins


# class IsCourseInstructorOrAdmin(permissions.BasePermission):
#     """
#     Custom permission to allow only the assigned instructor or an admin to create/edit content.
#     """

#     def has_permission(self, request, view):
#         if request.method in permissions.SAFE_METHODS:
#             return True  # Allow everyone to view lessons, quizzes, and assignments

#         course_id = request.data.get("course")  # Get course ID from request data
#         if course_id:
#             from .models import Course  # Import here to avoid circular imports
#             course = Course.objects.filter(id=course_id).first()
#             return course and (request.user == course.instructor or request.user.is_staff)  # ✅ Instructor/Admin

#         return False


# class IsEnrolledStudentOrInstructorOrAdmin(permissions.BasePermission):
#     """
#     Custom permission to allow only enrolled students, instructors, or admins to access course content.
#     """

#     def has_permission(self, request, view):
#         if request.method in permissions.SAFE_METHODS:  # Allow read-only requests
#             course_id = request.query_params.get("course") or request.data.get("course")
#             if course_id:
#                 from .models import Course, Enrollment  # Import here to avoid circular imports
#                 course = Course.objects.filter(id=course_id).first()
                
#                 # Check if the user is enrolled, the instructor, or an admin
#                 is_enrolled = Enrollment.objects.filter(course=course, student=request.user).exists()
#                 return is_enrolled or request.user == course.instructor or request.user.is_staff

#         return False  # Deny write operations unless covered by another permission


from rest_framework.permissions import BasePermission

class IsInstructor(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "instructor"

class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "student"

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "admin"