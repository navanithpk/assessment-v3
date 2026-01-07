from django.urls import path
from . import views

urlpatterns = [
    # Root
    path("", views.root_redirect, name="root"),
    path("admin/dashboard/", views.admin_dashboard, name="admin_dashboard"),

    # Auth
    path("accounts/login/", views.custom_login, name="login"),

    # Dashboards
    path("teacher/", views.teacher_dashboard, name="teacher_dashboard"),
    path("student/dashboard/", views.student_dashboard, name="student_dashboard"),

    # Tests (teacher)
    path("teacher/tests/", views.tests_list, name="tests_list"),
    path("teacher/tests/create/", views.create_test, name="create_test"),
    path("teacher/tests/<int:test_id>/edit/", views.test_editor, name="edit_test"),
    path("teacher/tests/<int:test_id>/delete/", views.delete_test, name="delete_test"),
    path("teacher/tests/<int:test_id>/toggle/", views.toggle_publish, name="toggle_publish"),
    path("teacher/tests/<int:test_id>/duplicate/", views.duplicate_test, name="duplicate_test"),
    path("teacher/tests/<int:test_id>/autosave/", views.autosave_test, name="autosave_test"),
    path("teacher/tests/<int:test_id>/add-questions/", views.add_questions_to_test, name="add_questions_to_test"),
    
    path(
        "teacher/import-questions/",
        views.import_questions_review,
        name="import_questions_review"
    ),

    # Questions
    path("questions/", views.question_library, name="question_library"),
    path("questions/add/", views.add_edit_question, name="add_question"),
    path("questions/edit/<int:question_id>/", views.add_edit_question, name="edit_question"),

    # AJAX
    path("ajax/topics/", views.ajax_topics, name="ajax_topics"),
    path("ajax/los/", views.ajax_learning_objectives, name="ajax_los"),
    path("ajax/questions/", views.ajax_questions, name="ajax_questions"),
    
    # Students
    path("teacher/students/", views.students_list, name="students_list"),
    path("teacher/students/add/", views.add_student, name="add_student"),
    path("teacher/students/<int:student_id>/edit/", views.edit_student, name="edit_student"),

    # Groups
    path("teacher/groups/", views.groups_list, name="groups_list"),
    path("teacher/groups/add/", views.add_group, name="add_group"),

    # Performance
    path("teacher/performance/class/", views.class_performance, name="class_performance"),
    path("teacher/performance/student/<int:student_id>/", views.student_performance, name="student_performance"),
]