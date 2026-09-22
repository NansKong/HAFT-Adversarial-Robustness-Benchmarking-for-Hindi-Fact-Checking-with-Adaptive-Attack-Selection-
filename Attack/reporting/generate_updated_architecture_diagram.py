"""HAFT — Master Publication Architecture Diagram Generator (Faithful Re-creation & Stage 2 Enhancement)

Recreates the visual aesthetics, layout, modular panels, badges, and circuits of
`attack diagram.jpeg` with 100% fidelity, incorporating all Stage 2 advancements:
- Exact 859 -> 987 state dimensions (+4.22% flip gain from 128-dim GraphSAGE embeds)
- Bipartite heterogeneous graph (1,142 nodes, 49,364 directed edges)
- Pure PyTorch vectorized GraphSAGE vs GAT vs Plain MLP link prediction
- RL Exemplar Selector (95.45% LOO accuracy, 52.4% token reduction)
- 31 survey attack tier classifications (2 POS, 28 MID, 1 NEG)
- 5-LLM empirical comparison matrix (DeepSeek 72.7% vs Western LLMs 27.3%)
- Native Devanagari Hindi font rendering (Nirmala UI) with zero missing glyphs
"""

from __future__ import annotations

import os
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Circle, Ellipse, Rectangle

# Enable native Devanagari Hindi font rendering
plt.rcParams["font.sans-serif"] = ["Nirmala UI", "Segoe UI", "DejaVu Sans", "Arial"]
plt.rcParams["axes.edgecolor"] = "#cbd5e1"
plt.rcParams["axes.linewidth"] = 1.0

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def draw_card(
    ax, x, y, w, h, bg_color, border_color, title="", subtitle="",
    border_style="solid", border_width=1.6, pad=0.008, zorder=2,
    title_color="#0f172a", title_size=9.5, title_align="center"
):
    """Draw a styled rounded card."""
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad={pad}",
        facecolor=bg_color,
        edgecolor=border_color,
        linestyle=border_style,
        linewidth=border_width,
        zorder=zorder,
        transform=ax.transAxes
    )
    ax.add_patch(box)

    if title:
        tx = x + w / 2 if title_align == "center" else x + 0.012
        ha = "center" if title_align == "center" else "left"
        ax.text(
            tx, y + h - 0.015, title,
            ha=ha, va="top", fontsize=title_size, fontweight="bold",
            color=title_color, transform=ax.transAxes, zorder=zorder + 1
        )
    if subtitle:
        ax.text(
            x + w / 2, y + h - 0.033, subtitle,
            ha="center", va="top", fontsize=7.8, fontstyle="italic",
            color="#475569", transform=ax.transAxes, zorder=zorder + 1
        )
    return box


def draw_pill(ax, x, y, w, h, text, bg_color, border_color, text_color, fontsize=7.2, fontweight="bold", zorder=4):
    """Draw a capsule pill badge."""
    pill = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.003",
        facecolor=bg_color,
        edgecolor=border_color,
        linewidth=1.0,
        zorder=zorder,
        transform=ax.transAxes
    )
    ax.add_patch(pill)
    ax.text(
        x + w / 2, y + h / 2, text,
        ha="center", va="center", fontsize=fontsize, fontweight=fontweight,
        color=text_color, transform=ax.transAxes, zorder=zorder + 1
    )


def draw_arrow(
    ax, x1, y1, x2, y2, color="#2563eb", style="->", lw=1.8,
    linestyle="solid", zorder=4, connectionstyle=None
):
    """Draw a styled connection arrow."""
    arrowprops = dict(
        arrowstyle=style,
        color=color,
        lw=lw,
        linestyle=linestyle,
        shrinkA=2,
        shrinkB=2,
    )
    if connectionstyle:
        arrowprops["connectionstyle"] = connectionstyle

    ax.annotate(
        "", xy=(x2, y2), xytext=(x1, y1),
        xycoords="axes fraction", textcoords="axes fraction",
        arrowprops=arrowprops, zorder=zorder
    )


def draw_sarvam_logo(ax, cx, cy, size=0.026, text="sarvam", zorder=4):
    """Draw the stylized Sarvam 'स' logo badge."""
    box = FancyBboxPatch(
        (cx - size / 2, cy - size / 2), size, size,
        boxstyle="round,pad=0.002",
        facecolor="#fdf4ff",
        edgecolor="#c084fc",
        linewidth=1.2,
        zorder=zorder,
        transform=ax.transAxes
    )
    ax.add_patch(box)
    ax.text(
        cx, cy + 0.002, "स",
        ha="center", va="center", fontsize=15.0, fontweight="bold",
        color="#7e22ce", transform=ax.transAxes, zorder=zorder + 1
    )
    if text:
        ax.text(
            cx, cy - size / 2 - 0.006, text,
            ha="center", va="top", fontsize=6.8, fontweight="bold",
            color="#581c87", transform=ax.transAxes, zorder=zorder + 1
        )


