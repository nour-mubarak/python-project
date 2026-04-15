#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG Generation Module
=====================

Generate answers using retrieved documents + LLM.
"""

import os
from typing import List, Dict, Any, Optional


class RAGGenerator:
    """
    Generate answers using retrieved context + LLM.
    """

    def __init__(
        self,
        llm_provider: str = "openai",
        model_id: str = "gpt-3.5-turbo",
        temperature: float = 0.3,
    ):
        """
        Initialize RAG generator.

        Args:
            llm_provider: 'openai', 'anthropic', 'ollama', etc.
            model_id: Model identifier
            temperature: Generation temperature
        """
        self.llm_provider = llm_provider
        self.model_id = model_id
        self.temperature = temperature
        self._init_llm()

    def _init_llm(self):
        """Initialize LLM client."""
        if self.llm_provider == "openai":
            try:
                import openai

                self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            except ImportError:
                raise ImportError("openai package required: pip install openai")

        elif self.llm_provider == "anthropic":
            try:
                import anthropic

                self.client = anthropic.Anthropic(
                    api_key=os.getenv("ANTHROPIC_API_KEY")
                )
            except ImportError:
                raise ImportError("anthropic package required: pip install anthropic")

        elif self.llm_provider == "ollama":
            # Ollama uses local HTTP API
            self.api_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")

        else:
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")

    def generate(
        self,
        query: str,
        context: List[str],
        language: str = "en",
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate answer from query and context.

        Args:
            query: User query
            context: List of context documents
            language: 'en' or 'ar'
            system_prompt: Optional custom system prompt

        Returns:
            Dict with 'answer', 'sources', 'metadata'
        """
        # Build prompt
        formatted_context = self._format_context(context)
        prompt = self._build_prompt(query, formatted_context, language, system_prompt)

        # Generate
        if self.llm_provider == "openai":
            result = self._generate_openai(prompt)
        elif self.llm_provider == "anthropic":
            result = self._generate_anthropic(prompt)
        elif self.llm_provider == "ollama":
            result = self._generate_ollama(prompt)

        return {
            "answer": result,
            "sources": self._extract_sources(context),
            "metadata": {
                "model": self.model_id,
                "provider": self.llm_provider,
                "query": query,
                "context_size": len(context),
            },
        }

    def _format_context(self, context: List[str]) -> str:
        """Format context documents."""
        formatted = ""
        for i, doc in enumerate(context, 1):
            formatted += f"\n[Source {i}]:\n{doc}\n"
        return formatted

    def _build_prompt(
        self,
        query: str,
        context: str,
        language: str,
        system_prompt: Optional[str],
    ) -> str:
        """Build the full prompt."""
        if system_prompt is None:
            if language == "ar":
                system_prompt = """أنت مساعد ذو معرفة متعمقة. استخدم المعلومات المقدمة لتجيب على السؤال.
إذا لم تعثر على الإجابة في السياق، قل ذلك بوضوح.
كن دقيقاً ومختصراً في إجابتك."""
            else:
                system_prompt = """You are a knowledgeable assistant. Use the provided information to answer the question.
If you cannot find the answer in the context, say so clearly.
Be precise and concise in your response."""

        prompt = f"""{system_prompt}

CONTEXT:
{context}

QUESTION:
{query}

ANSWER:"""

        return prompt

    def _generate_openai(self, prompt: str) -> str:
        """Generate using OpenAI."""
        response = self.client.chat.completions.create(
            model=self.model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=1000,
        )

        return response.choices[0].message.content

    def _generate_anthropic(self, prompt: str) -> str:
        """Generate using Anthropic Claude."""
        response = self.client.messages.create(
            model=self.model_id,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
        )

        return response.content[0].text

    def _generate_ollama(self, prompt: str) -> str:
        """Generate using Ollama (local)."""
        import httpx

        try:
            response = httpx.post(
                f"{self.api_base}/api/generate",
                json={
                    "model": self.model_id,
                    "prompt": prompt,
                    "temperature": self.temperature,
                    "stream": False,
                },
            )

            return response.json()["response"]
        except Exception as e:
            raise RuntimeError(f"Ollama API error: {e}")

    def _extract_sources(self, context: List[str]) -> List[Dict[str, str]]:
        """Extract source information."""
        return [
            {"index": i + 1, "content": doc[:100] + "..." if len(doc) > 100 else doc}
            for i, doc in enumerate(context)
        ]


class RAGPipeline:
    """
    Complete RAG pipeline: retrieval + generation.
    """

    def __init__(
        self,
        vector_store,
        generator: Optional[RAGGenerator] = None,
    ):
        """
        Initialize RAG pipeline.

        Args:
            vector_store: VectorStore instance
            generator: RAGGenerator instance
        """
        self.vector_store = vector_store
        self.generator = generator or RAGGenerator()

    def query(
        self,
        query: str,
        k: int = 5,
        language: str = "en",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute full RAG query.

        Args:
            query: User query
            k: Number of documents to retrieve
            language: 'en' or 'ar'
            **kwargs: Additional arguments for generator

        Returns:
            Dict with answer, sources, metadata
        """
        # Retrieve
        print(f"Retrieving documents for: {query}")
        search_results = self.vector_store.search(query, k=k)

        context = [
            doc[2].get("title", f"Document {i}") for i, doc in enumerate(search_results)
        ]

        # Generate
        print("Generating answer...")
        answer = self.generator.generate(
            query=query,
            context=context,
            language=language,
            **kwargs,
        )

        # Add retrieval info
        answer["retrieval"] = {
            "documents_retrieved": len(search_results),
            "top_match_score": search_results[0][1] if search_results else 0,
            "matches": [
                {
                    "rank": i + 1,
                    "score": score,
                    "title": metadata.get("title"),
                    "source": metadata.get("source"),
                }
                for i, (doc_id, score, metadata) in enumerate(search_results)
            ],
        }

        return answer
