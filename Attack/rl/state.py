"""HAFT Stage 2 — 859-Dimensional RL State Representation

Dimensions:
  1. e_claim (768): IndicBERT embedding of the Hindi claim.
  2. v_verdict (3): One-hot encoding of clean baseline verifier verdict [SUP, REF, NEI].
  3. m_tried (22): Binary mask indicating which of the 22 attacks have been attempted.
  4. r_prev (66): Previous attack outcomes (3 features per attack: [gated_success, judge_pass, raw_flip]).

Total: 768 + 3 + 22 + 66 = 859 dimensions.
"""

from __future__ import annotations
import numpy as np
import torch

STATE_DIM = 859
CLAIM_EMB_DIM = 768
VERDICT_DIM = 3
TRIED_MASK_DIM = 22
PREV_RESULTS_DIM = 66  # 22 * 3


def encode_verdict(label: str) -> np.ndarray:
    """One-hot encode the baseline verdict."""
    v = np.zeros(VERDICT_DIM, dtype=np.float32)
    label_clean = label.upper().strip()
    if label_clean == "SUP":
        v[0] = 1.0
    elif label_clean == "REF":
        v[1] = 1.0
    elif label_clean == "NEI":
        v[2] = 1.0
    return v


def build_state(
    claim_embedding: np.ndarray | torch.Tensor,
    verdict_one_hot: np.ndarray,
    tried_mask: np.ndarray,
    prev_results: np.ndarray,
) -> np.ndarray:
    """Construct the 859-dimensional state vector."""
    if isinstance(claim_embedding, torch.Tensor):
        claim_emb_np = claim_embedding.detach().cpu().numpy().flatten()
    else:
        claim_emb_np = np.asarray(claim_embedding, dtype=np.float32).flatten()

    assert claim_emb_np.shape == (CLAIM_EMB_DIM,), f"Expected claim emb shape ({CLAIM_EMB_DIM},), got {claim_emb_np.shape}"
    assert verdict_one_hot.shape == (VERDICT_DIM,), f"Expected verdict shape ({VERDICT_DIM},), got {verdict_one_hot.shape}"
    assert tried_mask.shape == (TRIED_MASK_DIM,), f"Expected tried_mask shape ({TRIED_MASK_DIM},), got {tried_mask.shape}"

    prev_flat = prev_results.flatten()
    assert prev_flat.shape == (PREV_RESULTS_DIM,), f"Expected prev_results shape ({PREV_RESULTS_DIM},), got {prev_flat.shape}"

    state = np.concatenate([claim_emb_np, verdict_one_hot, tried_mask, prev_flat]).astype(np.float32)
    assert state.shape == (STATE_DIM,), f"Expected total state dim {STATE_DIM}, got {state.shape}"
    return state
