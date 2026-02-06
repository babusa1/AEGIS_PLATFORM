"""
Constants for the Symptom Checker module.
Defines triage levels, input types, symptom categories, and groupings.
"""
from enum import Enum


class TriageLevel(str, Enum):
    """Triage action levels from most to least urgent."""
    CALL_911 = "call_911"           # Emergency - Call 911 immediately
    URGENT = "urgent"               # Urgent - Contact care team immediately
    NOTIFY_CARE_TEAM = "notify_care_team"  # Alert - Care team will be notified
    NONE = "none"                   # Monitor - Follow up at next appointment


class InputType(str, Enum):
    """Types of user input expected for questions."""
    YES_NO = "yes_no"
    TEXT = "text"
    NUMBER = "number"
    CHOICE = "choice"           # Single select
    MULTISELECT = "multiselect" # Multiple select
    BUTTON = "button"           # Single action button
    CONFIRM = "confirm"         # Confirmation with checkbox


class SymptomCategory(str, Enum):
    """Categories of symptoms."""
    EMERGENCY = "emergency"
    DIGESTIVE = "digestive"
    PAIN_NERVE = "pain_nerve"
    SYSTEMIC = "systemic"
    SKIN_EXTERNAL = "skin_external"
    COMMON = "common"
    OTHER = "other"


class ConversationPhase(str, Enum):
    """Phases of the symptom checker conversation."""
    DISCLAIMER = "disclaimer"                    # Medical disclaimer
    PATIENT_CONTEXT = "patient_context"          # NEW: Last chemo date, physician visit
    EMERGENCY_CHECK = "emergency_check"          # Urgent safety check
    SYMPTOM_SELECTION = "symptom_selection"      # Grouped symptom selection
    SCREENING = "screening"                      # Per-symptom questions
    FOLLOW_UP = "follow_up"                      # Follow-up questions
    SUMMARY = "summary"                          # Session summary
    ADDING_NOTES = "adding_notes"                # Adding personal notes
    COMPLETED = "completed"                      # Final state
    EMERGENCY = "emergency"                      # Emergency path
    BRANCHED = "branched"                        # Branched to another symptom


# =============================================================================
# SYMPTOM GROUPINGS (User-Friendly Categories)
# =============================================================================

# Emergency symptoms shown in Urgent Safety Check screen
EMERGENCY_SYMPTOMS = [
    {"id": "URG-101", "name": "Trouble Breathing", "icon": "🫁"},
    {"id": "URG-102", "name": "Chest Pain", "icon": "💔"},
    {"id": "URG-103", "name": "Bleeding / Bruising", "icon": "🩸"},
    {"id": "URG-107", "name": "Fainting / Syncope", "icon": "😵"},
    {"id": "URG-108", "name": "Confusion / Altered Mental Status", "icon": "🧠"},
]

# Grouped symptoms for main symptom selection screen
# IDs must match symptom_definitions.py
SYMPTOM_GROUPS = {
    "digestive": {
        "name": "Digestive Health",
        "icon": "🍽️",
        "symptoms": [
            {"id": "NAU-203", "name": "Nausea"},
            {"id": "VOM-204", "name": "Vomiting"},
            {"id": "DIA-205", "name": "Diarrhea"},
            {"id": "CON-210", "name": "Constipation"},
            {"id": "APP-209", "name": "No Appetite"},
            {"id": "MSO-208", "name": "Mouth Sores"},
            {"id": "DEH-201", "name": "Dehydration"},
        ]
    },
    "pain_nerve": {
        "name": "Pain & Nerve",
        "icon": "⚡",
        "symptoms": [
            {"id": "PAI-213", "name": "Pain / General Aches"},
            {"id": "NEU-216", "name": "Neuropathy (Numbness/Tingling)"},
            {"id": "HEA-210", "name": "Headache"},
            {"id": "ABD-211", "name": "Abdominal Pain"},
            {"id": "JMP-212", "name": "Joint / Muscle Pain"},
            {"id": "LEG-208", "name": "Leg / Calf Pain"},
            {"id": "URG-114", "name": "Port Site Pain"},
        ]
    },
    "systemic": {
        "name": "Systemic & Infection",
        "icon": "🌡️",
        "symptoms": [
            {"id": "FEV-202", "name": "Fever"},
            {"id": "FAT-206", "name": "Fatigue / Weakness"},
            {"id": "COU-215", "name": "Cough"},
            {"id": "URI-211", "name": "Urinary Problems"},
        ]
    },
    "skin_external": {
        "name": "Skin & External",
        "icon": "🩹",
        "symptoms": [
            {"id": "SKI-212", "name": "Skin Rash / Redness"},
            {"id": "SWE-214", "name": "Swelling"},
            {"id": "EYE-207", "name": "Eye Complaints"},
        ]
    }
}


