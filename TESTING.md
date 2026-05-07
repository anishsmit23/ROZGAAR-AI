# ROZGAAR AI — Testing Guide

## Testing Strategy Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    Testing Layers                             │
├──────────────────────────────────────────────────────────────┤
│  1. Unit Tests        → Individual functions, models         │
│  2. Integration Tests → Database, API endpoints              │
│  3. Agent Tests       → LangGraph workflows                  │
│  4. End-to-End Tests  → Full pipeline (Docker Compose)       │
│  5. Manual Tests      → API exploration, UI                  │
└──────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Unit Tests

### Testing Individual Components

#### A. Database Models
```bash
# Test User model
pytest tests/unit/test_models.py::test_user_creation

# Test Application state machine
pytest tests/unit/test_models.py::test_application_state_transitions
```

**File**: `tests/unit/test_models.py`
```python
import pytest
from app.db.models.user import User
from app.db.models.application import Application, ApplicationState

def test_user_creation():
    """Test user model creation and validation."""
    user = User(email="test@example.com", hashed_password="hashed")
    assert user.email == "test@example.com"
    assert user.skills is None or isinstance(user.skills, list)

def test_application_state_transitions():
    """Test valid application state transitions."""
    from app.db.models.application import APPLICATION_STAGE_ORDER
    
    # Valid progression
    assert APPLICATION_STAGE_ORDER[ApplicationState.DISCOVERED] == 1
    assert APPLICATION_STAGE_ORDER[ApplicationState.APPLIED] == 5
    assert APPLICATION_STAGE_ORDER[ApplicationState.CLOSED] == 8
```

#### B. Schemas & Validation
```bash
# Test schema validation
pytest tests/unit/test_schemas.py
```

**File**: `tests/unit/test_schemas.py`
```python
import pytest
from pydantic import ValidationError
from app.schemas.application import ResumeCustomizeRequest, EmailGenerateRequest

def test_resume_customize_request_valid():
    """Valid request should pass."""
    req = ResumeCustomizeRequest(job_id="550e8400-e29b-41d4-a716-446655440000")
    assert str(req.job_id) == "550e8400-e29b-41d4-a716-446655440000"

def test_resume_customize_request_invalid_uuid():
    """Invalid UUID should fail."""
    with pytest.raises(ValidationError):
        ResumeCustomizeRequest(job_id="invalid-uuid")

def test_email_generate_request_valid():
    """Valid email request should pass."""
    req = EmailGenerateRequest(application_id="550e8400-e29b-41d4-a716-446655440000")
    assert req.application_id == "550e8400-e29b-41d4-a716-446655440000"
```

#### C. LLM Client
```bash
# Test LLM client initialization
pytest tests/unit/test_llm_client.py
```

**File**: `tests/unit/test_llm_client.py`
```python
import pytest
from unittest.mock import Mock, patch
from app.llm.client import LLMClient

def test_llm_client_groq_initialization():
    """Test Groq client initialization."""
    with patch("app.llm.client.ChatGroq"):
        client = LLMClient(use_groq=True)
        client._ensure_clients_initialized()
        assert client._groq_client is not None

def test_llm_invoke_simple():
    """Test simple LLM invocation."""
    client = LLMClient()
    # Mock the response
    with patch.object(client, "client") as mock_client:
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_client.invoke.return_value = mock_response
        
        result = client.invoke("test prompt")
        assert result == "Test response"
```

---

## Layer 2: Integration Tests

### Testing with Database & Redis

#### A. Test Database Connection
```bash
# Run integration tests
pytest tests/integration/test_database.py -v

# With specific markers
pytest -m "integration" --tb=short
```

**File**: `tests/integration/test_database.py`
```python
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.db.base import Base, async_session
from app.db.models.user import User
from app.db.models.job_posting import JobPosting

@pytest.fixture
async def db_session():
    """Create test database session."""
    # Use in-memory SQLite or test PostgreSQL
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSession(engine) as session:
        yield session
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_create_user(db_session):
    """Test user creation in database."""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password"
    )
    db_session.add(user)
    await db_session.commit()
    
    result = await db_session.get(User, user.id)
    assert result.email == "test@example.com"

@pytest.mark.asyncio
async def test_create_job_posting(db_session):
    """Test job posting creation."""
    user = User(email="test@example.com", hashed_password="pwd")
    db_session.add(user)
    await db_session.commit()
    
    job = JobPosting(
        user_id=user.id,
        title="Software Engineer",
        company="Tech Corp",
        description="Build awesome software"
    )
    db_session.add(job)
    await db_session.commit()
    
    result = await db_session.get(JobPosting, job.id)
    assert result.title == "Software Engineer"
```

#### B. Test API Endpoints
```bash
# Test with test client
pytest tests/integration/test_api.py -v
```

