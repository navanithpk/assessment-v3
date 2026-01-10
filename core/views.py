from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.template.loader import render_to_string
from django.db import models
from django.db.models import Q
from django.utils import timezone
import json

from .models import (
    Grade,
    Subject,
    Topic,
    LearningObjective,
    Test,
    Student,
    ClassGroup,
    StudentAnswer,
    StudentTestAttempt,
    School,
    UserProfile,
)


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
# Replace your create_user_account view with this fixed version
from django.db import transaction

def enforce_staff_flag(user):
    if hasattr(user, "profile"):
        user.is_staff = user.profile.role in ("teacher", "school_admin")
        user.save(update_fields=["is_staff"])

@transaction.atomic
def create_user_with_role(
    *,
    email,
    password,
    full_name,
    role,
    school,
    created_by,
    grade=None,
    division=None,
    subject=None,
):
    email = email.lower().strip()

    # Create auth user
    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=full_name.split()[0],
        last_name=" ".join(full_name.split()[1:]),
    )

    # 🔒 STAFF RULE (HARD)
    user.is_staff = role in ("teacher", "school_admin")
    user.save()

    # Create profile (ALWAYS)
    profile = UserProfile.objects.create(
        user=user,
        role=role,
        school=school,
        grade=int(grade) if role == "student" and grade else None,
        division=division if role == "student" else None,
        subject=subject if role == "teacher" else None,
    )

    # Create Student record ONLY for students
    if role == "student":
        grade_obj = Grade.objects.get(name=str(grade))
        Student.objects.create(
            user=user,
            full_name=full_name,
            grade=grade_obj,
            section=division,
            school=school,
            created_by=created_by,
        )

    return user

@login_required
def create_user_account(request):
    school = get_user_school(request.user)

    # 🔁 Pull confirmation from session (if any)
    created_user = request.session.pop("created_user", None)
    created_password = request.session.pop("created_password", None)

    if request.method == 'POST':
        role = request.POST.get('role', 'student')

        email = request.POST.get('username', '').strip().lower()
        password = request.POST.get('password', '').strip()
        full_name = request.POST.get('name', '').strip()

        if not email or not password or not full_name:
            messages.error(request, 'All fields are required')
            return redirect('create_user_account')

        if User.objects.filter(username=email).exists():
            messages.error(request, f'Account with {email} already exists')
            return redirect('create_user_account')

        if role == 'teacher' and request.user.profile.role != 'school_admin':
            messages.error(request, 'Only school admins can create teacher accounts')
            return redirect('create_user_account')

        try:
            create_user_with_role(
                email=email,
                password=password,
                full_name=full_name,
                role=role,
                school=school,
                created_by=request.user,
                grade=request.POST.get('grade'),
                division=request.POST.get('division'),
                subject=request.POST.get('subject'),
            )

            # ✅ STORE confirmation in session
            request.session["created_user"] = email
            request.session["created_password"] = password

            return redirect('create_user_account')

        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
            return redirect('create_user_account')

    return render(request, 'teacher/create_user_account.html', {
        'school': school,
        'is_school_admin': request.user.profile.role == 'school_admin',
        'created_user': created_user,
        'created_password': created_password,
    })


# Add these views to your views.py

from django.db import transaction
from django.contrib.auth.models import User
from core.models import UserProfile, Student, Grade, Subject, School

def get_user_school(user):
    """Helper function to get user's school"""
    try:
        return user.profile.school
    except:
        return None

def get_user_role(user):
    """Helper function to get user's role"""
    if user.is_superuser:
        return 'superuser'
    try:
        return user.profile.role
    except:
        return 'student' if not user.is_staff else 'teacher'


