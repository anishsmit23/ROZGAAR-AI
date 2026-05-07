# ROZGAAR AI — Technical & System Requirements Document
**Version:** 1.0  
**Author:** Anish  
**Type:** Combined TRD + SRD (Brief)  
**Status:** In Development

---

## 1. Overview

Rozgaar AI is an asynchronous multi-agent AI pipeline designed to automate end-to-end job discovery, resume customization, and application tracking for job seekers. The system eliminates manual effort in finding relevant jobs, tailoring resumes, and managing application states by combining LLM-powered agents, semantic search, and a scalable microservices backend.

---

## 2. System Requirements Document (SRD)

### 2.1 Problem Statement

Job seekers spend significant time manually searching across platforms, customizing resumes per role, and tracking application statuses. Rozgaar AI reduces this effort to near-zero by automating each stage intelligently.

### 2.2 Functional Requirements

| ID | Requirement |
|----|------------|
| FR-01 | System shall autonomously discover relevant job listings based on user profile and preferences |
| FR-02 | System shall perform semantic ranking of job listings against the user's resume using RAG |
| FR-03 | System shall generate role-specific, customized resume drafts per job listing |
| FR-04 | System shall auto-generate personalized cold emails for job applications |
| FR-05 | System shall track each job application across 8 defined stages |
| FR-06 | System shall expose REST APIs for all pipeline operations and status queries |
| FR-07 | System shall support real-time task monitoring via async task queues |
| FR-08 | System shall persist user data, job data, and application states in structured storage |

### 2.3 Non-Functional Requirements

| ID | Requirement |
|----|------------|
| NFR-01 | Pipeline tasks must execute asynchronously — no blocking user-facing threads |
| NFR-02 | System must be containerized and reproducible via Docker Compose |
| NFR-03 | Semantic search responses must return within 2 seconds for cached queries |
| NFR-04 | System must support horizontal scaling of worker nodes via Celery |
| NFR-05 | All sensitive user data (resume content, emails) must be stored securely |
| NFR-06 | System must handle agent failures gracefully with retry logic |

### 2.4 User Stories

- **As a job seeker**, I want the system to find jobs matching my skills so I don't have to search manually.
- **As a user**, I want my resume auto-customized per job role so every application feels tailored.
- **As a user**, I want to receive a ready-to-send cold email draft per application.
- **As a user**, I want to track where each application stands at any point in time.

### 2.5 Application Tracking — 8 Stages

```
[1] Discovered → [2] Ranked → [3] Resume Customized → [4] Email Generated
      → [5] Applied → [6] Acknowledged → [7] Interview Scheduled → [8] Closed
```

Each stage transition is logged with timestamps and accessible via REST API.

---

## 3. Technical Requirements Document (TRD)

### 3.1 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User / Frontend                       │
│                     (Streamlit UI / API)                     │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP Requests
┌────────────────────────▼────────────────────────────────────┐
│                     FastAPI Gateway                          │
│              (REST API + Webhook Endpoints)                  │
└──────┬─────────────────┬──────────────────┬─────────────────┘
       │                 │                  │
┌──────▼──────┐  ┌───────▼───────┐  ┌──────▼──────┐
│   Celery    │  │  Agent Layer  │  │  Auth/User  │
│  Task Queue │  │  (LangGraph)  │  │   Service   │
└──────┬──────┘  └───────┬───────┘  └─────────────┘
       │                 │
