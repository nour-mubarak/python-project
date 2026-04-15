#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Deployment & Operations Guide
==============================================

Production deployment with evaluation, fine-tuning, and RAG.
"""

# ============================================================================
# PRODUCTION DEPLOYMENT GUIDE
# ============================================================================

DEPLOYMENT_GUIDE = """
═══════════════════════════════════════════════════════════════════════════════
DALĪL GROUP - PRODUCTION DEPLOYMENT GUIDE
Real Deployment with Evaluation, Fine-tuning, and RAG
═══════════════════════════════════════════════════════════════════════════════

## 1. SYSTEM REQUIREMENTS

### Hardware
- CPU: 8+ cores recommended
- RAM: 16GB minimum, 32GB for fine-tuning
- GPU: NVIDIA (optional, for faster fine-tuning)
- Storage: 100GB+ SSD

### Software
- Ubuntu 20.04 LTS or later (or CentOS 8+)
- Python 3.10+
- PostgreSQL 13+
- Redis 6+
- Docker & Docker Compose (optional, recommended)

## 2. INSTALLATION

### Step 1: System Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.10 python3-pip postgresql postgresql-contrib redis-server

# Start services
sudo systemctl start postgresql
sudo systemctl start redis-server

# Enable on boot
sudo systemctl enable postgresql
sudo systemctl enable redis-server
```

### Step 2: Python Environment
```bash
cd /home/nour/python-project
python3.10 -m venv .venv
source .venv/bin/activate

# Install production dependencies
pip install --upgrade pip
pip install -r dalil_group/requirements.txt

# Install additional production packages
pip install gunicorn uvicorn[standard]
pip install psycopg2-binary  # PostgreSQL driver
pip install redis  # Redis client
```

### Step 3: Database Setup
```bash
# Create PostgreSQL database
sudo -u postgres psql <<EOF
CREATE DATABASE dalil_group;
CREATE USER dalil_user WITH PASSWORD 'your_secure_password';
ALTER ROLE dalil_user SET client_encoding TO 'utf8';
ALTER ROLE dalil_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE dalil_user SET default_transaction_deferrable TO on;
ALTER ROLE dalil_user SET default_transaction_read_only TO off;
GRANT ALL PRIVILEGES ON DATABASE dalil_group TO dalil_user;
\\c dalil_group
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO dalil_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO dalil_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO dalil_user;
EOF

# Run migrations
cd dalil_group
python migrate.py
```

### Step 4: Environment Configuration
```bash
# Create .env file
cd dalil_group
cat > .env << 'EOF'
# Database
DATABASE_URL=postgresql://dalil_user:your_secure_password@localhost:5432/dalil_group
REDIS_URL=redis://localhost:6379/0

# API Keys
OPENAI_API_KEY=sk-xxx...
ANTHROPIC_API_KEY=sk-ant-xxx...

# LLM Settings
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4

# RAG Settings
RAG_EMBEDDING_MODEL=all-MiniLM-L6-v2
RAG_VECTOR_STORE_PATH=/var/lib/dalil_group/vector_store

# Fine-tuning
FINETUNING_OUTPUT_DIR=/var/lib/dalil_group/finetuned_models

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4
ENV=production
DEBUG=false
EOF

chmod 600 .env
```

## 3. SERVICE DEPLOYMENT

### Option A: Uvicorn + Systemd (Recommended for VPS)

```bash
# Create systemd service file
sudo tee /etc/systemd/system/dalil-group.service << 'EOF'
[Unit]
Description=Dalīl Group API Server
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=www-data
WorkingDirectory=/home/nour/python-project/dalil_group
Environment="LD_LIBRARY_PATH=/usr/local/cuda/lib64"
ExecStart=/home/nour/python-project/.venv/bin/uvicorn web.main:app --host 0.0.0.0 --port 8000 --workers 4 --timeout-keep-alive 65
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable dalil-group
sudo systemctl start dalil-group
sudo systemctl status dalil-group
```

### Option B: Docker Compose (Recommended for consistency)

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: dalil_group
      POSTGRES_USER: dalil_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: always

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: always

  app:
    build:
      context: ./dalil_group
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://dalil_user:${DB_PASSWORD}@postgres:5432/dalil_group
      - REDIS_URL=redis://redis:6379/0
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ENV=production
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    restart: always
    volumes:
      - ./results:/app/results
      - ./vector_store:/app/vector_store

  celery:  # For background tasks
    build:
      context: ./dalil_group
      dockerfile: Dockerfile
    command: celery -A celery_worker worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://dalil_user:${DB_PASSWORD}@postgres:5432/dalil_group
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    restart: always

volumes:
  postgres_data:

# Deploy with:
# docker-compose -f docker-compose.prod.yml up -d
```

## 4. NGINX REVERSE PROXY

