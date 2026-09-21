"""Compute and cache 768-dimensional IndicBERT claim embeddings for all 1,120 benchmark claims.
Uses ai4bharat/IndicBERTv2-MLM-only (or fallback to google/muril-base-cased).
"""

import csv
import os
import sys
import torch
from transformers import AutoTokenizer, AutoModel

MODEL_NAME = "ai4bharat/IndicBERTv2-MLM-only"
OUTPUT_PATH = "e:/Attack/Attack/data/claim_embeddings_indicbert_1120.pt"
DATASET_PATH = "e:/Attack/Attack/sampled_dataset_1120.csv"


def mean_pooling(model_output, attention_mask):
    """Mean pooling over token embeddings weighted by attention mask."""
    token_embeddings = model_output[0]  # First element contains hidden states
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
    sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    return sum_embeddings / sum_mask


def main():
    print(f"Loading claims from {DATASET_PATH}...")
    claims = []
    with open(DATASET_PATH, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            claim_text = (row.get("claim") or row.get("claim_text") or "").strip()
            claims.append(claim_text)

    print(f"Total claims to embed: {len(claims)}")
    assert len(claims) == 1120, f"Expected 1,120 claims, found {len(claims)}"

    print(f"Loading tokenizer and model: {MODEL_NAME}...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModel.from_pretrained(MODEL_NAME)
    except Exception as e:
        print(f"IndicBERT failed to load ({e}), falling back to google/muril-base-cased...")
        fallback_model = "google/muril-base-cased"
        tokenizer = AutoTokenizer.from_pretrained(fallback_model)
        model = AutoModel.from_pretrained(fallback_model)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    model.eval()

    batch_size = 32
    all_embeddings = []

    print("Computing embeddings in batches...")
    with torch.no_grad():
        for i in range(0, len(claims), batch_size):
            batch_texts = claims[i : i + batch_size]
            encoded = tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=128,
                return_tensors="pt"
            ).to(device)

            outputs = model(**encoded)
            pooled = mean_pooling(outputs, encoded["attention_mask"])
            all_embeddings.append(pooled.cpu())

            if (i // batch_size + 1) % 5 == 0 or (i + batch_size >= len(claims)):
                print(f"  Processed {min(i + batch_size, len(claims))} / {len(claims)} claims")

    embeddings = torch.cat(all_embeddings, dim=0)
    print(f"Computed embeddings shape: {embeddings.shape}")
    assert embeddings.shape == (1120, 768), f"Expected shape (1120, 768), got {embeddings.shape}"

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    torch.save(embeddings, OUTPUT_PATH)
    print(f"Saved claim embeddings to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
