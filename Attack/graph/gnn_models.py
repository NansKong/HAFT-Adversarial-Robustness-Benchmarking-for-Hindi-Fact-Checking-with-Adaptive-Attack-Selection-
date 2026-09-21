"""HAFT Stage 2 — Vectorized Pure PyTorch GNN Models for Link Prediction

Implements:
  1. GraphSAGE (Inductive Mean-Aggregation)
  2. GAT (Graph Attention Network)
  3. Plain MLP Baseline (No graph structure)
  4. Attribute-kNN Baseline
  5. Attack Mean ASR Baseline
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class GraphSAGELayer(nn.Module):
    """Vectorized GraphSAGE layer with mean neighborhood aggregation."""

    def __init__(self, in_dim: int, out_dim: int):
        super().__init__()
        self.w_self = nn.Linear(in_dim, out_dim, bias=False)
        self.w_neigh = nn.Linear(in_dim, out_dim, bias=False)
        self.bias = nn.Parameter(torch.zeros(out_dim))

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """
        x: (N, in_dim)
        edge_index: (2, E) where [0] is src, [1] is dst
        """
        src, dst = edge_index[0], edge_index[1]
        num_nodes = x.size(0)

        # Vectorized mean aggregation using scatter_add
        neigh_sum = torch.zeros_like(x)
        neigh_sum.index_add_(0, dst, x[src])

        deg = torch.zeros(num_nodes, 1, device=x.device)
        deg.index_add_(0, dst, torch.ones((src.size(0), 1), device=x.device))
        deg = torch.clamp(deg, min=1.0)
        neigh_mean = neigh_sum / deg

        out = self.w_self(x) + self.w_neigh(neigh_mean) + self.bias
        return F.relu(out)


class GraphSAGEModel(nn.Module):
    """Two-layer GraphSAGE network for inductive node representation learning."""

    def __init__(self, claim_in_dim: int = 777, attack_in_dim: int = 16, hidden_dim: int = 64):
        super().__init__()
        # Input projection layers to project heterogeneous claim/attack features to hidden_dim
        self.claim_proj = nn.Linear(claim_in_dim, hidden_dim)
        self.attack_proj = nn.Linear(attack_in_dim, hidden_dim)

        self.sage1 = GraphSAGELayer(hidden_dim, hidden_dim)
        self.sage2 = GraphSAGELayer(hidden_dim, hidden_dim)
        self.dropout = nn.Dropout(0.2)

        self.link_pred = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, 1),
        )

    def encode(self, claim_x: torch.Tensor, attack_x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        h_claim = self.dropout(F.relu(self.claim_proj(claim_x)))
        h_attack = self.dropout(F.relu(self.attack_proj(attack_x)))
        x = torch.cat([h_claim, h_attack], dim=0)

        h1 = self.sage1(x, edge_index)
        h1 = self.dropout(h1)
        h2 = self.sage2(h1, edge_index)
        return h2

    def predict_link(self, z: torch.Tensor, claim_indices: torch.Tensor, attack_indices: torch.Tensor) -> torch.Tensor:
        """Link prediction score via parameterized MLP predictor."""
        z_c = z[claim_indices]
        z_a = z[attack_indices]
        pair_feat = torch.cat([z_c, z_a], dim=-1)
        return torch.sigmoid(self.link_pred(pair_feat).squeeze(-1))


class GATLayer(nn.Module):
    """Vectorized Graph Attention Network layer."""

    def __init__(self, in_dim: int, out_dim: int):
        super().__init__()
        self.linear = nn.Linear(in_dim, out_dim, bias=False)
        self.attn_src = nn.Parameter(torch.zeros(out_dim, 1))
        self.attn_dst = nn.Parameter(torch.zeros(out_dim, 1))
        self.bias = nn.Parameter(torch.zeros(out_dim))
        nn.init.xavier_uniform_(self.attn_src)
        nn.init.xavier_uniform_(self.attn_dst)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        h = self.linear(x)
        src, dst = edge_index[0], edge_index[1]

        alpha_src = (h * self.attn_src.squeeze(-1)).sum(dim=-1)  # (N,)
        alpha_dst = (h * self.attn_dst.squeeze(-1)).sum(dim=-1)  # (N,)

        edge_alpha = F.leaky_relu(alpha_src[src] + alpha_dst[dst], negative_slope=0.2)
        # Numerical stability: shift by max
        edge_alpha_exp = torch.exp(edge_alpha - edge_alpha.max())

        num_nodes = x.size(0)
        norm = torch.zeros(num_nodes, device=x.device)
        norm.index_add_(0, dst, edge_alpha_exp)
        norm = torch.clamp(norm, min=1e-8)

        attn_weights = edge_alpha_exp / norm[dst]

        weighted_msg = h[src] * attn_weights.unsqueeze(-1)
        out = torch.zeros_like(h)
        out.index_add_(0, dst, weighted_msg)
        return F.elu(out + self.bias)


class GATModel(nn.Module):
    """Two-layer Graph Attention Network."""

    def __init__(self, claim_in_dim: int = 777, attack_in_dim: int = 16, hidden_dim: int = 64):
        super().__init__()
        self.claim_proj = nn.Linear(claim_in_dim, hidden_dim)
        self.attack_proj = nn.Linear(attack_in_dim, hidden_dim)

        self.gat1 = GATLayer(hidden_dim, hidden_dim)
        self.gat2 = GATLayer(hidden_dim, hidden_dim)
        self.dropout = nn.Dropout(0.2)

        self.link_pred = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, 1),
        )

    def encode(self, claim_x: torch.Tensor, attack_x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        h_claim = self.dropout(F.relu(self.claim_proj(claim_x)))
        h_attack = self.dropout(F.relu(self.attack_proj(attack_x)))
        x = torch.cat([h_claim, h_attack], dim=0)

        h1 = self.gat1(x, edge_index)
        h1 = self.dropout(h1)
        h2 = self.gat2(h1, edge_index)
        return h2

    def predict_link(self, z: torch.Tensor, claim_indices: torch.Tensor, attack_indices: torch.Tensor) -> torch.Tensor:
        z_c = z[claim_indices]
        z_a = z[attack_indices]
        pair_feat = torch.cat([z_c, z_a], dim=-1)
        return torch.sigmoid(self.link_pred(pair_feat).squeeze(-1))


class PlainMLPBaseline(nn.Module):
    """Plain MLP baseline predicting link success directly without graph structure."""

    def __init__(self, claim_dim: int = 777, attack_dim: int = 16, hidden_dim: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(claim_dim + attack_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid(),
        )

    def forward(self, claim_feats: torch.Tensor, attack_feats: torch.Tensor) -> torch.Tensor:
        x = torch.cat([claim_feats, attack_feats], dim=-1)
        return self.net(x).squeeze(-1)
