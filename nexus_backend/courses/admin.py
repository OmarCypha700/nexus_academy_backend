from django.contrib import admin
from .models import (
    Course, CourseModule, Lesson, Quiz, Question, QuizAttempt,
    Assignment, Enrollment, LessonProgress, CourseOutcome, CourseRequirement, LessonContent
)

# Inline for Course Outcomes
class CourseOutcomeInline(admin.TabularInline):
    model = CourseOutcome
    extra = 1
    fields = ('text', 'position')
    ordering = ('position',)

# Inline for Course Requirements
class CourseRequirementInline(admin.TabularInline):
    model = CourseRequirement
    extra = 1
    fields = ('text', 'position')
    ordering = ('position',)

# Inline for Lessons within a Module
class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ('title', 'description', 'position', 'duration')
    ordering = ('position',)
    show_change_link = True

# Inline for Quizzes within a Lesson
class QuizInline(admin.TabularInline):
    model = Quiz
    extra = 1
    fields = ('title', 'description', 'is_active', 'passing_score', 'max_attempts')
    show_change_link = True

# Inline for Questions within a Quiz
class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    fields = ('text', 'question_type', 'choices', 'correct_answer', 'points', 'position')
    ordering = ('position',)
    show_change_link = True

# Inline for Assignments within a Lesson
class AssignmentInline(admin.TabularInline):
    model = Assignment
    extra = 1
    fields = ('title', 'description', 'due_date')
    show_change_link = True

# Inline for LessonContent within a Lesson
class LessonContentInline(admin.TabularInline):
    model = LessonContent
    extra = 1
    fields = ('content_type', 'title', 'video_id', 'text_content', 'position')
    ordering = ('position',)
    show_change_link = True

# Admin for Course
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor', 'is_published', 'duration', 'rating', 'created_at')
    list_filter = ('is_published', 'created_at', 'rating')
    search_fields = ('title', 'description', 'instructor__username', 'instructor__first_name', 'instructor__last_name')
    inlines = [CourseOutcomeInline, CourseRequirementInline, LessonInline] 
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'instructor', 'is_published')
        }),
        ('Details', {
            'fields': ('price', 'intro_video_id', 'duration', 'rating')
        }),
    )
    ordering = ('-created_at',)
    list_per_page = 20

# Admin for CourseModule
@admin.register(CourseModule)
class CourseModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'position', 'duration_minutes')
    list_filter = ('course',)
    search_fields = ('title', 'course__title')
    inlines = [LessonInline]
    fieldsets = (
        ('Module Info', {
            'fields': ('course', 'title', 'position')
        }),
    )
    ordering = ('course', 'position')
    list_per_page = 20

# Admin for Lesson
@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'module', 'duration', 'position')
    list_filter = ('course', 'module')
    search_fields = ('title', 'description', 'course__title')
    inlines = [LessonContentInline, QuizInline, AssignmentInline]  # Added LessonContentInline
    fieldsets = (
        ('Basic Information', {
            'fields': ('course', 'module', 'title')
        }),
        ('Content Details', {
            'fields': ( 'description','position', 'duration')
        }),
    )
    ordering = ('course', 'position')
    list_per_page = 20

# Admin for LessonContent
@admin.register(LessonContent)
class LessonContentAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'content_type', 'title', 'position', 'video_id_preview')
    list_filter = ('content_type', 'lesson__course', 'lesson__module')
    search_fields = ('lesson__title', 'text_content')
    fieldsets = (
        ('Content Info', {
            'fields': ('lesson', 'content_type', 'title', 'video_id', 'text_content')
        }),
        ('Position', {
            'fields': ('position',)
        }),
    )
    ordering = ('lesson', 'position')
    list_per_page = 20

    def video_id_preview(self, obj):
        return obj.video_id[:10] + ('...' if obj.video_id and len(obj.video_id) > 10 else '')
    video_id_preview.short_description = 'Video ID'

