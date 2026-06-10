"""
Symptom Definitions for the Oncology Symptom Checker.
Contains all 27 symptom modules with their screening questions,
follow-up questions, and triage logic.
"""
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from .constants import (
    TriageLevel, InputType, SymptomCategory,
    ORAL_INTAKE_OPTIONS, ORAL_INTAKE_OPTIONS_12H, DEHYDRATION_SIGNS_OPTIONS,
    SEVERITY_OPTIONS, DURATION_OPTIONS_SHORT,
    MEDS_NAUSEA, MEDS_DIARRHEA, MEDS_CONSTIPATION, MEDS_NEUROPATHY, MEDS_COUGH
)


@dataclass
class Option:
    """Represents a selectable option for a question."""
    label: str
    value: Any


@dataclass
class Question:
    """Represents a single question in the symptom checker."""
    id: str
    text: str
    input_type: InputType
    options: List[Option] = field(default_factory=list)
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None  # When to show this question


@dataclass
class LogicResult:
    """Result of evaluating symptom logic."""
    action: str  # 'continue', 'branch', 'stop'
    triage_level: TriageLevel = TriageLevel.NONE
    triage_message: str = ""
    branch_to_symptom_id: Optional[str] = None


@dataclass
class SymptomDef:
    """Definition of a symptom module."""
    id: str
    name: str
    category: SymptomCategory
    screening_questions: List[Question]
    evaluate_screening: Callable[[Dict[str, Any]], LogicResult]
    follow_up_questions: List[Question] = field(default_factory=list)
    evaluate_follow_up: Optional[Callable[[Dict[str, Any]], LogicResult]] = None
    hidden: bool = False  # Hidden symptoms are triggered by branching only


def create_option(label: str, value: Any) -> Option:
    """Helper to create an Option."""
    return Option(label=label, value=value)


def _days_at_least(days_value: Any, threshold: int) -> bool:
    """Helper to check if days value is at least the threshold."""
    if days_value is None:
        return False
    try:
        return float(days_value) >= threshold
    except (ValueError, TypeError):
        return False


def opts_from_dicts(dicts: List[Dict]) -> List[Option]:
    """Convert list of dicts to list of Options."""
    return [Option(label=d["label"], value=d["value"]) for d in dicts]


def parse_vitals_from_text(vitals_text: str) -> Dict[str, bool]:
    """Parse vitals from text input and check for concerning values."""
    if not vitals_text:
        return {"hr_high": False, "bp_low": False}
    
    text = vitals_text.lower()
    hr_high = False
    bp_low = False
    
    # Try to extract HR value
    import re
    hr_match = re.search(r'hr[:\s]*(\d+)', text, re.IGNORECASE) or \
               re.search(r'heart\s*rate[:\s]*(\d+)', text, re.IGNORECASE) or \
               re.search(r'pulse[:\s]*(\d+)', text, re.IGNORECASE)
    if hr_match:
        hr = int(hr_match.group(1))
        if hr > 100:
            hr_high = True
    
    # Try to extract BP systolic value
    bp_match = re.search(r'bp[:\s]*(\d+)', text, re.IGNORECASE) or \
               re.search(r'blood\s*pressure[:\s]*(\d+)', text, re.IGNORECASE) or \
               re.search(r'(\d+)\s*/\s*\d+', text)
    if bp_match:
        sbp = int(bp_match.group(1))
        if sbp < 100:
            bp_low = True
    
    return {"hr_high": hr_high, "bp_low": bp_low}


# =============================================================================
# SYMPTOM DEFINITIONS
# =============================================================================

SYMPTOMS: Dict[str, SymptomDef] = {}


# -----------------------------------------------------------------------------
# EMERGENCY SYMPTOMS
# -----------------------------------------------------------------------------

# URG-101: Trouble Breathing
def _eval_breathing(answers: Dict[str, Any]) -> LogicResult:
    if answers.get('q1') is True:
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.CALL_911,
            triage_message='Patient reports Trouble Breathing or Shortness of Breath.'
        )
    return LogicResult(action='continue')

SYMPTOMS['URG-101'] = SymptomDef(
    id='URG-101',
    name='Trouble Breathing',
    category=SymptomCategory.EMERGENCY,
    screening_questions=[
        Question(
            id='q1',
            text='Are you having Trouble Breathing or Shortness of Breath right now?',
            input_type=InputType.YES_NO
        )
    ],
    evaluate_screening=_eval_breathing
)


# URG-102: Chest Pain (EMERGENCY ONLY - hidden, triggered from Pain module)
def _eval_chest_pain(answers: Dict[str, Any]) -> LogicResult:
    if answers.get('q1') is True:
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.CALL_911,
            triage_message='Patient reports Chest Pain.'
        )
    return LogicResult(action='continue')

SYMPTOMS['URG-102'] = SymptomDef(
    id='URG-102',
    name='Chest Pain',
    category=SymptomCategory.EMERGENCY,
    hidden=True,
    screening_questions=[
        Question(
            id='q1',
            text='Are you having Chest pain?',
            input_type=InputType.YES_NO
        )
    ],
    evaluate_screening=_eval_chest_pain
)


# URG-103: Bleeding / Bruising
def _eval_bleeding(answers: Dict[str, Any]) -> LogicResult:
    # CRITICAL: Non-stop bleeding with pressure → CALL 911 (highest priority)
    if answers.get('pressure') is True:
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.CALL_911,
            triage_message='Call 911 right now. Bleeding that will not stop with pressure requires immediate emergency care.'
        )
    # ANY blood in stool or urine → Contact care team or ED (NOT 911 per spec)
    if answers.get('stool_urine') is True:
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message='Contact your care team or go to the emergency department. Blood in stool or urine requires prompt medical evaluation.'
        )
    # No bleeding concerns - just bruising
    return LogicResult(
        action='stop',
        triage_level=TriageLevel.NONE,
        triage_message='Bruising reported without bleeding concerns. Monitor and report any changes to your care team.'
    )

SYMPTOMS['URG-103'] = SymptomDef(
    id='URG-103',
    name='Bleeding / Bruising',
    category=SymptomCategory.EMERGENCY,
    screening_questions=[
        Question(
            id='pressure',
            text="Are you bleeding and the bleeding won't stop with pressure?",
            input_type=InputType.YES_NO
        ),
        Question(
            id='stool_urine',
            text='Do you have any blood in your stool or urine?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='injury',
            text='Did you injure yourself?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='thinners',
            text='Are you on blood thinners?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='location',
            text='Is the bruising in one area or all over your body?',
            input_type=InputType.CHOICE,
            options=[
                create_option('One area', 'one'),
                create_option('All over', 'all')
            ]
        )
    ],
    evaluate_screening=_eval_bleeding
)


# URG-107: Fainting / Syncope
def _eval_fainting(answers: Dict[str, Any]) -> LogicResult:
    if answers.get('faint') is True:
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.CALL_911,
            triage_message='Patient reports fainting or near-fainting episode.'
        )
    return LogicResult(action='continue')

SYMPTOMS['URG-107'] = SymptomDef(
    id='URG-107',
    name='Fainting / Syncope',
    category=SymptomCategory.EMERGENCY,
    screening_questions=[
        Question(
            id='faint',
            text='Have you fainted or felt like you were going to faint?',
            input_type=InputType.YES_NO
        )
    ],
    evaluate_screening=_eval_fainting
)


# URG-108: Altered Mental Status
def _eval_mental_status(answers: Dict[str, Any]) -> LogicResult:
    if answers.get('confused') is True:
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.CALL_911,
            triage_message='Patient reports confusion, disorientation, or sudden change.'
        )
    return LogicResult(action='continue')

SYMPTOMS['URG-108'] = SymptomDef(
    id='URG-108',
    name='Altered Mental Status',
    category=SymptomCategory.EMERGENCY,
    screening_questions=[
        Question(
            id='confused',
            text='Are you feeling confused, disoriented, or having trouble speaking?',
            input_type=InputType.YES_NO
        )
    ],
    evaluate_screening=_eval_mental_status
)


# -----------------------------------------------------------------------------
# COMMON SIDE EFFECTS
# -----------------------------------------------------------------------------

# FEV-202: Fever
def _eval_fever(answers: Dict[str, Any]) -> LogicResult:
    temp = answers.get('temp')
    meds = answers.get('fever_meds')
    
    if meds is None:
        return LogicResult(action='continue')
    
    try:
        t = float(temp) if temp else 0
    except (ValueError, TypeError):
        t = 0
    
    # Low grade (≤100.3)
    if t <= 100.3:
        message = f"Temperature {t}°F is below fever threshold (100.3°F). "
        if meds and meds != 'none':
            detail = answers.get('fever_meds_detail', '')
            message += f"Patient taking {meds}{': ' + detail if detail else ''}."
        else:
            message += 'No fever medications taken.'
        message += ' Continue to monitor temperature.'
        return LogicResult(action='stop', triage_level=TriageLevel.NONE, triage_message=message)
    
    # High grade (>100.3)
    if t > 100.3:
        if 'high_temp_symptoms' not in answers:
            return LogicResult(action='continue')
        
        symps = answers.get('high_temp_symptoms', [])
        duration = answers.get('fever_duration', 'unknown')
        
        message = f"Fever {t}°F (Duration: {duration}). "
        if meds and meds != 'none':
            detail = answers.get('fever_meds_detail', '')
            message += f"Taking {meds}{': ' + detail if detail else ''}. "
        else:
            message += 'No fever medications taken. '
        
        # Check for concerning symptoms
        if symps and 'none' not in symps:
            filtered = [s for s in symps if s != 'none']
            message += f"Associated symptoms: {', '.join(filtered)}."
            return LogicResult(action='stop', triage_level=TriageLevel.NOTIFY_CARE_TEAM, triage_message=message)
        
        message += 'No additional symptoms reported.'
        return LogicResult(action='stop', triage_level=TriageLevel.NOTIFY_CARE_TEAM, triage_message=message)
    
    return LogicResult(action='continue')

SYMPTOMS['FEV-202'] = SymptomDef(
    id='FEV-202',
    name='Fever',
    category=SymptomCategory.COMMON,
    screening_questions=[
        Question(
            id='temp',
            text='Fever can be worrying. What is your temperature? (Enter number, e.g., 101.5)',
            input_type=InputType.NUMBER
        ),
        Question(
            id='fever_duration',
            text='How long have you had this fever?',
            input_type=InputType.CHOICE,
            options=[
                create_option('Just started today', 'today'),
                create_option('1-2 days', '1-2d'),
                create_option('3+ days', '3+d')
            ],
            condition=lambda a: float(a.get('temp', 0) or 0) > 100.3
        ),
        Question(
            id='fever_meds',
            text='What medications have you taken to lower your temperature?',
            input_type=InputType.CHOICE,
            options=[
                create_option('Tylenol (Acetaminophen)', 'tylenol'),
                create_option('Advil/Motrin (Ibuprofen)', 'ibuprofen'),
                create_option('Aspirin', 'aspirin'),
                create_option('Other medication', 'other'),
                create_option('None - I have not taken anything', 'none')
            ]
        ),
        Question(
            id='fever_meds_detail',
            text='What did you take and how often?',
            input_type=InputType.TEXT,
            condition=lambda a: a.get('fever_meds') and a.get('fever_meds') != 'none'
        ),
        Question(
            id='high_temp_symptoms',
            text='Are you experiencing any of these additional symptoms?',
            input_type=InputType.MULTISELECT,
            options=[
                create_option('Heart rate > 100', 'hr'),
                create_option('Nausea', 'nausea'),
                create_option('Vomiting', 'vomit'),
                create_option('Abdominal Pain', 'abd_pain'),
                create_option('Diarrhea', 'diarrhea'),
                create_option('Port Redness', 'port'),
                create_option('Cough', 'cough'),
                create_option('Dizziness', 'dizzy'),
                create_option('Confusion', 'confusion'),
                create_option('Burning with urination', 'burning'),
                create_option('Chills or shaking', 'chills'),
                create_option('Other', 'other'),
                create_option('None of these', 'none')
            ],
            condition=lambda a: float(a.get('temp', 0) or 0) > 100.3
        ),
        Question(
            id='high_temp_symptoms_other',
            text='Please describe the other symptom:',
            input_type=InputType.TEXT,
            condition=lambda a: float(a.get('temp', 0) or 0) > 100.3 and 'other' in (a.get('high_temp_symptoms') or [])
        ),
        Question(
            id='fever_intake',
            text='Have you been able to eat/drink normally?',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(ORAL_INTAKE_OPTIONS),
            condition=lambda a: float(a.get('temp', 0) or 0) > 100.3
        ),
        Question(
            id='fever_adl',
            text='Are you able to perform daily self care like bathing, using the toilet, eating independently?',
            input_type=InputType.YES_NO,
            condition=lambda a: float(a.get('temp', 0) or 0) > 100.3
        )
    ],
    evaluate_screening=_eval_fever
)


