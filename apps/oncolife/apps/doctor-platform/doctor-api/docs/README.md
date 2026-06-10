# Doctor API Documentation

## Overview

The Doctor API is a FastAPI-based backend service that provides APIs for healthcare staff (doctors, nurses, administrators) to:
- Manage patients assigned to them
- View patient symptom alerts
- Review patient conversations and diary entries
- Manage clinic staff

---

## Architecture

```
doctor-api/src/
├── main.py                      # Application entry point
│
├── core/                        # Core infrastructure
│   ├── config.py               # Settings (Pydantic)
│   ├── logging.py              # Structured logging
│   ├── exceptions.py           # Custom exceptions
│   └── middleware/             # Request middleware
│
├── db/                          # Database layer
│   ├── base.py                 # SQLAlchemy base
│   ├── session.py              # Session management
│   ├── models/                 # ORM models
│   └── repositories/           # Data access layer
│
├── services/                    # Business logic
│   ├── auth_service.py         # Cognito authentication
│   ├── clinic_service.py       # Clinic management
│   ├── staff_service.py        # Staff operations
│   └── patient_service.py      # Patient data access
│
└── api/v1/                      # API endpoints
    ├── router.py               # Main router
    └── endpoints/
        ├── auth.py             # Authentication
        ├── clinics.py          # Clinic management
        ├── staff.py            # Staff management
        ├── patients.py         # Patient access
        └── health.py           # Health checks
```

---

## API Endpoints

All endpoints are prefixed with `/api/v1/`

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | Staff login |
| POST | `/auth/signup` | Register new staff |
| POST | `/auth/logout` | Logout |
| POST | `/auth/complete-new-password` | Complete password setup |
| DELETE | `/auth/delete-user` | Delete staff account |

### Clinic Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/clinics` | List all clinics |
| POST | `/clinics` | Create new clinic |
| GET | `/clinics/{uuid}` | Get clinic details |
| PATCH | `/clinics/{uuid}` | Update clinic |
| DELETE | `/clinics/{uuid}` | Delete clinic |

### Staff Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/staff` | List staff members |
| GET | `/staff/profile` | Get current user's profile |
| GET | `/staff/{uuid}` | Get staff member details |
| PATCH | `/staff/{uuid}` | Update staff member |

### Patient Access (Read-Only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/patients` | List associated patients |
| GET | `/patients/{uuid}` | Get patient details |
| GET | `/patients/{uuid}/alerts` | Get patient symptom alerts |
| GET | `/patients/{uuid}/conversations` | Get patient chat history |
| GET | `/patients/{uuid}/diary` | Get patient diary entries |
| GET | `/patients/{uuid}/stats` | Get patient statistics |

### Health Checks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Basic health check |
| GET | `/health/ready` | Detailed readiness check |

---

## Services

### AuthService

Handles AWS Cognito authentication:
- Login with email/password
- Signup new staff members
- Password change flow
- Account deletion

### ClinicService

Manages healthcare facilities:
- Create/update/delete clinics
- List clinics for organization

### StaffService

Manages staff members:
- Get staff profiles
- Update staff information
- List staff by clinic

### PatientService

Read-only access to patient data:
- List patients associated with physician
- Get patient details with authorization checks
- Retrieve alerts, conversations, diary entries
- Get patient statistics

---

## Database Models

The Doctor API uses two databases:

### Doctor Database (Primary)

| Table | Description |
|-------|-------------|
| `staff_profiles` | Staff member information |
| `all_clinics` | Healthcare facilities |
| `staff_associations` | Staff-clinic relationships |

### Patient Database (Read-Only)

| Table | Description |
|-------|-------------|
| `patient_info` | Patient profiles |
| `patient_physician_associations` | Patient-doctor links |
| `conversations` | Chat sessions |
| `patient_diary_entries` | Diary entries |

---

## Configuration

### Environment Variables

```env
# Application
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
APP_NAME=OncoLife Doctor API
APP_VERSION=1.0.0

# Server
HOST=0.0.0.0
PORT=8001

# Database - Doctor DB (Primary)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=oncolife_admin
POSTGRES_PASSWORD=password
POSTGRES_DOCTOR_DB=oncolife_doctor

# Database - Patient DB (Read-Only)
POSTGRES_PATIENT_DB=oncolife_patient

# AWS Cognito
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
COGNITO_USER_POOL_ID=us-west-2_xxxxx
COGNITO_CLIENT_ID=xxxxx
COGNITO_CLIENT_SECRET=xxxxx

# CORS
CORS_ORIGINS=http://localhost:3001,http://localhost:5174
```

---

## Running the API

### Development

```bash
cd apps/doctor-platform/doctor-api

# Setup virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run with hot reload
cd src
uvicorn main:app --reload --port 8001
```

### Production

```bash
uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4
```

### Docker

```bash
docker build -t oncolife-doctor-api .
docker run -p 8001:8001 --env-file .env oncolife-doctor-api
```

---

## API Usage Examples

### Login

```bash
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "doctor@example.com", "password": "password123"}'
```

Response:
```json
{
  "valid": true,
  "message": "Login successful",
  "user_status": "CONFIRMED",
  "tokens": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "id_token": "eyJ...",
    "token_type": "Bearer"
  }
}
```

### List Patients

```bash
curl -X GET "http://localhost:8001/api/v1/patients?skip=0&limit=50" \
  -H "Authorization: Bearer <access_token>"
```

Response:
```json
{
  "patients": [
    {
      "uuid": "123e4567-e89b-12d3-a456-426614174000",
      "email_address": "patient@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "phone_number": "555-0123",
      "created_at": "2026-01-04T10:30:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50
}
```

### Get Patient Alerts

```bash
curl -X GET "http://localhost:8001/api/v1/patients/<patient_uuid>/alerts" \
  -H "Authorization: Bearer <access_token>"
```

Response:
```json
[
  {
    "conversation_uuid": "abc...",
    "triage_level": "notify_care_team",
    "symptom_list": ["Fever", "Fatigue"],
    "created_at": "2026-01-04T14:22:00Z",
    "conversation_state": "COMPLETED"
  }
]
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message here"
}
```

| Status Code | Description |
|-------------|-------------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Invalid/missing token |
| 403 | Forbidden - Not authorized for resource |
| 404 | Not Found - Resource doesn't exist |
| 500 | Internal Server Error |

---

*Last Updated: January 2026*





