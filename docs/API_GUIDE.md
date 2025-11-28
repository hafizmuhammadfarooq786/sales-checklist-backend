# Sales Checklist API - Complete Technical Guide

**Version:** 1.0.0
**Last Updated:** November 24, 2024
**Author:** Engineering Team

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Entity Relationship Diagram (ERD)](#3-entity-relationship-diagram-erd)
4. [Database Schema](#4-database-schema)
5. [API Endpoints Reference](#5-api-endpoints-reference)
6. [Complete User Flow](#6-complete-user-flow)
7. [Integration Status](#7-integration-status)
8. [Testing Guide](#8-testing-guide)
9. [Error Handling](#9-error-handling)
10. [Deployment Checklist](#10-deployment-checklist)

---

## 1. System Overview

### 1.1 Purpose
The Sales Checklist API is an AI-powered B2B sales coaching platform that:
- Records and transcribes sales calls
- Analyzes conversations against 92 checklist items across 10 categories
- Generates scores and risk assessments
- Provides AI-powered coaching feedback
- Generates audio coaching using text-to-speech
- Creates professional PDF reports

### 1.2 Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend Framework** | FastAPI (Python 3.11+) |
| **Database** | PostgreSQL (Neon Cloud) |
| **ORM** | SQLAlchemy 2.0 (Async) |
| **Authentication** | JWT (python-jose) |
| **File Storage** | AWS S3 |
| **Email Service** | AWS SES |
| **Transcription** | OpenAI Whisper |
| **AI Analysis** | OpenAI GPT-4 Turbo |
| **Text-to-Speech** | ElevenLabs |
| **PDF Generation** | ReportLab |
| **Task Queue** | Celery + Redis |

### 1.3 Key Features

1. **User Management** - Registration, authentication, role-based access
2. **Session Management** - Create, track, and manage sales call sessions
3. **Audio Processing** - Upload, store, and transcribe audio files
4. **AI Analysis** - GPT-4 powered checklist validation
5. **Scoring Engine** - Calculate scores with risk bands (Green/Yellow/Red)
6. **Coaching Feedback** - Personalized AI coaching with TTS audio
7. **Report Generation** - Professional PDF reports
8. **Email Notifications** - Transactional emails via AWS SES

---

## 2. Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Next.js    │  │   Mobile     │  │   Admin      │          │
│  │   Frontend   │  │   App        │  │   Dashboard  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        API GATEWAY                               │
│                     FastAPI Application                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  /api/v1/auth    │  /api/v1/sessions  │  /api/v1/users   │  │
│  │  /api/v1/checklists  │  /api/v1/scoring  │  /api/v1/...  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   SERVICES    │    │   EXTERNAL    │    │   STORAGE     │
│               │    │    APIs       │    │               │
│ - Auth        │    │               │    │ - PostgreSQL  │
│ - Session     │    │ - OpenAI      │    │ - AWS S3      │
│ - Scoring     │    │ - ElevenLabs  │    │ - Redis       │
│ - Coaching    │    │ - AWS SES     │    │               │
│ - Reports     │    │ - Salesforce  │    │               │
└───────────────┘    └───────────────┘    └───────────────┘
```

### 2.2 Request Flow

```
User Request
     │
     ▼
┌─────────────┐
│   Router    │ ──► Route matching
└─────────────┘
     │
     ▼
┌─────────────┐
│ Middleware  │ ──► CORS, Rate Limiting
└─────────────┘
     │
     ▼
┌─────────────┐
│Dependencies │ ──► Auth, DB Session
└─────────────┘
     │
     ▼
┌─────────────┐
│  Endpoint   │ ──► Business Logic
└─────────────┘
     │
     ▼
┌─────────────┐
│  Services   │ ──► External APIs, DB
└─────────────┘
     │
     ▼
┌─────────────┐
│  Response   │ ──► JSON/File
└─────────────┘
```

---

## 3. Entity Relationship Diagram (ERD)

### 3.1 Visual ERD

```
┌─────────────────────┐       ┌─────────────────────┐
│    ORGANIZATION     │       │        TEAM         │
├─────────────────────┤       ├─────────────────────┤
│ id (PK)             │───┐   │ id (PK)             │
│ name                │   │   │ organization_id (FK)│◄──┐
│ domain              │   │   │ name                │   │
│ is_active           │   │   │ description         │   │
│ scoring_mode        │   │   │ is_active           │   │
│ max_users           │   └──►│                     │   │
│ created_at          │       │ created_at          │   │
│ updated_at          │       │ updated_at          │   │
└─────────────────────┘       └─────────────────────┘   │
                                       │               │
                                       ▼               │
┌─────────────────────┐       ┌─────────────────────┐   │
│   CHECKLIST_CATEGORY│       │        USER         │   │
├─────────────────────┤       ├─────────────────────┤   │
│ id (PK)             │       │ id (PK)             │   │
│ name                │       │ email               │   │
│ description         │       │ password_hash       │   │
│ order               │       │ first_name          │   │
│ default_weight      │       │ last_name           │   │
│ max_score           │       │ role                │   │
│ is_active           │       │ organization_id (FK)│───┘
│ created_at          │       │ team_id (FK)        │◄──────┐
│ updated_at          │       │ is_active           │       │
└─────────────────────┘       │ is_verified         │       │
         │                    │ last_login          │       │
         ▼                    │ created_at          │       │
┌─────────────────────┐       │ updated_at          │       │
│   CHECKLIST_ITEM    │       └─────────────────────┘       │
├─────────────────────┤                │                    │
│ id (PK)             │                │                    │
│ category_id (FK)    │◄───────┐       │                    │
│ title               │        │       ▼                    │
│ definition          │        │┌─────────────────────┐     │
│ key_behavior        │        ││      SESSION        │     │
│ key_mindset         │        │├─────────────────────┤     │
│ coaching_question   │        ││ id (PK)             │     │
│ order               │        ││ user_id (FK)        │◄────┘
│ is_active           │        ││ customer_name       │
│ created_at          │        ││ opportunity_name    │
│ updated_at          │        ││ decision_influencer │
└─────────────────────┘        ││ deal_stage          │
         │                     ││ status              │
         │                     ││ submitted_at        │
         │                     ││ completed_at        │
         │                     ││ is_synced           │
         │                     ││ created_at          │
         │                     ││ updated_at          │
         │                     │└─────────────────────┘
         │                     │         │
         │                     │         ├──────────────────────────┐
         │                     │         │                          │
         │                     │         ▼                          ▼
         │                     │ ┌─────────────────────┐   ┌─────────────────────┐
         │                     │ │     AUDIO_FILE      │   │     TRANSCRIPT      │
         │                     │ ├─────────────────────┤   ├─────────────────────┤
         │                     │ │ id (PK)             │   │ id (PK)             │
         │                     │ │ session_id (FK)     │   │ session_id (FK)     │
         │                     │ │ filename            │   │ text                │
         │                     │ │ file_path           │   │ language            │
         │                     │ │ storage_type        │   │ duration            │
         │                     │ │ file_size           │   │ words_count         │
         │                     │ │ duration_seconds    │   │ transcribed_at      │
         │                     │ │ mime_type           │   │ processing_time     │
         │                     │ │ created_at          │   │ created_at          │
         │                     │ │ updated_at          │   │ updated_at          │
         │                     │ └─────────────────────┘   └─────────────────────┘
         │                     │
         │                     │         ├──────────────────────────┐
         │                     │         │                          │
         ▼                     │         ▼                          ▼
┌─────────────────────┐        │ ┌─────────────────────┐   ┌─────────────────────┐
│  SESSION_RESPONSE   │        │ │   SCORING_RESULT    │   │  COACHING_FEEDBACK  │
├─────────────────────┤        │ ├─────────────────────┤   ├─────────────────────┤
│ id (PK)             │        │ │ id (PK)             │   │ id (PK)             │
│ session_id (FK)     │◄───────┘ │ session_id (FK)     │   │ session_id (FK)     │
│ item_id (FK)        │◄─────────│ total_score         │   │ feedback_text       │
│ is_validated        │          │ risk_band           │   │ strengths           │
│ confidence          │          │ category_scores     │   │ improvement_areas   │
│ evidence_text       │          │ top_strengths       │   │ action_items        │
│ ai_reasoning        │          │ top_gaps            │   │ audio_s3_bucket     │
│ manual_override     │          │ items_validated     │   │ audio_s3_key        │
│ override_by_user_id │          │ items_total         │   │ audio_duration      │
│ override_reason     │          │ created_at          │   │ generated_at        │
│ created_at          │          │ updated_at          │   │ created_at          │
│ updated_at          │          └─────────────────────┘   │ updated_at          │
└─────────────────────┘                                    └─────────────────────┘
                                          │
                                          ▼
                                 ┌─────────────────────┐
                                 │       REPORT        │
                                 ├─────────────────────┤
                                 │ id (PK)             │
                                 │ session_id (FK)     │
                                 │ pdf_s3_bucket       │
                                 │ pdf_s3_key          │
                                 │ pdf_file_size       │
                                 │ generated_at        │
                                 │ is_generated        │
                                 │ emailed_at          │
                                 │ emailed_to          │
                                 │ created_at          │
                                 │ updated_at          │
                                 └─────────────────────┘
```

### 3.2 Relationship Summary

| Parent Entity | Child Entity | Relationship | Foreign Key |
|---------------|--------------|--------------|-------------|
| Organization | Team | 1:N | team.organization_id |
| Organization | User | 1:N | user.organization_id |
| Team | User | 1:N | user.team_id |
| User | Session | 1:N | session.user_id |
| Session | AudioFile | 1:1 | audio_file.session_id |
| Session | Transcript | 1:1 | transcript.session_id |
| Session | SessionResponse | 1:N | session_response.session_id |
| Session | ScoringResult | 1:1 | scoring_result.session_id |
| Session | CoachingFeedback | 1:1 | coaching_feedback.session_id |
| Session | Report | 1:1 | report.session_id |
| ChecklistCategory | ChecklistItem | 1:N | checklist_item.category_id |
| ChecklistItem | SessionResponse | 1:N | session_response.item_id |

---

## 4. Database Schema

### 4.1 Tables Overview

| Table | Description | Records |
|-------|-------------|---------|
| `organizations` | Companies using the platform | - |
| `teams` | Teams within organizations | - |
| `users` | All user accounts | - |
| `checklist_categories` | 10 sales categories | 10 |
| `checklist_items` | 92 checklist items | 92 |
| `sessions` | Sales call sessions | Dynamic |
| `audio_files` | Audio file metadata | 1 per session |
| `transcripts` | Whisper transcription results | 1 per session |
| `session_responses` | AI validation per item | 92 per session |
| `scoring_results` | Calculated scores | 1 per session |
| `coaching_feedback` | AI coaching text + audio | 1 per session |
| `reports` | PDF report metadata | 1 per session |
| `audit_logs` | System audit trail | Dynamic |
| `settings` | System configuration | - |

### 4.2 Checklist Categories (10)

| # | Category Name | Description | Items |
|---|---------------|-------------|-------|
| 1 | Trigger Event & Impact | Why the customer is buying | 10 |
| 2 | Trigger Priority | Is this truly a priority? | 8 |
| 3 | Sales Target | What, how much, when they plan to buy | 8 |
| 4 | Decision Influencer | Who influences the purchase decision | 7 |
| 5 | Individual Impact | Impact on decision influencers | 8 |
| 6 | Mentor | Internal champion for the deal | 12 |
| 7 | Decision Making Process | How the organization makes decisions | 12 |
| 8 | Fit | How well solution fits requirements | 10 |
| 9 | Alternatives | Competitive alternatives considered | 8 |
| 10 | Our Solution Ranking | How we rank vs. competitors | 9 |

**Total: 92 items**

### 4.3 Session Status Flow

```
DRAFT → UPLOADING → PROCESSING → ANALYZING → SCORING → COMPLETED
                                                   ↓
                                                FAILED
```

| Status | Description |
|--------|-------------|
| `draft` | Session created, no audio |
| `uploading` | Audio file being uploaded |
| `processing` | Whisper transcription in progress |
| `analyzing` | GPT-4 analyzing transcript |
| `scoring` | Calculating scores |
| `completed` | All processing done |
| `failed` | Error occurred |

### 4.4 Risk Bands

| Band | Score Range | Label | Color |
|------|-------------|-------|-------|
| Green | 80-100 | Healthy | #27ae60 |
| Yellow | 60-79 | Caution | #f39c12 |
| Red | 0-59 | At Risk | #e74c3c |

---

## 5. API Endpoints Reference

### 5.1 Authentication Endpoints

#### `POST /register` - Register New User
```json
// Request
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe"
}

// Response (201 Created)
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "rep",
  "is_active": true,
  "is_verified": false,
  "message": "Registration successful. Please verify your email."
}
```

#### `POST /login` - User Login
```json
// Request
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}

// Response (200 OK)
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 604800,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "rep"
  }
}
```

#### `POST /forgot-password` - Request Password Reset
```json
// Request
{ "email": "user@example.com" }

// Response (200 OK)
{ "message": "Password reset email sent" }
```

#### `POST /reset-password` - Reset Password
```json
// Request
{
  "token": "reset_token_here",
  "new_password": "NewSecurePass123!"
}

// Response (200 OK)
{ "message": "Password reset successful" }
```

---

### 5.2 Checklist Endpoints

#### `GET /checklists/summary` - Get Overview
```json
// Response (200 OK)
{
  "total_categories": 10,
  "total_items": 92,
  "categories": [
    {
      "id": 31,
      "name": "Trigger Event & Impact",
      "description": "Why the customer is buying...",
      "order": 1,
      "default_weight": 1.0,
      "max_score": 10,
      "is_active": true
    }
    // ... 9 more categories
  ]
}
```

#### `GET /checklists/categories` - List All Categories
#### `GET /checklists/categories/{id}` - Get Category with Items
#### `GET /checklists/items` - List All Items
#### `GET /checklists/items/{id}` - Get Item Details

---

### 5.3 Session Endpoints

#### `POST /sessions/` - Create Session
```json
// Request
{
  "customer_name": "Acme Corp",
  "opportunity_name": "Enterprise Deal Q4",
  "deal_stage": "Discovery",
  "decision_influencer": "John Smith, CTO"
}

// Response (201 Created)
{
  "id": 15,
  "user_id": 7,
  "customer_name": "Acme Corp",
  "opportunity_name": "Enterprise Deal Q4",
  "deal_stage": "Discovery",
  "status": "draft",
  "created_at": "2024-11-24T09:00:12.378133"
}
```

#### `GET /sessions/` - List User's Sessions
```json
// Response (200 OK)
{
  "total": 15,
  "sessions": [
    {
      "id": 15,
      "customer_name": "Acme Corp",
      "status": "completed",
      "score": 75,
      "risk_band": "yellow",
      "created_at": "2024-11-24T09:00:12"
    }
  ]
}
```

#### `GET /sessions/{id}` - Get Session Details
#### `PATCH /sessions/{id}` - Update Session
#### `DELETE /sessions/{id}` - Delete Session

---

### 5.4 Upload Endpoints

#### `POST /sessions/{id}/upload` - Upload Audio File
```bash
# Request (multipart/form-data)
curl -X POST "http://localhost:8000/api/v1/sessions/15/upload" \
  -H "Authorization: Bearer {token}" \
  -F "audio_file=@recording.webm"
```

```json
// Response (201 Created)
{
  "id": 5,
  "session_id": 15,
  "filename": "15_abc123.webm",
  "file_size": 2457600,
  "mime_type": "audio/webm",
  "storage_type": "s3",
  "file_path": "https://sales-checklist-audio.s3.us-east-2.amazonaws.com/...",
  "message": "Audio file uploaded successfully to s3"
}
```

#### `GET /sessions/{id}/audio` - Get Audio File Info

---

### 5.5 Transcription Endpoints

#### `POST /sessions/{id}/transcribe` - Start Transcription
```json
// Response (202 Accepted)
{
  "message": "Transcription started",
  "session_id": 15,
  "status": "processing"
}
```

**Background Process:**
1. Downloads audio from S3/local
2. Sends to OpenAI Whisper API
3. Saves transcript to database
4. Triggers GPT-4 analysis
5. Creates session responses
6. Updates session status

#### `GET /sessions/{id}/transcript` - Get Transcript
```json
// Response (200 OK)
{
  "session_id": 15,
  "transcript": {
    "id": 3,
    "text": "Hello, thank you for taking this call...",
    "language": "en",
    "duration_seconds": 1847.5,
    "word_count": 3521,
    "created_at": "2024-11-24T09:15:30"
  }
}
```

---

### 5.6 Response Endpoints

#### `POST /sessions/{id}/responses/initialize` - Initialize Responses
```json
// Response (200 OK)
{
  "session_id": 15,
  "total_items": 92,
  "message": "Initialized 92 empty responses"
}
```

#### `GET /sessions/{id}/responses` - Get All Responses
```json
// Response (200 OK)
{
  "session_id": 15,
  "total_items": 92,
  "responses": [
    {
      "id": 1,
      "item_id": 571,
      "is_validated": true,
      "confidence": 0.85,
      "evidence_text": "Customer mentioned budget approval...",
      "manual_override": false,
      "item": {
        "id": 571,
        "title": "Trigger Event & Impact - Part 1",
        "category": {
          "id": 31,
          "name": "Trigger Event & Impact"
        }
      }
    }
    // ... 91 more responses
  ]
}
```

#### `PATCH /sessions/{id}/responses/{item_id}` - Update Response
```json
// Request
{
  "is_validated": true,
  "manual_override": true
}

// Response (200 OK)
{
  "id": 1,
  "item_id": 571,
  "is_validated": true,
  "manual_override": true,
  "message": "Response updated successfully"
}
```

---

### 5.7 Scoring Endpoints

#### `POST /sessions/{id}/calculate` - Calculate Score
```json
// Response (201 Created)
{
  "session_id": 15,
  "total_score": 65,
  "max_possible_score": 100,
  "percentage": 65.0,
  "risk_band": "yellow",
  "risk_label": "Caution",
  "category_breakdown": [
    {
      "name": "Trigger Event & Impact",
      "score": 70,
      "max_score": 100,
      "items": [...]
    }
    // ... 9 more categories
  ],
  "strengths": [
    { "id": 571, "title": "Trigger Event Identified", "category": "Trigger Event & Impact", "score": 10 }
  ],
  "gaps": [
    { "id": 590, "title": "Decision Process Mapped", "category": "Decision Making Process", "score": 0 }
  ],
  "summary": {
    "validated_items": 60,
    "unvalidated_items": 32,
    "total_items": 92
  },
  "scoring_result_id": 6
}
```

#### `GET /sessions/{id}/score` - Get Existing Score

---

### 5.8 Coaching Endpoints

#### `POST /sessions/{id}/coaching` - Generate Coaching Feedback
```json
// Query Parameters
// ?include_audio=true (default: true)

// Response (201 Created)
{
  "session_id": 15,
  "coaching_id": 2,
  "feedback_text": "Great effort on this sales call! Your strongest areas were...",
  "strengths": [
    {
      "point": "Trigger Event Identification",
      "explanation": "You effectively identified the customer's pain point..."
    }
  ],
  "improvement_areas": [
    {
      "point": "Decision Process Mapping",
      "explanation": "Consider asking more about their approval process..."
    }
  ],
  "action_items": [
    "For your next call, prepare 3 questions about their decision timeline",
    "Research the company's recent announcements before the call",
    "Create a stakeholder map before the meeting"
  ],
  "audio_url": "https://sales-checklist-audio.s3.us-east-2.amazonaws.com/coaching/7/15/feedback.mp3",
  "audio_duration": 71,
  "generated_at": "2024-11-24T10:04:49.792890",
  "message": "Coaching feedback generated successfully"
}
```

#### `GET /sessions/{id}/coaching` - Get Existing Coaching
#### `POST /sessions/{id}/coaching/regenerate` - Regenerate Coaching

---

### 5.9 Report Endpoints

#### `POST /sessions/{id}/report` - Generate PDF Report
```json
// Query Parameters
// ?include_checklist_details=true (default: true)

// Response (201 Created)
{
  "session_id": 15,
  "report_id": 1,
  "pdf_url": "uploads/reports/7/15/report_20241124_091150.pdf",
  "file_size": 8878,
  "generated_at": "2024-11-24T09:11:50.339311",
  "message": "Report generated successfully"
}
```

#### `GET /sessions/{id}/report` - Get Report Metadata
#### `GET /sessions/{id}/report/download` - Download PDF File
#### `POST /sessions/{id}/report/email` - Email Report
```json
// Request
{ "recipient_email": "manager@company.com" }

// Response (200 OK)
{
  "session_id": 15,
  "emailed_to": "manager@company.com",
  "emailed_at": "2024-11-24T10:30:00",
  "message": "Report emailed successfully"
}
```

#### `POST /sessions/{id}/report/regenerate` - Regenerate Report

---

### 5.10 User Endpoints

#### `GET /users/me` - Get Current User Profile
#### `PATCH /users/me` - Update Profile
#### `GET /users/me/team` - Get User's Team
#### `GET /users/me/organization` - Get User's Organization

---

## 6. Complete User Flow

### 6.1 End-to-End Session Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    COMPLETE SESSION FLOW                        │
└─────────────────────────────────────────────────────────────────┘

Step 1: CREATE SESSION
────────────────────────
POST /api/v1/sessions/
{
  "customer_name": "Acme Corp",
  "opportunity_name": "Q4 Enterprise Deal"
}
         │
         ▼
Step 2: UPLOAD AUDIO
────────────────────────
POST /api/v1/sessions/{id}/upload
[audio_file: recording.webm]
         │
         ▼
Step 3: TRANSCRIBE (Background)
────────────────────────────────
POST /api/v1/sessions/{id}/transcribe

   ┌────────────────────────────────┐
   │     BACKGROUND PROCESSING      │
   │                                │
   │  1. Download audio from S3    │
   │  2. Send to OpenAI Whisper    │
   │  3. Save transcript           │
   │  4. Send to GPT-4 for analysis│
   │  5. Create 92 responses       │
   │  6. Update session status     │
   │                                │
   └────────────────────────────────┘
         │
         ▼
Step 4: INITIALIZE RESPONSES (if not auto)
──────────────────────────────────────────
POST /api/v1/sessions/{id}/responses/initialize

         │
         ▼
Step 5: REVIEW & UPDATE RESPONSES (Optional)
────────────────────────────────────────────
GET /api/v1/sessions/{id}/responses
PATCH /api/v1/sessions/{id}/responses/{item_id}
         │
         ▼
Step 6: CALCULATE SCORE
────────────────────────
POST /api/v1/sessions/{id}/calculate
         │
         ▼
Step 7: GENERATE COACHING
──────────────────────────
POST /api/v1/sessions/{id}/coaching?include_audio=true

   ┌────────────────────────────────┐
   │     AI COACHING GENERATION     │
   │                                │
   │  1. Send data to GPT-4        │
   │  2. Generate personalized     │
   │     coaching feedback         │
   │  3. Convert to audio via      │
   │     ElevenLabs TTS            │
   │  4. Upload audio to S3        │
   │  5. Save coaching record      │
   │                                │
   └────────────────────────────────┘
         │
         ▼
Step 8: GENERATE REPORT
────────────────────────
POST /api/v1/sessions/{id}/report

   ┌────────────────────────────────┐
   │      PDF REPORT GENERATION     │
   │                                │
   │  1. Gather session data       │
   │  2. Include scoring results   │
   │  3. Include coaching feedback │
   │  4. Generate PDF with         │
   │     ReportLab                 │
   │  5. Upload to S3              │
   │  6. Save report metadata      │
   │                                │
   └────────────────────────────────┘
         │
         ▼
Step 9: EMAIL REPORT (Optional)
────────────────────────────────
POST /api/v1/sessions/{id}/report/email
{
  "recipient_email": "manager@company.com"
}
         │
         ▼
      ✅ DONE
```

### 6.2 API Call Sequence Diagram

```
Client              API                 Database            External Services
  │                  │                     │                      │
  │ POST /sessions   │                     │                      │
  │─────────────────►│                     │                      │
  │                  │ INSERT session      │                      │
  │                  │────────────────────►│                      │
  │                  │◄────────────────────│                      │
  │◄─────────────────│                     │                      │
  │                  │                     │                      │
  │ POST /upload     │                     │                      │
  │─────────────────►│                     │                      │
  │                  │                     │    Upload to S3      │
  │                  │────────────────────────────────────────────►│
  │                  │◄────────────────────────────────────────────│
  │                  │ INSERT audio_file   │                      │
  │                  │────────────────────►│                      │
  │◄─────────────────│                     │                      │
  │                  │                     │                      │
  │ POST /transcribe │                     │                      │
  │─────────────────►│                     │                      │
  │◄─────────────────│ (202 Accepted)      │                      │
  │                  │                     │                      │
  │                  │           [Background Task]                │
  │                  │                     │   OpenAI Whisper     │
  │                  │────────────────────────────────────────────►│
  │                  │◄────────────────────────────────────────────│
  │                  │ INSERT transcript   │                      │
  │                  │────────────────────►│                      │
  │                  │                     │   OpenAI GPT-4       │
  │                  │────────────────────────────────────────────►│
  │                  │◄────────────────────────────────────────────│
  │                  │ INSERT responses    │                      │
  │                  │────────────────────►│                      │
  │                  │                     │                      │
  │ POST /calculate  │                     │                      │
  │─────────────────►│                     │                      │
  │                  │ SELECT responses    │                      │
  │                  │────────────────────►│                      │
  │                  │◄────────────────────│                      │
  │                  │ INSERT scoring      │                      │
  │                  │────────────────────►│                      │
  │◄─────────────────│                     │                      │
  │                  │                     │                      │
  │ POST /coaching   │                     │                      │
  │─────────────────►│                     │                      │
  │                  │                     │   OpenAI GPT-4       │
  │                  │────────────────────────────────────────────►│
  │                  │◄────────────────────────────────────────────│
  │                  │                     │   ElevenLabs TTS     │
  │                  │────────────────────────────────────────────►│
  │                  │◄────────────────────────────────────────────│
  │                  │                     │   Upload to S3       │
  │                  │────────────────────────────────────────────►│
  │                  │◄────────────────────────────────────────────│
  │                  │ INSERT coaching     │                      │
  │                  │────────────────────►│                      │
  │◄─────────────────│                     │                      │
  │                  │                     │                      │
  │ POST /report     │                     │                      │
  │─────────────────►│                     │                      │
  │                  │ SELECT all data     │                      │
  │                  │────────────────────►│                      │
  │                  │◄────────────────────│                      │
  │                  │ [Generate PDF]      │                      │
  │                  │                     │   Upload to S3       │
  │                  │────────────────────────────────────────────►│
  │                  │◄────────────────────────────────────────────│
  │                  │ INSERT report       │                      │
  │                  │────────────────────►│                      │
  │◄─────────────────│                     │                      │
  │                  │                     │                      │
```

---

## 7. Integration Status

### 7.1 Current Status

| Integration | Status | Tested | Notes |
|-------------|--------|--------|-------|
| **PostgreSQL (Neon)** | ✅ Working | Yes | All CRUD operations verified |
| **OpenAI GPT-4** | ✅ Working | Yes | Coaching generation tested |
| **OpenAI Whisper** | ✅ Working | Yes | Transcription tested - 187 chars from 10.9s audio |
| **ElevenLabs TTS** | ✅ Working | Yes | 71-second audio generated |
| **AWS S3** | ✅ Working | Yes | Audio/reports uploaded successfully |
| **AWS SES** | ✅ Working | Yes | Email sent successfully (sandbox: 200/day limit) |
| **Salesforce** | ❌ Deferred | No | Planned for future release |
| **Redis/Celery** | ⚠️ Ready | No | Config exists, not started |

### 7.2 Test Results Summary (November 24, 2024)

| Test | Result | Details |
|------|--------|---------|
| **Whisper Transcription** | ✅ PASSED | Audio: 484KB WAV, Duration: 10.9s, 187 chars transcribed |
| **GPT-4 Coaching** | ✅ PASSED | Personalized coaching generated in <5s |
| **ElevenLabs TTS** | ✅ PASSED | 71-second coaching audio generated |
| **S3 Upload** | ✅ PASSED | Files uploaded to both audio and reports buckets |
| **SES Email** | ✅ PASSED | Test email delivered, quota: 200/day (sandbox) |
| **PDF Report** | ✅ PASSED | 8.8KB professional PDF generated |

### 7.3 Environment Variables Required

```env
# Database
DATABASE_URL=postgresql+asyncpg://...

# Authentication
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# AWS
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-2
S3_BUCKET_AUDIO=sales-checklist-audio
S3_BUCKET_REPORTS=sales-checklist-reports

# AWS SES
SES_REGION=us-east-2
SES_SENDER_EMAIL=noreply@yourdomain.com

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL_WHISPER=whisper-1
OPENAI_MODEL_GPT=gpt-4-turbo-preview

# ElevenLabs
ELEVENLABS_API_KEY=sk_...
ELEVENLABS_VOICE_ID=2EiwWnXFnvU5JabPnv8n
```

---

## 8. Testing Guide

### 8.1 Local Testing Setup

```bash
# 1. Clone repository
cd sales-checklist-backend

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
cp .env.example .env
# Edit .env with your values

# 5. Run migrations
alembic upgrade head

# 6. Start server
uvicorn app.main:app --reload --port 8000

# 7. Access docs
open http://localhost:8000/api/v1/docs
```

### 8.2 Test Script

```bash
#!/bin/bash
BASE_URL="http://localhost:8000/api/v1"

echo "=== Testing Sales Checklist API ==="

# 1. Test API Root
echo "\n1. Testing API Root..."
curl -s "$BASE_URL/"

# 2. Test Checklists
echo "\n\n2. Testing Checklists..."
curl -s "$BASE_URL/checklists/summary"

# 3. Create Session
echo "\n\n3. Creating Session..."
SESSION=$(curl -s -X POST "$BASE_URL/sessions/" \
  -H "Content-Type: application/json" \
  -d '{"customer_name": "Test Company", "opportunity_name": "Test Deal"}')
echo $SESSION
SESSION_ID=$(echo $SESSION | jq -r '.id')

# 4. Initialize Responses
echo "\n\n4. Initializing Responses..."
curl -s -X POST "$BASE_URL/sessions/$SESSION_ID/responses/initialize"

# 5. Calculate Score
echo "\n\n5. Calculating Score..."
curl -s -X POST "$BASE_URL/sessions/$SESSION_ID/calculate"

# 6. Generate Coaching (without audio for speed)
echo "\n\n6. Generating Coaching..."
curl -s -X POST "$BASE_URL/sessions/$SESSION_ID/coaching?include_audio=false"

# 7. Generate Report
echo "\n\n7. Generating Report..."
curl -s -X POST "$BASE_URL/sessions/$SESSION_ID/report"

echo "\n\n=== All Tests Complete ==="
```

### 8.3 Expected Test Results

| Test | Expected Status | Response |
|------|-----------------|----------|
| API Root | 200 OK | Version info |
| Checklists Summary | 200 OK | 10 categories, 92 items |
| Create Session | 201 Created | Session ID returned |
| Initialize Responses | 200 OK | 92 responses created |
| Calculate Score | 201 Created | Score with risk band |
| Generate Coaching | 201 Created | Feedback text + audio URL |
| Generate Report | 201 Created | PDF URL + file size |

---

## 9. Error Handling

### 9.1 Standard Error Response Format

```json
{
  "detail": "Error message here"
}
```

### 9.2 HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | OK | Successful GET/PATCH |
| 201 | Created | Successful POST |
| 202 | Accepted | Background task started |
| 400 | Bad Request | Invalid input data |
| 401 | Unauthorized | Missing/invalid token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate resource |
| 422 | Validation Error | Invalid request body |
| 500 | Server Error | Internal error |

### 9.3 Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Session not found" | Invalid session ID | Verify session ID exists |
| "Session must be scored first" | Missing prerequisite | Run /calculate first |
| "No audio file found" | Audio not uploaded | Upload audio first |
| "Transcript already exists" | Duplicate transcription | Use existing transcript |

---

## 10. Deployment Checklist

### 10.1 Pre-Deployment

- [ ] All environment variables configured
- [ ] Database migrations run
- [ ] AWS S3 buckets created
- [ ] AWS SES sender email verified
- [ ] OpenAI API key active
- [ ] ElevenLabs API key active
- [ ] SSL certificate configured
- [ ] CORS origins configured
- [ ] Rate limiting configured

### 10.2 Post-Deployment Verification

- [ ] Health check endpoint responding
- [ ] Database connection working
- [ ] S3 uploads working
- [ ] Email sending working
- [ ] OpenAI API responding
- [ ] ElevenLabs API responding
- [ ] All API endpoints accessible
- [ ] Authentication working

### 10.3 Monitoring

- [ ] Sentry error tracking enabled
- [ ] CloudWatch logs configured
- [ ] API metrics dashboard
- [ ] Database connection pooling
- [ ] Background task monitoring

---

## Appendix A: File Structure

```
sales-checklist-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry
│   ├── api/
│   │   ├── __init__.py
│   │   ├── dependencies.py     # Auth dependencies
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── api.py          # Router registration
│   │       └── endpoints/
│   │           ├── auth.py
│   │           ├── checklists.py
│   │           ├── sessions.py
│   │           ├── uploads.py
│   │           ├── transcription.py
│   │           ├── responses_simple.py
│   │           ├── scoring.py
│   │           ├── coaching.py
│   │           ├── reports.py
│   │           └── users.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py           # Settings
│   ├── db/
│   │   ├── __init__.py
│   │   └── session.py          # Database session
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── session.py
│   │   ├── checklist.py
│   │   ├── scoring.py
│   │   └── report.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py
│   └── services/
│       ├── __init__.py
│       ├── auth_service.py
│       ├── s3_service.py
│       ├── transcription_service.py
│       ├── coaching_service.py
│       ├── report_service.py
│       └── email_service.py
├── alembic/                    # Database migrations
├── docs/                       # Documentation
├── tests/                      # Test files
├── uploads/                    # Local file storage
├── .env                        # Environment variables
├── .env.example               # Environment template
├── .env.production            # Production template
├── requirements.txt           # Python dependencies
├── alembic.ini               # Alembic config
└── README.md
```

---

## Appendix B: API Response Examples

See individual endpoint sections for request/response examples.

---

**Document Version:** 1.0.0
**Created:** November 24, 2024
**Last Updated:** November 24, 2024
