from django.urls import path
from .views import (
    # Dashboard 
    InstructorDashboardOverviewView, InstructorProgressOverviewView, 
    StudentListView, StudentDetailView, UserDashboardView,
    
    # Quiz 
    QuizListCreateView, QuizDetailView,
    QuestionListCreateView, QuestionDetailView,
    LessonQuizzesView, QuizTakeView, QuizSubmitView,
    QuizAttemptListView, QuizAttemptDetailView, QuizResultsView,

    # Course 
    PublicCourseListView, PublicCourseDetailView, InstructorCourseListView, 
    InstructorCourseDetailView, BulkCourseOutcomeView, BulkCourseRequirementView, 
    CourseOutcomeListCreateView, CourseOutcomeDetailView, CourseRequirementListCreateView, 
    CourseRequirementDetailView,CourseSpecificLessons,

    # Module
    ModuleCreateView, ModuleDetailView, ModuleReorderView,

    # Lesson 
    LessonListCreateView, LessonDetailView, LessonProgressView, 
    LessonResourcesView, ResourceDetailView,

    # Enrollment
    EnrollmentView, EnrollmentCheckView, EnrolledCourseDetailView, 
    EnrollmentProgressView, CompleteLessonView, 

    # Payment
    PaymentInitializeView,PaymentVerifyView,

    # Assingment
    AssignmentListCreateView, AssignmentDetailView,
)

dashboard_patterns = [
    # =================================
    # Instructor Dashboard Patterns
    # =================================
    # Dashboard Cards
    path('instructor/dashboard-overview/', InstructorDashboardOverviewView.as_view(), name='dashboard-overview'),
    # Dashboard Patterns Pie Chart
    path('instructor/progress-overview/', InstructorProgressOverviewView.as_view(), name='progress-overview'),
    path('instructor/progress-overview/<int:course_id>/', InstructorProgressOverviewView.as_view(), name='progress-overview-course'),

    # Student Management
    path('instructor/courses/<int:course_id>/students/', StudentListView.as_view(), name='student-list'),
    path('instructor/students/<int:id>/', StudentDetailView.as_view(), name='student-detail'),
    
    # =================================
    # User Dashboard Patterns
    # =================================
    path("user-dashboard/", UserDashboardView.as_view(), name='user-dashboard'),

]

quiz_patterns = [
    # Quiz CRUD
    path('quizzes/', QuizListCreateView.as_view(), name='quiz-list-create'),
    path('quizzes/<int:pk>/', QuizDetailView.as_view(), name='quiz-detail'),
    
    # Question CRUD
    path('questions/', QuestionListCreateView.as_view(), name='question-list-create'),
    path('questions/<int:pk>/', QuestionDetailView.as_view(), name='question-detail'),
    
    # Quiz taking and submission
    path('lessons/<int:lesson_id>/quizzes/', LessonQuizzesView.as_view(), name='lesson-quizzes'),
    path('quizzes/<int:quiz_id>/take/', QuizTakeView.as_view(), name='quiz-take'),
    path('quizzes/<int:quiz_id>/submit/', QuizSubmitView.as_view(), name='quiz-submit'),
    path('quizzes/<int:quiz_id>/results/', QuizResultsView.as_view(), name='quiz_results'),
    
    # Quiz attempts
    path('quizzes/<int:quiz_id>/attempts/', QuizAttemptListView.as_view(), name='quiz-attempts'),
    path('quiz-attempts/<int:pk>/', QuizAttemptDetailView.as_view(), name='quiz-attempt-detail'),
    path('my-quiz-attempts/', QuizAttemptListView.as_view(), name='my-quiz-attempts'),
]

course_patterns = [
    # Public Course View
    path("courses/", PublicCourseListView.as_view(), name="course-list"),
    path("courses/<int:pk>/", PublicCourseDetailView.as_view(), name="course-detail"),

    # Instructor Course View
    path("instructor/courses/", InstructorCourseListView.as_view(), name="course-list"),
    path("instructor/courses/<int:pk>/", InstructorCourseDetailView.as_view(), name="course-detail"),

    # Course CRUD patterns
    path("courses/outcomes/bulk-create/", BulkCourseOutcomeView.as_view(), name="bulk-course-outcomes"),
    path("courses/requirements/bulk-create/", BulkCourseRequirementView.as_view(), name="bulk-course-requirements"),
    path("courses/<int:course_id>/outcomes/", CourseOutcomeListCreateView.as_view(), name="course-outcomes"),
    path("courses/<int:course_id>/outcomes/<int:pk>/", CourseOutcomeDetailView.as_view(), name="course-outcome-detail"),
    path("courses/<int:course_id>/requirements/", CourseRequirementListCreateView.as_view(), name="course-requirements"),
    path("courses/<int:course_id>/requirements/<int:pk>/", CourseRequirementDetailView.as_view(), name="course-requirement-detail"),
    path("courses/<int:id>/lessons/", CourseSpecificLessons.as_view(), name="course-specific-lessons"),
]

payment_patterns = [
    path("payments/initialize/", PaymentInitializeView.as_view(), name="payment-initialize"),
    path("payments/verify/", PaymentVerifyView.as_view(), name="payment-verify"),
]

urlpatterns = [
    # Module Patterns
    path("modules/", ModuleCreateView.as_view(), name='module-create'),
    path("modules/<int:pk>/", ModuleDetailView.as_view(), name='module-create'),
    path("modules/reorder/", ModuleReorderView.as_view(), name="module-reorder"),

    # Lesson Pattern
    path("lessons/", LessonListCreateView.as_view(), name="lesson-list"),
    path("lessons/<int:pk>/", LessonDetailView.as_view(), name="lesson-detail"),
    path("lessons/<int:lesson_id>/resources/", LessonResourcesView.as_view(), name="lesson-resources"),
    
    path("resources/<int:pk>/", ResourceDetailView.as_view(), name="resource-detail"),

    # Enrollment Pattern
    path("enrollments/check/<int:course_id>/", EnrollmentCheckView.as_view(), name="enrollment-check"),
    path("enrollments/course/<int:course_id>/", EnrolledCourseDetailView.as_view(), name="enrolled-course-detail"),
    path("enrollments/progress/<int:course_id>/", EnrollmentProgressView.as_view(), name="enrollment-progress"),  
    path("enrollments/complete-lesson/", CompleteLessonView.as_view(), name="complete-lesson"),
    path("enroll/", EnrollmentView.as_view(), name="enroll-course"),
    
    path("progress/", LessonProgressView.as_view(), name="lesson-progress"),

    path("assignments/", AssignmentListCreateView.as_view(), name="assignment-list"),
    path("assignments/<int:pk>/", AssignmentDetailView.as_view(), name="assignment-detail"),
] + quiz_patterns + course_patterns + payment_patterns + dashboard_patterns