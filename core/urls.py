from django.urls import path
from .views import (
    # Existing imports
    root_redirect,
    custom_login,
    teacher_dashboard,
    student_dashboard,  # Add this
    admin_dashboard,
    tests_list,
    create_test,
    edit_test,
    test_editor,
    toggle_publish,
    delete_test,
    duplicate_test,
    question_library,
    add_edit_question,
    ajax_topics,
    ajax_learning_objectives,
    ajax_questions,
    list_learning_objectives,
    import_questions_review,
    add_student,
    students_list,
    edit_student,
    add_group,
    groups_list,
    class_performance,
    student_performance,
    remove_question_from_test,
    reorder_test_questions,
    add_questions_to_test,
    inline_add_question,
    autosave_test,
    # Student views - Add these
    student_test_list,
    student_test_attempt,
    student_save_answer,
    student_submit_test,
    student_test_review,
    student_results,
)

urlpatterns = [
    # Root and auth
    path("", root_redirect, name="root"),
    path("login/", custom_login, name="login"),
    
    # Teacher dashboard
    path("teacher/", teacher_dashboard, name="teacher_dashboard"),
    
    # Admin
    path("admin-panel/", admin_dashboard, name="admin_dashboard"),
    
    # Tests
    path("teacher/tests/", tests_list, name="tests_list"),
    path("teacher/tests/create/", create_test, name="create_test"),
    path("teacher/tests/<int:test_id>/edit/", edit_test, name="edit_test"),
    path("teacher/tests/<int:test_id>/", test_editor, name="test_editor"),
    path("teacher/tests/<int:test_id>/toggle-publish/", toggle_publish, name="toggle_publish"),
    path("teacher/tests/<int:test_id>/delete/", delete_test, name="delete_test"),
    path("teacher/tests/<int:test_id>/duplicate/", duplicate_test, name="duplicate_test"),
    path("teacher/tests/<int:test_id>/autosave/", autosave_test, name="autosave_test"),
    
    # Test questions
    path("teacher/tests/<int:test_id>/questions/<int:test_question_id>/remove/", 
         remove_question_from_test, name="remove_question_from_test"),
    path("teacher/tests/<int:test_id>/questions/reorder/", 
         reorder_test_questions, name="reorder_test_questions"),
    path("teacher/tests/<int:test_id>/questions/add/", 
         add_questions_to_test, name="add_questions_to_test"),
    path("teacher/tests/<int:test_id>/questions/inline-add/", 
         inline_add_question, name="inline_add_question"),
    
    # Question library
    path("teacher/questions/", question_library, name="question_library"),
    path("teacher/questions/add/", add_edit_question, name="add_question"),
    path("teacher/questions/<int:question_id>/edit/", add_edit_question, name="edit_question"),
    path("teacher/questions/import/", import_questions_review, name="import_questions"),
    
    # Learning objectives
    path("admin-panel/learning-objectives/", list_learning_objectives, name="list_learning_objectives"),
    
    # Students
    path("teacher/students/", students_list, name="students_list"),
    path("teacher/students/add/", add_student, name="add_student"),
    path("teacher/students/<int:student_id>/edit/", edit_student, name="edit_student"),
    
    # Groups
    path("teacher/groups/", groups_list, name="groups_list"),
    path("teacher/groups/add/", add_group, name="add_group"),
    
    # Performance
    path("teacher/performance/class/", class_performance, name="class_performance"),
    path("teacher/performance/student/<int:student_id>/", student_performance, name="student_performance"),
    
    # AJAX endpoints
    path("ajax/topics/", ajax_topics, name="ajax_topics"),
    path("ajax/learning-objectives/", ajax_learning_objectives, name="ajax_learning_objectives"),
    path("ajax/questions/", ajax_questions, name="ajax_questions"),
    
    # Student URLs - Add these
    path('student/', student_dashboard, name='student_dashboard'),
    path('student/tests/', student_test_list, name='student_test_list'),
    path('student/tests/<int:test_id>/', student_test_attempt, name='student_test_attempt'),
    path('student/tests/<int:test_id>/save-answer/', student_save_answer, name='student_save_answer'),
    path('student/tests/<int:test_id>/submit/', student_submit_test, name='student_submit_test'),
    path('student/tests/<int:test_id>/review/', student_test_review, name='student_test_review'),
    path('student/results/', student_results, name='student_results'),
]