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

    # User Management (NEW - Simplified)
    path("teacher/users/add/", views.add_user, name="add_user"),
    path("teacher/users/manage/", views.manage_users, name="manage_users"),
    path("teacher/users/change-password/", views.change_password, name="change_password"),

    # Tests (teacher)
    path("teacher/tests/", views.tests_list, name="tests_list"),
    path("teacher/tests/create/", views.create_test, name="create_test"),
    path("teacher/tests/<int:test_id>/edit/", views.test_editor, name="edit_test"),
    path("teacher/tests/<int:test_id>/delete/", views.delete_test, name="delete_test"),
    path("teacher/tests/<int:test_id>/toggle/", views.toggle_publish, name="toggle_publish"),
    path("teacher/tests/<int:test_id>/duplicate/", views.duplicate_test, name="duplicate_test"),
    path("teacher/tests/<int:test_id>/autosave/", views.autosave_test, name="autosave_test"),
    path("teacher/tests/<int:test_id>/add-questions/", views.add_questions_to_test, name="add_questions_to_test"),
    path("teacher/tests/<int:test_id>/questions/<int:test_question_id>/remove/", 
         views.remove_question_from_test, name="remove_question_from_test"),
    path("teacher/tests/<int:test_id>/inline-add-question/",
         views.inline_add_question, name="inline_add_question"),
    
    # Tests (student)
    path("student/tests/", views.student_tests_list, name="student_tests_list"),

    # Questions
    path("questions/", views.question_library, name="question_library"),
    path("questions/add/", views.add_edit_question, name="add_question"),
    path("questions/edit/<int:question_id>/", views.add_edit_question, name="edit_question"),

    # AJAX
    path("ajax/topics/", views.ajax_topics, name="ajax_topics"),
    path("ajax/los/", views.ajax_learning_objectives, name="ajax_los"),
    
    # Students (Legacy - keep for compatibility)
    path("teacher/students/", views.students_list, name="students_list"),
    path("teacher/students/add/", views.add_student, name="add_student"),
    path("teacher/students/<int:student_id>/edit/", views.edit_student, name="edit_student"),
    
    # Groups
    path("teacher/groups/", views.groups_list, name="groups_list"),
    path("teacher/groups/add/", views.add_group, name="add_group"),
    #path("teacher/groups/<int:group_id>/edit/", views.edit_group, name="edit_group"),
    #path("teacher/groups/<int:group_id>/delete/", views.delete_group, name="delete_group"),
    
    # Performance
    path("teacher/performance/class/", views.class_performance, name="class_performance"),
    path("teacher/users/add/", views.add_user, name="add_user"),
    path("teacher/groups/", views.groups_list, name="groups_list"),
    path("teacher/class-groups/", views.manage_class_groups, name="manage_class_groups"),
    path("teacher/class-groups/<int:group_id>/students/", views.get_group_students, name="get_group_students"),     
    path("teacher/users/manage/", views.manage_users, name="manage_users"),
    
    
    path("teacher/groups/", views.groups_list, name="groups_list"),
]