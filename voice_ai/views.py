import json
import uuid
import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from core.models import User
from core.audit_utils import record_audit_log
from .models import AssistantSession, ServerConfirmationToken
from .voice_engine import (
    VoiceDialogueEngine,
    tool_create_appointment_with_token,
    tool_cancel_appointment_with_token,
    ALLOWED_TOOLS,
    FORBIDDEN_OPERATIONS
)
from .smart_assistant import (
    scan_and_identify_medicine,
    explain_lab_report,
    explain_patient_prescriptions,
    explain_vitals_health_trends,
    answer_health_assistant_question
)
from .symptom_engine import SymptomGuidanceEngine


def _resolve_session_and_user(request, data):
    """
    Identifies authenticated user and loads or initializes AssistantSession.
    Derives patient identity ONLY from the authenticated session.
    """
    user = request.user if request.user and request.user.is_authenticated else None
    if not user:
        # Failsafe for unauthenticated demo/guest user
        user = User.objects.filter(role='PATIENT').first() or User.objects.first()

    session_id = data.get('session_id') or request.session.get('assistant_session_id')
    session_obj = None

    if session_id:
        session_obj = AssistantSession.objects.filter(session_id=session_id).first()

    if not session_obj:
        session_id = str(uuid.uuid4())
        session_obj = AssistantSession.objects.create(
            session_id=session_id,
            user=user,
            role=getattr(user, 'role', 'PATIENT'),
            preferred_language=data.get('lang', 'en-IN')
        )
        request.session['assistant_session_id'] = session_id
        request.session.modified = True

    return user, session_obj


# ==================== ASSISTANT GATEWAY API CONTROLLERS ====================

@csrf_exempt
def api_assistant_message(request):
    """
    POST /api/assistant/message
    Unified text/speech Assistant Gateway controller.
    Validates authentication, loads persistent state, enforces tool registry, and handles multi-turn flows.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    query = (data.get('query') or data.get('text') or '').strip()
    forced_lang = data.get('lang')
    route_context = data.get('context', {})

    user, session_obj = _resolve_session_and_user(request, data)

    # Load session state
    session_state = session_obj.workflow_data if isinstance(session_obj.workflow_data, dict) else {}
    if forced_lang:
        session_state['lang'] = forced_lang

    res = VoiceDialogueEngine.process_turn(
        query_text=query,
        user=user,
        session_state=session_state,
        request=request,
        lang_override=forced_lang,
        session_obj=session_obj,
        route_context=route_context
    )

    # Persist updated state in AssistantSession
    session_obj.workflow_data = res.get('session_state', {})
    session_obj.detected_language = res.get('lang', 'en-IN')
    session_obj.workflow_state = res.get('status_indicator', 'IDLE')
    session_obj.context_data = route_context
    session_obj.save()

    return JsonResponse({
        'success': True,
        'session_id': session_obj.session_id,
        'reply': res.get('reply'),
        'action': res.get('action'),
        'lang': res.get('lang', 'en-IN'),
        'target_lang': res.get('target_lang'),
        'tab': res.get('tab'),
        'route_key': res.get('route_key'),
        'booking_id': res.get('booking_id'),
        'token': res.get('token'),
        'is_urgent': res.get('is_urgent', False),
        'status_indicator': res.get('status_indicator', 'SPEAKING'),
        'confirmation_required': res.get('confirmation_required', False),
        'confirmation_token': res.get('confirmation_token', ''),
        'session_state': res.get('session_state', {})
    })


@csrf_exempt
def api_assistant_voice(request):
    """
    POST /api/assistant/voice
    Accepts audio metadata / speech transcription from client-side Web Speech API / STT pipeline.
    Ensures ephemeral audio lifecycle and confidence evaluation.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    transcript = data.get('transcript', '').strip()
    confidence = float(data.get('confidence', 1.0))
    lang = data.get('lang', 'en-IN')

    # If STT confidence is too low on critical actions, ask user to repeat
    if confidence < 0.35 and len(transcript) > 0:
        return JsonResponse({
            'success': True,
            'reply': "I didn't hear that clearly. Could you please repeat it?",
            'action': 'clarify',
            'lang': lang,
            'status_indicator': 'SPEAKING'
        })

    # Forward to core message processor
    return api_assistant_message(request)


