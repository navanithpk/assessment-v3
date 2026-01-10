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
    path("teacher/tests/create/", views.redirect_to_descriptive_create, name="create_test"),
    path("teacher/tests/<int:test_id>/edit/", views.redirect_to_descriptive_edit, name="edit_test"),
    path("teacher/tests/<int:test_id>/delete/", views.delete_test, name="delete_test"),
    path("teacher/tests/<int:test_id>/toggle/", views.toggle_publish, name="toggle_publish"),
    path("teacher/tests/<int:test_id>/duplicate/", views.duplicate_test, name="duplicate_test"),
    path("teacher/tests/<int:test_id>/autosave/", views.autosave_test, name="autosave_test"),
    # Old question-related URLs removed
    
    # Tests (student)
    path("student/tests/", views.student_tests_list, name="student_tests_list"),

    # Question library removed - using hierarchical tests only

    # AJAX
    path("ajax/grades/", views.ajax_grades, name="ajax_grades"),
    path("ajax/subjects/", views.ajax_subjects, name="ajax_subjects"),
    path("ajax/topics/", views.ajax_topics, name="ajax_topics"),
    path("ajax/los/", views.ajax_learning_objectives, name="ajax_los"),
    path("ajax/students/", views.ajax_students, name="ajax_students"),
    path("ajax/groups/", views.ajax_groups, name="ajax_groups"),
    
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
    path("teacher/tests/create-descriptive/", views.create_descriptive_test, name="create_descriptive_test"),
    path("teacher/tests/<int:test_id>/edit-descriptive/", views.edit_descriptive_test, name="edit_descriptive_test"),
    
    # Student Test Taking
    path("student/tests/<int:test_id>/take/", views.take_test, name="take_test"),
    path("student/tests/<int:test_id>/autosave/", views.autosave_test_answers, name="autosave_test_answers"),
    path("student/tests/<int:test_id>/answers/", views.get_saved_answers, name="get_saved_answers"),
    path("student/tests/<int:test_id>/submit/", views.submit_test, name="submit_test"),

    # Test Assignment API
    path("teacher/tests/<int:test_id>/students-groups/", views.get_students_and_groups, name="get_students_and_groups"),
    path("teacher/tests/<int:test_id>/save-assignments/", views.save_test_assignments, name="save_test_assignments"),
]