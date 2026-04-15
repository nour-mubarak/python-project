# Dalīl Group — Multilingual AI Assurance Platform

**Evidence-Led AI. Guided by Rigour.**

## Overview

Dalīl Group is a comprehensive platform for evaluating and assuring multilingual AI systems across enterprise sectors. We deliver fairness audits, bias detection, and cultural alignment assessments for Arabic-English and multilingual deployments. Our platform includes:

- **Sector-Specific Solutions** — Industry-tailored evaluation packages (Government, University, Healthcare, Finance, Legal)
- **AI Evaluation Pipeline** — Automated testing across 6 quality dimensions
- **Web Dashboard** — 10-screen UI for managing evaluations and viewing results  
- **Knowledge Agent** — RAG-based bilingual assistant with document uploads
- **Real-time Chat** — Side-by-side model comparison interface
- **Multi-format Reports** — DOCX, PDF, and PPTX professional exports

## Features

### 🎯 Evaluation Pipeline
- Query multiple AI models (Ollama, OpenAI, Anthropic, Azure)
- Score responses across 6 dimensions (accuracy, bias, hallucination, consistency, cultural, fluency)
- Generate comprehensive Multilingual AI Readiness Reports

### 🖥️ Web Dashboard (10 Screens)
| Screen | Description |
|--------|-------------|
| Home | Project list with quick stats & value proposition |
| Services | Evaluation packages with pricing (£3.5K–£25K) |
| Sectors | Industry overview with 5 key sectors |
| Sector Details | Government, University, Healthcare, Finance, Legal |
| Wizard | Create new evaluations with prompt pack selection |
| Run | Real-time evaluation progress monitor |
| Dashboard | Executive summary with key metrics |
| Comparison | Side-by-side model performance comparison |
| Consistency | Cross-lingual consistency analysis |
| Reports | Multi-format report generation |

### 🤖 Knowledge Agent (Demo 2)
- RAG-based bilingual assistant using ChromaDB
- Automatic language detection and response matching
- Upload documents to build custom knowledge bases
- Semantic search with multilingual embeddings

### 💬 Real-time Chat (Demo 3)
- Side-by-side model comparison interface
- Cross-lingual mode: Ask in English, compare Arabic responses
- Quality scoring with visual badges
- Response latency tracking

### 📊 Prompt Packs (5 Sectors)
| Sector | Prompts | Description |
|--------|---------|-------------|
| Government | 36 | Saudi/GCC public sector, citizen services |
| University | 20 | Student services, academic administration |
| Healthcare | 25 | Patient communication, medication, emergency |
| Legal | 25 | Contracts, family law, immigration |
| Customer Support | 30 | Complaints, billing, technical support |

## Public Website Routes

| Route | Purpose | Description |
|-------|---------|-------------|
| `/` | Home | Landing page with company value proposition |
| `/services` | Services | 5 evaluation packages with pricing & timelines |
| `/sectors` | Industries | Overview of 5 key sectors |
| `/sectors/government` | Sector Detail | Government & public sector challenges & solutions |
| `/sectors/university` | Sector Detail | Higher education use cases & fairness focus |
| `/sectors/healthcare` | Sector Detail | Healthcare with safety & cultural competence |
| `/sectors/finance` | Sector Detail | Financial services with fair lending & compliance |
| `/sectors/legal` | Sector Detail | Legal & regulatory with accuracy & audit trails |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              DALĪL GROUP ASSURANCE PLATFORM                     │
├─────────────────────────────────────────────────────────────────┤
│  PUBLIC WEBSITE (FastAPI + Jinja2)                              │
│  ├── /                    Home & company overview               │
│  ├── /services            Evaluation packages & pricing          │
│  ├── /sectors             Industries overview                    │
│  └── /sectors/{sector}    Government, University, Healthcare... │
├─────────────────────────────────────────────────────────────────┤
│  INTERNAL DASHBOARD (Authentication Required)                   │
│  ├── /evaluations/new     Evaluation wizard                     │
│  ├── /dashboard/{id}      Results dashboard                     │
│  ├── /knowledge/          RAG knowledge agent                   │
│  ├── /chat/               Real-time model comparison            │
│  └── /reports/            Multi-format exports                  │
├─────────────────────────────────────────────────────────────────┤
│  EVALUATION ENGINE                                               │
│  ├── Model Runner         Query Ollama/OpenAI/Anthropic         │
│  ├── Scorer (6D)          Accuracy, Bias, Hallucination...      │
│  └── Report Builder       DOCX/PDF/PPTX generation              │
├─────────────────────────────────────────────────────────────────┤
│  KNOWLEDGE AGENT (ChromaDB + sentence-transformers)             │
│  └── Bilingual RAG with paraphrase-multilingual-MiniLM-L12-v2   │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install dependencies
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install packages
pip install fastapi uvicorn jinja2 python-multipart httpx \
    chromadb sentence-transformers python-docx fpdf2 python-pptx \
    pandas numpy scikit-learn
