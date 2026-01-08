from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.template.loader import render_to_string
from django.db import models
from django.db.models import Q
import json

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
    School,
    UserProfile,
)


def get_user_school(user):
    """Helper function to get user's school"""
    try:
        return user.profile.school
    except:
        return None


def get_user_role(user):
    """Helper function to get user's role"""
    try:
        return user.profile.role
    except:
        return 'student' if not user.is_staff else 'teacher'


# ===================== AUTHENTICATION & REDIRECTS =====================

def root_redirect(request):
    if request.user.is_authenticated:
        role = get_user_role(request.user)
        if role in ['teacher', 'school_admin']:
            return redirect("teacher_dashboard")
        return redirect("student_dashboard")
    return redirect("login")


def custom_login(request):
    error = None

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is None:
            error = "Invalid username or password"
        else:
            login(request, user)
            
            # Redirect based on role
            role = get_user_role(user)
            if role in ['teacher', 'school_admin']:
                return redirect("teacher_dashboard")
            elif role == 'student':
                return redirect("student_dashboard")
            else:
                return redirect("/admin/")

    return render(request, "registration/login.html", {"error": error})


# ===================== DASHBOARDS =====================

@login_required
def teacher_dashboard(request):
    school = get_user_school(request.user)
    role = get_user_role(request.user)
    
    context = {
        'school': school,
        'role': role,
        'is_school_admin': role == 'school_admin'
    }
    
    return render(request, "teacher/teacher_dashboard.html", context)


@login_required
def student_dashboard(request):
    school = get_user_school(request.user)
    
    context = {
        'school': school,
    }
    
    return render(request, "student/student_dashboard.html", context)


# ===================== USER MANAGEMENT =====================

@login_required
def create_user_account(request):
    """
    Teachers can create student accounts
    School admins can create both student and teacher accounts
    """
    role = get_user_role(request.user)
    school = get_user_school(request.user)
    
    # Must be teacher or school admin
    if role not in ['teacher', 'school_admin']:
        messages.error(request, "You don't have permission to create accounts.")
        return redirect("teacher_dashboard")
    
    is_school_admin = (role == 'school_admin')
    
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        email = request.POST.get("email", "")
        first_name = request.POST.get("first_name", "")
        last_name = request.POST.get("last_name", "")
        new_user_role = request.POST.get("role", "student")
        
        # CRITICAL: Teachers can ONLY create students
        # School admins can create both students and teachers
        if not is_school_admin and new_user_role != "student":
            messages.error(request, "You can only create student accounts. Contact a school admin to create teacher accounts.")
            return redirect("create_user_account")
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("create_user_account")
        
        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            
            # Set staff status based on role
            if new_user_role == "teacher":
                user.is_staff = True
                user.save()
            else:
                user.is_staff = False
                user.save()
            
            # Create UserProfile
            UserProfile.objects.create(
                user=user,
                role=new_user_role,
                school=school
            )
            
            # Redirect appropriately
            if new_user_role == "student":
                messages.success(request, f"Student account '{username}' created successfully. Please complete the student profile.")
                return redirect("add_student")
            else:
                messages.success(request, f"Teacher account '{username}' created successfully.")
                return redirect("create_user_account")
                
        except Exception as e:
            messages.error(request, f"Error creating account: {str(e)}")
            return redirect("create_user_account")
    
    return render(request, "teacher/accounts/create_user.html", {
        "is_school_admin": is_school_admin,
        "school": school
    })


# ===================== SCHOOL USERS LIST =====================

