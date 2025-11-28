# Sales Checklist - Database ERD & Role Documentation

**Version:** 1.0.0
**Last Updated:** November 24, 2024
**Author:** Engineering Team

---

## Table of Contents

1. [Role-Based Access Control (RBAC)](#1-role-based-access-control-rbac)
2. [Role Permissions Matrix](#2-role-permissions-matrix)
3. [Entity Relationship Diagram (ERD)](#3-entity-relationship-diagram-erd)
4. [Table Descriptions](#4-table-descriptions)
5. [Relationship Summary](#5-relationship-summary)
6. [Enums & Constants](#6-enums--constants)

---

## 1. Role-Based Access Control (RBAC)

The system implements a hierarchical role-based access control system with three roles:

| Role | Level | Description |
|------|-------|-------------|
| **ADMIN** | Highest | Full system access, can manage all users, organizations, teams, and system settings |
| **MANAGER** | Mid | Team-level access, can view team members' sessions and override AI scores |
| **REP** | Basic | Individual access, can only manage their own sessions and data |

### Role Hierarchy

```
        ADMIN (Full Access)
            │
            ▼
        MANAGER (Team Access)
            │
            ▼
        REP (Self Access)
```

---

## 2. Role Permissions Matrix

| Feature | ADMIN | MANAGER | REP |
|---------|:-----:|:-------:|:---:|
| **Session Management** |
| Create Sessions | All users | Team only | Own only |
| View Sessions | All users | Team only | Own only |
| Delete Sessions | All users | Team only | Own only |
| **Audio & Transcription** |
| Upload Audio | Yes | Yes | Yes |
| View Transcripts | All | Team | Own |
| **Scoring & Analysis** |
| View Scores | All | Team | Own |
| Override AI Scores | Yes | Yes | No |
| **Reports & Coaching** |
| Generate Reports | All | Team | Own |
| View Coaching Feedback | All | Team | Own |
| Email Reports | All | Team | Own |
| **Administration** |
| Manage Users | Yes | No | No |
| Manage Organizations | Yes | No | No |
| Manage Teams | Yes | No | No |
| Manage Checklist Items | Yes | No | No |
| View Audit Logs | Yes | No | No |
| System Settings | Yes | No | No |

---

## 3. Entity Relationship Diagram (ERD)

### 3.1 Visual ERD

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           SALES CHECKLIST - DATABASE ERD                                 │
└─────────────────────────────────────────────────────────────────────────────────────────┘

 ┌──────────────────────┐          ┌──────────────────────┐
 │    ORGANIZATIONS     │          │        TEAMS         │
 ├──────────────────────┤          ├──────────────────────┤
 │ PK id                │──────┐   │ PK id                │
 │    name              │      │   │ FK organization_id   │───┐
 │    domain            │      │   │    name              │   │
 │    is_active         │      │   │    description       │   │
 │    scoring_mode      │      │   │    is_active         │   │
 │    max_users         │      │   │    created_at        │   │
 │    created_at        │      │   └──────────────────────┘   │
 └──────────────────────┘      │                              │
                               │   1:N                        │
                               └────────────────┬─────────────┘
                                                │
                                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │                          USERS                                │
 ├──────────────────────────────────────────────────────────────┤
 │ PK id                                                         │
 │    email (unique)                                             │
 │    password_hash                                              │
 │    first_name, last_name                                      │
 │    role (ADMIN/MANAGER/REP)                                   │
 │ FK organization_id                                            │
 │ FK team_id                                                    │
 │    is_active, is_verified                                     │
 │    last_login, failed_login_attempts, locked_until            │
 │    password_reset_token, password_reset_expires               │
 │    email_verification_token, email_verification_expires       │
 │    created_at, updated_at                                     │
 └──────────────────────────────────────────────────────────────┘
           │
           │ 1:N (User owns many Sessions)
           │
           ▼
 ┌──────────────────────────────────────────────────────────────┐
 │                        SESSIONS                               │
 │              (Main Entity - Sales Call Recording)             │
 ├──────────────────────────────────────────────────────────────┤
 │ PK id                                                         │
 │ FK user_id                                                    │
 │    customer_name                                              │
 │    opportunity_name                                           │
 │    decision_influencer                                        │
 │    deal_stage                                                 │
 │    status (DRAFT/UPLOADING/PROCESSING/ANALYZING/              │
 │            SCORING/COMPLETED/FAILED)                          │
 │    submitted_at, completed_at                                 │
 │    is_synced, sync_attempted_at                               │
 │    created_at, updated_at                                     │
 └──────────────────────────────────────────────────────────────┘
           │
           ├───────────────────────────────────────────────────────────────┐
           │                                                               │
           │ 1:1                                                           │
           ▼                                                               │
 ┌────────────────────────┐   ┌────────────────────────┐                  │
 │      AUDIO_FILES       │   │      TRANSCRIPTS       │                  │
 ├────────────────────────┤   ├────────────────────────┤                  │
 │ PK id                  │   │ PK id                  │                  │
 │ FK session_id (unique) │   │ FK session_id (unique) │                  │
 │    filename            │   │    text                │                  │
 │    file_path (S3 URL)  │   │    language            │                  │
 │    storage_type        │   │    duration            │                  │
 │    file_size           │   │    words_count         │                  │
 │    duration_seconds    │   │    transcribed_at      │                  │
 │    mime_type           │   │    processing_time     │                  │
 │    created_at          │   │    openai_request_id   │                  │
 └────────────────────────┘   └────────────────────────┘                  │
                                                                          │
           ┌──────────────────────────────────────────────────────────────┘
           │
           │ 1:N (Session has many Responses - one per checklist item)
           ▼
 ┌──────────────────────────────────────────────────────────────┐
 │                    SESSION_RESPONSES                          │
 │          (AI Analysis Results for Each Item)                  │
 ├──────────────────────────────────────────────────────────────┤
 │ PK id                                                         │
 │ FK session_id                                                 │
 │ FK item_id ─────────────────────────────────────────────────┐│
 │    is_validated (True/False/Null)                           ││
 │    confidence (0.0 - 1.0)                                   ││
 │    evidence_text (quote from transcript)                    ││
 │    ai_reasoning                                             ││
 │    manual_override (ADMIN/MANAGER can override)             ││
 │    override_by_user_id                                      ││
 │    override_reason                                          ││
 │    created_at                                               ││
 └──────────────────────────────────────────────────────────────┘│
                                                                 │
           ┌─────────────────────────────────────────────────────┘
           │
           │ N:1 (References Checklist Items)
           ▼
 ┌──────────────────────────────────────────────────────────────┐
 │                   CHECKLIST_CATEGORIES                        │
 │                      (10 Categories)                          │
 ├──────────────────────────────────────────────────────────────┤
 │ PK id                                                         │
 │    name (unique)                                              │
 │    description                                                │
 │    order (1-10)                                               │
 │    default_weight                                             │
 │    max_score                                                  │
 │    is_active                                                  │
 └──────────────────────────────────────────────────────────────┘
           │
           │ 1:N
           ▼
 ┌──────────────────────────────────────────────────────────────┐
 │                    CHECKLIST_ITEMS                            │
 │                      (92 Items)                               │
 ├──────────────────────────────────────────────────────────────┤
 │ PK id                                                         │
 │ FK category_id                                                │
 │    title                                                      │
 │    definition                                                 │
 │    key_behavior                                               │
 │    key_mindset                                                │
 │    order                                                      │
 │    weight                                                     │
 │    points (default: 1.087 = 100/92)                          │
 │    is_active                                                  │
 └──────────────────────────────────────────────────────────────┘
           │
           │ 1:N
           ▼
 ┌──────────────────────────────────────────────────────────────┐
 │                  COACHING_QUESTIONS                           │
 │            (4-8 questions per checklist item)                 │
 ├──────────────────────────────────────────────────────────────┤
 │ PK id                                                         │
 │ FK item_id                                                    │
 │    section                                                    │
 │    question                                                   │
 │    order                                                      │
 │    is_active                                                  │
 └──────────────────────────────────────────────────────────────┘
```

### 3.2 Session Output Entities (1:1 with Session)

```
 ┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐
 │    SCORING_RESULTS     │  │   COACHING_FEEDBACK    │  │        REPORTS         │
 ├────────────────────────┤  ├────────────────────────┤  ├────────────────────────┤
 │ PK id                  │  │ PK id                  │  │ PK id                  │
 │ FK session_id (unique) │  │ FK session_id (unique) │  │ FK session_id (unique) │
 │    total_score (0-100) │  │    feedback_text       │  │    pdf_s3_bucket       │
 │    risk_band           │  │    strengths (JSON)    │  │    pdf_s3_key          │
 │    (GREEN/YELLOW/RED)  │  │    improvement_areas   │  │    pdf_file_size       │
 │    category_scores     │  │    action_items (JSON) │  │    generated_at        │
 │    (JSON)              │  │    audio_s3_bucket     │  │    is_generated        │
 │    top_strengths       │  │    audio_s3_key        │  │    emailed_at          │
 │    top_gaps (JSON)     │  │    audio_duration      │  │    emailed_to          │
 │    previous_score      │  │    generated_at        │  └────────────────────────┘
 │    score_change        │  │    openai_request_id   │
 │    items_validated     │  └────────────────────────┘
 │    items_total (92)    │
 └────────────────────────┘
```

### 3.3 System Tables

```
 ┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐
 │      AUDIT_LOGS        │  │      SETTINGS          │  │   SALESFORCE_SYNC      │
 ├────────────────────────┤  ├────────────────────────┤  ├────────────────────────┤
 │ PK id                  │  │ PK id                  │  │ PK id                  │
 │ FK user_id             │  │    key (unique)        │  │ FK session_id          │
 │    action              │  │    value               │  │    sf_object_type      │
 │    entity_type         │  │    description         │  │    sf_object_id        │
 │    entity_id           │  └────────────────────────┘  │    is_synced           │
 │    changes (JSON)      │                              │    synced_at           │
 │    ip_address          │                              │    sync_error          │
 │    user_agent          │                              │    fields_synced       │
 └────────────────────────┘                              └────────────────────────┘
```

---

## 4. Table Descriptions

### 4.1 Core User Management

| Table | Description | Records |
|-------|-------------|---------|
| **organizations** | Companies/organizations using the platform | Variable |
| **teams** | Teams within organizations | Variable |
| **users** | User accounts with authentication | Variable |

### 4.2 Session & Analysis

| Table | Description | Records |
|-------|-------------|---------|
| **sessions** | Sales call recording sessions | Variable |
| **audio_files** | Uploaded audio file metadata | 1 per session |
| **transcripts** | OpenAI Whisper transcription results | 1 per session |
| **session_responses** | AI analysis for each checklist item | 92 per session |

### 4.3 Checklist Framework

| Table | Description | Records |
|-------|-------------|---------|
| **checklist_categories** | 10 main categories | 10 (fixed) |
| **checklist_items** | Individual checklist items | 92 (fixed) |
| **coaching_questions** | Questions for coaching | 4-8 per item |

### 4.4 Output & Results

| Table | Description | Records |
|-------|-------------|---------|
| **scoring_results** | Calculated scores and risk bands | 1 per session |
| **coaching_feedback** | AI-generated coaching with TTS audio | 1 per session |
| **reports** | Generated PDF reports | 1 per session |

### 4.5 System Tables

| Table | Description | Records |
|-------|-------------|---------|
| **audit_logs** | Action audit trail | Variable |
| **settings** | System-wide key-value settings | Variable |
| **salesforce_sync** | Salesforce integration logs | Variable |

---

## 5. Relationship Summary

| Parent | Child | Type | Description |
|--------|-------|------|-------------|
| organizations | teams | 1:N | Organization has many teams |
| organizations | users | 1:N | Organization has many users |
| teams | users | 1:N | Team has many users |
| users | sessions | 1:N | User owns many sessions |
| users | audit_logs | 1:N | User's actions are logged |
| sessions | audio_files | 1:1 | Session has one audio file |
| sessions | transcripts | 1:1 | Session has one transcript |
| sessions | scoring_results | 1:1 | Session has one score |
| sessions | coaching_feedback | 1:1 | Session has one coaching |
| sessions | reports | 1:1 | Session has one report |
| sessions | session_responses | 1:N | Session has 92 responses |
| sessions | salesforce_sync | 1:N | Session sync logs |
| checklist_categories | checklist_items | 1:N | Category has many items |
| checklist_items | coaching_questions | 1:N | Item has many questions |
| checklist_items | session_responses | 1:N | Item referenced in responses |

---

## 6. Enums & Constants

### 6.1 User Roles

```python
class UserRole(str, Enum):
    ADMIN = "admin"      # Full system access
    MANAGER = "manager"  # Team-level access
    REP = "rep"          # Individual access (default)
```

### 6.2 Session Status

```python
class SessionStatus(str, Enum):
    DRAFT = "draft"           # Started but not submitted
    UPLOADING = "uploading"   # Audio file uploading
    PROCESSING = "processing" # Transcribing audio
    ANALYZING = "analyzing"   # AI mapping to checklist
    SCORING = "scoring"       # Calculating scores
    COMPLETED = "completed"   # All done
    FAILED = "failed"         # Error occurred
```

### 6.3 Risk Bands

```python
class RiskBand(str, Enum):
    GREEN = "green"    # Healthy: 80-100 points
    YELLOW = "yellow"  # Caution: 60-79 points
    RED = "red"        # At Risk: 0-59 points
```

### 6.4 Risk Band Thresholds

| Score Range | Risk Band | Color | Meaning |
|-------------|-----------|-------|---------|
| 80 - 100 | GREEN | Green | Healthy - Strong sales performance |
| 60 - 79 | YELLOW | Yellow | Caution - Needs improvement |
| 0 - 59 | RED | Red | At Risk - Critical gaps identified |

---

## 7. Data Flow Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   User      │     │   Session   │     │   Audio     │     │  Transcript │
│  Creates    │────>│  Created    │────>│  Uploaded   │────>│  Generated  │
│  Session    │     │  (DRAFT)    │     │  (S3)       │     │  (Whisper)  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                                   │
                                                                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Report    │     │  Coaching   │     │   Scoring   │     │     AI      │
│  Generated  │<────│  Generated  │<────│  Calculated │<────│  Analysis   │
│   (PDF)     │     │ (GPT-4+TTS) │     │ (Risk Band) │     │  (GPT-4)    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

---

## 8. Database Statistics

| Metric | Value |
|--------|-------|
| Total Tables | 14 |
| Core Tables | 7 |
| System Tables | 3 |
| Junction Tables | 1 |
| Checklist Categories | 10 |
| Checklist Items | 92 |
| Points per Item | 1.087 (100/92) |

---

*Document generated for Sales Checklist Backend v1.0.0*
