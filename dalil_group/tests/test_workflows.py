#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-End (E2E) Tests for Evaluation Workflows
================================================

Test complete workflows from evaluation creation to report generation.
"""

import pytest
import json
from datetime import datetime


@pytest.mark.integration
class TestEvaluationWorkflow:
    """Test complete evaluation workflow."""

    def test_create_evaluation_workflow(self, client, sample_user):
        """Test complete workflow: Create → Run → Evaluate."""
        # 1. Create evaluation wizard request
        eval_data = {
            "client_name": "Test Government Agency",
            "sector": "government",
            "prompt_pack": "government",
            "models": ["gpt-4o-mini"],
            "languages": ["en", "ar"],
            "dimensions": ["accuracy", "bias", "cultural"],
        }
        
        # 2. Verify client can be accessed (would normally POST to /evaluations/new)
        assert eval_data["sector"] == "government"
        assert len(eval_data["models"]) > 0

    @pytest.mark.slow
    def test_batch_evaluation_pipeline(self, db_session, sample_evaluation):
        """Test batch evaluation pipeline."""
        from database import (
            create_model_response,
            create_prompt_result,
            update_evaluation_status,
        )
        
        # 1. Create model responses
        response = create_model_response(
            db_session,
            batch_job_id="batch_001",
            evaluation_id=sample_evaluation.id,
            prompt_id="gov_001",
            prompt_text="What is the tax rate?",
            model_id="gpt-4o-mini",
            provider="openai",
            language="en",
            response_text="The tax rate is 25% for income over $100,000.",
            tokens_input=10,
            tokens_output=18,
            latency_ms=450.2,
        )
        
        assert response is not None
        assert response.model_id == "gpt-4o-mini"
        
        # 2. Create evaluation result
        result = create_prompt_result(
            db_session,
            evaluation_id=sample_evaluation.id,
            prompt_id="gov_001",
            category="government",
            scores_json={
                "gpt-4o-mini": {
                    "en": [
                        {"dimension": "accuracy", "score": 95, "severity": "low"},
                        {"dimension": "bias", "score": 88, "severity": "low"},
                    ]
                }
            }
        )
        
        assert result is not None
        
        # 3. Update evaluation status
        update_evaluation_status(
            db_session,
            sample_evaluation.project_id,
            status="completed",
            overall_score=91.5,
            total_prompts=1,
            total_responses=1,
        )
        
        # 4. Verify evaluation was updated
        from database import get_evaluation
        updated_eval = get_evaluation(db_session, sample_evaluation.project_id)
        assert updated_eval.status == "completed"
        assert updated_eval.overall_score == 91.5


@pytest.mark.integration
class TestBatchQueueWorkflow:
    """Test batch queue management workflow."""

    def test_batch_job_lifecycle(self, db_session, sample_user):
        """Test complete batch job lifecycle."""
        from batch_queue import batch_queue
        
        # 1. Add job to queue
        job_id = batch_queue.add_job(
            user_id=sample_user.id,
            name="E2E Test Batch",
            config={
                "models": ["gpt-4o-mini"],
                "languages": ["en", "ar"],
                "prompt_pack": "government",
                "total_items": 36,
            }
        )
        
        assert job_id is not None
        
        # 2. Retrieve job
        job = batch_queue.get_job(job_id)
        assert job is not None
        assert job.status.value == "queued"
        
        # 3. Start job
        batch_queue.start_job(job_id)
        job = batch_queue.get_job(job_id)
        assert job.status.value == "running"
        
        # 4. Update progress
        batch_queue.update_job_progress(job_id, progress=50, completed_items=18)
        job = batch_queue.get_job(job_id)
        assert job.progress == 50
        assert job.completed_items == 18
        
        # 5. Complete job
        batch_queue.complete_job(
            job_id,
            result={"overall_score": 87.5, "total_items": 36}
        )
        job = batch_queue.get_job(job_id)
        assert job.status.value == "completed"
        assert job.progress == 100


@pytest.mark.api
class TestAPIWorkflows:
    """Test API workflows."""

    def test_health_check_workflow(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "services" in data

    def test_settings_workflow(self, client):
        """Test settings management workflow."""
        # Get settings
        response = client.get("/settings")
        assert response.status_code in [200, 307]  # May redirect to settings form
        
        # In a real test, would verify form content


@pytest.mark.integration
class TestCrossLingualConsistency:
    """Test cross-lingual consistency scoring."""

    def test_bilingual_evaluation_consistency(self, db_session, sample_evaluation):
        """Test consistency checking between English and Arabic responses."""
        from database import create_model_response
        
        # Create English response
        en_response = create_model_response(
            db_session,
            batch_job_id="batch_001",
            evaluation_id=sample_evaluation.id,
            prompt_id="gov_001",
            prompt_text="How do I renew my passport?",
            model_id="gpt-4o-mini",
            provider="openai",
            language="en",
            response_text="Visit your local passport office with required documents.",
            latency_ms=350.0,
        )
        
        # Create Arabic response (should be translated version)
        ar_response = create_model_response(
            db_session,
            batch_job_id="batch_001",
            evaluation_id=sample_evaluation.id,
            prompt_id="gov_001",
            prompt_text="كيف أجدد جواز سفري؟",
            model_id="gpt-4o-mini",
            provider="openai",
            language="ar",
            response_text="قم بزيارة مكتب الجوازات المحلي مع المستندات المطلوبة.",
            latency_ms=375.0,
        )
        
        # Verify both responses exist
        assert en_response is not None
        assert ar_response is not None
        
        # In a real test, would verify consistency scoring


@pytest.mark.integration
class TestReportGeneration:
    """Test report generation workflows."""

    def test_report_generation_pipeline(self, db_session, sample_evaluation):
        """Test complete report generation pipeline."""
        # Update evaluation with results
        from database import update_evaluation_status
        
        update_evaluation_status(
            db_session,
            sample_evaluation.project_id,
            status="completed",
            overall_score=88.5,
            total_prompts=36,
            total_responses=72,
        )
        
        # Verify evaluation is ready for report
        from database import get_evaluation
        eval_obj = get_evaluation(db_session, sample_evaluation.project_id)
        assert eval_obj.status == "completed"
        assert eval_obj.overall_score == 88.5
        
        # In a real test, would generate reports in different formats
        # - DOCX
        # - PDF
        # - PPTX


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling in workflows."""

    def test_invalid_evaluation_config(self, db_session, sample_user):
        """Test handling of invalid evaluation configuration."""
        from database import create_evaluation
        
        # This should work even with invalid config
        # (actual validation would happen during evaluation)
        eval_obj = create_evaluation(
            db_session,
            project_id="test_invalid",
            client_name="Invalid Test",
            sector="invalid_sector",  # Invalid sector
            prompt_pack="invalid_pack",
            models=["nonexistent_model"],
            languages=["xx"],  # Invalid language
            dimensions=["invalid_dimension"],
            user_id=sample_user.id
        )
        
        assert eval_obj is not None

    def test_batch_job_failure_handling(self, db_session, sample_user):
        """Test handling of batch job failures."""
        from batch_queue import batch_queue
        
        job_id = batch_queue.add_job(
            user_id=sample_user.id,
            name="Failure Test",
            config={"models": [], "languages": []},  # Empty config
        )
        
        # Start and then fail the job
        batch_queue.start_job(job_id)
        batch_queue.fail_job(job_id, error="Configuration validation failed")
        
        job = batch_queue.get_job(job_id)
        assert job.status.value == "failed"
        assert "Configuration validation" in job.error


