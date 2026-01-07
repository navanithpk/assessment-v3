from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.admin.views.decorators import staff_member_required
import json
import re
from django.template.loader import render_to_string
from django.db import models
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
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.db.models import Count, Q

@login_required
def autosave_test(request, test_id):
    """
    Autosave test details
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    
    try:
        data = json.loads(request.body)
        
        # Only allow autosave of basic fields
        test.title = data.get("title", test.title)
        
        # Don't autosave publish status - that should be explicit
        # test.is_published = data.get("published", test.is_published)
        
        test.save()
        
        return JsonResponse({"status": "ok"})
    except Exception as e:
        print(f"Autosave error: {str(e)}")
        return JsonResponse({"error": str(e)}, status=400)

@staff_member_required
def admin_dashboard(request):
    """
    Admin dashboard wrapper.
    Loads Django admin inside an iframe.
    """
    return render(request, "admin_panel/admin_dashboard.html")


@login_required
@require_GET
def ajax_questions(request):
    qs = Question.objects.filter(created_by=request.user).select_related(
        "topic", "grade", "subject"
    )

    grade_id = request.GET.get("grade")
    subject_id = request.GET.get("subject")
    topic_ids = request.GET.getlist("topics[]")
    question_type = request.GET.get("question_type")
    marks = request.GET.get("marks")
    year = request.GET.get("year")
    sort = request.GET.get("sort")

    if grade_id:
        qs = qs.filter(grade_id=grade_id)

    if subject_id:
        qs = qs.filter(subject_id=subject_id)

    if topic_ids:
        qs = qs.filter(topic_id__in=topic_ids)

    if question_type:
        qs = qs.filter(question_type=question_type)

    if marks:
        qs = qs.filter(marks=marks)

    if year:
        qs = qs.filter(year=year)

    if sort == "marks":
        qs = qs.order_by("marks")
    elif sort == "latest":
        qs = qs.order_by("-id")
    elif sort == "oldest":
        qs = qs.order_by("id")

    data = {
        "questions": [
            {
                "id": q.id,
                "text": q.question_text,
                "marks": q.marks,
                "type": q.question_type,
                "topic": q.topic.name,
            }
            for q in qs
        ]
    }

    return JsonResponse(data)


@login_required
def teacher_dashboard(request):
    """
    Updated dashboard with student management and stats
    """
    from core.models import Test, Question, Student, ClassGroup, Grade
    
    tests_count = Test.objects.filter(created_by=request.user).count()
    questions_count = Question.objects.filter(created_by=request.user).count()
    students_count = Student.objects.filter(created_by=request.user).count()
    groups_count = ClassGroup.objects.filter(created_by=request.user).count()
    
    # Get recent students (last 10)
    recent_students = Student.objects.filter(
        created_by=request.user
    ).select_related('grade').order_by('-created_at')[:10]
    
    # Get all grades for the form
    grades = Grade.objects.all()
    
    return render(request, 'teacher/teacher_dashboard.html', {
        'tests_count': tests_count,
        'questions_count': questions_count,
        'students_count': students_count,
        'groups_count': groups_count,
        'recent_students': recent_students,
        'grades': grades,
    })

@login_required
def student_dashboard(request):
    """
    Student dashboard showing available tests
    """
    # Get the student profile
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return render(request, 'student/no_profile.html')
    
    # Get assigned tests
    assigned_tests = Test.objects.filter(
        is_published=True
    ).filter(
        models.Q(assigned_students=student) | 
        models.Q(assigned_groups__students=student)
    ).exclude(
        excluded_students=student
    ).distinct().order_by('-created_at')
    
    # Get completed tests (tests where student has submitted answers)
    completed_test_ids = StudentAnswer.objects.filter(
        student=student
    ).values_list('test_id', flat=True).distinct()
    
    return render(request, 'student/student_dashboard.html', {
        'student': student,
        'assigned_tests': assigned_tests,
        'completed_test_ids': list(completed_test_ids),
    })

def root_redirect(request):
    if request.user.is_authenticated:
        return redirect("teacher_dashboard")
    return redirect("login")

@login_required
def tests_list(request):
    """
    List all tests with proper status display
    """
    tests = Test.objects.filter(created_by=request.user).prefetch_related(
        'assigned_students',
        'assigned_groups',
        'test_questions'
    ).order_by("-id")
    
    # Add submission counts to each test
    test_data = []
    for test in tests:
        submission_count = StudentAnswer.objects.filter(test=test).values('student').distinct().count()
        assigned_count = test.assigned_students.count()
        
        # Count students from groups
        group_student_count = 0
        for group in test.assigned_groups.all():
            group_student_count += group.students.count()
        
        total_assigned = assigned_count + group_student_count
        
        test_data.append({
            'test': test,
            'submission_count': submission_count,
            'total_assigned': total_assigned,
            'has_submissions': submission_count > 0,
        })
    
    return render(request, "teacher/tests_list.html", {
        "test_data": test_data
    })

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
    Returns learning objectives for a given topic ID.
    Used in question editor and test editor.
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


@login_required
def list_learning_objectives(request):
    los = LearningObjective.objects.select_related(
        "grade", "subject", "topic"
    )

    return render(
        request,
        "admin_panel/lo_list.html",
        {"learning_objectives": los}
    )


@login_required
def question_library(request):
    qs = Question.objects.filter(
        created_by=request.user
    ).select_related("grade", "subject", "topic").prefetch_related("learning_objectives")

    # ---------- BASIC FILTERS ----------
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

    # ---------- TOPIC FILTER ----------
    topics = request.GET.getlist("topics[]")
    if topics:
        qs = qs.filter(topic_id__in=topics)

    # ---------- LO FILTER ----------
    los = request.GET.getlist("los[]")
    if los:
        qs = qs.filter(learning_objectives__id__in=los).distinct()

    return render(
        request,
        "teacher/question_library.html",
        {
            "questions": qs,
            "grades": Grade.objects.all(),
            "subjects": Subject.objects.all(),
            "topics": Topic.objects.all(),
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

    # -----------------------
    # HANDLE FORM SUBMISSION
    # -----------------------
    if request.method == "POST":
        data = request.POST

        question_text = data.get("question_text", "").strip()
        answer_text = data.get("answer_text", "").strip()

        if not question_text:
            raise ValueError("Question text is empty — editor not wired")

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

        # Learning Objectives (from Quill-safe hidden input)
        los_raw = data.get("los_selected", "")
        lo_ids = [int(x) for x in los_raw.split(",") if x]
        question.learning_objectives.set(lo_ids)

        return redirect("question_library")

    # -----------------------
    # GET REQUEST (PAGE LOAD)
    # -----------------------
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
def toggle_publish(request, test_id):
    """
    Toggle test publish status with validation
    """
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    
    # Check if test has questions
    if not test.test_questions.exists():
        return JsonResponse({
            'status': 'error',
            'error': 'Cannot publish test without questions'
        }, status=400)
    
    # Toggle publish status
    test.is_published = not test.is_published
    test.save()
    
    print(f"Test '{test.title}' publish status: {test.is_published}")
    
    return redirect("tests_list")

@login_required
def delete_test(request, test_id):
    """
    Delete test with validation
    """
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    
    # Check if test has submissions
    if StudentAnswer.objects.filter(test=test).exists():
        # Don't allow deletion if students have submitted
        return JsonResponse({
            'status': 'error',
            'error': 'Cannot delete test with student submissions'
        }, status=403)
    
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
    )

    # Copy test questions properly
    test_questions = TestQuestion.objects.filter(test=test).order_by('order')
    for tq in test_questions:
        TestQuestion.objects.create(
            test=new_test,
            question=tq.question,
            order=tq.order,
        )

    return redirect("tests_list")

def custom_login(request):
    error = None

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        role = request.POST.get("role")

        user = authenticate(request, username=username, password=password)

        if user is None:
            error = "Invalid username or password"
        else:
            login(request, user)

            # Force landing pages by role
            if role == "teacher":
                # Check if user is staff/teacher
                if user.is_staff or not hasattr(user, 'student_profile'):
                    return redirect("teacher_dashboard")
                else:
                    error = "You don't have teacher access"
                    from django.contrib.auth import logout
                    logout(request)
            elif role == "student":
                # Check if user has student profile
                if hasattr(user, 'student_profile'):
                    return redirect("student_dashboard")
                else:
                    error = "No student profile found for this account"
                    from django.contrib.auth import logout
                    logout(request)
            elif role == "admin":
                if user.is_superuser:
                    return redirect("/admin/")
                else:
                    error = "You don't have admin access"
                    from django.contrib.auth import logout
                    logout(request)

    return render(request, "registration/login.html", {"error": error})
    
# TEMP staging (replace later with JSON / session)
STAGING_QUESTIONS = [
    {
        "number": 1,
        "question_html": "<p>The diagram shows a measuring cylinder...</p>",
        "options": ["13.0 cm³", "13.5 cm³", "16.0 cm³", "17.0 cm³"],
        "answer": "C"
    },
]

from .models import Student, ClassGroup

@login_required
def test_editor(request, test_id):
    """
    Edit test with proper assignment and publish status handling
    """
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    
    # Check if test has submissions
    has_submissions = StudentAnswer.objects.filter(test=test).exists()
    
    # Prevent editing if test is published and has submissions
    if request.method == "POST":
        # Check if trying to edit questions/content when published
        if test.is_published and has_submissions:
            return JsonResponse({
                'status': 'error',
                'error': 'Cannot edit test that has student submissions. Unpublish the test first.'
            }, status=403)
        
        # Save basic test info
        test.title = request.POST.get("title", test.title)
        test.start_time = request.POST.get("start_time") or None
        test.duration_minutes = request.POST.get("duration_minutes") or None
        
        # Handle publish status
        is_published = request.POST.get("is_published") == "on"
        test.is_published = is_published
        
        test.save()
        
        # Handle assignments - FIXED: Now properly saves M2M relationships
        # Get selected students
        assigned_student_ids = request.POST.getlist("assigned_students")
        if assigned_student_ids:
            test.assigned_students.set(assigned_student_ids)
        else:
            test.assigned_students.clear()
        
        # Get selected groups
        assigned_group_ids = request.POST.getlist("assigned_groups")
        if assigned_group_ids:
            test.assigned_groups.set(assigned_group_ids)
        else:
            test.assigned_groups.clear()
        
        # Get excluded students
        excluded_student_ids = request.POST.getlist("excluded_students")
        if excluded_student_ids:
            test.excluded_students.set(excluded_student_ids)
        else:
            test.excluded_students.clear()
        
        print(f"Test saved: {test.title}")
        print(f"Published: {test.is_published}")
        print(f"Assigned students: {list(test.assigned_students.all())}")
        print(f"Assigned groups: {list(test.assigned_groups.all())}")
        
        return redirect("tests_list")
    
    # GET request - load test with all assignments
    test_questions = TestQuestion.objects.filter(test=test).select_related(
        'question', 'question__topic', 'question__grade', 'question__subject'
    ).order_by('order')
    
    # Get all students and groups for assignment
    all_students = Student.objects.filter(created_by=request.user).select_related('grade', 'user')
    all_groups = ClassGroup.objects.filter(created_by=request.user).select_related('grade', 'subject')
    
    # Get currently assigned
    assigned_student_ids = list(test.assigned_students.values_list('id', flat=True))
    assigned_group_ids = list(test.assigned_groups.values_list('id', flat=True))
    excluded_student_ids = list(test.excluded_students.values_list('id', flat=True))
    
    return render(request, "teacher/create_test.html", {
        "test": test,
        "test_questions": test_questions,
        "groups": all_groups,
        "students": all_students,
        "grades": Grade.objects.all(),
        "subjects": Subject.objects.all(),
        "has_submissions": has_submissions,
        "assigned_student_ids": assigned_student_ids,
        "assigned_group_ids": assigned_group_ids,
        "excluded_student_ids": excluded_student_ids,
    })


@login_required
def create_test(request):
    # Always create a test first, then redirect to edit it
    test = Test.objects.create(
        title="Untitled Test",
        created_by=request.user,
        is_published=False,
    )
    return redirect("edit_test", test_id=test.id)


@login_required
def edit_test(request, test_id):
    """Alias for test_editor for backward compatibility"""
    return test_editor(request, test_id)

@login_required
def remove_question_from_test(request, test_id, test_question_id):
    """
    Remove a question from a test with validation
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    
    # Prevent editing published tests with submissions
    if test.is_published and StudentAnswer.objects.filter(test=test).exists():
        return JsonResponse({
            "error": "Cannot modify published test with submissions"
        }, status=403)
    
    test_question = get_object_or_404(TestQuestion, id=test_question_id, test=test)
    test_question.delete()
    
    # Reorder remaining questions
    remaining_questions = TestQuestion.objects.filter(test=test).order_by('order')
    for idx, tq in enumerate(remaining_questions, start=1):
        if tq.order != idx:
            tq.order = idx
            tq.save()
    
    return JsonResponse({"status": "ok", "message": "Question removed"})

