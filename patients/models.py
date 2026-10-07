from django.db import models
from django.conf import settings
from django.utils import timezone

class VitalRecord(models.Model):
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vitals')
    recorded_at = models.DateTimeField(default=timezone.now)
    bp_systolic = models.IntegerField(default=120, help_text="Systolic Blood Pressure in mmHg")
    bp_diastolic = models.IntegerField(default=80, help_text="Diastolic Blood Pressure in mmHg")
    o2_saturation = models.FloatField(default=98.0, help_text="SpO2 percentage (e.g. 98.5)")
    sugar_level = models.FloatField(default=95.0, help_text="Blood Glucose in mg/dL")
    sugar_type = models.CharField(max_length=20, default='Fasting', choices=(
        ('Fasting', 'Fasting (FBS)'),
        ('Postprandial', 'Post-Prandial (PPBS)'),
        ('Random', 'Random (RBS)')
    ))
    weight = models.FloatField(default=68.0, help_text="Body Weight in kg")
    blood_percentage = models.FloatField(default=13.8, help_text="Hemoglobin (Hb) in g/dL")
    heart_rate = models.IntegerField(default=72, help_text="Heart Rate in Beats Per Minute (BPM)")
    source = models.CharField(max_length=50, default='Hospital Lab', choices=(
        ('Hospital Lab', 'Hospital Lab Report'),
        ('Doctor Checkup', 'Doctor Clinical Checkup'),
        ('Patient Logged', 'Patient Self Logged')
    ))
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-recorded_at']

    @property
    def bp_display(self):
        return f"{self.bp_systolic}/{self.bp_diastolic}"

    @property
    def bp_status(self):
        if self.bp_systolic < 120 and self.bp_diastolic < 80:
            return {'label': 'Optimal', 'color': 'success'}
        elif self.bp_systolic <= 129 and self.bp_diastolic < 80:
            return {'label': 'Elevated', 'color': 'warning'}
        elif self.bp_systolic <= 139 or self.bp_diastolic <= 89:
            return {'label': 'Stage 1 Hypertension', 'color': 'orange'}
        else:
            return {'label': 'Stage 2 Hypertension', 'color': 'danger'}

    @property
    def o2_status(self):
        if self.o2_saturation >= 95:
            return {'label': 'Normal', 'color': 'success'}
        elif self.o2_saturation >= 90:
            return {'label': 'Moderate Hypoxia', 'color': 'warning'}
        else:
            return {'label': 'Critical Hypoxia', 'color': 'danger'}

    @property
    def sugar_status(self):
        if self.sugar_type == 'Fasting':
            if self.sugar_level < 100:
                return {'label': 'Normal', 'color': 'success'}
            elif self.sugar_level <= 125:
                return {'label': 'Prediabetic', 'color': 'warning'}
            else:
                return {'label': 'Diabetic Range', 'color': 'danger'}
        else:
            if self.sugar_level < 140:
                return {'label': 'Normal', 'color': 'success'}
            elif self.sugar_level <= 199:
                return {'label': 'Prediabetic', 'color': 'warning'}
            else:
                return {'label': 'Elevated', 'color': 'danger'}

    @property
    def hb_status(self):
        if self.blood_percentage >= 12.0:
            return {'label': 'Healthy', 'color': 'success'}
        elif self.blood_percentage >= 10.0:
            return {'label': 'Mild Anemia', 'color': 'warning'}
        else:
            return {'label': 'Anemia Alert', 'color': 'danger'}

    @property
    def hr_status(self):
        if 60 <= self.heart_rate <= 100:
            return {'label': 'Normal Resting', 'color': 'success'}
        elif self.heart_rate < 60:
            return {'label': 'Bradycardia', 'color': 'warning'}
        else:
            return {'label': 'Tachycardia', 'color': 'danger'}

    def __str__(self):
        return f"{self.patient.get_display_name()} Vitals @ {self.recorded_at.strftime('%d-%b-%Y %H:%M')}"