```nginx
# /etc/nginx/sites-available/dalil-group
upstream dalil_app {
    server localhost:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    # SSL certificates (use Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=general:10m rate=100r/m;
    limit_req zone=general burst=200 nodelay;
    
    location / {
        proxy_pass http://dalil_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location /static/ {
        alias /var/www/dalil-group/static/;
        expires 1d;
    }
}

# Enable site
sudo ln -s /etc/nginx/sites-available/dalil-group /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 5. MONITORING & LOGGING

### Application Logs
```bash
# View service logs
sudo journalctl -u dalil-group -f

# Rotate logs
cat > /etc/logrotate.d/dalil-group << 'EOF'
/var/log/dalil-group/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
}
EOF
```

### Metrics & Monitoring (Prometheus + Grafana)

```bash
# Install Prometheus
sudo apt install -y prometheus

# prometheus.yml configuration
cat > /etc/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'dalil-group'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
EOF

# Install Grafana
sudo apt install -y grafana-server
sudo systemctl enable grafana-server
sudo systemctl start grafana-server

# Access Grafana at http://localhost:3000
# Add Prometheus as data source
```

## 6. BACKUP & DISASTER RECOVERY

```bash
# Create backup script
cat > /usr/local/bin/backup-dalil-group.sh << 'EOF'
#!/bin/bash

BACKUP_DIR=/var/backups/dalil-group
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
mkdir -p $BACKUP_DIR
pg_dump -U dalil_user dalil_group > $BACKUP_DIR/db_backup_$DATE.sql

# Vector store backup
tar -czf $BACKUP_DIR/vector_store_$DATE.tar.gz /var/lib/dalil_group/vector_store

# Results backup
tar -czf $BACKUP_DIR/results_$DATE.tar.gz /var/lib/dalil_group/results

# Keep only last 30 days
find $BACKUP_DIR -type f -mtime +30 -delete

echo "Backup completed: $DATE"
EOF

chmod +x /usr/local/bin/backup-dalil-group.sh

# Schedule backups (daily at 2 AM)
echo "0 2 * * * /usr/local/bin/backup-dalil-group.sh" | sudo crontab -
```

## 7. SECURITY HARDENING

```bash
# Firewall rules
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw allow 5432  # PostgreSQL (internal only)
sudo ufw allow 6379  # Redis (internal only)

# SSL/TLS Setup with Let's Encrypt
sudo apt install -y certbot python3-certbot-nginx
sudo certbot certonly --nginx -d yourdomain.com -d www.yourdomain.com
sudo certbot renew --dry-run  # Test renewal

# Security groups in cloud (AWS, GCP, etc.)
# - Allow: 22 (SSH), 80 (HTTP), 443 (HTTPS) from known IPs only
# - Deny: All other inbound traffic
```

## 8. SCALING & PERFORMANCE OPTIMIZATION

### Horizontal Scaling (Multiple Instances)
```yaml
# Load balancer configuration (HAProxy)
frontend web_frontend
    bind 0.0.0.0:80
    bind 0.0.0.0:443 ssl crt /etc/ssl/certs/cert.pem
    default_backend web_backend

backend web_backend
    balance roundrobin
    server app1 192.168.1.10:8000 check
    server app2 192.168.1.11:8000 check
    server app3 192.168.1.12:8000 check
```

### Caching Strategy
```python
# Redis caching for frequently accessed data
from functools import wraps
import redis
import json

redis_cache = redis.Redis(host='localhost', port=6379, db=0)

def cache(key_prefix: str, ttl: int = 3600):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{str(args)}:{str(kwargs)}"
            cached = redis_cache.get(cache_key)
            if cached:
                return json.loads(cached)
            result = func(*args, **kwargs)
            redis_cache.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator
```

## 9. DEPLOYMENT CHECKLIST

Before going live:
- [ ] Database backed up
- [ ] SSL certificate installed and working
- [ ] Environment variables configured securely
- [ ] Logs monitored and rotating
- [ ] Metrics being collected
- [ ] Monitoring alerts configured
- [ ] Backup strategy tested
- [ ] Disaster recovery plan documented
- [ ] Rate limiting enabled
- [ ] API authentication working
- [ ] All services passing health checks
- [ ] Load testing completed
- [ ] Security scan passed
- [ ] Documentation updated

## 10. COMMON OPERATIONS

### Update Application
```bash
cd /home/nour/python-project
git pull origin main
source .venv/bin/activate
pip install -r dalil_group/requirements.txt
python dalil_group/migrate.py
sudo systemctl restart dalil-group
```

### View Service Status
```bash
sudo systemctl status dalil-group
docker ps  # If using Docker
```

### Database Maintenance
```bash
# Vacuum database
sudo -u postgres vacuumdb dalil_group

