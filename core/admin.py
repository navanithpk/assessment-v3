from django.contrib import admin
from django.contrib import admin
from .models import Grade, Subject, Topic, LearningObjective

# Register your models here.
@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "grade", "subject")
    list_filter = ("grade", "subject")
    search_fields = ("name",)
@admin.register(LearningObjective)
class LearningObjectiveAdmin(admin.ModelAdmin):
    list_display = (
        "grade",
        "subject",
        "topic",
        "code",
        "short_description",
    )
    list_filter = ("grade", "subject", "topic")
    search_fields = ("code", "description")

    def short_description(self, obj):
        return obj.description

    short_description.short_description = "LO Description"

