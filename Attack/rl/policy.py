"""HAFT Stage 2 — Policy Network and Value Baseline for RL Attack Selection

Architecture:
  - Policy: Linear(859, 256) -> ReLU -> Linear(256, 22) -> Masked Softmax
  - Value Baseline: Linear(859, 128) -> ReLU -> Linear(128, 1)
"""

from __future__ import annotations
from typing import Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Categorical

from rl.state import STATE_DIM, TRIED_MASK_DIM


class AttackPolicy(nn.Module):
    """Small, efficient 2-layer MLP policy for attack selection with action masking."""

    def __init__(self, state_dim: int = STATE_DIM, hidden_dim: int = 256, num_actions: int = 22):
        super().__init__()
        self.num_actions = num_actions
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, num_actions),
        )

    def forward(self, state: torch.Tensor, tried_mask: torch.Tensor) -> torch.Tensor:
        """Compute masked action probabilities.
        Args:
            state: Tensor of shape (B, state_dim) or (state_dim,)
            tried_mask: Tensor of shape (B, num_actions) or (num_actions,) where 1.0 = tried.
        Returns:
            probs: Masked probability distribution over available attacks.
        """
        if state.dim() == 1:
            state = state.unsqueeze(0)
            tried_mask = tried_mask.unsqueeze(0)
            squeeze_output = True
        else:
            squeeze_output = False

        logits = self.net(state)

        # Apply large negative penalty to already tried actions
        masked_logits = logits.clone()
        masked_logits[tried_mask > 0.5] = -1e9

        probs = F.softmax(masked_logits, dim=-1)

        # Safeguard: if all actions are tried (should not happen before K=5), avoid NaN
        sum_probs = probs.sum(dim=-1, keepdim=True)
        probs = torch.where(sum_probs > 0, probs / sum_probs, torch.ones_like(probs) / self.num_actions)

        if squeeze_output:
            probs = probs.squeeze(0)

        return probs

    def select_action(
        self, state: torch.Tensor, tried_mask: torch.Tensor, epsilon: float = 0.0
    ) -> Tuple[int, torch.Tensor, torch.Tensor]:
        """Select an action using the policy with optional epsilon-greedy exploration.
        Returns:
            action: Selected attack index (int)
            log_prob: Log probability of the selected action (torch.Tensor)
            probs: Full action probability vector
        """
        probs = self.forward(state, tried_mask)
        untried_indices = torch.where(tried_mask < 0.5)[0]

        if len(untried_indices) == 0:
            # Fallback if no untried actions remain
            return 0, torch.tensor(0.0, device=state.device), probs

        # Epsilon-greedy exploration
        if np.random.rand() < epsilon:
            rand_idx = int(np.random.choice(untried_indices.cpu().numpy()))
            action = rand_idx
            dist = Categorical(probs)
            log_prob = dist.log_prob(torch.tensor(action, device=state.device))
        else:
            dist = Categorical(probs)
            action = int(dist.sample().item())
            log_prob = dist.log_prob(torch.tensor(action, device=state.device))

        return action, log_prob, probs


class ValueBaseline(nn.Module):
    """State-value baseline network for REINFORCE variance reduction."""

    def __init__(self, state_dim: int = STATE_DIM, hidden_dim: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        return self.net(state).squeeze(-1)