@login_required  
def reorder_test_questions(request, test_id):
    """
    Reorder questions in a test via drag-and-drop
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    
    try:
        data = json.loads(request.body)
        question_order = data.get("question_order", [])
        
        # Update order for each question
        for idx, tq_id in enumerate(question_order, start=1):
            TestQuestion.objects.filter(
                id=tq_id, 
                test=test
            ).update(order=idx)
        
        return JsonResponse({"status": "ok"})
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@login_required
def import_questions_review(request):
    index = int(request.GET.get("i", 0))

    if index >= len(STAGING_QUESTIONS):
        return render(request, "teacher/import_done.html")

    q = STAGING_QUESTIONS[index]

    if request.method == "POST":
        Question.objects.create(
            question_text=request.POST["question_text"],
            answer_text=request.POST["answer_text"],
            marks=1,
            question_type="mcq",
            year=request.POST.get("year"),
            grade_id=request.POST["grade"],
            subject_id=request.POST["subject"],
            topic_id=request.POST["topic"],
            created_by=request.user,
        )
        return redirect(f"?i={index+1}")

    context = {
        "q": q,
        "index": index + 1,
        "total": len(STAGING_QUESTIONS),
        "grades": Grade.objects.all(),
        "subjects": Subject.objects.all(),
    }

    return render(request, "teacher/import_questions.html", context)

from django.contrib.auth.models import User
from django.db import transaction

@login_required
def add_student(request):
    """
    Handle adding a new student with user account creation
    Username can be email or simple username
    """
    if request.method == "POST":
        try:
            # Check if it's JSON (AJAX) or form data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST
            
            # Get username (required) - can be email
            username = data.get("username", "").strip()
            if not username:
                raise ValueError("Username/Email is required")
            
            # Validate username format - allow email addresses
            # Allow letters, numbers, dots, dashes, underscores, and @ for emails
            if not re.match(r'^[a-zA-Z0-9.@_-]+$', username):
                raise ValueError("Username can only contain letters, numbers, dots, @, dashes and underscores")
            
            # Start transaction
            with transaction.atomic():
                # Check if username already exists
                if User.objects.filter(username=username).exists():
                    raise ValueError(f"Username/Email '{username}' already exists")
                
                # Get password (required)
                password = data.get("password", "").strip()
                if not password:
                    raise ValueError("Password is required")
                
                if len(password) < 6:
                    raise ValueError("Password must be at least 6 characters long")
                
                # Create User
                name_parts = data.get("full_name", "").split()
                user = User.objects.create_user(
                    username=username,
                    email=username if '@' in username else '',  # Set email if it's an email
                    first_name=name_parts[0] if name_parts else '',
                    last_name=' '.join(name_parts[1:]) if len(name_parts) > 1 else '',
                )
                user.set_password(password)
                user.save()
                
                # Create Student
                student = Student.objects.create(
                    user=user,
                    full_name=data.get("full_name"),
                    roll_number=data.get("roll_number", ""),
                    admission_id=data.get("admission_id", ""),
                    grade_id=data.get("grade"),
                    section=data.get("section"),
                    created_by=request.user
                )
            
            # Return JSON for AJAX requests
            if request.content_type == 'application/json':
                return JsonResponse({
                    'status': 'success',
                    'student': {
                        'id': student.id,
                        'full_name': student.full_name,
                        'roll_number': student.roll_number,
                        'admission_id': student.admission_id,
                        'grade': student.grade.name,
                        'section': student.section,
                        'username': student.user.username,
                    }
                })
            else:
                return redirect("students_list")
                
        except ValueError as e:
            print(f"ValueError in add_student: {str(e)}")  # Debug
            if request.content_type == 'application/json':
                return JsonResponse({
                    'status': 'error',
                    'error': str(e)
                }, status=400)
            else:
                return render(request, "teacher/students/add_student.html", {
                    "grades": Grade.objects.all(),
                    "error": str(e)
                })
        except Exception as e:
            print(f"Exception in add_student: {str(e)}")  # Debug
            import traceback
            traceback.print_exc()
            
            if request.content_type == 'application/json':
                return JsonResponse({
                    'status': 'error',
                    'error': str(e)
                }, status=400)
            else:
                return render(request, "teacher/students/add_student.html", {
                    "grades": Grade.objects.all(),
                    "error": str(e)
                })
    
    # GET request
    return render(request, "teacher/students/add_student.html", {
        "grades": Grade.objects.all()
    })


@login_required
def students_list(request):
    """
    Display list of all students with filtering
    Search now includes username
    """
    students = Student.objects.filter(
        created_by=request.user
    ).select_related('grade', 'user').order_by('grade', 'section', 'roll_number')
    
    # Apply filters
    search = request.GET.get('search')
    if search:
        students = students.filter(
            Q(full_name__icontains=search) |
            Q(roll_number__icontains=search) |
            Q(admission_id__icontains=search) |
            Q(user__username__icontains=search)  # Added username search
        )
    
    grade_filter = request.GET.get('grade')
    if grade_filter:
        students = students.filter(grade_id=grade_filter)
    
    section_filter = request.GET.get('section')
    if section_filter:
        students = students.filter(section__iexact=section_filter)
    
    # Get stats
    all_students = Student.objects.filter(created_by=request.user)
    grades_count = all_students.values('grade').distinct().count()
    sections_count = all_students.values('section').distinct().count()
    
    return render(request, "teacher/students/students_list.html", {
        "students": students,
        "all_grades": Grade.objects.all(),
        "grades_count": grades_count,
        "sections_count": sections_count,
    })

    
@login_required
def add_group(request):
    if request.method == "POST":
        group = ClassGroup.objects.create(
            name=request.POST["name"],
            grade_id=request.POST["grade"],
            section=request.POST["section"],
            subject_id=request.POST["subject"],
            created_by=request.user
        )

        student_ids = request.POST.getlist("students")
        group.students.set(student_ids)

        return redirect("groups_list")

    return render(request, "teacher/groups/add_group.html", {
        "grades": Grade.objects.all(),
        "subjects": Subject.objects.all(),
        "students": Student.objects.filter(created_by=request.user),
    })


@login_required
def groups_list(request):
    groups = ClassGroup.objects.filter(created_by=request.user)
    return render(
        request,
        "teacher/groups/groups_list.html",
        {"groups": groups}
    )


@login_required
def class_performance(request):
    test_id = request.GET.get("test")
    group_id = request.GET.get("group")

    results = []

    if test_id and group_id:
        test = get_object_or_404(Test, id=test_id)
        group = get_object_or_404(ClassGroup, id=group_id)

        for student in group.students.all():
            attempts = StudentAnswer.objects.filter(
                student=student,
                test=test
            )

            total = sum(a.marks_awarded or 0 for a in attempts)
            results.append({
                "student": student,
                "score": total,
            })

    return render(request, "teacher/performance/class_performance.html", {
        "tests": Test.objects.filter(created_by=request.user),
        "groups": ClassGroup.objects.filter(created_by=request.user),
        "results": results,
    })


@login_required
def student_performance(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    attempts = StudentAnswer.objects.filter(student=student).select_related('test', 'question')

    return render(request, "teacher/performance/student_performance.html", {
        "student": student,
        "attempts": attempts,
    })

@login_required
def get_student(request, student_id):
    """
    Get student data for editing (AJAX endpoint)
    """
    try:
        student = get_object_or_404(
            Student, 
            id=student_id, 
            created_by=request.user
        )
        
        return JsonResponse({
            'status': 'success',
            'student': {
                'id': student.id,
                'full_name': student.full_name,
                'roll_number': student.roll_number or '',
                'admission_id': student.admission_id or '',
                'grade_id': student.grade_id,
                'section': student.section,
                'username': student.user.username if student.user else '',
            }
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=404)

@login_required
def edit_student(request, student_id):
    """
    Edit student details including username and password
    """
    student = get_object_or_404(
        Student, 
        id=student_id, 
        created_by=request.user
    )

    if request.method == "POST":
        try:
            # Debug: Print request info
            print(f"Content-Type: {request.content_type}")
            print(f"Request body: {request.body[:200] if request.body else 'Empty'}")
            
            # Check if it's JSON (AJAX) or form data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST
            
            print(f"Parsed data: {data}")  # Debug
            
            # Get username (required) - can be email
            new_username = data.get("username", "").strip()
            if not new_username:
                raise ValueError("Username/Email is required")
            
            # Validate username format - allow email addresses
            if not re.match(r'^[a-zA-Z0-9.@_-]+$', new_username):
                raise ValueError("Username can only contain letters, numbers, dots, @, dashes and underscores")
            
            with transaction.atomic():
                # Update student info
                student.full_name = data.get("full_name", student.full_name)
                student.roll_number = data.get("roll_number", "")
                student.admission_id = data.get("admission_id", "")
                student.grade_id = data.get("grade", student.grade_id)
                student.section = data.get("section", student.section)
                student.save()
                
                print(f"Student updated: {student.full_name}")  # Debug
                
                # Update or create user account
                if student.user:
                    print(f"Updating existing user: {student.user.username}")  # Debug
                    
                    # Check if username is changing
                    if new_username != student.user.username:
                        # Check if new username is available
                        if User.objects.filter(username=new_username).exclude(id=student.user.id).exists():
                            raise ValueError(f"Username/Email '{new_username}' already exists")
                        student.user.username = new_username
                        # Update email if it's an email address
                        if '@' in new_username:
                            student.user.email = new_username
                        print(f"Username changed to: {new_username}")  # Debug
                    
                    # Update password if provided
                    new_password = data.get("password", "").strip()
                    if new_password:
                        if len(new_password) < 6:
                            raise ValueError("Password must be at least 6 characters long")
                        student.user.set_password(new_password)
                        print("Password updated")  # Debug
                    
                    # Update name
                    name_parts = student.full_name.split()
                    student.user.first_name = name_parts[0] if name_parts else ''
                    student.user.last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
                    student.user.save()
                    
                    print("User saved successfully")  # Debug
                else:
                    # Create new user account if doesn't exist
                    print("Creating new user account")  # Debug
                    
                    if User.objects.filter(username=new_username).exists():
                        raise ValueError(f"Username/Email '{new_username}' already exists")
                    
                    password = data.get("password", "").strip() or "student123"
                    if len(password) < 6:
                        raise ValueError("Password must be at least 6 characters long")
                    
                    name_parts = student.full_name.split()
                    user = User.objects.create_user(
                        username=new_username,
                        email=new_username if '@' in new_username else '',
                        first_name=name_parts[0] if name_parts else '',
                        last_name=' '.join(name_parts[1:]) if len(name_parts) > 1 else '',
                    )
                    user.set_password(password)
                    user.save()
                    student.user = user
                    student.save()
                    
                    print(f"New user created: {user.username}")  # Debug
            
            # Return JSON for AJAX
            if request.content_type == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                response_data = {
                    'status': 'success',
                    'student': {
                        'id': student.id,
                        'full_name': student.full_name,
                        'roll_number': student.roll_number,
                        'grade': student.grade.name,
                        'section': student.section,
                        'username': student.user.username if student.user else '',
                    }
                }
                print(f"Returning success response: {response_data}")  # Debug
                return JsonResponse(response_data)
            else:
                return redirect("students_list")
                
        except ValueError as e:
            print(f"ValueError in edit_student: {str(e)}")  # Debug
            if request.content_type == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'error': str(e)
                }, status=400)
            else:
                return render(request, "teacher/students/edit_student.html", {
                    "student": student,
                    "grades": Grade.objects.all(),
                    "error": str(e)
                })
        except Exception as e:
            print(f"Exception in edit_student: {str(e)}")  # Debug
            import traceback
            traceback.print_exc()
            
            if request.content_type == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'error': str(e)
                }, status=500)
            else:
                return render(request, "teacher/students/edit_student.html", {
                    "student": student,
                    "grades": Grade.objects.all(),
                    "error": str(e)
                })

    # GET request
    return render(request, "teacher/students/edit_student.html", {
        "student": student,
        "grades": Grade.objects.all(),
    })

@login_required
def delete_student(request, student_id):
    """
    Delete a student and their user account
    """
    if request.method != "POST":
        return JsonResponse({
            'status': 'error',
            'error': 'POST required'
        }, status=405)
    
    try:
        student = get_object_or_404(
            Student, 
            id=student_id, 
            created_by=request.user
        )
        
        # Delete associated user account
        if student.user:
            student.user.delete()  # This will cascade delete the student
        else:
            student.delete()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Student deleted successfully'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=400)


@login_required
def add_questions_to_test(request, test_id):
    """
    AJAX endpoint to add questions to a test from the question library
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    
    try:
        data = json.loads(request.body)
        question_ids = data.get("question_ids", [])
        
        if not question_ids:
            return JsonResponse({"error": "No questions selected"}, status=400)
        
        # Get the current max order
        max_order = TestQuestion.objects.filter(test=test).aggregate(
            models.Max('order')
        )['order__max'] or 0
        
        # Add questions to test
        for idx, question_id in enumerate(question_ids):
            question = get_object_or_404(Question, id=question_id)
            
            # Check if already added
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
        
