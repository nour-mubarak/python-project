# LinguaEval — Evaluation Pipeline

## Overview

This is the production evaluation infrastructure for LinguaEval.
It queries multiple AI models, collects responses in Arabic and English,
scores them across 6 dimensions, and generates a Multilingual AI Readiness Report.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    EVALUATION PIPELINE                    │
│                                                           │
│  1. CONFIG          → Define client, models, dimensions   │
│  2. PROMPT PACKS    → Bilingual test suites by sector     │
│  3. MODEL RUNNER    → Query models via API, collect output │
│  4. SCORING ENGINE  → Score outputs across 6 dimensions   │
│  5. REPORT BUILDER  → Generate Readiness Report (docx)    │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install dependencies
```bash
pip install openai anthropic httpx python-docx pandas numpy scikit-learn --break-system-packages
```

### 2. Set API keys
```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
# Optional: Azure OpenAI
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_KEY="..."
```

### 3. Configure an evaluation
Edit `config/evaluation_config.yaml` or use the Python config builder:
```python
from config.builder import EvaluationConfig
config = EvaluationConfig(
    client_name="Durham University",
    sector="university",
    models=["gpt-4o", "claude-sonnet-4-20250514"],
    dimensions=["accuracy", "bias", "hallucination", "consistency", "cultural", "fluency"],
    languages=["en", "ar"],
)
config.save("config/durham_eval.yaml")
```

### 4. Run the evaluation
```bash
python run_evaluation.py --config config/durham_eval.yaml
```

### 5. Generate the report
```bash
python generate_report.py --results results/durham_eval_results.json
```

## Directory Structure

```
linguaeval/
├── README.md                  # This file
├── run_evaluation.py          # Main entry point
├── generate_report.py         # Report generator
├── config/
│   ├── builder.py             # Evaluation config builder
│   └── evaluation_config.yaml # Sample config
├── prompts/
│   ├── base_prompts.py        # Prompt pack manager
│   ├── government.json        # Government sector prompts
│   ├── university.json        # University sector prompts
│   └── finance.json           # Finance sector prompts
├── scoring/
│   ├── scorer.py              # Main scoring engine
│   ├── bias_detector.py       # Arabic/English bias detection
│   ├── hallucination.py       # Factual accuracy checker
│   ├── consistency.py         # Cross-lingual consistency
│   └── arabic_gender_lexicon.py # Arabic gendered term database
├── utils/
│   ├── model_runner.py        # Multi-model API client
│   └── helpers.py             # Utility functions
└── reports/
    └── report_builder.py      # DOCX report generator
```

## Prompt Pack Format

Each prompt pack is a JSON file with this structure:
```json
{
  "sector": "government",
  "version": "1.0",
  "prompts": [
    {
      "id": "GOV-001",
      "category": "factual_accuracy",
      "en": "What is the role of SDAIA in Saudi Arabia?",
      "ar": "ما هو دور هيئة سدايا في المملكة العربية السعودية؟",
      "ground_truth_en": "SDAIA is the national authority for data and AI...",
      "ground_truth_ar": "سدايا هي الجهة الوطنية المختصة بالبيانات والذكاء الاصطناعي...",
      "evaluation_dimensions": ["accuracy", "hallucination", "consistency"],
      "sensitivity": "low"
    }
  ]
}
```

## Scoring Dimensions

| Dimension | Method | Output |
|-----------|--------|--------|
| Factual Accuracy | Ground-truth comparison + judge model | 0-100 score |
| Gender Bias | Lexicon matching + pattern detection | severity: low/medium/high + flags |
| Hallucination | Claim extraction + verification | 0-100 score + flagged claims |
| Cross-Lingual Consistency | Embedding similarity + semantic comparison | 0-100 score + drift examples |
| Cultural Sensitivity | Pattern matching + judge model | severity + flags |
| Fluency & Coherence | Perplexity proxy + judge model | 0-100 score |

## Privacy Modes

- **Mode A (default)**: You run everything, client gets the report
- **Mode B**: Client accesses dashboard, you run pipeline behind scenes
- **Mode C**: Evaluation toolkit runs inside client environment

## Notes

- Start with Mode A for your first clients — it requires the least engineering
- The scoring uses a combination of automated methods and judge-model evaluation
- For sensitive clients, all data stays local — no outputs are sent externally
- Prompt packs are your core IP — invest time in making them comprehensive
