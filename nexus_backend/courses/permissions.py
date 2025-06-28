from rest_framework.permissions import BasePermission
from rest_framework import permissions
from .models import Quiz, Course


class IsInstructor(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "instructor"


class IsCourseInstructor(BasePermission):
    def has_permission(self, request, view):
        course_id = request.data.get('course_id') or view.kwargs.get('course_id')
        if course_id:
            try:
                course = Course.objects.get(id=course_id)
                return request.user.is_authenticated and course.instructor == request.user
            except Course.DoesNotExist:
                return False
        return False


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "student"

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "admin"
    

class IsCreatorOrEnrolled(BasePermission):
    """
    Allow GET if user is creator or enrolled.
    Allow PUT/PATCH/DELETE if user is creator.
    """

    def has_object_permission(self, request, view, obj):
        is_creator = obj.created_by == request.user
        is_enrolled = obj.lesson.course.enrollments.filter(student=request.user).exists()

        if request.method in permissions.SAFE_METHODS:  # GET, HEAD, OPTIONS
            return is_creator or is_enrolled

        return is_creator
    

class IsQuizInstructor(permissions.BasePermission):
    def has_permission(self, request, view):
        quiz_id = request.query_params.get('quiz_id') or request.data.get('quiz')
        if quiz_id:
            try:
                quiz = Quiz.objects.select_related('lesson__module__course__instructor').get(id=quiz_id)
                return request.user.is_authenticated and (
                    request.user.role == 'instructor' and
                    quiz.lesson.module.course.instructor == request.user
                )
            except Quiz.DoesNotExist:
                return False
        return request.user.is_authenticated and request.user.role == 'instructor'