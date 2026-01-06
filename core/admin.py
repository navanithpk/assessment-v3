from django.contrib import admin
from .models import (
    Grade,
    Subject,
    Topic,
    LearningObjective,
    Question,
)

# ----------------------------
# Grade
# ----------------------------
@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


# ----------------------------
# Subject
# ----------------------------
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


# ----------------------------
# Topic
# ----------------------------
@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "grade", "subject")
    list_filter = ("grade", "subject")
    search_fields = ("name",)


# ----------------------------
# Learning Objective
# ----------------------------
@admin.register(LearningObjective)
class LearningObjectiveAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "short_description",
        "topic",
        "subject",
        "grade",
    )
    list_filter = ("grade", "subject", "topic")
    search_fields = ("code", "description")

    def short_description(self, obj):
        return obj.description

    short_description.short_description = "LO Description"


# ----------------------------
# Question
# ----------------------------
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "short_question",
        "grade",
        "subject",
        "topic",
        "question_type",
        "marks",
        "created_by",
    )
    list_filter = ("grade", "subject", "topic", "question_type")
    search_fields = ("question_text", "answer_text")
    ordering = ("-id",)

    def short_question(self, obj):
        return obj.question_text[:80]

    short_question.short_description = "Question"