# =============================================================================
# MEDICAL DISCLAIMER
# =============================================================================

MEDICAL_DISCLAIMER = """⚠️ IMPORTANT MEDICAL DISCLAIMER

This system is an automated symptom checker. It is NOT a substitute for professional medical advice, diagnosis, or treatment.

• This tool helps you report symptoms to your care team
• It does not provide medical diagnoses
• Always follow your doctor's instructions

**If you believe you are having a medical emergency, call 911 immediately.**"""


EMERGENCY_CHECK_MESSAGE = """🚨 Urgent Safety Check

Before we assess your symptoms, we need to rule out immediate emergencies.

Please select any of the following that you are **currently experiencing**:"""


RUBY_GREETING = """Hello! I am **Ruby**, your automated triage assistant. 👋

I'm here to help assess your symptoms and share the information with your care team.

I'll ask you a few questions about each symptom you selected. Take your time - there's no rush."""


# =============================================================================
# STANDARD OPTIONS
# =============================================================================

ORAL_INTAKE_OPTIONS = [
    {"label": "I have a reduced appetite but can still eat and drink", "value": "reduced"},
    {"label": "I have had difficulty keeping food or fluids down", "value": "difficulty"},
    {"label": "I can barely eat or drink anything", "value": "barely"},
    {"label": "I have not been able to eat or drink in the last 24 hours", "value": "none"},
    {"label": "I can eat and drink normally", "value": "normal"}
]

ORAL_INTAKE_OPTIONS_12H = [
    {"label": "I have a reduced appetite but can still eat and drink", "value": "reduced"},
    {"label": "I have had difficulty keeping food or fluids down", "value": "difficulty"},
    {"label": "I can barely eat or drink anything", "value": "barely"},
    {"label": "I have not been able to eat or drink in the last 12 hours", "value": "none"},
    {"label": "I can eat and drink normally", "value": "normal"}
]

DEHYDRATION_SIGNS_OPTIONS = [
    {"label": "Dark urine", "value": "dark_urine"},
    {"label": "Reduced urination for over 12 hours", "value": "less_urine"},
    {"label": "Constantly feeling thirsty", "value": "thirsty"},
    {"label": "Feeling lightheaded", "value": "lightheaded"},
    {"label": "I know my Heart Rate/Blood Pressure", "value": "vitals_known"},
    {"label": "None of the above", "value": "none"}
]

SEVERITY_OPTIONS = [
    {"label": "Mild", "value": "mild"},
    {"label": "Moderate", "value": "mod"},
    {"label": "Severe", "value": "sev"}
]

DURATION_OPTIONS_SHORT = [
    {"label": "Less than 24 hours", "value": "<24h"},
    {"label": "1-2 days", "value": "1-2d"},
    {"label": "3-7 days", "value": "3-7d"},
    {"label": "More than a week", "value": ">1w"},
    {"label": "More than 3 weeks", "value": ">3w"}
]

DURATION_OPTIONS_NAUSEA = [
    {"label": "Less than 24 hours", "value": "<24h"},
    {"label": "24 hours", "value": "24h"},
    {"label": "2-3 days", "value": "2-3d"},
    {"label": "More than 3 days", "value": ">3d"}
]

