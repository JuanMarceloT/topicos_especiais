#!/usr/bin/env python3
"""Analise de sensibilidade do score de criticidade aos pesos.

O score adotado e a media simples dos tres componentes (pesos iguais 1/3).
Este script recalcula o ranking sob perturbacoes dos pesos (enfatizando cada
componente) e reporta a estabilidade do top-10 (intersecao e Jaccard com o
ranking base de pesos iguais), mostrando que o resultado nao depende da escolha
exata dos pesos. Le apenas resultados/ranking_criticidade_2025.csv.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RANKING_PATH = ROOT / "resultados" / "ranking_criticidade_2025.csv"

PESOS_BASE = (1 / 3, 1 / 3, 1 / 3)
PERTURBACOES = [
    ("base", 1 / 3, 1 / 3, 1 / 3),
    ("+BC", 0.50, 0.25, 0.25),
    ("+DC", 0.25, 0.50, 0.25),
    ("+Vol", 0.25, 0.25, 0.50),
    ("0,45/0,30/0,25", 0.45, 0.30, 0.25),
    ("0,40/0,30/0,30", 0.40, 0.30, 0.30),
]


def carregar() -> list[dict]:
    with RANKING_PATH.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def top10(rows: list[dict], wb: float, wd: float, wv: float) -> list[str]:
    max_log = math.log1p(max(float(r["grau_ponderado_passageiros"]) for r in rows))

    def score(r: dict) -> float:
        bc = float(r["betweenness_centrality"])
        dc = float(r["degree_centrality"])
        vol = math.log1p(float(r["grau_ponderado_passageiros"])) / max_log
        return wb * bc + wd * dc + wv * vol

    return [r["codigo"] for r in sorted(rows, key=score, reverse=True)[:10]]


def main() -> None:
    rows = carregar()
    base = top10(rows, *PESOS_BASE)

    print("Sensibilidade do score de criticidade aos pesos (BC/DC/Vol)")
    print("=" * 60)
    print(f"Top-10 base ({PESOS_BASE[0]:.2f}/{PESOS_BASE[1]:.2f}/{PESOS_BASE[2]:.2f}): "
          f"{', '.join(base)}\n")
    print(f"{'perturbacao':>12} | {'pesos':>16} | {'#1':>4} | {'no top-10':>9} | {'Jaccard':>7}")
    print("-" * 60)
    for nome, wb, wd, wv in PERTURBACOES:
        t = top10(rows, wb, wd, wv)
        inter = len(set(base) & set(t))
        jac = inter / len(set(base) | set(t))
        print(f"{nome:>12} | {wb:.2f}/{wd:.2f}/{wv:.2f} | {t[0]:>4} | "
              f"{inter:>7}/10 | {jac:>7.2f}")


if __name__ == "__main__":
    main()