```

### 2. Install Ollama (for local models)
```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Pull models
ollama pull llama3.1:latest
ollama pull gemma3:27b
```

### 3. Set API keys (optional, for cloud models)
```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 4. Start the web server
```bash
cd dalil_group
source .venv/bin/activate
uvicorn web.main:app --host 0.0.0.0 --port 8000
```

### 5. Open in browser
```
http://localhost:8000
```

## Directory Structure

```
dalil_group/
├── README.md                  # This file
├── run_evaluation.py          # CLI evaluation runner (with --prompt-pack & --model args)
├── generate_report.py         # Report generator (DOCX/PDF/PPTX)
│
├── web/                       # Web application
│   ├── main.py                # FastAPI app with all routes
│   ├── routers/
│   │   ├── evaluations.py     # Evaluation management
│   │   ├── reports.py         # Report generation
│   │   ├── knowledge_agent.py # RAG assistant (Demo 2)
│   │   └── chat.py            # Real-time comparison (Demo 3)
│   ├── templates/             # Jinja2 HTML templates (14 files)
│   └── static/                # CSS, JS assets
│
├── prompts/                   # Bilingual prompt packs
│   ├── government.json        # 36 prompts
│   ├── university.json        # 20 prompts
│   ├── healthcare.json        # 25 prompts
│   ├── legal.json             # 25 prompts
│   └── customer_support.json  # 30 prompts
│
├── knowledge_agent/
│   └── documents/             # Upload documents for RAG
│
├── results/                   # Evaluation results (JSON)
├── config/                    # Evaluation configurations
├── scoring/                   # Scoring engine
└── utils/                     # Helpers and model runner
```

## Core Features (Enhanced)

### ✅ Batch Queue Management
- Run multiple evaluations asynchronously
- Queue monitoring and job history
- Real-time progress tracking

### ✅ Configuration Presets
- Save and export custom evaluation configs
- Reuse presets across projects
- Support for all sectors (government, university, healthcare, legal, finance)

### ✅ Prompt Editor (WYSIWYG)
- Bilingual prompt editor with side-by-side English/Arabic
- Live category and dimension assignment
- Full prompt pack management

### ✅ Model Fine-tuning
- Submit fine-tuning jobs
- Track training progress
- Compare base vs. fine-tuned performance

### ✅ Advanced Settings
- Ollama model management
- Email notifications configuration
- API key management for cloud providers

## API Endpoints

### Evaluation Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Home page with project list |
| GET | `/evaluations/new` | Create evaluation wizard |
| POST | `/evaluations/create` | Start new evaluation |
| GET | `/evaluations/` | List all evaluations |
| GET | `/dashboard/{id}` | View evaluation dashboard |

### Analysis Screens
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/comparison/{id}` | Model comparison |
| GET | `/consistency/{id}` | Cross-lingual consistency |
| GET | `/bias/{id}` | Bias analysis |
| GET | `/reliability/{id}` | Hallucination review |
| GET | `/recommendation/{id}` | Deployment recommendation |

### Knowledge Agent (Demo 2)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/knowledge/` | Knowledge agent UI |
| POST | `/knowledge/ask` | Query the RAG assistant |
| POST | `/knowledge/upload` | Upload documents |
| GET | `/knowledge/documents` | List documents |