@login_required
def add_user(request):
    """
    Add new teacher or student account
    - School admins can create teachers and students
    - Teachers can only create students
    """
    school = get_user_school(request.user)
    role = get_user_role(request.user)
    is_school_admin = (role == 'school_admin')
    
    if not school:
        messages.error(request, "You are not assigned to a school.")
        return redirect("teacher_dashboard")
    
    if request.method == "POST":
        new_user_role = request.POST.get("role", "student")
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "").strip()
        
        # Validation
        if not full_name or not email or not password:
            messages.error(request, "All required fields must be filled.")
            return redirect("add_user")
        
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect("add_user")
        
        # Permission check: Only school admin can create teachers
        if new_user_role == 'teacher' and not is_school_admin:
            messages.error(request, "Only school administrators can create teacher accounts.")
            return redirect("add_user")
        
        # Check if user already exists
        if User.objects.filter(username=email).exists():
            messages.error(request, f"An account with email {email} already exists.")
            return redirect("add_user")
        
        try:
            with transaction.atomic():
                # Split name
                name_parts = full_name.split()
                first_name = name_parts[0] if name_parts else ""
                last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                
                # Create User
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    is_staff=(new_user_role in ['teacher', 'school_admin'])
                )
                
                # Create UserProfile
                profile = UserProfile.objects.create(
                    user=user,
                    role=new_user_role,
                    school=school
                )
                
                # Handle role-specific data
                if new_user_role == 'teacher':
                    # Teacher-specific
                    subject = request.POST.get("subject", "")
                    if subject:
                        profile.subject = subject
                        profile.save()
                    
                    messages.success(
                        request,
                        f'✓ Teacher account created successfully!\n'
                        f'Username: {email}\n'
                        f'Password: {password}'
                    )
                
                elif new_user_role == 'student':
                    # Student-specific
                    grade_name = request.POST.get("grade", "")
                    division = request.POST.get("division", "").strip()
                    roll_number = request.POST.get("roll_number", "").strip()
                    admission_id = request.POST.get("admission_id", "").strip()
                    
                    if not grade_name or not division:
                        raise ValueError("Grade and section are required for students")
                    
                    # Update profile
                    profile.grade = int(grade_name) if grade_name.isdigit() else None
                    profile.division = division
                    profile.save()
                    
                    # Create Student record
                    grade_obj = Grade.objects.get(name=grade_name)
                    Student.objects.create(
                        user=user,
                        full_name=full_name,
                        roll_number=roll_number,
                        admission_id=admission_id,
                        grade=grade_obj,
                        section=division,
                        school=school,
                        created_by=request.user
                    )
                    
                    messages.success(
                        request,
                        f'✓ Student account created successfully!\n'
                        f'Username: {email}\n'
                        f'Password: {password}'
                    )
                
                return redirect("manage_users")
        
        except Grade.DoesNotExist:
            messages.error(request, "Selected grade does not exist.")
        except Exception as e:
            messages.error(request, f"Error creating account: {str(e)}")
        
        return redirect("add_user")
    
    # GET request
    context = {
        'school': school,
        'is_school_admin': is_school_admin,
        'grades': Grade.objects.all(),
        'subjects': Subject.objects.all()
    }
    
    return render(request, "teacher/add_new_teacher_student.html", context)


@login_required
def manage_users(request):
    """
    View and manage all teachers and students
    - Show all users from the same school
    - Allow password changes based on permissions
    """
    school = get_user_school(request.user)
    role = get_user_role(request.user)
    is_school_admin = (role == 'school_admin')
    
    if not school:
        messages.error(request, "You are not assigned to a school.")
        return redirect("teacher_dashboard")
    
    # Get all user profiles from same school
    teachers = UserProfile.objects.filter(
        school=school,
        role__in=['teacher', 'school_admin']
    ).select_related('user').order_by('user__first_name', 'user__last_name')
    
    # Get student records
    students = Student.objects.filter(
        school=school
    ).select_related('grade', 'user').order_by('grade__name', 'section', 'roll_number')
    
    # Combine into unified list
    all_users = []
    
    for teacher in teachers:
        all_users.append({
            'user_id': teacher.user.id,
            'name': f"{teacher.user.first_name} {teacher.user.last_name}".strip() or teacher.user.username,
            'username': teacher.user.username,
            'email': teacher.user.email,
            'role': teacher.role,
            'role_display': teacher.get_role_display(),
            'joined': teacher.created_at,
            'additional_info': None,
            'student_id': None
        })
    
    for student in students:
        all_users.append({
            'user_id': student.user.id if student.user else None,
            'name': student.full_name,
            'username': student.user.username if student.user else 'No account',
            'email': student.user.email if student.user else '',
            'role': 'student',
            'role_display': 'Student',
            'joined': student.created_at,
            'additional_info': {
                'grade': student.grade.name,
                'section': student.section,
                'roll_number': student.roll_number,
                'admission_id': student.admission_id
            },
            'student_id': student.id
        })
    
    # Sort by name
    all_users.sort(key=lambda x: x['name'].lower())
    
    context = {
        'school': school,
        'all_users': all_users,
        'is_school_admin': is_school_admin,
        'role': role,
        'total_users': len(all_users),
        'total_teachers': teachers.count(),
        'total_students': students.count()
    }
    
    return render(request, "teacher/manage_teacher_student.html", context)


