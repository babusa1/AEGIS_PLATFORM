# AEGIS Voice Module

Voice-based patient interaction layer providing ROVA-like capabilities.

## Overview

The Voice Module enables voice-based patient interactions through:
- **VoiceGateway**: Telephony integration (Twilio/Amazon Connect)
- **VoiceAgent**: AI voice assistant extending BaseAgent
- **VoiceWorkflows**: Pre-built workflows for common use cases

## Features

✅ **Inbound/Outbound Calls**: Handle patient calls and initiate automated calls  
✅ **Speech-to-Text**: Convert voice to text for processing  
✅ **Text-to-Speech**: Convert responses to natural voice  
✅ **IVR Menus**: Interactive voice response menus  
✅ **Appointment Booking**: Voice-based appointment scheduling  
✅ **Follow-Up Calls**: Automated reminder and check-in calls  
✅ **Insurance Checks**: Voice-based eligibility inquiries  
✅ **Multilingual**: Support for multiple languages  
✅ **Integration**: Leverages existing VeritOS agents and Data Moat  

## Architecture

```
┌─────────────────────────────────────────┐
│   Voice API Routes                      │
│   /v1/voice/calls/*                     │
│   /v1/voice/workflows/*                 │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│   VoiceGateway                          │
│   • Twilio/Amazon Connect                │
│   • STT/TTS                              │
│   • IVR Menus                            │
│   • Call State Management                │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│   VoiceAgent                            │
│   • Extends BaseAgent                    │
│   • Voice-specific prompts               │
│   • Conversation state                  │
│   • Integrates UnifiedViewAgent          │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│   VeritOS Platform (Existing)              │
│   • LLM Gateway                          │
│   • UnifiedViewAgent                     │
│   • Data Moat                            │
│   • Workflow Engine                      │
│   • Scheduling Connector                 │
│   • X12 EDI                              │
└─────────────────────────────────────────┘
```

## Setup

### 1. Install Dependencies

```bash
# Twilio (optional - for Twilio integration)
pip install twilio

# AWS SDK (optional - for Amazon Connect)
pip install boto3
```

### 2. Configure Environment Variables

```bash
# Twilio Configuration
export TWILIO_ACCOUNT_SID="your_account_sid"
export TWILIO_AUTH_TOKEN="your_auth_token"
export TWILIO_FROM_NUMBER="+1234567890"
export VOICE_WEBHOOK_URL="https://your-api.com/v1/voice/calls/inbound/webhook"
```

### 3. Register Routes

Routes are automatically registered via `safe_include_router` in `main.py`.

## Usage

### Inbound Call Flow

1. **Patient calls** → Twilio webhook → `/v1/voice/calls/inbound/webhook`
2. **IVR Menu** → Patient selects option (appointments, queries, insurance)
3. **Voice Agent** → Processes speech → Generates response
4. **TTS** → Converts response to speech → Returns to patient

### Outbound Call Flow

1. **Schedule Follow-Up** → `POST /v1/voice/workflows/followup-call`
2. **Workflow Engine** → Waits until scheduled time
3. **VoiceGateway** → Initiates outbound call
4. **Voice Agent** → Delivers message → Collects response

### Appointment Booking

```python
from aegis.voice.workflows import AppointmentBookingRequest

request = AppointmentBookingRequest(
    patient_id="patient-001",
    appointment_type="follow-up",
    preferred_date="2024-02-15",
    preferred_time="10:00 AM",
)

# Execute via API or directly
result = await voice_workflows.execute_appointment_booking(request, call_state)
```

### Insurance Check

```python
from aegis.voice.workflows import InsuranceCheckRequest

request = InsuranceCheckRequest(
    patient_id="patient-001",
    service_code="99213",  # Office visit
    date_of_service="2024-02-15",
)

result = await voice_workflows.execute_insurance_check(request, call_state)
```

## API Endpoints

### Call Management

- `POST /v1/voice/calls/outbound` - Initiate outbound call
- `POST /v1/voice/calls/inbound/webhook` - Handle inbound call (Twilio webhook)
- `POST /v1/voice/calls/{call_id}/menu-action` - Handle IVR menu selection
- `POST /v1/voice/calls/{call_id}/message` - Process voice message
- `GET /v1/voice/calls/{call_id}` - Get call status
- `GET /v1/voice/calls` - List active calls

### Workflows

- `POST /v1/voice/workflows/appointment-booking` - Book appointment via voice
- `POST /v1/voice/workflows/followup-call` - Schedule follow-up call
- `POST /v1/voice/workflows/insurance-check` - Check insurance eligibility

## Integration Points

### Leverages Existing Components

1. **LLM Gateway** → Conversation AI
2. **UnifiedViewAgent** → Query resolution
3. **Data Moat** → Patient/claims/appointment data
4. **Workflow Engine** → Automation and scheduling
5. **Notifications** → SMS/Email fallback
6. **Scheduling Connector** → Appointment management
7. **X12 EDI** → Insurance eligibility checks

## Example: Complete Appointment Booking

```python
# 1. Patient calls → Inbound webhook triggered
# 2. IVR menu → Patient presses "1" for appointments
# 3. Voice Agent processes: "I need to schedule an appointment"
# 4. Agent extracts: appointment_type="follow-up", preferred_date="next week"
# 5. Checks availability via Scheduling Connector
# 6. Confirms with patient: "I have availability on Tuesday at 2 PM"
# 7. Books appointment via Scheduling API
# 8. Sends SMS confirmation via Notifications
# 9. Ends call: "Your appointment is confirmed. You'll receive a text confirmation."
```

## Multilingual Support

VoiceAgent supports multiple languages via `language` parameter:

```python
agent = VoiceAgent(
    tenant_id="default",
    voice_gateway=gateway,
    language="es-ES",  # Spanish
)
```

Supported languages:
- `en-US` (English - US)
- `es-ES` (Spanish)
- `hi-IN` (Hindi)
- More can be added via LLM translation

## Production Considerations

1. **Call State Storage**: Currently in-memory. Use Redis in production.
2. **Conversation History**: Store in database for audit/compliance.
3. **STT/TTS**: Integrate AWS Transcribe/Polly or Google Speech APIs.
4. **Error Handling**: Add retry logic and fallback to human agents.
5. **HIPAA Compliance**: Encrypt call recordings, secure webhook endpoints.
6. **Scaling**: Use message queue for high-volume call handling.

## Testing

```bash
# Test inbound webhook (using ngrok or similar)
curl -X POST http://localhost:8001/v1/voice/calls/inbound/webhook \
  -d "CallSid=test123" \
  -d "From=+1234567890" \
  -d "To=+18005551234"

# Test outbound call
curl -X POST http://localhost:8001/v1/voice/calls/outbound \
  -H "Content-Type: application/json" \
  -d '{
    "to_number": "+1234567890",
    "patient_id": "patient-001",
    "workflow_id": "followup_call"
  }'
```

## Next Steps

1. **Integrate Real STT/TTS**: Connect AWS Transcribe/Polly or Google Speech
2. **Add Call Recording**: Store recordings for compliance
3. **Human Escalation**: Route complex queries to human agents
4. **Analytics**: Track call metrics, success rates, patient satisfaction
5. **Mobile App Integration**: Voice interface in mobile apps