class HospitalVisit(models.Model):
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='visits')
    hospital_name = models.CharField(max_length=200)
    department = models.CharField(max_length=100)
    doctor_name = models.CharField(max_length=150)
    visit_date = models.DateField(default=timezone.now)
    reason_for_visit = models.CharField(max_length=255)
    diagnosis = models.TextField()
    treatment_summary = models.TextField()
    lab_reports_summary = models.TextField(blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    vitals_snapshot = models.ForeignKey(VitalRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name='visit_snapshots')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-visit_date', '-created_at']

    def __str__(self):
        return f"{self.hospital_name} - {self.patient.get_display_name()} ({self.visit_date})"


class Prescription(models.Model):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('STOPPED', 'Stopped / Discontinued'),
    )

    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='prescriptions')
    visit = models.ForeignKey(HospitalVisit, on_delete=models.SET_NULL, null=True, blank=True, related_name='prescriptions')
    medicine_name = models.CharField(max_length=150)
    generic_name = models.CharField(max_length=150, blank=True, default='')
    purpose = models.CharField(max_length=255, default="Relief of symptoms and therapeutic maintenance", help_text="Why tablet is used (Indications & Purpose)")
    dosage = models.CharField(max_length=50, default="1 Tablet")
    form = models.CharField(max_length=30, default='Tablet', choices=(
        ('Tablet', 'Tablet'),
        ('Capsule', 'Capsule'),
        ('Syrup', 'Syrup'),
        ('Injection', 'Injection'),
        ('Drops', 'Drops'),
        ('Ointment', 'Ointment')
    ))
    morning = models.BooleanField(default=True)
    afternoon = models.BooleanField(default=False)
    night = models.BooleanField(default=True)
    timing = models.CharField(max_length=30, default='After Food', choices=(
        ('Before Food', 'Before Food (खाली पेट)'),
        ('After Food', 'After Food (भोजन के बाद)'),
        ('With Food', 'With Food (भोजन के साथ)')
    ))
    duration_days = models.IntegerField(default=7)
    quantity = models.IntegerField(default=10, help_text="Total units dispensed / prescribed")
    start_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    is_active = models.BooleanField(default=True)
    instructions = models.TextField(blank=True, default="Take with warm water as directed.")
    prescribed_by = models.CharField(max_length=150, default="Govt Senior Medical Officer")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-start_date', '-id']

    def save(self, *args, **kwargs):
        self.is_active = (self.status == 'ACTIVE')
        super().save(*args, **kwargs)

    @property
    def schedule_summary(self):
        parts = []
        if self.morning: parts.append("Morning (सुबह)")
        if self.afternoon: parts.append("Afternoon (दोपहर)")
        if self.night: parts.append("Night (रात)")
        return " • ".join(parts) or "As needed"

    def __str__(self):
        return f"{self.medicine_name} ({self.dosage}) for {self.patient.get_display_name()} [{self.status}]"


class MedicationDoseLog(models.Model):
    SLOT_CHOICES = (
        ('MORNING', '08:00 AM (Morning / सुबह)'),
        ('AFTERNOON', '01:00 PM (Afternoon / दोपहर)'),
        ('NIGHT', '08:00 PM (Night / रात)'),
    )

    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='dose_logs')
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dose_logs')
    dose_date = models.DateField(default=timezone.now)
    time_slot = models.CharField(max_length=20, choices=SLOT_CHOICES, default='MORNING')
    is_taken = models.BooleanField(default=False)
    taken_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-dose_date', 'time_slot']
        unique_together = ('prescription', 'patient', 'dose_date', 'time_slot')

    def __str__(self):
        return f"{self.prescription.medicine_name} - {self.dose_date} ({self.time_slot}): {'Taken' if self.is_taken else 'Pending'}"


class LabTest(models.Model):
    CATEGORY_CHOICES = (
        ('Hematology', 'Hematology & Blood Counts'),
        ('Biochemistry', 'Biochemistry & Metabolic Panels'),
        ('Pathology', 'Clinical Pathology'),
        ('Microbiology', 'Microbiology & Serology'),
        ('Cardiology', 'Cardiovascular Diagnostics'),
        ('Imaging', 'Radiological & Ultrasound Imaging'),
    )

    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=50, unique=True, default='LAB-01')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Hematology')
    unit = models.CharField(max_length=50, blank=True, default='')
    reference_range = models.CharField(max_length=150, blank=True, default='')
    sample_type = models.CharField(max_length=100, default='Venous Whole Blood')
    turnaround_hours = models.IntegerField(default=24)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.code}) [{self.category}]"