def draw_robot_icon(ax, cx, cy, size=0.020, zorder=4):
    """Draw a vector robot head icon."""
    w, h = size, size * 0.85
    head = FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0.002",
        facecolor="#e0f2fe",
        edgecolor="#0284c7",
        linewidth=1.2,
        zorder=zorder,
        transform=ax.transAxes
    )
    ax.add_patch(head)
    # Eyes
    ax.add_patch(Circle((cx - w * 0.22, cy), w * 0.08, facecolor="#0284c7", zorder=zorder + 1, transform=ax.transAxes))
    ax.add_patch(Circle((cx + w * 0.22, cy), w * 0.08, facecolor="#0284c7", zorder=zorder + 1, transform=ax.transAxes))
    # Antenna
    ax.plot([cx, cx], [cy + h / 2, cy + h / 2 + 0.005], color="#0284c7", lw=1.2, zorder=zorder, transform=ax.transAxes)
    ax.add_patch(Circle((cx, cy + h / 2 + 0.006), 0.0016, facecolor="#0284c7", zorder=zorder + 1, transform=ax.transAxes))


def draw_db_icon(ax, cx, cy, w=0.016, h=0.020, color="#3b82f6", zorder=4):
    """Draw a cylinder database icon."""
    ax.add_patch(Ellipse((cx, cy + h / 2), w, h * 0.35, facecolor="#dbeafe", edgecolor=color, lw=1.2, zorder=zorder + 1, transform=ax.transAxes))
    ax.add_patch(Rectangle((cx - w / 2, cy - h / 2), w, h, facecolor="#eff6ff", edgecolor=color, lw=1.2, zorder=zorder, transform=ax.transAxes))
    ax.add_patch(Ellipse((cx, cy - h / 2), w, h * 0.35, facecolor="#eff6ff", edgecolor=color, lw=1.2, zorder=zorder + 1, transform=ax.transAxes))


def draw_target_icon(ax, cx, cy, radius=0.011, zorder=4):
    """Draw a vector target/bullseye icon."""
    ax.add_patch(Circle((cx, cy), radius, facecolor="#fee2e2", edgecolor="#ef4444", lw=1.4, zorder=zorder, transform=ax.transAxes))
    ax.add_patch(Circle((cx, cy), radius * 0.65, facecolor="#ffffff", edgecolor="#ef4444", lw=1.2, zorder=zorder + 1, transform=ax.transAxes))
    ax.add_patch(Circle((cx, cy), radius * 0.30, facecolor="#ef4444", edgecolor="#ef4444", lw=1.0, zorder=zorder + 2, transform=ax.transAxes))


def draw_checkbox(ax, x, y, text, checked=True, zorder=4):
    """Draw a custom vector checkbox with text."""
    box_size = 0.008
    ax.add_patch(FancyBboxPatch(
        (x, y - box_size / 2), box_size, box_size,
        boxstyle="round,pad=0.001",
        facecolor="#f0fdf4" if checked else "#ffffff",
        edgecolor="#16a34a" if checked else "#94a3b8",
        linewidth=1.2,
        zorder=zorder,
        transform=ax.transAxes
    ))
    if checked:
        ax.text(
            x + box_size / 2, y, "v",
            ha="center", va="center", fontsize=6.8, fontweight="bold",
            color="#16a34a", transform=ax.transAxes, zorder=zorder + 1
        )
    ax.text(
        x + box_size + 0.005, y, text,
        ha="left", va="center", fontsize=7.2, color="#1e293b",
        transform=ax.transAxes, zorder=zorder + 1
    )


def draw_bipartite_graph(ax, x, y, w, h, zorder=3):
    """Draw the bipartite heterogeneous graph in Knowledge Layer with pure ASCII labels."""
    a_x = x + 0.025
    a_ys = [y + h * 0.75, y + h * 0.50, y + h * 0.25]
    a_labels = ["A1", "A2", "A22"]

    c_x = x + w - 0.025
    c_ys = [y + h * 0.75, y + h * 0.50, y + h * 0.25]
    c_labels = ["C1", "C2", "C1120"]

    # Edges
    ax.plot([a_x, c_x], [a_ys[0], c_ys[0]], color="#ef4444", lw=2.0, zorder=zorder, transform=ax.transAxes)
    ax.plot([a_x, c_x], [a_ys[1], c_ys[1]], color="#f97316", lw=1.8, zorder=zorder, transform=ax.transAxes)
    ax.plot([a_x, c_x], [a_ys[2], c_ys[2]], color="#94a3b8", lw=1.4, linestyle="dotted", zorder=zorder, transform=ax.transAxes)
    ax.plot([a_x, c_x], [a_ys[0], c_ys[1]], color="#ef4444", lw=1.4, alpha=0.7, zorder=zorder, transform=ax.transAxes)

    # Edge labels
    ax.text((a_x + c_x) / 2, a_ys[0] + 0.012, "verdict flip (success)", ha="center", va="bottom", fontsize=6.8, color="#dc2626", fontweight="bold", transform=ax.transAxes, zorder=zorder+1)
    ax.text((a_x + c_x) / 2, a_ys[1] + 0.010, "attempted (no flip)", ha="center", va="bottom", fontsize=6.8, color="#ea580c", fontweight="bold", transform=ax.transAxes, zorder=zorder+1)
    ax.text((a_x + c_x) / 2, a_ys[2] - 0.014, "judged out / no link", ha="center", va="top", fontsize=6.5, color="#64748b", transform=ax.transAxes, zorder=zorder+1)

    # Attack circles
    for ay, lab in zip(a_ys, a_labels):
        ax.add_patch(Circle((a_x, ay), 0.012, facecolor="#ffedd5", edgecolor="#ea580c", lw=1.4, zorder=zorder + 2, transform=ax.transAxes))
        ax.text(a_x, ay, lab, ha="center", va="center", fontsize=7.2, fontweight="bold", color="#c2410c", transform=ax.transAxes, zorder=zorder + 3)

    # Claim circles
    for cy, lab in zip(c_ys, c_labels):
        ax.add_patch(Circle((c_x, cy), 0.012, facecolor="#dbeafe", edgecolor="#2563eb", lw=1.4, zorder=zorder + 2, transform=ax.transAxes))
        ax.text(c_x, cy, lab, ha="center", va="center", fontsize=6.5, fontweight="bold", color="#1e40af", transform=ax.transAxes, zorder=zorder + 3)

    # Column titles
    ax.text(a_x, y + h + 0.005, "Attack\nnodes (22+)", ha="center", va="bottom", fontsize=7.2, fontweight="bold", color="#ea580c", transform=ax.transAxes)
    ax.text(c_x, y + h + 0.005, "Claim\nnodes (1,120)", ha="center", va="bottom", fontsize=7.2, fontweight="bold", color="#2563eb", transform=ax.transAxes)


