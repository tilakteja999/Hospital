import uuid
import hashlib
import json
from django.db import models
from django.conf import settings
from django.utils import timezone
import datetime


class AssistantSession(models.Model):
    """
    Tracks persistent conversation & workflow state for the voice assistant.
    Stores workflow state without duplicating private medical records.
    """
    ROLE_CHOICES = (
        ('PATIENT', 'Patient'),
        ('DOCTOR', 'Doctor'),
        ('ADMIN', 'Admin / Hospital Authority'),
    )

    session_id = models.CharField(max_length=64, unique=True, db_index=True, default=uuid.uuid4)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='assistant_sessions')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='PATIENT')
    preferred_language = models.CharField(max_length=15, default='en-IN')
    detected_language = models.CharField(max_length=15, default='en-IN')
    active_intent = models.CharField(max_length=60, blank=True, default='UNKNOWN')
    workflow_state = models.CharField(max_length=60, default='IDLE')
    workflow_data = models.JSONField(default=dict, blank=True)
    context_data = models.JSONField(default=dict, blank=True, help_text="Client safe route & selected resource context")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-updated_at']

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + datetime.timedelta(hours=2)
        super().save(*args, **kwargs)

    def is_expired(self):
        return self.expires_at and timezone.now() > self.expires_at

    def reset_workflow(self):
        self.active_intent = 'UNKNOWN'
        self.workflow_state = 'IDLE'
        self.workflow_data = {}
        self.save()

    def __str__(self):
        user_str = self.user.get_display_name() if self.user else 'Guest'
        return f"AssistantSession [{self.session_id[:8]}] - {user_str} ({self.role}) [{self.workflow_state}]"


class ServerConfirmationToken(models.Model):
    """
    Cryptographic server-side confirmation token for consequential write operations.
    Tied to user, specific action, parameter hash, and short expiration (5 mins).
    Prevents prompt injection / LLM hallucinations from bypassing user consent.
    """
    token = models.CharField(max_length=64, unique=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='confirmation_tokens')
    action = models.CharField(max_length=60, help_text="e.g. CREATE_APPOINTMENT, CANCEL_APPOINTMENT, RESCHEDULE_APPOINTMENT")
    parameters_hash = models.CharField(max_length=64, help_text="SHA-256 hash of normalized parameters")
    parameters = models.JSONField(default=dict)
    summary_text = models.TextField(blank=True, help_text="Human-readable summary presented to user")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    idempotency_key = models.CharField(max_length=100, blank=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    @classmethod
    def compute_hash(cls, action, params):
        payload = f"{action}:{json.dumps(params, sort_keys=True)}"
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    @classmethod
    def create_token(cls, user, action, parameters, summary_text="", ttl_minutes=5, idempotency_key=""):
        p_hash = cls.compute_hash(action, parameters)
        token_str = str(uuid.uuid4()).replace('-', '')
        expires_at = timezone.now() + datetime.timedelta(minutes=ttl_minutes)

        # Invalidate existing pending tokens for this user & action
        cls.objects.filter(user=user, action=action, is_used=False).update(is_used=True)

        return cls.objects.create(
            token=token_str,
            user=user,
            action=action,
            parameters_hash=p_hash,
            parameters=parameters,
            summary_text=summary_text,
            expires_at=expires_at,
            idempotency_key=idempotency_key or token_str
        )

    def is_valid(self, action=None, params=None):
        if self.is_used:
            return False, "This confirmation token has already been used."
        if timezone.now() > self.expires_at:
            return False, "This confirmation token has expired. Please check the details and try again."
        if action and self.action != action:
            return False, "Action mismatch for confirmation token."
        if params is not None:
            expected_hash = self.compute_hash(self.action, params)
            if self.parameters_hash != expected_hash:
                return False, "Parameter integrity mismatch. The confirmed details have changed."
        return True, "Valid"

    def mark_used(self):
        self.is_used = True
        self.save()

    def __str__(self):
        return f"Token [{self.action}] for {self.user.get_display_name()} ({'Used' if self.is_used else 'Active'})"


class AISafetyLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_safety_logs')
    user_display = models.CharField(max_length=150, blank=True, default='Citizen')
    query_text = models.TextField()
    response_text = models.TextField()
    language = models.CharField(max_length=20, default='English')
    is_emergency_flagged = models.BooleanField(default=False)
    doctor_consultation_advised = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"AISafetyLog [{self.timestamp.strftime('%d-%b-%Y %H:%M')}] {self.user_display} - Emergency: {self.is_emergency_flagged}"

