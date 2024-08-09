# -*- coding: utf-8 -*-
"""RoBERTa_XSUM.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1rGCSNCothWsVR-YRmgcNE0EuxtpsTqws
"""

from datasets import load_dataset
from transformers import RobertaTokenizer, RobertaForSequenceClassification, Trainer, TrainingArguments
from rouge_score import rouge_scorer
import torch
import torch.nn as nn

# Load dataset
dataset = load_dataset("xsum")
train_data = dataset["train"]
val_data = dataset["validation"]

# Load RoBERTa tokenizer and model
model_name = "roberta-base"  # Use a suitable model if you have one for sequence-to-sequence tasks
tokenizer = RobertaTokenizer.from_pretrained(model_name)

# Custom model for sequence-to-sequence tasks
class RobertaForSeq2Seq(nn.Module):
    def __init__(self, roberta_model_name, vocab_size):
        super(RobertaForSeq2Seq, self).__init__()
        self.roberta = RobertaForSequenceClassification.from_pretrained(roberta_model_name, num_labels=vocab_size)
        self.fc = nn.Linear(self.roberta.config.hidden_size, vocab_size)

    def forward(self, input_ids, labels=None):
        outputs = self.roberta(input_ids)[0]  # Take the hidden states
        logits = self.fc(outputs)

        if labels is not None:
            loss = nn.CrossEntropyLoss()(logits.view(-1, logits.size(-1)), labels.view(-1))
            return loss, logits
        return logits

# Initialize the custom model
model = RobertaForSeq2Seq(model_name, vocab_size=tokenizer.vocab_size)

# Preprocess data
def preprocess_function(examples):
    inputs = examples["document"]
    targets = examples["summary"]
    model_inputs = tokenizer(inputs, max_length=512, truncation=True, padding="max_length")

    with tokenizer.as_target_tokenizer():
        labels = tokenizer(targets, max_length=150, truncation=True, padding="max_length")

    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

train_data = train_data.map(preprocess_function, batched=True)
val_data = val_data.map(preprocess_function, batched=True)

# Set up training arguments
training_args = TrainingArguments(
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    output_dir="./results",
    num_train_epochs=3,
    evaluation_strategy="epoch",
    logging_dir="./logs",
    logging_steps=10,
    save_steps=10_000,
    eval_steps=10_000,
    warmup_steps=500,
    weight_decay=0.01,
)

# Define Trainer
class RobertaTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False):
        input_ids = inputs.get("input_ids")
        labels = inputs.get("labels")
        loss, logits = model(input_ids, labels=labels)
        return (loss, logits) if return_outputs else loss

trainer = RobertaTrainer(
    model=model,
    args=training_args,
    train_dataset=train_data,
    eval_dataset=val_data,
)

# Train the model
trainer.train()

# Evaluate the model
def compute_rouge(predictions, references):
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    scores = {"rouge1": 0, "rouge2": 0, "rougeL": 0}
    num_predictions = len(predictions)

    for pred, ref in zip(predictions, references):
        score = scorer.score(ref, pred)
        for key in scores:
            scores[key] += score[key].fmeasure

    return {key: value / num_predictions for key, value in scores.items()}

# Get predictions
predictions = trainer.predict(val_data).predictions
decoded_preds = tokenizer.batch_decode(predictions, skip_special_tokens=True)
references = val_data["summary"]

# Compute ROUGE scores
rouge_scores = compute_rouge(decoded_preds, references)
print("ROUGE Scores:", rouge_scores)