@login_required
def inline_add_question(request, test_id):
    """
    Add question inline to test with validation
    """
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    
    # Prevent editing published tests with submissions
    if test.is_published and StudentAnswer.objects.filter(test=test).exists():
        return JsonResponse({
            "error": "Cannot modify published test with submissions"
        }, status=403)

    try:
        data = json.loads(request.body)

        # Get topic to derive grade and subject
        topic_id = data.get("topic")
        topic = None
        if topic_id:
            topic = get_object_or_404(Topic, id=topic_id)
        
        # Create Question
        question = Question.objects.create(
            question_text=data["question_text"],
            answer_text=data.get("answer_text", ""),
            marks=data.get("marks", 1),
            question_type=data.get("question_type", "theory"),
            year=data.get("year"),
            grade=topic.grade if topic else None,
            subject=topic.subject if topic else None,
            topic=topic,
            created_by=request.user,
        )

        # Compute order safely
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

        # Return HTML snippet
        html = render_to_string(
            "teacher/partials/test_question_card.html",
            {
                "tq": tq,
                "question": question,
            },
            request=request
        )

        return JsonResponse({
            "status": "ok",
            "html": html,
            "question_id": question.id,
            "order": tq.order,
        })
        
    except Exception as e:
        print(f"Error adding question: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)

from django.utils import timezone
from datetime import timedelta

@login_required
def student_test_list(request):
    """
    List of all tests available to the student
    """
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return render(request, 'student/no_profile.html')
    
    # Get all published tests assigned to this student
    tests = Test.objects.filter(
        is_published=True
    ).filter(
        models.Q(assigned_students=student) | 
        models.Q(assigned_groups__students=student)
    ).exclude(
        excluded_students=student
    ).distinct().order_by('-created_at')
    
    return render(request, 'student/test_list.html', {
        'student': student,
        'tests': tests,
    })

@login_required
def student_take_test(request, test_id):
    """
    Student takes a test
    """
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return render(request, 'student/no_profile.html')
    
    test = get_object_or_404(Test, id=test_id, is_published=True)
    
    # Check if student is assigned this test
    is_assigned = test.assigned_students.filter(id=student.id).exists() or \
                  test.assigned_groups.filter(students=student).exists()
    
    is_excluded = test.excluded_students.filter(id=student.id).exists()
    
    if not is_assigned or is_excluded:
        return render(request, 'student/test_not_available.html')
    
    # Get test questions
    test_questions = TestQuestion.objects.filter(
        test=test
    ).select_related('question').order_by('order')
    
    # Get student's previous answers if any
    student_answers = {}
    for tq in test_questions:
        try:
            answer = StudentAnswer.objects.get(
                student=student,
                test=test,
                question=tq.question
            )
            student_answers[tq.question.id] = answer.answer_text
        except StudentAnswer.DoesNotExist:
            student_answers[tq.question.id] = ''
    
    if request.method == 'POST':
        # Save answers
        for tq in test_questions:
            answer_text = request.POST.get(f'question_{tq.question.id}', '')
            
            StudentAnswer.objects.update_or_create(
                student=student,
                test=test,
                question=tq.question,
                defaults={
                    'answer_text': answer_text,
                }
            )
        
        return redirect('student_test_submitted', test_id=test.id)
    
    return render(request, 'student/take_test.html', {
        'student': student,
        'test': test,
        'test_questions': test_questions,
        'student_answers': student_answers,
    })

@login_required
def student_test_submitted(request, test_id):
    """
    Confirmation page after test submission
    """
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return render(request, 'student/no_profile.html')
    
    test = get_object_or_404(Test, id=test_id)
    
    return render(request, 'student/test_submitted.html', {
        'student': student,
        'test': test,
    })

@login_required
def student_test_attempt(request, test_id):
    """
    Main test-taking interface for students
    """
    # Get student
    try:
        student = request.user.student_profile
    except (Student.DoesNotExist, AttributeError):
        return redirect('student_test_list')
    
    # Get test
    test = get_object_or_404(Test, id=test_id, is_published=True)
    
    # Verify student has access
    has_access = (
        test.assigned_students.filter(id=student.id).exists() or
        test.assigned_groups.filter(students=student).exists()
    ) and not test.excluded_students.filter(id=student.id).exists()
    
    if not has_access:
        return redirect('student_test_list')
    
    # Check if test is available
    now = timezone.now()
    if test.start_time and now < test.start_time:
        return redirect('student_test_list')
    
    if test.start_time and test.duration_minutes:
        end_time = test.start_time + timedelta(minutes=test.duration_minutes)
        if now > end_time:
            return redirect('student_test_list')
    
    # Get or create attempt
    attempt, created = StudentTestAttempt.objects.get_or_create(
        student=student,
        test=test
    )
    
    # Check if already submitted
    if attempt.is_submitted:
        return redirect('student_test_review', test_id=test.id)
    
    # Calculate time remaining
    if test.duration_minutes and test.start_time:
        end_time = test.start_time + timedelta(minutes=test.duration_minutes)
        time_remaining_seconds = int((end_time - now).total_seconds())
        if time_remaining_seconds < 0:
            time_remaining_seconds = 0
    else:
        time_remaining_seconds = test.duration_minutes * 60 if test.duration_minutes else 3600
    
    # Get questions with saved answers
    test_questions = TestQuestion.objects.filter(test=test).select_related(
        'question', 'question__topic'
    ).order_by('order')
    
    # Attach saved answers to each question
    for tq in test_questions:
        try:
            saved = StudentAnswer.objects.get(
                student=student,
                test=test,
                question=tq.question
            )
            tq.saved_answer = saved.answer_text
        except StudentAnswer.DoesNotExist:
            tq.saved_answer = ''
    
    total_marks = sum(tq.question.marks for tq in test_questions)
    
    # Format time remaining
    hours = time_remaining_seconds // 3600
    minutes = (time_remaining_seconds % 3600) // 60
    seconds = time_remaining_seconds % 60
    time_remaining = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    return render(request, "student/test_attempt.html", {
        "test": test,
        "attempt": attempt,
        "test_questions": test_questions,
        "total_marks": total_marks,
        "time_remaining": time_remaining,
        "time_remaining_seconds": time_remaining_seconds,
    })

@login_required
def student_save_answer(request, test_id):
    """
    AJAX endpoint to save individual answers during test
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    
    try:
        student = request.user.student_profile
    except (Student.DoesNotExist, AttributeError):
        return JsonResponse({"error": "Student not found"}, status=403)
    
    test = get_object_or_404(Test, id=test_id)
    
    data = json.loads(request.body)
    question_id = data.get('question_id')
    answer_text = data.get('answer_text', '')
    
    question = get_object_or_404(Question, id=question_id)
    
    # Save or update answer
    answer, created = StudentAnswer.objects.update_or_create(
        student=student,
        test=test,
        question=question,
        defaults={'answer_text': answer_text}
    )
    
    return JsonResponse({"status": "ok", "saved_at": answer.submitted_at})

@login_required
def student_submit_test(request, test_id):
    """
    Submit the test and mark attempt as complete
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    
    try:
        student = request.user.student_profile
    except (Student.DoesNotExist, AttributeError):
        return JsonResponse({"error": "Student not found"}, status=403)
    
    test = get_object_or_404(Test, id=test_id)
    
    try:
        attempt = StudentTestAttempt.objects.get(student=student, test=test)
        attempt.is_submitted = True
        attempt.submitted_at = timezone.now()
        attempt.save()
        
        return JsonResponse({
            "status": "ok",
            "redirect": f"/student/tests/{test.id}/review/"
        })
    except StudentTestAttempt.DoesNotExist:
        return JsonResponse({"error": "Attempt not found"}, status=404)

@login_required
def student_test_review(request, test_id):
    """
    Show submitted test with answers (results view)
    """
    try:
        student = request.user.student_profile
    except (Student.DoesNotExist, AttributeError):
        return redirect('student_test_list')
    
    test = get_object_or_404(Test, id=test_id)
    attempt = get_object_or_404(StudentTestAttempt, student=student, test=test)
    
    # Get all answers
    answers = StudentAnswer.objects.filter(
        student=student,
        test=test
    ).select_related('question')
    
    test_questions = TestQuestion.objects.filter(test=test).select_related(
        'question'
    ).order_by('order')
    
    # Attach answers to questions
    answer_dict = {a.question_id: a for a in answers}
    for tq in test_questions:
        tq.student_answer = answer_dict.get(tq.question.id)
    
    return render(request, "student/test_review.html", {
        "test": test,
        "attempt": attempt,
        "test_questions": test_questions,
    })


@login_required
def student_results(request):
    """
    View student's test results
    """
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return render(request, 'student/no_profile.html')
    
    # Get tests with results
    results = []
    answered_tests = StudentAnswer.objects.filter(
        student=student,
        marks_awarded__isnull=False
    ).values_list('test_id', flat=True).distinct()
    
    for test_id in answered_tests:
        test = Test.objects.get(id=test_id)
        answers = StudentAnswer.objects.filter(
            student=student,
            test=test,
            marks_awarded__isnull=False
        )
        
        total_marks = sum(a.marks_awarded for a in answers if a.marks_awarded)
        max_marks = sum(a.question.marks for a in answers)
        
        results.append({
            'test': test,
            'total_marks': total_marks,
            'max_marks': max_marks,
            'percentage': (total_marks / max_marks * 100) if max_marks > 0 else 0,
        })
    
    return render(request, 'student/results.html', {
        'student': student,
        'results': results,
    })