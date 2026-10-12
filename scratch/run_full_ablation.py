import sys, os
sys.path.insert(0, r"e:\Attack\Attack")
from replay_env import OfflineAttackEnv, ATTACK_KEYS_22
from rl.train_selector import split_claims
import torch, numpy as np

emb_path = r"e:\Attack\Attack\data\claim_embeddings_indicbert_1120.pt"
embeddings = torch.load(emb_path, weights_only=True)
env = OfflineAttackEnv(base_dir=r"e:\Attack\Attack", max_budget_k=5, claim_embeddings=embeddings, exclude_baseline_failures=True)
all_claims = env.valid_claim_ids
seeds = [42, 43, 44, 45, 46]

def run_ablation(mode="full", epochs=25):
    scores = []
    rescues = []
    for s in seeds:
        train_ids, val_ids, test_ids = split_claims(all_claims, seed=s)
        torch.manual_seed(s)
        np.random.seed(s)
        
        from rl.reinforce import REINFORCEAgent
        agent = REINFORCEAgent(state_dim=859, hidden_dim=512, num_actions=env.num_attacks)
        
        for epoch in range(epochs):
            perm_train = np.random.permutation(train_ids)
            for cid in perm_train:
                state = env.reset(claim_id=int(cid))
                done = False
                states, actions, rewards, log_probs, masks = [], [], [], [], []
                while not done:
                    s_in = state.copy()
                    if mode == "no_claim_emb":
                        # Pure embedding ablation: zero out only the 768 claim embedding, keep 3-dim verdict
                        s_in[:768] = 0.0
                    elif mode == "history_only":
                        # Zero out both claim embedding and verdict (88-dim remaining)
                        s_in[:771] = 0.0
                    
                    action, log_prob, _ = agent.select_action(s_in, env.tried_mask, epsilon=0.10)
                    next_state, reward, done, info = env.step(action)
                    states.append(s_in)
                    actions.append(action)
                    rewards.append(reward)
                    log_probs.append(log_prob)
                    masks.append(env.tried_mask.copy())
                    state = next_state
                agent.update(states, actions, rewards, log_probs, masks)
        
        # Test evaluation with Hybrid policy (Top-2 static + RL handover)
        top2_indices = [env.attack_to_idx[k] for k in ["EA_CTXREP_01_ContextualizedReplace", "EA_ADVADD_01_AdvAdd"]]
        flips = []
        rescued = 0
        for cid in test_ids:
            state = env.reset(claim_id=int(cid))
            done = False
            found = False
            for act in top2_indices:
                next_state, _, done, info = env.step(act)
                if info["gated_flip"]:
                    found = True
                    break
                state = next_state
            while not done and not found:
                s_eval = state.copy()
                if mode == "no_claim_emb":
                    s_eval[:768] = 0.0
                elif mode == "history_only":
                    s_eval[:771] = 0.0
                
                action, _, _ = agent.select_action(s_eval, env.tried_mask, epsilon=0.0)
                next_state, _, done, info = env.step(action)
                if info["gated_flip"]:
                    found = True
                    rescued += 1
                state = next_state
            flips.append(1 if found else 0)
        scores.append(np.mean(flips) * 100)
        rescues.append(rescued)
    return scores, rescues

print("Running 25-epoch 5-seed Ablation...")
scores_full, rescues_full = run_ablation("full", epochs=25)
print(f"Full State (859-dim): {np.mean(scores_full):.2f}% +/- {np.std(scores_full, ddof=1):.2f}% | Rescues: {np.mean(rescues_full):.1f} +/- {np.std(rescues_full, ddof=1):.1f} per fold ({scores_full})")

scores_no_emb, rescues_no_emb = run_ablation("no_claim_emb", epochs=25)
print(f"No Claim Emb (91-dim, keeps verdict): {np.mean(scores_no_emb):.2f}% +/- {np.std(scores_no_emb, ddof=1):.2f}% | Rescues: {np.mean(rescues_no_emb):.1f} +/- {np.std(rescues_no_emb, ddof=1):.1f} ({scores_no_emb})")

scores_hist, rescues_hist = run_ablation("history_only", epochs=25)
print(f"History Only (88-dim, no verdict): {np.mean(scores_hist):.2f}% +/- {np.std(scores_hist, ddof=1):.2f}% | Rescues: {np.mean(rescues_hist):.1f} +/- {np.std(rescues_hist, ddof=1):.1f} ({scores_hist})")
