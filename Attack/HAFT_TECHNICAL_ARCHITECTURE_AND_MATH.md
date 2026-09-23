# HAFT: Technical Architecture and Mathematical Foundations

This implementation-oriented companion follows the latest Final Project Report.

## 1. System Boundary

Phase A performs attack generation, verification, and Judge-based quality assessment. Stage 2 replay, RL training, graph experiments, and exemplar selection operate offline over cached Phase A outcomes and make no additional verifier API calls during training. The complete framework is therefore not 100% offline.

## 2. Phase A Gate

For claim $c_i$ and attack $a_j$, $r_{ij}$ is the raw verdict flip and $b_i$ indicates a correct clean-verifier verdict. The Judge returns fluency $f_{ij}\in\{1,2,3,4,5\}$ and, where applicable, `meaning_preserved` $m_{ij}$.

$$q_{ij}=\begin{cases}\mathbb{I}[f_{ij}\ge3\land m_{ij}=1],&\text{meaning-preserving},\\\mathbb{I}[f_{ij}\ge3],&\text{meaning-drift},\\1,&\text{word jumbling},\\\text{excluded},&\text{missing Judge result},\end{cases}\qquad g_{ij}=\mathbb{I}[b_i=1]r_{ij}q_{ij}.$$

No cosine-similarity or perplexity gate is part of the implemented methodology.

## 3. Offline RL Selector

$$s_t=[e_{\mathrm{claim}}^{768}\Vert b_{\mathrm{verdict}}^3\Vert m_t^{\mathrm{tried},22}\Vert o_t^{66}]\in\mathbb{R}^{859}.$$

The state contains the IndicBERT embedding, clean-verdict one-hot vector, tried-attack mask, and 22 triples of gated success, Judge pass, and raw flip. Previously tried actions receive $-\infty$ logits before softmax.

```text
859 -> 512 -> 22
```

The policy uses ReLU and masked softmax. Training used 25 epochs, $\epsilon=0.10$, and seeds 42--46; final evaluation used $\epsilon=0.0$.

$$R_t=-0.05+1.0\,\mathbb{I}[\mathrm{gated\ flip}]+0.5\,\mathbb{I}[\mathrm{gated\ flip}\land\mathrm{POS\ attack}].$$

## 4. Phase C Exemplar Policy

The selector retained 8.1 exemplars, reducing exemplar count by 61.4% relative to 21. This is not measured token savings. Accuracy was 90.91% versus 95.45% for Random-5, with paired McNemar $p=1.0000$; report this as statistical equivalence, not superiority or optimality.

## 5. Heterogeneous Attack--Claim Graph

The graph has 1,120 claim nodes, 22 attack nodes, 24,640 measured claim--attack pairs, and 49,364 directed relational edges. It contains claim--attack outcome edges and attack--attack similarity edges, so it is not strictly bipartite.

Claim features are 777-dimensional:

$$768\ \text{IndicBERT}+3\ \text{label one-hot}+6\ \text{domain one-hot}=777.$$

Attack features use the report's 16-dimensional attribute encoding. Node features are projected to 64 dimensions before GraphSAGE or GAT message passing, with binary cross-entropy for link prediction.

## 6. Graph Results

The original random edge split produced GraphSAGE AUROC 0.865 and AUPRC 0.482. Strict Leave-Attack-Out produced AUROC 0.485 and AUPRC 0.121. Cold-start generalization to unseen attacks remains unestablished.

## 7. GNN--RL Integration

$$s_t^{\mathrm{GNN}}=[s_t^{\mathrm{flat}}\Vert z_{\mathrm{claim}}\Vert\bar z_{\mathrm{untried}}]\in\mathbb{R}^{987}.$$

Each graph representation has 64 dimensions. Flat RL achieved $82.16\%\pm2.02\%$ and GNN--RL achieved $80.72\%\pm3.06\%$; graph augmentation did not improve discovery in frozen-outcome replay.

## 8. Unmeasured-Attack Ranking

The 31 unmeasured survey attacks receive provisional MID-tier predictions. These rankings are prioritization hypotheses, not measured ASRs. Future generation, verification, judging, and benchmark inclusion are required before empirical success rates can be reported.

## 9. Cross-Model Audit

The transfer artifact lists 1,020 candidate pairs, of which 966 were completed and recorded as Llama 3 70B verification pairs. The remaining 54 candidates are Omission (51) and Imperceptible Verification (3), with no completed Llama records. Transfer is attack-dependent, including Fact2Fiction 100%, AdvAdd 99.5%, ContextReplace 89.5%, ClaimRewrite 73.78%, and FactMixing 3.5%. This is evidence of transfer for several attacks, not a decisive refutation of every single-model confound.