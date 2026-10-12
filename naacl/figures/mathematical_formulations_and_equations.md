 =========================================================================
 HAFT ICLR 2027: COMPLETE MATHEMATICAL FORMULATIONS (DROP-IN READY)
 =========================================================================

##{Task and Quality-Controlled Evaluation Formulations}

A fact-checking instance is defined as $x_i = (c_i, e_i, y_i)$, where $c_i$ is the Hindi claim in Devanagari script, $e_i$ is the associated evidence text, and $y_i \in \{\text{SUP}, \text{REF}, \text{NEI}\}$ is the gold verification label. The clean verifier produces prediction $\hat{y}_i = V(c_i, e_i)$, with baseline indicator $b_i = \mathbb{I}[\hat{y}_i = y_i]$. The clean verifier achieves $74.29\$ accuracy ($832$ of $1,120$ claims correct); the $288$ clean failures ($b_i = 0$) are quarantined from the attack-success denominator.

For attack $a_j$, the perturbed instance $(c'_{ij}, e'_{ij}) = A_j(c_i, e_i)$ yields prediction $\hat{y}_{ij} = V(c'_{ij}, e'_{ij})$, producing a raw flip indicator $r_{ij} = \mathbb{I}[\hat{y}_{ij} \neq \hat{y}_i]$. The quality gate $q_{ij}$ evaluates semantic invariance and Devanagari fluency:
\begin{equation}
q_{ij} = \begin{cases} 
\mathbb{I}[f_{ij} \ge 3 \land m_{ij} = 1], & \text{meaning-preserving attack}, \\ 
\mathbb{I}[f_{ij} \ge 3], & \text{meaning-drift attack}, \\ 
1, & \text{word jumbling (intended syntactic noise)}, 
\end{cases}
\end{equation}
where $f_{ij} \in \{1, \dots, 5\}$ is the fluency score, and $m_{ij} \in \{0, 1\}$ is meaning preservation. A gated flip $g_{ij}$ requires a raw flip on a clean-baseline correct claim passing quality gates:
\begin{equation}
g_{ij} = r_{ij} \cdot b_i \cdot x_{ij} \cdot q_{ij},
\end{equation}
where $x_{ij} \in \{0, 1\}$ indicates judge availability. The resulting success metrics are:
\begin{equation}
\text{ASR}_{\text{raw}}(a_j) = \frac{\sum_{i=1}^{N} r_{ij}}{N_{\text{eligible}}^j},     \text{ASR}_{\text{gated}}(a_j) = \frac{\sum_{i=1}^{N} g_{ij}}{N_{\text{gated}}^j}.
\end{equation}

##{Finite-Horizon MDP and REINFORCE Policy Optimization}

The budgeted audit search is formulated as a finite-horizon MDP $\mathcal{M} = \langle \mathcal{S}, \mathcal{A}, \mathcal{P}, \mathcal{R}, \gamma, K \le 5 \rangle$.

###{State Representation.} The flat state space vector $s_t \in \mathbb{R}^{859}$ concatenates semantic claim representations with episodic progress:
\begin{equation}
s_t = \left[ z_c \,\|\, v \,\|\, m_t \,\|\, h_t \right] \in \mathbb{R}^{859},     768 + 3 + 22 + 66 = 859,
\end{equation}
where $z_c \in \mathbb{R}^{768}$ is the IndicBERT v2 $[\text{CLS}]$ claim embedding, $v \in \{0, 1\}^3$ is the one-hot clean verdict, $m_t \in \{0, 1\}^{22}$ is the tried-attack mask, and $h_t \in \{0, 1\}^{66}$ stores historical attack outcomes (3 binary signals per attack: gated flip, judge pass, raw flip).

###{Dynamic Action Masking.} To prevent repeating attacks, invalid actions are masked before softmax:
\begin{equation}
\tilde{z}_i = \begin{cases} z_i, & \text{if } m_t[i] = 0 \\ -\infty, & \text{if } m_t[i] = 1 \end{cases},     \pi_\theta(a_t = i \mid s_t) = \frac{\exp(\tilde{z}_i)}{\sum_{j=1}^{22} \exp(\tilde{z}_j)}.
\end{equation}