class LabOrder(models.Model):
    STATUS_CHOICES = (
        ('ORDERED', 'Ordered (जांच दर्ज)'),
        ('SAMPLE_COLLECTED', 'Sample Collected (सैंपल प्राप्त)'),
        ('PROCESSING', 'Processing (परीक्षण जारी)'),
        ('COMPLETED', 'Completed (रिपोर्ट तैयार)'),
        ('CANCELLED', 'Cancelled (रद्द)'),
    )

    order_reference = models.CharField(max_length=40, unique=True, blank=True)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lab_orders')
    doctor_name = models.CharField(max_length=150, default='Govt Medical Officer')
    hospital_name = models.CharField(max_length=200, default='Central Govt Hospital')
    test = models.ForeignKey(LabTest, on_delete=models.CASCADE, related_name='orders')
    order_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='ORDERED')
    result_value = models.CharField(max_length=100, blank=True, default='')
    unit = models.CharField(max_length=50, blank=True, default='')
    reference_range = models.CharField(max_length=150, blank=True, default='')
    lab_technician = models.CharField(max_length=150, blank=True, default='Certified Lab Technologist')
    result_date = models.DateTimeField(null=True, blank=True)
    report_file_url = models.CharField(max_length=255, blank=True, default='')
    notes = models.TextField(blank=True, help_text="Clinical observations / sample quality remarks")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-order_date', '-created_at']

    def save(self, *args, **kwargs):
        if not self.order_reference:
            import random
            year = timezone.now().year
            rand_code = random.randint(10000, 99999)
            self.order_reference = f"LAB-{year}-{rand_code}"
        if not self.unit and self.test:
            self.unit = self.test.unit
        if not self.reference_range and self.test:
            self.reference_range = self.test.reference_range
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_reference} - {self.test.name} for {self.patient.get_display_name()} [{self.status}]"


class DischargeSummary(models.Model):
    summary_reference = models.CharField(max_length=40, unique=True, blank=True)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='discharge_summaries')
    doctor_name = models.CharField(max_length=150)
    doctor_reg_no = models.CharField(max_length=100, default='MCI-98421')
    hospital_name = models.CharField(max_length=200, default='All India Institute of Medical Sciences (AIIMS)')
    department = models.CharField(max_length=100, default='General Medicine')
    admission_date = models.DateField(default=timezone.now)
    discharge_date = models.DateField(default=timezone.now)
    reason_for_admission = models.CharField(max_length=255)
    clinical_findings = models.TextField()
    diagnosis = models.TextField()
    procedures_treatment = models.TextField()
    investigation_results = models.TextField(blank=True)
    condition_at_discharge = models.CharField(max_length=150, default='Stable and Ambulatory (स्थिर एवं स्वस्थ)')
    discharge_medicines = models.TextField(help_text="Prescribed medicines list with dosage and frequency")
    diet_instructions = models.TextField(default="Normal balanced diet, avoid oily and overly salty food. Drink 2.5L water daily.")
    activity_instructions = models.TextField(default="Light walking allowed. Avoid strenuous physical activity for 7 days.")
    follow_up_instructions = models.TextField(default="Review in OPD after 10 days with repeat Fasting Blood Sugar and BP readings.")
    follow_up_date = models.DateField(null=True, blank=True)
    verification_code = models.CharField(max_length=64, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-discharge_date', '-created_at']

    def save(self, *args, **kwargs):
        if not self.summary_reference:
            import random
            year = timezone.now().year
            rand_code = random.randint(10000, 99999)
            self.summary_reference = f"DS-{year}-{rand_code}"
        if not self.verification_code:
            import uuid
            self.verification_code = str(uuid.uuid4()).replace('-', '')[:16].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Discharge Summary #{self.summary_reference} - {self.patient.get_display_name()} ({self.discharge_date})"


class VaccinationRecord(models.Model):
    STATUS_CHOICES = (
        ('COMPLETED', 'Completed (लगाई गई)'),
        ('SCHEDULED', 'Scheduled (नियत)'),
        ('OVERDUE', 'Overdue (अतिदेय)'),
    )

    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vaccinations')
    vaccine_name = models.CharField(max_length=150)
    dose_number = models.IntegerField(default=1)
    date_given = models.DateField(null=True, blank=True)
    hospital_center = models.CharField(max_length=200, default='Govt Primary Health Center')
    provider_name = models.CharField(max_length=150, default='Govt Vaccination Officer')
    next_due_date = models.DateField(null=True, blank=True)
    batch_number = models.CharField(max_length=100, blank=True, default='VAC-2026-X89')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='COMPLETED')
    notes = models.TextField(blank=True, default='Administered intramuscularly. No adverse reaction observed.')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_given', 'next_due_date']

    def __str__(self):
        return f"{self.vaccine_name} Dose #{self.dose_number} - {self.patient.get_display_name()} [{self.status}]"


