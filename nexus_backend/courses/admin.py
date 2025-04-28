from django.contrib import admin
from .models import (
    Course, CourseModule, Lesson, Quiz, Question,
    Assignment, Enrollment, LessonProgress,
    CourseOutcome, CourseRequirement
)

# Inline classes
class CourseModuleInline(admin.TabularInline):
    model = CourseModule
    extra = 1

class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1

class OutcomeInline(admin.TabularInline):
    model = CourseOutcome
    extra = 1

class RequirementInline(admin.TabularInline):
    model = CourseRequirement
    extra = 1

class QuizInline(admin.TabularInline):
    model = Quiz
    extra = 1

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1

class AssignmentInline(admin.TabularInline):
    model = Assignment
    extra = 1


# Admin classes
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "instructor", "price", "category", "duration", "rating", "created_at")
    list_filter = ("category", "instructor", "created_at")
    search_fields = ("title", "description")
    inlines = [CourseModuleInline, OutcomeInline, RequirementInline]


@admin.register(CourseModule)
class CourseModuleAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "position")
    list_filter = ("course",)
    search_fields = ("title",)
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "module", "content_type", "position", "duration")
    list_filter = ("course", "module", "content_type")
    search_fields = ("title", "description")
    inlines = [QuizInline, AssignmentInline]


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "lesson")
    search_fields = ("title",)
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("quiz", "question_text", "correct_answer")
    search_fields = ("question_text",)


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("title", "lesson", "due_date")
    search_fields = ("title", "description")
    list_filter = ("due_date",)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "enrolled_at")
    search_fields = ("student__username", "course__title")
    list_filter = ("enrolled_at",)


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ("student", "lesson", "completed", "completed_at")
    list_filter = ("completed",)
    search_fields = ("student__username", "lesson__title")


@admin.register(CourseOutcome)
class CourseOutcomeAdmin(admin.ModelAdmin):
    list_display = ("course", "text", "position")
    ordering = ("course", "position")


@admin.register(CourseRequirement)
class CourseRequirementAdmin(admin.ModelAdmin):
    list_display = ("course", "text", "position")
    ordering = ("course", "position")
