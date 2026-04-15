#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
README: Real Production Deployment
===================================

Complete guide to production deployment with:
- Evaluation System
- Fine-tuning Pipeline
- RAG (Retrieval-Augmented Generation)

Generated: 2026-04-15
"""

README = """
═══════════════════════════════════════════════════════════════════════════════
DALĪL GROUP - PRODUCTION DEPLOYMENT
Real Deployment with Evaluation, Fine-tuning, and RAG
═══════════════════════════════════════════════════════════════════════════════

## 🚀 Quick Start

### 1. Installation
```bash
cd dalil_group
python3.10 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Run Evaluation
```bash
# Run evaluation on government sector
python cli_eval.py run --preset government --client "Ministry" --use-judge --report pdf

# List evaluation results
python cli_eval.py list --limit 10

# Compare two evaluations
python cli_eval.py compare --file1 results/eval1.json --file2 results/eval2.json

# Export dataset for fine-tuning
python cli_eval.py export --results-file results/baseline.json --balance --format jsonl
```

### 3. Fine-tune Models
```bash
# Fine-tune OpenAI GPT-3.5-turbo
python cli_finetune.py openai \\
  --training-file finetuning/training_data.jsonl \\
  --model gpt-3.5-turbo \\
  --epochs 3 \\
  --wait

# Fine-tune local Llama model with QLoRA
python cli_finetune.py local \\
  --model meta-llama/Llama-2-7b \\
  --training-file finetuning/training_data.jsonl \\
  --epochs 3 \\
  --batch-size 4 \\
  --merge

# List fine-tuning jobs
python cli_finetune.py jobs --limit 10

# Get job status
python cli_finetune.py status --job-id ftjob-abc123
```

### 4. Deploy RAG System
```bash
# Ingest documents
python cli_rag.py ingest \\
  --files knowledge_base/ \\
  --urls "https://example.com/docs" \\
  --chunk-size 512 \\
  --collection dalil_rag

# Query RAG system
python cli_rag.py query \\
  --query "How do I renew my driver's license?" \\
  --language en \\
  --top-k 5

# Search documents
python cli_rag.py search \\
  --query "government procedures" \\
  --top-k 10

# Update collection
python cli_rag.py update --delete doc_id_1 doc_id_2

# Export collection
python cli_rag.py export --output collection_backup.json
```

═══════════════════════════════════════════════════════════════════════════════

## 📊 Evaluation System

### Features
- ✅ Multi-model evaluation (OpenAI, Anthropic, local models)
- ✅ Cross-lingual evaluation (English + Arabic)
- ✅ 6 scoring dimensions (accuracy, bias, hallucination, consistency, cultural sensitivity, fluency)
- ✅ Judge model support for enhanced scoring
- ✅ Automated report generation (PDF, HTML, JSON)

### Workflow
1. **Configure**: Select sector (government, university, healthcare, finance)
2. **Query**: Run prompts against multiple LLMs
3. **Score**: Evaluate responses on multiple dimensions
4. **Report**: Generate comprehensive reports

### Example
```python
from config.builder import preset_university
from utils.model_runner import ModelRunner
from scoring.scorer import ScoringEngine

# Create config
config = preset_university(client_name="Durham University")

# Run evaluation
runner = ModelRunner(config.models)
responses = runner.run()

# Score responses
scorer = ScoringEngine()
results = scorer.score_batch(responses)

# Generate report
from generate_report import generate_report
generate_report(results, output_format="pdf")
```

═══════════════════════════════════════════════════════════════════════════════

## 🎓 Fine-tuning Pipeline

### Supported Models
- **OpenAI**: GPT-3.5-turbo, GPT-4, GPT-4 Turbo
- **Open-Source**: Llama 2/3, Mistral, Falcon
- **Local**: Full LoRA or memory-efficient QLoRA

### Workflow
1. **Collect**: Extract high-quality responses from evaluations
2. **Prepare**: Build balanced training dataset
3. **Fine-tune**: Train on domain-specific data
4. **Deploy**: Use fine-tuned models in production

### Example: OpenAI Fine-tuning
```python
from finetuning.dataset_builder import DatasetBuilder
from finetuning.openai_finetuner import OpenAIFinetuner

