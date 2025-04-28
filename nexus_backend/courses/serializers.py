from rest_framework import serializers
from .models import (
    Course, Lesson, Quiz, 
    Question, Assignment, Enrollment, 
    LessonProgress, CourseModule, CourseOutcome, 
    CourseRequirement
    )
from django.contrib.auth import get_user_model

User = get_user_model()

class InstructorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'bio', 'position']  # Add any additional fields you need

class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ["id", "course", "module", "title", "description", "video_id", "position", "duration"]

class CourseModuleSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = CourseModule
        fields = ["id", "title", "position", "lessons", "duration"]
    
    def get_duration(self, obj):
        return obj.duration_minutes()
    
class CourseOutcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseOutcome
        fields = ['id', 'text', 'position']

class CourseRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseRequirement
        fields = ['id', 'text', 'position']

class CourseSerializer(serializers.ModelSerializer):
    instructor_details = serializers.SerializerMethodField()
    modules = serializers.SerializerMethodField()
    total_lessons = serializers.SerializerMethodField()
    outcomes = CourseOutcomeSerializer(many=True, read_only=True)
    requirements = CourseRequirementSerializer(many=True, read_only=True)
    
    class Meta:
        model = Course
        fields = ["id", "title", "description", "price", "playlist_id", "intro_video_id", 
                 "instructor", "instructor_details", "created_at", "category", 
                 "duration", "rating", "modules", "total_lessons", 
                 "outcomes", "requirements"]
        read_only_fields = ["created_at"]  # Admin can assign instructor manually
    
    def get_instructor_details(self, obj):
        if obj.instructor:
            return InstructorSerializer(obj.instructor).data
        return None
    
    def get_modules(self, obj):
        modules = obj.modules.all().prefetch_related('lessons')
        return CourseModuleSerializer(modules, many=True).data
    
    def get_total_lessons(self, obj):
        return obj.lessons.count()

class QuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = "__all__"

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ["id", "quiz", "question_text", "type", "option_a", "option_b", "option_c", "option_d", "correct_answer", "max_points"]

class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = "__all__"

class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = "__all__"
        read_only_fields = ["student", "enrolled_at"]

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["student"] = request.user  # Auto-assign the logged-in student
        return super().create(validated_data)


class LessonProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonProgress
        fields = "__all__"

