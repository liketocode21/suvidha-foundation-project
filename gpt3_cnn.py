# -*- coding: utf-8 -*-
"""GPT3_CNN.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1rGCSNCothWsVR-YRmgcNE0EuxtpsTqws
"""

import openai

# Set your OpenAI API key
openai.api_key = "86ce2406-4bc4-49d6-8907-e5f73f2208b4"

from datasets import load_dataset

# Load the CNN/DailyMail dataset
dataset = load_dataset("cnn_dailymail", "3.0.0")

# Process the data into prompts and expected outputs
def preprocess_data(example):
    return {
        "prompt": f"Summarize the following article:\n\n{example['article']}",
        "target": example['highlights']
    }

# Apply preprocessing to the dataset
processed_dataset = dataset.map(preprocess_data, batched=True)

def gpt3_summarize(prompt, engine="text-davinci-003"):
    response = openai.Completion.create(
        engine=engine,
        prompt=prompt,
        max_tokens=150,  # Adjust based on the desired summary length
        temperature=0.7,
        top_p=1,
        n=1,
        stop=["\n"]
    )
    return response.choices[0].text.strip()

# Generate summaries for a subset of the test set
generated_summaries = []
for example in processed_dataset['test'].select(range(10)):  # Adjust the range to control the number of examples
    prompt = example['prompt']
    summary = gpt3_summarize(prompt, engine="text-davinci-003")
    generated_summaries.append({
        "prompt": prompt,
        "generated_summary": summary,
        "reference_summary": example["target"]
    })

from rouge_score import rouge_scorer

# Initialize ROUGE scorer
scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)

# Compute ROUGE scores
rouge_scores = {"rouge1": [], "rouge2": [], "rougeL": []}

for summary_pair in generated_summaries:
    scores = scorer.score(summary_pair["reference_summary"], summary_pair["generated_summary"])
    for key in rouge_scores.keys():
        rouge_scores[key].append(scores[key].fmeasure)

# Calculate average ROUGE scores
avg_rouge_scores = {key: sum(values)/len(values) for key, values in rouge_scores.items()}
print("Average ROUGE Scores:", avg_rouge_scores)