# NAU-203: Nausea
def _eval_nausea(answers: Dict[str, Any]) -> LogicResult:
    intake = answers.get('intake')
    days = answers.get('days')
    trend = answers.get('trend')
    severity = answers.get('severity_post_meds')  # Check post-med severity
    severity_no_meds = answers.get('severity_no_meds')  # Check if not taking meds
    
    # Get effective severity (from meds or no-meds path)
    effective_severity = severity or severity_no_meds
    
    # Alert: Oral intake "barely" or "none"
    intake_bad = intake in ['none', 'barely']
    
    # Alert: SEVERE nausea (post-meds or not taking meds)
    severe_nausea = effective_severity == 'sev'
    
    # Per spec: Alert if MODERATE + ≥3 days + worsening/same (not improving)
    moderate_chronic_worsening = (
        effective_severity == 'mod' and 
        days == '>3d' and 
        trend == 'bad'  # 'bad' = worsening or same
    )
    
    if intake_bad or severe_nausea or moderate_chronic_worsening:
        reasons = []
        if intake_bad:
            reasons.append(f'Oral intake: {intake}')
        if severe_nausea:
            reasons.append('Severe nausea despite medication')
        if moderate_chronic_worsening:
            reasons.append('Moderate nausea for ≥3 days and worsening/same')
        return LogicResult(
            action='continue',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message=f"Nausea alert: {', '.join(reasons)}. Please contact your care team."
        )
    return LogicResult(action='continue')

def _eval_nausea_followup(answers: Dict[str, Any]) -> LogicResult:
    if answers.get('vomiting_check') is True:
        return LogicResult(action='branch', branch_to_symptom_id='VOM-204')
    
    symps = answers.get('dehydration_signs', [])
    dehy_keys = ['dark_urine', 'less_urine', 'thirsty', 'lightheaded']
    
    # Check vitals
    if 'vitals_known' in symps and answers.get('vitals_input'):
        vitals = parse_vitals_from_text(answers['vitals_input'])
        if vitals['hr_high'] or vitals['bp_low']:
            return LogicResult(action='branch', branch_to_symptom_id='DEH-201')
    
    if any(s in dehy_keys for s in symps):
        return LogicResult(action='branch', branch_to_symptom_id='DEH-201')
    
    return LogicResult(action='continue')

SYMPTOMS['NAU-203'] = SymptomDef(
    id='NAU-203',
    name='Nausea',
    category=SymptomCategory.COMMON,
    screening_questions=[
        Question(
            id='days',
            text="I'm sorry to hear you're feeling nauseous. How long has this been going on?",
            input_type=InputType.CHOICE,
            options=[
                create_option('Less than a day', '<1'),
                create_option('Last 24 hours', '24h'),
                create_option('2-3 days', '2-3d'),
                create_option('>3 days', '>3d')
            ]
        ),
        Question(
            id='trend',
            text='Is the nausea the same or worsening?',
            input_type=InputType.CHOICE,
            options=[
                create_option('Worsening/Same', 'bad'),
                create_option('Improving', 'good')
            ],
            condition=lambda a: a.get('days') == '>3d'
        ),
        Question(
            id='intake',
            text='How is your oral intake?',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(ORAL_INTAKE_OPTIONS)
        ),
        Question(
            id='meds',
            text='What anti-nausea medications are you taking?',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(MEDS_NAUSEA)
        ),
        Question(
            id='med_freq',
            text='How often are you taking these medications?',
            input_type=InputType.TEXT,
            condition=lambda a: a.get('meds') == 'other'
        ),
        Question(
            id='severity_post_meds',
            text='Rate your nausea after taking medication:',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(SEVERITY_OPTIONS),
            condition=lambda a: a.get('meds') and a.get('meds') != 'none'
        ),
        Question(
            id='severity_no_meds',
            text='Rate your nausea:',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(SEVERITY_OPTIONS),
            condition=lambda a: a.get('meds') == 'none'
        )
    ],
    evaluate_screening=_eval_nausea,
    follow_up_questions=[
        Question(
            id='vomiting_check',
            text='Have you vomited?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='abd_pain',
            text='Do you have abdominal pain or cramping?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='dehydration_signs',
            text='Any signs of dehydration?',
            input_type=InputType.MULTISELECT,
            options=opts_from_dicts(DEHYDRATION_SIGNS_OPTIONS)
        ),
        Question(
            id='vitals_input',
            text='Please enter your Heart Rate and/or Blood Pressure (e.g., HR: 95, BP: 110/70):',
            input_type=InputType.TEXT,
            condition=lambda a: 'vitals_known' in (a.get('dehydration_signs') or [])
        ),
        Question(
            id='fluids_kept_down',
            text='Have you been able to keep fluids or food down for more than 24 hours?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='adl',
            text='Are you able to perform daily self care like bathing and dressing yourself?',
            input_type=InputType.YES_NO
        )
    ],
    evaluate_follow_up=_eval_nausea_followup
)


# VOM-204: Vomiting
def _eval_vomiting(answers: Dict[str, Any]) -> LogicResult:
    vom_freq = answers.get('vom_freq')
    intake = answers.get('intake')
    severity = answers.get('severity_post_med')
    days = answers.get('days')
    trend = answers.get('vom_trend')
    
    # Parse days as number
    try:
        days_num = float(days) if days else 0
    except (ValueError, TypeError):
        days_num = 0
    
    # Alert criteria per spec:
    # - >6 episodes in 24 hours
    # - No oral intake for ≥12 hours
    # - Vomiting rated severe despite medication
    if vom_freq == 'high' or intake == 'none' or severity == 'sev':
        reasons = []
        if vom_freq == 'high':
            reasons.append('>6 episodes in 24 hours')
        if intake == 'none':
            reasons.append('No oral intake for 12+ hours')
        if severity == 'sev':
            reasons.append('Severe vomiting despite medication')
        return LogicResult(
            action='continue',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message=f"Vomiting alert: {', '.join(reasons)}. Please contact your care team immediately."
        )
    
    # Per spec: Vomiting rated moderate for ≥3 days and worsening or same
    if severity == 'mod' and days_num >= 3 and trend in ['worse', 'same']:
        return LogicResult(
            action='continue',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message=f"Moderate vomiting for {int(days_num)} days ({trend}). Please contact your care team."
        )
    
    return LogicResult(action='continue')

def _eval_vomiting_followup(answers: Dict[str, Any]) -> LogicResult:
    """Evaluate vomiting follow-up with dehydration checks."""
    urine_dark = answers.get('vom_urine_dark') is True
    urine_less = answers.get('vom_urine_less') is True
    thirsty = answers.get('vom_thirsty') is True
    lightheaded = answers.get('vom_lightheaded') is True
    vitals_text = answers.get('vom_vitals', '')
    
    # Parse vitals if provided
    vitals = parse_vitals_from_text(vitals_text) if vitals_text else {'hr_high': False, 'bp_low': False}
    
    # Check for dehydration signs
    dehy_signs = []
    if urine_dark:
        dehy_signs.append('Dark urine')
    if urine_less:
        dehy_signs.append('Reduced urination')
    if thirsty:
        dehy_signs.append('Very thirsty')
    if lightheaded:
        dehy_signs.append('Lightheaded')
    if vitals['hr_high']:
        dehy_signs.append('HR ≥100')
    if vitals['bp_low']:
        dehy_signs.append('SBP ≤100')
    
    if dehy_signs:
        return LogicResult(
            action='branch',
            branch_to_symptom_id='DEH-201',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message=f"Dehydration signs with vomiting: {', '.join(dehy_signs)}."
        )
    
    return LogicResult(action='continue')

SYMPTOMS['VOM-204'] = SymptomDef(
    id='VOM-204',
    name='Vomiting',
    category=SymptomCategory.COMMON,
    screening_questions=[
        Question(
            id='days',
            text='How many days have you been vomiting?',
            input_type=InputType.NUMBER
        ),
        # Per spec: Ask trend for ≥3 days to check for moderate + worsening/same
        Question(
            id='vom_trend',
            text='Is the vomiting worsening or the same?',
            input_type=InputType.CHOICE,
            options=[
                create_option('Worsening', 'worse'),
                create_option('Same', 'same'),
                create_option('Improving', 'better')
            ],
            condition=lambda a: _days_at_least(a.get('days'), 3)
        ),
        Question(
            id='vom_freq',
            text='How many times have you vomited in the last 24 hours?',
            input_type=InputType.CHOICE,
            options=[
                create_option('1-2 times', 'low'),
                create_option('3-5 times', 'med'),
                create_option('>6 times', 'high')
            ]
        ),
        Question(
            id='intake',
            text='How is your oral intake over the last 12 hours?',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(ORAL_INTAKE_OPTIONS_12H)
        ),
        Question(
            id='meds',
            text='What medications for vomiting are you taking?',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(MEDS_NAUSEA)
        ),
        Question(
            id='med_freq',
            text='How often are you taking them?',
            input_type=InputType.TEXT,
            condition=lambda a: a.get('meds') == 'other'
        ),
        Question(
            id='severity_post_med',
            text='Rate your vomiting after taking medication:',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(SEVERITY_OPTIONS),
            condition=lambda a: a.get('meds') and a.get('meds') != 'none'
        )
    ],
    evaluate_screening=_eval_vomiting,
    follow_up_questions=[
        Question(
            id='abd_pain',
            text='Do you have abdominal pain or cramping?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='adl',
            text='Are you able to perform daily self care like bathing and dressing yourself?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='vom_urine_dark',
            text='Is your urine dark?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='vom_urine_less',
            text='Is the amount of urine a lot less over the last 12 hours?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='vom_thirsty',
            text='Are you very thirsty?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='vom_lightheaded',
            text='Are you feeling lightheaded?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='vom_vitals',
            text='Do you know what your heart rate and blood pressure is? If so, please state.',
            input_type=InputType.TEXT
        )
    ],
    evaluate_follow_up=_eval_vomiting_followup
)


