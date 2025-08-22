from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied, NotFound
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from django.db.models import Max
from .permissions import IsCreatorOrEnrolled, IsQuizInstructor, IsCourseInstructor
from django.utils import timezone
from django.db import transaction
from django.db.models import Prefetch, OuterRef
from django.utils.timezone import now
from rest_framework.response import Response
from .models import (Course, Lesson, Assignment, 
                     Enrollment, LessonProgress, CourseRequirement, 
                     CourseOutcome, CourseModule, Quiz, LessonContent,
                     Question, QuizAttempt, Resource)
from .serializers import (
    CourseSerializer, LessonSerializer, AssignmentSerializer, 
    EnrollmentSerializer, LessonProgressSerializer, CourseDetailSerializer, 
    ModuleCreateSerializer, QuestionSerializer,LessonContentSerializer, ResourceSerializer,
    BulkCourseOutcomeSerializer, BulkCourseRequirementSerializer, CourseOutcomeSerializer,CourseRequirementSerializer, 
    QuizSerializer, QuizListSerializer, 
    QuizAttemptSerializer, QuizResultSerializer, QuizDashboardSerializer, StudentEnrollmentSerializer
)
import json
import random
import logging
logger = logging.getLogger(__name__)
import requests
from django.conf import settings

# Paystack Integration
class PaymentInitializeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        course_id = request.data.get("course_id")
        email = request.data.get("email")
        amount = request.data.get("amount")  # Amount in pesewas

        if not all([course_id, email, amount]):
            return Response(
                {"detail": "course_id, email, and amount are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            course = Course.objects.get(id=course_id)
            if Enrollment.objects.filter(student=request.user, course=course).exists():
                return Response(
                    {"detail": "You are already enrolled in this course"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Initialize Paystack transaction
            headers = {
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "email": email,
                "amount": int(amount),  # Ensure amount is an integer
                "currency": "GHS",
                "metadata": {
                    "course_id": course_id,
                    "user_id": request.user.id,
                },
            }
            response = requests.post(
                "https://api.paystack.co/transaction/initialize",
                json=payload,
                headers=headers,
            )
            response_data = response.json()

            if response.status_code != 200 or not response_data.get("status"):
                logger.error(f"Paystack initialization failed: {response_data}")
                return Response(
                    {"detail": "Failed to initialize payment"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response({
                "access_code": response_data["data"]["access_code"],
                "reference": response_data["data"]["reference"],
            })
        except Course.DoesNotExist:
            return Response(
                {"detail": "Course not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Payment initialization error: {str(e)}")
            return Response(
                {"detail": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PaymentVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        reference = request.data.get("reference")
        course_id = request.data.get("course_id")

        if not all([reference, course_id]):
            return Response(
                {"detail": "reference and course_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Verify Paystack transaction
            headers = {
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json",
            }
            response = requests.get(
                f"https://api.paystack.co/transaction/verify/{reference}",
                headers=headers,
            )
            response_data = response.json()

            if response.status_code != 200 or not response_data.get("status"):
                logger.error(f"Paystack verification failed: {response_data}")
                return Response(
                    {"detail": "Payment verification failed"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if response_data["data"]["status"] != "success":
                return Response(
                    {"detail": "Payment was not successful"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Ensure the payment amount and metadata match
            course = Course.objects.get(id=course_id)
            expected_amount = int(course.price * 100)  # Convert to pesewas
            paid_amount = response_data["data"]["amount"]
            metadata = response_data["data"]["metadata"]

            if paid_amount != expected_amount or metadata.get("course_id") != course_id:
                logger.error(f"Payment validation failed: amount or metadata mismatch")
                return Response(
                    {"detail": "Invalid payment details"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Enroll the user atomically
            with transaction.atomic():
                enrollment, created = Enrollment.objects.get_or_create(
                    student=request.user,
                    course_id=course_id,
                    defaults={"enrolled_at": timezone.now()}
                )
                if not created:
                    return Response(
                        {"detail": "You are already enrolled in this course"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            return Response({
                "status": "success",
                "enrollment": EnrollmentSerializer(enrollment).data,
            })
        except Course.DoesNotExist:
            return Response(
                {"detail": "Course not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Payment verification error: {str(e)}")
            return Response(
                {"detail": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

class InstructorProgressOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id=None):
        courses = Course.objects.filter(instructor=request.user, is_published=True)
        if course_id:
            courses = courses.filter(id=course_id)
        
        result = []
        for course in courses:
            total_lessons = Lesson.objects.filter(module__course=course).count()
            enrollments = Enrollment.objects.filter(course=course).prefetch_related(
                'student__lesson_progress'
            )
            
            completed = 0
            in_progress = 0
            incomplete = 0
            
            for enrollment in enrollments:
                completed_lessons = LessonProgress.objects.filter(
                    student=enrollment.student,
                    lesson__module__course=course,
                    completed=True
                ).count()
                progress_percent = (
                    (completed_lessons / total_lessons * 100) if total_lessons else 0
                )
                
                if progress_percent == 100:
                    completed += 1
                elif progress_percent > 0:
                    in_progress += 1
                elif progress_percent == 0:
                    incomplete += 1
            
            result.append({
                'course_id': course.id,
                'course_title': course.title,
                'completed': completed,
                'in_progress': in_progress,
                'incomplete': incomplete
            })
        
        return Response(result)

class InstructorDashboardOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Fetch counts for the dashboard
        courses = Course.objects.filter(instructor=request.user)
        total_courses = courses.count()
        published_courses = courses.filter(is_published=True).count()
        draft_courses = courses.filter(is_published=False).count()
        
        # Count unique students across all courses
        total_enrolled_students = (
            Enrollment.objects
            .filter(course__instructor=request.user)
            .values('student')
            .distinct()
            .count()
        )

        return Response({
            'total_courses': total_courses,
            'total_enrolled_students': total_enrolled_students,
            'published_courses': published_courses,
            'draft_courses': draft_courses
        })

class UserDashboardView(APIView):
    def get(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        # Optimize queries with select_related and prefetch_related
        courses = Course.objects.filter(
            enrollments__student=user
        ).select_related('instructor').prefetch_related(
            Prefetch('modules', queryset=CourseModule.objects.prefetch_related('lessons'))
        ).distinct()

        quizzes = Quiz.objects.filter(
            lesson__module__course__enrollments__student=user
        ).select_related('lesson__module__course')

        lesson_progress = LessonProgress.objects.filter(
            student=user,
            lesson__module__course__enrollments__student=user
        ).select_related('lesson')

        course_data = CourseSerializer(courses, many=True, context={'request': request}).data
        quiz_data = QuizDashboardSerializer(quizzes, many=True, context={'request': request}).data
        lesson_progress_data = [
            {
                'lesson_id': progress.lesson.id,
                'completed': progress.completed,
                'completed_at': progress.completed_at,
            }
            for progress in lesson_progress
        ]

        return Response({
            'courses': course_data,
            'quizzes': quiz_data,
            'lesson_progress': lesson_progress_data,
            'upcoming_assignments': [],
        })
    
class StudentDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StudentEnrollmentSerializer

    def get_object(self):
        student_id = self.kwargs.get('id')
        enrollment = get_object_or_404(Enrollment, id=student_id, course__instructor=self.request.user)
        return enrollment


class StudentListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StudentEnrollmentSerializer

    def get_queryset(self):
        course_id = self.kwargs.get('course_id')
        course = get_object_or_404(Course, id=course_id, instructor=self.request.user)
        return Enrollment.objects.filter(
            course=course
        ).select_related('student')

    def get(self, request, *args, **kwargs):
        course_id = kwargs.get('course_id')
        if not Course.objects.filter(id=course_id, instructor=self.request.user).exists():
            return Response({"detail": "Course not found or unauthorized"}, status=403)
        return super().get(request, *args, **kwargs)
    

# Course Views
class PublicCourseListView(generics.ListAPIView):
    queryset = Course.objects.filter(is_published=True)
    serializer_class = CourseSerializer
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        print(f"Public GET request to {request.path} by {request.user}")
        return response

class InstructorCourseListView(generics.ListCreateAPIView):
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Course.objects.filter(instructor=self.request.user)

    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)  # Automatically set instructor

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        print(f"Instructor GET request to {request.path} by {request.user}")
        print(f"Response: {response.data}")  # Print the response data to the console
        return response

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        print(f"Instructor POST to {request.path} by {request.user}")
        print(f"Response: {response.data}")  # Print the response data to the console

        return response
    
class PublicCourseDetailView(generics.RetrieveAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseDetailSerializer
    permission_classes = [permissions.AllowAny]  # No login needed

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        print(f"Public GET course detail {request.path} by {request.user}")
        print(f"Response: {response.data}")
        return response
    
class InstructorCourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Course.objects.filter(instructor=self.request.user)

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        print(f"Instructor GET {request.path} by {request.user}")
        return response

    def put(self, request, *args, **kwargs):
        response = super().put(request, *args, **kwargs)
        print(f"Instructor PUT {request.path} by {request.user}")
        return response

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        print(f"Instructor DELETE {request.path} by {request.user}")
        return response

class BulkCourseOutcomeView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsCourseInstructor]

    def post(self, request):
        course_id = request.data.get('course')
        if not course_id:
            return Response({"detail": "course_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = BulkCourseOutcomeSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    course = Course.objects.get(id=course_id)
                    if course.instructor != request.user:
                        return Response({"detail": "You are not authorized to modify this course"}, status=status.HTTP_403_FORBIDDEN)
                    outcomes_data = serializer.validated_data.get('outcomes', [])
                    created_outcomes = []
                    for outcome_data in outcomes_data:
                        outcome = CourseOutcome(
                            course=course,
                            text=outcome_data['text'],
                            position=outcome_data.get('position', 0)
                        )
                        outcome.save()
                        created_outcomes.append(CourseOutcomeSerializer(outcome).data)
                    return Response({
                        "detail": "Course outcomes created successfully",
                        "outcomes": created_outcomes
                    }, status=status.HTTP_201_CREATED)
            except Course.DoesNotExist:
                return Response({"detail": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                return Response({"detail": f"Error creating outcomes: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BulkCourseRequirementView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsCourseInstructor]

    def post(self, request):
        course_id = request.data.get('course_id')
        if not course_id:
            return Response({"detail": "course_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = BulkCourseRequirementSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    course = Course.objects.get(id=course_id)
                    if course.instructor != request.user:
                        return Response({"detail": "You are not authorized to modify this course"}, status=status.HTTP_403_FORBIDDEN)
                    requirements_data = serializer.validated_data.get('requirements', [])
                    created_requirements = []
                    for req_data in requirements_data:
                        requirement = CourseRequirement(
                            course=course,
                            text=req_data['text'],
                            position=req_data.get('position', 0)
                        )
                        requirement.save()
                        created_requirements.append(CourseRequirementSerializer(requirement).data)
                    return Response({
                        "detail": "Course requirements created successfully",
                        "requirements": created_requirements
                    }, status=status.HTTP_201_CREATED)
            except Course.DoesNotExist:
                return Response({"detail": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                return Response({"detail": f"Error creating requirements: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CourseOutcomeListCreateView(generics.ListCreateAPIView):
    serializer_class = CourseOutcomeSerializer
    permission_classes = [permissions.IsAuthenticated, IsCourseInstructor]

    def get_queryset(self):
        course_id = self.kwargs.get('course_id')
        return CourseOutcome.objects.filter(course_id=course_id)

    def perform_create(self, serializer):
        course_id = self.kwargs.get('course_id')
        course = get_object_or_404(Course, id=course_id)
        if course.instructor != self.request.user:
            raise PermissionDenied("You are not authorized to add outcomes to this course")
        max_position = CourseOutcome.objects.filter(course_id=course_id).aggregate(Max('position'))['position__max'] or 0
        serializer.save(course=course, position=max_position + 1)

class CourseOutcomeDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CourseOutcomeSerializer
    permission_classes = [permissions.IsAuthenticated, IsCourseInstructor]

    def get_queryset(self):
        course_id = self.kwargs.get('course_id')
        return CourseOutcome.objects.filter(course_id=course_id)

    def get_object(self):
        obj = super().get_object()
        if obj.course.instructor != self.request.user:
            raise PermissionDenied("You are not authorized to modify this outcome")
        return obj

class CourseRequirementListCreateView(generics.ListCreateAPIView):
    serializer_class = CourseRequirementSerializer
    permission_classes = [permissions.IsAuthenticated, IsCourseInstructor]

    def get_queryset(self):
        course_id = self.kwargs.get('course_id')
        return CourseRequirement.objects.filter(course_id=course_id)

    def perform_create(self, serializer):
        course_id = self.kwargs.get('course_id')
        course = get_object_or_404(Course, id=course_id)
        if course.instructor != self.request.user:
            raise PermissionDenied("You are not authorized to add requirements to this course")
        max_position = CourseRequirement.objects.filter(course_id=course_id).aggregate(Max('position'))['position__max'] or 0
        serializer.save(course=course, position=max_position + 1)

class CourseRequirementDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CourseRequirementSerializer
    permission_classes = [permissions.IsAuthenticated, IsCourseInstructor]

    def get_queryset(self):
        course_id = self.kwargs.get('course_id')
        return CourseRequirement.objects.filter(course_id=course_id)

    def get_object(self):
        obj = super().get_object()
        if obj.course.instructor != self.request.user:
            raise PermissionDenied("You are not authorized to modify this requirement")
        return obj
    

# Lesson Views
class CourseSpecificLessons(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id, format=None):
        lessons = Lesson.objects.filter(course=id)
        serializer = LessonSerializer(lessons, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class LessonListCreateView(generics.ListCreateAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        print(f"GET request to {request.path} by {request.user}")
        print(f"Response: {response.data}")  # Print the response data to the console
        return response

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        print(f"POST request to {request.path} by {request.user}")
        print(f"Response: {response.data}")  # Print the response data to the console
        return response

class LessonDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated] 

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        print(f"GET request to {request.path} by {request.user}")
        print(f"Response: {response.data}")  # Print the response data to the console
        return response

    def put(self, request, *args, **kwargs):
        instance = self.get_object()
        print(f"PUT request to {request.path} by {request.user}")
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        if serializer.is_valid():
            with transaction.atomic():
                self.perform_update(serializer)
            return Response(serializer.data)
        # print(f"Response: {Response}")  # Print the response data to the console
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def perform_update(self, serializer):
        serializer.save()

    # def put(self, request, *args, **kwargs):
    #     response = super().put(request, *args, **kwargs)
    #     print(f"PUT request to {request.path} by {request.user}")
    #     print(f"Response: {response.data}")  # Print the response data to the console
    #     return response

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        print(f"DELETE request to {request.path} by {request.user}")
        print(f"Response: {response.data}")  # Print the response data to the console
        return response

class LessonContentListCreateView(generics.ListCreateAPIView):
    serializer_class = LessonContentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Retrieve LessonContent for a specific lesson based on the lesson_id from URL kwargs
        lesson_id = self.kwargs.get('pk')
        lesson = get_object_or_404(Lesson, id=lesson_id)
        return LessonContent.objects.filter(lesson=lesson).order_by('position')

    def get(self, request, *args, **kwargs):
        # Optimize response by prefetching related data if needed (currently none for LessonContent)
        response = super().get(request, *args, **kwargs)
        print(f"GET request to /lessons/{kwargs['pk']}/contents/ by {request.user}")
        print(f"Response: {response.data}")
        return response

    def post(self, request, *args, **kwargs):
        # Ensure the lesson exists and the user has permission to modify it
        lesson_id = kwargs.get('pk')
        lesson = get_object_or_404(Lesson, id=lesson_id)
        if lesson.course.instructor != request.user:
            return Response({"detail": "You are not authorized to modify this lesson's content"}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            with transaction.atomic():
                # Assign the lesson to the new content and save
                serializer.validated_data['lesson'] = lesson
                self.perform_create(serializer)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        # Automatically set the position based on the current max position + 1
        lesson_id = self.kwargs.get('pk')
        max_position = LessonContent.objects.filter(lesson_id=lesson_id).aggregate(Max('position'))['position__max'] or 0
        serializer.save(position=max_position + 1)

class LessonResourcesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lesson_id):
        try:
            lesson = get_object_or_404(Lesson, id=lesson_id)
            is_enrolled = lesson.course.enrollments.filter(student=request.user).exists()
            if not is_enrolled:
                return Response(
                    {"detail": "You are not enrolled in the course containing this lesson"},
                    status=status.HTTP_403_FORBIDDEN
                )
            resources = Resource.objects.filter(lesson_id=lesson_id).order_by('position')
            serializer = ResourceSerializer(resources, many=True)
            return Response({
                "lesson_id": lesson_id,
                "lesson_title": lesson.title,
                "resources": serializer.data
            })
        except Exception as e:
            logger.error(f"Error fetching resources for lesson {lesson_id}: {str(e)}")
            return Response(
                {"detail": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ModuleCreateView(generics.ListCreateAPIView):
    queryset = CourseModule.objects.all()
    serializer_class = ModuleCreateSerializer
    permission_classes = [permissions.IsAuthenticated]  # Only Course Instructor or Admin can create

    # Creating module
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        print(f"POST request to {request.path} by {request.user}")
        print(f"Response: {response.data}")  # Print the response data to the console
        return response
    
    # Get module data
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        print(f"GET request to {request.path} by {request.user}")
        print(f"Response: {response.data}")  # Print the response data to the console
        return response
    
class ModuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CourseModule.objects.all()
    serializer_class = ModuleCreateSerializer
    permission_classes = [permissions.IsAuthenticated]  # Only Enrolled Students, Instructors, or Admins can view/edit

    # Get module data
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        print(f"GET request to {request.path} by {request.user}")
        print(f"Response: {response.data}")  # Print the response data to the console
        return response
    
    # Update module
    def put(self, request, *args, **kwargs):
        response = super().put(request, *args, **kwargs)
        print(f"PUT request to {request.path} by {request.user}")
        print(f"Response: {response.data}")  # Print the response data to the console
        return response
    
    # Delete module
    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        print(f"DELETE request to {request.path} by {request.user}")
        print(f"Response: {response.data}")  # Print the response data to the console
        return response
    
class QuizListCreateView(generics.ListCreateAPIView):
    serializer_class = QuizListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Filter by lesson if provided
        queryset = Quiz.objects.all()
        course_id = self.request.query_params.get('course_id')
        lesson_id = self.request.query_params.get('lesson_id')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        if lesson_id:
            queryset = queryset.filter(lesson_id=lesson_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class QuizDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticated, IsCreatorOrEnrolled]

class QuestionListCreateView(generics.ListCreateAPIView):
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticated, IsQuizInstructor]

    def get_queryset(self):
        quiz_id = self.request.query_params.get('quiz_id')
        if not quiz_id:
            raise NotFound("quiz_id is required")
        return Question.objects.filter(quiz_id=quiz_id).prefetch_related('quiz')

    def perform_create(self, serializer):
        quiz_id = self.request.data.get('quiz')
        if not quiz_id:
            raise NotFound("quiz_id is required")
        try:
            quiz = Quiz.objects.get(id=quiz_id)
            logger.info(f"Creating question for quiz {quiz_id} with data: {self.request.data}")
            serializer.save(quiz=quiz)
        except Quiz.DoesNotExist:
            raise NotFound("Quiz not found")

class QuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticated, IsQuizInstructor]

    def get_object(self):
        question = super().get_object()
        if question.quiz.lesson.module.course.instructor != self.request.user:
            raise PermissionDenied("You are not authorized to modify this question")
        return question

class LessonQuizzesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, lesson_id):
        try:
            lesson = get_object_or_404(Lesson, id=lesson_id)
            
            # Check if user is enrolled in the course
            is_enrolled = lesson.course.enrollments.filter(student=request.user).exists()
            if not is_enrolled:
                return Response(
                    {"detail": "You are not enrolled in this course."}, 
                    status=status.HTTP_403_FORBIDDEN
                )

            # Get active quizzes for this lesson
            quizzes = Quiz.objects.filter(lesson_id=lesson_id, is_active=True)
            
            # Add attempt information for each quiz
            quiz_data = []
            for quiz in quizzes:
                # Get user's attempts for this quiz
                attempts = QuizAttempt.objects.filter(
                    student=request.user, 
                    quiz=quiz
                ).order_by('-started_at')
                
                quiz_info = QuizListSerializer(quiz).data
                quiz_info['attempts_count'] = attempts.count()
                quiz_info['max_attempts'] = quiz.max_attempts
                quiz_info['can_attempt'] = attempts.count() < quiz.max_attempts
                
                if attempts.exists():
                    best_attempt = attempts.order_by('-score').first()
                    quiz_info['best_score'] = best_attempt.score
                    quiz_info['passed'] = best_attempt.passed
                    quiz_info['last_attempt'] = QuizResultSerializer(attempts.first()).data
                else:
                    quiz_info['best_score'] = None
                    quiz_info['passed'] = False
                    quiz_info['last_attempt'] = None
                
                quiz_data.append(quiz_info)
            
            return Response({
                'lesson_id': lesson_id,
                'lesson_title': lesson.title,
                'quizzes': quiz_data
            })
            
        except Exception as e:
            return Response(
                {"detail": f"An error occurred: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class QuizTakeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, quiz_id):
        user = request.user
        try:
            quiz = Quiz.objects.get(id=quiz_id)
            attempt_count = QuizAttempt.objects.filter(student=user, quiz=quiz).count()
            if quiz.max_attempts and attempt_count >= quiz.max_attempts:
                logger.warning(f"No attempts remaining for quiz {quiz_id} by user {user}")
                return Response(
                    {"error": "No attempts remaining"},
                    status=status.HTTP_403_FORBIDDEN
                )
            quiz_data = QuizSerializer(quiz, context={'request': request}).data
            response_data = {"quiz": quiz_data}
            logger.info(f"GET /quizzes/{quiz_id}/take/ by {user} - Success")
            return Response(response_data, status=status.HTTP_200_OK)
        except Quiz.DoesNotExist:
            logger.error(f"Quiz {quiz_id} not found for user {user}")
            return Response(
                {"error": "Quiz not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in GET /quizzes/{quiz_id}/take/ by {user}: {str(e)}")
            return Response(
                {"error": f"Server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class QuizSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, quiz_id):
        try:
            quiz = Quiz.objects.filter(id=quiz_id).first()
            if not quiz:
                return Response({"detail": "Quiz not found"}, status=status.HTTP_404_NOT_FOUND)

            # Check if user can attempt
            attempts = QuizAttempt.objects.filter(quiz=quiz.id, student=request.user).count()
            if not quiz.is_active or attempts >= quiz.max_attempts:
                return Response(
                    {"detail": "No attempts remaining or quiz is not available"},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Get answers
            answers = request.data.get('answers', {})
            time_taken = request.data.get('time_taken', 0)

            # Validate answers
            questions = Question.objects.filter(quiz=quiz)
            if not questions.exists():
                return Response({"detail": "No questions found"}, status=status.HTTP_400_BAD_REQUEST)

            # Calculate score
            score = 0
            total_points = 0
            correct_answers = 0
            total_questions = questions.count()
            detailed_results = {}

            for question in questions:
                user_answer = answers.get(str(question.id))
                correct_answer = question.correct_answer
                if question.question_type == 'multiple_choice_multiple':
                    correct = isinstance(user_answer, list) and sorted(user_answer) == sorted(json.loads(correct_answer))
                elif question.question_type == 'short_answer':
                    correct = user_answer.strip().lower() == correct_answer.strip().lower()
                else:
                    correct = user_answer == correct_answer

                if correct:
                    score += question.points
                    correct_answers += 1

                total_points += question.points
                detailed_results[question.id] = {
                    'question': question.text,
                    'your_answer': user_answer,
                    'correct_answer': correct_answer,
                    'is_correct': correct,
                    'explanation': question.explanation,
                }

            # Save attempt
            QuizAttempt.objects.create(
                quiz=quiz,
                student=request.user,
                score=score,
                time_taken=time_taken,
                answers=answers
            )

            # Response
            result = {
                'score': (score / total_points * 100) if total_points > 0 else 0,
                'total_points': total_points,
                'correct_answers': correct_answers,
                'total_questions': total_questions,
                'passed': score >= quiz.passing_score * total_points / 100,
                'attempts_remaining': max(0, quiz.max_attempts - attempts - 1),
                'detailed_results': detailed_results
            }

            return Response(result, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"Error in QuizSubmitView: {str(e)}")
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class QuizAttemptListView(generics.ListAPIView):
    serializer_class = QuizAttemptSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        quiz_id = self.kwargs.get('quiz_id')
        if quiz_id:
            return QuizAttempt.objects.filter(
                quiz_id=quiz_id,
                student=self.request.user
            ).order_by('-started_at')
        return QuizAttempt.objects.filter(student=self.request.user).order_by('-started_at')

class QuizAttemptDetailView(generics.RetrieveAPIView):
    serializer_class = QuizAttemptSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return QuizAttempt.objects.filter(student=self.request.user)

class QuizResultsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, quiz_id):
        user = request.user
        try:
            quiz = Quiz.objects.get(id=quiz_id)
            latest_attempt = QuizAttempt.objects.filter(
                user=user,
                quiz=quiz
            ).order_by('-attempt_number').first()

            if not latest_attempt:
                logger.warning(f"No attempts found for quiz {quiz_id} by user {user}")
                return Response(
                    {"error": "No quiz attempts found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            detailed_results = {}
            for answer in latest_attempt.answers:
                question = Question.objects.get(id=answer.question_id)
                is_correct = answer.is_correct
                your_answer = answer.selected_answers
                correct_answer = question.correct_answer
                detailed_results[question.id] = {
                    "question": question.text,
                    "your_answer": your_answer,
                    "correct_answer": correct_answer,
                    "is_correct": is_correct,
                    "explanation": question.explanation or ""
                }

            response_data = {
                "results": {
                    "score": latest_attempt.score,
                    "total_points": latest_attempt.total_points,
                    "attempts_remaining": quiz.max_attempts - latest_attempt.attempt_number,
                    "detailed_results": detailed_results
                }
            }
            logger.info(f"GET /quizzes/{quiz_id}/results/ by {user} - Success")
            return Response(response_data, status=status.HTTP_200_OK)
        except Quiz.DoesNotExist:
            logger.error(f"Quiz {quiz_id} not found for user {user}")
            return Response(
                {"error": "Quiz not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in GET /quizzes/{quiz_id}/results/ by {user}: {str(e)}")
            return Response(
                {"error": f"Server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Assignment Views
class AssignmentListCreateView(generics.ListCreateAPIView):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]  # Only Course Instructor or Admin can create

class AssignmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]  # Only Enrolled Students, Instructors, or Admins can view/edit

# Enrollment View
# class EnrollmentView(generics.CreateAPIView):
#     queryset = Enrollment.objects.all()
#     serializer_class = EnrollmentSerializer
#     permission_classes = [IsAuthenticated]  # Any logged-in user can enroll

#     def get_serializer_context(self):
#         return {"request": self.request}
    
#     def create(self, request, *args, **kwargs):
#         print("Request content type:", request.content_type)  # Debug the content type
#         print("Request data:", request.data)  # Debug the received data

#         course_id = request.data.get('course_id')
#         if not course_id:
#             return Response({"detail": "course_id is required"}, status=400)
            
#         # Check if already enrolled
#         if Enrollment.objects.filter(student=request.user, course_id=course_id).exists():
#             return Response({"detail": "Already enrolled in this course"}, status=400)
            
#         # Create enrollment
#         enrollment = Enrollment(student=request.user, course_id=course_id)
#         enrollment.save()
        
#         return Response(EnrollmentSerializer(enrollment).data, status=201)
    

class EnrollmentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        course_id = request.data.get("course_id")
        if not course_id:
            return Response({"detail": "course_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            course = Course.objects.get(id=course_id)
            if Enrollment.objects.filter(student=request.user, course=course).exists():
                return Response({"detail": "You are already enrolled in this course"}, status=status.HTTP_400_BAD_REQUEST)

            # For free courses (price = 0), allow direct enrollment
            if course.price == 0:
                with transaction.atomic():
                    enrollment = Enrollment.objects.create(
                        student=request.user,
                        course=course,
                        enrolled_at=timezone.now()
                    )
                return Response(EnrollmentSerializer(enrollment).data, status=status.HTTP_201_CREATED)

            return Response(
                {"detail": "Payment required for this course"},
                status=status.HTTP_402_PAYMENT_REQUIRED
            )
        except Course.DoesNotExist:
            return Response({"detail": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Enrollment error: {str(e)}")
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EnrollmentCheckView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id):
        """Check if the current user is enrolled in a specific course"""
        enrollment_exists = Enrollment.objects.filter(
            student=request.user,
            course_id=course_id
        ).exists()
        course_requirement = CourseRequirement.objects.filter(
            course_id=course_id
        )
        return Response({
            "enrolled": enrollment_exists
        })

# Lesson Progress Tracking
class LessonProgressView(generics.CreateAPIView):
    queryset = LessonProgress.objects.all()
    serializer_class = LessonProgressSerializer
    permission_classes = [permissions.IsAuthenticated]  #Only Enrolled Students, Instructors, or Admins can track progress

    def get_serializer_context(self):
        return {"request": self.request}
    
class EnrolledCourseDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        try:
            print(f"DEBUG: Processing request for course {course_id} by user {request.user.id}")
            enrollment_exists = Enrollment.objects.filter(
                student=request.user,
                course_id=course_id
            ).exists()
            print(f"DEBUG: User enrolled: {enrollment_exists}")
            if not enrollment_exists:
                return Response(
                    {"detail": "Course not found or you're not enrolled in this course"},
                    status=status.HTTP_404_NOT_FOUND
                )
            course = Course.objects.filter(id=course_id).prefetch_related(
                Prefetch('modules', queryset=CourseModule.objects.prefetch_related(
                    Prefetch('lessons', queryset=Lesson.objects.prefetch_related('contents', 'quizzes', 'assignments', 'resources'))
                ))
            ).first()
            print(f"DEBUG: Course found: {course is not None}")
            if not course:
                return Response({"detail": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
            completed_lessons = set(
                LessonProgress.objects.filter(
                    student=request.user,
                    lesson__course=course,
                    completed=True
                ).values_list('lesson_id', flat=True)
            )
            print(f"DEBUG: Found {len(completed_lessons)} completed lessons")
            serializer = CourseSerializer(
                course,
                context={'request': request, 'completed_lessons': completed_lessons}
            )
            print(f"DEBUG: Successfully built response for course {course_id}")
            return Response(serializer.data)
        except Exception as e:
            import traceback
            print(f"ERROR: Exception in EnrolledCourseDetailView: {str(e)}")
            traceback.print_exc()
            return Response(
                {"detail": "An error occurred while fetching the course"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ResourceDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    permission_classes = [permissions.IsAuthenticated, IsCourseInstructor]

    def get_object(self):
        resource = super().get_object()
        if resource.lesson.course.instructor != self.request.user:
            raise PermissionDenied("You are not authorized to modify this resource")
        return resource

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        logger.info(f"GET request to {request.path} by {request.user}")
        logger.info(f"Response: {response.data}")
        return response

    def put(self, request, *args, **kwargs):
        response = super().put(request, *args, **kwargs)
        logger.info(f"PUT request to {request.path} by {request.user}")
        logger.info(f"Response: {response.data}")
        return response

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        logger.info(f"DELETE request to {request.path} by {request.user}")
        logger.info(f"Response: {response.data}")
        return response

class EnrollmentProgressView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id):
        """Get progress data for an enrolled course"""
        try:
            # Check if user is enrolled
            enrollment = Enrollment.objects.filter(
                student=request.user,
                course_id=course_id
            ).first()
            
            if not enrollment:
                return Response({"detail": "Not enrolled in this course"}, status=404)
                
            # Get lessons for this course
            lessons = Lesson.objects.filter(course_id=course_id)
            total_lessons = lessons.count()
            
            # Get completed lessons
            completed_lessons = LessonProgress.objects.filter(
                student=request.user,
                lesson__course_id=course_id,
                completed=True
            ).values_list('lesson_id', flat=True)
            
            # Calculate progress percentage
            completed_count = len(completed_lessons)
            overall_progress = round((completed_count / total_lessons) * 100, 1) if total_lessons else 0.0
            
            return Response({
                "overall_progress": overall_progress,
                "completed_lessons": completed_lessons,
                "total_lessons": total_lessons,
                "completed_count": completed_count
            })
            
        except Exception as e:
            print(f"Error fetching progress: {str(e)}")
            return Response({"detail": "An error occurred"}, status=500)
        
class CompleteLessonView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Mark a lesson as complete"""
        course_id = request.data.get('course_id')
        lesson_id = request.data.get('lesson_id')
        
        if not course_id or not lesson_id:
            return Response({"detail": "course_id and lesson_id are required"}, status=400)
            
        # Check if user is enrolled
        enrollment = Enrollment.objects.filter(
            student=request.user,
            course_id=course_id
        ).first()
        
        if not enrollment:
            return Response({"detail": "Not enrolled in this course"}, status=403)
            
        # Get or create progress record
        progress, created = LessonProgress.objects.get_or_create(
            student=request.user,
            lesson_id=lesson_id,
            defaults={'completed': True}
        )
        
        if not created:
            progress.completed = True
            progress.save()
            
        return Response({
            "success": True,
            "lesson_id": lesson_id,
            "completed": True
        })

class LessonAssignmentsView(APIView):
    """
    API endpoint to retrieve all assignments for a specific lesson.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, lesson_id):
        """
        Get all assignments for the specified lesson ID.
        
        Args:
            request: The HTTP request
            lesson_id: The ID of the lesson to get assignments for
        
        Returns:
            Response with serialized assignments data
        """
        try:
            # Verify the lesson exists
            lesson = get_object_or_404(Lesson, id=lesson_id)
            
            # Check if the user is enrolled in the course containing this lesson
            is_enrolled = lesson.course.enrollment_set.filter(student=request.user).exists()
            
            if not is_enrolled:
                return Response(
                    {"detail": "You are not enrolled in the course containing this lesson"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get all assignments for this lesson
            assignments = Assignment.objects.filter(lesson_id=lesson_id)
            
            # Include submission status for each assignment
            assignment_data = []
            for assignment in assignments:
                # Check if the user has submitted this assignment
                has_submitted = assignment.submission_set.filter(student=request.user).exists()
                
                # Get the serialized assignment
                assignment_serialized = AssignmentSerializer(assignment).data
                assignment_serialized['submitted'] = has_submitted
                
                # Add to the results
                assignment_data.append(assignment_serialized)
            
            return Response({
                "lesson_id": lesson_id,
                "lesson_title": lesson.title,
                "assignments": assignment_data
            })
            
        except Exception as e:
            return Response(
                {"detail": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class ModuleReorderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            module_positions = request.data.get('modules', [])
            with transaction.atomic():
                for item in module_positions:
                    module_id = item.get('id')
                    position = item.get('position')
                    module = CourseModule.objects.get(id=module_id, course__instructor=request.user)
                    module.position = position
                    module.save()
            return Response({"detail": "Module order updated"}, status=status.HTTP_200_OK)
        except CourseModule.DoesNotExist:
            return Response({"detail": "Module not found or unauthorized"}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({"detail": f"Error updating module order: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)