from django.urls import path
from . import views

urlpatterns = [
    # Public & Auth
    path('', views.home, name='home'),
    path('register/', views.patient_register, name='patient_register'),
    path('login/', views.patient_login, name='patient_login'),
    path('logout/', views.user_logout, name='user_logout'),
    path('change-password/', views.patient_change_password, name='patient_change_password'),
    path('forgot-password/', views.patient_forgot_password, name='patient_forgot_password'),
    
    # Patient Dashboard & Actions
    path('dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('profile/', views.patient_profile, name='patient_profile'),
    path('book/', views.patient_book_appointment, name='patient_book_appointment'),
    path('history/', views.patient_appointment_history, name='patient_appointment_history'),
    path('appointment/<int:appointment_id>/', views.patient_appointment_detail, name='patient_appointment_detail'),
    path('doctors/', views.patient_doctors, name='patient_doctors'),
    path('cancel-appointment/<int:appointment_id>/', views.patient_cancel_appointment, name='patient_cancel_appointment'),
    path('reschedule/<int:appointment_id>/', views.patient_reschedule_appointment, name='patient_reschedule_appointment'),
    
    # Admin Panel
    path('admin-panel/login/', views.admin_login, name='admin_login'),
    path('admin-panel/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/departments/', views.admin_manage_departments, name='admin_manage_departments'),
    path('admin-panel/departments/edit/<int:dept_id>/', views.admin_edit_department, name='admin_edit_department'),
    path('admin-panel/departments/delete/<int:dept_id>/', views.admin_delete_department, name='admin_delete_department'),
    path('admin-panel/doctors/', views.admin_manage_doctors, name='admin_manage_doctors'),
    path('admin-panel/doctors/edit/<int:doctor_id>/', views.admin_edit_doctor, name='admin_edit_doctor'),
    path('admin-panel/doctors/delete/<int:doctor_id>/', views.admin_delete_doctor, name='admin_delete_doctor'),
    path('admin-panel/patients/', views.admin_manage_patients, name='admin_manage_patients'),
    path('admin-panel/patients/<int:patient_id>/', views.admin_patient_detail, name='admin_patient_detail'),
    path('admin-panel/appointments/', views.admin_manage_appointments, name='admin_manage_appointments'),
    path('admin-panel/appointments/update-status/<int:appointment_id>/<str:status>/', views.admin_update_appointment_status, name='admin_update_appointment_status'),
    path('admin-panel/appointments/<int:appointment_id>/update/', views.admin_update_appointment, name='admin_update_appointment'),
    path('admin-panel/reports/', views.admin_reports, name='admin_reports'),
    path('admin-panel/reports/export/', views.admin_reports_export, name='admin_reports_export'),
    
    # AJAX Dynamic Fetch API
    path('ajax/get-doctors-by-department/', views.get_doctors_by_department, name='ajax_get_doctors_by_department'),
]