# Medication Options
MEDS_NAUSEA = [
    {"label": "Compazine (prochlorperazine) 5 mg every 6 hours", "value": "compazine"},
    {"label": "Zofran (ondansetron) 8 mg every 8 hours", "value": "zofran"},
    {"label": "Olanzapine 5 mg daily", "value": "olanzapine"},
    {"label": "Other", "value": "other"},
    {"label": "None", "value": "none"}
]

MEDS_DIARRHEA = [
    {"label": "Imodium (loperamide) 4 mg then 2 mg after each loose stool", "value": "imodium"},
    {"label": "Lomotil (diphenoxylate/atropine) 1-2 tablets up to 4 times daily", "value": "lomotil"},
    {"label": "Other", "value": "other"},
    {"label": "None", "value": "none"}
]

MEDS_CONSTIPATION = [
    {"label": "Miralax 17g once daily", "value": "miralax_qd"},
    {"label": "Miralax 17g twice daily", "value": "miralax_bid"},
    {"label": "Senna 8.6mg", "value": "senna"},
    {"label": "Bisacodyl (Dulcolax)", "value": "bisacodyl"},
    {"label": "Docusate (Colace)", "value": "docusate"},
    {"label": "Other", "value": "other"},
    {"label": "None", "value": "none"}
]

MEDS_NEUROPATHY = [
    {"label": "Gabapentin", "value": "gabapentin"},
    {"label": "Duloxetine (Cymbalta)", "value": "duloxetine"},
    {"label": "Pregabalin (Lyrica)", "value": "pregabalin"},
    {"label": "Other", "value": "other"},
    {"label": "None", "value": "none"}
]

MEDS_COUGH = [
    {"label": "Robitussin (dextromethorphan) 10-20 mg every 4 hours", "value": "robitussin_10_20"},
    {"label": "Robitussin (dextromethorphan) 30 mg every 6-8 hours", "value": "robitussin_30"},
    {"label": "Other", "value": "other"},
    {"label": "None", "value": "none"}
]


# =============================================================================
# PATIENT CONTEXT QUESTIONS (Critical Physician Data)
# =============================================================================

PATIENT_CONTEXT_MESSAGE = """📋 **Quick Check-In**

Before we start, I need a couple of important details to help your care team:"""

LAST_CHEMO_OPTIONS = [
    {"label": "Today", "value": "today"},
    {"label": "Yesterday", "value": "1d"},
    {"label": "2-3 days ago", "value": "2-3d"},
    {"label": "4-7 days ago", "value": "4-7d"},
    {"label": "1-2 weeks ago", "value": "1-2w"},
    {"label": "More than 2 weeks ago", "value": ">2w"},
    {"label": "I haven't had chemotherapy yet", "value": "none"},
]

PHYSICIAN_VISIT_OPTIONS = [
    {"label": "Today", "value": "today"},
    {"label": "Tomorrow", "value": "1d"},
    {"label": "In 2-3 days", "value": "2-3d"},
    {"label": "This week", "value": "this_week"},
    {"label": "Next week", "value": "next_week"},
    {"label": "In 2+ weeks", "value": ">2w"},
    {"label": "Not scheduled yet", "value": "not_scheduled"},
]


# =============================================================================
# INPUT VALIDATION
# =============================================================================

import re

# -----------------------------------------------------------------------------
# Temperature Validation (Fahrenheit with Celsius Detection)
# -----------------------------------------------------------------------------
TEMP_MIN_F = 90.0    # Minimum valid Fahrenheit
TEMP_MAX_F = 110.0   # Maximum valid Fahrenheit
TEMP_FEVER_THRESHOLD = 100.3  # Fever threshold

# Celsius range (for auto-detection)
TEMP_MIN_C = 32.0    # 32°C = ~90°F (low fever range)
TEMP_MAX_C = 43.0    # 43°C = ~109°F (high fever range)


def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return (celsius * 9/5) + 32


