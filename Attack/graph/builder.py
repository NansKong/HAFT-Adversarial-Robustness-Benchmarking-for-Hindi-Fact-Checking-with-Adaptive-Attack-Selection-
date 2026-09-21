"""HAFT Stage 2 — Attack-Claim Knowledge Graph Construction

Constructs the bipartite graph:
  - 1,120 claim nodes
  - 22 attack nodes
  Total: 1,142 nodes
  Edges: 24,640 measured edges from Phase A ground truth + attack-attack similarity edges.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from typing import Dict, List, Tuple, Any

import numpy as np
import torch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from replay_env import ATTACK_KEYS_22
from exemplar.selector import ATTACK_PROPERTIES, encode_attack_attributes, compute_pair_similarity

NUM_CLAIMS = 1120
NUM_ATTACKS = 22
TOTAL_NODES = NUM_CLAIMS + NUM_ATTACKS

DOMAINS = [
    "Crime_public_safety",
    "Celebrity_News",
    "Disaster_BreakingNews",
    "Government_Schemes",
    "Health_Medicine",
    "Politics_and_Election",
]
LABELS = ["SUP", "REF", "NEI"]


class AttackClaimGraph:
    """In-memory bipartite Knowledge Graph representing claims, attacks, and measured Phase A outcomes."""

    def __init__(self, base_dir: str = BASE_DIR, device: str = "cpu"):
        self.base_dir = os.path.abspath(base_dir)
        self.device = torch.device(device)

        self.num_claims = NUM_CLAIMS
        self.num_attacks = NUM_ATTACKS
        self.num_nodes = TOTAL_NODES

        # Load claim embeddings (768 dims)
        emb_path = os.path.join(self.base_dir, "data", "claim_embeddings_indicbert_1120.pt")
        if not os.path.exists(emb_path):
            raise FileNotFoundError(f"Claim embeddings missing at {emb_path}")
        self.claim_embeddings = torch.load(emb_path, weights_only=True)

        # Load claims metadata
        self.claims_meta: List[Dict[str, Any]] = []
        self._load_claims()

        # Build node features
        # Common embedding dimension: 64
        self.claim_features, self.attack_features = self._build_node_features()

        # Load measured edges
        self.edge_index, self.edge_labels, self.edge_attrs = self._build_edges()

    def _load_claims(self) -> None:
        dataset_path = os.path.join(self.base_dir, "sampled_dataset_1120.csv")
        with open(dataset_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                self.claims_meta.append({
                    "row_id": i,
                    "claim": (row.get("claim") or row.get("claim_text") or "").strip(),
                    "evidence": (row.get("evidence") or row.get("evidence_text") or "").strip(),
                    "label": (row.get("label") or row.get("gold_label") or "").upper(),
                    "domain": row.get("domain", ""),
                })

    def _build_node_features(self) -> Tuple[torch.Tensor, torch.Tensor]:
        """Construct raw feature matrices for claims and attacks."""
        # 1. Claims: [768-dim IndicBERT, 3-dim label, 6-dim domain] -> 777 dims
        claim_feats = []
        for i in range(self.num_claims):
            meta = self.claims_meta[i]
            emb = self.claim_embeddings[i].numpy()

            # Label one-hot (3)
            lbl_vec = [1.0 if meta["label"] == l else 0.0 for l in LABELS]

            # Domain one-hot (6)
            dom_vec = [1.0 if meta["domain"] == d else 0.0 for d in DOMAINS]

            feat = np.concatenate([emb, lbl_vec, dom_vec]).astype(np.float32)
            claim_feats.append(feat)

        claim_feats_t = torch.tensor(np.array(claim_feats), dtype=torch.float32)

        # 2. Attacks: 16-dim semantic attributes from Master KB
        atk_feats = []
        for atk_key in ATTACK_KEYS_22:
            atk_feats.append(encode_attack_attributes(atk_key))

        atk_feats_t = torch.tensor(np.array(atk_feats), dtype=torch.float32)

        return claim_feats_t, atk_feats_t

    def _build_edges(self) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Load all 24,640 measured attack-claim edges from results/full_run/."""
        edges_src = []
        edges_dst = []
        labels = []
        attrs = []

        results_dir = os.path.join(self.base_dir, "results", "full_run")

        for atk_idx, atk_key in enumerate(ATTACK_KEYS_22):
            csv_path = os.path.join(results_dir, f"{atk_key}_results.csv")
            attack_node_id = self.num_claims + atk_idx

            with open(csv_path, encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    claim_node_id = int(row["row_id"])
                    raw_flip = str(row.get("flipped", "")).lower() == "true"
                    excluded = str(row.get("excluded", "")).lower() == "true"
                    reason = row.get("reason", "")
                    gated_success = raw_flip and not excluded and (reason != "baseline_failure")

                    # Bidirectional edge: Claim <-> Attack
                    edges_src.extend([claim_node_id, attack_node_id])
                    edges_dst.extend([attack_node_id, claim_node_id])

                    lbl = 1.0 if gated_success else 0.0
                    labels.extend([lbl, lbl])

                    # Edge attributes: [raw_flip, judge_pass, baseline_failure]
                    judge_pass = 1.0 if not excluded else 0.0
                    base_fail = 1.0 if reason == "baseline_failure" else 0.0
                    edge_feat = [1.0 if raw_flip else 0.0, judge_pass, base_fail]
                    attrs.extend([edge_feat, edge_feat])

        # Add Attack-Attack similarity edges (if cosine similarity >= 0.65)
        for i in range(self.num_attacks):
            for j in range(i + 1, self.num_attacks):
                atk_i = ATTACK_KEYS_22[i]
                atk_j = ATTACK_KEYS_22[j]
                sim = compute_pair_similarity(atk_i, atk_j)
                if sim >= 0.65:
                    node_i = self.num_claims + i
                    node_j = self.num_claims + j
                    edges_src.extend([node_i, node_j])
                    edges_dst.extend([node_j, node_i])
                    labels.extend([0.0, 0.0])  # Non-target edge
                    attrs.extend([[0.0, sim, 0.0], [0.0, sim, 0.0]])

        edge_index = torch.tensor([edges_src, edges_dst], dtype=torch.long)
        edge_labels = torch.tensor(labels, dtype=torch.float32)
        edge_attrs = torch.tensor(np.array(attrs), dtype=torch.float32)

        return edge_index, edge_labels, edge_attrs