@login_required
def change_user_password(request):
    """
    Change password for any user (teachers/students)
    Only accessible by school admins and teachers
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    
    role = get_user_role(request.user)
    school = get_user_school(request.user)
    
    if role not in ['teacher', 'school_admin']:
        return JsonResponse({"error": "Permission denied"}, status=403)
    
    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")
        new_password = data.get("new_password")
        
        if not user_id or not new_password:
            return JsonResponse({"error": "User ID and password required"}, status=400)
        
        user = get_object_or_404(User, id=user_id)
        
        # Verify user belongs to same school
        try:
            user_profile = user.profile
            if user_profile.school != school:
                return JsonResponse({"error": "User not in your school"}, status=403)
        except:
            # Check if it's a student
            try:
                student = user.student_profile
                if student.school != school:
                    return JsonResponse({"error": "User not in your school"}, status=403)
            except:
                return JsonResponse({"error": "User not found"}, status=404)
        
        # Change password
        user.set_password(new_password)
        user.save()
        
        return JsonResponse({
            "status": "success",
            "message": f"Password changed successfully for {user.username}"
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@login_required
def school_users_list(request):
    """
    View all teachers and students in the same school in a unified table
    """
    school = get_user_school(request.user)
    role = get_user_role(request.user)
    
    # Allow staff users to view even without a school profile
    if not school:
        if request.user.is_staff or request.user.is_superuser:
            # Get all schools and let admin choose
            schools = School.objects.all()
            
            # If there's only one school, use it
            if schools.count() == 1:
                school = schools.first()
            else:
                # Show error and suggest creating/assigning school
                messages.warning(request, 
                    "You don't have a school assigned. Please create a school or contact an administrator.")
                
                # Show all users without school filter (for superadmin)
                if request.user.is_superuser:
                    teachers = UserProfile.objects.filter(
                        role__in=['teacher', 'school_admin']
                    ).select_related('user').order_by('user__first_name', 'user__last_name')
                    
                    students = Student.objects.all().select_related('grade', 'user').order_by('grade__name', 'section', 'roll_number')
                else:
                    return redirect("teacher_dashboard")
        else:
            messages.error(request, "You are not assigned to a school. Please contact an administrator.")
            return redirect("teacher_dashboard")
    
    # Get search query
    search_query = request.GET.get('search', '').strip()
    
    # Get all user profiles from same school (teachers and school admins)
    if school:
        teachers = UserProfile.objects.filter(
            school=school,
            role__in=['teacher', 'school_admin']
        ).select_related('user').order_by('user__first_name', 'user__last_name')
        
        # Get student records with their user accounts
        students = Student.objects.filter(
            school=school
        ).select_related('grade', 'user').order_by('grade__name', 'section', 'roll_number')
    else:
        # Already filtered above for superuser
        pass
    
    # Apply search filter
    if search_query:
        teachers = teachers.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )
        students = students.filter(
            Q(full_name__icontains=search_query) |
            Q(roll_number__icontains=search_query) |
            Q(admission_id__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )
    
    # Combine into a unified list with user type
    all_users = []
    
    for teacher in teachers:
        all_users.append({
            'id': teacher.user.id,
            'name': f"{teacher.user.first_name} {teacher.user.last_name}".strip() or teacher.user.username,
            'username': teacher.user.username,
            'email': teacher.user.email,
            'role': teacher.get_role_display(),
            'type': 'teacher',
            'joined': teacher.created_at,
            'additional_info': None
        })
    
    for student in students:
        all_users.append({
            'id': student.user.id if student.user else None,
            'name': student.full_name,
            'username': student.user.username if student.user else 'No account',
            'email': student.user.email if student.user else '',
            'role': 'Student',
            'type': 'student',
            'joined': student.created_at,
            'additional_info': {
                'grade': student.grade.name,
                'section': student.section,
                'roll_number': student.roll_number,
                'admission_id': student.admission_id
            }
        })
    
    # Sort by name
    all_users.sort(key=lambda x: x['name'].lower())
    
    context = {
        'school': school,
        'all_users': all_users,
        'role': role,
        'search_query': search_query,
        'total_teachers': teachers.count(),
        'total_students': students.count(),
    }
    
    return render(request, "teacher/school/users_list.html", context)


# ===================== TESTS =====================

@login_required
def tests_list(request):
    school = get_user_school(request.user)
    tests = Test.objects.filter(created_by=request.user).order_by("-id")

    return render(
        request,
        "teacher/tests_list.html",
        {"tests": tests, "school": school}
    )


@login_required
def create_test(request):
    test = Test.objects.create(
        title="Untitled Test",
        created_by=request.user,
        is_published=False,
    )
    return redirect("edit_test", test_id=test.id)


@login_required
def test_editor(request, test_id):
    """
    Test editor with persistent assignment tags
    """
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    school = get_user_school(request.user)

    if request.method == "POST":
        # Save test details
        test.title = request.POST.get("title", test.title)
        test.is_published = bool(request.POST.get("is_published"))
        
        # Handle datetime
        start_time = request.POST.get("start_time")
        if start_time:
            test.start_time = start_time
            
        duration = request.POST.get("duration_minutes")
        if duration:
            test.duration_minutes = int(duration)
        
        # Handle subject
        subject_id = request.POST.get("subject")
        if subject_id:
            test.subject_id = subject_id
            
        test.save()

        # Handle assignments - get IDs from POST
        assigned_student_ids = request.POST.getlist("assigned_students")
        assigned_group_ids = request.POST.getlist("assigned_groups")
        
        # Update assignments
        test.assigned_students.set(assigned_student_ids)
        test.assigned_groups.set(assigned_group_ids)
        
        messages.success(request, "Test saved successfully!")
        return redirect("edit_test", test_id=test.id)

    # GET request - load test data
    test_questions = TestQuestion.objects.filter(
        test=test
    ).select_related('question', 'question__topic').order_by('order')
    
    # Get students and groups from same school
    students = Student.objects.filter(school=school).select_related('grade')
    groups = ClassGroup.objects.filter(school=school, created_by=request.user)
    
    # Get currently assigned students and groups
    assigned_students = test.assigned_students.all()
    assigned_groups = test.assigned_groups.all()
    
    subjects = Subject.objects.all()

    return render(
        request,
        "teacher/create_test.html",
        {
            "test": test,
            "test_questions": test_questions,
            "groups": groups,
            "students": students,
            "assigned_students": assigned_students,
            "assigned_groups": assigned_groups,
            "grades": Grade.objects.all(),
            "subjects": subjects,
            "school": school,
        }
    )


@login_required
def toggle_publish(request, test_id):
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    test.is_published = not test.is_published
    test.save()
    return redirect("tests_list")


@login_required
def delete_test(request, test_id):
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    test.delete()
    return redirect("tests_list")


@login_required
def duplicate_test(request, test_id):
    test = get_object_or_404(Test, id=test_id, created_by=request.user)

    new_test = Test.objects.create(
        title=f"{test.title} (Copy)",
        created_by=request.user,
        duration_minutes=test.duration_minutes,
        start_time=test.start_time,
        subject=test.subject,
    )

    # Copy test questions
    test_questions = TestQuestion.objects.filter(test=test).order_by('order')
    for tq in test_questions:
        TestQuestion.objects.create(
            test=new_test,
            question=tq.question,
            order=tq.order,
        )

    return redirect("tests_list")


@login_required
def autosave_test(request, test_id):
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    data = json.loads(request.body)

    test.title = data.get("title", test.title)
    test.is_published = data.get("published", test.is_published)
    test.save()

    return JsonResponse({"status": "ok"})


# ===================== STUDENT TEST LIST WITH SORTING =====================

@login_required
def student_tests_list(request):
    """
    Show all published tests assigned to the logged-in student
    with sorting and filtering
    """
    # Get student profile
    try:
        student = Student.objects.get(created_by=request.user)
    except Student.DoesNotExist:
        return render(request, "student/student_tests_list.html", {
            "tests": [],
            "error": "Student profile not found"
        })
    
    # Get sorting parameters
    sort_by = request.GET.get('sort', 'date')  # date, subject
    order = request.GET.get('order', 'desc')  # asc, desc
    subject_filter = request.GET.get('subject', '')  # filter by subject
    
    # Get tests assigned directly
    directly_assigned = Test.objects.filter(
        assigned_students=student,
        is_published=True
    ).exclude(
        excluded_students=student
    )
    
    # Get tests assigned through groups
    student_groups = ClassGroup.objects.filter(students=student)
    group_assigned = Test.objects.filter(
        assigned_groups__in=student_groups,
        is_published=True
    ).exclude(
        excluded_students=student
    )
    
    # Combine and remove duplicates
    all_tests = (directly_assigned | group_assigned).distinct()
    
    # Apply subject filter
    if subject_filter:
        all_tests = all_tests.filter(subject_id=subject_filter)
    
    # Apply sorting
    if sort_by == 'subject':
        all_tests = all_tests.order_by('subject__name' if order == 'asc' else '-subject__name')
    else:  # date
        all_tests = all_tests.order_by('created_at' if order == 'asc' else '-created_at')
    
    # Add attempt status
    tests_with_status = []
    for test in all_tests:
        attempts = StudentAnswer.objects.filter(
            student=student,
            test=test
        ).count()
        
        tests_with_status.append({
            'test': test,
            'attempted': attempts > 0,
            'attempt_count': attempts
        })
    
    # Get available subjects for filter dropdown
    subjects = Subject.objects.filter(
        test__in=all_tests
    ).distinct()
    
    return render(request, "student/student_tests_list.html", {
        "tests_with_status": tests_with_status,
        "student": student,
        "sort_by": sort_by,
        "order": order,
        "subject_filter": subject_filter,
        "subjects": subjects,
    })


# ===================== QUESTIONS =====================

@login_required
def question_library(request):
    """
    Question library with option to hide inline-created questions
    """
    school = get_user_school(request.user)
    qs = Question.objects.filter(
        created_by=request.user
    ).select_related("grade", "subject", "topic").prefetch_related("learning_objectives")

    # âœ… NEW: Filter out questions that were created inline for tests (optional)
    # Uncomment the line below if you want to hide inline questions by default
    # qs = qs.annotate(test_count=models.Count('tests')).filter(test_count=0)

    # Filters
    grade = request.GET.get("grade")
    subject = request.GET.get("subject")
    qtype = request.GET.get("question_type")
    marks = request.GET.get("marks")
    year = request.GET.get("year")

    if grade:
        qs = qs.filter(grade_id=grade)
    if subject:
        qs = qs.filter(subject_id=subject)
    if qtype:
        qs = qs.filter(question_type=qtype)
    if marks:
        qs = qs.filter(marks=marks)
    if year:
        qs = qs.filter(year=year)

    topics = request.GET.getlist("topics[]")
    if topics:
        qs = qs.filter(topic_id__in=topics)

    los = request.GET.getlist("los[]")
    if los:
        qs = qs.filter(learning_objectives__id__in=los).distinct()

    # âœ… IMPROVED: Add test count annotation for UI display
    qs = qs.annotate(test_count=models.Count('tests'))

    return render(
        request,
        "teacher/question_library.html",
        {
            "questions": qs,
            "grades": Grade.objects.all(),
            "subjects": Subject.objects.all(),
            "topics": Topic.objects.all(),
            "school": school,
        }
    )
    
@login_required
def add_edit_question(request, question_id=None):
    question = None
    selected_lo_ids = []

    if question_id:
        question = get_object_or_404(
            Question,
            id=question_id,
            created_by=request.user
        )
        selected_lo_ids = list(
            question.learning_objectives.values_list("id", flat=True)
        )

    grades = Grade.objects.all()
    subjects = Subject.objects.all()
    topics = Topic.objects.all()

    if request.method == "POST":
        data = request.POST

        question_text = data.get("question_text", "").strip()
        answer_text = data.get("answer_text", "").strip()

        if not question_text:
            raise ValueError("Question text is empty")

        if not question:
            question = Question.objects.create(
                grade_id=data["grade"],
                subject_id=data["subject"],
                topic_id=data["topic"],
                year=data.get("year") or None,
                question_text=question_text,
                answer_text=answer_text,
                marks=data["marks"],
                question_type=data["question_type"],
                created_by=request.user,
            )
        else:
            question.grade_id = data["grade"]
            question.subject_id = data["subject"]
            question.topic_id = data["topic"]
            question.year = data.get("year") or None
            question.question_text = question_text
            question.answer_text = answer_text
            question.marks = data["marks"]
            question.question_type = data["question_type"]
            question.save()

        los_raw = data.get("los_selected", "")
        lo_ids = [int(x) for x in los_raw.split(",") if x]
        question.learning_objectives.set(lo_ids)

        return redirect("question_library")

    years = list(range(2026, 1999, -1))

    return render(
        request,
        "teacher/question_editor.html",
        {
            "question": question,
            "grades": grades,
            "subjects": subjects,
            "topics": topics,
            "selected_lo_ids": selected_lo_ids,
            "years": years,
        }
    )

@login_required
def inline_add_question(request, test_id):
    """
    Create question inline with full LO support
    """
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    test = get_object_or_404(Test, id=test_id, created_by=request.user)

    try:
        data = json.loads(request.body)

        if not data.get("question_text"):
            return JsonResponse({"error": "Question text is required"}, status=400)
        
        if not data.get("grade") or not data.get("subject") or not data.get("topic"):
            return JsonResponse({"error": "Grade, subject, and topic are required"}, status=400)

        # Create question
        question = Question.objects.create(
            question_text=data["question_text"],
            answer_text=data.get("answer_text", ""),
            marks=data.get("marks", 1),
            question_type=data.get("question_type", "theory"),
            year=data.get("year") or None,
            grade_id=data["grade"],
            subject_id=data["subject"],
            topic_id=data["topic"],
            created_by=request.user,
        )
        
        # âœ… UPDATED: Handle learning objectives
        lo_ids = data.get("learning_objectives", [])
        if lo_ids:
            # Validate LO IDs belong to the selected topic
            valid_los = LearningObjective.objects.filter(
                id__in=lo_ids,
                topic_id=data["topic"]
            )
            question.learning_objectives.set(valid_los)

        # Add to test
        last_order = (
            TestQuestion.objects
            .filter(test=test)
            .aggregate(max_order=models.Max("order"))
            ["max_order"] or 0
        )

        tq = TestQuestion.objects.create(
            test=test,
            question=question,
            order=last_order + 1
        )

        return JsonResponse({
            "status": "ok",
            "question_id": question.id,
            "order": tq.order,
            "message": "Question added successfully with learning objectives"
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def remove_question_from_test(request, test_id, test_question_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    test_question = get_object_or_404(TestQuestion, id=test_question_id, test=test)
    
    test_question.delete()
    
    # Reorder
    remaining_questions = TestQuestion.objects.filter(test=test).order_by('order')
    for idx, tq in enumerate(remaining_questions, start=1):
        if tq.order != idx:
            tq.order = idx
            tq.save()
    
    return JsonResponse({"status": "ok", "message": "Question removed"})


@login_required
def add_questions_to_test(request, test_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    
    try:
        data = json.loads(request.body)
        question_ids = data.get("question_ids", [])
        
        if not question_ids:
            return JsonResponse({"error": "No questions selected"}, status=400)
        
        max_order = TestQuestion.objects.filter(test=test).aggregate(
            models.Max('order')
        )['order__max'] or 0
        
        for idx, question_id in enumerate(question_ids):
            question = get_object_or_404(Question, id=question_id)
            
            if not TestQuestion.objects.filter(test=test, question=question).exists():
                TestQuestion.objects.create(
                    test=test,
                    question=question,
                    order=max_order + idx + 1
                )
        
        return JsonResponse({"status": "ok", "message": "Questions added successfully"})
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ===================== STUDENTS =====================

@login_required
def add_student(request):
    school = get_user_school(request.user)
    
    if request.method == "POST":
        Student.objects.create(
            full_name=request.POST["full_name"],
            roll_number=request.POST.get("roll_number", ""),
            admission_id=request.POST.get("admission_id", ""),
            grade_id=request.POST["grade"],
            section=request.POST["section"],
            school=school,
            created_by=request.user
        )
        messages.success(request, f"Student '{request.POST['full_name']}' added successfully!")
        return redirect("school_users_list")  # ✅ FIXED: Changed from students_list

    return render(request, "teacher/students/add_student.html", {
        "grades": Grade.objects.all(),
        "school": school
    })

@login_required
def edit_student(request, student_id):
    school = get_user_school(request.user)
    student = get_object_or_404(Student, id=student_id, school=school)

    if request.method == "POST":
        student.full_name = request.POST.get("full_name")
        student.roll_number = request.POST.get("roll_number", "")
        student.admission_id = request.POST.get("admission_id", "")
        student.grade_id = request.POST.get("grade")
        student.section = request.POST.get("section")
        student.save()
        messages.success(request, f"Student '{student.full_name}' updated successfully!")
        return redirect("school_users_list")  # ✅ FIXED: Changed from students_list

    return render(
        request,
        "teacher/students/edit_student.html",
        {
            "student": student,
            "grades": Grade.objects.all(),
            "school": school,
        }
    )

# ===================== GROUPS =====================

@login_required
def add_group(request):
    school = get_user_school(request.user)
    
    if request.method == "POST":
        group = ClassGroup.objects.create(
            name=request.POST["name"],
            grade_id=request.POST["grade"],
            section=request.POST["section"],
            subject_id=request.POST["subject"],
            school=school,
            created_by=request.user
        )

        student_ids = request.POST.getlist("students")
        group.students.set(student_ids)

        return redirect("groups_list")

    return render(request, "teacher/groups/add_group.html", {
        "grades": Grade.objects.all(),
        "subjects": Subject.objects.all(),
        "students": Student.objects.filter(school=school),
        "school": school,
    })


@login_required
def groups_list(request):
    school = get_user_school(request.user)
    groups = ClassGroup.objects.filter(school=school, created_by=request.user)
    return render(
        request,
        "teacher/groups/groups_list.html",
        {"groups": groups, "school": school}
    )


# ===================== AJAX =====================

@login_required
def ajax_topics(request):
    grade_id = request.GET.get("grade_id")
    subject_id = request.GET.get("subject_id")

    qs = Topic.objects.all()

    if grade_id:
        qs = qs.filter(grade_id=grade_id)
    if subject_id:
        qs = qs.filter(subject_id=subject_id)

    topics = [
        {"id": t.id, "name": t.name}
        for t in qs.order_by("name")
    ]

    return JsonResponse({"topics": topics})


@login_required
@require_GET
def ajax_learning_objectives(request):
    """
    Get learning objectives for a topic
    """
    topic_id = request.GET.get("topic_id")

    if not topic_id:
        return JsonResponse({"los": []})

    los = LearningObjective.objects.filter(
        topic_id=topic_id
    ).order_by("code")

    return JsonResponse({
        "los": [
            {
                "id": lo.id,
                "code": lo.code,
                "description": lo.description,
            }
            for lo in los
        ]
    })
    
@staff_member_required
def admin_dashboard(request):
    return render(request, "admin_panel/admin_dashboard.html")
    
@login_required
def class_performance(request):
    school = get_user_school(request.user)
    return render(request, "teacher/performance/class_performance.html", {
        "school": school
    })


@login_required
def student_performance(request, student_id):
    school = get_user_school(request.user)
    student = get_object_or_404(Student, id=student_id, school=school)
    return render(request, "teacher/performance/student_performance.html", {
        "school": school,
        "student": student
    })

# Add these views to your views.py file

@login_required
def groups_list(request):
    school = get_user_school(request.user)
    groups = ClassGroup.objects.filter(school=school, created_by=request.user).prefetch_related('students', 'subject', 'grade')
    
    # Calculate statistics
    total_students = sum(group.students.count() for group in groups)
    unique_subjects = len(set(group.subject for group in groups if group.subject))
    
    return render(
        request,
        "teacher/groups/groups_list.html",
        {
            "groups": groups,
            "school": school,
            "total_students": total_students,
            "unique_subjects": unique_subjects,
        }
    )


@login_required
def edit_group(request, group_id):
    school = get_user_school(request.user)
    group = get_object_or_404(ClassGroup, id=group_id, school=school, created_by=request.user)

    if request.method == "POST":
        group.name = request.POST["name"]
        group.grade_id = request.POST["grade"]
        group.section = request.POST["section"]
        group.subject_id = request.POST["subject"]
        group.save()

        student_ids = request.POST.getlist("students")
        group.students.set(student_ids)

        messages.success(request, f"Group '{group.name}' updated successfully!")
        return redirect("groups_list")

    return render(request, "teacher/groups/edit_group.html", {
        "group": group,
        "grades": Grade.objects.all(),
        "subjects": Subject.objects.all(),
        "students": Student.objects.filter(school=school),
        "school": school,
    })


@login_required
def delete_group(request, group_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    
    school = get_user_school(request.user)
    group = get_object_or_404(ClassGroup, id=group_id, school=school, created_by=request.user)
    
    group_name = group.name
    group.delete()
    
    return JsonResponse({"status": "success", "message": f"Group '{group_name}' deleted successfully"})
    
@login_required
def bulk_import_upload(request):
    """
    Handle PDF upload and initiate parsing
    """
    if request.method == "POST":
        pdf_file = request.FILES['pdf']
        grade_id = request.POST.get('grade')
        subject_id = request.POST.get('subject')
        
        # Save temporarily
        import_session = ImportSession.objects.create(
            uploaded_by=request.user,
            pdf_file=pdf_file,
            grade_id=grade_id,
            subject_id=subject_id,
            status='processing'
        )
        
        # Trigger async task
        parse_pdf_questions.delay(import_session.id)
        
        return JsonResponse({
            'session_id': import_session.id,
            'status': 'processing'
        })
        
@login_required
def bulk_import_preview(request, session_id):
    """
    Get parsed questions for review
    """
    session = get_object_or_404(ImportSession, id=session_id)
    
    questions = ParsedQuestion.objects.filter(
        import_session=session
    ).order_by('order')
    
    return JsonResponse({
        'questions': [
            {
                'id': q.id,
                'question_text': q.question_text,
                'answer_text': q.answer_text,
                'marks': q.marks,
                'question_type': q.question_type,
                'topic_id': q.topic_id
            }
            for q in questions
        ]
    })
    
@login_required
def bulk_import_confirm(request, session_id):
    """
    Import validated questions to library
    """
    session = get_object_or_404(ImportSession, id=session_id)
    data = json.loads(request.body)
    
    imported_count = 0
    for q_data in data['questions']:
        question = Question.objects.create(
            question_text=q_data['question_text'],
            answer_text=q_data.get('answer_text', ''),
            marks=q_data['marks'],
            question_type=q_data['question_type'],
            grade_id=session.grade_id,
            subject_id=session.subject_id,
            topic_id=q_data.get('topic_id'),
            created_by=request.user
        )
        
        # Set LOs
        if 'learning_objective_ids' in q_data:
            question.learning_objectives.set(q_data['learning_objective_ids'])
        
        imported_count += 1
    
    session.status = 'completed'
    session.imported_count = imported_count
    session.save()
    
    return JsonResponse({
        'status': 'success',
        'imported_count': imported_count
    })