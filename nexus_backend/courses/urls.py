from django.urls import path
from .views import (
    PublicCourseListView, InstructorCourseListView, PublicCourseDetailView, InstructorCourseDetailView, 
    CourseSpecificLessons, LessonListCreateView, LessonDetailView,
    AssignmentListCreateView, AssignmentDetailView,
    EnrollmentView, LessonProgressView,
    UserDashboardView, EnrollmentCheckView,
    EnrolledCourseDetailView, EnrollmentProgressView,
    CompleteLessonView, LessonAssignmentsView, ModuleCreateView, ModuleDetailView,
    QuizListCreateView, QuizDetailView,
    QuestionListCreateView, QuestionDetailView,
    LessonQuizzesView, QuizTakeView, QuizSubmitView,
    QuizAttemptListView, QuizAttemptDetailView, QuizResultsView, ModuleReorderView,
    # BulkCourseOutcomeView, BulkCourseRequirementView
)

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

urlpatterns = [
    path("courses/", PublicCourseListView.as_view(), name="course-list"),
    path("courses/<int:pk>/", PublicCourseDetailView.as_view(), name="course-detail"),

    path("instructor/courses/", InstructorCourseListView.as_view(), name="course-list"),
    path("instructor/courses/<int:pk>/", InstructorCourseDetailView.as_view(), name="course-detail"),

    path("modules/", ModuleCreateView.as_view(), name='module-create'),
    path("modules/<int:pk>/", ModuleDetailView.as_view(), name='module-create'),

    path("lessons/", LessonListCreateView.as_view(), name="lesson-list"),
    path("lessons/<int:pk>/", LessonDetailView.as_view(), name="lesson-detail"),
    path("courses/<int:id>/lessons/", CourseSpecificLessons.as_view(), name="course-specific-lessons"),


    path("assignments/", AssignmentListCreateView.as_view(), name="assignment-list"),
    path("assignments/<int:pk>/", AssignmentDetailView.as_view(), name="assignment-detail"),

    path("enroll/", EnrollmentView.as_view(), name="enroll-course"),
    path("progress/", LessonProgressView.as_view(), name="lesson-progress"),

    path("user-dashboard/", UserDashboardView.as_view(), name='user-dashboard'),
    path("modules/reorder/", ModuleReorderView.as_view(), name="module-reorder"),

    path("enrollments/check/<int:course_id>/", EnrollmentCheckView.as_view(), name="enrollment-check"),
    path("enrollments/course/<int:course_id>/", EnrolledCourseDetailView.as_view(), name="enrolled-course-detail"),
    path("enrollments/progress/<int:course_id>/", EnrollmentProgressView.as_view(), name="enrollment-progress"),  
    path("enrollments/complete-lesson/", CompleteLessonView.as_view(), name="complete-lesson"),
    # path("courses/outcomes/bulk-create/", BulkCourseOutcomeView.as_view(), name="bulk-course-outcomes"),
    # path("courses/requirements/bulk-create/", BulkCourseRequirementView.as_view(), name="bulk-course-requirements"),
] + quiz_patterns
