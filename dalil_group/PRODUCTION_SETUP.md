# Production Infrastructure & Security Guide

## Authentication Hardening

### 1. API Key Management

```python
# web/security.py
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthCredentialsDetails
from datetime import datetime, timedelta
import jwt

security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthCredentialsDetails = Security(security)):
    """Verify API key with JWT validation."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, "SECRET_KEY", algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id
```

### 2. Password Hashing

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)
```

### 3. CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### 4. Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.get("/api/evaluations")
@limiter.limit("100/minute")
async def get_evaluations(request: Request):
    pass
```

---

##Performance Optimization

### 1. Query Optimization

```python
# Use select() with specific columns
from sqlalchemy import select

stmt = select(Evaluation.id, Evaluation.project_id, Evaluation.overall_score)
results = db.execute(stmt).fetchall()

# Enable query eager loading
from sqlalchemy.orm import joinedload
evaluations = db.query(Evaluation).options(joinedload(Evaluation.user)).all()
```

### 2. Caching Strategies

```python
# Cache evaluation results
@cached(ttl=3600)
def get_evaluation_stats(eval_id: int):
    # Expensive operation
    pass

# Cache invalidation on updates
def update_evaluation(eval_id: int, **kwargs):
    # Update database
    db.commit()
    # Invalidate cache
    cache_delete(f"eval:results:{eval_id}")
```

### 3. Async Processing

```python
# Use background tasks for long operations
from fastapi import BackgroundTasks

@app.post("/evaluations")
async def create_evaluation(req: EvaluationRequest, background_tasks: BackgroundTasks):
    eval = db.create_evaluation(...)
    background_tasks.add_task(run_evaluation, eval.id)
    return {"eval_id": eval.id}

async def run_evaluation(eval_id: int):
    # Long-running evaluation job
    pass
```

---

## Monitoring & Observability

### 1. Structured Logging

```python
import logging
from pythonjsonlogger import jsonlogger

# Configure JSON logging
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Usage
logger.info("Evaluation started", extra={
    "eval_id": eval_id,
    "models": models,
    "duration_sec": 120
})
```

### 2. Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, start_http_server

# Define metrics  
evaluation_counter = Counter(
    'evaluations_total',
    'Total evaluations',
    ['status']
)

evaluation_duration = Histogram(
    'evaluation_duration_seconds',
    'Evaluation duration'
)

# Record metrics
with evaluation_duration.time():
    run_evaluation()
```

### 3. Error Tracking

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn="https://key@sentry.io/project",
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1
)
```

---

## Disaster Recovery

### 1. Database Backups

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/backups"
DB_NAME="linguaeval"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

pg_dump -U linguaeval $DB_NAME | gzip > $BACKUP_DIR/backup_$TIMESTAMP.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete
```

### 2. High Availability Setup

```yaml
# docker-compose.yml with replication
services:
  postgres-primary:
    image: postgres:16
    environment:
      POSTGRES_REPLICATION_MODE: master
      
  postgres-replica:
    image: postgres:16
    depends_on:
      - postgres-primary
    environment:
      POSTGRES_REPLICATION_MODE: slave
```

### 3. Failover Configuration

```python
# Implement connection pooling with failover
from sqlalchemy import event, create_engine
from sqlalchemy.pool import Pool

@event.listens_for(Pool, "connect")
def receive_connect(dbapi_conn, connection_record):
    # Implement health checks and failover logic
    pass
```

---

## API Documentation Generation

### 1. Enhanced OpenAPI Schema

```python
from web.schemas import (
    HealthResponse,
    BatchJobResponse,
    EvaluationResponse,
)

@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """
    Check platform health status.
    
    Returns health status of all services including:
    - Database connectivity
    - Redis cache
    - Ollama LLM server
    - OpenAI/Anthropic API availability
    """
    pass
```

### 2. API Documentation Endpoints

- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI Schema**: `/openapi.json`

---

## Cost Optimization

### 1. Model API Usage Tracking

```python
# Track costs per evaluation
def log_api_usage(model_id: str, tokens_used: int, cost: float):
    usage = APIUsage(
        model_id=model_id,
        tokens=tokens_used,
        cost=cost,
        timestamp=datetime.utcnow()
    )
    db.add(usage)
    db.commit()
```

### 2. Batch Processing

```python
# Batch similar requests to reduce API calls
def batch_model_queries(prompts: List[str], model_id: str):
    # Group by model and language
    # Make fewer, larger API calls
    pass
```

---

## Compliance & Reporting

### 1. Audit Logging

```python
def log_audit(action: str, user_id: int, resource: str, details: dict):
    log = AuditLog(
        action=action,
        user_id=user_id,
        resource_type=resource,
        details=json.dumps(details),
        ip_address=request.client.host,
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()
```

### 2. Data Retention Policy

```python
# Implement automatic data cleanup
from sqlalchemy import delete

def cleanup_old_evaluations(days: int = 90):
    cutoff = datetime.utcnow() - timedelta(days=days)
    db.execute(delete(Evaluation).where(Evaluation.created_at < cutoff))
    db.commit()
```

---

## Support Resources

- **Documentation**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
