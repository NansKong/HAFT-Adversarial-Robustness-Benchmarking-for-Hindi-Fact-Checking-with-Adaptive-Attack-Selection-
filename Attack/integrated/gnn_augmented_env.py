"""HAFT Stage 2 — GNN-Augmented Offline Environment

FLAW 2 FIX: This module provides GNNAugmentedOfflineEnv, a wrapper around
OfflineAttackEnv that augments the RL state vector from 859 to 987 dimensions
by concatenating GraphSAGE node embeddings:

    s_t^GNN = [s_t^flat (859) || z_claim (64) || z_bar_untried (64)]

Where:
  - z_claim (64): GNN embedding of the current claim node
  - z_bar_untried (64): mean GNN embedding of all untried attack nodes

This enables the RL policy to leverage learned structural features from the
knowledge graph, capturing relational patterns between claims and attacks.

State Dimensions:
  - Flat state:     859 dims (IndicBERT 768 + verdict 3 + tried_mask 22 + prev_results 66)
  - GNN claim:       64 dims (GraphSAGE claim node embedding)
  - GNN untried:     64 dims (mean of untried attack node embeddings)
  - TOTAL:          987 dims

Usage:
    from integrated.gnn_augmented_env import GNNAugmentedOfflineEnv
    env = GNNAugmentedOfflineEnv(base_dir=BASE_DIR, gnn_embeddings=z_tensor, ...)
"""

from __future__ import annotations

import numpy as np
import torch
from typing import Optional, Tuple, Dict, Any

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from replay_env import OfflineAttackEnv
from graph.builder import NUM_CLAIMS, NUM_ATTACKS

GNN_STATE_DIM = 987  # 859 (flat) + 64 (claim GNN) + 64 (untried GNN mean)
GNN_EMB_DIM = 64


class GNNAugmentedOfflineEnv(OfflineAttackEnv):
    """Extends OfflineAttackEnv with GNN node embeddings in the state vector.

    Args:
        gnn_embeddings: Tensor of shape (NUM_CLAIMS + NUM_ATTACKS, 64) — output
                        of the trained GraphSAGE model over all 1,142 nodes.
                        First NUM_CLAIMS rows = claim embeddings,
                        remaining NUM_ATTACKS rows = attack embeddings.
        All other args: passed through to OfflineAttackEnv.
    """

    def __init__(
        self,
        gnn_embeddings: torch.Tensor,
        base_dir: str = BASE_DIR,
        max_budget_k: int = 5,
        flip_reward: float = 1.0,
        api_cost_penalty: float = 0.05,
        terminal_pos_bonus: float = 0.5,
        claim_embeddings: Optional[torch.Tensor] = None,
        exclude_baseline_failures: bool = True,
    ):
        super().__init__(
            base_dir=base_dir,
            max_budget_k=max_budget_k,
            flip_reward=flip_reward,
            api_cost_penalty=api_cost_penalty,
            terminal_pos_bonus=terminal_pos_bonus,
            claim_embeddings=claim_embeddings,
            exclude_baseline_failures=exclude_baseline_failures,
        )

        # Validate shape
        expected_nodes = NUM_CLAIMS + NUM_ATTACKS
        if gnn_embeddings.shape[0] != expected_nodes:
            raise ValueError(
                f"gnn_embeddings must have {expected_nodes} rows (claims + attacks), "
                f"got {gnn_embeddings.shape[0]}"
            )
        if gnn_embeddings.shape[1] != GNN_EMB_DIM:
            raise ValueError(
                f"gnn_embeddings must have {GNN_EMB_DIM} cols (hidden_dim), "
                f"got {gnn_embeddings.shape[1]}"
            )

        # Split into claim and attack embeddings
        self.gnn_claim_embs = gnn_embeddings[:NUM_CLAIMS].detach().cpu().numpy()  # (1120, 64)
        self.gnn_attack_embs = gnn_embeddings[NUM_CLAIMS:].detach().cpu().numpy()  # (22, 64)

    def get_state(self) -> np.ndarray:
        """Construct 987-dimensional augmented state vector.

        [flat_state (859) || z_claim (64) || z_bar_untried (64)]
        """
        # 1. Get base 859-dim flat state from parent
        flat_state = super().get_state()  # (859,)

        # 2. GNN claim embedding for current claim
        z_claim = self.gnn_claim_embs[self.current_claim_id]  # (64,)

        # 3. Mean GNN embedding of untried attacks
        untried_mask = (self.tried_mask < 0.5)  # boolean (22,)
        untried_indices = np.where(untried_mask)[0]

        if len(untried_indices) > 0:
            z_untried_mean = self.gnn_attack_embs[untried_indices].mean(axis=0)  # (64,)
        else:
            # All attacks tried — use zeros
            z_untried_mean = np.zeros(GNN_EMB_DIM, dtype=np.float32)

        # 4. Concatenate
        augmented_state = np.concatenate([flat_state, z_claim, z_untried_mean]).astype(np.float32)
        assert augmented_state.shape == (GNN_STATE_DIM,), \
            f"Expected GNN state dim {GNN_STATE_DIM}, got {augmented_state.shape}"
        return augmented_state

    @property
    def state_dim(self) -> int:
        return GNN_STATE_DIM
