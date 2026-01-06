from django.db import models

# Create your models here.
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

from django.contrib.auth.models import User
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
        related_name="questions"
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

from django.db import models
from django.contrib.auth.models import User

class Test(models.Model):
    title = models.CharField(max_length=255)
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

    def __str__(self):
        return self.title

class TestQuestion(models.Model):
    test = models.ForeignKey("Test", on_delete=models.CASCADE)
    question = models.ForeignKey("Question", on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        unique_together = ("test", "question")

    def __str__(self):
        return f"{self.test.title} → Q{self.order}"
