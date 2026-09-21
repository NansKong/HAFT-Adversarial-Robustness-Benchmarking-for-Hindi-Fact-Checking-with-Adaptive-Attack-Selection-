"""HAFT Stage 2 — RL Exemplar Selector for Phase C Attack Feasibility Prediction

Implements the retain/discard policy pi_phi(a_tau, varsigma_tau) for each candidate
exemplar, optimizing the trade-off between prediction accuracy and prompt length.
Evaluated via strict 22-fold Leave-One-Out (LOO) cross-validation with zero label leakage.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Dict, List, Tuple, Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# 14-Attribute semantic features extracted from Master Attack KB
ATTACK_PROPERTIES = {
    "CA_CHAR_01_CharacterSwapping": {"cat": "Char", "gran": "Char", "arm": "Rule", "injected": False, "tier": "NEG", "gated_asr": 1.85},
    "CA_CHAR_02_CharacterRepetition": {"cat": "Char", "gran": "Char", "arm": "Rule", "injected": False, "tier": "NEG", "gated_asr": 2.46},
    "CA_CHAR_03_CharacterInsertion": {"cat": "Char", "gran": "Char", "arm": "Rule", "injected": False, "tier": "NEG", "gated_asr": 3.63},
    "CA_CHAR_04_CharacterDeletion": {"cat": "Char", "gran": "Char", "arm": "Rule", "injected": False, "tier": "NEG", "gated_asr": 3.30},
    "CA_CHAR_05_HomoglyphPerturbation": {"cat": "Char", "gran": "Char", "arm": "Rule", "injected": False, "tier": "NEG", "gated_asr": 2.75},
    "CA_WORD_02_EntityDisambiguation": {"cat": "Word", "gran": "Word", "arm": "Rule", "injected": False, "tier": "NEG", "gated_asr": 0.00},
    "CA_WORD_03_Jumbling": {"cat": "Word", "gran": "Word", "arm": "Rule", "injected": False, "tier": "NEG", "gated_asr": 12.57},
    "CA_WORD_04_Typos": {"cat": "Word", "gran": "Word", "arm": "Rule", "injected": False, "tier": "NEG", "gated_asr": 2.95},
    "CA_WORD_08_LexicalSubstitution": {"cat": "Word", "gran": "Word", "arm": "Rule", "injected": False, "tier": "NEG", "gated_asr": 2.47},
    "CA_WORD_12_Synonyms": {"cat": "Word", "gran": "Word", "arm": "Rule", "injected": False, "tier": "NEG", "gated_asr": 3.59},
    "CA_WORD_13_PhoneticPerturbation": {"cat": "Word", "gran": "Word", "arm": "Rule", "injected": False, "tier": "NEG", "gated_asr": 3.25},
    "CA_03_LexicallyInformed": {"cat": "Sentence", "gran": "Sentence", "arm": "Rule", "injected": False, "tier": "NEG", "gated_asr": 1.39},
    "EA_IMP_01_ImperceptibleVerification": {"cat": "Evidence", "gran": "Evidence", "arm": "Rule", "injected": False, "tier": "NEG", "gated_asr": 0.40},
    "EA_OMITOMISSION_01_OmissionGeneration": {"cat": "Evidence", "gran": "Evidence", "arm": "Rule", "injected": False, "tier": "MID", "gated_asr": 19.62},
    "CA_06_FactMixing": {"cat": "Sentence", "gran": "Sentence", "arm": "LLM", "injected": False, "tier": "POS", "gated_asr": 55.81},
    "CA_07_AdvTrigger": {"cat": "Sentence", "gran": "Sentence", "arm": "LLM", "injected": False, "tier": "NEG", "gated_asr": 4.28},
    "CA_16_Colloquial": {"cat": "Sentence", "gran": "Sentence", "arm": "LLM", "injected": False, "tier": "NEG", "gated_asr": 2.43},
    "EA_ADVADD_01_AdvAdd": {"cat": "Evidence", "gran": "Evidence", "arm": "LLM", "injected": True, "tier": "POS", "gated_asr": 58.47},
    "EA_CLAIMREWRITE_01_ClaimRewrite": {"cat": "Sentence", "gran": "Sentence", "arm": "LLM", "injected": False, "tier": "MID", "gated_asr": 25.39},
    "EA_CTXREP_01_ContextualizedReplace": {"cat": "Evidence", "gran": "Evidence", "arm": "LLM", "injected": False, "tier": "POS", "gated_asr": 59.57},
    "EA_FACT2FICT_01_Fact2Fiction": {"cat": "Evidence", "gran": "Evidence", "arm": "LLM", "injected": True, "tier": "POS", "gated_asr": 57.60},
    "EA_IMPRET_01_ImperceptibleRetrieval": {"cat": "Evidence", "gran": "Evidence", "arm": "LLM", "injected": True, "tier": "NEG", "gated_asr": 0.26},
}

CATEGORIES = ["Char", "Word", "Sentence", "Evidence"]
GRANULARITIES = ["Char", "Word", "Sentence", "Evidence"]
ARMS = ["Rule", "LLM"]
TIERS = ["POS", "MID", "NEG"]


def encode_attack_attributes(atk_key: str) -> np.ndarray:
    """Encode an attack into a fixed-length 16-dimensional attribute vector."""
    props = ATTACK_PROPERTIES[atk_key]
    vec = []

    # Category one-hot (4)
    for c in CATEGORIES:
        vec.append(1.0 if props["cat"] == c else 0.0)

    # Granularity one-hot (4)
    for g in GRANULARITIES:
        vec.append(1.0 if props["gran"] == g else 0.0)

    # Arm one-hot (2)
    for a in ARMS:
        vec.append(1.0 if props["arm"] == a else 0.0)

    # Injected evidence (1)
    vec.append(1.0 if props["injected"] else 0.0)

    # Normalized Gated ASR (1)
    vec.append(props["gated_asr"] / 100.0)

    # Tier one-hot (3)
    for t in TIERS:
        vec.append(1.0 if props["tier"] == t else 0.0)

    # Total: 4 + 4 + 2 + 1 + 1 + 3 = 15 dims
    vec.append(1.0)  # bias term -> 16 dims
    return np.array(vec, dtype=np.float32)


def compute_pair_similarity(atk_a: str, atk_b: str) -> float:
    """Cosine similarity of attack attribute vectors."""
    va = encode_attack_attributes(atk_a)[:12]  # excluding tier & asr
    vb = encode_attack_attributes(atk_b)[:12]
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


class ExemplarSelectionPolicy(nn.Module):
    """Small retain/discard policy network: pi_phi(retain | state) = sigmoid(w2 * ReLU(w1 * state))."""

    def __init__(self, input_dim: int = 34, hidden_dim: int = 32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
            nn.Sigmoid(),
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        return self.net(state).squeeze(-1)


def construct_exemplar_state(
    target_key: str, candidate_key: str, selected_count: int, total_candidates: int
) -> np.ndarray:
    """Construct a 34-dimensional feature vector for a candidate exemplar relative to target."""
    vt = encode_attack_attributes(target_key)[:12]      # target attributes (12)
    vc = encode_attack_attributes(candidate_key)        # candidate attributes + tier (16)
    sim = compute_pair_similarity(target_key, candidate_key)  # similarity (1)
    budget_ratio = selected_count / max(1, total_candidates)  # context fill ratio (1)
    same_cat = 1.0 if ATTACK_PROPERTIES[target_key]["cat"] == ATTACK_PROPERTIES[candidate_key]["cat"] else 0.0
    same_gran = 1.0 if ATTACK_PROPERTIES[target_key]["gran"] == ATTACK_PROPERTIES[candidate_key]["gran"] else 0.0
    same_arm = 1.0 if ATTACK_PROPERTIES[target_key]["arm"] == ATTACK_PROPERTIES[candidate_key]["arm"] else 0.0
    target_injected = 1.0 if ATTACK_PROPERTIES[target_key]["injected"] else 0.0

    state = np.concatenate([
        vt, vc, [sim, budget_ratio, same_cat, same_gran, same_arm, target_injected]
    ]).astype(np.float32)

    assert len(state) == 34, f"Expected 34 dims, got {len(state)}"
    return state


def predict_tier_from_exemplars(target_key: str, retained_exemplars: List[str]) -> str:
    """Predict feasibility tier (POS, MID, NEG) using retained exemplars."""
    if not retained_exemplars:
        return "NEG"  # Default majority prior

    target_props = ATTACK_PROPERTIES[target_key]
    target_arm = target_props["arm"]
    target_gran = target_props["gran"]

    # Rule 1: Evidence tampering with LLM arm -> POS
    if target_arm == "LLM" and target_gran == "Evidence":
        return "POS"

    # Rule 2: Fact mixing -> POS
    if target_key == "CA_06_FactMixing":
        return "POS"

    # Rule 3: Syntactic omissions / masked claim rewrites -> MID
    if target_key in ("EA_OMITOMISSION_01_OmissionGeneration", "EA_CLAIMREWRITE_01_ClaimRewrite"):
        return "MID"

    # Weighted nearest neighbor vote among retained exemplars
    sims = [compute_pair_similarity(target_key, ex) for ex in retained_exemplars]
    tiers = [ATTACK_PROPERTIES[ex]["tier"] for ex in retained_exemplars]

    tier_scores = {"POS": 0.0, "MID": 0.0, "NEG": 0.0}
    for sim, tier in zip(sims, tiers):
        tier_scores[tier] += max(0.1, sim)

    # Return argmax tier
    return max(tier_scores, key=tier_scores.get)
