from django.urls import path
from . import views

urlpatterns = [
    # Universal AI Assistant Gateway API Endpoints
    path('api/assistant/message', views.api_assistant_message, name='api_assistant_message'),
    path('api/assistant/voice', views.api_assistant_voice, name='api_assistant_voice'),
    path('api/assistant/confirm', views.api_assistant_confirm, name='api_assistant_confirm'),
    path('api/assistant/session-reset', views.api_assistant_session_reset, name='api_assistant_session_reset'),

    # Backward-compatible routes
    path('api/voice/process/', views.process_voice_query, name='api_voice_process'),
    path('api/voice/session-reset/', views.api_voice_reset_session, name='api_voice_reset_session'),
    path('api/ai/symptom-guidance/', views.api_ai_symptom_guidance, name='api_ai_symptom_guidance'),
    path('api/ai/scan-medicine/', views.api_ai_scan_medicine, name='api_ai_scan_medicine'),
    path('api/ai/explain-lab-report/', views.api_ai_explain_lab_report, name='api_ai_explain_lab_report'),
    path('api/ai/explain-prescription/', views.api_ai_explain_prescription, name='api_ai_explain_prescription'),
    path('api/ai/explain-health-trends/', views.api_ai_explain_health_trends, name='api_ai_explain_health_trends'),
    path('api/ai/ask-report/', views.api_ai_ask_report, name='api_ai_ask_report'),
]