# Check database size
sudo -u postgres psql -c "SELECT pg_size_pretty(pg_database_size('dalil_group'));"
```

### Debug Issues
```bash
# Check logs
journalctl -u dalil-group -n 100
docker logs dalil-group  # If using Docker

# Test database connection
python -c "from sqlalchemy import create_engine; \
  engine = create_engine('postgresql://dalil_user:password@localhost/dalil_group'); \
  engine.execute('SELECT 1'); print('OK')"

# Test Redis connection
redis-cli ping
```

═══════════════════════════════════════════════════════════════════════════════
"""

# ============================================================================
# EVALUATION DEPLOYMENT
# ============================================================================

EVALUATION_DEPLOYMENT = """
═══════════════════════════════════════════════════════════════════════════════
EVALUATION SYSTEM DEPLOYMENT
═══════════════════════════════════════════════════════════════════════════════

## Running Evaluations on Production Data

### 1. Setting up Evaluation Environment
```python
from config.builder import EvaluationConfig, preset_university
from utils.model_runner import ModelRunner
from scoring.scorer import ScoringEngine

# Configure evaluation
config = preset_university(client_name="Government Agency")
```

### 2. Running Baseline Evaluation
```bash
python run_evaluation.py \\
  --preset government \\
  --client "Ministry of Internal Affairs" \\
  --use-judge \\
  --output-dir results/baseline
```

### 3. Continuous Evaluation Pipeline
```bash
# Run evaluation daily via cron
0 2 * * * cd /home/nour/python-project/dalil_group && \\
  python run_evaluation.py \\
  --preset university \\
  --use-judge \\
  --output-dir results/daily_$(date +\\%Y\\%m\\%d)
```

### 4. Performance Benchmarking
```python
# Track metrics over time
from scoring.scorer import ScoringEngine
import pandas as pd

results = []
for date in date_range:
    result = load_evaluation_result(f"results/{date}")
    results.append({
        'date': date,
        'avg_accuracy': result['accuracy_mean'],
        'avg_bias_score': result['bias_mean'],
        'inference_latency': result['latency_ms'],
    })

metrics_df = pd.DataFrame(results)
metrics_df.to_csv('metrics_history.csv')
```

═══════════════════════════════════════════════════════════════════════════════
"""

# ============================================================================
# FINE-TUNING DEPLOYMENT
# ============================================================================

FINETUNING_DEPLOYMENT = """
═══════════════════════════════════════════════════════════════════════════════
FINE-TUNING DEPLOYMENT
═══════════════════════════════════════════════════════════════════════════════

## Fine-tuning Models on Production Data

### 1. Prepare Training Data from Evaluations
```python
from finetuning.dataset_builder import DatasetBuilder

builder = DatasetBuilder()

# Load high-quality responses from evaluation results
added = builder.add_from_evaluation_results(
    results_file="results/baseline/results.json",
    min_quality_score=85.0
)

# Balance dataset
balance_info = builder.balance_dataset(max_per_category=100)

# Export for fine-tuning
builder.export_jsonl("finetuning/training_data.jsonl")
builder.save_metadata("finetuning/metadata.json")

stats = builder.get_statistics()
print(f"Dataset: {stats['total_examples']} examples")
print(f"Languages: {stats['by_language']}")
print(f"Quality: avg={stats['quality_score_stats']['avg']:.1f}")
```

### 2. Fine-tune OpenAI Models
```python
from finetuning.openai_finetuner import OpenAIFinetuner

tuner = OpenAIFinetuner(api_key="sk-...")

# Upload training data
file_id = tuner.upload_training_file("finetuning/training_data.jsonl")

# Create fine-tuning job
job = tuner.create_finetuning_job(
    training_file_id=file_id,
    model="gpt-3.5-turbo",
    hyperparameters={
        "n_epochs": 3,
        "learning_rate_multiplier": 0.1,
    },
    suffix="dalil_v1"
)

# Wait for completion
final_status = tuner.wait_for_completion(job['id'])
tuned_model = final_status['fine_tuned_model']
print(f"Fine-tuned model ready: {tuned_model}")
```

### 3. Fine-tune Open-Source Models
```python
from finetuning.finetuner import Finetuner

tuner = Finetuner(
    model_id="meta-llama/Llama-2-7b",
    output_dir="finetuned_models",
    use_qlora=True  # Memory efficient
)

# Fine-tune
result = tuner.finetune(
    dataset_file="finetuning/training_data.jsonl",
    epochs=3,
    batch_size=4,
    learning_rate=2e-4,
    num_gpus=1
)

# Merge LoRA weights
merged_model = tuner.merge_lora_weights(
    lora_dir=result['output_dir']
)
```

### 4. Evaluate Fine-tuned Models
```python
# Compare fine-tuned vs baseline
from config.builder import ModelConfig
from utils.model_runner import ModelRunner

