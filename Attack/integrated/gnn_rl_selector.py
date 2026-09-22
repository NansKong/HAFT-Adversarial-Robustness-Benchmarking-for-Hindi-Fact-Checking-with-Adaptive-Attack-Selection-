"""HAFT Stage 2 — GNN-Enhanced RL Attack Selector: Corrected Empirical Ablation

FLAW 2 FIX: Replaces hardcoded arithmetic (+4.22pp, -0.5 steps) and torch.randn
fallbacks with a full empirical training run of the 987-dim GNN-augmented RL policy.

Generates Table 4: GNN-RL Component Ablation Benchmark.
Compares (all using real training, no simulated values):
  A. Flat RL (859-dim standard state)
  B. GNN-Enhanced RL (987-dim relational state, requires gnn_node_embeddings.pt)
  C. RL without API Cost Penalty (api_cost_penalty=0.0)
  D. RL without Exploration (epsilon=0.0)
  E. Full Dataset (1,120 claims including 288 baseline failures)

Protocol:
  - 5 seeds per configuration (seeds 42-46)
  - 25 training epochs per seed
  - 60/20/20 claim split (same split as Table 1)
  - Evaluation: greedy policy (epsilon=0.0) on held-out test set
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd
import torch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from replay_env import OfflineAttackEnv, ATTACK_KEYS_22
from rl.state import STATE_DIM
from rl.reinforce import REINFORCEAgent
from rl.train_selector import split_claims, evaluate_rl_agent, train_rl_agent
from integrated.gnn_augmented_env import GNNAugmentedOfflineEnv, GNN_STATE_DIM

SEEDS = [42, 43, 44, 45, 46]
EPOCHS = 25


def _load_or_train_gnn_embeddings(base_dir: str) -> torch.Tensor:
    """Load pre-computed GNN embeddings, or train GraphSAGE first if missing."""
    emb_path = os.path.join(base_dir, "results", "stage2", "graph", "gnn_node_embeddings.pt")
    if os.path.exists(emb_path):
        print(f"Loading GNN node embeddings from {emb_path}...")
        return torch.load(emb_path, weights_only=True)
    else:
        print("GNN node embeddings not found. Training GraphSAGE first...")
        print("Running: python graph/leave_attack_out.py")
        import subprocess
        result = subprocess.run(
            [sys.executable, os.path.join(base_dir, "graph", "leave_attack_out.py")],
            capture_output=True, text=True, cwd=base_dir
        )
        if result.returncode != 0:
            raise RuntimeError(f"GNN training failed:\n{result.stderr}")
        print(result.stdout[-2000:])
        if not os.path.exists(emb_path):
            raise FileNotFoundError(f"GNN embeddings still missing after training: {emb_path}")
        return torch.load(emb_path, weights_only=True)


def _run_multi_seed(
    env_factory,
    state_dim: int,
    hidden_dim: int,
    seeds: List[int],
    epochs: int,
    epsilon: float,
    config_name: str,
) -> Dict[str, Any]:
    """Run multi-seed evaluation for a given environment factory and return aggregated metrics."""
    print(f"\n{'='*60}")
    print(f"  Config: {config_name} | state_dim={state_dim} | eps={epsilon} | epochs={epochs}")
    print(f"{'='*60}")

    seed_results = []
    for seed in seeds:
        env = env_factory()
        train_ids, val_ids, test_ids = split_claims(env.valid_claim_ids, seed=seed)
        agent, _ = train_rl_agent(
            env, train_ids, val_ids,
            epochs=epochs, epsilon=epsilon, seed=seed,
            state_dim=state_dim, hidden_dim=hidden_dim
        )
        res = evaluate_rl_agent(env, agent, test_ids)
        seed_results.append(res)
        print(f"  Seed {seed}: flip_disc={res['success_rate_pct']:.2f}% | "
              f"median_steps={res['median_steps_to_flip']:.1f} | "
              f"calls/claim={res['calls_per_claim']:.2f}")

    rates = [r["success_rate_pct"] for r in seed_results]
    steps = [r["median_steps_to_flip"] for r in seed_results]
    calls = [r["calls_per_claim"] for r in seed_results]

    return {
        "config": config_name,
        "state_dim": state_dim,
        "mean_flip_pct": float(np.mean(rates)),
        "std_flip_pct": float(np.std(rates)),
        "mean_median_steps": float(np.mean(steps)),
        "mean_calls_per_claim": float(np.mean(calls)),
        "seed_results": seed_results,
    }


def run_gnn_rl_ablation(output_dir: str = "results/stage2/integrated") -> pd.DataFrame:
    """Run full GNN-RL ablation suite and generate corrected Table 4."""
    os.makedirs(os.path.join(BASE_DIR, output_dir), exist_ok=True)

    # Load embeddings
    embeddings_path = os.path.join(BASE_DIR, "data", "claim_embeddings_indicbert_1120.pt")
    embeddings = torch.load(embeddings_path, weights_only=True)

    # Load GNN node embeddings (train if missing)
    gnn_embs = _load_or_train_gnn_embeddings(BASE_DIR)
    print(f"GNN embeddings shape: {gnn_embs.shape}")

    print("\n--- Running HAFT Stage 2 GNN-RL Ablation (True Empirical Results) ---\n")

    all_configs = []

    # ------------------------------------------------------------------
    # A. Flat RL (859-dim) — baseline for relative gain computation
    # ------------------------------------------------------------------
    res_flat = _run_multi_seed(
        env_factory=lambda: OfflineAttackEnv(
            base_dir=BASE_DIR, max_budget_k=5,
            claim_embeddings=embeddings, exclude_baseline_failures=True
        ),
        state_dim=STATE_DIM,
        hidden_dim=512,
        seeds=SEEDS, epochs=EPOCHS, epsilon=0.10,
        config_name="Flat RL (859-dim)",
    )
    all_configs.append(res_flat)

    # ------------------------------------------------------------------
    # B. GNN-Enhanced RL (987-dim) — EMPIRICAL, no hardcoding
    # ------------------------------------------------------------------
    res_gnn = _run_multi_seed(
        env_factory=lambda: GNNAugmentedOfflineEnv(
            gnn_embeddings=gnn_embs,
            base_dir=BASE_DIR, max_budget_k=5,
            claim_embeddings=embeddings, exclude_baseline_failures=True
        ),
        state_dim=GNN_STATE_DIM,
        hidden_dim=512,
        seeds=SEEDS, epochs=EPOCHS, epsilon=0.10,
        config_name="GNN-Enhanced RL (987-dim)",
    )
    all_configs.append(res_gnn)

    # ------------------------------------------------------------------
    # C. RL without API Cost Penalty (api_cost_penalty=0.0)
    # ------------------------------------------------------------------
    res_no_cost = _run_multi_seed(
        env_factory=lambda: OfflineAttackEnv(
            base_dir=BASE_DIR, max_budget_k=5, api_cost_penalty=0.0,
            claim_embeddings=embeddings, exclude_baseline_failures=True
        ),
        state_dim=STATE_DIM,
        hidden_dim=512,
        seeds=SEEDS, epochs=EPOCHS, epsilon=0.10,
        config_name="RL w/o API Cost Penalty",
    )
    all_configs.append(res_no_cost)

    # ------------------------------------------------------------------
    # D. RL without Exploration (epsilon=0.0 — pure greedy policy)
    # ------------------------------------------------------------------
    res_no_exp = _run_multi_seed(
        env_factory=lambda: OfflineAttackEnv(
            base_dir=BASE_DIR, max_budget_k=5,
            claim_embeddings=embeddings, exclude_baseline_failures=True
        ),
        state_dim=STATE_DIM,
        hidden_dim=512,
        seeds=SEEDS, epochs=EPOCHS, epsilon=0.0,
        config_name="RL w/o Exploration (eps=0)",
    )
    all_configs.append(res_no_exp)

    # ------------------------------------------------------------------
    # E. Full Dataset (1,120 claims including 288 baseline failures)
    # ------------------------------------------------------------------
    res_full = _run_multi_seed(
        env_factory=lambda: OfflineAttackEnv(
            base_dir=BASE_DIR, max_budget_k=5,
            claim_embeddings=embeddings, exclude_baseline_failures=False
        ),
        state_dim=STATE_DIM,
        hidden_dim=512,
        seeds=SEEDS, epochs=EPOCHS, epsilon=0.10,
        config_name="Full Dataset (incl. 288 failures)",
    )
    all_configs.append(res_full)

    # ------------------------------------------------------------------
    # Assemble Table 4
    # ------------------------------------------------------------------
    flat_rate = res_flat["mean_flip_pct"]

    table4_rows = []
    for cfg in all_configs:
        gain = cfg["mean_flip_pct"] - flat_rate
        gain_str = f"+{gain:.2f}%" if gain >= 0 else f"{gain:.2f}%"
        if cfg["config"] == "Flat RL (859-dim)":
            gain_str = "—"

        n_claims = 832 if "Full" not in cfg["config"] else 1120
        table4_rows.append({
            "Ablation Configuration":   cfg["config"],
            "State Dims":               cfg["state_dim"],
            "Claims Evaluated":         n_claims,
            "Flip Discovery (mean±std)": f"{cfg['mean_flip_pct']:.2f}% ± {cfg['std_flip_pct']:.2f}%",
            "Median Steps":             f"{cfg['mean_median_steps']:.1f}",
            "Relative Gain vs Flat":    gain_str,
        })

    table4_df = pd.DataFrame(table4_rows)
    print("\n" + "=" * 100)
    print("TABLE 4: GNN-RL INTEGRATION & COMPONENT ABLATION (5-SEED EMPIRICAL RESULTS)")
    print("NOTE: All results are real training runs — no hardcoded or simulated values.")
    print("=" * 100)
    print(table4_df.to_string(index=False))

    # Save outputs
    out_csv = os.path.join(BASE_DIR, output_dir, "table4_gnn_rl_ablation.csv")
    table4_df.to_csv(out_csv, index=False)
    print(f"\nSaved Table 4 to {out_csv}")

    out_json = os.path.join(BASE_DIR, output_dir, "table4_gnn_rl_raw.json")
    # Serialize seed_results (convert numpy types)
    serializable = []
    for cfg in all_configs:
        c = {k: v for k, v in cfg.items() if k != "seed_results"}
        c["seed_results"] = [
            {k2: (v2.tolist() if hasattr(v2, "tolist") else v2)
             for k2, v2 in sr.items()}
            for sr in cfg["seed_results"]
        ]
        serializable.append(c)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2)
    print(f"Saved raw 5-seed data to {out_json}")

    return table4_df


if __name__ == "__main__":
    run_gnn_rl_ablation()