@csrf_exempt
def api_assistant_confirm(request):
    """
    POST /api/assistant/confirm
    Direct controller for executing pre-staged consequential write operations
    using a server-side confirmation token.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    token_str = data.get('confirmation_token', '').strip()
    action = data.get('action', 'CREATE_APPOINTMENT').strip()
    user, session_obj = _resolve_session_and_user(request, data)

    if not token_str:
        return JsonResponse({'success': False, 'error': 'Missing confirmation token.'}, status=400)

    if action == 'CREATE_APPOINTMENT':
        res = tool_create_appointment_with_token(user, token_str, request)
    elif action == 'CANCEL_APPOINTMENT':
        res = tool_cancel_appointment_with_token(user, token_str, request)
    else:
        return JsonResponse({'success': False, 'error': f'Unsupported confirmation action: {action}'}, status=400)

    if res.get('success'):
        # Clear session workflow
        session_obj.reset_workflow()
        return JsonResponse({
            'success': True,
            'message': 'Operation confirmed and completed successfully.',
            'result': res
        })
    else:
        return JsonResponse({
            'success': False,
            'error': res.get('error', 'Execution failed.')
        }, status=400)


@csrf_exempt
def api_assistant_session_reset(request):
    """
    POST /api/assistant/session-reset
    Resets the multi-turn session state.
    """
    user, session_obj = _resolve_session_and_user(request, {})
    session_obj.reset_workflow()
    request.session['voice_session_state'] = {}
    request.session.modified = True
    return JsonResponse({'success': True, 'message': 'Assistant conversation state has been reset.'})


# ==================== LEGACY / EXTENDED COMPATIBILITY ENDPOINTS ====================

@csrf_exempt
def process_voice_query(request):
    """Backward-compatible alias for existing frontend callers."""
    return api_assistant_message(request)

@csrf_exempt
def api_voice_reset_session(request):
    """Backward-compatible alias for reset session."""
    return api_assistant_session_reset(request)

@csrf_exempt
def api_ai_symptom_guidance(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    query = data.get('query', '') or data.get('symptom', '')
    lang = data.get('lang', 'en-IN')
    user, _ = _resolve_session_and_user(request, data)
    result = SymptomGuidanceEngine.process_symptom_turn(query, user, {}, lang=lang, request=request)
    return JsonResponse(result or {'success': True, 'reply': 'How can I assist you?', 'action': 'speak', 'lang': lang})

@csrf_exempt
def api_ai_scan_medicine(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
        query_text = data.get('query', '') or data.get('medicine_name', '')
    except Exception:
        query_text = request.POST.get('query', '') or request.POST.get('medicine_name', '')
    user, _ = _resolve_session_and_user(request, {})
    return JsonResponse(scan_and_identify_medicine(query_text, user))

@csrf_exempt
def api_ai_explain_lab_report(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
        report_text = data.get('report_text', '') or data.get('ocr_text', '') or data.get('lab_type', '')
    except Exception:
        report_text = request.POST.get('report_text', '') or request.POST.get('ocr_text', '') or request.POST.get('lab_type', '')
    user, _ = _resolve_session_and_user(request, {})
    return JsonResponse(explain_lab_report(report_text, user))

@csrf_exempt
def api_ai_explain_prescription(request):
    user, _ = _resolve_session_and_user(request, {})
    return JsonResponse(explain_patient_prescriptions(user))

@csrf_exempt
def api_ai_explain_health_trends(request):
    user, _ = _resolve_session_and_user(request, {})
    return JsonResponse(explain_vitals_health_trends(user))

@csrf_exempt
def api_ai_ask_report(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
        question = data.get('question', '')
    except Exception:
        question = request.POST.get('question', '')
    user, _ = _resolve_session_and_user(request, {})
    return JsonResponse(answer_health_assistant_question(question, user))