# DIA-205: Diarrhea
def _eval_diarrhea(answers: Dict[str, Any]) -> LogicResult:
    stools = answers.get('stools')
    types = answers.get('stool_type', [])
    dehy = answers.get('dehydration_signs', [])
    days = answers.get('preface')
    diarrhea_severity = answers.get('severity_post_med')  # Diarrhea severity post-meds
    diarrhea_severity_no_meds = answers.get('severity_no_meds')  # Diarrhea severity without meds
    intake = answers.get('intake')
    abd_sev = answers.get('abd_pain_sev')
    trend = answers.get('trend')
    
    try:
        stools_num = float(stools) if stools else 0
        days_num = float(days) if days else 0
    except (ValueError, TypeError):
        stools_num = 0
        days_num = 0
    
    # Combine diarrhea severity (post-meds or no meds)
    effective_severity = diarrhea_severity or diarrhea_severity_no_meds
    
    # Alert: >5 loose stools/day
    if stools_num > 5:
        return LogicResult(action='continue', triage_level=TriageLevel.NOTIFY_CARE_TEAM, triage_message='>5 loose stools/day reported.')
    
    # Alert: Bloody/Black/Mucus stool
    if any(t in ['black', 'blood', 'mucus'] for t in types):
        return LogicResult(action='continue', triage_level=TriageLevel.NOTIFY_CARE_TEAM, triage_message='Bloody/Black/Mucus Stool reported.')
    
    # Alert: Moderate DIARRHEA ≥ 3 days AND (Worsening/Same) - per oncologist spec
    if effective_severity == 'mod' and days_num >= 3 and trend == 'bad':
        return LogicResult(action='continue', triage_level=TriageLevel.NOTIFY_CARE_TEAM, triage_message='Moderate diarrhea for ≥3 days and worsening/same.')
    
    # Alert: Moderate/Severe abdominal pain
    if abd_sev in ['mod', 'sev']:
        return LogicResult(action='continue', triage_level=TriageLevel.NOTIFY_CARE_TEAM, triage_message=f'{abd_sev.title()} abdominal pain with diarrhea.')
    
    # Alert: Dehydration signs or no intake
    dehy_actual = [d for d in dehy if d not in ['none', 'vitals_known']]
    if dehy_actual or intake == 'none':
        return LogicResult(action='continue', triage_level=TriageLevel.NOTIFY_CARE_TEAM, triage_message='Dehydration signs or No Intake.')
    
    # Alert: Severe diarrhea (with or without meds)
    if effective_severity == 'sev':
        return LogicResult(action='continue', triage_level=TriageLevel.NOTIFY_CARE_TEAM, triage_message='Severe Diarrhea reported.')
    
    return LogicResult(action='continue')

def _eval_diarrhea_followup(answers: Dict[str, Any]) -> LogicResult:
    dehy = answers.get('dehydration_signs', [])
    dehy_keys = ['dark_urine', 'less_urine', 'thirsty', 'lightheaded']
    
    # Check vitals
    if 'vitals_known' in dehy and answers.get('vitals_input'):
        vitals = parse_vitals_from_text(answers['vitals_input'])
        if vitals['hr_high'] or vitals['bp_low']:
            return LogicResult(action='branch', branch_to_symptom_id='DEH-201')
    
    if any(s in dehy_keys for s in dehy):
        return LogicResult(action='branch', branch_to_symptom_id='DEH-201')
    
    return LogicResult(action='continue')

SYMPTOMS['DIA-205'] = SymptomDef(
    id='DIA-205',
    name='Diarrhea',
    category=SymptomCategory.COMMON,
    screening_questions=[
        Question(
            id='preface',
            text="Now let's talk about your diarrhea. How many days have you had diarrhea?",
            input_type=InputType.NUMBER
        ),
        Question(
            id='trend',
            text='Is it worsening or the same?',
            input_type=InputType.CHOICE,
            options=[
                create_option('Worsening/Same', 'bad'),
                create_option('Improving', 'good')
            ],
            condition=lambda a: float(a.get('preface', 0) or 0) >= 3
        ),
        Question(
            id='stools',
            text='How many loose stools have you had in the last 24 hours?',
            input_type=InputType.NUMBER
        ),
        Question(
            id='stool_type',
            text='Are you experiencing any of these?',
            input_type=InputType.MULTISELECT,
            options=[
                create_option('My stool is black', 'black'),
                create_option('My stool has blood', 'blood'),
                create_option('My stool has mucus', 'mucus'),
                create_option('Other', 'other'),
                create_option('None of the above', 'none')
            ]
        ),
        Question(
            id='stool_type_other',
            text='Please describe:',
            input_type=InputType.TEXT,
            condition=lambda a: 'other' in (a.get('stool_type') or [])
        ),
        Question(
            id='abd_pain',
            text='Are you having any abdominal pain or cramping?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='abd_pain_sev',
            text='Rate your abdominal pain:',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(SEVERITY_OPTIONS),
            condition=lambda a: a.get('abd_pain') is True
        ),
        Question(
            id='meds',
            text='What medications for diarrhea are you taking?',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(MEDS_DIARRHEA)
        ),
        Question(
            id='med_freq',
            text='How often are you taking them?',
            input_type=InputType.TEXT,
            condition=lambda a: a.get('meds') == 'other'
        ),
        Question(
            id='severity_post_med',
            text='Rate your diarrhea after medication:',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(SEVERITY_OPTIONS),
            condition=lambda a: a.get('meds') and a.get('meds') != 'none'
        ),
        Question(
            id='severity_no_meds',
            text='Rate your diarrhea:',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(SEVERITY_OPTIONS),
            condition=lambda a: a.get('meds') == 'none'
        ),
        Question(
            id='dehydration_signs',
            text='Any signs of dehydration?',
            input_type=InputType.MULTISELECT,
            options=opts_from_dicts(DEHYDRATION_SIGNS_OPTIONS)
        ),
        Question(
            id='vitals_input',
            text='Please enter your Heart Rate and/or Blood Pressure (e.g., HR: 95, BP: 110/70):',
            input_type=InputType.TEXT,
            condition=lambda a: 'vitals_known' in (a.get('dehydration_signs') or [])
        ),
        Question(
            id='intake',
            text='Able to eat/drink normally?',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(ORAL_INTAKE_OPTIONS)
        )
    ],
    evaluate_screening=_eval_diarrhea,
    follow_up_questions=[
        Question(
            id='adl',
            text='Are you able to do daily activities such as household work, eating and moving around?',
            input_type=InputType.YES_NO
        )
    ],
    evaluate_follow_up=_eval_diarrhea_followup
)


# DEH-201: Dehydration (Hidden - triggered by cross-reference)
def _eval_dehydration(answers: Dict[str, Any]) -> LogicResult:
    vitals = parse_vitals_from_text(answers.get('vitals_known', '') or '')
    thirsty = answers.get('thirsty') is True
    lightheaded = answers.get('lightheaded') is True
    less_urine = answers.get('urine_amt') is True
    dark_urine = answers.get('urine_color') == 'dark'
    
    if vitals['hr_high'] or vitals['bp_low'] or thirsty or lightheaded or less_urine or dark_urine:
        reasons = []
        if vitals['hr_high']:
            reasons.append('HR ≥100')
        if vitals['bp_low']:
            reasons.append('SBP ≤100')
        if thirsty:
            reasons.append('Very thirsty')
        if lightheaded:
            reasons.append('Lightheaded')
        if less_urine:
            reasons.append('Reduced urine output')
        if dark_urine:
            reasons.append('Dark urine')
        
        message = 'Dehydration signs detected: ' + ', '.join(reasons) + '.'
        return LogicResult(action='continue', triage_level=TriageLevel.NOTIFY_CARE_TEAM, triage_message=message)
    
    return LogicResult(action='continue')

def _eval_dehydration_followup(answers: Dict[str, Any]) -> LogicResult:
    if answers.get('vomiting_check') is True:
        return LogicResult(action='branch', branch_to_symptom_id='VOM-204')
    if answers.get('diarrhea_check') is True:
        return LogicResult(action='branch', branch_to_symptom_id='DIA-205')
    if answers.get('fever_check') is True:
        return LogicResult(action='branch', branch_to_symptom_id='FEV-202')
    return LogicResult(action='continue')

SYMPTOMS['DEH-201'] = SymptomDef(
    id='DEH-201',
    name='Dehydration',
    category=SymptomCategory.COMMON,
    hidden=True,
    screening_questions=[
        Question(
            id='urine_color',
            text='What color is your urine?',
            input_type=InputType.CHOICE,
            options=[
                create_option('Clear', 'clear'),
                create_option('Pale Yellow', 'pale'),
                create_option('Dark', 'dark')
            ]
        ),
        Question(
            id='urine_amt',
            text='Is the amount of urine a lot less over the last 12 hours?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='thirsty',
            text='Are you feeling very thirsty?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='lightheaded',
            text='Are you feeling lightheaded?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='vitals_known',
            text='Do you know your heart rate or blood pressure? Please state if yes.',
            input_type=InputType.TEXT
        )
    ],
    evaluate_screening=_eval_dehydration,
    follow_up_questions=[
        Question(
            id='vomiting_check',
            text='Have you been vomiting?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='diarrhea_check',
            text='Have you had diarrhea?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='intake',
            text='How is your oral intake (eating and drinking)?',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(ORAL_INTAKE_OPTIONS)
        ),
        Question(
            id='fever_check',
            text='Do you have a fever?',
            input_type=InputType.YES_NO
        )
    ],
    evaluate_follow_up=_eval_dehydration_followup
)


# -----------------------------------------------------------------------------
# PAIN MODULE (Router)
# -----------------------------------------------------------------------------

# PAI-213: Pain (Location-based routing)
def _eval_pain(answers: Dict[str, Any]) -> LogicResult:
    locations = answers.get('loc', [])
    
    # EMERGENCY: Chest Pain triggers 911
    if 'chest' in locations:
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.CALL_911,
            triage_message='Patient reports Chest Pain. Call 911 immediately.'
        )
    
    # Route to specific modules
    if 'port' in locations:
        return LogicResult(action='branch', branch_to_symptom_id='URG-114')
    if 'head' in locations:
        return LogicResult(action='branch', branch_to_symptom_id='HEA-210')
    if 'legs' in locations:
        return LogicResult(action='branch', branch_to_symptom_id='LEG-208')
    if 'stomach' in locations:
        return LogicResult(action='branch', branch_to_symptom_id='ABD-211')
    if 'urinary' in locations:
        return LogicResult(action='branch', branch_to_symptom_id='URI-211')
    if 'joints' in locations or 'general' in locations:
        return LogicResult(action='branch', branch_to_symptom_id='JMP-212')
    if 'mouth' in locations:
        return LogicResult(action='branch', branch_to_symptom_id='MSO-208')
    if 'nerve' in locations:
        return LogicResult(action='branch', branch_to_symptom_id='NEU-216')
    
    # "Other" selected - continue with follow-up
    if 'other' in locations:
        return LogicResult(action='continue')
    
    return LogicResult(action='continue')

def _eval_pain_followup(answers: Dict[str, Any]) -> LogicResult:
    temp = answers.get('pain_temp')
    severity = answers.get('severity')
    interfere = answers.get('interfere')
    controlled = answers.get('controlled')
    
    try:
        t = float(temp) if temp else 0
    except (ValueError, TypeError):
        t = 0
    
    fever = t >= 100.3
    
    if severity == 'sev' or interfere is True or fever or controlled is False:
        reasons = []
        if severity == 'sev':
            reasons.append('Severe pain')
        if interfere is True:
            reasons.append('Interferes with daily activities')
        if fever:
            reasons.append(f'Temp {t}°F')
        if controlled is False:
            reasons.append('Not controlled with usual meds')
        
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message=f"Pain alert: {', '.join(reasons)}. Contact provider."
        )
    
    return LogicResult(
        action='stop',
        triage_level=TriageLevel.NONE,
        triage_message='Pain reported - manageable with current treatment.'
    )

SYMPTOMS['PAI-213'] = SymptomDef(
    id='PAI-213',
    name='Pain',
    category=SymptomCategory.OTHER,
    screening_questions=[
        Question(
            id='loc',
            text='Where does it hurt?',
            input_type=InputType.MULTISELECT,
            options=[
                create_option('⚠️ Chest (EMERGENCY)', 'chest'),
                create_option('Port/IV Site', 'port'),
                create_option('Head', 'head'),
                create_option('Leg/Calf (one side)', 'legs'),
                create_option('Abdomen/Stomach', 'stomach'),
                create_option('Urinary/Pelvic', 'urinary'),
                create_option('Joints/Muscles', 'joints'),
                create_option('General Aches', 'general'),
                create_option('Nerve (Burning/Tingling)', 'nerve'),
                create_option('Mouth/Throat', 'mouth'),
                create_option('Other', 'other')
            ]
        ),
        Question(
            id='loc_other',
            text='Please describe the location:',
            input_type=InputType.TEXT,
            condition=lambda a: 'other' in (a.get('loc') or [])
        )
    ],
    evaluate_screening=_eval_pain,
    follow_up_questions=[
        Question(
            id='severity',
            text='Rate your pain:',
            input_type=InputType.CHOICE,
            options=[
                create_option('Mild (1-3)', 'mild'),
                create_option('Moderate (4-6)', 'mod'),
                create_option('Severe (7-10)', 'sev')
            ]
        ),
        Question(
            id='interfere',
            text='Does the pain interfere with your daily activities or self-care?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='pain_temp',
            text='What is your temperature?',
            input_type=InputType.NUMBER
        ),
        Question(
            id='controlled',
            text='Is the pain controlled with your usual medications?',
            input_type=InputType.YES_NO
        )
    ],
    evaluate_follow_up=_eval_pain_followup
)


