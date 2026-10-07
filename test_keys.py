# -*- coding: utf-8 -*-
"""
Generator for comprehensive multi-lingual translations.js supporting:
en-IN, hi-IN, te-IN, ta-IN, kn-IN, ml-IN, mr-IN, bn-IN, gu-IN
"""
import json

keys = [
    # Header & Nav
    "brand_title", "brand_sub", "portal_login", "logout", "aadhaar_verified", "aadhaar_unverified",
    "role_patient", "role_doctor", "role_admin",
    "tab_home", "tab_records", "tab_bookings", "tab_notifications", "tab_prescription",
    "tab_physio", "tab_radiology", "tab_about", "tab_settings", "btn_ai_scanner", "btn_easy_voice_mode",

    # Easy Voice Mode
    "easy_speak", "easy_home", "easy_appointment", "easy_medicines", "easy_reports",
    "easy_doctor", "easy_notifications", "easy_emergency", "easy_voice_mode_title",
    "easy_listening_prompt", "easy_understanding_prompt", "easy_speaking_prompt",

    # Home Tab & Vitals
    "home_title", "refresh_plots", "log_vitals_btn", "bp_title", "bp_unit", "bp_footer",
    "o2_title", "o2_unit", "o2_footer", "sugar_title", "sugar_unit", "sugar_footer",
    "weight_title", "weight_unit", "weight_footer", "blood_title", "blood_unit", "blood_footer",
    "heart_title", "heart_unit", "heart_footer", "plots_heading", "plots_sub",
    "chart_bp_title", "chart_sugar_title", "chart_hr_title", "chart_hb_title",

    # OPD Queue
    "opd_consultation_title", "your_token", "current_in_room", "patients_ahead",

    # Emergency & Smart AI Strip
    "emergency_profile_title", "btn_view_emergency_card", "btn_edit",
    "ai_smart_title", "ai_smart_sub", "ai_guardrails_active",
    "ai_scan_medicine_title", "ai_scan_medicine_desc",
    "ai_explain_lab_title", "ai_explain_lab_desc",
    "ai_explain_rx_title", "ai_explain_rx_desc",
    "ai_explain_trends_title", "ai_explain_trends_desc",
    "ai_ask_report_title", "ai_ask_report_desc", "ai_disclaimer_notice",

    # Records Tab
    "records_title", "records_sub", "explain_reports_btn", "add_record_btn",
    "records_labs_heading", "records_labs_sub",
    "col_order_ref", "col_test_name", "col_category", "col_date", "col_status", "col_result", "col_ref_range", "col_action",
    "status_completed", "status_processing", "status_sample_collected", "status_ordered",
    "btn_view_download", "btn_sync_vitals",
    "records_discharge_heading", "records_vaccinations_heading", "records_consent_heading", "records_visits_heading",
    "reason_label", "diagnosis_label", "vitals_label", "view_report_btn",

    # Bookings Tab
    "bookings_title", "bookings_sub", "loc_status_heading", "btn_use_current_loc", "btn_change_loc",
    "btn_apply_search", "btn_find_nearest_hospital", "interactive_map_title", "interactive_map_sub",
    "search_box_title", "loc_label", "loc_auto_btn", "loc_placeholder", "area_label", "area_placeholder",
    "hosp_label", "hosp_placeholder", "date_label", "slot_label", "doctor_label", "doctor_placeholder",
    "symptoms_label", "check_book_btn", "hospitals_near_you", "scheduled_apts_title",
    "booking_accepted_title", "booking_denied_title",

    # Prescriptions Tab
    "rx_title", "rx_sub", "rx_read_btn", "rx_purpose_label", "status_active", "no_prescriptions", "no_rx_sub",
    "morning_pill", "afternoon_pill", "night_pill", "timing_label", "instructions_label",
    "prescribed_by_label", "duration_label", "btn_mark_taken", "badge_dose_taken",

    # Physiotherapy Tab
    "physio_banner_title", "physio_badge_protocol", "physio_banner_sub", "physio_free_tag",
    "physio_filter_heading", "physio_search_placeholder",
    "physio_cat_all", "physio_cat_back", "physio_cat_knee", "physio_cat_neck", "physio_cat_shoulder", "physio_cat_stroke",
    "physio_play_video", "physio_instructions_heading", "physio_level_label", "physio_duration_label", "physio_source_label",
    "physio_external_notice",

    # Radiology Tab
    "rad_banner_title", "rad_badge_pac", "rad_banner_sub", "rad_security_pill",
    "rad_filter_heading", "rad_search_placeholder",
    "rad_mod_all", "rad_mod_xray", "rad_mod_ct", "rad_mod_mri", "rad_mod_usg", "rad_mod_mammo",
    "rad_reason_heading", "rad_proc_heading", "rad_findings_heading", "rad_meas_heading", "rad_impression_heading",
    "rad_view_full_report", "rad_inspect_dicom", "no_rad_reports", "rad_empty_msg",
    "rad_cert_title", "rad_cert_sub", "lbl_patient_name", "lbl_patient_id", "lbl_exam_date", "lbl_modality", "lbl_facility",
    "rad_section_clinical", "rad_section_procedure", "rad_section_findings", "rad_section_meas", "rad_section_impression",
    "rad_digital_auth", "rad_preset_label", "btn_close_pacs", "btn_print", "btn_close",

    # Notifications Tab
    "notifications_title", "notifications_sub", "dismiss_btn",

    # About Us Tab
    "about_title", "about_sub", "guide_heading", "free_health",

    # Settings Tab
    "settings_title", "settings_sub", "edit_profile_title", "name_label", "age_label", "gender_label",
    "blood_group_label", "city_label", "emergency_label", "save_profile_btn", "high_contrast_label", "pref_lang_label",

    # Modals & Confirmations
    "confirm_action_title", "btn_cancel", "btn_confirm_proceed", "btn_save", "btn_close_modal",
    "modal_log_vitals_title", "modal_booking_status_title",

    # Auth & Login
    "patient_login_title", "patient_login_sub", "doctor_login_title", "admin_login_title",
    "phone_number_label", "password_label", "forgot_password_link",
    "btn_login_patient", "btn_login_doctor", "btn_login_admin",
    "continue_with_google", "no_account_text", "create_account_link",
    "register_title", "register_sub", "full_name_label", "aadhaar_label",
    "get_otp_btn", "verify_otp_btn", "enter_otp_label",

    # Voice AI Interface
    "voice_bot_title", "voice_bot_sub", "ai_safety_indicator", "ai_safety_sub",
    "btn_repeat", "btn_reset", "btn_doctor", "btn_scanner", "btn_emergency",
    "chip_headache", "chip_fever", "chip_cough", "chip_stomach", "chip_med_ask",
    "voice_chip_locate", "voice_chip_explain", "voice_chip_records", "voice_chip_book",
    "voice_chip_rx", "voice_chip_vitals", "voice_input_placeholder"
]

print(f"Total keys defined: {len(keys)}")
