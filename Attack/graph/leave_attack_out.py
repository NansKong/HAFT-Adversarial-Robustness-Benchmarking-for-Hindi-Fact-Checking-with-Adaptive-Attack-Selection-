"""HAFT Stage 2 — Knowledge Graph Link Prediction: True Inductive Leave-Attack-Out Benchmark

FLAW 4 FIX: Replaces the previous random 80/20 edge split (which caused transductive leakage
by passing messages over test edges) with a rigorous Leave-Attack-Out (LAO) inductive protocol:

  For each fold i in {0..21}:
    1. Remove ALL edges connected to attack node i from the training edge_index.
    2. Zero out attack node i features during message passing (node is unseen).
    3. Evaluate link prediction ONLY on pairs (claim_j, attack_i) for all test claims.

This is the standard inductive GNN evaluation: attack i is a cold-start node the model
has never seen during propagation. AUPRC on rare flip links is the primary metric.

After all 22 folds, trains a final full-graph model and saves node embeddings for GNN-RL.

Generates Table 3: Graph Link Prediction — Inductive Leave-Attack-Out Evaluation.
Compares:
  - Attack Mean ASR (marginal baseline)
  - Attribute-kNN (k=3)
  - Plain MLP (No graph structure)
  - GraphSAGE (Ours, inductive LAO)
  - GAT (comparison)
"""

from __future__ import annotations

import json
import os
import sys
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, average_precision_score

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from replay_env import ATTACK_KEYS_22
from exemplar.selector import ATTACK_PROPERTIES, compute_pair_similarity
from graph.builder import AttackClaimGraph, NUM_CLAIMS, NUM_ATTACKS
from graph.gnn_models import GraphSAGEModel, GATModel, PlainMLPBaseline


def evaluate_metrics(y_true: np.ndarray, y_pred_prob: np.ndarray, threshold: float = 0.50) -> Dict[str, float]:
    """Calculate Accuracy, Macro-F1, AUROC, AUPRC."""
    if len(y_true) == 0:
        return {"accuracy": 0.0, "macro_f1": 0.0, "auroc": 0.5, "auprc": float(np.mean(y_true)) if len(y_true) > 0 else 0.0}
    y_pred = (y_pred_prob >= threshold).astype(int)
    acc = accuracy_score(y_true, y_pred) * 100
    macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)

    try:
        auroc = roc_auc_score(y_true, y_pred_prob) if len(np.unique(y_true)) > 1 else 0.5
    except ValueError:
        auroc = 0.50

    try:
        auprc = average_precision_score(y_true, y_pred_prob) if len(np.unique(y_true)) > 1 else float(np.mean(y_true))
    except ValueError:
        auprc = float(np.mean(y_true))

    return {
        "accuracy": float(acc),
        "macro_f1": float(macro_f1),
        "auroc": float(auroc),
        "auprc": float(auprc),
    }


def mask_attack_edges(edge_index: torch.Tensor, attack_node_id: int) -> torch.Tensor:
    """Return edge_index with all edges connected to attack_node_id removed.
    This is the core of the inductive protocol: the GNN cannot propagate
    information from/to the held-out attack node during training.
    """
    src, dst = edge_index[0], edge_index[1]
    keep = (src != attack_node_id) & (dst != attack_node_id)
    return edge_index[:, keep]