# -----------------------------------------------------------------------------
# OTHER SYMPTOMS (Additional key modules)
# -----------------------------------------------------------------------------

# CON-210: Constipation
def _eval_constipation(answers: Dict[str, Any]) -> LogicResult:
    days_bm = answers.get('days_bm')
    passing_gas = answers.get('passing_gas')
    days_gas = answers.get('days_gas')
    discomfort = answers.get('discomfort')
    meds = answers.get('meds')
    dehy_signs = answers.get('dehydration_signs', [])
    abd_pain = answers.get('abd_pain')
    abd_pain_sev = answers.get('abd_pain_sev')
    
    try:
        days_bm_num = float(days_bm) if days_bm else 0
        days_gas_num = float(days_gas) if days_gas and passing_gas is False else 0
    except (ValueError, TypeError):
        days_bm_num = 0
        days_gas_num = 0
    
    # Check for dehydration signs
    dehy_actual = [d for d in dehy_signs if d not in ['none', 'vitals_known']]
    has_dehydration = len(dehy_actual) > 0
    
    # Check for moderate-severe abdominal pain
    has_bad_abd_pain = abd_pain_sev in ['mod', 'sev']
    
    # Alert conditions per oncologist spec:
    # >2 days since BM OR >2 days since gas OR Severe discomfort 
    # OR signs of dehydration OR severe constipation OR moderate-severe abdominal pain
    if (days_bm_num > 2 or days_gas_num > 2 or discomfort == 'sev' or 
        has_dehydration or has_bad_abd_pain):
        reasons = []
        if days_bm_num > 2:
            reasons.append(f'No BM for {int(days_bm_num)} days')
        if days_gas_num > 2:
            reasons.append(f'No gas for {int(days_gas_num)} days')
        if discomfort == 'sev':
            reasons.append('Severe discomfort')
        if has_dehydration:
            reasons.append(f"Dehydration signs: {', '.join(dehy_actual)}")
        if has_bad_abd_pain:
            reasons.append(f'{abd_pain_sev.title()} abdominal pain')
        
        if meds and meds != 'none':
            meds_freq = answers.get('meds_freq', '')
            reasons.append(f"Currently taking: {meds}{' - ' + meds_freq if meds_freq else ''}")
        else:
            reasons.append('Not taking constipation medication')
        
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message=f"Constipation alert: {'. '.join(reasons)}."
        )
    
    return LogicResult(
        action='stop',
        triage_level=TriageLevel.NONE,
        triage_message='Mild constipation - continue monitoring.'
    )

SYMPTOMS['CON-210'] = SymptomDef(
    id='CON-210',
    name='Constipation',
    category=SymptomCategory.OTHER,
    screening_questions=[
        Question(
            id='days_bm',
            text='How many days has it been since your last bowel movement?',
            input_type=InputType.NUMBER
        ),
        Question(
            id='passing_gas',
            text='Are you passing gas?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='days_gas',
            text='How many days has it been since you passed gas?',
            input_type=InputType.NUMBER,
            condition=lambda a: a.get('passing_gas') is False
        ),
        Question(
            id='discomfort',
            text='Rate your discomfort:',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(SEVERITY_OPTIONS)
        ),
        Question(
            id='abd_pain',
            text='Are you having abdominal pain?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='abd_pain_sev',
            text='Rate your abdominal pain:',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(SEVERITY_OPTIONS),
            condition=lambda a: a.get('abd_pain') is True
        ),
        Question(
            id='dehydration_signs',
            text='Any signs of dehydration?',
            input_type=InputType.MULTISELECT,
            options=opts_from_dicts(DEHYDRATION_SIGNS_OPTIONS)
        ),
        Question(
            id='meds',
            text='What medications are you taking for constipation?',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(MEDS_CONSTIPATION)
        ),
        Question(
            id='meds_freq',
            text='How often are you taking it?',
            input_type=InputType.TEXT,
            condition=lambda a: a.get('meds') == 'other'
        )
    ],
    evaluate_screening=_eval_constipation
)


# FAT-206: Fatigue / Weakness
def _eval_fatigue(answers: Dict[str, Any]) -> LogicResult:
    interfere = answers.get('interfere')
    severity = answers.get('severity')
    days = answers.get('days')
    trend = answers.get('trend')
    
    if interfere is True:
        return LogicResult(
            action='continue',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message='Fatigue interferes with daily tasks.'
        )
    
    if severity == 'sev':
        return LogicResult(
            action='continue',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message='Severe fatigue reported.'
        )
    
    if severity == 'mod':
        try:
            days_num = float(days) if days else 0
        except (ValueError, TypeError):
            days_num = 0
        
        if days_num >= 3 and trend != 'better':
            return LogicResult(
                action='continue',
                triage_level=TriageLevel.NOTIFY_CARE_TEAM,
                triage_message=f"Moderate fatigue for {int(days_num)} days ({trend})."
            )
    
    return LogicResult(action='continue')

def _eval_fatigue_followup(answers: Dict[str, Any]) -> LogicResult:
    if answers.get('adl_self') is True:
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message='Fatigue affects ability to perform self-care (bathing, dressing, feeding).'
        )
    return LogicResult(action='continue')

SYMPTOMS['FAT-206'] = SymptomDef(
    id='FAT-206',
    name='Fatigue / Weakness',
    category=SymptomCategory.OTHER,
    screening_questions=[
        Question(
            id='interfere',
            text='Does your fatigue interfere with performing daily tasks?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='severity',
            text='Rate your fatigue:',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(SEVERITY_OPTIONS)
        ),
        Question(
            id='days',
            text='How many continuous days have you had this level of fatigue?',
            input_type=InputType.NUMBER,
            condition=lambda a: a.get('severity') in ['mod', 'sev']
        ),
        Question(
            id='trend',
            text='Is it getting worse, staying the same, or improving?',
            input_type=InputType.CHOICE,
            options=[
                create_option('Worse', 'worse'),
                create_option('Same', 'same'),
                create_option('Improving', 'better')
            ],
            condition=lambda a: a.get('severity') in ['mod', 'sev']
        )
    ],
    evaluate_screening=_eval_fatigue,
    follow_up_questions=[
        Question(
            id='sleep_hrs',
            text='How many hours are you sleeping in bed during the day?',
            input_type=InputType.NUMBER
        ),
        Question(
            id='worse_yesterday',
            text='Is the fatigue worsening compared to yesterday?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='adl_self',
            text='Has the fatigue affected your ability to bathe, dress, and feed yourself without help?',
            input_type=InputType.YES_NO
        )
    ],
    evaluate_follow_up=_eval_fatigue_followup
)


# NEU-216: Neuropathy (Numbness/Tingling)
def _eval_neuropathy(answers: Dict[str, Any]) -> LogicResult:
    start_date = answers.get('start_date')
    affect_function = answers.get('affect_function')
    severity = answers.get('severity')
    
    if start_date == 'today' or affect_function is True or severity == 'sev':
        reasons = []
        if start_date == 'today':
            reasons.append('New onset today')
        if affect_function is True:
            reasons.append('Affects walking/handling objects')
        if severity == 'sev':
            reasons.append('Severe symptoms')
        
        return LogicResult(
            action='continue',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message=f"Neuropathy alert: {', '.join(reasons)}. Possible chemo-induced acute neuropathy."
        )
    
    return LogicResult(action='continue')

def _eval_neuropathy_followup(answers: Dict[str, Any]) -> LogicResult:
    meds = answers.get('meds')
    meds_helping = answers.get('meds_helping')
    fine_motor = answers.get('neuro_fine_motor') is True
    worsening_spreading = answers.get('neuro_worsening') is True
    balance_issues = answers.get('neuro_balance') is True
    
    # Check for concerning signs
    if fine_motor or worsening_spreading or balance_issues:
        reasons = []
        if fine_motor:
            reasons.append('Difficulty with fine motor tasks')
        if worsening_spreading:
            reasons.append('Worsening or spreading higher')
        if balance_issues:
            reasons.append('Balance/walking issues')
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message=f"Neuropathy progression: {', '.join(reasons)}. May need dose adjustment."
        )
    
    if meds and meds != 'none' and meds_helping is False:
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message='Neuropathy medications not helping - may need adjustment.'
        )
    
    return LogicResult(
        action='stop',
        triage_level=TriageLevel.NONE,
        triage_message='Neuropathy reported. Monitor and discuss with care team.'
    )

SYMPTOMS['NEU-216'] = SymptomDef(
    id='NEU-216',
    name='Neuropathy (Numbness/Tingling)',
    category=SymptomCategory.OTHER,
    screening_questions=[
        Question(
            id='start_date',
            text='When did the numbness/tingling start?',
            input_type=InputType.CHOICE,
            options=[
                create_option('Started today', 'today'),
                create_option('1-3 days ago', '1-3d'),
                create_option('4-7 days ago', '4-7d'),
                create_option('More than a week ago', '>1w')
            ]
        ),
        Question(
            id='location',
            text='Where do you feel the numbness or tingling?',
            input_type=InputType.TEXT
        ),
        Question(
            id='affect_function',
            text='Does it affect your ability to walk or pick up objects?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='severity',
            text='Rate your symptoms:',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(SEVERITY_OPTIONS)
        ),
        Question(
            id='interfere',
            text='Does this interfere with your daily activities?',
            input_type=InputType.YES_NO
        )
    ],
    evaluate_screening=_eval_neuropathy,
    follow_up_questions=[
        Question(
            id='neuro_fine_motor',
            text='Is it hard to do things like button your shirt, type, write, turn pages, or walk long distances because of the tingling or numbness?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='neuro_worsening',
            text='Has the numbness or tingling gotten worse in the past week or started to move higher up your arms or legs?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='neuro_balance',
            text='Have you had trouble feeling the ground when walking, or felt unsteady or off balance?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='meds',
            text='Are you taking any medication for neuropathy (e.g., gabapentin, duloxetine)?',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(MEDS_NEUROPATHY)
        ),
        Question(
            id='meds_other',
            text='What medication are you taking?',
            input_type=InputType.TEXT,
            condition=lambda a: a.get('meds') == 'other'
        ),
        Question(
            id='meds_helping',
            text='Is the medication helping?',
            input_type=InputType.YES_NO,
            condition=lambda a: a.get('meds') and a.get('meds') != 'none'
        )
    ],
    evaluate_follow_up=_eval_neuropathy_followup
)


# COU-215: Cough
def _eval_cough(answers: Dict[str, Any]) -> LogicResult:
    temp = answers.get('cough_temp')
    mucus = answers.get('mucus')
    days = answers.get('days')
    adl_prevent = answers.get('cough_adl_prevent') is True
    chest_sob = answers.get('cough_chest_sob') is True
    o2_sat = answers.get('cough_o2_sat')
    severity = answers.get('cough_severity')
    
    try:
        t = float(temp) if temp else 0
    except (ValueError, TypeError):
        t = 0
    
    # Parse O2 sat if provided
    low_o2 = False
    if o2_sat:
        try:
            o2_val = float(o2_sat)
            if o2_val < 92:
                low_o2 = True
        except (ValueError, TypeError):
            pass
    
    high_temp = t >= 100.3
    blood_mucus = mucus == 'blood'
    long_duration = days in ['>1w', '>3w']
    
    # Alert conditions per oncologist doc
    if adl_prevent or chest_sob or high_temp or low_o2 or blood_mucus or long_duration or severity == 'sev':
        reasons = []
        if adl_prevent:
            reasons.append('Prevents daily activities')
        if chest_sob:
            reasons.append('Chest pain/shortness of breath')
        if high_temp:
            reasons.append(f'Temp {t}°F')
        if low_o2:
            reasons.append(f'O2 sat {o2_sat}% (<92%)')
        if blood_mucus:
            reasons.append('Blood-streaked/pink mucus')
        if long_duration:
            reasons.append('Duration > 1 week')
        if severity == 'sev':
            reasons.append('Severe cough')
        
        # Emergency if chest/sob
        if chest_sob:
            return LogicResult(
                action='branch',
                branch_to_symptom_id='URG-101',
                triage_level=TriageLevel.NOTIFY_CARE_TEAM,
                triage_message=f"Cough with concerning symptoms: {', '.join(reasons)}."
            )
        
        return LogicResult(
            action='continue',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message=f"Cough alert: {', '.join(reasons)}."
        )
    
    return LogicResult(action='continue')