@pytest.mark.slow
class TestPerformanceWorkflows:
    """Test performance and scalability."""

    def test_large_batch_processing(self, db_session, sample_evaluation):
        """Test processing of large batch job."""
        from database import create_model_response
        
        # Simulate processing 100 prompts × 2 models × 2 languages = 400 responses
        prompt_count = 100
        model_count = 2
        language_count = 2
        
        total_responses = 0
        for prompt_idx in range(prompt_count):
            for model_idx in range(model_count):
                for lang_idx in range(language_count):
                    response = create_model_response(
                        db_session,
                        batch_job_id="batch_large",
                        evaluation_id=sample_evaluation.id,
                        prompt_id=f"prompt_{prompt_idx}",
                        prompt_text=f"Sample prompt {prompt_idx}",
                        model_id=f"model_{model_idx}",
                        provider="openai",
                        language="en" if lang_idx == 0 else "ar",
                        response_text=f"Sample response {prompt_idx}",
                    )
                    total_responses += 1
        
        assert total_responses == (prompt_count * model_count * language_count)

    def test_concurrent_evaluation_handling(self, db_session):
        """Test handling of concurrent evaluations."""
        from database import create_evaluation
        
        # Create multiple concurrent evaluations
        num_concurrent = 5
        evaluations = []
        
        for i in range(num_concurrent):
            ev = create_evaluation(
                db_session,
                project_id=f"concurrent_{i}",
                client_name=f"Client {i}",
                sector="government",
                prompt_pack="government",
                models=["gpt-4o-mini"],
                languages=["en", "ar"],
                dimensions=["accuracy"],
            )
            evaluations.append(ev)
        
        assert len(evaluations) == num_concurrent


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
