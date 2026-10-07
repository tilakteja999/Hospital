from django.urls import path
from . import views
from . import admin_views
from . import doctor_views
from . import hospital_views
from . import emergency_views

urlpatterns = [
    path('', views.role_portal_view, name='role_portal'),
    path('login/patient/', views.patient_login_view, name='patient_login'),
    path('login/doctor/', views.doctor_login_view, name='doctor_login'),
    path('login/hospital/', views.hospital_login_view, name='hospital_login'),
    path('login/admin/', views.admin_login_view, name='admin_login'),
    path('register/', views.register_view, name='register'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dedicated Portals
    path('admin-portal/', admin_views.admin_portal_view, name='admin_portal'),
    path('hospital-portal/', hospital_views.hospital_portal_view, name='hospital_portal'),
    path('doctor-portal/', doctor_views.doctor_portal_view, name='doctor_portal'),

    # Emergency SOS & Ambulance APIs
    path('api/patient/sos/', emergency_views.api_patient_sos_create, name='api_patient_sos_create'),
    path('api/patient/sos/<int:request_id>/status/', emergency_views.api_patient_sos_status, name='api_patient_sos_status'),
    path('api/patient/sos/<int:request_id>/cancel/', emergency_views.api_patient_sos_cancel, name='api_patient_sos_cancel'),
    path('api/patient/appointments/completed/', emergency_views.api_patient_completed_appointments, name='api_patient_completed_appointments'),
    path('api/hospital/emergency/<int:request_id>/action/', emergency_views.api_hospital_emergency_action, name='api_hospital_emergency_action'),
    path('api/hospital/ambulances/', emergency_views.api_hospital_ambulance_manage, name='api_hospital_ambulance_manage'),
    path('api/patient/feedback/submit/', emergency_views.api_patient_feedback_create, name='api_patient_feedback_submit'),

    # Patient Feedback & Complaints APIs
    path('api/patient/feedback/create/', emergency_views.api_patient_feedback_create, name='api_patient_feedback_create'),
    path('api/hospital/feedback/<int:feedback_id>/action/', emergency_views.api_hospital_feedback_action, name='api_hospital_feedback_action'),

    # Hospital Performance Scorecard API
    path('api/hospital/<int:hospital_id>/scorecard/', emergency_views.api_hospital_scorecard, name='api_hospital_scorecard'),

    # Targeted Broadcasts & Disease Analytics APIs
    path('api/admin/broadcasts/create/', emergency_views.api_admin_broadcast_create, name='api_admin_broadcast_create'),
    path('api/admin/disease-analytics/', emergency_views.api_admin_disease_analytics, name='api_admin_disease_analytics'),

    # Hospital Admin APIs
    path('api/hospital/appointments/', hospital_views.api_hospital_appointments_list, name='api_hospital_appointments_list'),
    path('api/hospital/appointments/<int:booking_id>/action/', hospital_views.api_hospital_appointment_action, name='api_hospital_appointment_action'),
    path('api/hospital/doctors/add/', hospital_views.api_hospital_add_doctor, name='api_hospital_add_doctor'),
    path('api/hospital/doctors/<int:doctor_id>/update/', hospital_views.api_hospital_update_doctor, name='api_hospital_update_doctor'),
    path('api/hospital/resources/update/', hospital_views.api_hospital_update_resources, name='api_hospital_update_resources'),
    path('api/hospital/reports/export/', hospital_views.api_hospital_export_reports, name='api_hospital_export_reports'),

    # Admin APIs (Hospital, Doctor Verification, Multi-Hospital Analytics, Queue, Audit, Advisories & Schemes)
    path('api/admin/hospitals/add/', admin_views.api_admin_add_hospital, name='api_admin_add_hospital'),
    path('api/admin/hospitals/<int:hospital_id>/update/', admin_views.api_admin_update_hospital, name='api_admin_update_hospital'),
    path('api/admin/doctors/verify/', admin_views.api_admin_verify_doctor, name='api_admin_verify_doctor'),
    path('api/admin/multi-hospital-analytics/', admin_views.api_admin_multi_hospital_analytics, name='api_admin_multi_hospital_analytics'),

    path('api/admin/doctors/add/', admin_views.api_add_doctor, name='api_admin_add_doctor'),
    path('api/admin/doctors/<int:doctor_id>/update/', admin_views.api_update_doctor, name='api_admin_update_doctor'),
    path('api/admin/doctors/<int:doctor_id>/status/', admin_views.api_set_doctor_status, name='api_admin_set_doctor_status'),
    path('api/admin/doctors/<int:doctor_id>/remove/', admin_views.api_remove_doctor, name='api_admin_remove_doctor'),
    path('api/admin/doctors/<int:doctor_id>/toggle-presence/', admin_views.api_toggle_doctor_presence, name='api_admin_toggle_doctor_presence'),
    path('api/admin/audit-logs/', admin_views.api_admin_audit_logs, name='api_admin_audit_logs'),
    path('api/admin/advisories/', admin_views.api_admin_health_advisories, name='api_admin_advisories'),
    path('api/admin/health-advisories/', admin_views.api_admin_health_advisories, name='api_admin_health_advisories'),
    path('api/admin/health-advisories/add/', admin_views.api_admin_health_advisories, name='api_admin_health_advisories_add'),
    path('api/admin/health-advisories/<int:advisory_id>/toggle/', admin_views.api_admin_toggle_advisory, name='api_admin_toggle_advisory'),
    path('api/admin/schemes/', admin_views.api_admin_health_schemes, name='api_admin_schemes'),
    path('api/admin/health-schemes/', admin_views.api_admin_health_schemes, name='api_admin_health_schemes'),
    path('api/admin/health-schemes/add/', admin_views.api_admin_health_schemes, name='api_admin_health_schemes_add'),
    path('api/admin/health-schemes/<int:scheme_id>/toggle/', admin_views.api_admin_toggle_scheme, name='api_admin_toggle_scheme'),
    path('api/admin/stats/', admin_views.api_admin_stats, name='api_admin_stats'),

    # Doctor APIs (Clinical Consultation, OPD Queue, Lab Orders, Discharge, Consent, Vaccinations)
    path('api/doctor/appointments/<int:booking_id>/action/', doctor_views.api_doctor_opd_action, name='api_doctor_opd_action'),
    path('api/doctor/appointments/<int:booking_id>/complete/', doctor_views.api_mark_appointment_completed, name='api_doctor_mark_completed'),
    path('api/doctor/duty/toggle/<int:doctor_id>/', doctor_views.api_doctor_toggle_duty, name='api_doctor_toggle_duty'),
    path('api/doctor/lab-orders/add/', doctor_views.api_doctor_order_lab_test, name='api_doctor_order_lab_test'),
    path('api/doctor/lab-orders/<int:order_id>/update/', doctor_views.api_doctor_update_lab_result, name='api_doctor_update_lab_result'),
    path('api/doctor/discharge-summary/create/', doctor_views.api_doctor_create_discharge_summary, name='api_doctor_create_discharge_summary'),
    path('api/doctor/consent/request/', doctor_views.api_doctor_request_consent, name='api_doctor_request_consent'),
    path('api/doctor/vaccinations/add/', doctor_views.api_doctor_add_vaccination, name='api_doctor_add_vaccination'),

    # User & Aadhaar APIs
    path('api/aadhaar/generate-otp/', views.generate_aadhaar_otp_api, name='api_aadhaar_generate_otp'),
    path('api/aadhaar/verify-otp/', views.verify_aadhaar_otp_api, name='api_aadhaar_verify_otp'),
    path('api/profile/update/', views.update_profile_api, name='api_profile_update'),
]