###{Reward Function and Immediate Early Stopping.}
\begin{equation}
R_t = -0.05 + 1.0 \cdot \mathbb{I}[\text{gated flip}] + 0.5 \cdot \mathbb{I}[\text{gated flip} \land \text{POS-tier attack}].
\end{equation}
*{Note on training formulation:} The POS-tier bonus is an auxiliary shaping signal used solely during offline simulation training to reward fatal evidence discovery; during test evaluation, the policy operates greedily on $s_t$ without access to reward signals or ground-truth attack tiers.

###{REINFORCE Policy Gradient Estimator with Learned Value Baseline.}
\begin{equation}
\nabla_\theta J(\theta) = \mathbb{E}_{\tau \sim \pi_\theta} \left[ \sum_{t=0}^{K-1} \nabla_\theta \log \pi_\theta(a_t \mid s_t) \cdot (G_t - V_\phi(s_t)) + \beta \nabla_\theta \mathcal{H}(\pi_\theta(\cdot \mid s_t)) \right],
\end{equation}
where $G_t = \sum_{k=t}^{K-1} \gamma^{k-t} R_{k+1}$ is discounted return ($\gamma = 0.99$), $V_\phi(s_t)$ is the learned state-value network ($859 \to 256 \to 1$ MLP) optimized via $\mathcal{L}_V = \frac{1}{K}\sum_{t=0}^{K-1} (V_\phi(s_t) - G_t)^2$, and $\beta = 0.05$ controls entropy regularization.

##{Inductive GraphSAGE Relational Topology}

The bipartite graph $\mathcal{G} = (\mathcal{V}, \mathcal{E})$ comprises $1,142$ nodes ($1,120$ claims, $22$ attacks) and $49,364$ directed relational edges. Claim features ($777$-dim) and attack features ($16$-dim) project into a common $d=64$ space:
\begin{equation}
h_{\mathcal{N}(i)}^{(k)} = \frac{1}{|\mathcal{N}(i)|} \sum_{j \in \mathcal{N}(i)} h_j^{(k-1)},     h_i^{(k)} = \text{ReLU}\left( W_{\text{self}}^{(k)} h_i^{(k-1)} + W_{\text{neigh}}^{(k)} h_{\mathcal{N}(i)}^{(k)} + b^{(k)} \right).
\end{equation}
Link prediction scores pair representations via a classification head:
\begin{equation}
p_{\text{link}}(v, u) = \sigma\left( W_{\text{cls}} [z_v \,\|\, z_u] + b_{\text{cls}} \right),   \mathcal{L}_{\text{BCE}} = - \frac{1}{|\mathcal{E}|} \sum_{(v, u) \in \mathcal{E}} \left[ y_{vu} \log p_{vu} + (1 - y_{vu}) \log (1 - p_{vu}) \right].
\end{equation}
In the GNN-RL ablation, relational features augment the policy state to $s_t^{(\text{GNN})} \in \mathbb{R}^{987}$:
\begin{equation}
s_t^{(\text{GNN})} = \left[ s_t^{(\text{flat})} (859) \,\|\, z_{\text{claim}}(c) (64) \,\|\, \bar{z}_{\text{untried}} (64) \right] \in \mathbb{R}^{987}.
\end{equation}

##{Cross-Model Transfer Attack Success Rate}

The cross-model transferability against Meta Llama 3 70B Instruct evaluates flips produced by GPT-4o-mini:
\begin{equation}
\text{Transfer\_ASR}(a_j) = \frac{\sum_{i \in \text{Flips}_{4o}(a_j)} \mathbb{I}\left[ V_{\text{Llama}}(c'_{ij}, e'_{ij}) \neq y_i \right]}{|\text{Flips}_{4o}(a_j)|} \times 100\.
\end{equation}
