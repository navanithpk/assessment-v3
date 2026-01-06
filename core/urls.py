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
    # Tests
    path("teacher/tests/", views.tests_list, name="tests_list"),
    path("teacher/tests/create/", views.test_editor, name="create_test"),
    path("teacher/tests/<int:test_id>/edit/", views.test_editor, name="edit_test"),
    path("teacher/tests/<int:test_id>/delete/", views.delete_test, name="delete_test"),
    path("teacher/tests/<int:test_id>/toggle/", views.toggle_publish, name="toggle_publish"),
    path("teacher/tests/<int:test_id>/duplicate/", views.duplicate_test, name="duplicate_test"),
    path("teacher/tests/<int:test_id>/autosave/", views.autosave_test, name="autosave_test"),

    # Questions
    path("questions/", views.question_library, name="question_library"),
    path("questions/add/", views.add_edit_question, name="add_question"),
    path("questions/edit/<int:question_id>/", views.add_edit_question, name="edit_question"),

    # AJAX
    path("ajax/topics/", views.ajax_topics, name="ajax_topics"),
    path("ajax/los/", views.ajax_learning_objectives, name="ajax_los"),
    path("ajax/questions/", views.ajax_questions, name="ajax_questions"),

]
