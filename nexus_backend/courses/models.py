from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class Course(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    playlist_id = models.CharField(max_length=100, blank=True, null=True)  # Optional YouTube Playlist ID
    intro_video_id = models.CharField(max_length=50, blank=True, null=True)  # YouTube Video ID for Intro
    instructor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="courses")
    created_at = models.DateTimeField(auto_now_add=True)
    
    category = models.CharField(max_length=100, blank=True, null=True)
    duration = models.PositiveIntegerField(help_text="Duration in minutes", default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    
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


# Lesson Model
class Lesson(models.Model):
    CONTENT_TYPES = [
        ('video', 'Video Lesson'),
        ('text', 'Text Lesson'),
        ('mixed', 'Mixed Content')
    ]
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES, default='text')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    module = models.ForeignKey(CourseModule, on_delete=models.CASCADE, related_name="lessons", null=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    video_id = models.CharField(max_length=50, blank=True, null=True)  # YouTube Video ID for Lesson
    position = models.PositiveIntegerField(default=0)  # Order of lessons in the course
    duration = models.PositiveIntegerField(help_text="Duration in minutes", default=0)
    
    class Meta:
        ordering = ['position']

    def __str__(self):
        return f"{self.course.title} - {self.title}"
    

# Quiz Model
class Quiz(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="quizzes")
    title = models.CharField(max_length=255)

    def __str__(self):
        return f"Quiz: {self.title} (Lesson: {self.lesson.title})"

# Question Model
class Question(models.Model):
    QUESTION_TYPES = [
        ("mcq", "Multiple Choice"),
        ("fill_in", "Fill in the Blank"),
        ("short_answer", "Short Answer"),
    ]
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    question_text = models.TextField()
    type = models.CharField(max_length=20, choices=QUESTION_TYPES, default="mcq")
    option_a = models.CharField(max_length=255, blank=True, null=True)
    option_b = models.CharField(max_length=255, blank=True, null=True)
    option_c = models.CharField(max_length=255, blank=True, null=True)
    option_d = models.CharField(max_length=255, blank=True, null=True)
    correct_answer = models.TextField()  # For fill-in and short answer, store the expected answer
    max_points = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.question_text
    
    
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