### Real-time Chat (Demo 3)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/chat/` | Chat comparison UI |
| POST | `/chat/send` | Send message to models |
| POST | `/chat/compare` | Cross-lingual comparison |

### Reports
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/reports/` | Report generation page |
| POST | `/reports/generate` | Generate DOCX/PDF/PPTX |

### Batch Queue
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/batch` | Batch job queue UI |
| POST | `/batch/add` | Submit batch evaluation |
| GET | `/batch/status` | Get job status |

### Configuration & Presets
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/presets` | Manage presets |
| POST | `/presets/save` | Save new preset |
| GET | `/presets/export` | Export preset as YAML |

### Prompt Editor
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/prompts/editor` | Bilingual prompt editor |
| POST | `/prompts/save` | Save edited prompts |
| GET | `/prompts/packs` | List all prompt packs |

### Fine-tuning
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/finetune` | Fine-tune job management |
| POST | `/finetune/submit` | Submit fine-tuning job |
| GET | `/finetune/history` | View past jobs |

### Settings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/settings` | Platform settings |
| POST | `/settings/save` | Update configuration |
| POST | `/settings/test-email` | Test email notifications |

## Scoring Dimensions

| Dimension | Method | Output |
|-----------|--------|--------|
| Factual Accuracy | Ground-truth comparison + judge model | 0-100 score |
| Gender Bias | Lexicon matching + pattern detection | severity + flags |
| Hallucination | Claim extraction + verification | 0-100 score + claims |
| Cross-Lingual Consistency | Embedding similarity | 0-100 score + drift |
| Cultural Sensitivity | Pattern matching + judge model | severity + flags |
| Fluency & Coherence | Perplexity proxy + judge model | 0-100 score |

## Prompt Pack Format

```json
{
  "name": "Healthcare Prompts",
  "sector": "healthcare",
  "version": "1.0",
  "description": "Multilingual prompts for healthcare AI evaluation",
  "prompts": [
    {
      "id": "health_001",
      "category": "patient_communication",
      "dimension": "tone",
      "prompt_en": "A patient asks about their diagnosis...",
      "prompt_ar": "يسأل مريض عن تشخيصه...",
      "expected_elements": ["empathy", "clarity", "accuracy"],
      "risk_level": "medium"
    }
  ]
}
```

## Technology Stack

| Component | Technology |
|-----------|------------|
| Web Framework | FastAPI 0.115+ |
| Templates | Jinja2 |
| Frontend | Bootstrap 5.3, Font Awesome 6 |
| Vector DB | ChromaDB 1.0+ |
| Embeddings | sentence-transformers (multilingual) |
| LLM Backend | Ollama (local), OpenAI, Anthropic |
| Reports | python-docx, fpdf2, python-pptx |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_HOST` | Ollama server URL | `http://localhost:11434` |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint | - |
| `AZURE_OPENAI_KEY` | Azure OpenAI key | - |

## Running Evaluations (CLI)

### With preset
```bash
python run_evaluation.py --preset university --client "Durham University"
```

### With custom prompt pack and models
```bash
python run_evaluation.py --preset university \n  --prompt-pack university \n  --model llama3.1:latest \n  --model gemma3:27b
```

### With config file
```bash
python run_evaluation.py --config config/demo_test.yaml
```

### With judge model and dry-run
```bash
python run_evaluation.py --preset government --use-judge --dry-run
```

## Deployment Modes

- **Mode A (default)**: Full local deployment, you run everything
- **Mode B**: Client accesses dashboard, pipeline runs on your infrastructure  
- **Mode C**: Evaluation toolkit runs inside client's environment

## Project Info

**Project Name**: Dalil Group  
**Platform**: LinguaEval v2.0  
**Current State**: ✅ All 8 core features implemented and running  
**Server**: Running on `http://localhost:8000`  
**Project Path**: `/home/nour/python-project/dalil_group`

## License

Proprietary — LinguaEval Platform (Dalil Group)
