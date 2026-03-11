"""
LinguaEval Model Runner
Queries multiple AI models via their APIs, collects and stores responses.
Supports OpenAI, Anthropic (Claude), Azure OpenAI, Groq (free), and Ollama (local).
"""

import os
import json
import time
import asyncio
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional


@dataclass
class ModelResponse:
    """A single model response to a single prompt."""

    prompt_id: str
    model_id: str
    provider: str
    language: str
    prompt_text: str
    response_text: str
    tokens_input: int
    tokens_output: int
    latency_ms: float
    temperature: float
    timestamp: str
    error: Optional[str] = None


class ModelRunner:
    """Runs prompts against multiple models and collects responses."""

    def __init__(self, model_configs: list):
        self.model_configs = model_configs
        self.responses: List[ModelResponse] = []
        self._init_clients()

    def _init_clients(self):
        """Initialise API clients for each provider."""
        self.clients = {}

        # OpenAI
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            try:
                from openai import OpenAI

                self.clients["openai"] = OpenAI(api_key=openai_key)
                print("[+] OpenAI client initialised")
            except ImportError:
                print("[!] openai package not installed. Run: pip install openai")

        # Anthropic
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            try:
                import anthropic

                self.clients["anthropic"] = anthropic.Anthropic(api_key=anthropic_key)
                print("[+] Anthropic client initialised")
            except ImportError:
                print("[!] anthropic package not installed. Run: pip install anthropic")

        # Azure OpenAI
        azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        azure_key = os.environ.get("AZURE_OPENAI_KEY")
        if azure_endpoint and azure_key:
            try:
                from openai import AzureOpenAI

                self.clients["azure"] = AzureOpenAI(
                    azure_endpoint=azure_endpoint,
                    api_key=azure_key,
                    api_version="2024-02-15-preview",
                )
                print("[+] Azure OpenAI client initialised")
            except ImportError:
                print("[!] openai package not installed for Azure")

        # Groq (free tier)
        groq_key = os.environ.get("GROQ_API_KEY")
        if groq_key:
            try:
                from groq import Groq

                self.clients["groq"] = Groq(api_key=groq_key)
                print("[+] Groq client initialised (free tier)")
            except ImportError:
                print("[!] groq package not installed. Run: pip install groq")

        # Ollama (local, free)
        ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        try:
            import httpx

            # Check if Ollama is running
            resp = httpx.get(f"{ollama_host}/api/tags", timeout=2.0)
            if resp.status_code == 200:
                self.clients["ollama"] = ollama_host
                print(f"[+] Ollama client initialised at {ollama_host}")
        except Exception:
            pass  # Ollama not running, skip silently

    def _query_openai(self, model_config, prompt: str, system_prompt: str = "") -> dict:
        """Query OpenAI API."""
        client = self.clients.get("openai")
        if not client:
            return {"error": "OpenAI client not available"}

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        start = time.time()
        try:
            response = client.chat.completions.create(
                model=model_config.model_id,
                messages=messages,
                temperature=model_config.temperature,
                max_tokens=model_config.max_tokens,
            )
            latency = (time.time() - start) * 1000

            return {
                "text": response.choices[0].message.content,
                "tokens_input": response.usage.prompt_tokens,
                "tokens_output": response.usage.completion_tokens,
                "latency_ms": round(latency, 1),
            }
        except Exception as e:
            return {"error": str(e)}

    def _query_anthropic(
        self, model_config, prompt: str, system_prompt: str = ""
    ) -> dict:
        """Query Anthropic Claude API."""
        client = self.clients.get("anthropic")
        if not client:
            return {"error": "Anthropic client not available"}

        start = time.time()
        try:
            kwargs = {
                "model": model_config.model_id,
                "max_tokens": model_config.max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            response = client.messages.create(**kwargs)
            latency = (time.time() - start) * 1000

            return {
                "text": response.content[0].text,
                "tokens_input": response.usage.input_tokens,
                "tokens_output": response.usage.output_tokens,
                "latency_ms": round(latency, 1),
            }
        except Exception as e:
            return {"error": str(e)}

    def _query_azure(self, model_config, prompt: str, system_prompt: str = "") -> dict:
        """Query Azure OpenAI API."""
        client = self.clients.get("azure")
        if not client:
            return {"error": "Azure OpenAI client not available"}

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        start = time.time()
        try:
            response = client.chat.completions.create(
                model=model_config.model_id,
                messages=messages,
                temperature=model_config.temperature,
                max_tokens=model_config.max_tokens,
            )
            latency = (time.time() - start) * 1000

            return {
                "text": response.choices[0].message.content,
                "tokens_input": response.usage.prompt_tokens,
                "tokens_output": response.usage.completion_tokens,
                "latency_ms": round(latency, 1),
            }
        except Exception as e:
            return {"error": str(e)}

    def _query_groq(self, model_config, prompt: str, system_prompt: str = "") -> dict:
        """Query Groq API (free tier)."""
        client = self.clients.get("groq")
        if not client:
            return {"error": "Groq client not available. Set GROQ_API_KEY env var."}

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        start = time.time()
        try:
            response = client.chat.completions.create(
                model=model_config.model_id,
                messages=messages,
                temperature=model_config.temperature,
                max_tokens=model_config.max_tokens,
            )
            latency = (time.time() - start) * 1000

            return {
                "text": response.choices[0].message.content,
                "tokens_input": response.usage.prompt_tokens,
                "tokens_output": response.usage.completion_tokens,
                "latency_ms": round(latency, 1),
            }
        except Exception as e:
            return {"error": str(e)}

    def _query_ollama(self, model_config, prompt: str, system_prompt: str = "") -> dict:
        """Query Ollama (local, free)."""
        host = self.clients.get("ollama")
        if not host:
            return {"error": "Ollama not available. Start Ollama with: ollama serve"}

        import httpx

        start = time.time()
        try:
            payload = {
                "model": model_config.model_id,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": model_config.temperature,
                    "num_predict": model_config.max_tokens,
                },
            }
            if system_prompt:
                payload["system"] = system_prompt

            resp = httpx.post(f"{host}/api/generate", json=payload, timeout=120.0)
            resp.raise_for_status()
            data = resp.json()
            latency = (time.time() - start) * 1000

            return {
                "text": data.get("response", ""),
                "tokens_input": data.get("prompt_eval_count", 0),
                "tokens_output": data.get("eval_count", 0),
                "latency_ms": round(latency, 1),
            }
        except Exception as e:
            return {"error": str(e)}

    def query_model(self, model_config, prompt: str, system_prompt: str = "") -> dict:
        """Route a query to the correct provider."""
        provider = model_config.provider
        if provider == "openai":
            return self._query_openai(model_config, prompt, system_prompt)
        elif provider == "anthropic":
            return self._query_anthropic(model_config, prompt, system_prompt)
        elif provider == "azure":
            return self._query_azure(model_config, prompt, system_prompt)
        elif provider == "groq":
            return self._query_groq(model_config, prompt, system_prompt)
        elif provider == "ollama":
            return self._query_ollama(model_config, prompt, system_prompt)
        else:
            return {"error": f"Unknown provider: {provider}"}

    def run_evaluation(
        self,
        prompts: List[dict],
        model_configs: list,
        system_prompt: str = "",
        runs_per_prompt: int = 1,
        progress_callback=None,
    ) -> List[ModelResponse]:
        """
        Run all prompts against all models in both languages.

        Args:
            prompts: List of prompt dicts with 'id', 'en', 'ar' fields
            model_configs: List of ModelConfig objects
            system_prompt: Optional system prompt for all queries
            runs_per_prompt: Number of times to repeat each prompt (for stability)
            progress_callback: Optional callable(current, total, message) for progress updates

        Returns:
            List of ModelResponse objects
        """
        self.responses = []
        total = len(prompts) * len(model_configs) * 2 * runs_per_prompt  # 2 = en + ar
        current = 0

        for prompt in prompts:
            for model_config in model_configs:
                for lang in ["en", "ar"]:
                    prompt_text = prompt.get(lang)
                    if not prompt_text:
                        continue

                    for run_idx in range(runs_per_prompt):
                        current += 1
                        if progress_callback:
                            progress_callback(
                                current,
                                total,
                                f"[{current}/{total}] {model_config.display_name} | {lang.upper()} | {prompt['id']}",
                            )

                        result = self.query_model(
                            model_config, prompt_text, system_prompt
                        )

                        response = ModelResponse(
                            prompt_id=prompt["id"],
                            model_id=model_config.model_id,
                            provider=model_config.provider,
                            language=lang,
                            prompt_text=prompt_text,
                            response_text=result.get("text", ""),
                            tokens_input=result.get("tokens_input", 0),
                            tokens_output=result.get("tokens_output", 0),
                            latency_ms=result.get("latency_ms", 0),
                            temperature=model_config.temperature,
                            timestamp=datetime.now().isoformat(),
                            error=result.get("error"),
                        )
                        self.responses.append(response)

                        # Rate limiting: small delay between requests
                        time.sleep(0.5)

        return self.responses

    def save_responses(self, path: str):
        """Save all responses to a JSON file."""
        os.makedirs(
            os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True
        )
        data = [asdict(r) for r in self.responses]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[+] Saved {len(data)} responses to {path}")

    @staticmethod
    def load_responses(path: str) -> List[ModelResponse]:
        """Load responses from a JSON file."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return [ModelResponse(**r) for r in data]

    def get_stats(self) -> dict:
        """Get summary statistics for the evaluation run."""
        if not self.responses:
            return {}

        total_tokens = sum(r.tokens_input + r.tokens_output for r in self.responses)
        errors = [r for r in self.responses if r.error]
        models = set(r.model_id for r in self.responses)
        prompts = set(r.prompt_id for r in self.responses)

        return {
            "total_responses": len(self.responses),
            "total_tokens": total_tokens,
            "unique_models": len(models),
            "unique_prompts": len(prompts),
            "errors": len(errors),
            "avg_latency_ms": round(
                sum(r.latency_ms for r in self.responses) / len(self.responses), 1
            ),
        }


def print_progress(current, total, message):
    """Simple progress callback for terminal output."""
    bar_len = 30
    filled = int(bar_len * current / total)
    bar = "\u2588" * filled + "\u2591" * (bar_len - filled)
    pct = round(100 * current / total)
    print(f"\r  {bar} {pct}% {message}", end="", flush=True)
    if current == total:
        print()  # newline at end