@login_required
def change_password(request):
    """
    Change password for users
    - School admin can change teacher and student passwords
    - Teacher can only change student passwords
    """
    if request.method != "POST":
        return redirect("manage_users")
    
    school = get_user_school(request.user)
    role = get_user_role(request.user)
    is_school_admin = (role == 'school_admin')
    
    user_id = request.POST.get("user_id")
    new_password = request.POST.get("new_password", "").strip()
    
    if not user_id or not new_password:
        messages.error(request, "User ID and password are required.")
        return redirect("manage_users")
    
    if len(new_password) < 8:
        messages.error(request, "Password must be at least 8 characters long.")
        return redirect("manage_users")
    
    try:
        user = User.objects.get(id=user_id)
        
        # Get the target user's role
        try:
            target_role = user.profile.role
        except:
            # Check if it's a student
            try:
                student = user.student_profile
                target_role = 'student'
            except:
                messages.error(request, "User profile not found.")
                return redirect("manage_users")
        
        # Permission check
        if target_role in ['teacher', 'school_admin'] and not is_school_admin:
            messages.error(request, "Only school administrators can change teacher passwords.")
            return redirect("manage_users")
        
        # Verify user belongs to same school
        try:
            user_profile = user.profile
            if user_profile.school != school:
                messages.error(request, "You can only change passwords for users in your school.")
                return redirect("manage_users")
        except:
            # Check student
            try:
                student = user.student_profile
                if student.school != school:
                    messages.error(request, "You can only change passwords for users in your school.")
                    return redirect("manage_users")
            except:
                messages.error(request, "User not found in your school.")
                return redirect("manage_users")
        
        # Change password
        user.set_password(new_password)
        user.save()
        
        messages.success(request, f"✓ Password changed successfully for {user.username}")
    
    except User.DoesNotExist:
        messages.error(request, "User not found.")
    except Exception as e:
        messages.error(request, f"Error changing password: {str(e)}")
    
    return redirect("manage_users")

# ===================== SCHOOL USERS LIST =====================
# Add this to your views.py
@login_required
def manage_students(request):
    """
    View and manage all students in the school
    """
    school = get_user_school(request.user)
    
    if not school:
        messages.error(request, "You are not assigned to a school.")
        return redirect("teacher_dashboard")
    
    # Get all students from the same school
    students = Student.objects.filter(
        school=school
    ).select_related('grade', 'school', 'created_by', 'user').order_by('grade', 'section', 'roll_number')
    
    # Get all grades for the edit modal dropdown
    grades = Grade.objects.all()
    
    context = {
        'students': students,
        'grades': grades,
        'school': school,
        'role': get_user_role(request.user)
    }
    
    return render(request, 'teacher/manage_students.html', context)



# You'll also need to add this URL pattern to urls.py:
# path("teacher/students/manage/", views.manage_students, name="manage_students"),


