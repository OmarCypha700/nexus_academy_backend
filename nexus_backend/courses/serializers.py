from rest_framework import serializers
from django.db import models
from .models import (
    Course, Lesson, LessonContent, Assignment, Enrollment, 
    LessonProgress, CourseModule, CourseOutcome, CourseRequirement,
    Quiz, Question, QuizAttempt, Resource
    )
from django.contrib.auth import get_user_model
import logging
logger = logging.getLogger(__name__)

User = get_user_model()


class StudentProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonProgress
        fields = ['lesson_id', 'completed', 'completed_at']

class StudentEnrollmentSerializer(serializers.ModelSerializer):
    student = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = ['id', 'student', 'enrolled_at', 'progress']

    def get_student(self, obj):
        return {
            'id': obj.student.id,
            'name': f"{obj.student.first_name} {obj.student.last_name}",
            'email': obj.student.email
        }

    def get_progress(self, obj):
        student = obj.student  # Use the enrolled student from the Enrollment object
        course = obj.course    # Use the related Course from the Enrollment object
        
        total_lessons = Lesson.objects.filter(module__course=course).count()
        if total_lessons == 0:
            return {
                'completed_count': 0,
                'total_lessons': 0,
                'progress_percent': 0.0
            }
        
        completed_lessons = LessonProgress.objects.filter(
            student=student,
            lesson__module__course=course,
            completed=True
        ).count()
        
        return {
            'completed_count': completed_lessons,
            'total_lessons': total_lessons,
            'progress_percent': round((completed_lessons / total_lessons * 100), 1)
        }


class InstructorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'bio', 'position']

class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = ['id', 'title', 'url', 'resource_type', 'description', 'position']

# Serializers for quizzes

class QuizDashboardSerializer(serializers.ModelSerializer):
    course_id = serializers.SerializerMethodField()
    lesson_id = serializers.IntegerField(source='lesson.id')
    attempts_count = serializers.SerializerMethodField()
    can_attempt = serializers.SerializerMethodField()
    max_attempts = serializers.IntegerField()

    class Meta:
        model = Quiz
        fields = [
            'id', 'title', 'description', 'course_id', 'lesson_id',
            'attempts_count', 'can_attempt', 'max_attempts'
        ]

    def get_course_id(self, obj):
        return obj.lesson.module.course.id

    def get_attempts_count(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return QuizAttempt.objects.filter(quiz=obj, student=user).count()
        return 0

    def get_can_attempt(self, obj):
        user = self.context['request'].user
        if user.is_authenticated and obj.is_active:
            attempts = QuizAttempt.objects.filter(quiz=obj, student=user).count()
            return attempts < obj.max_attempts
        return False

class DynamicAnswerField(serializers.Field):
    def to_internal_value(self, data):
        return data  # Let the parent serializer handle type checks during validation

    def to_representation(self, value):
        return value
    
class QuestionSerializer(serializers.ModelSerializer):
    choices = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    correct_answer = DynamicAnswerField()

    class Meta:
        model = Question
        fields = ['id', 'quiz', 'text', 'question_type', 'choices', 'correct_answer', 'points', 'position', 'explanation']


    def validate(self, data):
        logger.info(f"Validating question data: {data}")
        logger.info(f"Type of correct_answer: {type(data.get('correct_answer'))}")
        question_type = data.get('question_type')
        choices = data.get('choices', [])
        correct_answer = data.get('correct_answer')

        if question_type in ['multiple_choice_single', 'multiple_choice_multiple']:
            if len(choices) < 2:
                raise serializers.ValidationError("Multiple choice questions must have at least 2 choices")
            if len(set(choices)) != len(choices):
                raise serializers.ValidationError("Choices must be unique")
            if question_type == 'multiple_choice_single':
                if not isinstance(correct_answer, str):
                    logger.error(f"correct_answer is not a string: {correct_answer}")
                    raise serializers.ValidationError("Single-answer question must have a string correct answer")
            if question_type == 'multiple_choice_multiple':
                if not isinstance(correct_answer, list):
                    raise serializers.ValidationError("Multiple-answer question must have a list of correct answers")
                # if not all(a in choices for a in correct_answer):
                #     raise serializers.ValidationError("All correct answers must be from the provided choices")
        elif question_type == 'true_false':
            data['choices'] = ['True', 'False']
            if correct_answer not in ['True', 'False']:
                raise serializers.ValidationError("True/False question must have 'True' or 'False' as correct answer")
        elif question_type == 'short_answer':
            data['choices'] = []
            if not isinstance(correct_answer, str):
                raise serializers.ValidationError("Short answer question must have a string correct answer")
        return data
    

    def get_choices(self, obj):
        if isinstance(obj.choices, list):
            # Remove duplicates while preserving order
            seen = set()
            unique_choices = [choice for choice in obj.choices if not (choice in seen or seen.add(choice))]
            return unique_choices
        if isinstance(obj.choices, str):
            choices = [choice.strip() for choice in obj.choices.split(',') if choice.strip()]
            seen = set()
            unique_choices = [choice for choice in choices if not (choice in seen or seen.add(choice))]
            return unique_choices
        return []

class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    attempts_count = serializers.SerializerMethodField()
    can_attempt = serializers.SerializerMethodField()
    attempts_remaining = serializers.SerializerMethodField()
    total_questions = serializers.IntegerField(source='questions.count', read_only=True)

    class Meta:
        model = Quiz
        fields = [
            'id', 'title', 'lesson', 'course', 'description', 'is_active', 'passing_score', 'max_attempts',
            'attempts_count', 'can_attempt', 'attempts_remaining', 'shuffle_questions',
            'time_limit', 'questions', 'total_questions'
        ]

    def get_attempts_count(self, obj):
        # Check if request is in context to avoid KeyError
        if 'request' not in self.context:
            return 0  # Return a default value if request is not available
        user = self.context['request'].user
        if user.is_authenticated:
            return QuizAttempt.objects.filter(quiz=obj, student=user).count()
        return 0

    def get_can_attempt(self, obj):
        # Check if request is in context to avoid KeyError
        if 'request' not in self.context:
            return 0  # Return a default value if request is not available
        user = self.context['request'].user
        if user.is_authenticated and obj.is_active:
            attempts = QuizAttempt.objects.filter(quiz=obj, student=user).count()
            return attempts < obj.max_attempts
        return False

    def get_attempts_remaining(self, obj):
        # Check if request is in context to avoid KeyError
        if 'request' not in self.context:
            return 0  # Return a default value if request is not available
        user = self.context['request'].user
        if user.is_authenticated and obj.is_active:
            attempts = QuizAttempt.objects.filter(quiz=obj, student=user).count()
            return max(0, obj.max_attempts - attempts)
        return 0

class QuestionTakeSerializer(serializers.ModelSerializer):
    """For taking quiz - excludes correct answer and explanation"""
    class Meta:
        model = Question
        fields = ['id', 'text', 'question_type', 'choices', 'points', 'position']

class QuizListSerializer(serializers.ModelSerializer):
    """Simplified serializer for quiz lists"""
    questions = QuestionSerializer(many=True, read_only=True)
    total_questions = serializers.SerializerMethodField()
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)
    
    class Meta:
        model = Quiz
        fields = ['id', 'course', 'title', 'description', 'lesson', 'lesson_title', 'time_limit', 
                 'passing_score', 'max_attempts', 'is_active', 'total_questions', 'questions', 'shuffle_questions']

    def get_total_questions(self, obj):
        return obj.total_questions()

