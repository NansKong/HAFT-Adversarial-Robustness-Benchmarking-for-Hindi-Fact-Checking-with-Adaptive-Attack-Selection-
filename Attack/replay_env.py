"""HAFT Stage 2 — Offline Replay Environment
Simulates the Attack -> Verify -> Judge pipeline by replaying the frozen Phase A
ground truth benchmark across 1,120 claims and 22 attacks (24,640 evaluations).

Zero API calls are made during RL training and evaluation.
"""

from __future__ import annotations

import csv
import json
import os
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import torch

# Canonical mapping of the 22 evaluated attacks
ATTACK_KEYS_22 = [
    "CA_CHAR_01_CharacterSwapping",
    "CA_CHAR_02_CharacterRepetition",
    "CA_CHAR_03_CharacterInsertion",
    "CA_CHAR_04_CharacterDeletion",
    "CA_CHAR_05_HomoglyphPerturbation",
    "CA_WORD_02_EntityDisambiguation",
    "CA_WORD_03_Jumbling",
    "CA_WORD_04_Typos",
    "CA_WORD_08_LexicalSubstitution",
    "CA_WORD_12_Synonyms",
    "CA_WORD_13_PhoneticPerturbation",
    "CA_03_LexicallyInformed",
    "EA_IMP_01_ImperceptibleVerification",
    "EA_OMITOMISSION_01_OmissionGeneration",
    "CA_06_FactMixing",
    "CA_07_AdvTrigger",
    "CA_16_Colloquial",
    "EA_ADVADD_01_AdvAdd",
    "EA_CLAIMREWRITE_01_ClaimRewrite",
    "EA_CTXREP_01_ContextualizedReplace",
    "EA_FACT2FICT_01_Fact2Fiction",
    "EA_IMPRET_01_ImperceptibleRetrieval",
]

# POS tier attacks identified in Phase A benchmark
POS_TIER_ATTACKS = {
    "EA_CTXREP_01_ContextualizedReplace",
    "EA_ADVADD_01_AdvAdd",
    "EA_FACT2FICT_01_Fact2Fiction",
    "CA_06_FactMixing",
}


