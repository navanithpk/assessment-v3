from django.contrib import admin
from .models import (
    Grade,
    Subject,
    Topic,
    LearningObjective,
    Question,
    Test,
    TestQuestion,
    Student,
    ClassGroup,
    StudentAnswer,
)

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "grade", "subject")
    list_filter = ("grade", "subject")


@admin.register(LearningObjective)
class LearningObjectiveAdmin(admin.ModelAdmin):
    list_display = ("code", "topic", "subject", "grade")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "grade",
        "subject",
        "topic",
        "question_type",
        "marks",
        "year",
        "created_by",
    )
    search_fields = ("question_text", "answer_text")


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "created_by", "is_published", "created_at")
    list_filter = ("is_published",)


@admin.register(TestQuestion)
class TestQuestionAdmin(admin.ModelAdmin):
    list_display = ("test", "question", "order")


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("full_name", "roll_number", "grade", "section", "created_by")
    list_filter = ("grade", "section")
    search_fields = ("full_name", "roll_number", "admission_id")


@admin.register(ClassGroup)
class ClassGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "grade", "section", "subject", "created_by")
    list_filter = ("grade", "section", "subject")
    filter_horizontal = ("students",)


@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "test",
        "question",
        "marks_awarded",
        "submitted_at",
        "evaluated_by"
    )
    list_filter = ("test", "evaluated_at")
    search_fields = ("student__full_name", "test__title")
    readonly_fields = ("submitted_at",)