class QuizTakeSerializer(serializers.ModelSerializer):
    """For taking quiz - includes questions but no answers"""
    questions = QuestionTakeSerializer(many=True, read_only=True)
    
    class Meta:
        model = Quiz
        fields = ['id', 'title', 'description', 'time_limit', 'passing_score', 
                 'max_attempts', 'shuffle_questions', 'questions']

class QuizAttemptSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    student_username = serializers.CharField(source='student.username', read_only=True)
    
    class Meta:
        model = QuizAttempt
        fields = ['id', 'student', 'student_username', 'quiz', 'quiz_title', 'score', 
                 'total_points', 'earned_points', 'passed', 'started_at', 'completed_at', 
                 'time_taken', 'answers']
        read_only_fields = ['student', 'started_at']

class QuizResultSerializer(serializers.ModelSerializer):
    """For showing quiz results with detailed feedback"""
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    
    class Meta:
        model = QuizAttempt
        fields = ['id', 'quiz_title', 'score', 'total_points', 'earned_points', 
                 'passed', 'completed_at', 'time_taken']

# Assignment serializers
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


# Lessons Serializer
class LessonContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonContent
        fields = ["id", "content_type", "title", "video_id", "text_content", "position", "duration" ] #'title'

    def validate(self, data):
        if data['content_type'] == 'video' and not data.get('video_id'):
            raise serializers.ValidationError("Video ID is required for video content.")
        if data['content_type'] == 'text' and not data.get('text_content'):
            raise serializers.ValidationError("Text Content is required for text content.")
        if data['content_type'] == 'video' and data.get('text_content'):
            raise serializers.ValidationError("Text Content should be empty for video content.")
        return data