@login_required
def school_users_list(request):
    """
    View all teachers and students in the same school
    """
    school = get_user_school(request.user)
    role = get_user_role(request.user)
    
    if not school:
        messages.error(request, "You are not assigned to a school.")
        return redirect("teacher_dashboard")
    
    # Get all users from same school
    teachers = UserProfile.objects.filter(
        school=school,
        role__in=['teacher', 'school_admin']
    ).select_related('user')
    
    students_profiles = UserProfile.objects.filter(
        school=school,
        role='student'
    ).select_related('user')
    print(">>> SCHOOL USERS LIST VIEW HIT <<<")
    # Get student details
    students = Student.objects.filter(school=school).select_related('grade')
    
    context = {
        'school': school,
        'teachers': teachers,
        'students': students,
        'role': role
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
def redirect_to_descriptive_create(request):
    """Redirect old create_test URL to new hierarchical test creation"""
    return redirect("create_descriptive_test")


@login_required
def redirect_to_descriptive_edit(request, test_id):
    """Redirect old edit_test URL to new hierarchical test editor"""
    return redirect("edit_descriptive_test", test_id=test_id)




@login_required
def toggle_publish(request, test_id):
    test = get_object_or_404(Test, id=test_id, created_by=request.user)

    # If publishing, check if at least one student or group is assigned
    if not test.is_published:
        has_students = test.assigned_students.exists()
        has_groups = test.assigned_groups.exists()

        if not has_students and not has_groups:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
               request.content_type == 'application/json':
                return JsonResponse({
                    'success': False,
                    'error': 'Cannot publish test. Please assign at least one student or class group first.'
                }, status=400)
            messages.error(request, 'Cannot publish test. Please assign at least one student or class group first.')
            return redirect("edit_descriptive_test", test_id=test.id)
    else:
        # If unpublishing, check if any students have started the test
        has_attempts = StudentTestAttempt.objects.filter(test=test).exists()
        if has_attempts:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
               request.content_type == 'application/json':
                return JsonResponse({
                    'success': False,
                    'error': 'Cannot unpublish test. At least one student has already started this test.'
                }, status=400)
            messages.error(request, 'Cannot unpublish test. At least one student has already started this test.')
            return redirect("edit_descriptive_test", test_id=test.id)

    test.is_published = not test.is_published
    test.save()

    # Return JSON for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
       request.content_type == 'application/json':
        return JsonResponse({
            'success': True,
            'is_published': test.is_published,
            'message': f"Test {'published' if test.is_published else 'unpublished'} successfully!"
        })

    messages.success(request, f"Test {'published' if test.is_published else 'unpublished'} successfully!")
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




# ===================== QUESTIONS =====================

@login_required
# Question library removed - using hierarchical tests only


# Old question views removed - using hierarchical tests only
# add_edit_question, inline_add_question, remove_question_from_test, add_questions_to_test removed


# ===================== STUDENTS =====================

# Replace your add_student view in views.py with this

@login_required
def add_student(request):
    school = get_user_school(request.user)
    
    if request.method == "POST":
        from django.db import transaction
        
        try:
            with transaction.atomic():
                full_name = request.POST["full_name"]
                roll_number = request.POST.get("roll_number", "")
                admission_id = request.POST.get("admission_id", "")
                grade_id = request.POST["grade"]
                section = request.POST["section"]
                
                # Get the Grade object
                grade = Grade.objects.get(id=grade_id)
                
                # Create student record
                student = Student.objects.create(
                    full_name=full_name,
                    roll_number=roll_number,
                    admission_id=admission_id,
                    grade=grade,
                    section=section,
                    school=school,
                    created_by=request.user
                )
                
                # Generate username
                base_username = admission_id if admission_id else \
                               full_name.lower().replace(' ', '_')
                username = base_username
                counter = 1
                
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{counter}"
                    counter += 1
                
                # Create user account
                user = User.objects.create_user(
                    username=username,
                    first_name=full_name.split()[0] if full_name else '',
                    last_name=' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else '',
                    password='student123'  # Default password
                )
                
                # Create UserProfile with student role
                profile, created = UserProfile.objects.get_or_create(user=user)
                profile.role = 'student'
                profile.school = school
                profile.grade = int(grade.name) if grade.name.isdigit() else None
                profile.division = section
                profile.save()
                
                # Link user to student
                student.user = user
                student.save()
                
                messages.success(
                    request, 
                    f'Student "{full_name}" added successfully! Username: {username}, Password: student123'
                )
                
        except Exception as e:
            messages.error(request, f'Error creating student: {str(e)}')
            
        return redirect("students_list")

    return render(request, "teacher/students/add_student.html", {
        "grades": Grade.objects.all(),
        "school": school
    })
@login_required
def students_list(request):
    school = get_user_school(request.user)
    students = Student.objects.filter(school=school)

    return render(request, "teacher/students/students_list.html", {
        "students": students,
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
        return redirect("students_list")

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
@require_GET
def ajax_grades(request):
    grades = Grade.objects.all().order_by("name")
    return JsonResponse([
        {"id": g.id, "name": g.name}
        for g in grades
    ], safe=False)


@login_required
@require_GET
def ajax_subjects(request):
    subjects = Subject.objects.all().order_by("name")
    return JsonResponse([
        {"id": s.id, "name": s.name}
        for s in subjects
    ], safe=False)


@login_required
@require_GET
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

    return JsonResponse(topics, safe=False)


@login_required
@require_GET
def ajax_learning_objectives(request):
    topic_id = request.GET.get("topic_id")

    if not topic_id:
        return JsonResponse([], safe=False)

    los = LearningObjective.objects.filter(
        topic_id=topic_id
    ).order_by("code")

    return JsonResponse([
        {
            "id": lo.id,
            "code": lo.code,
            "description": lo.description,
        }
        for lo in los
    ], safe=False)


@login_required
@require_GET
def ajax_students(request):
    """Get all students for the teacher's school"""
    school = get_user_school(request.user)
    if not school:
        return JsonResponse([], safe=False)

    students = Student.objects.filter(school=school).select_related('user')

    return JsonResponse([
        {
            "id": s.id,
            "name": s.user.get_full_name() or s.user.username,
            "email": s.user.email,
        }
        for s in students
    ], safe=False)


@login_required
@require_GET
def ajax_groups(request):
    """Get all class groups for the teacher's school"""
    school = get_user_school(request.user)
    if not school:
        return JsonResponse([], safe=False)

    groups = ClassGroup.objects.filter(school=school)

    return JsonResponse([
        {
            "id": g.id,
            "name": g.name,
            "student_count": g.students.count(),
        }
        for g in groups
    ], safe=False)


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

# Add these views to your views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q

@login_required
def manage_class_groups(request):
    """
    Main page for managing class groups (all teachers can access)
    """
    school = get_user_school(request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if action == 'create':
            # Create new group
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            color = request.POST.get('color', '#3b82f6')
            grade_id = request.POST.get('grade')
            student_ids = request.POST.getlist('students')
            
            if not name:
                if is_ajax:
                    return JsonResponse({'error': 'Group name is required'}, status=400)
                messages.error(request, 'Group name is required')
                return redirect('manage_class_groups')
            
            try:
                group = ClassGroup.objects.create(
                    name=name,
                    school=school,
                    created_by=request.user,
                    grade_id=grade_id if grade_id else None,
                )
                
                # Add color if the field exists
                if hasattr(group, 'color'):
                    group.color = color
                    group.save()
                
                # Add description if the field exists
                if hasattr(group, 'description'):
                    group.description = description
                    group.save()
                
                # Add students
                if student_ids:
                    students = User.objects.filter(
                        id__in=student_ids,
                        profile__school=school,
                        profile__role='student'
                    )
                    group.students.set(students)
                
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': f'Group "{name}" created successfully',
                        'group_id': group.id
                    })
                
                messages.success(request, f'Group "{name}" created successfully with {len(student_ids)} students')
                return redirect('manage_class_groups')
                
            except Exception as e:
                if is_ajax:
                    return JsonResponse({'error': str(e)}, status=500)
                messages.error(request, f'Error creating group: {str(e)}')
                return redirect('manage_class_groups')
        
        elif action == 'edit':
            # Edit existing group
            group_id = request.POST.get('group_id')
            
            if not group_id:
                if is_ajax:
                    return JsonResponse({'error': 'Group ID is required'}, status=400)
                messages.error(request, 'Group ID is required')
                return redirect('manage_class_groups')
            
            try:
                group = get_object_or_404(ClassGroup, id=group_id, school=school)
                
                group.name = request.POST.get('name', group.name)
                grade_id = request.POST.get('grade')
                group.grade_id = grade_id if grade_id else None
                
                # Update optional fields if they exist
                if hasattr(group, 'description'):
                    group.description = request.POST.get('description', '')
                
                if hasattr(group, 'color'):
                    group.color = request.POST.get('color', group.color if hasattr(group, 'color') else '#3b82f6')
                
                group.save()
                
                # Update students
                student_ids = request.POST.getlist('students')
                if student_ids:
                    students = User.objects.filter(
                        id__in=student_ids,
                        profile__school=school,
                        profile__role='student'
                    )
                    group.students.set(students)
                else:
                    group.students.clear()
                
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': f'Group "{group.name}" updated successfully'
                    })
                
                messages.success(request, f'Group "{group.name}" updated successfully')
                return redirect('manage_class_groups')
                
            except Exception as e:
                if is_ajax:
                    return JsonResponse({'error': str(e)}, status=500)
                messages.error(request, f'Error updating group: {str(e)}')
                return redirect('manage_class_groups')
        
        elif action == 'delete':
            # Delete group
            group_id = request.POST.get('group_id')
            
            try:
                group = get_object_or_404(ClassGroup, id=group_id, school=school)
                group_name = group.name
                group.delete()
                
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': f'Group "{group_name}" deleted successfully'
                    })
                
                messages.success(request, f'Group "{group_name}" deleted successfully')
                return redirect('manage_class_groups')
                
            except Exception as e:
                if is_ajax:
                    return JsonResponse({'error': str(e)}, status=500)
                messages.error(request, f'Error deleting group: {str(e)}')
                return redirect('manage_class_groups')
    
    # GET request - display groups
    groups = ClassGroup.objects.filter(
        school=school
    ).prefetch_related('students').order_by('name')
    
    # Get all students in the school
    students = User.objects.filter(
        profile__school=school,
        profile__role='student'
    ).select_related('profile').order_by('profile__grade', 'profile__division', 'first_name')
    
    grades = Grade.objects.all()
    
    return render(request, 'teacher/manage_class_groups.html', {
        'groups': groups,
        'students': students,
        'grades': grades,
        'school': school
    })