class OfflineAttackEnv:
    """Fast, deterministic offline environment for RL attack selection.
    Replays the 24,640 ground-truth outcomes from Phase A.
    """

    def __init__(
        self,
        base_dir: str = "e:/Attack/Attack",
        max_budget_k: int = 5,
        flip_reward: float = 1.0,
        api_cost_penalty: float = 0.05,
        terminal_pos_bonus: float = 0.5,
        claim_embeddings: Optional[torch.Tensor] = None,
        exclude_baseline_failures: bool = True,
    ):
        self.base_dir = os.path.abspath(base_dir)
        self.max_budget_k = max_budget_k
        self.flip_reward = flip_reward
        self.api_cost_penalty = api_cost_penalty
        self.terminal_pos_bonus = terminal_pos_bonus
        self.claim_embeddings = claim_embeddings
        self.exclude_baseline_failures = exclude_baseline_failures

        self.num_attacks = len(ATTACK_KEYS_22)
        self.attack_to_idx = {k: i for i, k in enumerate(ATTACK_KEYS_22)}
        self.idx_to_attack = {i: k for i, k in enumerate(ATTACK_KEYS_22)}

        # Load dataset
        self.claims: List[Dict[str, Any]] = []
        self._load_dataset()

        # Load Phase A ground truth matrices
        # shape: (1120, 22, 3) -> [gated_flip, judge_pass, raw_flip]
        self.outcomes = np.zeros((len(self.claims), self.num_attacks, 3), dtype=np.float32)
        self.is_baseline_failure = np.zeros(len(self.claims), dtype=bool)
        self._load_ground_truth()

        # Filter valid claim indices (832 claims if exclude_baseline_failures else 1120)
        if self.exclude_baseline_failures:
            self.valid_claim_ids = np.where(~self.is_baseline_failure)[0]
        else:
            self.valid_claim_ids = np.arange(len(self.claims))

        # Episode state variables
        self.current_claim_id: int = 0
        self.current_step: int = 0
        self.tried_mask = np.zeros(self.num_attacks, dtype=np.float32)
        self.prev_results = np.zeros((self.num_attacks, 3), dtype=np.float32)
        self.episode_flips: int = 0

    def _load_dataset(self) -> None:
        dataset_path = os.path.join(self.base_dir, "sampled_dataset_1120.csv")
        with open(dataset_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                self.claims.append({
                    "row_id": i,
                    "claim": (row.get("claim") or row.get("claim_text") or "").strip(),
                    "evidence": (row.get("evidence") or row.get("evidence_text") or "").strip(),
                    "label": (row.get("label") or row.get("gold_label") or "").upper(),
                    "domain": row.get("domain", ""),
                })

    def _load_ground_truth(self) -> None:
        results_dir = os.path.join(self.base_dir, "results", "full_run")
        for atk_idx, atk_key in enumerate(ATTACK_KEYS_22):
            csv_path = os.path.join(results_dir, f"{atk_key}_results.csv")
            if not os.path.exists(csv_path):
                raise FileNotFoundError(f"Required benchmark result file missing: {csv_path}")

            with open(csv_path, encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row_id = int(row["row_id"])
                    reason = row.get("reason", "")
                    if reason == "baseline_failure":
                        self.is_baseline_failure[row_id] = True

                    raw_flip = str(row.get("flipped", "")).lower() == "true"
                    excluded = str(row.get("excluded", "")).lower() == "true"
                    try:
                        fluency = float(row.get("fluency") or 0)
                    except ValueError:
                        fluency = 0.0
                    meaning_preserved = str(row.get("meaning_preserved", "")).lower() == "true"

                    judge_pass = (fluency >= 3.0 or meaning_preserved) and not excluded
                    gated_flip = raw_flip and not excluded and (reason != "baseline_failure")

                    self.outcomes[row_id, atk_idx, 0] = 1.0 if gated_flip else 0.0
                    self.outcomes[row_id, atk_idx, 1] = 1.0 if judge_pass else 0.0
                    self.outcomes[row_id, atk_idx, 2] = 1.0 if raw_flip else 0.0

    def get_verdict_one_hot(self, claim_id: int) -> np.ndarray:
        label = self.claims[claim_id]["label"]
        # SUP=[1,0,0], REF=[0,1,0], NEI=[0,0,1]
        v = np.zeros(3, dtype=np.float32)
        if label == "SUP":
            v[0] = 1.0
        elif label == "REF":
            v[1] = 1.0
        elif label == "NEI":
            v[2] = 1.0
        return v

    def get_state(self) -> np.ndarray:
        """Construct the exact 859-dimensional state vector:
        [claim_embedding (768), verdict_one_hot (3), tried_mask (22), prev_results (66)]
        """
        # 1. Claim embedding: 768 dims
        if self.claim_embeddings is not None:
            claim_emb = self.claim_embeddings[self.current_claim_id].numpy()
        else:
            claim_emb = np.zeros(768, dtype=np.float32)

        # 2. Baseline verdict: 3 dims
        verdict_one_hot = self.get_verdict_one_hot(self.current_claim_id)

        # 3. Tried mask: 22 dims
        tried = self.tried_mask.copy()

        # 4. Previous attack results: 66 dims (22 x 3)
        prev = self.prev_results.flatten()

        state = np.concatenate([claim_emb, verdict_one_hot, tried, prev])
        assert state.shape == (859,), f"Expected state dimension 859, got {state.shape}"
        return state

    def reset(self, claim_id: Optional[int] = None) -> np.ndarray:
        """Reset the environment for a new episode."""
        if claim_id is None:
            self.current_claim_id = int(np.random.choice(self.valid_claim_ids))
        else:
            self.current_claim_id = claim_id

        self.current_step = 0
        self.tried_mask.fill(0.0)
        self.prev_results.fill(0.0)
        self.episode_flips = 0

        return self.get_state()

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        """Take an action (select one of the 22 attacks)."""
        assert 0 <= action < self.num_attacks, f"Invalid action {action}"

        # Penalty if agent repeats an attack
        if self.tried_mask[action] == 1.0:
            reward = -0.5
            done = self.current_step >= self.max_budget_k
            return self.get_state(), reward, done, {"repeated": True, "gated_flip": False}

        self.current_step += 1
        self.tried_mask[action] = 1.0

        # Retrieve ground truth outcome
        gated_flip = bool(self.outcomes[self.current_claim_id, action, 0] > 0.5)
        judge_pass = bool(self.outcomes[self.current_claim_id, action, 1] > 0.5)
        raw_flip = bool(self.outcomes[self.current_claim_id, action, 2] > 0.5)

        self.prev_results[action, 0] = 1.0 if gated_flip else 0.0
        self.prev_results[action, 1] = 1.0 if judge_pass else 0.0
        self.prev_results[action, 2] = 1.0 if raw_flip else 0.0

        # Calculate reward
        reward = -self.api_cost_penalty  # -0.05 attempt cost
        atk_key = self.idx_to_attack[action]

        if gated_flip:
            reward += self.flip_reward  # +1.0
            self.episode_flips += 1
            if atk_key in POS_TIER_ATTACKS:
                reward += self.terminal_pos_bonus  # +0.5 POS bonus

        done = self.current_step >= self.max_budget_k

        info = {
            "claim_id": self.current_claim_id,
            "action": action,
            "attack_key": atk_key,
            "gated_flip": gated_flip,
            "judge_pass": judge_pass,
            "raw_flip": raw_flip,
            "step": self.current_step,
            "total_flips": self.episode_flips,
            "is_pos_tier": (atk_key in POS_TIER_ATTACKS),
        }

        return self.get_state(), reward, done, info
