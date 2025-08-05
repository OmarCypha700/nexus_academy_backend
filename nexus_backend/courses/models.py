from django.db import models
from django.conf import settings
import json
from django.forms import ValidationError

User = settings.AUTH_USER_MODEL

class Course(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    intro_video_id = models.CharField(max_length=50, blank=True, null=True)  # YouTube Video ID for Intro
    instructor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="courses")
    created_at = models.DateTimeField(auto_now_add=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    duration = models.PositiveIntegerField(help_text="Duration in minutes", default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    is_published = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title

class CourseModule(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=255)
    position = models.PositiveIntegerField(default=0)  # Order of modules in the course
    
    class Meta:
        ordering = ['position']
        
    def __str__(self):
        return f"{self.course.title} - Module {self.position}: {self.title}"
        
    def duration_minutes(self):
        """Calculate total duration of all lessons in this module"""
        return sum(lesson.duration for lesson in self.lessons.all())

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    module = models.ForeignKey(CourseModule, on_delete=models.CASCADE, related_name="lessons", null=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    position = models.PositiveIntegerField(default=0)
    duration = models.PositiveIntegerField(help_text="Total duration in minutes", default=0)

    class Meta:
        ordering = ['position']

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class LessonContent(models.Model):
    CONTENT_TYPES = [
        ('video', 'Video'),
        ('text', 'Text'),
    ]
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="contents")
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES, default='text')
    title = models.CharField(max_length=255, default="")
    video_id = models.CharField(max_length=50, blank=True, null=True, help_text="YouTube Video ID (11 characters)")
    text_content = models.TextField(blank=True, null=True)
    position = models.PositiveIntegerField(default=0, help_text="Order of content in the lesson")
    duration = models.PositiveIntegerField(help_text="Total duration in minutes", default=0)

    class Meta:
        ordering = ['position']
        unique_together = ('lesson', 'position')

    def __str__(self):
        return f"{self.lesson.title} - Content {self.position} ({self.content_type})"

    def clean(self):
        if self.content_type == 'video' and self.video_id and len(self.video_id) != 11:
            raise ValidationError("Video ID must be 11 characters long for YouTube.")


class Resource(models.Model):
    RESOURCE_TYPES = [
        ('link', 'Webpage Link'),
        ('document', 'Document'),
    ]
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="resources")
    title = models.CharField(max_length=255)
    url = models.URLField(max_length=500)
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES, default='link')
    description = models.TextField(blank=True, null=True)
    position = models.PositiveIntegerField(default=0, help_text="Order of resource in the lesson")

    class Meta:
        ordering = ['position']
        unique_together = ('lesson', 'position')

    def __str__(self):
        return f"{self.lesson.title} - Resource: {self.title} ({self.resource_type})"


class Quiz(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="quizzes")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    shuffle_questions = models.BooleanField(default=False)
    time_limit = models.PositiveIntegerField(help_text="Time limit in minutes", null=True, blank=True)
    passing_score = models.DecimalField(max_digits=5, decimal_places=2, default=70.00, help_text="Minimum score to pass")
    max_attempts = models.PositiveIntegerField(default=3, help_text="Maximum number of attempts allowed")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.lesson.title} - {self.title}"

    def total_questions(self):
        return self.questions.count()