def _eval_cough_followup(answers: Dict[str, Any]) -> LogicResult:
    if answers.get('exposure') is True:
        return LogicResult(
            action='continue',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message='Cough with recent exposure to respiratory illness.'
        )
    return LogicResult(action='continue')

SYMPTOMS['COU-215'] = SymptomDef(
    id='COU-215',
    name='Cough',
    category=SymptomCategory.OTHER,
    screening_questions=[
        Question(
            id='days',
            text='How long have you had this cough?',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(DURATION_OPTIONS_SHORT)
        ),
        Question(
            id='cough_temp',
            text='What is your temperature?',
            input_type=InputType.NUMBER
        ),
        Question(
            id='mucus',
            text='Are you coughing up any mucus?',
            input_type=InputType.CHOICE,
            options=[
                create_option('No', 'no'),
                create_option('Clear', 'clear'),
                create_option('Yellow-Green', 'yellow_green'),
                create_option('Blood-streaked or Pink', 'blood')
            ]
        ),
        Question(
            id='meds',
            text='What medications are you using for your cough?',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(MEDS_COUGH)
        ),
        Question(
            id='helping',
            text='Is the medication helping?',
            input_type=InputType.YES_NO,
            condition=lambda a: a.get('meds') and a.get('meds') != 'none'
        ),
        Question(
            id='cough_adl_prevent',
            text='Does the cough prevent you from doing your daily activities?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='cough_chest_sob',
            text='Do you have chest pain or shortness of breath?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='cough_o2_available',
            text='Do you have the ability to check your oxygen saturation at home?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='cough_o2_sat',
            text='What is your oxygen saturation?',
            input_type=InputType.NUMBER,
            condition=lambda a: a.get('cough_o2_available') is True
        ),
        Question(
            id='cough_severity',
            text='Rate your cough:',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(SEVERITY_OPTIONS)
        )
    ],
    evaluate_screening=_eval_cough,
    follow_up_questions=[
        Question(
            id='exposure',
            text='Have you been around anyone with a recent respiratory illness?',
            input_type=InputType.YES_NO
        )
    ],
    evaluate_follow_up=_eval_cough_followup
)


# SWE-214: Swelling
def _eval_swelling(answers: Dict[str, Any]) -> LogicResult:
    locations = answers.get('swell_loc', [])
    one_side = answers.get('swell_side')
    severity = answers.get('severity')
    onset = answers.get('swell_onset')
    associated = answers.get('swell_associated', [])
    redness = answers.get('redness') is True
    
    # EMERGENT conditions per spec
    is_one_sided = one_side == 'one'
    is_sudden = onset == 'today'
    has_critical_location = any(loc in locations for loc in ['neck_chest', 'port', 'iv_site'])
    has_sob = 'sob' in associated
    has_chest = 'chest_discomfort' in associated
    has_fever = 'fever' in associated
    has_redness = 'redness' in associated or redness
    is_severe = severity == 'sev'
    
    # Per spec: SOB with swelling → branch to URG-101 for breathing emergency
    if has_sob:
        return LogicResult(
            action='branch',
            branch_to_symptom_id='URG-101',
            triage_level=TriageLevel.CALL_911,
            triage_message='Swelling with shortness of breath. This may be an emergency.'
        )
    
    # Build reasons list for messaging
    reasons = []
    if is_one_sided:
        reasons.append('One-sided swelling')
    if is_sudden:
        reasons.append('Sudden onset')
    if has_critical_location:
        reasons.append('Neck/chest/port/IV site involvement')
    if has_chest:
        reasons.append('Chest discomfort')
    if has_fever:
        reasons.append('Fever')
    if has_redness:
        reasons.append('Redness')
    if is_severe:
        reasons.append('Severe swelling')
    
    # EMERGENT per spec: All these conditions require "Call 911 or your care team right away"
    # - One-sided swelling with sudden onset
    # - Neck/chest/port/IV site involvement
    # - Chest discomfort, fever, redness, or severe swelling
    emergent_condition = (
        (is_one_sided and is_sudden) or  # One-sided + sudden
        has_critical_location or          # Neck/chest/port/IV
        has_chest or                      # Chest discomfort
        has_fever or                      # Fever
        has_redness or                    # Redness
        is_severe                         # Severe
    )
    
    if emergent_condition:
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.CALL_911,
            triage_message=f"URGENT: Call 911 or your care team right away. {', '.join(reasons)}."
        )
    
    # One-sided OR sudden alone (not combined) - still concerning but not emergent
    if is_one_sided or is_sudden:
        return LogicResult(
            action='continue',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message=f"Swelling concern: {', '.join(reasons)}. Contact your care team."
        )
    
    # Notify: Moderate OR worsening OR >3 days OR bilateral arm/leg
    has_arm_leg = any(loc in locations for loc in ['arms_hands', 'legs_ankles'])
    is_both_sides = one_side == 'both'
    is_moderate = severity == 'mod'
    is_prolonged = onset in ['2-3d', '>3d']
    
    if is_moderate or is_prolonged or (has_arm_leg and is_both_sides):
        reasons = []
        if is_moderate:
            reasons.append('Moderate swelling')
        if is_prolonged:
            reasons.append('Duration >2 days')
        if has_arm_leg and is_both_sides:
            reasons.append('Both sides arm/leg involvement')
        return LogicResult(
            action='continue',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message=f"Swelling: {', '.join(reasons)}."
        )
    
    return LogicResult(action='continue')

def _eval_swelling_followup(answers: Dict[str, Any]) -> LogicResult:
    if answers.get('swell_clots') is True:
        return LogicResult(
            action='continue',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message='Swelling with history of blood clots - increased DVT risk.'
        )
    return LogicResult(action='continue')

SYMPTOMS['SWE-214'] = SymptomDef(
    id='SWE-214',
    name='Swelling',
    category=SymptomCategory.OTHER,
    screening_questions=[
        Question(
            id='swell_loc',
            text='Where is your swelling? (You can select more than one)',
            input_type=InputType.MULTISELECT,
            options=[
                create_option('Face or eyes', 'face_eyes'),
                create_option('Neck or chest', 'neck_chest'),
                create_option('Around my port', 'port'),
                create_option('Arm(s) or hand(s)', 'arms_hands'),
                create_option('Belly or waist', 'belly_waist'),
                create_option('Leg(s), ankle(s), or foot/feet', 'legs_ankles'),
                create_option('Near an IV site', 'iv_site'),
                create_option('Surgical area', 'surgical'),
                create_option('Other', 'other')
            ]
        ),
        Question(
            id='swell_loc_other',
            text='Please describe the location:',
            input_type=InputType.TEXT,
            condition=lambda a: 'other' in (a.get('swell_loc') or [])
        ),
        Question(
            id='swell_side',
            text='Is the swelling on one side or both?',
            input_type=InputType.CHOICE,
            options=[
                create_option('One side', 'one'),
                create_option('Both sides', 'both'),
                create_option('Not sure', 'unsure')
            ]
        ),
        Question(
            id='swell_onset',
            text='When did the swelling start?',
            input_type=InputType.CHOICE,
            options=[
                create_option('Today', 'today'),
                create_option('Yesterday', 'yesterday'),
                create_option('2-3 days ago', '2-3d'),
                create_option('More than 3 days ago', '>3d')
            ]
        ),
        Question(
            id='swell_trigger',
            text='Did the swelling start after any of the following? (Select all that apply)',
            input_type=InputType.MULTISELECT,
            options=[
                create_option('Chemotherapy', 'chemo'),
                create_option('Steroid medication', 'steroid'),
                create_option('IV or infusion', 'iv'),
                create_option('Surgery', 'surgery'),
                create_option('A long day of sitting or standing', 'sitting_standing'),
                create_option('Not sure', 'unsure')
            ]
        ),
        Question(
            id='severity',
            text='Rate your swelling:',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(SEVERITY_OPTIONS)
        ),
        Question(
            id='swell_associated',
            text='Are you also noticing any of these today? (Select all that apply)',
            input_type=InputType.MULTISELECT,
            options=[
                create_option('Shortness of breath', 'sob'),
                create_option('Chest discomfort', 'chest_discomfort'),
                create_option('Fever', 'fever'),
                create_option('Redness', 'redness'),
                create_option('None of the above', 'none')
            ]
        ),
        Question(
            id='redness',
            text='Is there any redness where you have swelling?',
            input_type=InputType.YES_NO
        )
    ],
    evaluate_screening=_eval_swelling,
    follow_up_questions=[
        Question(
            id='swell_clots',
            text='Do you have a history of blood clots?',
            input_type=InputType.YES_NO
        )
    ],
    evaluate_follow_up=_eval_swelling_followup
)


# MSO-208: Mouth Sores
def _eval_mouth_sores(answers: Dict[str, Any]) -> LogicResult:
    intake = answers.get('intake')
    weight_loss = answers.get('weight_loss')
    discomfort = answers.get('discomfort')
    temp = answers.get('mouth_temp')
    
    try:
        t = float(temp) if temp else 0
    except (ValueError, TypeError):
        t = 0
    
    has_fever = t >= 100.3
    intake_bad = intake in ['none', 'barely', 'difficulty']
    
    # Alert: Not able to eat/drink normally AND/OR Fever OR Rating Severe
    # Use 'continue' to proceed to follow-up questions (swallowing pain, dehydration)
    if intake_bad or weight_loss is True or discomfort == 'sev' or has_fever:
        reasons = []
        if intake == 'none':
            reasons.append('Unable to eat/drink for 24 hours')
        elif intake_bad:
            reasons.append('Difficulty eating/drinking')
        if weight_loss is True:
            reasons.append('>3lbs weight loss this week')
        if discomfort == 'sev':
            reasons.append('Severe pain')
        if has_fever:
            reasons.append(f'Fever {t}°F')
        
        return LogicResult(
            action='continue',  # Continue to follow-up questions
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message=f"Mouth sores alert: {', '.join(reasons)}. Please contact your care team."
        )
    
    # Still continue to follow-up even for manageable cases
    return LogicResult(
        action='continue',
        triage_level=TriageLevel.NONE,
        triage_message='Mouth sores reported - manageable.'
    )