class EmergencyProfile(models.Model):
    patient = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='emergency_profile')
    contact_name = models.CharField(max_length=150, default='Sunil Kumar (Brother)')
    relationship = models.CharField(max_length=100, default='Brother / Primary Kin')
    phone_number = models.CharField(max_length=20, default='+91 9876543210')
    blood_group = models.CharField(max_length=10, default='B+')
    date_of_birth = models.DateField(null=True, blank=True)
    known_allergies = models.TextField(default='Penicillin, Sulfa Drugs (None known for NSAIDs)')
    important_current_meds = models.TextField(default='Telmisartan 40mg (Morning), Metformin 500mg (Night)')
    major_medical_conditions = models.TextField(default='Primary Hypertension, Type-2 Diabetes Mellitus')
    preferred_hospital = models.CharField(max_length=200, default='AIIMS Hospital Trauma Center, New Delhi')
    emergency_hotline = models.CharField(max_length=50, default='108 (Ambulance) / 112 (National Emergency)')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Emergency Profile - {self.patient.get_display_name()} ({self.blood_group})"


class ConsentRecord(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending (अनुमति प्रतीक्षारत)'),
        ('GRANTED', 'Granted (अनुमति स्वीकृत)'),
        ('DENIED', 'Denied (अनुमति अस्वीकृत)'),
        ('REVOKED', 'Revoked (अनुमति वापस ली गई)'),
        ('EXPIRED', 'Expired (समय समाप्त)'),
    )

    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='consents_given')
    doctor_name = models.CharField(max_length=150)
    doctor_reg_id = models.CharField(max_length=100, blank=True, default='')
    hospital_name = models.CharField(max_length=200, default='Government Hospital')
    purpose = models.CharField(max_length=255, default='Clinical Consultation & Diagnosis')
    scope_medical_history = models.BooleanField(default=True)
    scope_lab_reports = models.BooleanField(default=True)
    scope_prescriptions = models.BooleanField(default=True)
    scope_other_records = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='GRANTED')
    requested_at = models.DateTimeField(default=timezone.now)
    actioned_at = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default='Consent granted via National Digital Health consent protocol.')

    class Meta:
        ordering = ['-requested_at']

    def is_active(self):
        if self.status != 'GRANTED':
            return False
        if self.valid_until and self.valid_until < timezone.now():
            return False
        return True

    def __str__(self):
        return f"Consent for Dr. {self.doctor_name} by {self.patient.get_display_name()} [{self.status}]"


