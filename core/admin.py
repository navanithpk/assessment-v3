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
from django.contrib.auth.models import User

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
    list_display = (
        "full_name", 
        "username_display",
        "roll_number", 
        "grade", 
        "section", 
        "created_by"
    )
    list_filter = ("grade", "section")
    search_fields = ("full_name", "roll_number", "admission_id", "user__username")
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('full_name', 'roll_number', 'admission_id')
        }),
        ('Academic Information', {
            'fields': ('grade', 'section')
        }),
        ('Login Credentials', {
            'fields': ('username_field', 'password_field'),
            'description': 'Set username and password for student login'
        }),
        ('System Information', {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('username_field',)
    
    def username_display(self, obj):
        """Display username in list view"""
        return obj.user.username if obj.user else "No account"
    username_display.short_description = "Username"
    
    def username_field(self, obj):
        """Display username in form"""
        if obj.user:
            return obj.user.username
        return "Not created yet"
    username_field.short_description = "Username"
    
    def password_field(self, obj):
        """Display password info"""
        if obj.user:
            return "••••••••  (Use 'Change password' in user admin)"
        return "Will be created on save"
    password_field.short_description = "Password"
    
    def save_model(self, request, obj, form, change):
        """Override save to create user if needed"""
        if not obj.user:
            # Generate username from name or admission_id
            base_username = obj.admission_id if obj.admission_id else \
                           obj.full_name.lower().replace(' ', '_')
            username = base_username
            counter = 1
            
            # Ensure unique username
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
            
            # Create user
            user = User.objects.create_user(
                username=username,
                first_name=obj.full_name.split()[0] if obj.full_name else '',
                last_name=' '.join(obj.full_name.split()[1:]) if len(obj.full_name.split()) > 1 else '',
            )
            # Set default password (should be changed on first login)
            user.set_password('student123')
            user.save()
            
            obj.user = user
        
        # Set created_by if not set
        if not obj.pk and not obj.created_by_id:
            obj.created_by = request.user
            
        super().save_model(request, obj, form, change)
        
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