def _eval_mouth_sores_followup(answers: Dict[str, Any]) -> LogicResult:
    """Evaluate mouth sores follow-up with dehydration checks per spec MSO-208."""
    swallowing_pain = answers.get('swallowing_pain') is True
    
    # Check dehydration signs
    urine_dark = answers.get('mso_urine_dark') is True
    urine_less = answers.get('mso_urine_less') is True
    thirsty = answers.get('mso_thirsty') is True
    lightheaded = answers.get('mso_lightheaded') is True
    vitals_text = answers.get('mso_vitals', '')
    
    # Parse vitals if provided
    vitals = parse_vitals_from_text(vitals_text) if vitals_text else {'hr_high': False, 'bp_low': False}
    
    # Collect dehydration signs
    dehy_signs = []
    if urine_dark:
        dehy_signs.append('Dark urine')
    if urine_less:
        dehy_signs.append('Reduced urination')
    if thirsty:
        dehy_signs.append('Very thirsty')
    if lightheaded:
        dehy_signs.append('Lightheaded')
    if vitals['hr_high']:
        dehy_signs.append('HR ≥100')
    if vitals['bp_low']:
        dehy_signs.append('SBP ≤100')
    
    # Build message with all findings
    findings = []
    if swallowing_pain:
        findings.append('Pain when swallowing')
    if dehy_signs:
        findings.extend(dehy_signs)
    
    # If dehydration signs present, branch to DEH-201 for full evaluation
    if dehy_signs:
        return LogicResult(
            action='branch',
            branch_to_symptom_id='DEH-201',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message=f"Mouth sores with dehydration signs: {', '.join(findings)}. You may be dehydrated. Please contact your care team immediately."
        )
    
    # If swallowing pain but no dehydration
    if swallowing_pain:
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message='Mouth sores with pain when swallowing. Please contact your care team.'
        )
    
    # No concerning follow-up findings
    return LogicResult(
        action='stop',
        triage_level=TriageLevel.NONE,
        triage_message='Mouth sores follow-up complete. Continue home care and contact your care team if symptoms worsen.'
    )

SYMPTOMS['MSO-208'] = SymptomDef(
    id='MSO-208',
    name='Mouth Sores',
    category=SymptomCategory.OTHER,
    screening_questions=[
        Question(
            id='intake',
            text='How is your oral intake (eating and drinking)?',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(ORAL_INTAKE_OPTIONS)
        ),
        Question(
            id='weight_loss',
            text='Have you lost more than 3 pounds in the last week?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='mouth_remedy',
            text='What remedies have you tried?',
            input_type=InputType.CHOICE,
            options=[
                create_option('Magic Mouthwash Rinse 5-10 mL for 30-60 seconds every 4-6 hours', 'magic_mouthwash'),
                create_option('Other', 'other'),
                create_option('None', 'none')
            ]
        ),
        Question(
            id='mouth_remedy_other',
            text='What remedy have you tried?',
            input_type=InputType.TEXT,
            condition=lambda a: a.get('mouth_remedy') == 'other'
        ),
        Question(
            id='mouth_remedy_days',
            text='How many days have you been using this remedy?',
            input_type=InputType.NUMBER,
            condition=lambda a: a.get('mouth_remedy') and a.get('mouth_remedy') != 'none'
        ),
        Question(
            id='mouth_remedy_helped',
            text='Has the remedy helped?',
            input_type=InputType.YES_NO,
            condition=lambda a: a.get('mouth_remedy') and a.get('mouth_remedy') != 'none'
        ),
        Question(
            id='mouth_temp',
            text='What is your temperature?',
            input_type=InputType.NUMBER
        ),
        Question(
            id='discomfort',
            text='Rate your discomfort:',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(SEVERITY_OPTIONS)
        )
    ],
    evaluate_screening=_eval_mouth_sores,
    follow_up_questions=[
        # Per spec MSO-208: "Are you having any pain when you swallow?"
        Question(
            id='swallowing_pain',
            text='Are you having any pain when you swallow?',
            input_type=InputType.YES_NO
        ),
        # Standard dehydration question set (5 questions per DEH-201 spec)
        Question(
            id='mso_urine_dark',
            text='Is your urine dark?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='mso_urine_less',
            text='Is the amount of urine a lot less over the last 12 hours?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='mso_thirsty',
            text='Are you very thirsty?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='mso_lightheaded',
            text='Are you lightheaded?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='mso_vitals',
            text='Do you know what your heart rate and blood pressure is? If so, please enter (e.g., HR: 95, BP: 110/70):',
            input_type=InputType.TEXT
        )
    ],
    evaluate_follow_up=_eval_mouth_sores_followup
)


# EYE-207: Eye Complaints
def _eval_eye(answers: Dict[str, Any]) -> LogicResult:
    interfere = answers.get('interfere')
    severity = answers.get('severity')
    
    if interfere is True or severity == 'sev':
        return LogicResult(
            action='continue',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message='Eye symptoms interfere with daily tasks or rated severe.'
        )
    
    return LogicResult(action='continue')

SYMPTOMS['EYE-207'] = SymptomDef(
    id='EYE-207',
    name='Eye Complaints',
    category=SymptomCategory.OTHER,
    screening_questions=[
        Question(
            id='new_concern',
            text='Is this eye concern new?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='symptoms',
            text='Are you experiencing any of the following?',
            input_type=InputType.MULTISELECT,
            options=[
                create_option('Pain', 'pain'),
                create_option('Discharge', 'discharge'),
                create_option('Excessive tearing', 'tearing'),
                create_option('None', 'none')
            ]
        ),
        Question(
            id='vision_problems',
            text='Are you having any NEW problems with your vision?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='interfere',
            text='Does this interfere with your daily tasks?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='severity',
            text='Rate your symptoms:',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(SEVERITY_OPTIONS)
        )
    ],
    evaluate_screening=_eval_eye,
    follow_up_questions=[
        Question(
            id='eye_doctor',
            text='Have you seen an eye doctor for this yet?',
            input_type=InputType.YES_NO
        )
    ],
    evaluate_follow_up=lambda a: LogicResult(action='continue')
)


# SKI-212: Skin Rash / Redness
def _eval_skin(answers: Dict[str, Any]) -> LogicResult:
    locations = answers.get('loc', [])
    face_breath = answers.get('face_breath')
    infusion_sx = answers.get('infusion_sx', [])
    adl = answers.get('adl')
    coverage = answers.get('coverage')
    temp = answers.get('rash_temp')
    
    # EMERGENCY: Face rash + trouble breathing → Branch to URG-101 per spec
    if 'face' in locations and face_breath is True:
        return LogicResult(
            action='branch',
            branch_to_symptom_id='URG-101',
            triage_level=TriageLevel.CALL_911,
            triage_message='Facial Rash with Breathing Difficulty - possible allergic reaction. Seek immediate emergency care.'
        )
    
    try:
        t = float(temp) if temp else 0
    except (ValueError, TypeError):
        t = 0
    
    # Infusion site issues: swelling, blistering, or open wound
    infusion_issue = any(sx in infusion_sx for sx in ['swelling', 'blistering', 'wound'])
    adl_issue = adl is True
    fever_issue = t > 100.3
    coverage_issue = coverage is True
    
    if infusion_issue or adl_issue or fever_issue or coverage_issue:
        reasons = []
        if infusion_issue:
            issues = [sx for sx in ['swelling', 'blistering', 'wound'] if sx in infusion_sx]
            reasons.append(f"Infusion site: {', '.join(issues)}")
        if adl_issue:
            reasons.append('Affects daily activities')
        if fever_issue:
            reasons.append(f'Fever {t}°F')
        if coverage_issue:
            reasons.append('>30% body coverage')
        return LogicResult(
            action='continue',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message=f"Skin rash alert: {', '.join(reasons)}."
        )
    
    return LogicResult(action='continue')

def _eval_skin_followup(answers: Dict[str, Any]) -> LogicResult:
    symptoms = answers.get('symptoms', [])
    worse = answers.get('worse')
    days = answers.get('days')
    
    if 'unwell' in symptoms:
        return LogicResult(action='branch', branch_to_symptom_id='FEV-202')
    
    try:
        days_num = float(days) if days else 0
    except (ValueError, TypeError):
        days_num = 0
    
    if worse is True and days_num > 2:
        return LogicResult(
            action='continue',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message='Worsening rash > 2 days.'
        )
    
    return LogicResult(action='continue')

SYMPTOMS['SKI-212'] = SymptomDef(
    id='SKI-212',
    name='Skin Rash / Redness',
    category=SymptomCategory.OTHER,
    screening_questions=[
        Question(
            id='loc',
            text='Where is the rash?',
            input_type=InputType.MULTISELECT,
            options=[
                create_option('Face', 'face'),
                create_option('Chest', 'chest'),
                create_option('Arms', 'arms'),
                create_option('Legs', 'legs'),
                create_option('Hands/Feet', 'hands_feet'),
                create_option('Infusion Site', 'infusion'),
                create_option('Other', 'other')
            ]
        ),
        Question(
            id='loc_other',
            text='Please describe the location:',
            input_type=InputType.TEXT,
            condition=lambda a: 'other' in (a.get('loc') or [])
        ),
        Question(
            id='infusion_sx',
            text='If Infusion Site, do you have:',
            input_type=InputType.MULTISELECT,
            options=[
                create_option('Swelling', 'swelling'),
                create_option('Blistering', 'blistering'),
                create_option('Redness', 'redness'),
                create_option('Open Wound', 'wound'),
                create_option('Other', 'other'),
                create_option('None', 'none')
            ],
            condition=lambda a: 'infusion' in (a.get('loc') or [])
        ),
        Question(
            id='face_breath',
            text='Is there any trouble breathing?',
            input_type=InputType.YES_NO,
            condition=lambda a: 'face' in (a.get('loc') or [])
        ),
        Question(
            id='coverage',
            text='Does the rash cover more than 30% of your body?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='adl',
            text='Does the rash affect your daily activities (ADLs)?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='rash_temp',
            text='What is your temperature?',
            input_type=InputType.NUMBER
        ),
        Question(
            id='severity',
            text='Rate your rash:',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(SEVERITY_OPTIONS)
        )
    ],
    evaluate_screening=_eval_skin,
    follow_up_questions=[
        Question(
            id='days',
            text='How many days have you had a rash?',
            input_type=InputType.NUMBER
        ),
        Question(
            id='worse',
            text='Is it getting worse?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='symptoms',
            text='Are you experiencing any of these?',
            input_type=InputType.MULTISELECT,
            options=[
                create_option('I feel unwell', 'unwell'),
                create_option('Skin cracked', 'cracked'),
                create_option('Liquid from rash', 'liquid'),
                create_option('Other', 'other'),
                create_option('None', 'none')
            ]
        )
    ],
    evaluate_follow_up=_eval_skin_followup
)


# URI-211: Urinary Problems
def _eval_urinary(answers: Dict[str, Any]) -> LogicResult:
    amount = answers.get('amount')
    burning = answers.get('burning')
    pelvic = answers.get('pelvic')
    blood = answers.get('blood')
    
    burning_alert = burning in ['mod', 'sev']
    
    if amount is True or pelvic is True or blood is True or burning_alert:
        reasons = []
        if amount is True:
            reasons.append('Drastic urine change')
        if pelvic is True:
            reasons.append('Pelvic pain')
        if blood is True:
            reasons.append('Blood in urine')
        if burning_alert:
            reasons.append(f'{burning} burning with urination')
        
        return LogicResult(
            action='continue',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message=f"Urinary problems: {', '.join(reasons)}."
        )
    
    return LogicResult(action='continue')

def _eval_urinary_followup(answers: Dict[str, Any]) -> LogicResult:
    sugar = answers.get('sugar')
    fluid_intake = answers.get('fluid_intake_normal')
    
    try:
        sugar_num = float(sugar) if sugar else None
    except (ValueError, TypeError):
        sugar_num = None
    
    if sugar_num is not None and (sugar_num > 250 or sugar_num < 60):
        return LogicResult(
            action='continue',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message='Diabetic with Blood Sugar >250 or <60.'
        )
    
    if fluid_intake is False:
        return LogicResult(action='branch', branch_to_symptom_id='DEH-201')
    
    return LogicResult(action='continue')

SYMPTOMS['URI-211'] = SymptomDef(
    id='URI-211',
    name='Urinary Problems',
    category=SymptomCategory.OTHER,
    screening_questions=[
        Question(
            id='amount',
            text='Has the amount of urine you produce drastically reduced or increased?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='burning',
            text='Do you have burning with urination?',
            input_type=InputType.CHOICE,
            options=[
                create_option('No', 'no'),
                create_option('Mild', 'mild'),
                create_option('Moderate', 'mod'),
                create_option('Severe', 'sev')
            ]
        ),
        Question(
            id='pelvic',
            text='Are you having pelvic pain with urination?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='blood',
            text='Do you see any blood in your urine?',
            input_type=InputType.YES_NO
        )
    ],
    evaluate_screening=_eval_urinary,
    follow_up_questions=[
        Question(
            id='smell',
            text='Does your urine have an unusual smell?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='fluid_intake_normal',
            text='Are you drinking your normal amount of fluids?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='diabetic',
            text='Are you diabetic?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='sugar',
            text='If so, what is your blood sugar level?',
            input_type=InputType.NUMBER,
            condition=lambda a: a.get('diabetic') is True
        )
    ],
    evaluate_follow_up=_eval_urinary_followup
)