class PhysiotherapyVideo(models.Model):
    CATEGORY_CHOICES = (
        ('back', 'Lumbar Spine & Back Strain'),
        ('knee', 'Knee Joint & Osteoarthritis'),
        ('neck', 'Neck & Cervical Spondylosis'),
        ('shoulder', 'Frozen Shoulder & Rotator Cuff'),
        ('stroke', 'Post-Stroke & Balance Rehab'),
    )

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='back')
    duration_text = models.CharField(max_length=30, default='8:30 mins')
    level_text = models.CharField(max_length=50, default='Beginner Safe')
    instructions = models.TextField(help_text="Step-by-step exercise instructions")
    embed_url = models.URLField(help_text="Embeddable video URL (e.g. YouTube nocookie embed)")
    thumbnail_url = models.URLField(blank=True, default='')
    source_name = models.CharField(max_length=150, default='AIIMS Tele-Physiotherapy Protocol')
    language = models.CharField(max_length=50, default='English / Hindi / Telugu')
    external_video_id = models.CharField(max_length=100, blank=True, default='', help_text="External video ID or source reference")
    external_platform = models.CharField(max_length=60, default='YouTube (Embeddable)', help_text="e.g. YouTube, Vimeo, Educational Medical Host")
    external_url = models.URLField(blank=True, default='', help_text="Direct link if embedding disallowed or for external viewing")
    allows_embedding = models.BooleanField(default=True, help_text="Whether external platform permits iframe embedding")
    date_added = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', '-created_at']

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"


class RadiologyReport(models.Model):
    MODALITY_CHOICES = (
        ('X-Ray', 'Digital X-Ray Radiograph'),
        ('CT Scan', 'Computed Tomography (CT Scan)'),
        ('MRI', 'Magnetic Resonance Imaging (MRI)'),
        ('Ultrasound', 'Ultrasound & Doppler Sonography'),
        ('Mammography', 'Diagnostic Mammography'),
    )

    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='radiology_reports')
    report_title = models.CharField(max_length=200, help_text="e.g. Chest X-Ray PA View, HRCT Chest, CT Brain Non-Contrast, Lumbar Spine MRI")
    modality = models.CharField(max_length=30, choices=MODALITY_CHOICES, default='X-Ray')
    scan_type = models.CharField(max_length=30, default='X-Ray', help_text="X-Ray, CT Scan, MRI, Ultrasound, Mammography")
    body_part = models.CharField(max_length=100, default='Chest')
    report_date = models.DateField(default=timezone.now)
    hospital_name = models.CharField(max_length=200, default='AIIMS Radiodiagnosis Department')
    radiologist_name = models.CharField(max_length=150, default='Dr. Subhash Chandra (MD Radiology)')
    radiologist_reg = models.CharField(max_length=100, blank=True, default='MCI-98421')
    reason_for_exam = models.TextField(blank=True, default='Clinical evaluation for persistent pain / routine diagnostic review', help_text="Clinical information / Reason for examination")
    procedure_name = models.CharField(max_length=200, blank=True, default='Standard Diagnostic High-Resolution Multi-Slice Acquisition')
    findings = models.TextField(help_text="Detailed radiological observations and findings")
    measurements = models.TextField(blank=True, default='Standard organ anatomical dimensions within normal limits.', help_text="Quantitative measurements & diagnostic parameters")
    impression = models.TextField(help_text="Radiological diagnosis and conclusion summary")
    dicom_slice_count = models.IntegerField(default=48, help_text="Total DICOM slices in imaging study")
    dicom_frames_json = models.TextField(blank=True, default='[]', help_text="JSON array of DICOM frame image URLs")
    image_svg = models.TextField(blank=True, help_text="SVG vector image or preview graphic data")
    has_imaging_files = models.BooleanField(default=False, help_text="True if study files or frames are uploaded")
    is_dicom = models.BooleanField(default=False, help_text="True if study is native DICOM format")
    dicom_file = models.FileField(upload_to='radiology_studies/', null=True, blank=True, help_text="Authorized raw DICOM (.dcm) or imaging study file")
    secure_token = models.CharField(max_length=64, blank=True, default='', db_index=True, help_text="Non-predictable cryptographic token for authorized imaging access")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-report_date', '-created_at']

    def save(self, *args, **kwargs):
        if not self.secure_token:
            import uuid
            self.secure_token = uuid.uuid4().hex
        if not self.scan_type:
            self.scan_type = self.modality
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.modality}] {self.report_title} - {self.patient.get_display_name()} ({self.report_date})"


