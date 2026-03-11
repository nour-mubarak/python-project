"""
LinguaEval Configuration Builder
Defines evaluation parameters for each client engagement.
"""

import json
import yaml
import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import datetime


VALID_SECTORS = [
    "government",
    "university",
    "finance",
    "healthcare",
    "legal",
    "general",
]
VALID_DIMENSIONS = [
    "accuracy",
    "bias",
    "hallucination",
    "consistency",
    "cultural",
    "fluency",
]
VALID_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "claude-sonnet-4-20250514",
    "claude-haiku-4-5-20251001",
    "gemma-3",
    "azure-gpt-4o",  # Azure-hosted
    # Groq free tier models
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
    # Ollama local models
    "ollama-llama3.2",
    "ollama-mistral",
    "ollama-gemma2",
    "ollama-qwen2.5",
]


@dataclass
class ModelConfig:
    """Configuration for a single model to evaluate."""

    model_id: str
    display_name: str
    provider: str  # "openai", "anthropic", "azure", "custom"
    temperature: float = 0.3
    max_tokens: int = 1024
    system_prompt: str = ""
    api_endpoint: Optional[str] = None  # For custom/Azure endpoints

    def validate(self):
        if self.provider not in ["openai", "anthropic", "azure", "custom"]:
            raise ValueError(f"Invalid provider: {self.provider}")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(f"Temperature must be 0.0-2.0, got {self.temperature}")


@dataclass
class EvaluationConfig:
    """Complete configuration for an evaluation engagement."""

    # Client details
    client_name: str
    client_contact: str = ""
    sector: str = "general"
    use_case: str = ""
    evaluation_objective: str = ""

    # Models to evaluate
    models: List[str] = field(
        default_factory=lambda: ["gpt-4o", "claude-sonnet-4-20250514"]
    )

    # Evaluation parameters
    dimensions: List[str] = field(default_factory=lambda: VALID_DIMENSIONS.copy())
    languages: List[str] = field(default_factory=lambda: ["en", "ar"])
    prompt_pack: str = "general"  # Sector name or path to custom pack

    # Scoring
    judge_model: str = "claude-sonnet-4-20250514"  # Model used to score outputs
    runs_per_prompt: int = 1  # Repeat each prompt N times for stability

    # Privacy mode
    privacy_mode: str = "mode_a"  # mode_a, mode_b, mode_c

    # Output
    report_format: str = "docx"  # docx, pdf, json
    output_dir: str = "results"

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "1.0"

    def validate(self):
        """Validate all configuration parameters."""
        if self.sector not in VALID_SECTORS:
            raise ValueError(
                f"Invalid sector '{self.sector}'. Must be one of: {VALID_SECTORS}"
            )

        for dim in self.dimensions:
            if dim not in VALID_DIMENSIONS:
                raise ValueError(
                    f"Invalid dimension '{dim}'. Must be one of: {VALID_DIMENSIONS}"
                )

        for lang in self.languages:
            if lang not in ["en", "ar"]:
                raise ValueError(f"Invalid language '{lang}'. Must be 'en' or 'ar'")

        if len(self.models) < 1:
            raise ValueError("Must evaluate at least 1 model")
        if len(self.models) > 5:
            raise ValueError("Maximum 5 models per evaluation")

        if self.privacy_mode not in ["mode_a", "mode_b", "mode_c"]:
            raise ValueError(f"Invalid privacy mode: {self.privacy_mode}")

    def get_model_configs(self) -> List[ModelConfig]:
        """Generate ModelConfig objects for each model ID."""
        configs = []
        for model_id in self.models:
            if model_id.startswith("gpt") or model_id.startswith("azure"):
                provider = "azure" if model_id.startswith("azure") else "openai"
                configs.append(
                    ModelConfig(
                        model_id=model_id.replace("azure-", ""),
                        display_name=model_id.upper().replace("-", " "),
                        provider=provider,
                        temperature=0.3,
                    )
                )
            elif model_id.startswith("claude"):
                configs.append(
                    ModelConfig(
                        model_id=model_id,
                        display_name=model_id.split("-")[0].title()
                        + " "
                        + model_id.split("-")[1].title(),
                        provider="anthropic",
                        temperature=0.3,
                    )
                )
            elif model_id.startswith("ollama-"):
                # Ollama local models
                actual_model = model_id.replace("ollama-", "")
                configs.append(
                    ModelConfig(
                        model_id=actual_model,
                        display_name=f"Ollama {actual_model.title()}",
                        provider="ollama",
                        temperature=0.3,
                    )
                )
            elif model_id in [
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "mixtral-8x7b-32768",
                "gemma2-9b-it",
            ]:
                # Groq free tier models
                configs.append(
                    ModelConfig(
                        model_id=model_id,
                        display_name=model_id.split("-")[0].title() + " (Groq)",
                        provider="groq",
                        temperature=0.3,
                    )
                )
            else:
                configs.append(
                    ModelConfig(
                        model_id=model_id,
                        display_name=model_id,
                        provider="custom",
                        temperature=0.3,
                    )
                )
        return configs

    def save(self, path: str):
        """Save configuration to YAML file."""
        self.validate()
        os.makedirs(
            os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True
        )
        with open(path, "w") as f:
            yaml.dump(asdict(self), f, default_flow_style=False, allow_unicode=True)
        print(f"Config saved to {path}")

    @classmethod
    def load(cls, path: str) -> "EvaluationConfig":
        """Load configuration from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        config = cls(**data)
        config.validate()
        return config

    def summary(self) -> str:
        """Print a human-readable summary."""
        return f"""
