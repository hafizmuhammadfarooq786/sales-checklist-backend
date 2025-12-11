# The Sales Checklist™ API - Backend

> **AI-Powered B2B Sales Conversation Analysis Platform**
> Transform your sales conversations into actionable insights with AI-driven checklist validation, automatic transcription, and intelligent coaching.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-412991?logo=openai)](https://openai.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

---

## 📋 Overview

The **The Sales Checklist™ API** is an enterprise-grade backend system that leverages cutting-edge AI to analyze B2B sales conversations. It validates 10 critical success factors, generates intelligent coaching insights, and provides actionable feedback to improve sales performance.

### Key Features

✅ **AI-Powered Analysis** - GPT-4 driven conversation analysis with contextual understanding
🎯 **10-Point Checklist** - Validates critical B2B sales success factors (Trigger Events, Decision Makers, Fit, etc.)
🎤 **Audio Transcription** - Automatic speech-to-text using OpenAI Whisper
📊 **Intelligent Scoring** - Binary scoring system (0-100 scale) with health indicators
💬 **Personalized Coaching** - AI-generated coaching questions and improvement recommendations
📄 **PDF Reports** - Professional, branded reports with detailed analysis
🔐 **Enterprise Security** - JWT authentication, password hashing, role-based access control
📧 **Email Integration** - AWS SES for transactional emails and report delivery
☁️ **Cloud Storage** - AWS S3 for audio files, reports, and backups
⚡ **Async Processing** - Celery-powered background tasks for long-running operations
📈 **Scalable Architecture** - PostgreSQL + Redis + async Python for high performance

---

## 🚀 Tech Stack

### Core Framework

- **[FastAPI](https://fastapi.tiangolo.com/)** `0.115` - Modern, high-performance Python web framework
- **[Uvicorn](https://www.uvicorn.org/)** `0.32` - Lightning-fast ASGI server
- **[Pydantic](https://docs.pydantic.dev/)** `2.9` - Data validation using Python type annotations

### Database & ORM

- **[PostgreSQL](https://www.postgresql.org/)** - Primary relational database
- **[SQLAlchemy](https://www.sqlalchemy.org/)** `2.0` - Async ORM with modern Python support
- **[Alembic](https://alembic.sqlalchemy.org/)** `1.13` - Database migration tool
- **[asyncpg](https://github.com/MagicStack/asyncpg)** - High-performance async PostgreSQL driver

### Caching & Queue

- **[Redis](https://redis.io/)** `5.2` - In-memory data store for caching and task queue
- **[Celery](https://docs.celeryq.dev/)** `5.4` - Distributed task queue for background jobs
- **[Flower](https://flower.readthedocs.io/)** `2.0` - Real-time Celery task monitoring

### AI & Machine Learning

- **[OpenAI API](https://platform.openai.com/)** `1.54` - GPT-4 for analysis, Whisper for transcription
- **[ElevenLabs](https://elevenlabs.io/)** `1.9` - Neural text-to-speech for coaching audio

### AWS Services

- **[boto3](https://boto3.amazonaws.com/)** `1.35` - AWS SDK for Python
- **Amazon S3** - Object storage for audio files and reports
- **Amazon SES** - Email delivery service

### Security & Authentication

- **[python-jose](https://python-jose.readthedocs.io/)** `3.3` - JWT token generation and validation
- **[passlib](https://passlib.readthedocs.io/)** `1.7` - Password hashing with bcrypt

### Utilities

- **[ReportLab](https://www.reportlab.com/)** `4.2` - PDF generation
- **[Sentry](https://sentry.io/)** `2.17` - Application monitoring and error tracking
- **[httpx](https://www.python-httpx.org/)** `0.27` - Modern async HTTP client

---

## 📦 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+** ([Download](https://www.python.org/downloads/))
- **PostgreSQL 15+** ([Download](https://www.postgresql.org/download/))
- **Redis 7+** ([Download](https://redis.io/download))
- **Git** ([Download](https://git-scm.com/downloads))

### External Services (API Keys Required)

1. **OpenAI API** - Required for transcription and analysis

   - Sign up: https://platform.openai.com/
   - Get API key: https://platform.openai.com/api-keys

2. **AWS Account** - Required for S3 and SES

   - Sign up: https://aws.amazon.com/
   - Create IAM user with S3 and SES permissions

3. **ElevenLabs** (Optional) - For text-to-speech coaching audio
   - Sign up: https://elevenlabs.io/

---

## ⚙️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/hafizmuhammadfarooq786/sales-checklist-backend.git
cd sales-checklist-backend
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env  # or use your preferred editor
```

#### Required Environment Variables

```env
# Database (PostgreSQL)
DATABASE_URL=postgresql://user:password@localhost:5432/sales_checklist

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT Secret (generate with: openssl rand -hex 32)
SECRET_KEY=your-super-secret-key-here

# OpenAI API
OPENAI_API_KEY=sk-proj-your-openai-api-key

# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_BUCKET_NAME=your-bucket-name
SES_SENDER_EMAIL=noreply@yourdomain.com

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

> **Security Note**: Never commit `.env` to version control. The `.gitignore` is configured to exclude it.

### 5. Database Setup

```bash
# Create PostgreSQL database
createdb sales_checklist

# Run database migrations
alembic upgrade head

# Seed checklist items (10 default items)
python -m app.db.seed
```

### 6. Start Redis

```bash
# macOS (Homebrew)
brew services start redis

# Linux
sudo systemctl start redis

# Or run directly
redis-server
```

---

## 🏃 Running the Application

### Development Mode

#### Start API Server

```bash
# Activate virtual environment
source venv/bin/activate

# Start FastAPI with auto-reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:

- **API Base**: http://localhost:8000/api/v1
- **Interactive Docs (Swagger)**: http://localhost:8000/docs
- **Alternative Docs (ReDoc)**: http://localhost:8000/redoc

#### Start Celery Worker

Open a new terminal:

```bash
# Activate virtual environment
source venv/bin/activate

# Start Celery worker
celery -A app.core.celery_app worker --loglevel=info
```

#### Start Celery Flower (Optional - Task Monitoring)

Open another terminal:

```bash
# Activate virtual environment
source venv/bin/activate

# Start Flower dashboard
celery -A app.core.celery_app flower --port=5555
```

Access Flower at: http://localhost:5555

### Production Mode

```bash
# Use production environment file
cp .env.production .env

# Run with production settings
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 📁 Project Structure

```
sales-checklist-backend/
├── alembic/                    # Database migrations
│   ├── versions/               # Migration files
│   └── env.py                  # Alembic configuration
├── app/
│   ├── api/                    # API layer
│   │   ├── endpoints/          # Endpoint implementations
│   │   │   ├── auth.py         # Authentication endpoints
│   │   │   ├── sessions.py     # Session management
│   │   │   ├── checklists.py   # Checklist CRUD
│   │   │   └── users.py        # User management
│   │   └── v1/                 # API version 1
│   │       └── router.py       # Route aggregation
│   ├── core/                   # Core functionality
│   │   ├── config.py           # Application configuration
│   │   ├── security.py         # JWT, password hashing
│   │   ├── celery_app.py       # Celery task queue
│   │   └── dependencies.py     # FastAPI dependencies
│   ├── db/                     # Database layer
│   │   ├── session.py          # Database session management
│   │   └── seed.py             # Database seeding scripts
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── user.py             # User model
│   │   ├── session.py          # Session model
│   │   ├── checklist.py        # Checklist models
│   │   └── organization.py     # Organization model
│   ├── schemas/                # Pydantic schemas
│   │   ├── user.py             # User request/response schemas
│   │   ├── session.py          # Session schemas
│   │   ├── checklist.py        # Checklist schemas
│   │   └── auth.py             # Auth schemas
│   ├── services/               # Business logic layer
│   │   ├── openai_service.py   # OpenAI integration
│   │   ├── s3_service.py       # AWS S3 operations
│   │   ├── ses_service.py      # AWS SES email
│   │   ├── report_service.py   # PDF report generation
│   │   └── analysis_service.py # AI analysis logic
│   ├── utils/                  # Utility functions
│   │   ├── validators.py       # Input validation
│   │   └── helpers.py          # Helper functions
│   └── main.py                 # Application entry point
├── .env.example                # Environment template
├── .gitignore                  # Git ignore rules
├── alembic.ini                 # Alembic configuration
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

---

## 🔌 API Documentation

### Base URL

```
http://localhost:8000/api/v1
```

### Authentication

All authenticated endpoints require a JWT token in the `Authorization` header:

```bash
Authorization: Bearer <your-jwt-token>
```

### Key Endpoints

#### Authentication

- `POST /auth/register` - Create new user account
- `POST /auth/login` - Login and get JWT token
- `POST /auth/forgot-password` - Request password reset
- `POST /auth/reset-password` - Reset password with token

#### Sessions

- `POST /sessions/` - Create new sales conversation session
- `GET /sessions/` - List all sessions (paginated)
- `GET /sessions/{id}` - Get session details
- `POST /sessions/{id}/upload` - Upload audio file
- `GET /sessions/{id}/score` - Get checklist score
- `GET /sessions/{id}/transcript` - Get transcription
- `GET /sessions/{id}/coaching` - Get AI coaching insights
- `POST /sessions/{id}/report` - Generate PDF report
- `POST /sessions/{id}/report/email` - Email report

#### Checklists

- `GET /checklists/summary` - Get checklist summary
- `GET /checklists/categories` - List all categories
- `GET /checklists/items` - List all checklist items

#### Users

- `GET /users/me` - Get current user profile
- `PATCH /users/me` - Update user profile
- `GET /users/me/metrics` - Get user performance metrics

### Interactive API Docs

Visit **http://localhost:8000/docs** for:

- Interactive API explorer
- Request/response schemas
- Try-it-out functionality
- Authentication testing

---

## 🗄️ Database Migrations

### Create New Migration

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "description of changes"

# Create empty migration (manual changes)
alembic revision -m "description of changes"
```

### Apply Migrations

```bash
# Upgrade to latest version
alembic upgrade head

# Upgrade to specific version
alembic upgrade <revision_id>

# Downgrade one version
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

---

## 🧪 Testing

```bash
# Install development dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v
```

---

## 🚀 Deployment

### AWS Elastic Beanstalk

```bash
# Install EB CLI
pip install awsebcli

# Initialize EB application
eb init -p python-3.11 sales-checklist-api

# Create environment
eb create production-env

# Deploy
eb deploy
```

### Docker

```dockerfile
# Dockerfile (create this file)
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build image
docker build -t sales-checklist-api .

# Run container
docker run -p 8000:8000 --env-file .env sales-checklist-api
```

### Environment Variables for Production

Ensure these are set in your production environment:

- `ENVIRONMENT=production`
- `DEBUG=False`
- Secure `SECRET_KEY` (generate with `openssl rand -hex 32`)
- Production database URL
- AWS credentials with minimal required permissions
- `SENTRY_DSN` for error tracking

---

## 🔒 Security Best Practices

1. **Never commit secrets** - Use `.env` files and environment variables
2. **Rotate API keys regularly** - Especially OpenAI and AWS keys
3. **Use strong passwords** - Enable password requirements in production
4. **Enable CORS carefully** - Restrict `ALLOWED_ORIGINS` to your frontend domain
5. **Keep dependencies updated** - Run `pip list --outdated` regularly
6. **Monitor with Sentry** - Track errors and performance issues
7. **Rate limiting** - Configure `RATE_LIMIT_PER_MINUTE` appropriately
8. **HTTPS only** - Never run production without SSL/TLS

---

## 📊 Monitoring & Logging

### Application Logs

```bash
# View Uvicorn logs
tail -f logs/app.log

# View Celery logs
tail -f logs/celery.log
```

### Sentry Integration

Add your Sentry DSN to `.env`:

```env
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

### Celery Flower Dashboard

Monitor background tasks at http://localhost:5555:

- Task status (pending, success, failed)
- Worker health
- Task execution times
- Retry attempts

---

## 🤝 Contributing

This is a proprietary project. For authorized contributors:

1. Create a feature branch: `git checkout -b feature/your-feature-name`
2. Make your changes and commit: `git commit -m "Add feature X"`
3. Push to the branch: `git push origin feature/your-feature-name`
4. Create a Pull Request

### Code Style

- Follow [PEP 8](https://pep8.org/) style guide
- Use [Black](https://black.readthedocs.io/) for formatting: `black .`
- Use [Ruff](https://docs.astral.sh/ruff/) for linting: `ruff check .`
- Write docstrings for all functions and classes
- Add type hints to function signatures

---

## 📝 License

**Proprietary** - All rights reserved. This software is confidential and proprietary. Unauthorized copying, distribution, or use is strictly prohibited.

---

## 🆘 Support

For questions, issues, or feature requests:

- **Email**: support@saleschecklist.com
- **Documentation**: https://docs.saleschecklist.com
- **Issue Tracker**: Create an issue in this repository (authorized users only)

---

## 🎯 Roadmap

- [ ] Multi-language support for transcription
- [ ] Salesforce CRM integration
- [ ] HubSpot integration
- [ ] Advanced analytics dashboard
- [ ] Custom checklist templates
- [ ] Team performance comparisons
- [ ] Mobile app support
- [ ] Real-time audio processing

---

## 🙏 Acknowledgments

Built with:

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [OpenAI](https://openai.com/) - GPT-4 and Whisper AI models
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL toolkit
- [Celery](https://docs.celeryq.dev/) - Distributed task queue

---

**Made with ❤️ for B2B Sales Teams**