def run_graph_benchmark(output_dir: str = "results/stage2/graph", epochs: int = 50) -> pd.DataFrame:
    """Run full inductive Leave-Attack-Out graph link prediction benchmark."""
    os.makedirs(output_dir, exist_ok=True)
    np.random.seed(42)
    torch.manual_seed(42)

    print("Building Attack-Claim Knowledge Graph...")
    graph = AttackClaimGraph(base_dir=BASE_DIR)
    print(f"Graph: {graph.num_nodes} nodes, {graph.edge_index.size(1)} directed edges.")

    # ------------------------------------------------------------------
    # Load all 24,640 (claim, attack, label) triples
    # ------------------------------------------------------------------
    claim_ids = []
    attack_ids = []
    labels = []

    results_dir = os.path.join(BASE_DIR, "results", "full_run")
    for atk_idx, atk_key in enumerate(ATTACK_KEYS_22):
        csv_path = os.path.join(results_dir, f"{atk_key}_results.csv")
        df = pd.read_csv(csv_path)
        for _, row in df.iterrows():
            cid = int(row["row_id"])
            raw_flip = str(row.get("flipped", "")).lower() == "true"
            excluded = str(row.get("excluded", "")).lower() == "true"
            reason = str(row.get("reason", ""))
            gated = raw_flip and not excluded and (reason != "baseline_failure")
            claim_ids.append(cid)
            attack_ids.append(atk_idx)
            labels.append(1.0 if gated else 0.0)

    claim_ids_np = np.array(claim_ids)
    attack_ids_np = np.array(attack_ids)
    labels_np = np.array(labels)

    print(f"Total pairs: {len(labels_np)}, Flip rate: {labels_np.mean()*100:.2f}%")

    # ------------------------------------------------------------------
    # Compute per-attack global mean ASR (from all pairs, used as a baseline)
    # ------------------------------------------------------------------
    atk_global_means = {}
    for a in range(NUM_ATTACKS):
        mask = attack_ids_np == a
        atk_global_means[a] = float(np.mean(labels_np[mask])) if np.any(mask) else 0.0

    # ------------------------------------------------------------------
    # INDUCTIVE LEAVE-ATTACK-OUT PROTOCOL
    # For each fold i: train on all edges EXCEPT those touching attack node i,
    # evaluate on (claim, attack_i) pairs only.
    # ------------------------------------------------------------------
    print("\n=== INDUCTIVE LEAVE-ATTACK-OUT EVALUATION (22 folds) ===\n")

    sage_fold_metrics = []
    gat_fold_metrics = []
    mlp_fold_metrics = []
    atk_mean_fold_metrics = []
    knn_fold_metrics = []

    for fold_i in range(NUM_ATTACKS):
        attack_node_id = NUM_CLAIMS + fold_i
        atk_key_i = ATTACK_KEYS_22[fold_i]

        # Test pairs: all (claim, attack_i) pairs
        test_mask = attack_ids_np == fold_i
        test_c = claim_ids_np[test_mask]
        test_a = attack_ids_np[test_mask]
        test_y = labels_np[test_mask]

        # Training pairs: all pairs NOT involving attack_i
        train_mask = attack_ids_np != fold_i
        train_c = claim_ids_np[train_mask]
        train_a = attack_ids_np[train_mask]
        train_y = labels_np[train_mask]

        # Training edge_index: mask out ALL edges connected to attack_i node
        train_edge_index = mask_attack_edges(graph.edge_index, attack_node_id)

        # Mask attack node features to zero (cold-start: node is unseen during propagation)
        claim_feats = graph.claim_features.clone()
        attack_feats = graph.attack_features.clone()
        attack_feats_masked = attack_feats.clone()
        attack_feats_masked[fold_i] = 0.0  # Zero out held-out attack

        # Tensors for training
        train_c_t = torch.tensor(train_c, dtype=torch.long)
        train_a_node_t = torch.tensor(NUM_CLAIMS + train_a, dtype=torch.long)
        train_y_t = torch.tensor(train_y, dtype=torch.float32)

        # Tensors for test
        test_c_t = torch.tensor(test_c, dtype=torch.long)
        test_a_node_t = torch.tensor(NUM_CLAIMS + test_a, dtype=torch.long)

        # --- Baseline 1: Attack Mean (marginal, uses only training attack means) ---
        train_atk_means = {}
        for a in range(NUM_ATTACKS):
            if a == fold_i:
                # Use kNN of similar attacks as proxy
                sims = [(j, compute_pair_similarity(ATTACK_KEYS_22[fold_i], ATTACK_KEYS_22[j]))
                        for j in range(NUM_ATTACKS) if j != fold_i]
                sims.sort(key=lambda x: x[1], reverse=True)
                top3 = [x[0] for x in sims[:3]]
                train_atk_means[a] = float(np.mean([atk_global_means[j] for j in top3]))
            else:
                mask_a = (attack_ids_np == a) & train_mask
                train_atk_means[a] = float(np.mean(labels_np[mask_a])) if np.any(mask_a) else 0.0

        pred_mean = np.array([train_atk_means[fold_i]] * len(test_y))
        atk_mean_fold_metrics.append(evaluate_metrics(test_y, pred_mean))

        # --- Baseline 2: Attribute-kNN ---
        sims_knn = [(j, compute_pair_similarity(atk_key_i, ATTACK_KEYS_22[j]))
                    for j in range(NUM_ATTACKS) if j != fold_i]
        sims_knn.sort(key=lambda x: x[1], reverse=True)
        top3_knn = [x[0] for x in sims_knn[:3]]
        knn_prob = float(np.mean([train_atk_means[j] for j in top3_knn]))
        knn_preds = np.full(len(test_y), knn_prob)
        knn_fold_metrics.append(evaluate_metrics(test_y, knn_preds))

        # --- Baseline 3: Plain MLP (no graph, uses raw features) ---
        mlp = PlainMLPBaseline(claim_dim=777, attack_dim=16, hidden_dim=128)
        opt_mlp = optim.Adam(mlp.parameters(), lr=0.005)
        loss_fn = nn.BCELoss()

        train_cx_t = claim_feats[train_c_t]
        train_ax_t = attack_feats_masked[train_a_node_t - NUM_CLAIMS]
        test_cx_t = claim_feats[test_c_t]
        test_ax_t = attack_feats_masked[test_a_node_t - NUM_CLAIMS]  # zeroed features

        for ep in range(epochs):
            mlp.train()
            pred_t = mlp(train_cx_t, train_ax_t)
            loss = loss_fn(pred_t, train_y_t)
            opt_mlp.zero_grad(); loss.backward(); opt_mlp.step()

        mlp.eval()
        with torch.no_grad():
            mlp_pred = mlp(test_cx_t, test_ax_t).numpy()
        mlp_fold_metrics.append(evaluate_metrics(test_y, mlp_pred))

        # --- Model 4: GraphSAGE (Inductive, masked edges + features) ---
        sage = GraphSAGEModel(claim_in_dim=777, attack_in_dim=16, hidden_dim=64)
        opt_sage = optim.Adam(sage.parameters(), lr=0.005, weight_decay=1e-4)

        for ep in range(epochs):
            sage.train()
            # Encode using MASKED edge_index (no edges to attack_i) and MASKED features
            z = sage.encode(claim_feats, attack_feats_masked, train_edge_index)
            pred_t = sage.predict_link(z, train_c_t, train_a_node_t)
            loss = loss_fn(pred_t, train_y_t)
            opt_sage.zero_grad(); loss.backward(); opt_sage.step()

        sage.eval()
        with torch.no_grad():
            z_test = sage.encode(claim_feats, attack_feats_masked, train_edge_index)
            sage_pred = sage.predict_link(z_test, test_c_t, test_a_node_t).numpy()
        sage_fold_metrics.append(evaluate_metrics(test_y, sage_pred))

        # --- Model 5: GAT ---
        gat = GATModel(claim_in_dim=777, attack_in_dim=16, hidden_dim=64)
        opt_gat = optim.Adam(gat.parameters(), lr=0.005, weight_decay=1e-4)

        for ep in range(epochs):
            gat.train()
            z_g = gat.encode(claim_feats, attack_feats_masked, train_edge_index)
            pred_g = gat.predict_link(z_g, train_c_t, train_a_node_t)
            loss_g = loss_fn(pred_g, train_y_t)
            opt_gat.zero_grad(); loss_g.backward(); opt_gat.step()

        gat.eval()
        with torch.no_grad():
            z_gtest = gat.encode(claim_feats, attack_feats_masked, train_edge_index)
            gat_pred = gat.predict_link(z_gtest, test_c_t, test_a_node_t).numpy()
        gat_fold_metrics.append(evaluate_metrics(test_y, gat_pred))

        flip_rate = test_y.mean() * 100
        sage_auprc = sage_fold_metrics[-1]["auprc"]
        print(f"  Fold {fold_i:2d} ({atk_key_i[:30]:30s}) | flip_rate={flip_rate:.1f}% | "
              f"SAGE_AUPRC={sage_auprc:.3f} | n_test={len(test_y)}")

    # ------------------------------------------------------------------
    # Aggregate metrics across 22 folds
    # ------------------------------------------------------------------
    def agg(fold_list: List[Dict]) -> Dict:
        keys = ["accuracy", "macro_f1", "auroc", "auprc"]
        return {k: float(np.mean([f[k] for f in fold_list])) for k in keys}

    results = {
        "Attack Mean ASR":  agg(atk_mean_fold_metrics),
        "Attribute-kNN":    agg(knn_fold_metrics),
        "Plain MLP":        agg(mlp_fold_metrics),
        "GraphSAGE (Ours)": agg(sage_fold_metrics),
        "GAT":              agg(gat_fold_metrics),
    }

    # ------------------------------------------------------------------
    # Table 3
    # ------------------------------------------------------------------
    table3_rows = []
    for method, m in results.items():
        table3_rows.append({
            "Method": method,
            "Protocol": "Inductive LOO",
            "AUROC": f"{m['auroc']:.3f}",
            "AUPRC": f"{m['auprc']:.3f}",
            "Accuracy (%)": f"{m['accuracy']:.2f}%",
            "Macro-F1": f"{m['macro_f1']:.3f}",
        })

    table3_df = pd.DataFrame(table3_rows)
    print("\n" + "=" * 90)
    print("TABLE 3: GRAPH LINK PREDICTION — INDUCTIVE LEAVE-ATTACK-OUT PROTOCOL")
    print("NOTE: Each fold masks attack node i and its edges during training (true cold-start)")
    print("=" * 90)
    print(table3_df.to_string(index=False))

    out_csv = os.path.join(BASE_DIR, output_dir, "table3_graph_prediction.csv")
    table3_df.to_csv(out_csv, index=False)
    print(f"\nSaved Table 3 to {out_csv}")

    # ------------------------------------------------------------------
    # Save per-fold detail for reporting
    # ------------------------------------------------------------------
    fold_detail = []
    for fold_i in range(NUM_ATTACKS):
        fold_detail.append({
            "fold": fold_i,
            "attack": ATTACK_KEYS_22[fold_i],
            "sage_auroc": sage_fold_metrics[fold_i]["auroc"],
            "sage_auprc": sage_fold_metrics[fold_i]["auprc"],
            "mlp_auprc": mlp_fold_metrics[fold_i]["auprc"],
            "atk_mean_auprc": atk_mean_fold_metrics[fold_i]["auprc"],
        })
    fold_df = pd.DataFrame(fold_detail)
    fold_csv = os.path.join(BASE_DIR, output_dir, "table3_fold_detail.csv")
    fold_df.to_csv(fold_csv, index=False)

    # ------------------------------------------------------------------
    # SAVE GNN NODE EMBEDDINGS (full graph, all 22 attacks)
    # for use by integrated/gnn_rl_selector.py (GNN-RL integration)
    # ------------------------------------------------------------------
    print("\nTraining final full-graph GraphSAGE for GNN-RL embedding export...")
    torch.manual_seed(42)
    sage_final = GraphSAGEModel(claim_in_dim=777, attack_in_dim=16, hidden_dim=64)
    opt_final = optim.Adam(sage_final.parameters(), lr=0.005, weight_decay=1e-4)

    all_c_t = torch.tensor(claim_ids_np, dtype=torch.long)
    all_a_node_t = torch.tensor(NUM_CLAIMS + attack_ids_np, dtype=torch.long)
    all_y_t = torch.tensor(labels_np, dtype=torch.float32)
    loss_fn_final = nn.BCELoss()

    for ep in range(epochs):
        sage_final.train()
        z_all = sage_final.encode(graph.claim_features, graph.attack_features, graph.edge_index)
        pred_all = sage_final.predict_link(z_all, all_c_t, all_a_node_t)
        loss_f = loss_fn_final(pred_all, all_y_t)
        opt_final.zero_grad(); loss_f.backward(); opt_final.step()
        if (ep + 1) % 10 == 0:
            print(f"  Full-graph training epoch {ep+1}/{epochs} | loss={loss_f.item():.4f}")

    sage_final.eval()
    with torch.no_grad():
        z_final = sage_final.encode(graph.claim_features, graph.attack_features, graph.edge_index)

    emb_path = os.path.join(BASE_DIR, "results", "stage2", "graph", "gnn_node_embeddings.pt")
    os.makedirs(os.path.dirname(emb_path), exist_ok=True)
    torch.save(z_final.detach().cpu(), emb_path)
    print(f"Saved GNN node embeddings ({z_final.shape}) to {emb_path}")
    print("(These embeddings are used by integrated/gnn_rl_selector.py for GNN-RL augmentation)")

    return table3_df


if __name__ == "__main__":
    run_graph_benchmark()