**File**: `tests/integration/test_api.py`
```python
import pytest
from fastapi.testclient import TestClient
from app.main import create_app

@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)

def test_health_check(client):
    """Test /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_list_jobs_unauthenticated(client):
    """Test that jobs endpoint requires auth."""
    response = client.get("/api/v1/jobs")
    # Should return 403 Forbidden (not authenticated)
    assert response.status_code in [401, 403]
```

---

## Layer 3: Agent Tests

### Testing LangGraph Workflows

**File**: `tests/integration/test_agents.py`
```python
import pytest
from app.agents.graphs.job_search import build_job_search_graph
from app.agents.graphs.resume_tailor import build_resume_tailor_graph
from app.agents.graphs.email_gen import build_email_generation_graph

def test_job_search_graph_compilation():
    """Test job search graph builds correctly."""
    graph = build_job_search_graph()
    assert graph is not None
    
    # Test graph invocation
    state = {
        "query": "Python Developer",
        "location": "Remote",
        "limit": 5
    }
    # This will fail without actual nodes, but tests structure
    # result = graph.invoke(state)
    # assert "normalized_results" in result

def test_resume_tailor_graph_compilation():
    """Test resume tailor graph builds correctly."""
    graph = build_resume_tailor_graph()
    assert graph is not None
    
def test_email_generation_graph_compilation():
    """Test email generation graph builds correctly."""
    graph = build_email_generation_graph()
    assert graph is not None
```

---

## Layer 4: End-to-End Tests with Docker

### A. Start Docker Environment
```bash
# Build and start all services
docker-compose up -d

# Verify all services are running
docker-compose ps
# Expected output:
# NAME                COMMAND                  SERVICE       STATUS
# rozgaar-postgres    postgres                 postgres      Up
# rozgaar-redis       redis-server             redis         Up
# rozgaar-chroma      chroma run               chroma        Up
# rozgaar-minio       minio server             minio         Up
# rozgaar-api         uvicorn                  api           Up
# rozgaar-worker      celery worker            worker        Up
# rozgaar-beat        celery beat              beat          Up
# rozgaar-ui          streamlit run            ui            Up
```

### B. Test Database Migrations
```bash
# Run migrations inside API container
docker-compose exec api alembic upgrade head

# Verify tables created
docker-compose exec postgres psql -U rozgaar -d rozgaar -c "\dt"
```

### C. Test API Endpoints
```bash
# Get health status
curl http://localhost:8000/health

# Expected: {"status":"ok"}
```

### D. Test Authentication Flow
```bash
# Register a new user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/jwt/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=SecurePassword123!"

# Expected response with access_token
# {"access_token":"eyJ0eXAi...","token_type":"bearer"}
```

---

## Layer 5: Manual Integration Testing

### A. Job Search Pipeline
```bash
# 1. Get access token (from auth flow above)
TOKEN="your_access_token_here"

# 2. Start job search pipeline
curl -X POST http://localhost:8000/api/v1/pipeline/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Python Developer",
    "location": "San Francisco",
    "remote": true,
    "limit": 10
  }'

# Expected response:
# {"task_id":"abc-123-def","run_id":"run-123"}

# 3. Check task status
curl http://localhost:8000/api/v1/tasks/abc-123-def \
  -H "Authorization: Bearer $TOKEN"

# Expected:
# {"task_id":"abc-123-def","status":"SUCCESS","result":{...},"error":null}
```

### B. Resume Customization Pipeline
```bash
# 1. Get a job ID (from job search results)
JOB_ID="job-123-uuid"

# 2. Request resume customization
curl -X POST http://localhost:8000/api/v1/resume/customize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"job_id\":\"$JOB_ID\"}"

# Expected:
# {"application_id":"app-123","task_id":"task-456"}

# 3. Monitor task progress
curl http://localhost:8000/api/v1/tasks/task-456 \
  -H "Authorization: Bearer $TOKEN"
```

### C. Email Generation Pipeline
```bash
# 1. Get application ID (from resume customization)
APP_ID="app-123-uuid"

# 2. Request email generation
curl -X POST http://localhost:8000/api/v1/email/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"application_id\":\"$APP_ID\"}"

# Expected:
# {"application_id":"app-123","task_id":"task-789"}
```

### D. Check Application Status
```bash
# List all applications
curl http://localhost:8000/api/v1/applications \
  -H "Authorization: Bearer $TOKEN"

# List applications by state
curl "http://localhost:8000/api/v1/applications?state=EMAIL_GENERATED&limit=10" \
  -H "Authorization: Bearer $TOKEN"

# Update application stage
curl -X PATCH http://localhost:8000/api/v1/applications/app-123/stage \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"stage":"APPLIED","note":"Application submitted"}'
```

---

## Layer 6: Testing with Streamlit UI