class Question(models.Model):
    QUESTION_TYPES = (
        ('multiple_choice_single', 'Multiple Choice (Single Answer)'),
        ('multiple_choice_multiple', 'Multiple Choice (Multiple Answers)'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer'),
    )

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    question_type = models.CharField(max_length=50, choices=QUESTION_TYPES)
    choices = models.JSONField(default=list)
    correct_answer = models.TextField()  # JSON or string depending on type
    points = models.PositiveIntegerField(default=1)
    position = models.PositiveIntegerField(default=0)
    explanation = models.TextField(blank=True)

    class Meta:
        ordering = ['position']
        indexes = [
            models.Index(fields=['quiz', 'position']),
        ]

    def save(self, *args, **kwargs):
        if self.question_type in ['multiple_choice_single', 'multiple_choice_multiple']:
            if not self.choices or len(self.choices) < 2:
                raise ValueError("Multiple choice questions must have at least 2 choices")
            if self.question_type == 'multiple_choice_single' and not isinstance(self.correct_answer, str):
                raise ValueError("Single-answer question must have a string correct answer")
            if self.question_type == 'multiple_choice_multiple' and not isinstance(self.correct_answer, list):
                raise ValueError("Multiple-answer question must have a list of correct answers")
        elif self.question_type == 'true_false':
            self.choices = ['True', 'False']
            if self.correct_answer not in ['True', 'False']:
                raise ValueError("True/False question must have 'True' or 'False' as correct answer")
        elif self.question_type == 'short_answer':
            self.choices = []
            if not isinstance(self.correct_answer, str):
                raise ValueError("Short answer question must have a string correct answer")
        super().save(*args, **kwargs)
        
        # Validate correct_answer
        valid_labels = [chr(65+i) for i in range(len(self.choices))]
        if self.question_type == 'multiple_choice_single':
            if not isinstance(self.correct_answer, str) or not self.correct_answer in valid_labels:
                raise ValueError("Correct answer must be a valid option label (e.g., 'A')")
        elif self.question_type == 'multiple_choice_multiple':
            if not isinstance(self.correct_answer, list) or not all(a in valid_labels for a in self.correct_answer):
                raise ValueError("Correct answer must be a list of valid option labels (e.g., ['A', 'C'])")
        elif self.question_type == 'true_false':
            if not self.correct_answer in ['A', 'B']:
                raise ValueError("Correct answer must be 'A' or 'B' for True/False")
        
        super().save(*args, **kwargs)

    def __str__(self):
            return f"{self.quiz.title} - {self.text[:30]}"
    

class QuizAttempt(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quiz_attempts")
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    score = models.DecimalField(max_digits=5, decimal_places=2)
    total_points = models.PositiveIntegerField(default=0)
    earned_points = models.PositiveIntegerField(default=0)
    passed = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_taken = models.PositiveIntegerField(null=True, blank=True, help_text="Time taken in seconds")
    answers = models.JSONField(default=dict, help_text="{question_id: {'answer': 'user_answer', 'is_correct': bool}}")

    class Meta:
        ordering = ['-started_at']
        unique_together = ['student', 'quiz', 'started_at']  # Allow multiple attempts but track them
        indexes = [
            models.Index(fields=['quiz', 'student']),
        ]

    def __str__(self):
        return f"{self.student.username} - {self.quiz.title} - {self.score}%"

    def save(self, *args, **kwargs):
        # Calculate if passed based on quiz passing score
        self.passed = self.score >= self.quiz.passing_score
        super().save(*args, **kwargs)
    
# Assignment Model
class Assignment(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(max_length=255)
    description = models.TextField()
    file = models.FileField(upload_to="assignments/")
    due_date = models.DateTimeField()

    def __str__(self):
        return f"Assignment: {self.title} (Lesson: {self.lesson.title})"

# Enrollment Model
class Enrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "course")  # Prevent duplicate enrollments
        indexes = [
            models.Index(fields=['student', 'course']),
        ]

    def __str__(self):
        return f"{self.student.username} enrolled in {self.course.title}"
    

# Lesson Progress
class LessonProgress(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress")
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("student", "lesson")  # Prevent duplicate tracking


class CourseOutcome(models.Model):
    """Represents a learning outcome or benefit from taking the course"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="outcomes")
    text = models.CharField(max_length=255)
    position = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['position']
    
    def __str__(self):
        return f"{self.course.title} - Outcome: {self.text[:30]}"


class CourseRequirement(models.Model):
    """Represents a prerequisite or requirement for the course"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="requirements")
    text = models.CharField(max_length=255)
    position = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['position']
    
    def __str__(self):
        return f"{self.course.title} - Requirement: {self.text[:30]}"
    

# Optional: Track completed lessons
# class UserProfile(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     completed_lessons = models.ManyToManyField(Lesson, related_name="completed_by")

#     def __str__(self):
#         return self.user.username