# APP-209: No Appetite
def _eval_no_appetite(answers: Dict[str, Any]) -> LogicResult:
    intake = answers.get('intake')
    weight_loss = answers.get('weight_loss')
    discomfort = answers.get('discomfort')
    half_meals = answers.get('half_meals')
    
    # Alert: Recent weight loss >3 lbs in a week OR Eating less than half of usual meals for ≥2 days
    if intake == 'none' or weight_loss is True or discomfort == 'sev' or half_meals is True:
        reasons = []
        if intake == 'none':
            reasons.append('Unable to eat/drink for 24 hours')
        if weight_loss is True:
            reasons.append('>3lbs weight loss this week')
        if half_meals is True:
            reasons.append('Eating less than half meals for ≥2 days')
        if discomfort == 'sev':
            reasons.append('Severe discomfort')
        
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message=f"No appetite alert: {', '.join(reasons)}."
        )
    
    return LogicResult(
        action='stop',
        triage_level=TriageLevel.NONE,
        triage_message='Reduced appetite reported - continue monitoring.'
    )

SYMPTOMS['APP-209'] = SymptomDef(
    id='APP-209',
    name='No Appetite',
    category=SymptomCategory.OTHER,
    screening_questions=[
        Question(
            id='intake',
            text='How is your oral intake (eating and drinking)?',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(ORAL_INTAKE_OPTIONS)
        ),
        Question(
            id='weight_loss',
            text='Have you lost more than 3 pounds in the last week?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='half_meals',
            text='Are you eating half of your usual meals for 2 days or more?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='discomfort',
            text='Rate your discomfort:',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(SEVERITY_OPTIONS)
        )
    ],
    evaluate_screening=_eval_no_appetite
)


# -----------------------------------------------------------------------------
# HIDDEN PAIN SUB-MODULES (Triggered from Pain Router PAI-213)
# -----------------------------------------------------------------------------

# URG-114: Port/IV Site Pain (HIGH RISK - Infection)
def _eval_port_site(answers: Dict[str, Any]) -> LogicResult:
    redness = answers.get('redness') is True
    drainage = answers.get('drainage') is True
    chills = answers.get('chills') is True
    temp = answers.get('port_temp')
    
    try:
        t = float(temp) if temp else 0
    except (ValueError, TypeError):
        t = 0
    
    has_fever = t >= 100.3
    
    # URGENT: Infection signs WITH fever
    if has_fever and (redness or drainage or chills):
        reasons = []
        if redness:
            reasons.append('Redness')
        if drainage:
            reasons.append('Drainage')
        if chills:
            reasons.append('Chills')
        reasons.append(f'Temp {t}°F')
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.CALL_911,
            triage_message=f"Port/IV site infection WITH fever - URGENT: {', '.join(reasons)}."
        )
    
    # Any concerning sign → Notify Care Team
    if redness or drainage or chills or has_fever:
        reasons = []
        if redness:
            reasons.append('Redness')
        if drainage:
            reasons.append('Drainage')
        if chills:
            reasons.append('Chills')
        if has_fever:
            reasons.append(f'Temp {t}°F')
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message=f"Port/IV site concern: {', '.join(reasons)}."
        )
    
    return LogicResult(
        action='stop',
        triage_level=TriageLevel.NONE,
        triage_message='Port/IV site checked - no concerning signs.'
    )

SYMPTOMS['URG-114'] = SymptomDef(
    id='URG-114',
    name='Port/IV Site Pain',
    category=SymptomCategory.OTHER,
    hidden=True,
    screening_questions=[
        Question(
            id='redness',
            text='Is there any new redness at your port or IV site?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='drainage',
            text='Is there any drainage from the site?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='chills',
            text='Are you experiencing chills?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='port_temp',
            text='What is your temperature?',
            input_type=InputType.NUMBER
        )
    ],
    evaluate_screening=_eval_port_site
)


# HEA-210: Headache (HIGH RISK - CNS)
def _eval_headache(answers: Dict[str, Any]) -> LogicResult:
    worst_ever = answers.get('worst_ever') is True
    neuro_symptoms = answers.get('neuro_symptoms', [])
    severity = answers.get('severity')
    
    # Check for ANY neurological red flags (per oncologist spec)
    has_neuro_red_flags = (
        worst_ever or
        'vision' in neuro_symptoms or
        'speech' in neuro_symptoms or
        'face_droop' in neuro_symptoms or
        'limb_weak' in neuro_symptoms or
        'balance' in neuro_symptoms or
        'confusion' in neuro_symptoms
    )
    
    # Alert: ANY of the neurological red flags → CALL 911 AND Notify Care Team
    if has_neuro_red_flags:
        reasons = []
        if worst_ever:
            reasons.append('Worst headache of life / sudden onset')
        if 'vision' in neuro_symptoms:
            reasons.append('Blurred or double vision')
        if 'speech' in neuro_symptoms:
            reasons.append('Trouble speaking or understanding words')
        if 'face_droop' in neuro_symptoms:
            reasons.append('Face drooping on one side')
        if 'limb_weak' in neuro_symptoms:
            reasons.append('Arm or leg weakness')
        if 'balance' in neuro_symptoms:
            reasons.append('Trouble walking or balance')
        if 'confusion' in neuro_symptoms:
            reasons.append('Confusion or trouble staying awake')
        
        return LogicResult(
            action='continue',
            triage_level=TriageLevel.CALL_911,
            triage_message=f"URGENT HEADACHE - Call 911: {', '.join(reasons)}. Rule out CNS mass/bleed/stroke."
        )
    
    return LogicResult(action='continue')

def _eval_headache_followup(answers: Dict[str, Any]) -> LogicResult:
    onset = answers.get('onset')
    fever = answers.get('fever') is True
    temp = answers.get('ha_temp')
    duration = answers.get('duration')
    severity = answers.get('severity')  # From screening
    
    try:
        t = float(temp) if temp else 0
    except (ValueError, TypeError):
        t = 0
    
    # Sudden onset is very concerning → Emergency
    if onset == 'sudden':
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.CALL_911,
            triage_message='Sudden onset headache - possible stroke/aneurysm. Seek emergency care.'
        )
    
    # Fever ≥100.3 with headache - possible meningitis → Branch to Fever
    if fever or t >= 100.3:
        return LogicResult(action='branch', branch_to_symptom_id='FEV-202')
    
    # If NO neurological red flags but: Severe OR (Moderate for ≥3 days) → Notify Care Team
    if severity == 'sev':
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message='Severe headache - contact care team.'
        )
    
    if severity == 'mod' and duration in ['3d', '>3d']:
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message='Moderate headache for 3+ days - contact care team.'
        )
    
    return LogicResult(
        action='stop',
        triage_level=TriageLevel.NONE,
        triage_message='Headache reported - monitor and follow up if worsening.'
    )

SYMPTOMS['HEA-210'] = SymptomDef(
    id='HEA-210',
    name='Headache',
    category=SymptomCategory.OTHER,
    hidden=True,
    screening_questions=[
        Question(
            id='worst_ever',
            text='Is this the worst headache you\'ve ever had, or did it start suddenly and very strongly?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='neuro_symptoms',
            text='Do you have any of these symptoms?',
            input_type=InputType.MULTISELECT,
            options=[
                create_option('Blurred or double vision', 'vision'),
                create_option('Trouble speaking or understanding words', 'speech'),
                create_option('One side of your face looks droopy', 'face_droop'),
                create_option('One arm or leg feels weak, heavy, or harder to move', 'limb_weak'),
                create_option('Trouble walking or keeping your balance', 'balance'),
                create_option('Confusion or trouble staying awake', 'confusion'),
                create_option('None of these', 'none')
            ]
        ),
        Question(
            id='severity',
            text='Rate your headache:',
            input_type=InputType.CHOICE,
            options=[
                create_option('Mild (1-3)', 'mild'),
                create_option('Moderate (4-6)', 'mod'),
                create_option('Severe (7-10)', 'sev')
            ]
        ),
        Question(
            id='interfere',
            text='Does the headache interfere with your daily activities?',
            input_type=InputType.YES_NO
        )
    ],
    evaluate_screening=_eval_headache,
    follow_up_questions=[
        Question(
            id='onset',
            text='When did this headache start?',
            input_type=InputType.CHOICE,
            options=[
                create_option('Sudden (seconds/minutes)', 'sudden'),
                create_option('Today', 'today'),
                create_option('1-3 days ago', '1-3d'),
                create_option('More than 3 days', '>3d')
            ]
        ),
        Question(
            id='duration',
            text='How long have you had this headache?',
            input_type=InputType.CHOICE,
            options=[
                create_option('Less than a day', '<1d'),
                create_option('1-2 days', '1-2d'),
                create_option('3 days', '3d'),
                create_option('More than 3 days', '>3d')
            ]
        ),
        Question(
            id='meds',
            text='Have you taken any medications for the headache?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='meds_helped',
            text='Did the medications help?',
            input_type=InputType.YES_NO,
            condition=lambda a: a.get('meds') is True
        ),
        Question(
            id='fever',
            text='Do you have a fever?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='ha_temp',
            text='What is your temperature?',
            input_type=InputType.NUMBER,
            condition=lambda a: a.get('fever') is True
        )
    ],
    evaluate_follow_up=_eval_headache_followup
)


# ABD-211: Abdominal Pain (GI Risk)
def _eval_abdominal(answers: Dict[str, Any]) -> LogicResult:
    severity = answers.get('severity')
    temp = answers.get('abd_temp')
    last_bm = answers.get('last_bm_days')
    passing_gas = answers.get('passing_gas')
    blood_stool = answers.get('blood_stool_screen') is True
    
    try:
        t = float(temp) if temp else 0
        bm_days = float(last_bm) if last_bm else 0
    except (ValueError, TypeError):
        t = 0
        bm_days = 0
    
    fever = t > 100.3
    no_bm_3_days = bm_days >= 3
    no_gas = passing_gas is False
    
    # Alert per oncologist spec:
    # If abdominal pain moderate or severe, 3 days of no bowel movement or passing gas, 
    # OR temperature >100.3 OR blood in stool → Notify Care Team
    if severity in ['mod', 'sev'] or no_bm_3_days or no_gas or fever or blood_stool:
        reasons = []
        if severity == 'sev':
            reasons.append('Severe abdominal pain')
        elif severity == 'mod':
            reasons.append('Moderate abdominal pain')
        if no_bm_3_days:
            reasons.append(f'No bowel movement for {int(bm_days)} days')
        if no_gas:
            reasons.append('Not passing gas')
        if fever:
            reasons.append(f'Temperature {t}°F')
        if blood_stool:
            reasons.append('Blood in stool')
        return LogicResult(
            action='continue',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message=f"Abdominal pain alert: {', '.join(reasons)}. Rule out GI bleed/obstruction."
        )
    
    return LogicResult(action='continue')

def _eval_abdominal_followup(answers: Dict[str, Any]) -> LogicResult:
    blood_stool = answers.get('blood_stool') is True
    vomiting = answers.get('vomiting') is True
    dehydration = answers.get('dehydration') is True
    last_bm = answers.get('last_bm')
    
    # Blood in stool is urgent
    if blood_stool:
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message='Abdominal pain with blood in stool - GI bleed concern.'
        )
    
    # Branch to related modules
    if vomiting:
        return LogicResult(action='branch', branch_to_symptom_id='VOM-204')
    
    if dehydration:
        return LogicResult(action='branch', branch_to_symptom_id='DEH-201')
    
    if last_bm == '>2d':
        return LogicResult(action='branch', branch_to_symptom_id='CON-210')
    
    return LogicResult(
        action='stop',
        triage_level=TriageLevel.NONE,
        triage_message='Abdominal pain reported - monitor and follow up if worsening.'
    )