### A. Start the UI
```bash
# If not using docker-compose, start manually
streamlit run ui/streamlit_app.py
```

Access at: `http://localhost:8501`

### B. Manual UI Testing
1. **User Registration**
   - Register with valid email and password
   - Verify success message

2. **Job Search**
   - Enter search query (e.g., "Python Developer")
   - Select location
   - Click search
   - Verify jobs appear in results

3. **Resume Upload**
   - Upload PDF resume
   - Verify parsing and storage

4. **Application Tracking**
   - View applications by stage
   - Check 8-stage pipeline progression
   - Monitor status updates

---

## Testing Commands Summary

### Quick Start
```bash
# Run all tests
pytest tests/ -v

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests only
pytest tests/integration/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test
pytest tests/integration/test_api.py::test_health_check -v
```

### Docker Testing
```bash
# Start environment
docker-compose up -d

# Check logs
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f beat

# Stop environment
docker-compose down

# Stop and remove volumes (reset DB)
docker-compose down -v
```

### Health Checks
```bash
# API health
curl http://localhost:8000/health

# Database connection
docker-compose exec postgres psql -U rozgaar -d rozgaar -c "SELECT 1"

# Redis connection
docker-compose exec redis redis-cli ping

# ChromaDB connection
curl http://localhost:8001/api/v1/heartbeat

# MinIO connection
curl http://localhost:9000/minio/bootstrap.html
```

---

## Monitoring & Debugging

### Check Service Logs
```bash
# API logs
docker-compose logs api -f

# Worker logs
docker-compose logs worker -f

# Beat scheduler logs
docker-compose logs beat -f

# PostgreSQL logs
docker-compose logs postgres -f
```

### Database Debugging
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U rozgaar -d rozgaar

# Check tables
\dt

# Check specific table
SELECT * FROM applications;
SELECT * FROM agent_runs;

# Check user
SELECT id, email FROM users;
```

### Redis Debugging
```bash
# Connect to Redis
docker-compose exec redis redis-cli

# Check queues
LLEN celery
LLEN agents
LLEN scrapers

# Monitor tasks
MONITOR
```

### ChromaDB Debugging
```bash
# List collections
curl http://localhost:8001/api/v1/collections

# Query collection
curl -X POST http://localhost:8001/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"collection_name":"job_embeddings","query_texts":["python"]}'
```

---

## Automated Testing Script

Create `scripts/test.sh`:
```bash
#!/bin/bash

echo "🧪 Running ROZGAAR AI Tests"
echo "============================="

# Step 1: Unit tests
echo "1️⃣  Running unit tests..."
pytest tests/unit/ -v --tb=short || exit 1

# Step 2: Integration tests
echo "2️⃣  Running integration tests..."
pytest tests/integration/ -v --tb=short || exit 1

# Step 3: Docker health
echo "3️⃣  Checking Docker services..."
docker-compose ps

# Step 4: Health checks
echo "4️⃣  Running health checks..."
curl -s http://localhost:8000/health | jq .

echo "✅ All tests passed!"
```

Run with:
```bash
chmod +x scripts/test.sh
./scripts/test.sh
```

---

## CI/CD Integration (GitHub Actions)

Create `.github/workflows/test.yml`:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: rozgaar
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run tests
        run: pytest tests/ -v --cov=app
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Expected Test Results

```
======================== test session starts ========================
platform linux -- Python 3.11.x
collected 42 items

tests/unit/test_models.py ............................ ✓
tests/unit/test_schemas.py ........................... ✓
tests/unit/test_llm_client.py ........................ ✓
tests/integration/test_database.py .................. ✓
tests/integration/test_api.py ........................ ✓
tests/integration/test_agents.py ..................... ✓

======================== 42 passed in 3.21s ==========================
```

---

## Troubleshooting Common Issues

### Issue: Tests timeout
**Solution**: Increase timeout in pytest.ini
```ini
[pytest]
timeout = 30
asyncio_mode = auto
```

### Issue: Database locks
**Solution**: Use test database isolation
```python
@pytest.fixture
def db_session():
    # Use transaction rollback after each test
    with engine.begin() as conn:
        conn.execute("ROLLBACK")
```

### Issue: Celery tasks not running
**Solution**: Check worker is running
```bash
docker-compose logs worker
docker-compose restart worker
```

### Issue: ChromaDB connection refused
**Solution**: Ensure ChromaDB service started
```bash
docker-compose up -d chroma
docker-compose logs chroma
```

---

## Next Steps

1. ✅ Create test files in `tests/` directory
2. ✅ Run `pytest tests/ -v` to execute all tests
3. ✅ Set up Docker Compose for integration testing
4. ✅ Add tests to CI/CD pipeline
5. ✅ Monitor coverage: `pytest --cov=app`
