#!/usr/bin/env python3
"""Simula realocacao de demanda sob restricao de capacidade na rede aeroportuaria.

Modelo (adaptado de Cumelles, Lordan & Sallan, 2021): ao fechar um aeroporto, sua
demanda de passageiros e realocada para as alternativas geograficamente mais proximas
que ainda tenham capacidade disponivel. Cada aeroporto tem capacidade
C_i = (1 + alpha) * L_i, onde L_i e a demanda (passageiros embarcados + desembarcados)
e alpha e a folga operacional. A realocacao preenche primeiro os aeroportos mais
proximos com capacidade residual; a demanda que nao encontra alternativa viavel e
contabilizada como demanda nao realocada (stranded). Aeroportos que atingem a
capacidade tornam-se gargalos (saturados).

Entradas:
- resultados/grafo_aeroportuario_2025.json
- resultados/ranking_criticidade_2025.csv
- resultados/aeroportos_2025.csv

Saidas:
- resultados/simulacao_cascata_capacidade_2025.csv   (detalhe para alpha de referencia)
- resultados/resumo_cascata_capacidade_2025.txt      (varredura de alpha)
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simular_falhas_rede import carregar_grafo, componentes, remover_nos  # noqa: E402
from mapa_html import COORDS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RESULTADOS_DIR = ROOT / "resultados"
RANKING_PATH = RESULTADOS_DIR / "ranking_criticidade_2025.csv"
AEROPORTOS_PATH = RESULTADOS_DIR / "aeroportos_2025.csv"

ALPHA_REFERENCIA = 0.2
ALPHAS_VARREDURA = [0.1, 0.2, 0.5, 1.0]


def carregar_ordem_ranking() -> list[str]:
    with RANKING_PATH.open(encoding="utf-8") as f:
        return [linha["codigo"] for linha in csv.DictReader(f)]


def carregar_demanda() -> dict[str, float]:
    """Demanda de cada aeroporto = passageiros embarcados + desembarcados (throughput O/D)."""
    demanda: dict[str, float] = {}
    with AEROPORTOS_PATH.open(encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            emb = float(linha.get("passageiros_embarcados", 0) or 0)
            des = float(linha.get("passageiros_desembarcados", 0) or 0)
            demanda[linha["codigo"]] = emb + des
    return demanda


def haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = a
    lat2, lon2 = b
    raio = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    h = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * raio * math.asin(math.sqrt(h))


def realocar_demanda(
    adj0: dict[str, dict[str, int]],
    demanda0: dict[str, float],
    coords: dict[str, tuple[float, float]],
    removidos: list[str],
    alpha: float,
) -> dict[str, object]:
    """Realoca a demanda dos aeroportos fechados para as alternativas proximas.

    alpha = inf => capacidade infinita: toda demanda com algum destino viavel e absorvida.
    """
    infinita = math.isinf(alpha)
    capacidade = {
        no: (math.inf if infinita else (1 + alpha) * demanda0.get(no, 0.0))
        for no in adj0
    }
    ocupacao = dict(demanda0)
    vivos = set(adj0) - set(removidos)
    saturados: list[str] = []
    nao_realocada = 0.0

    for fechado in removidos:
        a_realocar = demanda0.get(fechado, 0.0)
        if fechado not in coords:
            nao_realocada += a_realocar
            continue
        cand = sorted(
            (v for v in vivos if v in coords),
            key=lambda v: haversine(coords[fechado], coords[v]),
        )
        for v in cand:
            if a_realocar <= 1e-6:
                break
            residual = capacidade[v] - ocupacao[v]
            if residual <= 0:
                continue
            usado = min(residual, a_realocar)
            ocupacao[v] += usado
            a_realocar -= usado
            if not infinita and ocupacao[v] >= capacidade[v] - 1e-6 and v not in saturados:
                saturados.append(v)
        nao_realocada += a_realocar

    return {"vivos": vivos, "saturados": saturados, "nao_realocada": nao_realocada}


def simular_ataque_cascata(
    adj0: dict[str, dict[str, int]],
    demanda0: dict[str, float],
    coords: dict[str, tuple[float, float]],
    ordem: list[str],
    limite: int,
    alpha: float,
) -> list[dict[str, object]]:
    """Remove aeroportos na ordem do ranking; a cada passo realoca a demanda acumulada."""
    total_nos = len(adj0)
    demanda_total = sum(demanda0.values()) or 1.0
    linhas = []
    for k in range(1, limite + 1):
        removidos = ordem[:k]
        res = realocar_demanda(adj0, demanda0, coords, removidos, alpha)
        adj = remover_nos(adj0, set(removidos))
        comps = componentes(adj)
        maior = comps[0] if comps else []
        linhas.append(
            {
                "passo": k,
                "aeroporto_removido": ordem[k - 1],
                "alpha": alpha,
                "aeroportos_removidos": k,
                "aeroportos_saturados": len(res["saturados"]),
                "maior_componente": len(maior),
                "fracao_maior_componente": len(maior) / total_nos if total_nos else 0,
                "passageiros_nao_realocados": round(res["nao_realocada"]),
                "fracao_demanda_nao_realocada": res["nao_realocada"] / demanda_total,
            }
        )
    return linhas


def escrever_csv(path: Path, linhas: list[dict[str, object]]) -> None:
    if not linhas:
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        escritor.writeheader()
        escritor.writerows(linhas)


def main() -> None:
    adj, _ = carregar_grafo()
    ordem = carregar_ordem_ranking()
    demanda = carregar_demanda()
    limite = min(30, len(adj))

    detalhe = simular_ataque_cascata(adj, demanda, COORDS, ordem, limite, ALPHA_REFERENCIA)
    escrever_csv(RESULTADOS_DIR / "simulacao_cascata_capacidade_2025.csv", detalhe)

    passo_ref = min(10, limite)
    with (RESULTADOS_DIR / "resumo_cascata_capacidade_2025.txt").open(
        "w", encoding="utf-8"
    ) as f:
        f.write("Resumo da realocacao de demanda sob capacidade - 2025\n")
        f.write("=" * 60 + "\n\n")
        f.write("Modelo: Cumelles, Lordan & Sallan (2021) - realocacao para as\n")
        f.write("alternativas mais proximas com capacidade disponivel.\n")
        f.write("Capacidade C = (1 + alpha) * demanda inicial (embarcados + desembarcados).\n\n")
        f.write(f"Aeroportos na rede: {len(adj)}\n")
        f.write(f"Demanda total: {round(sum(demanda.values())):,} passageiros\n")
        f.write(f"Passos de ataque por cenario: {limite}\n\n")
        f.write(f"Varredura de alpha (estado no passo {passo_ref}):\n")
        f.write(
            f"{'alpha':>7} | {'saturados':>9} | {'maior comp':>10} | "
            f"{'nao realocados':>15} | {'% demanda':>9}\n"
        )
        f.write("-" * 62 + "\n")
        for alpha in ALPHAS_VARREDURA:
            linhas = simular_ataque_cascata(adj, demanda, COORDS, ordem, limite, alpha)
            r = linhas[passo_ref - 1]
            f.write(
                f"{alpha:>7.1f} | {r['aeroportos_saturados']:>9} | "
                f"{r['maior_componente']:>10} | "
                f"{r['passageiros_nao_realocados']:>15,} | "
                f"{r['fracao_demanda_nao_realocada']:>8.1%}\n"
            )
        f.write(
            "\nQuanto menor o alpha (menos folga de capacidade), mais aeroportos\n"
            "saturam e maior a demanda de passageiros que nao encontra realocacao viavel.\n"
        )

    print("Realocacao sob capacidade concluida.")
    print(f"Detalhe (alpha={ALPHA_REFERENCIA}): "
          f"{RESULTADOS_DIR / 'simulacao_cascata_capacidade_2025.csv'}")
    print(f"Resumo: {RESULTADOS_DIR / 'resumo_cascata_capacidade_2025.txt'}")


if __name__ == "__main__":
    main()