class LessonSerializer(serializers.ModelSerializer):
    quizzes = QuizSerializer(many=True, read_only=True)
    assignments = AssignmentSerializer(many=True, read_only=True)
    contents = LessonContentSerializer(many=True, required=False)
    resources = ResourceSerializer(many=True, required=False)

    class Meta:
        model = Lesson
        fields = ["id", "course", "module", "title", "description", "position", "duration", "quizzes", "assignments", "contents", "resources"]

    def validate_resources(self, value):
        if value is None:
            return value
        if not isinstance(value, list):
            raise serializers.ValidationError("Resources must be a list")
        for resource in value:
            if not isinstance(resource, dict):
                raise serializers.ValidationError("Each resource must be a dictionary")
            required_fields = ['title', 'url', 'resource_type']
            for field in required_fields:
                if field not in resource:
                    raise serializers.ValidationError(f"Resource missing required field: {field}")
            if resource.get('resource_type') not in dict(Resource.RESOURCE_TYPES).keys():
                raise serializers.ValidationError(f"Invalid resource_type: {resource.get('resource_type')}")
        return value

    def create(self, validated_data):
        contents_data = validated_data.pop('contents', [])
        resources_data = validated_data.pop('resources', [])
        validated_data['position'] = int(validated_data.get('position', 0))
        lesson = Lesson.objects.create(**validated_data)
        for content_data in contents_data:
            LessonContent.objects.create(lesson=lesson, **content_data)
        for resource_data in resources_data:
            Resource.objects.create(lesson=lesson, **resource_data)
        return lesson

    def update(self, instance, validated_data):
        contents_data = validated_data.pop('contents', None)
        resources_data = validated_data.pop('resources', None)
        instance = super().update(instance, validated_data)
        if contents_data is not None:
            instance.contents.all().delete()
            max_position = LessonContent.objects.filter(lesson=instance).aggregate(models.Max('position'))['position__max'] or -1
            for index, content_data in enumerate(contents_data):
                content_data['position'] = max_position + index + 1
                LessonContent.objects.create(lesson=instance, **content_data)
        if resources_data is not None:
            instance.resources.all().delete()
            max_position = Resource.objects.filter(lesson=instance).aggregate(models.Max('position'))['position__max'] or -1
            for index, resource_data in enumerate(resources_data):
                resource_data['position'] = max_position + index + 1
                Resource.objects.create(lesson=instance, **resource_data)
        return instance

class CourseModuleSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = CourseModule
        fields = ["id", "title", "position", "lessons", "duration"]
    
    def get_duration(self, obj):
        return obj.duration_minutes()

class ModuleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseModule
        fields = ['course', 'title', 'position']

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
    progress_percent = serializers.SerializerMethodField()
    completed_lessons = serializers.SerializerMethodField()

    
    class Meta:
        model = Course
        fields = ["id", "title", "description", "price", "intro_video_id", 
                 "instructor", "instructor_details", "created_at", "category", "is_published", 
                 "duration", "rating", "modules", "total_lessons", 
                 "outcomes", "requirements", "progress_percent", "completed_lessons"]
        read_only_fields = ["created_at"]
    
    def get_instructor_details(self, obj):
        if obj.instructor:
            return InstructorSerializer(obj.instructor).data
        return None
    
    def get_modules(self, obj):
        modules = obj.modules.all().prefetch_related('lessons')
        return CourseModuleSerializer(modules, many=True).data
    
    def get_total_lessons(self, obj):
        return obj.lessons.count()
    
    def get_progress_percent(self, obj):
        user = self.context['request'].user
        if not user.is_authenticated:
            return None  # or 0
        
        total_lessons = Lesson.objects.filter(
            module__course=obj
        ).count()

        if total_lessons == 0:
            return 0

        completed_lessons = LessonProgress.objects.filter(
            student=user,
            lesson__module__course=obj,
            completed=True
        ).count()

        return round((completed_lessons / total_lessons) * 100)
    
    def get_completed_lessons(self, obj):
        return list(self.context.get('completed_lessons', set()))

class CourseDetailSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)
    requirements = CourseRequirementSerializer(many=True, read_only=True)
    outcomes = CourseOutcomeSerializer(many=True, read_only=True)
    instructor_details = serializers.SerializerMethodField()
    modules = serializers.SerializerMethodField()
    class Meta:
        model = Course
        fields = '__all__'

    def get_instructor_details(self, obj):
        if obj.instructor:
            return InstructorSerializer(obj.instructor).data
        return None
    
    def get_modules(self, obj):
        modules = obj.modules.all().prefetch_related('lessons')
        return CourseModuleSerializer(modules, many=True).data

class BulkCourseOutcomeSerializer(serializers.Serializer):
    course = serializers.IntegerField()
    outcomes = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField()
        ),
        allow_empty=False
    )

    def validate(self, data):
        course = data.get('course')
        outcomes = data.get('outcomes')
        if not Course.objects.filter(id=course).exists():
            raise serializers.ValidationError("Invalid course")
        for outcome in outcomes:
            if 'text' not in outcome:
                raise serializers.ValidationError("Each outcome must have a 'text' field")
            if not isinstance(outcome.get('position', 0), int):
                raise serializers.ValidationError("Position must be an integer")
        return data

class BulkCourseRequirementSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()
    requirements = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField()
        ),
        allow_empty=False
    )

    def validate(self, data):
        course_id = data.get('course_id')
        requirements = data.get('requirements')
        if not Course.objects.filter(id=course_id).exists():
            raise serializers.ValidationError("Invalid course_id")
        for req in requirements:
            if 'text' not in req:
                raise serializers.ValidationError("Each requirement must have a 'text' field")
            if not isinstance(req.get('position', 0), int):
                raise serializers.ValidationError("Position must be an integer")
        return data
