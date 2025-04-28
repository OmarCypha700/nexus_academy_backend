from rest_framework import generics, permissions
from rest_framework import status
from django.db.models import Prefetch, Count, Case, When, IntegerField
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils.timezone import now
from rest_framework.response import Response
from .models import Course, Lesson, Quiz, Question, Assignment, Enrollment, LessonProgress
from .serializers import (
    CourseSerializer, LessonSerializer, QuizSerializer, 
    QuestionSerializer, AssignmentSerializer, EnrollmentSerializer, 
    LessonProgressSerializer
)
# from .permissions import IsCourseInstructorOrAdmin, IsAdminUser, IsEnrolledStudentOrInstructorOrAdmin
import logging

class UserDashboard(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Enrolled courses
        enrollments = Enrollment.objects.filter(student=user).select_related('course')
        courses = [enrollment.course for enrollment in enrollments]

        # Lesson progress
        progress = LessonProgress.objects.filter(student=user)

        # Upcoming assignments
        assignments = Assignment.objects.filter(
            lesson__course__in=courses,
            due_date__gt=now()
        ).order_by("due_date")

        # Quizzes
        quizzes = Quiz.objects.filter(lesson__course__in=courses)

        # Build course progress data
        course_data = []
        for course in courses:
            lessons = course.lessons.all()
            total_lessons = lessons.count()
            completed_lessons = progress.filter(lesson__in=lessons, completed=True).count()
            progress_percent = round((completed_lessons / total_lessons) * 100, 1) if total_lessons else 0.0

            course_data.append({
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "progress_percent": progress_percent,
            })

        return Response({
            "courses": course_data,
            "upcoming_assignments": AssignmentSerializer(assignments, many=True).data,
            "quizzes": QuizSerializer(quizzes, many=True).data,
        })


# Course Views
class CourseListCreateView(generics.ListCreateAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

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

class CourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    # permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        print(f"GET request to {request.path} by {request.user}")
        print(f"Response: {response.data}")  # Print the response data to the console
        return response

    def put(self, request, *args, **kwargs):
        response = super().put(request, *args, **kwargs)
        print(f"PUT request to {request.path} by {request.user}")
        print(f"Response: {response.data}")  # Print the response data to the console
        return response

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        print(f"DELETE request to {request.path} by {request.user}")
        print(f"Response: {response.data}")  # Print the response data to the console
        return response

# Lesson Views
class LessonListCreateView(generics.ListCreateAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]

class LessonDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]  # Only Enrolled Students, Instructors, or Admins can view/edit

# Quiz Views
class QuizListCreateView(generics.ListCreateAPIView):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticated]  # Only Course Instructor or Admin can create

class QuizDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticated]  # Only Enrolled Students, Instructors, or Admins can view/edit

# Question Views
class QuestionListCreateView(generics.ListCreateAPIView):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticated]  # Only Course Instructor or Admin can create

class QuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticated]  # Only Enrolled Students, Instructors, or Admins can view/edit

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
class EnrollmentView(generics.CreateAPIView):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]  # Any logged-in user can enroll

    def get_serializer_context(self):
        return {"request": self.request}
    
    def create(self, request, *args, **kwargs):
        print("Request content type:", request.content_type)  # Debug the content type
        print("Request data:", request.data)  # Debug the received data

        course_id = request.data.get('course_id')
        if not course_id:
            return Response({"detail": "course_id is required"}, status=400)
            
        # Check if already enrolled
        if Enrollment.objects.filter(student=request.user, course_id=course_id).exists():
            return Response({"detail": "Already enrolled in this course"}, status=400)
            
        # Create enrollment
        enrollment = Enrollment(student=request.user, course_id=course_id)
        enrollment.save()
        
        return Response(EnrollmentSerializer(enrollment).data, status=201)
    