class HealthNotification(models.Model):
    CATEGORY_CHOICES = (
        ('Checkup Reminder', 'Routine Health Checkup'),
        ('Medication Alert', 'Medication Refill / Dose Alert'),
        ('Immunization', 'Vaccination / Immunization Drive'),
        ('Advisory', 'Public Health Advisory (GOI)'),
        ('Record Update', 'New Lab / Diagnostic Record Added'),
        ('Consent Alert', 'Patient Consent Request'),
    )

    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES, default='Checkup Reminder')
    created_at = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)
    action_tab = models.CharField(max_length=30, default='home', help_text="Tab identifier to navigate to")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.category}] {self.title} - {self.patient.get_display_name()}"


class Ambulance(models.Model):
    STATUS_CHOICES = (
        ('AVAILABLE', 'Available (उपलब्ध)'),
        ('ON_DUTY', 'On Duty (कार्यरत)'),
        ('MAINTENANCE', 'Under Maintenance (रखरखाव)'),
        ('OFFLINE', 'Offline (ऑफलाइन)'),
    )

    hospital = models.ForeignKey('appointments.HospitalFacility', on_delete=models.CASCADE, related_name='ambulances')
    vehicle_number = models.CharField(max_length=30, unique=True, help_text="e.g. DL-01-AB-1080")
    driver_name = models.CharField(max_length=150, default='Rajesh Kumar')
    driver_phone = models.CharField(max_length=20, default='+91 9810810800')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')
    latitude = models.FloatField(null=True, blank=True, default=28.5672)
    longitude = models.FloatField(null=True, blank=True, default=77.2100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ambulance [{self.vehicle_number}] - {self.hospital.name} ({self.get_status_display()})"


class EmergencyRequest(models.Model):
    EMERGENCY_TYPES = (
        ('Accident / Injury', 'Accident & Trauma Injury'),
        ('Chest pain', 'Severe Chest Pain / Cardiac Event'),
        ('Breathing difficulty', 'Breathing Difficulty / Low O2'),
        ('Unconsciousness', 'Unconsciousness / Fainting'),
        ('Severe bleeding', 'Severe Haemorrhage / Bleeding'),
        ('Pregnancy emergency', 'Maternity / Pregnancy Emergency'),
        ('Stroke symptoms', 'Stroke / Neurological Attack'),
        ('Other emergency', 'Other Acute Medical Emergency'),
    )

    PRIORITY_CHOICES = (
        ('CRITICAL', 'Critical (Immediate Dispatch)'),
        ('HIGH', 'High Priority'),
        ('MEDIUM', 'Medium Priority'),
        ('LOW', 'Low Priority'),
    )

    STATUS_CHOICES = (
        ('RECEIVED', 'Request Received'),
        ('ACCEPTED', 'Hospital Accepted'),
        ('AMBULANCE_ASSIGNED', 'Ambulance Assigned'),
        ('DISPATCHED', 'Ambulance Dispatched'),
        ('ON_THE_WAY', 'Ambulance On the Way'),
        ('PICKED_UP', 'Patient Picked Up'),
        ('REACHED_HOSPITAL', 'Patient Reached Hospital'),
        ('COMPLETED', 'Request Completed'),
        ('CANCELLED', 'Request Cancelled'),
    )

    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='emergency_requests')
    emergency_type = models.CharField(max_length=60, choices=EMERGENCY_TYPES, default='Accident / Injury')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='CRITICAL')
    latitude = models.FloatField(default=28.5672)
    longitude = models.FloatField(default=77.2100)
    location_address = models.CharField(max_length=255, default='Near Patient Location, New Delhi')
    patient_notes = models.TextField(blank=True, default='Urgent medical assistance required.')
    contact_phone = models.CharField(max_length=20, default='+91 9876543210')
    hospital = models.ForeignKey('appointments.HospitalFacility', on_delete=models.SET_NULL, null=True, blank=True, related_name='emergency_requests')
    ambulance = models.ForeignKey(Ambulance, on_delete=models.SET_NULL, null=True, blank=True, related_name='dispatches')
    driver_name = models.CharField(max_length=150, blank=True, default='')
    driver_phone = models.CharField(max_length=20, blank=True, default='')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='RECEIVED')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"SOS [{self.emergency_type}] by {self.patient.get_display_name()} ({self.status})"


