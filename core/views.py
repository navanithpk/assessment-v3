from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def teacher_dashboard(request):
    return render(request, "teacher/teacher_dashboard.html")
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def student_dashboard(request):
    return render(request, "student/student_dashboard.html")


from .models import (
    LearningObjective,
    Question,
    Grade,
    Subject,
    Topic,
)
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

from django.shortcuts import redirect

def root_redirect(request):
    if request.user.is_authenticated:
        return redirect("teacher_dashboard")  # ✅ CHANGE HERE
    return redirect("login")


@login_required
def tests_list(request):
    tests = Test.objects.filter(created_by=request.user)

    return render(
        request,
        "teacher/tests_list.html",
        {"tests": tests}
    )


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
    questions = Question.objects.filter(
        created_by=request.user
    ).select_related("grade", "subject", "topic")

    return render(
        request,
        "teacher/question_library.html",
        {"questions": questions}
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

        if not question:
            question = Question.objects.create(
                grade_id=data["grade"],
                subject_id=data["subject"],
                topic_id=data["topic"],
                question_text=data["question_text"],
                answer_text=data.get("answer_text", ""),
                marks=data["marks"],
                question_type=data["question_type"],
                created_by=request.user,
            )
        else:
            question.grade_id = data["grade"]
            question.subject_id = data["subject"]
            question.topic_id = data["topic"]
            question.question_text = data["question_text"]
            question.answer_text = data.get("answer_text", "")
            question.marks = data["marks"]
            question.question_type = data["question_type"]
            question.save()

        question.learning_objectives.set(
            data.getlist("los")
        )

        return redirect("question_library")

    return render(
        request,
        "teacher/question_editor.html",
        {
            "question": question,
            "grades": grades,
            "subjects": subjects,
            "topics": topics,
            "selected_lo_ids": selected_lo_ids,  # ✅ FIX
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

    for q in test.questions.all():
        TestQuestion.objects.create(
            test=new_test,
            question_text=q.question_text,
            answer_text=q.answer_text,
            marks=q.marks,
            order=q.order,
        )

    return redirect("tests_list")


@login_required
def test_editor(request, test_id=None):
    test = None

    if test_id:
        test = get_object_or_404(Test, id=test_id, created_by=request.user)

    if request.method == "POST":
        title = request.POST["title"]
        duration = request.POST.get("duration") or None
        start_time = request.POST.get("start_time") or None

        if not test:
            test = Test.objects.create(
                title=title,
                created_by=request.user,
                duration_minutes=duration,
                start_time=start_time
            )
        else:
            test.title = title
            test.duration_minutes = duration
            test.start_time = start_time
            test.save()

        return redirect("edit_test", test_id=test.id)

    questions = test.questions.order_by("order") if test else []

    return render(
        request,
        "teacher/test_editor.html",
        {
            "test": test,
            "questions": questions,
        }
    )
    

from django.contrib.auth import authenticate, login
from django.contrib.auth.models import Group
@login_required
def create_test(request):
    """
    Create new test.
    Uses the unified test_editor.html page.
    """
    return render(
        request,
        "teacher/test_editor.html",
        {
            "test": None,   # important: template expects this safely
        }
    )

@login_required
def edit_test(request, test_id):
    """
    Edit existing test.
    Uses the same test_editor.html page.
    """
    # Placeholder: actual Test fetching will come later
    test = {
        "id": test_id,
        "name": "Sample Test",
    }

    return render(
        request,
        "teacher/test_editor.html",
        {
            "test": test,
        }
    )


from django.shortcuts import redirect
from django.contrib.auth import authenticate, login

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

            # ✅ FORCE landing pages by role
            if role == "teacher":
                return redirect("teacher_dashboard")
            elif role == "student":
                return redirect("student_dashboard")
            elif role == "admin":
                return redirect("/admin/")

    return render(request, "registration/login.html", {"error": error})

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Test, TestQuestion, Question
