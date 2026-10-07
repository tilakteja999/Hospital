from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # OPD Live Queue Status
    path('api/patient/opd-status/', views.api_patient_opd_status, name='api_patient_opd_status'),

    # Vitals APIs
    path('api/vitals/', views.get_vitals_api, name='api_get_vitals'),
    path('api/vitals/add/', views.add_vital_api, name='api_add_vital'),

    # Records APIs
    path('api/records/', views.get_records_api, name='api_get_records'),
    path('api/records/<int:record_id>/', views.get_record_detail_api, name='api_get_record_detail'),
    path('api/records/<int:record_id>/sync-vitals/', views.sync_record_vitals_api, name='api_sync_record_vitals'),
    path('api/records/add/', views.add_record_api, name='api_add_record'),

    # Prescriptions & Medication Adherence APIs
    path('api/prescriptions/', views.get_prescriptions_api, name='api_get_prescriptions'),
    path('api/prescriptions/<int:prescription_id>/toggle-dose/', views.api_toggle_dose_taken, name='api_toggle_dose_taken'),

    # Lab Reports APIs
    path('api/lab-reports/', views.api_patient_lab_reports, name='api_patient_lab_reports'),

    # Digital Discharge Summary & Public Verification
    path('api/discharge-summary/<int:summary_id>/', views.api_patient_discharge_summary, name='api_patient_discharge_summary'),
    path('verify-discharge/<str:ref_code>/', views.verify_discharge_summary, name='verify_discharge_summary'),

    # Emergency Information & Emergency Card
    path('emergency-card/<str:patient_identifier>/', views.view_emergency_card, name='view_emergency_card'),
    path('api/emergency-profile/update/', views.api_update_emergency_profile, name='api_update_emergency_profile'),

    # Patient Consent & Privacy APIs
    path('api/consent/<int:consent_id>/action/', views.api_patient_consent_action, name='api_patient_consent_action'),

    # Vaccination APIs
    path('api/vaccinations/', views.api_patient_vaccinations, name='api_patient_vaccinations'),

    # Notifications APIs
    path('api/notifications/', views.get_notifications_api, name='api_get_notifications'),
    path('api/notifications/<int:note_id>/read/', views.mark_notification_read_api, name='api_mark_notification_read'),

    # Physiotherapy Videos APIs
    path('api/physiotherapy-videos/', views.api_get_physiotherapy_videos, name='api_get_physiotherapy_videos'),

    # Radiology & Diagnostic Imaging APIs
    path('api/radiology-reports/', views.api_get_radiology_reports, name='api_get_radiology_reports'),
    path('api/radiology/<int:report_id>/', views.api_get_radiology_report_detail, name='api_get_radiology_report_detail'),
    path('api/radiology/<int:report_id>/imaging/', views.api_stream_radiology_imaging, name='api_stream_radiology_imaging'),
    path('api/radiology/<int:report_id>/dicom/', views.api_stream_dicom_file, name='api_stream_dicom_file'),

    # Language Preference API
    path('api/user/language/', views.api_update_language_preference, name='api_update_language_preference'),
]

