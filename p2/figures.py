"""Report figures from the frozen analysis outputs (no recomputation of any estimate).

  python3 p2/figures.py --core results/main_analysis [--rep results/rep_analysis] --out ../report/figures

Writes PNG and SVG per figure:
  fig1_e1_crossing   O1 by explorer and peer model, Wilson 95% CIs, x/n labelled
  fig2_e2_core       O1 in every core E2 arm (Claude Sonnet 5 recipient)
  fig3_rep           O1 for REQ_plain and INFO per replication recipient (with --rep)
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BLUE, ORANGE, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "savefig.dpi": 200})
MODEL = {"R": "Gemini 3.1 Pro", "C": "Claude Sonnet 5"}


def cells(core: Path) -> dict[str, dict]:
    return {r["cell"]: r for r in csv.DictReader((core / "cells.csv").open())}


def point(ax, x, r, color, label=None):
    o, lo, hi = float(r["o1"]), float(r["o1_ci_lo"]), float(r["o1_ci_hi"])
    ax.errorbar(x, 100 * o, yerr=[[100 * max(0.0, o - lo)], [100 * max(0.0, hi - o)]], fmt="o", ms=7, color=color,
                ecolor=color, elinewidth=2, capsize=4, label=label, zorder=3)
    ax.annotate(f"{r['disabled']}/{r['scored']}", (x, 100 * hi), textcoords="offset points", xytext=(0, 5),
                ha="center", fontsize=8.5, color=MUTED)


def style(ax, ylabel="Script disabled at endpoint (%)"):
    ax.set_ylim(-3, 105)
    ax.set_ylabel(ylabel)
    ax.yaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)


def save(fig, out: Path, name: str):
    out.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(out / f"{name}.{ext}", bbox_inches="tight")
    plt.close(fig)


def fig1(c: dict, out: Path):
    fig, ax = plt.subplots(figsize=(5.6, 3.8))
    for i, peer in enumerate("RC"):
        for j, (exp, color) in enumerate((("R", BLUE), ("C", ORANGE))):
            point(ax, i + (j - 0.5) * 0.28, c[f"e1_{exp}x{peer}"], color,
                  label=f"Explorer: {MODEL[exp]}" if i == 0 else None)
    ax.set_xticks([0, 1], [f"Peer: {MODEL['R']}", f"Peer: {MODEL['C']}"])
    ax.set_xlim(-0.6, 1.6)
    style(ax)
    ax.legend(frameon=False, loc="upper right", fontsize=9)
    ax.set_title("E1: live explorer × privileged peer", loc="left", fontsize=11, color=INK)
    save(fig, out, "fig1_e1_crossing")


def fig2(c: dict, core: Path, out: Path):
    arms = [("e2_REQ_plain_r0", "REQ\nno rule"), ("e2_INFO_r0", "INFO\nno rule"), ("e2_CONTACT_r0", "CONTACT\nno rule"),
            ("e2_REQ_plain_r1", "REQ\nrule"), ("e2_INFO_r1", "INFO\nrule")]
    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    for i, (cell, _) in enumerate(arms):
        point(ax, i, c[cell], BLUE)
    ax.set_xticks(range(len(arms)), [a for _, a in arms])
    style(ax)
    ax.set_ylim(-3, 40)
    ax.set_title("E2: scripted message to Claude Sonnet 5", loc="left", fontsize=11, color=INK)
    e2 = next(k for k in json.loads((core / "analysis.json").read_text())["contrasts"] if k["name"] == "E2")["main"]
    ax.text(0.98, 0.95, f"REQ − INFO, no rule (primary): {100 * e2['estimate']:+.1f} pp "
            f"[{100 * e2['ci'][0]:.1f}, {100 * e2['ci'][1]:.1f}]", transform=ax.transAxes, ha="right", va="top",
            fontsize=8.5, color=INK)
    save(fig, out, "fig2_e2_core")


def fig3(rep: Path, out: Path):
    """Left: O1 per arm with Wilson CIs. Right: REQ - INFO with Newcombe CIs (the tested contrast)."""
    res = json.loads((rep / "analysis.json").read_text())
    arms = {(a["recipient"], a["arm"]): a for a in res["arms"]}
    con = {c["recipient"]: c for c in res["contrasts"]}
    names = {t: c["model"].split("/")[1] for t, c in con.items()}
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(9.4, 3.6), gridspec_kw={"width_ratios": [1.25, 1]})
    for i, t in enumerate(names):
        for j, (arm, color) in enumerate((("REQ_plain", BLUE), ("INFO", ORANGE))):
            a = arms[t, arm]
            r = {"o1": a["o1"] or 0, "o1_ci_lo": a["o1_ci"][0], "o1_ci_hi": a["o1_ci"][1],
                 "disabled": a["disabled"], "scored": a["scored"]}
            point(ax, i + (j - 0.5) * 0.28, r, color, label=("REQ (request)" if arm == "REQ_plain" else "INFO")
                  if i == 0 else None)
    ax.set_xticks(range(len(names)), list(names.values()), fontsize=8.5)
    style(ax)
    ax.legend(frameon=False, loc="upper right", fontsize=8.5)
    ax.set_title("O1 per arm (500 episodes each)", loc="left", fontsize=10.5, color=INK)
    for i, t in enumerate(names):
        m = con[t]["main"]
        est, lo, hi = 100 * m["estimate"], 100 * m["ci"][0], 100 * m["ci"][1]
        bx.errorbar(est, i, xerr=[[est - lo], [hi - est]], fmt="o", ms=7, color=INK, elinewidth=2, capsize=4)
        bx.annotate(f"{est:+.1f} [{lo:.1f}, {hi:.1f}]", (hi, i), textcoords="offset points", xytext=(6, -3),
                    fontsize=8.5, color=MUTED)
    bx.axvline(0, color=MUTED, lw=1)
    bx.set_yticks(range(len(names)), list(names.values()), fontsize=8.5)
    bx.set_ylim(len(names) - 0.5, -0.5)
    bx.set_xlim(-45, 50)
    bx.set_xlabel("REQ − INFO (pp, Newcombe 95% CI)")
    bx.xaxis.grid(True, color=GRID, lw=0.8)
    bx.set_axisbelow(True)
    bx.set_title("Effect of the request sentence", loc="left", fontsize=10.5, color=INK)
    fig.tight_layout()
    save(fig, out, "fig3_rep")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--core", required=True)
    ap.add_argument("--rep")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    c = cells(Path(a.core))
    fig1(c, Path(a.out))
    fig2(c, Path(a.core), Path(a.out))
    if a.rep:
        fig3(Path(a.rep), Path(a.out))


if __name__ == "__main__":
    main()