┌──────▼─────────────────▼──────────────────────────────────┐
│                     Data Layer                              │
│   PostgreSQL │ Redis │ ChromaDB │ MinIO                     │
└────────────────────────────────────────────────────────────┘
```

### 3.2 Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Agent Orchestration | LangGraph | Multi-agent state machine and workflow control |
| API Layer | FastAPI | REST endpoints, async request handling |
| Task Queue | Celery + Redis | Async job execution, task scheduling |
| Primary DB | PostgreSQL | User profiles, job listings, application states |
| Cache | Redis | Task queue broker, session caching, fast lookups |
| Vector Store | ChromaDB | Resume and job description embeddings for RAG |
| File Storage | MinIO | Resume files, generated documents (S3-compatible) |
| Containerization | Docker Compose | Service orchestration and environment parity |
| Frontend | Streamlit | User-facing dashboard and monitoring UI |

### 3.3 Agent Architecture (LangGraph Multi-Agent Pipeline)

```
                    ┌─────────────────┐
                    │  Orchestrator   │
                    │     Agent       │
                    └────────┬────────┘
          ┌─────────┬────────┼──────────┬──────────┐
          ▼         ▼        ▼          ▼          ▼
    ┌──────────┐ ┌──────┐ ┌──────┐ ┌───────┐ ┌────────┐
    │   Job    │ │Rank  │ │Resume│ │ Email │ │Tracker │
    │Discovery │ │Agent │ │Agent │ │ Agent │ │ Agent  │
    └──────────┘ └──────┘ └──────┘ └───────┘ └────────┘
```

| Agent | Responsibility |
|-------|---------------|
| Orchestrator Agent | Routes tasks, manages pipeline state, handles retries |
| Job Discovery Agent | Scrapes/queries job APIs, filters by user profile |
| Ranking Agent | RAG-based semantic scoring of jobs vs. resume |
| Resume Customization Agent | LLM-powered resume tailoring per job description |
| Email Generation Agent | Cold email drafting using job + user context |
| Tracker Agent | Updates application stage, logs transitions |

### 3.4 RAG Pipeline Design

```
Resume (PDF) ──► Chunking ──► Embedding ──► ChromaDB
                                                │
Job Description ──► Embedding ──► Similarity Search
                                                │
                                        Ranked Job List
                                        (semantic score)
```

- **Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2` or OpenAI `text-embedding-3-small`
- **Chunk Strategy:** 512 tokens with 64-token overlap
- **Ranking Metric:** Cosine similarity score ≥ 0.70 threshold for shortlisting

### 3.5 Data Models (Simplified)

**User Profile**
```
user_id | name | email | skills[] | experience_years | resume_path | preferences{}
```

**Job Listing**
```
job_id | title | company | description | source_url | embedding_id | discovered_at
```

**Application**
```
app_id | user_id | job_id | stage (1–8) | resume_version_path | email_draft | updated_at
```

### 3.6 API Endpoints (Key)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/pipeline/start` | Trigger full job discovery pipeline |
| GET | `/api/v1/jobs/ranked` | Fetch semantically ranked job list |
| POST | `/api/v1/resume/customize` | Generate customized resume for a job |
| POST | `/api/v1/email/generate` | Generate cold email for a job |
| GET | `/api/v1/applications/` | Get all applications with stage info |
| PATCH | `/api/v1/applications/{id}/stage` | Update application stage |
| GET | `/api/v1/tasks/{task_id}/status` | Real-time Celery task status |

### 3.7 Async Task Flow

```
API Request → FastAPI → Celery Task Enqueued (Redis Broker)
                                    │
                            Celery Worker Picks Up
                                    │
                         LangGraph Agent Executes
                                    │
                        Result Stored (PostgreSQL/MinIO)
                                    │
                        Task Status Updated (Redis)
                                    │
                        Client Polls /tasks/{id}/status
```

### 3.8 Infrastructure (Docker Compose Services)

```yaml
services:
  - api          # FastAPI application
  - worker       # Celery worker(s)
  - beat         # Celery scheduler (periodic tasks)
  - postgres     # Primary database
  - redis        # Broker + cache
  - chromadb     # Vector store
  - minio        # File storage
  - streamlit    # Frontend UI
```

---

## 4. Constraints & Assumptions

- LLM API calls (Gemini/OpenAI) are treated as external dependencies with rate limit handling
- Job discovery sources are either public APIs or scraped ethically with `robots.txt` compliance
- Resume files are stored as PDFs; output customized resumes are generated as PDFs via template
- System assumes single-user context in v1; multi-tenancy planned for v2

---

## 5. Future Scope (V2)

- Auto-apply to jobs via browser automation (Playwright)
- Interview preparation agent triggered post stage-6
- LinkedIn and Naukri API integrations
- Evaluation layer using RAGAS for RAG quality monitoring
- web-friendly frontend (React + FastAPI)

---

*Document generated for portfolio and internship application purposes.*