@login_required
def get_group_students(request, group_id):
    """
    API endpoint to get students in a specific group
    """
    school = get_user_school(request.user)
    group = get_object_or_404(ClassGroup, id=group_id, school=school)
    
    student_ids = list(group.students.values_list('id', flat=True))
    
    return JsonResponse({
        'student_ids': student_ids,
        'count': len(student_ids)
    })

# Add these new views to your views.py

import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST

# ===================== DESCRIPTIVE TESTS (TEACHER) =====================

@login_required
def create_descriptive_test(request):
    """
    Create a new descriptive test with hierarchical questions
    """
    school = get_user_school(request.user)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            title = data.get('title', '').strip()
            questions_data = data.get('questions', [])
            markscheme = data.get('markscheme', '').strip()

            if not title:
                return JsonResponse({'error': 'Title is required'}, status=400)

            if not questions_data:
                return JsonResponse({'error': 'At least one question is required'}, status=400)

            # Create the test
            test = Test.objects.create(
                title=title,
                created_by=request.user,
                is_published=False,
                test_type='descriptive'
            )

            # Store the hierarchical structure and markscheme
            test.descriptive_structure = json.dumps(questions_data)
            if markscheme:
                test.markscheme = markscheme

            # Set start time and duration
            start_time = data.get('start_time')
            if start_time:
                from django.utils.dateparse import parse_datetime
                test.start_time = parse_datetime(start_time)

            duration_minutes = data.get('duration_minutes')
            if duration_minutes:
                test.duration_minutes = duration_minutes

            test.save()

            return JsonResponse({
                'success': True,
                'test_id': test.id,
                'message': 'Test created successfully'
            })

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    # GET request - show the editor
    return render(request, 'teacher/create_descriptive_test_v3.html', {
        'school': school
    })