models = [
    ModelConfig(model_id="gpt-3.5-turbo", provider="openai"),
    ModelConfig(model_id=tuned_model, provider="openai"),  # Fine-tuned
]

runner = ModelRunner(models)
results = runner.run()

# Analyze improvements
print(f"Baseline accuracy: {results[0]['accuracy']:.1f}%")
print(f"Fine-tuned accuracy: {results[1]['accuracy']:.1f}%")
print(f"Improvement: +{results[1]['accuracy'] - results[0]['accuracy']:.1f}%")
```

═══════════════════════════════════════════════════════════════════════════════
"""

# ============================================================================
# RAG DEPLOYMENT
# ============================================================================

RAG_DEPLOYMENT = """
═══════════════════════════════════════════════════════════════════════════════
RAG SYSTEM DEPLOYMENT
═══════════════════════════════════════════════════════════════════════════════

## Setting up RAG for Production

### 1. Ingest Documents from Multiple Sources
```python
from rag.document_loader import (
    FileDocumentLoader,
    URLDocumentLoader,
    DocumentChunker
)
from rag.vector_store import VectorStore

# Load documents from files
file_loader = FileDocumentLoader()
documents = file_loader.load("knowledge_base/")

# Load from URLs
url_loader = URLDocumentLoader()
web_docs = url_loader.load("https://example.com/docs")

all_docs = documents + web_docs

# Chunk documents
chunker = DocumentChunker()
chunks = []
for doc in all_docs:
    doc_chunks = chunker.chunk_by_tokens(doc, chunk_size=512)
    chunks.extend(doc_chunks)

print(f"Created {len(chunks)} chunks from {len(all_docs)} documents")
```

### 2. Initialize Vector Store
```python
from rag.vector_store import VectorStore

# Create vector store with embeddings
vector_store = VectorStore(
    name="dalil_knowledge",
    embedding_model="all-MiniLM-L6-v2",
    persist_dir="vector_store"
)

# Add documents
added = vector_store.add_documents(chunks)
print(f"Added {added} documents to vector store")

# Save metadata
vector_store.save_metadata("vector_store/metadata.json")
```

### 3. Query RAG System
```python
from rag.generation import RAGPipeline, RAGGenerator

# Create RAG pipeline
generator = RAGGenerator(
    llm_provider="openai",
    model_id="gpt-3.5-turbo",
    temperature=0.3
)

pipeline = RAGPipeline(vector_store, generator)

# Ask question
result = pipeline.query(
    query="How do I renew my driver's license?",
    k=5,
    language="en"
)

print(f"Answer: {result['answer']}")
print(f"Sources: {[s['rank'] for s in result['retrieval']['matches']]}")
print(f"Top document: {result['retrieval']['matches'][0]['title']}")
```

### 4. Update Knowledge Base
```python
# Add new documents to existing vector store
new_docs = file_loader.load("knowledge_base/new_documents/")
new_chunks = []
for doc in new_docs:
    doc_chunks = chunker.chunk_by_tokens(doc)
    new_chunks.extend(doc_chunks)

# Add to vector store
vector_store.add_documents(new_chunks)

print(f"Updated with {len(new_chunks)} new chunks")
```

### 5. Monitor RAG Performance
```python
import json
from datetime import datetime

# Log queries for monitoring
def log_rag_query(query: str, result: dict):
    log = {
        'timestamp': datetime.now().isoformat(),
        'query': query,
        'answer_length': len(result['answer']),
        'retrieval_score': result['retrieval']['top_match_score'],
        'documents_used': len(result['retrieval']['matches']),
        'model': result['metadata']['model'],
    }
    
    with open('rag_logs.jsonl', 'a') as f:
        f.write(json.dumps(log) + '\\n')

# Analyze usage patterns
import pandas as pd
logs_df = pd.read_json('rag_logs.jsonl', lines=True)
print(f"Total queries: {len(logs_df)}")
print(f"Avg retrieval score: {logs_df['retrieval_score'].mean():.2f}")
print(f"Avg documents used: {logs_df['documents_used'].mean():.1f}")
```

═══════════════════════════════════════════════════════════════════════════════
"""

# ============================================================================
# MAIN DEPLOYMENT DOCUMENTATION
# ============================================================================

def print_deployment_guide():
    """Print comprehensive deployment guide."""
    print(DEPLOYMENT_GUIDE)
    print("\n" + "="*80 + "\n")
    print(EVALUATION_DEPLOYMENT)
    print("\n" + "="*80 + "\n")
    print(FINETUNING_DEPLOYMENT)
    print("\n" + "="*80 + "\n")
    print(RAG_DEPLOYMENT)

if __name__ == "__main__":
    print_deployment_guide()
