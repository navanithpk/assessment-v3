from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.admin.views.decorators import staff_member_required
import json
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


@login_required
def autosave_test(request, test_id):
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    data = json.loads(request.body)

    test.title = data.get("title", test.title)
    test.is_published = data.get("published", test.is_published)
    test.save()

    return JsonResponse({"status": "ok"})


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
    return render(request, "teacher/teacher_dashboard.html")


@login_required
def student_dashboard(request):
    return render(request, "student/student_dashboard.html")


def root_redirect(request):
    if request.user.is_authenticated:
        return redirect("teacher_dashboard")
    return redirect("login")


@login_required
def tests_list(request):
    tests = Test.objects.filter(created_by=request.user).order_by("-id")

    return render(
        request,
        "teacher/tests_list.html",
        {"tests": tests}
    )


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
                return redirect("teacher_dashboard")
            elif role == "student":
                return redirect("student_dashboard")
            elif role == "admin":
                return redirect("/admin/")

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
    test = get_object_or_404(Test, id=test_id, created_by=request.user)

    if request.method == "POST":
        # basic test save
        test.title = request.POST.get("title", test.title)
        test.start_time = request.POST.get("start_time") or None
        test.duration_minutes = request.POST.get("duration_minutes") or None
        test.is_published = bool(request.POST.get("is_published"))
        test.save()

        # assignments
        test.assigned_students.set(request.POST.getlist("assigned_students"))
        test.assigned_groups.set(request.POST.getlist("assigned_groups"))
        test.excluded_students.set(request.POST.getlist("excluded_students"))
        
        return redirect("tests_list")

    # Get test questions with proper ordering
    test_questions = TestQuestion.objects.filter(test=test).select_related(
        'question', 'question__topic', 'question__grade', 'question__subject'
    ).order_by('order')

    return render(
        request,
        "teacher/create_test.html",
        {
            "test": test,
            "test_questions": test_questions,
            "groups": ClassGroup.objects.filter(created_by=request.user),
            "students": Student.objects.filter(created_by=request.user),
            "grades": Grade.objects.all(),
            "subjects": Subject.objects.all(),
        }
    )


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
    Remove a specific question from a test
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
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


@login_required
def add_student(request):
    if request.method == "POST":
        Student.objects.create(
            full_name=request.POST["full_name"],
            roll_number=request.POST.get("roll_number", ""),
            admission_id=request.POST.get("admission_id", ""),
            grade_id=request.POST["grade"],
            section=request.POST["section"],
            created_by=request.user
        )
        return redirect("students_list")

    return render(request, "teacher/students/add_student.html", {
        "grades": Grade.objects.all()
    })


@login_required
def students_list(request):
    students = Student.objects.filter(created_by=request.user)

    return render(request, "teacher/students/students_list.html", {
        "students": students,
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
def edit_student(request, student_id):
    student = get_object_or_404(Student, id=student_id, created_by=request.user)

    if request.method == "POST":
        student.full_name = request.POST.get("full_name")
        student.roll_number = request.POST.get("roll_number", "")
        student.admission_id = request.POST.get("admission_id", "")
        student.grade_id = request.POST.get("grade")
        student.section = request.POST.get("section")
        student.save()
        return redirect("students_list")

    return render(
        request,
        "teacher/students/edit_student.html",
        {
            "student": student,
            "grades": Grade.objects.all(),
        }
    )


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
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    test = get_object_or_404(Test, id=test_id, created_by=request.user)

    data = json.loads(request.body)

    # 1️⃣ Create Question
    question = Question.objects.create(
        question_text=data["question_text"],
        answer_text=data.get("answer_text", ""),
        marks=data.get("marks", 1),
        question_type=data.get("question_type", "theory"),
        year=data.get("year"),
        grade=test.grade if hasattr(test, "grade") else None,
        subject=test.subject if hasattr(test, "subject") else None,
        topic_id=data.get("topic"),
        created_by=request.user,
    )

    # 2️⃣ Compute order safely
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

    # 3️⃣ Return HTML snippet
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