def validate_temperature(temp_value: str) -> tuple[bool, float, str]:
    """
    Validate temperature input in Fahrenheit.
    Detects Celsius input and auto-converts.
    
    Returns:
        (is_valid, parsed_value_in_F, message)
    """
    if not temp_value:
        return False, 0.0, "📝 Please enter your temperature.\n\n**Format:** Enter in Fahrenheit (e.g., 98.6 or 101.5)"
    
    try:
        temp = float(str(temp_value).strip())
    except (ValueError, TypeError):
        return False, 0.0, "📝 Please enter a valid number.\n\n**Format:** Enter in Fahrenheit (e.g., 98.6 or 101.5)"
    
    # Detect if likely Celsius (35-43°C range is typical human body temp)
    if TEMP_MIN_C <= temp <= TEMP_MAX_C:
        converted = celsius_to_fahrenheit(temp)
        return True, converted, f"🔄 Converted: {temp}°C = **{converted:.1f}°F**"
    
    # Validate Fahrenheit range
    if temp < TEMP_MIN_F:
        return False, temp, f"⚠️ Temperature {temp}°F seems too low.\n\nPlease verify and re-enter in Fahrenheit (e.g., 98.6)"
    
    if temp > TEMP_MAX_F:
        return False, temp, f"⚠️ Temperature {temp}°F seems too high.\n\nPlease verify and re-enter in Fahrenheit (e.g., 98.6)"
    
    return True, temp, ""


# -----------------------------------------------------------------------------
# Blood Pressure Validation (Format: 120/80)
# -----------------------------------------------------------------------------
BP_PATTERN = re.compile(r'^(\d{2,3})\s*/\s*(\d{2,3})$')
SBP_MIN = 70   # Systolic min
SBP_MAX = 250  # Systolic max
DBP_MIN = 40   # Diastolic min
DBP_MAX = 150  # Diastolic max


def validate_blood_pressure(bp_value: str) -> tuple[bool, dict, str]:
    """
    Validate blood pressure input (format: 120/80).
    
    Returns:
        (is_valid, parsed_values, message)
        parsed_values = {'systolic': int, 'diastolic': int} if valid
    """
    if not bp_value:
        return False, {}, "📝 Please enter your blood pressure.\n\n**Format:** 120/80 (systolic/diastolic)"
    
    cleaned = str(bp_value).strip()
    match = BP_PATTERN.match(cleaned)
    
    if not match:
        return False, {}, "📝 Invalid format.\n\n**Format:** Enter as 120/80 (systolic/diastolic)"
    
    systolic = int(match.group(1))
    diastolic = int(match.group(2))
    
    # Validate ranges
    errors = []
    if systolic < SBP_MIN or systolic > SBP_MAX:
        errors.append(f"Systolic ({systolic}) should be between {SBP_MIN}-{SBP_MAX}")
    if diastolic < DBP_MIN or diastolic > DBP_MAX:
        errors.append(f"Diastolic ({diastolic}) should be between {DBP_MIN}-{DBP_MAX}")
    if systolic <= diastolic:
        errors.append("Systolic should be higher than diastolic")
    
    if errors:
        return False, {}, f"⚠️ Please verify:\n" + "\n".join(f"• {e}" for e in errors) + "\n\n**Format:** 120/80"
    
    return True, {'systolic': systolic, 'diastolic': diastolic}, ""


# -----------------------------------------------------------------------------
# Heart Rate Validation
# -----------------------------------------------------------------------------
HR_MIN = 40   # Minimum HR (bradycardia threshold)
HR_MAX = 200  # Maximum HR (extreme tachycardia)


def validate_heart_rate(hr_value: str) -> tuple[bool, int, str]:
    """
    Validate heart rate input (beats per minute).
    
    Returns:
        (is_valid, parsed_value, message)
    """
    if not hr_value:
        return False, 0, "📝 Please enter your heart rate.\n\n**Format:** Enter a number (e.g., 72 or 85)"
    
    try:
        hr = int(float(str(hr_value).strip()))
    except (ValueError, TypeError):
        return False, 0, "📝 Please enter a valid number.\n\n**Format:** Enter heart rate in BPM (e.g., 72 or 85)"
    
    if hr < HR_MIN:
        return False, hr, f"⚠️ Heart rate {hr} BPM seems too low.\n\nTypical range: {HR_MIN}-{HR_MAX} BPM"
    
    if hr > HR_MAX:
        return False, hr, f"⚠️ Heart rate {hr} BPM seems too high.\n\nTypical range: {HR_MIN}-{HR_MAX} BPM"
    
    return True, hr, ""


