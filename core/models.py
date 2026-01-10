from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class School(models.Model):
    """
    School model - Teachers and Students belong to a school
    """
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)  # e.g., "SCH001"
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["name"]
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class UserProfile(models.Model):
    """
    Extended user profile for role management
    """
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('school_admin', 'School Admin'),
    ]
    subject = models.CharField(max_length=100, blank=True, null=True)
    grade = models.IntegerField(null=True, blank=True)  # For students
    division = models.CharField(max_length=10, blank=True, null=True) 
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='users', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["user__username"]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()} at {self.school}"


class Grade(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ["name"]
        verbose_name = "Grade"
        verbose_name_plural = "Grades"

    def __str__(self):
        return self.name
        
        
class Subject(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
        
        
class Topic(models.Model):
    name = models.CharField(max_length=150)

    grade = models.ForeignKey(
        Grade,
        on_delete=models.CASCADE,
        related_name="topics"
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="topics"
    )

    class Meta:
        unique_together = ("name", "grade", "subject")
        ordering = ["grade__name", "subject__name", "name"]

    def __str__(self):
        return f"{self.grade} | {self.subject} | {self.name}"


class LearningObjective(models.Model):
    code = models.CharField(max_length=30)
    description = models.TextField()

    grade = models.ForeignKey(
        Grade,
        on_delete=models.CASCADE,
        related_name="learning_objectives"
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="learning_objectives"
    )

    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="learning_objectives"
    )

    class Meta:
        unique_together = (
            "grade",
            "subject",
            "topic",
            "code",
        )
        ordering = ["grade__name", "subject__name", "topic__name", "code"]

    def __str__(self):
        return f"{self.grade}.{self.subject}.{self.topic}.{self.code}"


# Question model removed - hierarchical tests use JSON structure instead


# Update your Test model in models.py to add this field:

class Test(models.Model):
    """
    Hierarchical/Descriptive Test Model
    Tests are created with a hierarchical question structure stored as JSON
    """
    TEST_TYPE_CHOICES = [
        ('standard', 'Standard Question Bank'),
        ('descriptive', 'Descriptive/Hierarchical'),
    ]

    title = models.CharField(max_length=255)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_published = models.BooleanField(default=False)

    test_type = models.CharField(
        max_length=20,
        choices=TEST_TYPE_CHOICES,
        default='descriptive'
    )

    start_time = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    assigned_students = models.ManyToManyField(
        "Student",
        blank=True,
        related_name="assigned_tests"
    )

    assigned_groups = models.ManyToManyField(
        "ClassGroup",
        blank=True,
        related_name="assigned_tests"
    )

    excluded_students = models.ManyToManyField(
        "Student",
        blank=True,
        related_name="excluded_from_tests"
    )

    # Hierarchical question structure stored as JSON
    descriptive_structure = models.TextField(
        blank=True,
        null=True,
        help_text="JSON structure for hierarchical questions"
    )

    # Markscheme for AI evaluation
    markscheme = models.TextField(
        blank=True,
        null=True,
        help_text="Marking criteria and rubric for AI-assisted evaluation"
    )
    
    def __str__(self):
        return self.title
    
    def get_all_assigned_students(self):
        """
        Get all students assigned to this test (both directly and through groups)
        excluding those in excluded_students
        """
        from django.db.models import Q
        
        # Direct assignments
        direct_students = self.assigned_students.all()
        
        # Group assignments
        group_students = Student.objects.filter(classgroup__in=self.assigned_groups.all())
        
        # Combine and exclude
        all_students = (direct_students | group_students).distinct()
        excluded = self.excluded_students.all()
        
        return all_students.exclude(id__in=excluded)


# After adding this field, run migrations:
# python manage.py makemigrations
# python manage.py migrate


# TestQuestion model removed - hierarchical tests use JSON structure instead


class Student(models.Model):
    full_name = models.CharField(max_length=200)
    roll_number = models.CharField(max_length=50, blank=True)
    admission_id = models.CharField(max_length=50, blank=True)

    grade = models.ForeignKey(Grade, on_delete=models.CASCADE)
    section = models.CharField(max_length=10)  # A, B, C
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True)
    
    # Link Student to User account
    user = models.OneToOneField(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='student_profile'
    )
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='students_created')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("grade", "section", "roll_number", "school")
        ordering = ["school", "grade", "section", "roll_number"]

    def __str__(self):
        return f"{self.full_name} ({self.grade}-{self.section})"


class ClassGroup(models.Model):
    name = models.CharField(max_length=200)
    school = models.ForeignKey('School', on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    grade = models.ForeignKey('Grade', on_delete=models.SET_NULL, null=True, blank=True)
    students = models.ManyToManyField(User, related_name='student_groups', blank=True)
    
    section = models.CharField(max_length=10, blank=True)  # e.g., "A", "B", "Morning"
    subject = models.ForeignKey('Subject', on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return self.name


class StudentAnswer(models.Model):
    """
    Stores student answers for hierarchical test questions
    question_id is a string identifier like 'q1a', 'q2bi', etc.
    """
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="answers"
    )

    test = models.ForeignKey(
        Test,
        on_delete=models.CASCADE,
        related_name="student_answers"
    )

    # Question identifier from the hierarchical structure (e.g., 'q1', 'q1a', 'q2bi')
    question_id = models.CharField(max_length=50, default='q1')

    answer_text = models.TextField(blank=True)

    marks_awarded = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    submitted_at = models.DateTimeField(auto_now_add=True)
    evaluated_at = models.DateTimeField(null=True, blank=True)
    evaluated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evaluated_answers"
    )

    class Meta:
        unique_together = ("student", "test", "question_id")
        ordering = ["test", "student", "question_id"]

    def __str__(self):
        return f"{self.student.full_name} - {self.test.title} - {self.question_id}"


class StudentTestAttempt(models.Model):
    """
    Track student test attempts - when they started, submitted, and time remaining
    """
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="test_attempts"
    )
    test = models.ForeignKey(
        Test,
        on_delete=models.CASCADE,
        related_name="attempts"
    )
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    time_remaining_seconds = models.IntegerField(null=True, blank=True)
    is_submitted = models.BooleanField(default=False)

    class Meta:
        unique_together = ("student", "test")
        ordering = ["-started_at"]

    def __str__(self):
        status = "Submitted" if self.is_submitted else "In Progress"
        return f"{self.student.full_name} - {self.test.title} ({status})"