# Admin for Quiz
@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'lesson', 'course', 'created_by', 'is_active', 'passing_score', 'max_attempts', 'total_questions')
    list_filter = ('is_active', 'lesson__course', 'created_by')
    search_fields = ('title', 'description', 'lesson__title')
    inlines = [QuestionInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('lesson', 'title', 'description', 'created_by')
        }),
        ('Quiz Settings', {
            'fields': ('shuffle_questions', 'time_limit', 'passing_score', 'max_attempts', 'is_active')
        }),
    )
    ordering = ('-created_at',)
    list_per_page = 20

# Admin for Question
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text_preview', 'quiz', 'question_type', 'points', 'position')
    list_filter = ('question_type', 'quiz__lesson__course')
    search_fields = ('text', 'quiz__title')
    fieldsets = (
        ('Question Details', {
            'fields': ('quiz', 'text', 'question_type', 'choices', 'correct_answer')
        }),
        ('Additional Info', {
            'fields': ('explanation', 'points', 'position')
        }),
    )
    ordering = ('quiz', 'position')
    list_per_page = 20

    def text_preview(self, obj):
        return obj.text[:50] + ('...' if len(obj.text) > 50 else '')
    text_preview.short_description = 'Question Text'

# Admin for QuizAttempt
@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'quiz', 'score', 'passed', 'started_at', 'time_taken')
    list_filter = ('passed', 'quiz__lesson__course', 'started_at')
    search_fields = ('student__username', 'quiz__title')
    fieldsets = (
        ('Attempt Info', {
            'fields': ('student', 'quiz', 'score', 'total_points', 'earned_points')
        }),
        ('Status & Timing', {
            'fields': ('passed', 'started_at', 'completed_at', 'time_taken')
        }),
        ('Answers', {
            'fields': ('answers',)
        }),
    )
    readonly_fields = ('started_at', 'completed_at', 'answers')
    ordering = ('-started_at',)
    list_per_page = 20

# Admin for Assignment
@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'lesson', 'due_date')
    list_filter = ('due_date', 'lesson__course')
    search_fields = ('title', 'description', 'lesson__title')
    fieldsets = (
        ('Assignment Info', {
            'fields': ('lesson', 'title', 'description')
        }),
        ('Details', {
            'fields': ('file', 'due_date')
        }),
    )
    ordering = ('due_date',)
    list_per_page = 20

# Admin for Enrollment
@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'enrolled_at')
    list_filter = ('enrolled_at', 'course')
    search_fields = ('student__username', 'course__title')
    fieldsets = (
        ('Enrollment Info', {
            'fields': ('student', 'course', 'enrolled_at')
        }),
    )
    readonly_fields = ('enrolled_at',)
    ordering = ('-enrolled_at',)
    list_per_page = 20

# Admin for LessonProgress
@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'lesson', 'completed', 'completed_at')
    list_filter = ('completed', 'lesson__course')
    search_fields = ('student__username', 'lesson__title')
    fieldsets = (
        ('Progress Info', {
            'fields': ('student', 'lesson', 'completed', 'completed_at')
        }),
    )
    readonly_fields = ('completed_at',)
    ordering = ('-completed_at',)
    list_per_page = 20

# Admin for CourseOutcome
@admin.register(CourseOutcome)
class CourseOutcomeAdmin(admin.ModelAdmin):
    list_display = ('course', 'text', 'position')
    list_filter = ('course',)
    search_fields = ('text', 'course__title')
    fieldsets = (
        ('Outcome Info', {
            'fields': ('course', 'text', 'position')
        }),
    )
    ordering = ('course', 'position')
    list_per_page = 20

# Admin for CourseRequirement
@admin.register(CourseRequirement)
class CourseRequirementAdmin(admin.ModelAdmin):
    list_display = ('course', 'text', 'position')
    list_filter = ('course',)
    search_fields = ('text', 'course__title')
    fieldsets = (
        ('Requirement Info', {
            'fields': ('course', 'text', 'position')
        }),
    )
    ordering = ('course', 'position')
    list_per_page = 20