# Collect high-quality examples
builder = DatasetBuilder()
builder.add_from_evaluation_results("results/baseline.json", min_quality_score=85)
builder.export_jsonl("training_data.jsonl")

# Fine-tune
tuner = OpenAIFinetuner()
file_id = tuner.upload_training_file("training_data.jsonl")
job = tuner.create_finetuning_job(file_id, model="gpt-3.5-turbo")
status = tuner.wait_for_completion(job['id'])

print(f"Fine-tuned model: {status['fine_tuned_model']}")
```

### Example: Local Model Fine-tuning
```python
from finetuning.finetuner import Finetuner

tuner = Finetuner(
    model_id="meta-llama/Llama-2-7b",
    use_qlora=True  # Memory efficient
)

result = tuner.finetune(
    dataset_file="training_data.jsonl",
    epochs=3,
    batch_size=4,
    num_gpus=1
)

# Merge LoRA weights
merged_model = tuner.merge_lora_weights(result['output_dir'])
```

═══════════════════════════════════════════════════════════════════════════════

## 🔍 RAG System (Retrieval-Augmented Generation)

### Features
- ✅ Multi-source document ingestion (files, URLs, APIs)
- ✅ Automatic document chunking and embedding
- ✅ Vector similarity search with ChromaDB
- ✅ Hybrid retrieval (semantic + keyword search)
- ✅ LLM-based answer generation
- ✅ Multi-language support (English + Arabic)

### Supported Document Formats
- Text files (.txt, .md)
- PDF documents (.pdf)
- Microsoft Office (.docx, .pptx)
- Data formats (JSON, CSV)
- Web pages (via URLs)

### Workflow
1. **Ingest**: Load documents from multiple sources
2. **Chunk**: Split into manageable pieces
3. **Embed**: Generate vector embeddings
4. **Store**: Save to vector database
5. **Retrieve**: Find relevant documents for queries
6. **Generate**: Use LLM to create answers

### Example
```python
from rag.document_loader import FileDocumentLoader, DocumentChunker
from rag.vector_store import VectorStore
from rag.generation import RAGPipeline

# 1. Load documents
loader = FileDocumentLoader()
documents = loader.load("knowledge_base/")

# 2. Chunk documents
chunker = DocumentChunker()
chunks = []
for doc in documents:
    chunks.extend(chunker.chunk_by_tokens(doc, chunk_size=512))

# 3. Create vector store
vector_store = VectorStore(name="dalil_rag")
vector_store.add_documents(chunks)

# 4. Query
pipeline = RAGPipeline(vector_store)
result = pipeline.query(
    query="How do I file a complaint?",
    k=5,
    language="en"
)

print(f"Answer: {result['answer']}")
print(f"Sources: {result['retrieval']['matches']}")
```

═══════════════════════════════════════════════════════════════════════════════

## 📦 System Architecture

### Services
1. **Web API** (FastAPI on Uvicorn)
   - REST endpoints for evaluation, chat, reports
   - Dashboard for visualization
   - Authentication & session management

2. **Evaluation Engine**
   - Multi-model runner with caching
   - Scoring engine with multiple dimensions
   - Report generator

3. **Fine-tuning Service**
   - Dataset builder from evaluation results
   - OpenAI API integration
   - Local model training (LoRA/QLoRA)

4. **RAG System**
   - Document loader & chunker
   - Vector embedding engine
   - Citation & source tracking

5. **Database**
   - PostgreSQL for persistent data
   - Redis for caching
   - ChromaDB for vector storage

### Technology Stack
- **Framework**: FastAPI 0.115+
- **Server**: Uvicorn + Gunicorn
- **Database**: PostgreSQL 13+
- **Cache**: Redis 6+
- **Vector DB**: ChromaDB 1.0+
- **ML**: Transformers, PyTorch
- **LLMs**: OpenAI, Anthropic, local models

═══════════════════════════════════════════════════════════════════════════════

## 🌐 Deployment Options

### Option 1: Traditional (Systemd + Nginx)
Best for: VPS, on-premise servers

```bash
# Install dependencies
sudo apt install postgresql redis-server nginx

# Deploy app
sudo systemctl start dalil-group
sudo systemctl enable dalil-group