# -----------------------------------------------------------------------------
# Oxygen Saturation Validation
# -----------------------------------------------------------------------------
O2_MIN = 70   # Critical low
O2_MAX = 100  # Maximum (100%)


def validate_oxygen_saturation(o2_value: str) -> tuple[bool, int, str]:
    """
    Validate oxygen saturation (SpO2) percentage.
    
    Returns:
        (is_valid, parsed_value, message)
    """
    if not o2_value:
        return False, 0, "📝 Please enter your oxygen saturation.\n\n**Format:** Enter percentage (e.g., 98 or 95)"
    
    try:
        # Handle percentage sign
        cleaned = str(o2_value).strip().rstrip('%')
        o2 = int(float(cleaned))
    except (ValueError, TypeError):
        return False, 0, "📝 Please enter a valid number.\n\n**Format:** Enter SpO2 percentage (e.g., 98 or 95)"
    
    if o2 < O2_MIN:
        return False, o2, f"⚠️ SpO2 {o2}% seems too low.\n\nTypical range: {O2_MIN}-{O2_MAX}%"
    
    if o2 > O2_MAX:
        return False, o2, f"⚠️ SpO2 cannot exceed 100%.\n\n**Format:** Enter percentage (e.g., 98 or 95)"
    
    return True, o2, ""


# -----------------------------------------------------------------------------
# Numeric Days/Times Validation
# -----------------------------------------------------------------------------
DAYS_MIN = 0
DAYS_MAX = 30   # Max 30 days for symptom tracking
TIMES_MIN = 0
TIMES_MAX = 50  # Max 50 times per day (reasonable upper limit)


def validate_days(days_value: str, max_days: int = DAYS_MAX) -> tuple[bool, int, str]:
    """
    Validate number of days input.
    
    Returns:
        (is_valid, parsed_value, message)
    """
    if not days_value:
        return False, 0, "📝 Please enter the number of days.\n\n**Format:** Enter a number (e.g., 3 or 7)"
    
    try:
        days = int(float(str(days_value).strip()))
    except (ValueError, TypeError):
        return False, 0, "📝 Please enter a valid number.\n\n**Format:** Enter number of days (e.g., 3 or 7)"
    
    if days < DAYS_MIN:
        return False, days, "⚠️ Days cannot be negative.\n\n**Format:** Enter a number (e.g., 3 or 7)"
    
    if days > max_days:
        return False, days, f"⚠️ Please enter a value between 0-{max_days} days.\n\nIf more, please specify in follow-up."
    
    return True, days, ""


def validate_times_per_day(times_value: str, max_times: int = TIMES_MAX) -> tuple[bool, int, str]:
    """
    Validate frequency (times per day) input.
    
    Returns:
        (is_valid, parsed_value, message)
    """
    if not times_value:
        return False, 0, "📝 Please enter the number of times.\n\n**Format:** Enter a number (e.g., 3 or 6)"
    
    try:
        times = int(float(str(times_value).strip()))
    except (ValueError, TypeError):
        return False, 0, "📝 Please enter a valid number.\n\n**Format:** Enter number of times (e.g., 3 or 6)"
    
    if times < TIMES_MIN:
        return False, times, "⚠️ Value cannot be negative.\n\n**Format:** Enter a number (e.g., 3 or 6)"
    
    if times > max_times:
        return False, times, f"⚠️ Please enter a value between 0-{max_times}.\n\nIf more, please specify in follow-up."
    
    return True, times, ""


# -----------------------------------------------------------------------------
# Text Input Validation
# -----------------------------------------------------------------------------
def validate_text_input(text: str, min_length: int = 1, max_length: int = 500) -> tuple[bool, str]:
    """
    Validate text input.
    
    Returns:
        (is_valid, error_message)
    """
    if not text or len(text.strip()) < min_length:
        return False, "📝 Please provide a response."
    
    if len(text) > max_length:
        return False, f"⚠️ Response is too long.\n\nPlease limit to {max_length} characters."
    
    return True, ""