@login_required
def edit_descriptive_test(request, test_id):
    """
    Edit an existing descriptive test
    """
    school = get_user_school(request.user)
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            test.title = data.get('title', test.title)
            test.descriptive_structure = json.dumps(data.get('questions', []))

            markscheme = data.get('markscheme', '').strip()
            if markscheme:
                test.markscheme = markscheme

            # Update start time and duration
            start_time = data.get('start_time')
            if start_time:
                from django.utils.dateparse import parse_datetime
                test.start_time = parse_datetime(start_time)
            else:
                test.start_time = None

            duration_minutes = data.get('duration_minutes')
            if duration_minutes:
                test.duration_minutes = duration_minutes
            else:
                test.duration_minutes = None

            test.save()

            return JsonResponse({
                'success': True,
                'message': 'Test updated successfully'
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    # GET request - show editor with existing data
    questions_data = []
    if hasattr(test, 'descriptive_structure') and test.descriptive_structure:
        try:
            questions_data = json.loads(test.descriptive_structure)
        except:
            questions_data = []

    return render(request, 'teacher/create_descriptive_test_v3.html', {
        'school': school,
        'test': test,
        'questions_data': json.dumps(questions_data),
        'markscheme': test.markscheme or ''
    })


# ===================== STUDENT TEST TAKING =====================


# CRITICAL FIX: Update these specific views in your views.py file

@login_required
def test_editor(request, test_id):
    """
    Test editor with proper student assignment handling
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
        else:
            test.start_time = None
            
        duration = request.POST.get("duration_minutes")
        if duration:
            test.duration_minutes = int(duration)
        else:
            test.duration_minutes = None
        
        # Handle subject
        subject_id = request.POST.get("subject")
        if subject_id:
            test.subject_id = subject_id
        else:
            test.subject = None
            
        test.save()

        # Handle student assignments - CRITICAL FIX
        # Get individual student IDs from the hidden inputs
        assigned_student_ids = request.POST.getlist("assigned_students")
        
        # Clear existing assignments and set new ones
        test.assigned_students.clear()
        test.assigned_groups.clear()
        
        if assigned_student_ids:
            # Validate that these students belong to the teacher's school
            valid_students = Student.objects.filter(
                id__in=assigned_student_ids,
                school=school
            )
            test.assigned_students.set(valid_students)
        
        messages.success(request, "Test saved successfully!")
        return redirect("edit_test", test_id=test.id)

    # GET request - load test data
    test_questions = TestQuestion.objects.filter(
        test=test
    ).select_related('question', 'question__topic', 'question__grade', 'question__subject').order_by('order')
    
    # Get students and groups from same school
    students = Student.objects.filter(school=school).select_related('grade', 'user').order_by('grade__name', 'section', 'roll_number')
    groups = ClassGroup.objects.filter(school=school, created_by=request.user).prefetch_related('students')
    
    # Get currently assigned students
    assigned_students = test.assigned_students.all()
    
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
            "grades": Grade.objects.all(),
            "subjects": subjects,
            "school": school,
        }
    )


@login_required
def student_tests_list(request):
    """
    Show all published tests assigned to the logged-in student
    CRITICAL FIX: Changed from created_by to user lookup
    """
    # Get student profile - FIXED
    try:
        student = Student.objects.get(user=request.user)  # ✅ FIXED: was created_by=request.user
    except Student.DoesNotExist:
        return render(request, "student/student_tests_list.html", {
            "tests_with_status": [],
            "error": "Student profile not found. Please contact your teacher.",
            "student": None,
        })
    
    # Get sorting parameters
    sort_by = request.GET.get('sort', 'date')
    order = request.GET.get('order', 'desc')
    subject_filter = request.GET.get('subject', '')
    
    # Get tests assigned directly to this student
    directly_assigned = Test.objects.filter(
        assigned_students=student,
        is_published=True
    )
    
    # Get tests assigned through groups (if using group-based assignment)
    # Note: Since we're now using individual student assignment, this may not be needed
    # but keeping it for backward compatibility
    student_groups = ClassGroup.objects.filter(students__student_profile=student)
    group_assigned = Test.objects.filter(
        assigned_groups__in=student_groups,
        is_published=True
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


@login_required
def take_test(request, test_id):
    """
    Student interface for taking a hierarchical test
    """
    # Get student profile
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found")
        return redirect("student_dashboard")

    test = get_object_or_404(Test, id=test_id, is_published=True)

    # Check if student is assigned to this test
    is_directly_assigned = test.assigned_students.filter(id=student.id).exists()

    # Check group assignment
    student_groups = ClassGroup.objects.filter(students__student_profile=student)
    is_group_assigned = test.assigned_groups.filter(id__in=student_groups).exists()

    if not (is_directly_assigned or is_group_assigned):
        messages.error(request, "You are not assigned to this test")
        return redirect("student_tests_list")

    # Parse the hierarchical test structure
    if test.descriptive_structure:
        test_structure = json.loads(test.descriptive_structure)
    else:
        test_structure = []

    # Convert to paginated format
    test_data = convert_to_pages(test_structure)

    return render(request, 'student/student_take_test.html', {
        'test': test,
        'test_data': json.dumps(test_data),
        'student': student
    })


# Additional helper function for debugging
@login_required
def debug_student_assignments(request, test_id):
    """
    DEBUG VIEW - Remove in production
    Shows assignment details for troubleshooting
    """
    if not request.user.is_staff:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    test = get_object_or_404(Test, id=test_id)
    
    assigned_students = test.assigned_students.all().values('id', 'full_name', 'user__username')
    assigned_groups = test.assigned_groups.all().values('id', 'name')
    
    return JsonResponse({
        'test': {
            'id': test.id,
            'title': test.title,
            'is_published': test.is_published,
        },
        'assigned_students': list(assigned_students),
        'assigned_groups': list(assigned_groups),
        'total_assigned': test.assigned_students.count(),
    })

def convert_to_pages(questions_structure):
    """
    Convert hierarchical question structure to paginated format for student view
    Each main question becomes a page
    """
    pages = []
    
    for idx, main_question in enumerate(questions_structure, 1):
        page = {
            'pageNumber': idx,
            'questions': [convert_question_to_display_format(main_question)]
        }
        pages.append(page)
    
    return {'pages': pages}


def convert_question_to_display_format(question, parent_number=''):
    """
    Recursively convert question structure to display format
    """
    result = {
        'number': question.get('number', ''),
        'content': question.get('content', ''),
        'marks': question.get('marks', 1),
        'subQuestions': []
    }
    
    # Add answer field if this is a leaf question (no children)
    if not question.get('children') or len(question.get('children', [])) == 0:
        result['answerId'] = f"q{question.get('id', '')}"
    
    # Process children
    if question.get('children'):
        for child in question['children']:
            sub_q = convert_question_to_display_format(child, result['number'])
            result['subQuestions'].append(sub_q)
    
    return result


def convert_regular_test_to_pages(test):
    """
    Convert regular question-bank test to paginated format
    """
    pages = []
    test_questions = TestQuestion.objects.filter(test=test).select_related('question').order_by('order')
    
    for idx, tq in enumerate(test_questions, 1):
        page = {
            'pageNumber': idx,
            'questions': [{
                'number': str(idx),
                'content': tq.question.question_text,
                'marks': tq.question.marks,
                'answerId': f'q{tq.question.id}',
                'subQuestions': []
            }]
        }
        pages.append(page)
    
    return {'pages': pages}


# save_answer view removed - only using hierarchical tests now


@login_required
@require_POST
def autosave_test_answers(request, test_id):
    """
    Auto-save student answers (for descriptive tests)
    """
    try:
        student = Student.objects.get(user=request.user)
        test = get_object_or_404(Test, id=test_id)

        data = json.loads(request.body)
        answers = data.get('answers', {})

        # Store answers in session or database
        # You can create a StudentTestProgress model for this
        request.session[f'test_{test_id}_answers'] = answers
        
        return JsonResponse({'success': True, 'message': 'Answers saved'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_saved_answers(request, test_id):
    """
    Retrieve saved answers for a test
    """
    try:
        answers = request.session.get(f'test_{test_id}_answers', {})
        return JsonResponse({'answers': answers})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def submit_test(request, test_id):
    """
    Submit completed hierarchical test
    """
    try:
        student = Student.objects.get(user=request.user)
        test = get_object_or_404(Test, id=test_id)

        # Mark test attempt as submitted
        try:
            attempt = StudentTestAttempt.objects.get(student=student, test=test)
            attempt.is_submitted = True
            attempt.submitted_at = timezone.now()
            attempt.save()
        except StudentTestAttempt.DoesNotExist:
            # Create attempt if it doesn't exist
            StudentTestAttempt.objects.create(
                student=student,
                test=test,
                is_submitted=True,
                submitted_at=timezone.now(),
                started_at=timezone.now()
            )

        # Save answers from the request
        data = json.loads(request.body)
        answers = data.get('answers', {})

        for question_id, answer_text in answers.items():
            StudentAnswer.objects.update_or_create(
                student=student,
                test=test,
                question_id=question_id,
                defaults={'answer_text': answer_text}
            )

        # Clear session answers
        if f'test_{test_id}_answers' in request.session:
            del request.session[f'test_{test_id}_answers']

        return JsonResponse({
            'status': 'ok',
            'message': 'Test submitted successfully',
            'redirect': '/student/tests/'
        })

    except Student.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Student not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ===================== TEST ASSIGNMENT API =====================

@login_required
@require_GET
def get_students_and_groups(request, test_id):
    """
    API endpoint to get students and groups for assignment modal
    """
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    school = get_user_school(request.user)

    # Get all students in the school
    students = Student.objects.filter(school=school).select_related('grade', 'user').order_by('grade', 'section', 'roll_number')

    students_data = [{
        'id': s.id,
        'name': s.full_name,
        'grade': str(s.grade),
        'section': s.section,
        'roll_number': s.roll_number,
        'admission_id': s.admission_id
    } for s in students]

    # Get all class groups in the school
    groups = ClassGroup.objects.filter(school=school).select_related('grade', 'subject')

    groups_data = [{
        'id': g.id,
        'name': g.name,
        'grade': str(g.grade) if g.grade else '',
        'section': g.section,
        'subject': str(g.subject) if g.subject else '',
        'student_count': g.students.count()
    } for g in groups]

    # Get currently assigned students and groups
    assigned_students = list(test.assigned_students.values_list('id', flat=True))
    assigned_groups = list(test.assigned_groups.values_list('id', flat=True))

    return JsonResponse({
        'students': students_data,
        'groups': groups_data,
        'assigned_students': assigned_students,
        'assigned_groups': assigned_groups
    })


@login_required
@require_POST
def save_test_assignments(request, test_id):
    """
    API endpoint to save student/group assignments for a test
    """
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    school = get_user_school(request.user)

    try:
        data = json.loads(request.body)
        student_ids = data.get('student_ids', [])
        group_ids = data.get('group_ids', [])

        # Validate that students belong to the school
        valid_students = Student.objects.filter(
            id__in=student_ids,
            school=school
        )

        # Validate that groups belong to the school
        valid_groups = ClassGroup.objects.filter(
            id__in=group_ids,
            school=school
        )

        # Update assignments
        test.assigned_students.set(valid_students)
        test.assigned_groups.set(valid_groups)

        return JsonResponse({
            'success': True,
            'message': 'Assignments saved successfully',
            'assigned_count': valid_students.count() + valid_groups.count()
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)