class EnrollmentCheckView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id):
        """Check if the current user is enrolled in a specific course"""
        enrollment_exists = Enrollment.objects.filter(
            student=request.user,
            course_id=course_id
        ).exists()
        
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
        """Get detailed course content for enrolled users"""
        try:
            print(f"DEBUG: Processing request for course {course_id} by user {request.user.id}")
            
            # Check if user is enrolled
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
                
            # Get course with all necessary data
            course = Course.objects.filter(id=course_id).first()
            
            print(f"DEBUG: Course found: {course is not None}")
            
            if not course:
                return Response({"detail": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Get lessons with progress info - FIXED: Only order by 'order' if it exists
            try:
                lessons = Lesson.objects.filter(course=course).order_by('position')
                print(f"DEBUG: Lessons ordered by 'order' field, found {lessons.count()} lessons")
            except Exception as field_error:
                print(f"DEBUG: 'order' field error: {str(field_error)}")
                # Fallback if 'order' field doesn't exist
                lessons = Lesson.objects.filter(course=course)
                print(f"DEBUG: Retrieved lessons without ordering, found {lessons.count()} lessons")
            
            # Get completed lessons for this user
            completed_lessons = set(
                LessonProgress.objects.filter(
                    student=request.user,
                    lesson__course=course,
                    completed=True
                ).values_list('lesson_id', flat=True)
            )
            
            print(f"DEBUG: Found {len(completed_lessons)} completed lessons")
            
            # Create response structure
            modules = []  # Placeholder for module structure
            
            # FIXED: Use safer approach to access attributes that might not exist
            for lesson in lessons:
                # Safely get module attributes with defaults
                # title= getattr(lesson, f"{lesson.module.title}")
                module_title = getattr(lesson, 'title', "Main Module")
                module_id = getattr(lesson, 'module_id', 1)
                
                print(f"DEBUG: Processing lesson {lesson.id}, module: {module_title}")
                # print(f"DEBUG: Actual module name {lesson.id}, module: {module_title}")
                
                # Find existing module or create new one
                module = next((m for m in modules if m['id'] == module_id), None)
                if not module:
                    module = {
                        'id': module_id,
                        'title': module_title,
                        'description': '',
                        'lessons': []
                    }
                    modules.append(module)

                # Determine the type of content
                def determine_content_type(lesson):
                    """
                    Determine the primary content type of a lesson based on its attributes.
                    
                    Args:
                        lesson: A Lesson object with various attributes
                        
                    Returns:
                        str: The content type identifier ('video', 'text', 'quiz', 'assignment', etc.)
                    """
                    # Check for video content first
                    if hasattr(lesson, 'video_id') and lesson.video_id:
                        return 'video'
                    
                    # Check for quiz content
                    if Quiz.objects.filter(lesson_id=lesson.id).exists():
                        return 'quiz'
                    
                    # Check for assignments
                    if Assignment.objects.filter(lesson_id=lesson.id).exists():
                        return 'assignment'
                    
                    # Check if it's a text/reading lesson
                    if (hasattr(lesson, 'content') and lesson.content) or (hasattr(lesson, 'text_content') and lesson.text_content):
                        return 'text'
                    
                    # Check for downloadable content
                    if hasattr(lesson, 'attachment') and lesson.attachment:
                        return 'download'
                    
                    # Check for interactive content
                    if hasattr(lesson, 'interactive') and lesson.interactive:
                        return 'interactive'
                    
                    # Default to generic content type
                    return 'content'
                
                # FIXED: Safely get lesson attributes with defaults
                lesson_data = {
                    'id': lesson.id,
                    'title': lesson.title,
                    'type': determine_content_type(lesson),  # Implement this function
                    'duration': getattr(lesson, 'duration', 0),
                    'video_id': getattr(lesson, 'video_id', ''),
                    'description': getattr(lesson, 'description', ''),
                    'completed': lesson.id in completed_lessons
                }
                
                # Add quizzes related to this lesson
                quizzes = Quiz.objects.filter(lesson_id=lesson.id)
                if quizzes.exists():
                    lesson_data['quizzes'] = [{
                        'id': quiz.id,
                        'title': quiz.title
                    } for quiz in quizzes]
                
                # Add assignments related to this lesson
                assignments = Assignment.objects.filter(lesson_id=lesson.id)
                if assignments.exists():
                    lesson_data['assignments'] = [{
                        'id': assignment.id,
                        'title': assignment.title,
                        'description': assignment.description,
                        'due_date': assignment.due_date
                    } for assignment in assignments]

                module['lessons'].append(lesson_data)
            
            # Calculate overall progress
            total_lessons = lessons.count()
            completed_count = len(completed_lessons)
            progress_percent = round((completed_count / total_lessons) * 100, 1) if total_lessons else 0.0
            
            # FIXED: Safely access instructor if it exists
            instructor_name = ""
            if hasattr(course, 'instructor'):
                instructor = course.instructor
                if hasattr(instructor, 'get_full_name'):
                    instructor_name = instructor.get_full_name()
                elif hasattr(instructor, 'username'):
                    instructor_name = instructor.username
            
            response_data = {
                'id': course.id,
                'title': course.title,
                'description': getattr(course, 'description', ''),
                'instructor': instructor_name,
                'duration': getattr(course, 'duration', 0),
                'modules': modules,
                'progress': progress_percent,
                'completed_lessons': list(completed_lessons)
            }
            
            print(f"DEBUG: Successfully built response for course {course_id}")
            return Response(response_data)
            
        except Exception as e:
            import traceback
            print(f"ERROR: Exception in EnrolledCourseDetailView: {str(e)}")
            traceback.print_exc()  # This will print the full stack trace
            return Response(
                {"detail": "An error occurred while fetching the course"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
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

class LessonQuizzesView(APIView):
    """
    API endpoint to retrieve all quizzes for a specific lesson.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, lesson_id):
        """
        Get all quizzes for the specified lesson ID.
        
        Args:
            request: The HTTP request
            lesson_id: The ID of the lesson to get quizzes for
        
        Returns:
            Response with serialized quizzes data
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
            
            # Get all quizzes for this lesson
            quizzes = Quiz.objects.filter(lesson_id=lesson_id)
            
            # Serialize the quizzes
            serializer = QuizSerializer(quizzes, many=True)
            
            return Response({
                "lesson_id": lesson_id,
                "lesson_title": lesson.title,
                "quizzes": serializer.data
            })
            
        except Exception as e:
            return Response(
                {"detail": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )    


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
        

class QuizSubmissionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            quiz = get_object_or_404(Quiz, id=pk)
            lesson = quiz.lesson
            if not lesson.course.enrollment_set.filter(student=request.user).exists():
                return Response(
                    {"detail": "You are not enrolled in the course containing this quiz"},
                    status=status.HTTP_403_FORBIDDEN
                )

            answers = request.data.get("answers", {})
            questions = quiz.questions.all()
            score = 0
            total = sum(q.max_points for q in questions)
            results = []

            for question in questions:
                user_answer = answers.get(str(question.id), "")
                is_correct = False

                if question.type == "mcq":
                    is_correct = user_answer == question.correct_answer
                elif question.type == "fill_in":
                    is_correct = user_answer.strip().lower() == question.correct_answer.strip().lower()
                elif question.type == "short_answer":
                    is_correct = user_answer.strip().lower() in [ans.strip().lower() for ans in question.correct_answer.split("|")]

                score += question.max_points if is_correct else 0
                results.append({
                    "question_id": question.id,
                    "question_text": question.question_text,
                    "user_answer": user_answer,
                    "correct_answer": question.correct_answer,
                    "is_correct": is_correct,
                    "points": question.max_points if is_correct else 0,
                })

            return Response({
                "score": score,
                "total": total,
                "results": results,
            })
        except Exception as e:
            return Response(
                {"detail": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