# -----------------------------------------------------------------------------
# Blood Sugar Validation
# -----------------------------------------------------------------------------
BLOOD_SUGAR_MIN = 20   # Critical low
BLOOD_SUGAR_MAX = 600  # Critical high


def validate_blood_sugar(sugar_value: str) -> tuple[bool, int, str]:
    """
    Validate blood sugar input (mg/dL).
    
    Returns:
        (is_valid, parsed_value, message)
    """
    if not sugar_value:
        return False, 0, "📝 Please enter your blood sugar level.\n\n**Format:** Enter in mg/dL (e.g., 120 or 95)"
    
    try:
        sugar = int(float(str(sugar_value).strip()))
    except (ValueError, TypeError):
        return False, 0, "📝 Please enter a valid number.\n\n**Format:** Enter blood sugar in mg/dL (e.g., 120 or 95)"
    
    if sugar < BLOOD_SUGAR_MIN:
        return False, sugar, f"⚠️ Blood sugar {sugar} mg/dL seems too low.\n\nTypical range: {BLOOD_SUGAR_MIN}-{BLOOD_SUGAR_MAX} mg/dL"
    
    if sugar > BLOOD_SUGAR_MAX:
        return False, sugar, f"⚠️ Blood sugar {sugar} mg/dL seems too high.\n\nTypical range: {BLOOD_SUGAR_MIN}-{BLOOD_SUGAR_MAX} mg/dL"
    
    return True, sugar, ""


# -----------------------------------------------------------------------------
# Weight Validation
# -----------------------------------------------------------------------------
WEIGHT_MIN_LBS = 50    # Minimum weight in lbs
WEIGHT_MAX_LBS = 500   # Maximum weight in lbs


def validate_weight(weight_value: str) -> tuple[bool, float, str]:
    """
    Validate weight input (pounds).
    
    Returns:
        (is_valid, parsed_value, message)
    """
    if not weight_value:
        return False, 0.0, "📝 Please enter your weight.\n\n**Format:** Enter in pounds (e.g., 150 or 165.5)"
    
    try:
        weight = float(str(weight_value).strip())
    except (ValueError, TypeError):
        return False, 0.0, "📝 Please enter a valid number.\n\n**Format:** Enter weight in pounds (e.g., 150 or 165.5)"
    
    if weight < WEIGHT_MIN_LBS:
        return False, weight, f"⚠️ Weight {weight} lbs seems too low.\n\nPlease verify and re-enter in pounds."
    
    if weight > WEIGHT_MAX_LBS:
        return False, weight, f"⚠️ Weight {weight} lbs seems too high.\n\nPlease verify and re-enter in pounds."
    
    return True, weight, ""


# -----------------------------------------------------------------------------
# Input Hints (for UI display)
# -----------------------------------------------------------------------------
INPUT_HINTS = {
    'temperature': "📝 Enter temperature in °F (e.g., 98.6 or 101.5)",
    'blood_pressure': "📝 Enter as systolic/diastolic (e.g., 120/80)",
    'heart_rate': "📝 Enter heart rate in BPM (e.g., 72 or 85)",
    'oxygen': "📝 Enter SpO2 percentage (e.g., 98 or 95)",
    'blood_sugar': "📝 Enter blood sugar in mg/dL (e.g., 120 or 95)",
    'days': "📝 Enter number of days (e.g., 3 or 7)",
    'times': "📝 Enter number of times (e.g., 3 or 6)",
    'weight': "📝 Enter weight in pounds (e.g., 150 or 165.5)",
}


# =============================================================================
# SUMMARY OPTIONS
# =============================================================================

SUMMARY_ACTIONS = [
    {"label": "✏️ Add Personal Notes", "value": "add_notes", "icon": "edit"},
    {"label": "📥 Download Summary", "value": "download", "icon": "download"},
    {"label": "📔 View in My Diary", "value": "view_diary", "icon": "diary"},
    {"label": "🔄 Report Another Symptom", "value": "report_another", "icon": "repeat"},
    {"label": "✅ Done for Today", "value": "done", "icon": "check"},
]
