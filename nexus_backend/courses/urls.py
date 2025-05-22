from django.urls import path
from .views import (
    CourseListCreateView, CourseDetailView,
    LessonListCreateView, LessonDetailView,
    QuizListCreateView, QuizDetailView,
    QuestionListCreateView, QuestionDetailView,
    AssignmentListCreateView, AssignmentDetailView,
    EnrollmentView, LessonProgressView,
    UserDashboard, EnrollmentCheckView,
    EnrolledCourseDetailView, EnrollmentProgressView,
    CompleteLessonView, LessonQuizzesView, LessonAssignmentsView,
    QuizSubmissionView, ModuleCreateView, ModuleDetailView
)

urlpatterns = [
    path("courses/", CourseListCreateView.as_view(), name="course-list"),
    path("courses/<int:pk>/", CourseDetailView.as_view(), name="course-detail"),
    path("modules/", ModuleCreateView.as_view(), name='module-create'),
    path("modules/<int:pk>/", ModuleDetailView.as_view(), name='module-create'),

    path("lessons/", LessonListCreateView.as_view(), name="lesson-list"),
    path("lessons/<int:pk>/", LessonDetailView.as_view(), name="lesson-detail"),

    path("quizzes/", QuizListCreateView.as_view(), name="quiz-list"),
    path("quizzes/<int:pk>/", QuizDetailView.as_view(), name="quiz-detail"),

    path("questions/", QuestionListCreateView.as_view(), name="question-list"),
    path("questions/<int:pk>/", QuestionDetailView.as_view(), name="question-detail"),

    path("assignments/", AssignmentListCreateView.as_view(), name="assignment-list"),
    path("assignments/<int:pk>/", AssignmentDetailView.as_view(), name="assignment-detail"),

    path("enroll/", EnrollmentView.as_view(), name="enroll-course"),
    path("progress/", LessonProgressView.as_view(), name="lesson-progress"),

    path("user-dashboard/", UserDashboard.as_view(), name='user-dashboard'),

    path("enrollments/check/<int:course_id>/", EnrollmentCheckView.as_view(), name="enrollment-check"),
    path("enrollments/course/<int:course_id>/", EnrolledCourseDetailView.as_view(), name="enrolled-course-detail"),
    path("enrollments/progress/<int:course_id>/", EnrollmentProgressView.as_view(), name="enrollment-progress"),  
    path("enrollments/complete-lesson/", CompleteLessonView.as_view(), name="complete-lesson"),
    path("quizzes/lesson/<int:lesson_id>/", LessonQuizzesView.as_view(), name="lesson-quizzes"),
    path("assignments/lesson/<int:lesson_id>/", LessonAssignmentsView.as_view(), name="lesson-assignments"),
    path("quizzes/<int:pk>/submit/", QuizSubmissionView.as_view(), name="quiz-submit")

]
