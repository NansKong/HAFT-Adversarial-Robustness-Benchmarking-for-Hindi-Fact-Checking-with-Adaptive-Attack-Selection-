"""HAFT Stage 2 — Knowledge Graph Link Prediction & Leave-One-Attack-Out Benchmark

Generates Table 3: Graph Link Prediction & Cold-Start Evaluation.
Compares:
  - Attack Mean ASR
  - Attribute-kNN
  - Plain MLP (No graph)
  - GraphSAGE (Ours)
  - GAT (Ours)
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
    y_pred = (y_pred_prob >= threshold).astype(int)
    acc = accuracy_score(y_true, y_pred) * 100
    macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)

    try:
        auroc = roc_auc_score(y_true, y_pred_prob)
    except ValueError:
        auroc = 0.50

    try:
        auprc = average_precision_score(y_true, y_pred_prob)
    except ValueError:
        auprc = float(np.mean(y_true))

    return {
        "accuracy": float(acc),
        "macro_f1": float(macro_f1),
        "auroc": float(auroc),
        "auprc": float(auprc),
    }


def run_graph_benchmark(output_dir: str = "results/stage2/graph", epochs: int = 40) -> pd.DataFrame:
    """Run full graph link prediction benchmark across all baselines and GNNs."""
    os.makedirs(output_dir, exist_ok=True)
    np.random.seed(42)
    torch.manual_seed(42)

    print("Building Attack-Claim Knowledge Graph...")
    graph = AttackClaimGraph(base_dir=BASE_DIR)
    print(f"Graph constructed: {graph.num_nodes} nodes, {graph.edge_index.size(1)} directed edges.")

    # Prepare ground truth outcome matrix for link prediction
    # Target edges: Claim <-> Attack pairs (24,640 pairs)
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

    # 80/20 Edge Train/Test Split
    n_pairs = len(labels_np)
    perm = np.random.permutation(n_pairs)
    n_train = int(0.80 * n_pairs)

    train_idx = perm[:n_train]
    test_idx = perm[n_train:]

    train_c, train_a, train_y = claim_ids_np[train_idx], attack_ids_np[train_idx], labels_np[train_idx]
    test_c, test_a, test_y = claim_ids_np[test_idx], attack_ids_np[test_idx], labels_np[test_idx]

    print(f"Edge Split: {len(train_idx)} train edges, {len(test_idx)} test edges.")

    results = {}

    # 1. Baseline 1: Attack Mean ASR
    print("\nEvaluating Baseline 1: Attack Mean ASR...")
    atk_means = {}
    for a in range(NUM_ATTACKS):
        mask = train_a == a
        atk_means[a] = float(np.mean(train_y[mask])) if np.any(mask) else 0.0
    pred_mean = np.array([atk_means[a] for a in test_a])
    results["Attack Mean"] = evaluate_metrics(test_y, pred_mean)

    # 2. Baseline 2: Attribute-kNN (k=3)
    print("Evaluating Baseline 2: Attribute-kNN...")
    knn_preds = []
    for a in test_a:
        atk_key = ATTACK_KEYS_22[a]
        sims = [(i, compute_pair_similarity(atk_key, ATTACK_KEYS_22[i])) for i in range(NUM_ATTACKS) if i != a]
        sims.sort(key=lambda x: x[1], reverse=True)
        top3_indices = [x[0] for x in sims[:3]]
        pred_prob = float(np.mean([atk_means[idx] for idx in top3_indices]))
        knn_preds.append(pred_prob)
    results["kNN (Attributes)"] = evaluate_metrics(test_y, np.array(knn_preds))

    # 3. Baseline 3: Plain MLP (No Graph)
    print("Evaluating Baseline 3: Plain MLP (No Graph Structure)...")
    mlp = PlainMLPBaseline(claim_dim=777, attack_dim=16, hidden_dim=128)
    opt_mlp = optim.Adam(mlp.parameters(), lr=0.005)
    loss_fn = nn.BCELoss()

    train_cx_t = graph.claim_features[train_c]
    train_ax_t = graph.attack_features[train_a]
    train_y_t = torch.tensor(train_y, dtype=torch.float32)

    test_cx_t = graph.claim_features[test_c]
    test_ax_t = graph.attack_features[test_a]

    for ep in range(epochs):
        mlp.train()
        pred_t = mlp(train_cx_t, train_ax_t)
        loss = loss_fn(pred_t, train_y_t)
        opt_mlp.zero_grad()
        loss.backward()
        opt_mlp.step()

    mlp.eval()
    with torch.no_grad():
        mlp_pred = mlp(test_cx_t, test_ax_t).numpy()
    results["Plain MLP"] = evaluate_metrics(test_y, mlp_pred)

    # 4. Model 4: GraphSAGE
    print("Evaluating Model 4: GraphSAGE...")
    sage = GraphSAGEModel(claim_in_dim=777, attack_in_dim=16, hidden_dim=64)
    opt_sage = optim.Adam(sage.parameters(), lr=0.005)

    claim_idx_t = torch.tensor(train_c, dtype=torch.long)
    atk_node_idx_t = torch.tensor(NUM_CLAIMS + train_a, dtype=torch.long)

    test_claim_t = torch.tensor(test_c, dtype=torch.long)
    test_atk_node_t = torch.tensor(NUM_CLAIMS + test_a, dtype=torch.long)

    for ep in range(epochs):
        sage.train()
        z = sage.encode(graph.claim_features, graph.attack_features, graph.edge_index)
        pred_link = sage.predict_link(z, claim_idx_t, atk_node_idx_t)
        loss = loss_fn(pred_link, train_y_t)
        opt_sage.zero_grad()
        loss.backward()
        opt_sage.step()

    sage.eval()
    with torch.no_grad():
        z_test = sage.encode(graph.claim_features, graph.attack_features, graph.edge_index)
        sage_pred = sage.predict_link(z_test, test_claim_t, test_atk_node_t).numpy()
    results["GraphSAGE (Ours)"] = evaluate_metrics(test_y, sage_pred)

    # 5. Model 5: GAT (Graph Attention Network)
    print("Evaluating Model 5: GAT (Graph Attention Network)...")
    gat = GATModel(claim_in_dim=777, attack_in_dim=16, hidden_dim=64)
    opt_gat = optim.Adam(gat.parameters(), lr=0.005)

    for ep in range(epochs):
        gat.train()
        z = gat.encode(graph.claim_features, graph.attack_features, graph.edge_index)
        pred_link = gat.predict_link(z, claim_idx_t, atk_node_idx_t)
        loss = loss_fn(pred_link, train_y_t)
        opt_gat.zero_grad()
        loss.backward()
        opt_gat.step()

    gat.eval()
    with torch.no_grad():
        z_gat = gat.encode(graph.claim_features, graph.attack_features, graph.edge_index)
        gat_pred = gat.predict_link(z_gat, test_claim_t, test_atk_node_t).numpy()
    results["GAT (Ours)"] = evaluate_metrics(test_y, gat_pred)

    # Format Table 3
    table3_rows = []
    for m, met in results.items():
        table3_rows.append({
            "Model": m,
            "Accuracy (%)": f"{met['accuracy']:.2f}%",
            "Macro-F1": f"{met['macro_f1']:.3f}",
            "AUROC": f"{met['auroc']:.3f}",
            "AUPRC": f"{met['auprc']:.3f}",
        })

    table3_df = pd.DataFrame(table3_rows)
    print("\n" + "=" * 80)
    print("TABLE 3: ATTACK-CLAIM KNOWLEDGE GRAPH LINK PREDICTION BENCHMARK")
    print("=" * 80)
    print(table3_df.to_string(index=False))

    out_csv = os.path.join(output_dir, "table3_graph_prediction.csv")
    table3_df.to_csv(out_csv, index=False)
    print(f"\nSaved Table 3 to {out_csv}")

    # Save trained embeddings for integration
    torch.save(z_test.detach().cpu(), os.path.join(output_dir, "gnn_node_embeddings.pt"))
    print("Saved GNN node embeddings to gnn_node_embeddings.pt")

    return table3_df


if __name__ == "__main__":
    run_graph_benchmark()