class PatientFeedback(models.Model):
    COMPLAINT_CATEGORIES = (
        ('Doctor behavior', 'Doctor Communication & Behavior'),
        ('Staff behavior', 'Hospital Support Staff Behavior'),
        ('Long waiting time', 'Excessive OPD Waiting Time'),
        ('Billing issue', 'Billing / Scheme Claim Issue'),
        ('Medicine availability', 'Pharmacy & Medicine Shortage'),
        ('Lab report delay', 'Lab Report / Diagnostic Delay'),
        ('Appointment issue', 'Appointment Slot Conflict'),
        ('Cleanliness', 'Sanitation & Cleanliness'),
        ('Ambulance/emergency issue', 'Ambulance & SOS Delay'),
        ('Other', 'Other Feedback / Complaint'),
        ('None', 'No Complaint / General Praise'),
    )

    STATUS_CHOICES = (
        ('SUBMITTED', 'Submitted'),
        ('IN_PROGRESS', 'In Progress / Under Review'),
        ('RESOLVED', 'Resolved'),
        ('ESCALATED', 'Escalated to Govt Admin'),
        ('REJECTED', 'Closed / Rejected'),
    )

    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='feedbacks')
    appointment = models.ForeignKey('appointments.AppointmentBooking', on_delete=models.SET_NULL, null=True, blank=True, related_name='feedbacks')
    hospital = models.ForeignKey('appointments.HospitalFacility', on_delete=models.CASCADE, related_name='feedbacks')
    doctor = models.ForeignKey('appointments.DoctorProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='feedbacks')

    doctor_rating = models.IntegerField(default=5, help_text="1 to 5 Stars")
    cleanliness_rating = models.IntegerField(default=5)
    waiting_time_rating = models.IntegerField(default=5)
    booking_rating = models.IntegerField(default=5)
    staff_rating = models.IntegerField(default=5)
    overall_rating = models.IntegerField(default=5)

    written_feedback = models.TextField(blank=True, default='')
    complaint_category = models.CharField(max_length=50, choices=COMPLAINT_CATEGORIES, default='None')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUBMITTED')
    response_notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Feedback ({self.overall_rating}★) by {self.patient.get_display_name()} for {self.hospital.name}"


class TargetedBroadcast(models.Model):
    SEVERITY_CHOICES = (
        ('INFO', 'Information Advisory (Blue)'),
        ('WARNING', 'Warning Alert (Orange)'),
        ('CRITICAL', 'Critical Health Emergency (Red)'),
    )

    TARGET_TYPE_CHOICES = (
        ('ALL', 'All Citizens Nationally'),
        ('STATE', 'Specific State'),
        ('DISTRICT', 'Specific District'),
        ('PINCODE', 'Specific PIN Code Area'),
        ('HEALTH_CONDITION', 'Patients with Specific Health Condition'),
        ('AGE_GROUP', 'Target Age Group'),
    )

    title = models.CharField(max_length=255)
    message = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='WARNING')
    target_type = models.CharField(max_length=30, choices=TARGET_TYPE_CHOICES, default='ALL')
    target_value = models.CharField(max_length=100, default='All India', help_text="e.g. Delhi, 110001, Diabetes, 60+")
    issuing_authority = models.CharField(max_length=150, default='Ministry of Health & Family Welfare (MoHFW)')
    valid_until = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, default='ACTIVE', choices=(('ACTIVE', 'Active'), ('EXPIRED', 'Expired')))
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.severity}] {self.title} -> {self.target_value}"


class DiseaseRecord(models.Model):
    hospital = models.ForeignKey('appointments.HospitalFacility', on_delete=models.CASCADE, related_name='disease_records')
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='disease_entries')
    disease_name = models.CharField(max_length=150, db_index=True, help_text="e.g. Dengue Fever, Viral Illness, Acute Respiratory Infection, Typhoid, Diabetes")
    symptoms = models.TextField(blank=True, default='')
    district = models.CharField(max_length=100, default='New Delhi', db_index=True)
    state = models.CharField(max_length=100, default='Delhi')
    reported_date = models.DateField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-reported_date']

    def __str__(self):
        return f"{self.disease_name} at {self.hospital.name} ({self.reported_date})"