╔══════════════════════════════════════════════════════╗
║           LINGUAEVAL EVALUATION CONFIG               ║
╠══════════════════════════════════════════════════════╣
║ Client:      {self.client_name:<38} ║
║ Sector:      {self.sector:<38} ║
║ Use Case:    {self.use_case[:38]:<38} ║
║ Models:      {', '.join(self.models)[:38]:<38} ║
║ Languages:   {', '.join(self.languages):<38} ║
║ Dimensions:  {len(self.dimensions)} of {len(VALID_DIMENSIONS):<33} ║
║ Prompt Pack: {self.prompt_pack:<38} ║
║ Privacy:     {self.privacy_mode:<38} ║
║ Judge Model: {self.judge_model:<38} ║
╚══════════════════════════════════════════════════════╝
"""


# ─── Preset configurations for common engagement types ───


def preset_university() -> EvaluationConfig:
    """Preset for university administration evaluation."""
    return EvaluationConfig(
        client_name="[University Name]",
        sector="university",
        use_case="Policy Q&A and student services",
        evaluation_objective="Evaluate AI assistants for multilingual policy access and student guidance",
        models=["gpt-4o", "claude-sonnet-4-20250514"],
        prompt_pack="university",
    )


def preset_government() -> EvaluationConfig:
    """Preset for government/public sector evaluation."""
    return EvaluationConfig(
        client_name="[Government Entity]",
        sector="government",
        use_case="Public service delivery and policy information",
        evaluation_objective="Evaluate AI systems for bilingual citizen-facing services",
        models=["gpt-4o", "claude-sonnet-4-20250514", "gpt-4o-mini"],
        prompt_pack="government",
    )


def preset_finance() -> EvaluationConfig:
    """Preset for financial services evaluation."""
    return EvaluationConfig(
        client_name="[Financial Institution]",
        sector="finance",
        use_case="Customer service and internal knowledge access",
        evaluation_objective="Evaluate AI for bilingual financial services with compliance focus",
        models=["gpt-4o", "claude-sonnet-4-20250514"],
        prompt_pack="finance",
        dimensions=["accuracy", "bias", "hallucination", "consistency", "fluency"],
    )


def preset_free() -> EvaluationConfig:
    """Preset using free API models (Groq)."""
    return EvaluationConfig(
        client_name="[Client Name]",
        sector="general",
        use_case="General evaluation with free models",
        evaluation_objective="Evaluate free-tier AI models for multilingual tasks",
        models=["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
        judge_model="llama-3.3-70b-versatile",
        prompt_pack="university",
    )


def preset_local() -> EvaluationConfig:
    """Preset using local Ollama models (completely free)."""
    return EvaluationConfig(
        client_name="[Client Name]",
        sector="general",
        use_case="Local evaluation with Ollama",
        evaluation_objective="Evaluate local AI models for multilingual tasks",
        models=["ollama-llama3.1:latest", "ollama-gemma3:27b"],
        judge_model="ollama-llama3.1:latest",
        prompt_pack="university",
    )


if __name__ == "__main__":
    # Example: Create and save a config
    config = preset_university()
    config.client_name = "Durham University"
    config.client_contact = "CIO Office"
    print(config.summary())
    config.save("config/durham_eval.yaml")
