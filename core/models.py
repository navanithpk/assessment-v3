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


class Question(models.Model):

    QUESTION_TYPES = [
        ("mcq", "MCQ"),
        ("theory", "Theory"),
        ("structured", "Structured"),
        ("practical", "Practical"),
    ]

    grade = models.ForeignKey(Grade, on_delete=models.PROTECT)
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    topic = models.ForeignKey(Topic, on_delete=models.PROTECT)
    year = models.PositiveIntegerField(null=True, blank=True)

    learning_objectives = models.ManyToManyField(
        LearningObjective,
        related_name="questions",
        blank=True
    )

    question_text = models.TextField()
    answer_text = models.TextField(blank=True)

    marks = models.PositiveIntegerField(default=1)
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPES
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="questions"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Q{self.id} | {self.grade}.{self.subject}.{self.topic}"


class Test(models.Model):
    title = models.CharField(max_length=255)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)  # Added for filtering
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_published = models.BooleanField(default=False)

    start_time = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    questions = models.ManyToManyField(
        "Question",
        through="TestQuestion",
        blank=True,
        related_name="tests"
    )
    
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


class TestQuestion(models.Model):
    test = models.ForeignKey(
        Test,
        on_delete=models.CASCADE,
        related_name="test_questions"
    )

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE
    )

    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.test.title} – Q{self.order}"


# Update your Student model in models.py to include the user field

class Student(models.Model):
    full_name = models.CharField(max_length=200)
    roll_number = models.CharField(max_length=50, blank=True)
    admission_id = models.CharField(max_length=50, blank=True)

    grade = models.ForeignKey(Grade, on_delete=models.CASCADE)
    section = models.CharField(max_length=10)  # A, B, C
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True)
    
    # Add this field for login account
    user = models.OneToOneField(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='student_profile'
    )
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_students')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("grade", "section", "roll_number", "school")
        ordering = ["school", "grade", "section", "roll_number"]

    def __str__(self):
        return f"{self.full_name} ({self.grade}-{self.section})"

class ClassGroup(models.Model):
    name = models.CharField(max_length=100)  # "Grade 8A Physics"
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE)
    section = models.CharField(max_length=10)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True)  # Added

    students = models.ManyToManyField(Student, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        ordering = ["school", "name"]

    def __str__(self):
        return self.name


class StudentAnswer(models.Model):
    """
    Stores student answers/attempts for test questions
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
    
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE
    )
    
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
        unique_together = ("student", "test", "question")
        ordering = ["test", "student", "question"]
    
    def __str__(self):
        return f"{self.student.full_name} - {self.test.title} - Q{self.question.id}"