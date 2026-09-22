"""HAFT Stage 2 — REINFORCE with Learned Baseline and Entropy Regularization

Updates the policy parameters using:
  theta <- theta + alpha * grad(log pi(a_t | s_t)) * (G_t - V(s_t)) + beta * grad(H(pi))
"""

from __future__ import annotations
from typing import List, Dict, Any, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical

from rl.policy import AttackPolicy, ValueBaseline


class REINFORCEAgent:
    """REINFORCE agent with learned state-value baseline and action masking.

    Supports both the standard 859-dim flat state and the 987-dim GNN-augmented
    state (Flaw 2 fix). Pass state_dim=987 for GNN-enhanced RL training.
    Entropy coefficient raised to 0.05 for improved exploration coverage.
    """

    def __init__(
        self,
        state_dim: int = 859,
        hidden_dim: int = 512,
        num_actions: int = 22,
        lr_policy: float = 0.001,
        lr_value: float = 0.002,
        gamma: float = 0.99,
        entropy_coef: float = 0.05,
        max_grad_norm: float = 1.0,
        device: str = "cpu",
    ):
        self.gamma = gamma
        self.entropy_coef = entropy_coef
        self.max_grad_norm = max_grad_norm
        self.device = torch.device(device)

        self.policy = AttackPolicy(state_dim, hidden_dim, num_actions).to(self.device)
        self.value_baseline = ValueBaseline(state_dim, hidden_dim // 2).to(self.device)

        self.optimizer_policy = optim.Adam(self.policy.parameters(), lr=lr_policy)
        self.optimizer_value = optim.Adam(self.value_baseline.parameters(), lr=lr_value)

    def select_action(
        self, state: np.ndarray, tried_mask: np.ndarray, epsilon: float = 0.0
    ) -> Tuple[int, torch.Tensor, torch.Tensor]:
        """Select action using policy network."""
        state_t = torch.tensor(state, dtype=torch.float32, device=self.device)
        mask_t = torch.tensor(tried_mask, dtype=torch.float32, device=self.device)
        return self.policy.select_action(state_t, mask_t, epsilon=epsilon)

    def update(
        self,
        states: List[np.ndarray],
        actions: List[int],
        rewards: List[float],
        log_probs: List[torch.Tensor],
        tried_masks: List[np.ndarray],
    ) -> Dict[str, float]:
        """Perform REINFORCE update with baseline subtraction on an episode trajectory."""
        T = len(rewards)
        if T == 0:
            return {"policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0, "return": 0.0}

        # 1. Compute discounted returns G_t
        returns = np.zeros(T, dtype=np.float32)
        G = 0.0
        for t in reversed(range(T)):
            G = rewards[t] + self.gamma * G
            returns[t] = G

        states_t = torch.tensor(np.array(states), dtype=torch.float32, device=self.device)
        returns_t = torch.tensor(returns, dtype=torch.float32, device=self.device)
        actions_t = torch.tensor(actions, dtype=torch.long, device=self.device)
        masks_t = torch.tensor(np.array(tried_masks), dtype=torch.float32, device=self.device)
        log_probs_t = torch.stack(log_probs).to(self.device)

        # 2. Compute state values V(s_t)
        values = self.value_baseline(states_t)
        advantages = returns_t - values.detach()

        # Normalize advantages if batch > 1
        if len(advantages) > 1 and advantages.std() > 1e-6:
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        # 3. Compute policy entropy
        probs = self.policy(states_t, masks_t)
        dist = Categorical(probs)
        entropy = dist.entropy().mean()

        # 4. Policy loss: -log_prob * advantage - beta * entropy
        policy_loss = -(log_probs_t * advantages).mean() - self.entropy_coef * entropy

        self.optimizer_policy.zero_grad()
        policy_loss.backward()
        nn.utils.clip_grad_norm_(self.policy.parameters(), self.max_grad_norm)
        self.optimizer_policy.step()

        # 5. Value loss: MSE(V(s_t), G_t)
        value_loss = nn.functional.mse_loss(values, returns_t)

        self.optimizer_value.zero_grad()
        value_loss.backward()
        nn.utils.clip_grad_norm_(self.value_baseline.parameters(), self.max_grad_norm)
        self.optimizer_value.step()

        return {
            "policy_loss": float(policy_loss.item()),
            "value_loss": float(value_loss.item()),
            "entropy": float(entropy.item()),
            "return": float(returns[0]),
        }