def generate_master_diagram():
    fig, ax = plt.subplots(figsize=(26, 14.5), dpi=300)
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    # Background canvas
    ax.add_patch(Rectangle((0, 0), 1, 1, facecolor="#f8fafc", zorder=0, transform=ax.transAxes))

    # Master Title Banner
    ax.text(
        0.500, 0.988,
        "HAFT: End-to-End System Architecture & Adaptive Intelligence Layer",
        ha="center", va="top", fontsize=16.5, fontweight="bold", color="#0f172a", transform=ax.transAxes
    )
    ax.text(
        0.500, 0.968,
        "Devanagari Robustness Benchmarking (24,640 Evals)  |  Offline RL Attack Selector (K <= 5)  |  Inductive GraphSAGE Knowledge Graph",
        ha="center", va="top", fontsize=9.8, fontstyle="italic", color="#475569", transform=ax.transAxes
    )

    # =========================================================================
    # 1. PHASE 0: BASELINE STUDY (COMPLETED) [LEFT PANEL: x in 0.012..0.165]
    # =========================================================================
    draw_card(
        ax, 0.012, 0.315, 0.153, 0.635,
        bg_color="#f8fafc", border_color="#94a3b8",
        title="Phase 0 : Baseline Study", subtitle="(Completed)",
        border_style="dashed", border_width=1.8, title_size=10.0
    )

    # 1A. Dataset card
    draw_card(
        ax, 0.020, 0.745, 0.137, 0.165,
        bg_color="#ffffff", border_color="#cbd5e1",
        title="Hindi Claims Dataset", pad=0.006, title_size=9.0
    )
    draw_db_icon(ax, 0.033, 0.880, w=0.015, h=0.018, color="#2563eb")
    ax.text(
        0.026, 0.855,
        "• 1,120 Hindi Claims\n"
        "• 6 domains (Politics, Crime...)\n"
        "• Gold Verdict: SUP / REF / NEI\n"
        "• Inter-Annotator: 96.7% (k=0.946)\n"
        "• Clean Baseline Acc: 74.29%",
        fontsize=7.8, color="#1e293b", va="top", transform=ax.transAxes, zorder=3
    )

    draw_arrow(ax, 0.088, 0.745, 0.088, 0.680, color="#64748b", lw=2.0)

    # 1B. Run All 22 Attacks
    draw_card(
        ax, 0.020, 0.575, 0.137, 0.105,
        bg_color="#ede9fe", border_color="#8b5cf6",
        title="Run all 22 attacks\n(Exhaustive)", pad=0.006, title_size=8.8
    )
    ax.text(
        0.088, 0.598,
        "22 x 1,120 = 24,640\nevaluations",
        ha="center", va="center", fontsize=8.4, fontweight="bold", color="#5b21b6", transform=ax.transAxes, zorder=3
    )

    draw_arrow(ax, 0.088, 0.575, 0.088, 0.525, color="#64748b", lw=2.0)

    # 1C. Attack Knowledge Base
    draw_card(
        ax, 0.020, 0.325, 0.137, 0.200,
        bg_color="#ffffff", border_color="#cbd5e1",
        title="Attack Knowledge Base", pad=0.006, title_size=9.0
    )
    draw_db_icon(ax, 0.033, 0.495, w=0.016, h=0.020, color="#0284c7")
    ax.text(
        0.026, 0.470,
        "• Measured attack success rates\n"
        "  (ASR: 1.8% to 59.6%)\n"
        "• 24,640 results (claim, attack,\n"
        "  verifier verdict, judge decision)\n"
        "• IndicBERTv2 768-dim Embeds\n"
        "• Used for RL training & GNN",
        fontsize=7.6, color="#1e293b", va="top", transform=ax.transAxes, zorder=3
    )

    # Connection arrow from Phase 0 to Phase 1
    draw_arrow(ax, 0.157, 0.425, 0.174, 0.425, color="#2563eb", lw=2.2, linestyle="dashed")
    ax.text(
        0.165, 0.445, "trains RL\nand builds\ngraph",
        fontsize=7.2, fontweight="bold", color="#1d4ed8", ha="center", transform=ax.transAxes
    )

    # =========================================================================
    # 2. PHASE 1: ADAPTIVE MEASUREMENT (RL ATTACK SELECTOR) [CENTER: x in 0.174..0.772]
    # =========================================================================
    draw_card(
        ax, 0.174, 0.315, 0.598, 0.635,
        bg_color="#ffffff", border_color="#2563eb",
        title="Phase 1 : Adaptive Measurement (RL Attack Selector)",
        subtitle="·  Test smart, not everything   (Budget K <= 5 queries per claim | 77.27% Cost Reduction | Median 1.4 steps to flip)",
        border_width=2.2, title_size=11.0
    )

    # Top red feedback loop arrow: Reward r_t to RL Selector
    draw_arrow(
        ax, 0.725, 0.885, 0.370, 0.885,
        color="#e11d48", lw=2.0, linestyle="dashed"
    )
    ax.text(
        0.548, 0.895,
        "Reward r_t (success - cost) policy gradient feedback",
        fontsize=8.0, fontweight="bold", color="#be123c", ha="center", transform=ax.transAxes
    )
    draw_arrow(ax, 0.370, 0.885, 0.370, 0.865, color="#e11d48", lw=2.0, linestyle="dashed")

    # ---------------- Column 1: Input & State & Effective Attacks ----------------
    # 2A. Input Claim
    draw_card(
        ax, 0.184, 0.690, 0.114, 0.185,
        bg_color="#f0fdf4", border_color="#16a34a",
        title="Input : New Hindi Claim", pad=0.006, title_size=8.8
    )
    ax.text(
        0.190, 0.835,
        "\"प्रधानमंत्री मोदी ने 2024 में\n"
        "अयोध्या में नया हवाई अड्डा\n"
        "उद्घाटन किया।\"\n\n"
        "Domain: Politics\n"
        "Gold Verdict: SUP",
        fontsize=7.8, color="#14532d", va="top", transform=ax.transAxes, zorder=3
    )

    draw_arrow(ax, 0.241, 0.690, 0.241, 0.655, color="#16a34a", lw=2.0)

    # 2B. State s_t (859 dims -> 987 dims)
    draw_card(
        ax, 0.184, 0.410, 0.114, 0.245,
        bg_color="#eff6ff", border_color="#3b82f6",
        title="State s_t (859 dims)", pad=0.006, title_size=8.8
    )
    ax.text(
        0.190, 0.615,
        "• Claim embedding (768)\n"
        "• Tried attack mask (22)\n"
        "• Flip history (22)\n"
        "• Attack properties (44)\n"
        "• Progression ratio (3)\n"
        "+ GNN GraphSAGE (128)\n"
        "  = 987 dims (+4.22% flip)",
        fontsize=7.5, color="#1e3a8a", va="top", transform=ax.transAxes, zorder=3
    )

    # 2C. Effective Attacks Found (pill card)
    draw_card(
        ax, 0.184, 0.335, 0.114, 0.055,
        bg_color="#dcfce7", border_color="#16a34a",
        pad=0.004
    )
    ax.text(
        0.241, 0.362,
        "Effective attacks found\n(Median 1.4 calls, max 5)",
        ha="center", va="center", fontsize=7.2, fontweight="bold", color="#15803d", transform=ax.transAxes, zorder=3
    )

    # Curve arrow from State to RL Selector
    draw_arrow(ax, 0.298, 0.535, 0.315, 0.740, color="#2563eb", lw=2.0, connectionstyle="arc3,rad=-0.12")

    # ---------------- Column 2: RL Selector & Attack Candidates ----------------
    # 2D. RL Attack Selector
    draw_card(
        ax, 0.315, 0.680, 0.114, 0.185,
        bg_color="#e0f2fe", border_color="#0284c7",
        title="RL Attack Selector", pad=0.006, title_size=9.0
    )
    draw_robot_icon(ax, 0.372, 0.812, size=0.020)
    ax.text(
        0.372, 0.785,
        "pi_theta(a_t | s_t)\n"
        "2-Layer MLP (256 dims)\n"
        "Action Logit Masking\n"
        "(eps-greedy, eps=0.10)\n"
        "Early Stopping Rule",
        ha="center", va="top", fontsize=7.6, fontweight="bold", color="#0369a1", transform=ax.transAxes, zorder=3
    )

    # Arrow down: Action a_t to Candidates
    draw_arrow(ax, 0.372, 0.680, 0.372, 0.635, color="#0284c7", lw=2.2)
    ax.text(0.380, 0.655, "Action a_t\n(select attack)", fontsize=7.2, fontweight="bold", color="#0369a1", transform=ax.transAxes)

    # 2E. Attack Candidates (with colorful pills)
    draw_card(
        ax, 0.315, 0.375, 0.114, 0.260,
        bg_color="#fffbeb", border_color="#d97706",
        title="Attack Candidates (A_t)", pad=0.006, title_size=8.8
    )
    pills = [
        ("A1 ContextReplace (59.6%)", "#fee2e2", "#ef4444", "#991b1b"),
        ("A2 AdvAdd (58.5%)", "#dcfce7", "#22c55e", "#166534"),
        ("A3 Fact2Fiction (57.6%)", "#e0e7ff", "#6366f1", "#3730a3"),
        ("A4 FactMixing (55.8%)", "#fef3c7", "#f59e0b", "#92400e"),
        ("A5 OmissionGen (24.7%)", "#f3e8ff", "#a855f7", "#6b21a8"),
        ("A6 AdvTrigger (11.4%)", "#ccfbf1", "#14b8a6", "#115e59"),
        ("A7 CharSwapping (1.8%)", "#f1f5f9", "#94a3b8", "#475569"),
    ]
    py_start = 0.585
    for text, bg, border, tc in pills:
        draw_pill(ax, 0.320, py_start, 0.104, 0.022, text, bg, border, tc, fontsize=6.8)
        py_start -= 0.026
    ax.text(0.372, 0.388, "... (up to 22 attacks)", ha="center", va="center", fontsize=7.2, fontstyle="italic", color="#78350f", transform=ax.transAxes, zorder=3)

    # Arrow to Attack Generator
    draw_arrow(ax, 0.429, 0.485, 0.448, 0.485, color="#d97706", lw=2.0)

    # ---------------- Column 3: Attack Generator ----------------
    # 2F. Sarvam-2B (Attack Generation)
    draw_card(
        ax, 0.448, 0.395, 0.104, 0.220,
        bg_color="#faf5ff", border_color="#9333ea",
        pad=0.006
    )
    draw_sarvam_logo(ax, 0.500, 0.575, size=0.028, text="sarvam")
    ax.text(
        0.500, 0.525,
        "Sarvam-2B\n"
        "(Attack Generation)\n"
        "LoRA Fine-Tuned\n\n"
        "Generate adversarial\n"
        "claim using selected attack",
        ha="center", va="top", fontsize=7.5, color="#581c87", transform=ax.transAxes, zorder=3
    )

    # Arrow up-right to Fact Verifier
    draw_arrow(ax, 0.552, 0.485, 0.572, 0.740, color="#9333ea", lw=2.0, connectionstyle="arc3,rad=-0.12")
    ax.text(0.552, 0.615, "Adversarial\nClaim c'", fontsize=7.5, fontweight="bold", color="#6b21a8", ha="center", transform=ax.transAxes)

    # ---------------- Column 4: Fact Verifier & Quality Judge ----------------
    # 2G. Fact Verifier
    draw_card(
        ax, 0.572, 0.670, 0.100, 0.180,
        bg_color="#fef2f2", border_color="#ef4444",
        pad=0.006
    )
    draw_sarvam_logo(ax, 0.622, 0.815, size=0.026, text="sarvam")
    ax.text(
        0.622, 0.770,
        "(Fact Verification)\n"
        "Indic-NLI / Sarvam\n\n"
        "Verify claim against\n"
        "evidence  ->  REF",
        ha="center", va="top", fontsize=7.5, color="#991b1b", transform=ax.transAxes, zorder=3
    )

    # Arrow down to Quality Judge
    draw_arrow(ax, 0.622, 0.670, 0.622, 0.615, color="#ef4444", lw=2.0)

    # 2H. Quality Judge
    draw_card(
        ax, 0.572, 0.395, 0.100, 0.220,
        bg_color="#f0fdf4", border_color="#22c55e",
        title="Judge (LLM)", pad=0.006, title_size=8.8
    )
    ax.text(
        0.622, 0.560,
        "Meaning & Fluency Gate\n\n"
        "Check Hindi fluency\n"
        "(score >= 3) and\n"
        "meaning preservation\n"
        "(BERTScore >= 0.70)\n\n"
        "Judge: PASS / FAIL",
        ha="center", va="top", fontsize=7.3, color="#166534", transform=ax.transAxes, zorder=3
    )

    # Arrow to Step Result
    draw_arrow(ax, 0.672, 0.485, 0.692, 0.680, color="#16a34a", lw=2.0, connectionstyle="arc3,rad=-0.1")

    # ---------------- Column 5: Step Result & Reward Function ----------------
    # 2I. Step Result
    draw_card(
        ax, 0.688, 0.620, 0.076, 0.230,
        bg_color="#ffffff", border_color="#64748b",
        title="Step Result", pad=0.005, title_size=8.8
    )
    ax.text(
        0.694, 0.810,
        "Predicted: REF\n"
        "Gold:       SUP\n"
        "Verdict Flip:  [YES]\n"
        "Judge Pass:  [PASS]\n"
        "Success:       1\n"
        "API Cost:      c",
        fontsize=7.4, fontweight="bold", color="#0f172a", va="top", transform=ax.transAxes, zorder=3
    )

    draw_arrow(ax, 0.726, 0.620, 0.726, 0.580, color="#64748b", lw=2.0)

    # 2J. Reward Function
    draw_card(
        ax, 0.688, 0.375, 0.076, 0.205,
        bg_color="#fff1f2", border_color="#f43f5e",
        title="Reward r_t", pad=0.005, title_size=8.8
    )
    ax.text(
        0.694, 0.540,
        "r_t = {\n"
        " +10 - 0.1*t\n"
        "  (genuine flip)\n"
        " -0.1\n"
        "  (no flip cost)\n"
        " -1.0\n"
        "  (exhausted)",
        fontsize=7.2, fontweight="bold", color="#881337", va="top", transform=ax.transAxes, zorder=3
    )

    # Loop line to RL Selector
    draw_arrow(ax, 0.726, 0.580, 0.726, 0.885, color="#e11d48", lw=2.0, linestyle="dashed")

    # Bottom blue dashed feedback line: State update
    draw_arrow(
        ax, 0.688, 0.345, 0.298, 0.345,
        color="#2563eb", lw=1.8, linestyle="dashed"
    )
    ax.text(
        0.493, 0.355,
        "Update state s_{t+1} (add attack outcome, mask, counters) — Repeat until flip or K=5 attempts",
        fontsize=7.2, fontweight="bold", color="#1e40af", ha="center", transform=ax.transAxes
    )

    # =========================================================================
    # 3. PHASE 2: LLM COMPARISON (COMPLETED) [TOP-RIGHT: x in 0.780..0.988]
    # =========================================================================
    draw_card(
        ax, 0.780, 0.675, 0.208, 0.275,
        bg_color="#fffbeb", border_color="#f59e0b",
        title="Phase 2 : LLM Comparison (Completed)",
        border_style="dashed", border_width=1.8, title_size=9.8
    )
    ax.text(
        0.884, 0.920, "5 LLMs vs 24,640 Ground Truth Evaluations",
        ha="center", va="top", fontsize=7.8, fontstyle="italic", color="#78350f", transform=ax.transAxes
    )
    draw_pill(ax, 0.792, 0.888, 0.184, 0.022, "Models: DeepSeek · Sarvam · GPT-4o · Claude · Kimi", "#fef3c7", "#f59e0b", "#92400e", fontsize=7.0)
    ax.text(
        0.788, 0.865,
        "• DeepSeek-V3: 72.73% accuracy (top reasoning)\n"
        "• Sarvam AI (Indic): 40.91% accuracy (native Hindi)\n"
        "• GPT-4o: 27.27% | Claude 3.5: 27.27% | Kimi: 27.27%\n\n"
        "• Core Finding: 45.45% Model Disagreement Rate\n"
        "• Western Disconnect: Overestimated typos (predicted\n"
        "  POS on 1.8% flips); missed evidence tampering.",
        fontsize=7.6, color="#78350f", va="top", transform=ax.transAxes, zorder=3
    )

    # =========================================================================
    # 4. PHASE 3: CALIBRATED FEASIBILITY PREDICTION [MIDDLE-RIGHT: y in 0.315..0.665]
    # =========================================================================
    draw_card(
        ax, 0.780, 0.315, 0.208, 0.350,
        bg_color="#faf5ff", border_color="#a855f7",
        title="Phase 3 : Calibrated Prediction",
        border_width=2.0, title_size=9.8
    )
    ax.text(
        0.884, 0.635, "(for 31 unmeasured attacks)",
        ha="center", va="top", fontsize=7.8, fontstyle="italic", color="#581c87", transform=ax.transAxes
    )

    # 4A. Measured Examples Pill
    draw_pill(ax, 0.815, 0.598, 0.138, 0.022, "Measured examples (21)", "#f3e8ff", "#a855f7", "#581c87", fontsize=7.2)
    draw_arrow(ax, 0.884, 0.598, 0.884, 0.565, color="#a855f7", lw=1.8)

    # 4B. RL Exemplar Selector
    draw_card(
        ax, 0.788, 0.450, 0.192, 0.115,
        bg_color="#fff7ed", border_color="#ea580c",
        title="RL Exemplar Selector (Ours)", pad=0.005, title_size=8.6
    )
    ax.text(
        0.794, 0.528,
        "• 22-Fold Leave-One-Out (LOO) In-Fold Policy Gradient\n"
        "• 95.45% LOO Accuracy (21 / 22 correctly predicted)\n"
        "• 52.4% Prompt Token Reduction (9.9 vs 21 exemplars)\n"
        "• Macro-F1: 0.952 across all feasibility tiers",
        fontsize=7.2, color="#7c2d12", va="top", transform=ax.transAxes, zorder=3
    )

    draw_arrow(ax, 0.884, 0.450, 0.884, 0.425, color="#ea580c", lw=1.8)

    # 4C. Sarvam-2B fine-tuned banner
    draw_card(
        ax, 0.788, 0.395, 0.192, 0.030,
        bg_color="#fdf4ff", border_color="#c084fc",
        pad=0.002
    )
    draw_sarvam_logo(ax, 0.805, 0.410, size=0.016, text="")
    ax.text(
        0.820, 0.410, "Sarvam-2B (LoRA fine-tuned) replaces few-shot prompting",
        fontsize=7.0, fontweight="bold", color="#581c87", va="center", transform=ax.transAxes
    )

    # 4D. 31 Unmeasured Survey Attacks predicted tiers
    ax.text(
        0.884, 0.380, "Predicted tier for 31 unmeasured attacks",
        ha="center", va="top", fontsize=7.4, fontweight="bold", color="#3b0764", transform=ax.transAxes
    )
    # Tier badges
    draw_pill(ax, 0.795, 0.330, 0.052, 0.024, "POS (>40%)", "#dcfce7", "#22c55e", "#15803d", fontsize=6.8)
    draw_pill(ax, 0.852, 0.330, 0.056, 0.024, "MID (15-40%)", "#fef3c7", "#f59e0b", "#92400e", fontsize=6.8)
    draw_pill(ax, 0.913, 0.330, 0.052, 0.024, "NEG (<15%)", "#fee2e2", "#ef4444", "#991b1b", fontsize=6.8)

    # =========================================================================
    # 5. KNOWLEDGE LAYER (STAGE 2) [BOTTOM PANEL: y in 0.088..0.298]
    # =========================================================================
    draw_card(
        ax, 0.012, 0.088, 0.976, 0.210,
        bg_color="#f0fdfa", border_color="#059669",
        title="Knowledge Layer (Stage 2) — Attack–Claim Bipartite Graph + Inductive GraphSAGE GNN",
        border_style="dashed", border_width=2.0, title_size=10.5
    )
    ax.text(
        0.500, 0.268,
        "Structural Relational Modeling across 1,120 Claims and 22 Attacks (49,364 Directed Edges)",
        ha="center", va="top", fontsize=8.0, fontstyle="italic", color="#065f46", transform=ax.transAxes
    )

    # 5A. Graph Construction (with visual bipartite graph!)
    draw_card(
        ax, 0.020, 0.098, 0.185, 0.150,
        bg_color="#ffffff", border_color="#10b981",
        title="Graph Construction", pad=0.006, title_size=8.8
    )
    draw_bipartite_graph(ax, 0.025, 0.135, 0.175, 0.072)
    ax.text(
        0.112, 0.108,
        "1,142 nodes · 49,364 directed edges\nClaims: 777-dim feat | Attacks: 16-dim feat",
        ha="center", va="center", fontsize=7.2, fontweight="bold", color="#065f46", transform=ax.transAxes
    )

    draw_arrow(ax, 0.205, 0.173, 0.222, 0.173, color="#059669", lw=2.2)

    # 5B. Vectorized Inductive GNN
    draw_card(
        ax, 0.222, 0.098, 0.215, 0.150,
        bg_color="#ffffff", border_color="#0284c7",
        title="GNN (message passing over graph)", pad=0.006, title_size=8.8
    )
    ax.text(
        0.230, 0.212,
        "• GraphSAGE (Ours): Mean neighborhood aggregation\n"
        "  h_v = ReLU(W_self*h_v + W_neigh*Mean(h_N) + b)\n"
        "• GAT (Attention): Multi-head attention (over-smoothing)\n"
        "• Edge split: 80% train / 20% test cold-start inductive",
        fontsize=7.4, color="#075985", va="top", transform=ax.transAxes, zorder=3
    )
    # Plain MLP baseline ablation box
    draw_card(
        ax, 0.230, 0.106, 0.199, 0.036,
        bg_color="#f8fafc", border_color="#94a3b8",
        border_style="dashed", pad=0.003
    )
    ax.text(
        0.329, 0.124,
        "Plain MLP baseline (ablation)\nattack attributes + claim embedding (no graph structure)",
        ha="center", va="center", fontsize=6.8, color="#475569", transform=ax.transAxes, zorder=3
    )

    draw_arrow(ax, 0.437, 0.173, 0.455, 0.173, color="#0284c7", lw=2.2)

    # 5C. Link Prediction
    draw_card(
        ax, 0.455, 0.098, 0.235, 0.150,
        bg_color="#ffffff", border_color="#0284c7",
        title="Link Prediction Performance", pad=0.006, title_size=8.8
    )
    ax.text(
        0.463, 0.212,
        "Would attack a succeed on claim c? (including new attacks)\n\n"
        "• GraphSAGE (Ours):   AUROC 0.865 | AUPRC 0.482\n"
        "• Plain MLP Baseline:  AUROC 0.862 | AUPRC 0.483\n"
        "• Attack Mean ASR:     AUROC 0.877 | AUPRC 0.329\n"
        "• Attribute-kNN:           AUROC 0.739 | AUPRC 0.188\n"
        "• GAT (Attention):        AUROC 0.355 (over-smoothing)",
        fontsize=7.4, fontweight="bold", color="#0369a1", va="top", transform=ax.transAxes, zorder=3
    )

    # Upward Arrow from GNN up to State s_t (clean straight line through channel)
    draw_arrow(
        ax, 0.255, 0.248, 0.255, 0.335,
        color="#0284c7", lw=2.2, linestyle="dashed"
    )
    ax.text(
        0.260, 0.290,
        "graph embeddings\n(upgrades RL state: +4.22% flip)",
        fontsize=7.2, fontweight="bold", color="#0284c7", ha="left", va="center", transform=ax.transAxes
    )

    # Upward Arrow from Knowledge Layer to Phase 3 (clean line through channel)
    draw_arrow(
        ax, 0.884, 0.248, 0.884, 0.315,
        color="#0284c7", lw=2.2, linestyle="dashed"
    )
    ax.text(
        0.890, 0.280,
        "link prediction\n(second path for Phase C)",
        fontsize=7.2, fontweight="bold", color="#0284c7", ha="left", va="center", transform=ax.transAxes
    )

    draw_arrow(ax, 0.690, 0.173, 0.708, 0.173, color="#059669", lw=2.2)

    # 5D. A brand-new attack enters (any time) - 5 discrete step boxes!
    draw_card(
        ax, 0.708, 0.098, 0.272, 0.150,
        bg_color="#f0fdf4", border_color="#16a34a",
        title="A brand-new attack enters (any time)", pad=0.006, title_size=8.8
    )
    steps = [
        ("Identify\n(features)", "#ffffff"),
        ("Insert\n(to graph)", "#ffffff"),
        ("Predict\n(POS/MID)", "#ffffff"),
        ("Verify\n(sample)", "#ffffff"),
        ("Update\n(edges)", "#ffffff"),
    ]
    sx = 0.716
    for i, (stext, sbg) in enumerate(steps):
        draw_card(ax, sx, 0.143, 0.045, 0.045, sbg, "#16a34a", pad=0.002, border_width=1.0)
        ax.text(sx + 0.0225, 0.165, stext, ha="center", va="center", fontsize=6.8, fontweight="bold", color="#15803d", transform=ax.transAxes, zorder=4)
        if i < len(steps) - 1:
            draw_arrow(ax, sx + 0.045, 0.165, sx + 0.054, 0.165, color="#16a34a", lw=1.6)
        sx += 0.054

    ax.text(
        0.844, 0.116,
        "The GNN generalizes to unseen attacks and claims,\nand improves over time without full retraining.",
        ha="center", va="center", fontsize=7.2, fontstyle="italic", color="#166534", transform=ax.transAxes
    )

    # =========================================================================
    # 6. BOTTOM BANNER: FINAL OUTPUT & GOAL [y in 0.012..0.076]
    # =========================================================================
    draw_card(
        ax, 0.012, 0.012, 0.976, 0.064,
        bg_color="#ffffff", border_color="#cbd5e1",
        pad=0.004
    )

    # Output header badge
    draw_pill(ax, 0.020, 0.028, 0.088, 0.032, "FINAL OUTPUT\n(for each claim)", "#eff6ff", "#3b82f6", "#1d4ed8", fontsize=7.0)

    # Multi-column Checkboxes
    col1 = [
        "Baseline verdict (SUP / REF / NEI)",
        "Up to 5 selected attacks (instead of 22)",
    ]
    col2 = [
        "Which attacks caused gated flips",
        "GNN vs plain-MLP outcome (77.3% saved)",
    ]
    col3 = [
        "Predicted POS / MID / NEG for 31 unmeasured attacks",
        "API cost: 1.4 median calls instead of 22",
    ]
    col4 = [
        "How the system reached the result (explainable)",
        "Zero-shot feasibility prior for unseen attacks",
    ]

    for i, line in enumerate(col1):
        draw_checkbox(ax, 0.118, 0.054 - i * 0.022, line)
    for i, line in enumerate(col2):
        draw_checkbox(ax, 0.285, 0.054 - i * 0.022, line)
    for i, line in enumerate(col3):
        draw_checkbox(ax, 0.468, 0.054 - i * 0.022, line)
    for i, line in enumerate(col4):
        draw_checkbox(ax, 0.690, 0.054 - i * 0.022, line)

    # Goal box on the far right
    draw_card(
        ax, 0.865, 0.016, 0.115, 0.056,
        bg_color="#f0fdf4", border_color="#16a34a",
        pad=0.003
    )
    draw_target_icon(ax, 0.880, 0.044, radius=0.010)
    ax.text(
        0.898, 0.044,
        "GOAL\nRobust, efficient, scalable\nadversarial fact-checking for Hindi",
        fontsize=6.8, fontweight="bold", color="#166534", va="center", transform=ax.transAxes
    )

    # Save to all requested locations
    out1 = os.path.join(BASE_DIR, "results", "stage2", "figures", "attack_diagram_updated.png")
    out2 = os.path.join(BASE_DIR, "results", "stage2", "figures", "fig1_framework_architecture.png")
    out3 = os.path.join(os.path.dirname(BASE_DIR), "attack_docs", "attack_diagram_updated.png")

    os.makedirs(os.path.dirname(out1), exist_ok=True)
    os.makedirs(os.path.dirname(out3), exist_ok=True)

    plt.tight_layout()
    plt.savefig(out1, dpi=300, bbox_inches="tight")
    plt.savefig(out2, dpi=300, bbox_inches="tight")
    plt.savefig(out3, dpi=300, bbox_inches="tight")
    plt.close()

    print("Master diagram successfully generated at:")
    print(f"  1. {out1}")
    print(f"  2. {out2}")
    print(f"  3. {out3}")


if __name__ == "__main__":
    generate_master_diagram()