# Configure reverse proxy
sudo systemctl restart nginx
```

### Option 2: Docker Compose (Recommended)
Best for: Consistency, easy scaling

```bash
docker-compose -f docker-compose.prod.yml up -d
```

See PRODUCTION_DEPLOYMENT.md for detailed instructions.

═══════════════════════════════════════════════════════════════════════════════

## 📈 Monitoring & Operations

### Health Checks
```bash
# API health
curl http://localhost:8000/health

# Database
python -c "from database import engine; engine.execute('SELECT 1')"

# Redis
redis-cli ping

# Vector store
python cli_rag.py search --query "test"
```

### Common Commands
```bash
# View logs
journalctl -u dalil-group -f

# Database maintenance
sudo -u postgres vacuumdb dalil_group

# Backup
/usr/local/bin/backup-dalil-group.sh

# Update application
git pull && pip install -r requirements.txt && systemctl restart dalil-group
```

### Metrics
- Request latency
- Model API costs
- Vector store size
- Fine-tuning progress

═══════════════════════════════════════════════════════════════════════════════

## 🔒 Security Checklist

- [ ] SSL/TLS certificates installed
- [ ] Environment variables secured (.env file)
- [ ] Database encrypted
- [ ] API keys rotated regularly
- [ ] Rate limiting enabled
- [ ] CORS configured properly
- [ ] SQL injection protection (ORM)
- [ ] Backup strategy implemented
- [ ] Monitoring/alerting configured
- [ ] Security patches applied

═══════════════════════════════════════════════════════════════════════════════

## 📚 Key Files

### Core Modules
- `finetuning/` - Fine-tuning pipeline
- `rag/` - RAG system
- `web/` - Web interface
- `scoring/` - Evaluation scoring
- `utils/` - Utilities

### CLI Tools
- `cli_eval.py` - Evaluation management
- `cli_finetune.py` - Fine-tuning management
- `cli_rag.py` - RAG operations

### Configuration
- `requirements.txt` - Python dependencies
- `docker-compose.prod.yml` - Production deployment
- `PRODUCTION_DEPLOYMENT.md` - Detailed deployment guide

═══════════════════════════════════════════════════════════════════════════════

## 💡 Use Cases

### 1. Baseline & Benchmarking
```bash
python cli_eval.py run --preset government --use-judge --report pdf
```
Compare LLM performance, identify strengths/weaknesses

### 2. Model Improvement via Fine-tuning
```bash
# Collect high-quality responses
python cli_eval.py export --results-file results/baseline.json

# Fine-tune on domain data
python cli_finetune.py openai --training-file training_data.jsonl --wait

# Re-evaluate with fine-tuned model
python cli_eval.py run --preset government
```

### 3. Knowledge Assistant
```bash
# Load organizational documents
python cli_rag.py ingest --files knowledge_base/ --urls "https://help.example.com"

# Users chat with RAG system
# via web interface or API
```

### 4. Automated Evaluation Pipeline
```bash
# Daily evaluation via cron
0 2 * * * cd /path && python cli_eval.py run --preset university --use-judge
```

═══════════════════════════════════════════════════════════════════════════════

## 🆘 Troubleshooting

### Common Issues

**Issue: Vector store not finding documents**
```bash
# Reingest documents
python cli_rag.py ingest --files knowledge_base/ --collection dalil_rag
```

**Issue: Fine-tuning stuck**
```bash
# Check job status
python cli_finetune.py status --job-id <job_id>

# Cancel if needed
python cli_finetune.py cancel --job-id <job_id>
```

**Issue: Evaluation slow**
```bash
# Enable caching
# Check REDIS_URL in .env
redis-cli info

# Run with dry-run first
python cli_eval.py run --preset government --dry-run
```

═══════════════════════════════════════════════════════════════════════════════

## 📞 Support

For detailed deployment instructions, see:
- `PRODUCTION_DEPLOYMENT.md` - Complete deployment guide
- `IMPLEMENTATION_SUMMARY.md` - Architecture overview  
- `PRODUCTION_SETUP.md` - Security & hardening

═══════════════════════════════════════════════════════════════════════════════
Generated: April 15, 2026
Version: 2.0.0
"""

if __name__ == "__main__":
    print(README)
