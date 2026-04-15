#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local Fine-tuning for Open-Source Models
==========================================

Fine-tune open-source models (Llama, Mistral) using LoRA/QLoRA.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, List


class Finetuner:
    """
    Fine-tune open-source models using LoRA/QLoRA.

    Supports:
    - Llama 2/3
    - Mistral
    - Other HuggingFace models

    Features:
    - Memory-efficient QLoRA training
    - Multi-GPU support
    - Merging LoRA weights into base model
    """

    def __init__(
        self,
        model_id: str,
        output_dir: str = "./finetuned_models",
        use_qlora: bool = True,
    ):
        """
        Initialize local fine-tuner.

        Args:
            model_id: HuggingFace model ID (e.g., 'meta-llama/Llama-2-7b')
            output_dir: Directory to save fine-tuned models
            use_qlora: Use QLoRA (memory efficient) vs LoRA
        """
        self.model_id = model_id
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.use_qlora = use_qlora

        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """Check that required packages are installed."""
        required = ["transformers", "peft", "datasets"]

        if self.use_qlora:
            required.extend(["bitsandbytes", "accelerate"])

        missing = []
        for pkg in required:
            try:
                __import__(pkg)
            except ImportError:
                missing.append(pkg)

        if missing:
            cmd = f"pip install {' '.join(missing)}"
            print(f"⚠️  Missing dependencies: {cmd}")
            raise ImportError(f"Missing packages: {missing}")

    def prepare_training_data(
        self,
        dataset_file: str,
        test_size: float = 0.1,
    ) -> tuple:
        """
        Prepare training data from JSONL file.

        Args:
            dataset_file: Path to JSONL training file
            test_size: Fraction for validation set

        Returns:
            (train_dataset, eval_dataset)
        """
        from datasets import Dataset, load_dataset

        print(f"Loading dataset from {dataset_file}")

        # Load JSONL file
        data = []
        with open(dataset_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))

        # Convert to HuggingFace format
        examples = []
        for item in data:
            messages = item.get("messages", [])

            # Format as chat template
            prompt = ""
            completion = ""

            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")

                if role == "user":
                    prompt = content
                else:
                    completion = content

            if prompt and completion:
                examples.append(
                    {
                        "text": f"USER: {prompt}\nASSISTANT: {completion}",
                        "prompt": prompt,
                        "completion": completion,
                    }
                )

        # Create dataset
        dataset = Dataset.from_dict(
            {
                "text": [e["text"] for e in examples],
            }
        )

        # Split
        split_dataset = dataset.train_test_split(test_size=test_size)

        print(f"✅ Training data prepared:")
        print(f"   Train: {len(split_dataset['train'])} examples")
        print(f"   Eval: {len(split_dataset['test'])} examples")

        return split_dataset["train"], split_dataset["test"]

    def finetune(
        self,
        dataset_file: str,
        epochs: int = 3,
        batch_size: int = 4,
        learning_rate: float = 2e-4,
        warmup_steps: int = 100,
        num_gpus: int = 1,
    ) -> Dict[str, Any]:
        """
        Fine-tune the model.

        Args:
            dataset_file: Path to training data (JSONL)
            epochs: Number of training epochs
            batch_size: Batch size (per GPU)
            learning_rate: Learning rate
            warmup_steps: Warmup steps
            num_gpus: Number of GPUs to use

        Returns:
            Training results
        """
        import torch
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            TrainingArguments,
            Trainer,
        )
        from peft import LoraConfig, get_peft_model

        print(f"Starting fine-tuning of {self.model_id}")
        print(f"  QLoRA: {self.use_qlora}")
        print(f"  Epochs: {epochs}")
        print(f"  Batch size: {batch_size} x {num_gpus} GPU(s)")

        # Prepare data
        train_dataset, eval_dataset = self.prepare_training_data(dataset_file)

        # Load model
        print("\nLoading model...")

        if self.use_qlora:
            from transformers import BitsAndBytesConfig

            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
            )

            model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                quantization_config=bnb_config,
                device_map="auto",
                trust_remote_code=True,
            )
        else:
            model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True,
            )

        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(self.model_id, trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        # Apply LoRA
        print("Configuring LoRA...")
        lora_config = LoraConfig(
            r=16,
            lora_alpha=32,
            target_modules=["q_proj", "v_proj"],
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
        )

        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()

        # Training arguments
        output_dir = str(self.output_dir / f"{self.model_id.split('/')[-1]}_lora")

        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            learning_rate=learning_rate,
            warmup_steps=warmup_steps,
            weight_decay=0.01,
            logging_steps=10,
            evaluation_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            optim="paged_adamw_32bit",
            gradient_checkpointing=True,
        )

        # Trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            tokenizer=tokenizer,
        )

        # Train
        print("\nStarting training...")
        trainer.train()

        print(f"✅ Training completed")
        print(f"   Output: {output_dir}")

        return {
            "model_id": self.model_id,
            "output_dir": output_dir,
            "epochs": epochs,
            "batch_size": batch_size,
        }

    def merge_lora_weights(
        self,
        lora_dir: str,
        output_dir: Optional[str] = None,
    ) -> str:
        """
        Merge LoRA weights into base model.

        Args:
            lora_dir: Directory with LoRA weights
            output_dir: Output directory for merged model

        Returns:
            Path to merged model
        """
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel

        if output_dir is None:
            output_dir = str(self.output_dir / f"{self.model_id.split('/')[-1]}_merged")

        print(f"Merging LoRA weights...")
        print(f"  Base model: {self.model_id}")
        print(f"  LoRA dir: {lora_dir}")

        # Load base model
        base_model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16,
            device_map="auto",
        )

        # Load LoRA model
        lora_model = PeftModel.from_pretrained(base_model, lora_dir)

        # Merge
        merged_model = lora_model.merge_and_unload()

        # Save
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        merged_model.save_pretrained(output_dir)

        # Save tokenizer too
        tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        tokenizer.save_pretrained(output_dir)

        print(f"✅ Merged model saved to: {output_dir}")

        return output_dir