SYMPTOMS['ABD-211'] = SymptomDef(
    id='ABD-211',
    name='Abdominal Pain',
    category=SymptomCategory.OTHER,
    hidden=True,
    screening_questions=[
        Question(
            id='severity',
            text='Rate your abdominal pain:',
            input_type=InputType.CHOICE,
            options=[
                create_option('Mild (1-3)', 'mild'),
                create_option('Moderate (4-6)', 'mod'),
                create_option('Severe (7-10)', 'sev')
            ]
        ),
        Question(
            id='interfere',
            text='Does the pain interfere with your daily activities?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='abd_temp',
            text='What is your temperature?',
            input_type=InputType.NUMBER
        ),
        Question(
            id='last_bm_days',
            text='How many days since your last bowel movement?',
            input_type=InputType.NUMBER
        ),
        Question(
            id='passing_gas',
            text='Are you passing gas?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='blood_stool_screen',
            text='Is there any blood in your stool?',
            input_type=InputType.YES_NO
        )
    ],
    evaluate_screening=_eval_abdominal,
    follow_up_questions=[
        Question(
            id='vomiting',
            text='Have you been vomiting?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='blood_stool',
            text='Is there any blood in your stool?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='dehydration',
            text='Are you experiencing signs of dehydration (dark urine, thirsty, lightheaded)?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='last_bm',
            text='When was your last bowel movement?',
            input_type=InputType.CHOICE,
            options=[
                create_option('Today', 'today'),
                create_option('Yesterday', 'yesterday'),
                create_option('2+ days ago', '>2d')
            ]
        )
    ],
    evaluate_follow_up=_eval_abdominal_followup
)


# LEG-208: Leg/Calf Pain (HIGH RISK - DVT)
def _eval_leg_pain(answers: Dict[str, Any]) -> LogicResult:
    asymmetric = answers.get('asymmetric') is True
    worse_walk_press = answers.get('worse_walk_press') is True
    
    # DVT Alert: Asymmetric OR Worse with walk/press → CALL 911 AND Notify Care Team (per oncologist spec)
    if asymmetric or worse_walk_press:
        reasons = []
        if asymmetric:
            reasons.append('One leg more swollen/red/warm/painful than the other')
        if worse_walk_press:
            reasons.append('Pain worsens with walking/pressing on calf')
        return LogicResult(
            action='continue',
            triage_level=TriageLevel.CALL_911,
            triage_message=f"⚠️ DVT CONCERN - URGENT: {', '.join(reasons)}. Notify Care Team immediately for evaluation."
        )
    
    return LogicResult(action='continue')

def _eval_leg_pain_followup(answers: Dict[str, Any]) -> LogicResult:
    sob = answers.get('sob') is True
    immobility = answers.get('immobility') is True
    clot_history = answers.get('clot_history') is True
    
    # SOB with leg pain = possible PE → Emergency
    if sob:
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.CALL_911,
            triage_message='Leg pain with shortness of breath - possible pulmonary embolism. Seek emergency care.'
        )
    
    # Risk factors present
    if immobility or clot_history:
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message='Leg pain with DVT risk factors (immobility/clot history). Recommend evaluation.'
        )
    
    return LogicResult(
        action='stop',
        triage_level=TriageLevel.NONE,
        triage_message='Leg pain - no DVT signs. Monitor and follow up if worsening.'
    )

SYMPTOMS['LEG-208'] = SymptomDef(
    id='LEG-208',
    name='Leg/Calf Pain',
    category=SymptomCategory.OTHER,
    hidden=True,
    screening_questions=[
        Question(
            id='asymmetric',
            text='Is one leg more swollen, red, warm, or painful than the other?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='worse_walk_press',
            text='Does the pain get worse when you walk or press on your calf?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='severity',
            text='Rate your leg/calf pain:',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(SEVERITY_OPTIONS)
        ),
        Question(
            id='interfere',
            text='Does the pain interfere with walking or daily activities?',
            input_type=InputType.YES_NO
        )
    ],
    evaluate_screening=_eval_leg_pain,
    follow_up_questions=[
        Question(
            id='immobility',
            text='Have you had recent immobility (bed rest, long travel, surgery)?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='clot_history',
            text='Do you have a history of blood clots?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='sob',
            text='Are you experiencing any shortness of breath?',
            input_type=InputType.YES_NO
        )
    ],
    evaluate_follow_up=_eval_leg_pain_followup
)


# JMP-212: Joint/Muscle/General Pain (MSK)
def _eval_joint_muscle(answers: Dict[str, Any]) -> LogicResult:
    severity = answers.get('severity')
    interfere = answers.get('interfere') is True
    move_sleep = answers.get('move_sleep') is True  # Per spec: hard to move around or sleep
    better_rest = answers.get('better_rest')
    temp = answers.get('jmp_temp')
    
    try:
        t = float(temp) if temp else 0
    except (ValueError, TypeError):
        t = 0
    
    fever = t >= 100.4
    
    # Alert: Sev OR Interfere OR Move/Sleep impact OR Not controlled/better OR Fever → Notify
    if severity == 'sev' or interfere or move_sleep or better_rest is False or fever:
        reasons = []
        pain_type = answers.get('pain_type', 'Pain')
        if severity == 'sev':
            reasons.append('Severe pain')
        if move_sleep:
            reasons.append('Difficulty moving or sleeping')
        if interfere:
            reasons.append('Interferes with daily activities')
        if better_rest is False:
            reasons.append('Not improved with rest/OTC')
        if fever:
            reasons.append(f'Fever {t}°F')
        return LogicResult(
            action='continue',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message=f"{pain_type} pain: {', '.join(reasons)}. Contact provider."
        )
    
    return LogicResult(action='continue')

def _eval_joint_muscle_followup(answers: Dict[str, Any]) -> LogicResult:
    controlled_meds = answers.get('controlled_meds')
    
    if controlled_meds is False:
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message='Pain not controlled with usual medications - may need adjustment.'
        )
    
    # Per spec for General Aches / Fatigue (non-urgent path):
    # "Please let your care team know about your symptoms at your next appointment.
    # This chatbot is not a substitute for medical care and is not continuously monitored.
    # If you feel unsafe or believe this may be an emergency, please call 911 right away.
    # You definitely want your care team to know. Should I add this as a diary in the list of questions to ask your care team?"
    return LogicResult(
        action='stop',
        triage_level=TriageLevel.NONE,
        triage_message=(
            'Please let your care team know about your symptoms at your next appointment. '
            'This chatbot is not a substitute for medical care and is not continuously monitored. '
            'If you feel unsafe or believe this may be an emergency, please call 911 right away.\n\n'
            '💡 **Would you like to add this to your diary as a question for your care team?**'
        )
    )

SYMPTOMS['JMP-212'] = SymptomDef(
    id='JMP-212',
    name='Joint/Muscle/General Pain',
    category=SymptomCategory.OTHER,
    hidden=True,
    screening_questions=[
        Question(
            id='pain_type',
            text='What type of pain are you experiencing?',
            input_type=InputType.CHOICE,
            options=[
                create_option('Joint pain', 'joint'),
                create_option('Muscle pain', 'muscle'),
                create_option('General aches', 'general')
            ]
        ),
        # Per spec: Q1 - "Is your pain making it hard to move around or sleep?"
        Question(
            id='move_sleep',
            text='Is your pain making it hard to move around or sleep?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='severity',
            text='Rate your pain:',
            input_type=InputType.CHOICE,
            options=opts_from_dicts(SEVERITY_OPTIONS)
        ),
        Question(
            id='interfere',
            text='Does the pain interfere with your daily activities?',
            input_type=InputType.YES_NO
        ),
        # Per spec: Q2 - "Is it controlled with your usual pain medicine?"
        Question(
            id='better_rest',
            text='Does the pain get better with rest, hydration, or over-the-counter medicine?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='jmp_temp',
            text='What is your temperature?',
            input_type=InputType.NUMBER
        )
    ],
    evaluate_screening=_eval_joint_muscle,
    follow_up_questions=[
        Question(
            id='quality',
            text='How would you describe the pain?',
            input_type=InputType.CHOICE,
            options=[
                create_option('Sharp/stabbing', 'sharp'),
                create_option('Dull/aching', 'ache'),
                create_option('Burning', 'burning'),
                create_option('Throbbing', 'throbbing')
            ]
        ),
        Question(
            id='duration',
            text='How long have you had this pain?',
            input_type=InputType.CHOICE,
            options=[
                create_option('Started today', 'today'),
                create_option('1-3 days', '1-3d'),
                create_option('4-7 days', '4-7d'),
                create_option('More than a week', '>1w')
            ]
        ),
        Question(
            id='controlled_meds',
            text='Is the pain controlled with your usual pain medications?',
            input_type=InputType.YES_NO
        )
    ],
    evaluate_follow_up=_eval_joint_muscle_followup
)


# NEU-304: Falls & Balance (Hidden - Neurological Risk)
def _eval_falls(answers: Dict[str, Any]) -> LogicResult:
    falls = answers.get('falls') is True
    neuro_signs = answers.get('neuro_signs') is True
    
    # Alert: Falls OR new neuro signs → Notify Care Team
    if falls or neuro_signs:
        return LogicResult(
            action='continue',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message='Falls or new neurological symptoms (dizziness, confusion, balance issues).'
        )
    
    return LogicResult(
        action='stop',
        triage_level=TriageLevel.NONE,
        triage_message='No falls or balance issues reported.'
    )

def _eval_falls_followup(answers: Dict[str, Any]) -> LogicResult:
    head_hit = answers.get('head_hit') is True
    blood_thinners = answers.get('blood_thinners') is True
    
    # HIGH PRIORITY: Head hit + blood thinners → CALL 911
    if head_hit and blood_thinners:
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.CALL_911,
            triage_message='HIGH PRIORITY: Fall with head injury while on blood thinners - immediate evaluation required.'
        )
    
    # Head injury alone still concerning
    if head_hit:
        return LogicResult(
            action='stop',
            triage_level=TriageLevel.NOTIFY_CARE_TEAM,
            triage_message='Fall with head injury - needs evaluation.'
        )
    
    return LogicResult(
        action='stop',
        triage_level=TriageLevel.NONE,
        triage_message='Fall reported without head injury. Monitor for any new symptoms.'
    )

SYMPTOMS['NEU-304'] = SymptomDef(
    id='NEU-304',
    name='Falls & Balance',
    category=SymptomCategory.OTHER,
    hidden=True,
    screening_questions=[
        Question(
            id='falls',
            text='Have you had any falls since your last visit?',
            input_type=InputType.YES_NO
        ),
        Question(
            id='neuro_signs',
            text='Are you experiencing any new dizziness, confusion, or trouble with your balance?',
            input_type=InputType.YES_NO
        )
    ],
    evaluate_screening=_eval_falls,
    follow_up_questions=[
        Question(
            id='head_hit',
            text='Did you hit your head?',
            input_type=InputType.YES_NO,
            condition=lambda a: a.get('falls') is True
        ),
        Question(
            id='blood_thinners',
            text='Are you currently on any blood thinners?',
            input_type=InputType.YES_NO,
            condition=lambda a: a.get('falls') is True
        )
    ],
    evaluate_follow_up=_eval_falls_followup
)


# Get visible symptoms (non-hidden) for the symptom selector
def get_visible_symptoms() -> List[Dict[str, Any]]:
    """Returns list of visible symptoms for the symptom selector UI."""
    visible = []
    for symptom_id, symptom in SYMPTOMS.items():
        if not symptom.hidden:
            visible.append({
                'id': symptom.id,
                'name': symptom.name,
                'category': symptom.category.value
            })
    return visible


def get_symptom_by_id(symptom_id: str) -> Optional[SymptomDef]:
    """Get a symptom definition by its ID."""
    return SYMPTOMS.get(symptom_id)

