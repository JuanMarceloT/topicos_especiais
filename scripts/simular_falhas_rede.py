#!/usr/bin/env python3
"""Simula falhas na rede aeroportuaria modelada.

Entradas esperadas:
- resultados/grafo_aeroportuario_2025.json
- resultados/ranking_criticidade_2025.csv  (somente para ataque estatico)

Saidas:
- resultados/simulacao_ataque_direcionado_2025.csv   (estatico)
- resultados/simulacao_ataque_adaptativo_2025.csv    (adaptativo)
- resultados/simulacao_falha_aleatoria_2025.csv
- resultados/resumo_simulacao_falhas_2025.txt
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import defaultdict, deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from metricas_grafo import (  # noqa: E402
    PESOS_PADRAO,
    PesosInput,
    betweenness_nao_ponderada,
    calcular_scores,
    carregar_pesos,
    formatar_formula_pesos,
    normalizar_pesos,
    parsear_pesos,
    ranking_por_score,
    salvar_pesos,
)


ROOT = Path(__file__).resolve().parents[1]
RESULTADOS_DIR = ROOT / "resultados"
GRAFO_PATH = RESULTADOS_DIR / "grafo_aeroportuario_2025.json"
RANKING_PATH = RESULTADOS_DIR / "ranking_criticidade_2025.csv"


def carregar_grafo() -> tuple[dict[str, dict[str, int]], dict[str, dict[str, str]]]:
    with GRAFO_PATH.open("r", encoding="utf-8") as f:
        grafo = json.load(f)

    aeroportos = {node["id"]: node for node in grafo["nodes"]}
    adj: dict[str, dict[str, int]] = defaultdict(dict)
    for node_id in aeroportos:
        adj[node_id] = {}
    for edge in grafo["edges"]:
        origem = edge["source"]
        destino = edge["target"]
        peso = int(edge["weight"])
        adj[origem][destino] = peso
        adj[destino][origem] = peso
    return dict(adj), aeroportos


def carregar_ranking() -> list[str]:
    with RANKING_PATH.open("r", encoding="utf-8") as f:
        leitor = csv.DictReader(f)
        return [linha["codigo"] for linha in leitor]


def remover_nos(adj_original: dict[str, dict[str, int]], removidos: set[str]) -> dict[str, dict[str, int]]:
    adj = {}
    for no, vizinhos in adj_original.items():
        if no in removidos:
            continue
        adj[no] = {vizinho: peso for vizinho, peso in vizinhos.items() if vizinho not in removidos}
    return adj


def componentes(adj: dict[str, dict[str, int]]) -> list[list[str]]:
    visitados: set[str] = set()
    resultado: list[list[str]] = []
    for no in adj:
        if no in visitados:
            continue
        fila = deque([no])
        visitados.add(no)
        comp = []
        while fila:
            atual = fila.popleft()
            comp.append(atual)
            for vizinho in adj[atual]:
                if vizinho not in visitados:
                    visitados.add(vizinho)
                    fila.append(vizinho)
        resultado.append(sorted(comp))
    return sorted(resultado, key=len, reverse=True)


def volume_restante(adj: dict[str, dict[str, int]]) -> int:
    total = 0
    vistos: set[tuple[str, str]] = set()
    for origem, vizinhos in adj.items():
        for destino, peso in vizinhos.items():
            chave = tuple(sorted((origem, destino)))
            if chave in vistos:
                continue
            vistos.add(chave)
            total += peso
    return total


def metricas_estado(
    adj_original: dict[str, dict[str, int]],
    removidos_ordenados: list[str],
    passo: int,
    aeroporto_removido: str,
    total_nos_original: int,
    total_volume_original: int,
    score_no_passo: float | None = None,
) -> dict[str, object]:
    removidos = set(removidos_ordenados)
    adj = remover_nos(adj_original, removidos)
    comps = componentes(adj)
    maior = comps[0] if comps else []
    isolados = sorted([comp[0] for comp in comps if len(comp) == 1])
    volume = volume_restante(adj)

    linha: dict[str, object] = {
        "passo": passo,
        "aeroporto_removido": aeroporto_removido,
        "removidos_acumulados": "|".join(removidos_ordenados),
        "qtd_removidos": len(removidos),
        "aeroportos_restantes": len(adj),
        "componentes_conectados": len(comps),
        "maior_componente": len(maior),
        "fracao_maior_componente": len(maior) / total_nos_original if total_nos_original else 0,
        "aeroportos_isolados": len(isolados),
        "lista_aeroportos_isolados": "|".join(isolados),
        "volume_passageiros_restante": volume,
        "fracao_volume_restante": volume / total_volume_original if total_volume_original else 0,
    }
    if score_no_passo is not None:
        linha["score_no_passo"] = score_no_passo
    return linha


def simular_ordem(
    adj_original: dict[str, dict[str, int]],
    ordem: list[str],
    limite: int,
) -> list[dict[str, object]]:
    total_nos_original = len(adj_original)
    total_volume_original = volume_restante(adj_original)
    removidos: list[str] = []
    linhas = []

    for passo, aeroporto in enumerate(ordem[:limite], start=1):
        removidos.append(aeroporto)
        linhas.append(
            metricas_estado(
                adj_original=adj_original,
                removidos_ordenados=removidos,
                passo=passo,
                aeroporto_removido=aeroporto,
                total_nos_original=total_nos_original,
                total_volume_original=total_volume_original,
            )
        )
    return linhas


def escolher_proximo_adaptativo(
    adj_atual: dict[str, dict[str, int]],
    criterio: str,
    pesos: PesosInput | None = None,
) -> tuple[str, float | None]:
    candidatos = list(adj_atual.keys())
    if criterio == "score":
        scores = calcular_scores(adj_atual, pesos)
        proximo = max(candidatos, key=lambda c: (scores[c], c))
        return proximo, scores[proximo]
    if criterio == "betweenness":
        bc = betweenness_nao_ponderada(adj_atual)
        proximo = max(candidatos, key=lambda c: (bc[c], c))
        return proximo, bc[proximo]
    proximo = max(candidatos, key=lambda c: (len(adj_atual[c]), c))
    return proximo, float(len(adj_atual[proximo]))


def simular_adaptativo(
    adj_original: dict[str, dict[str, int]],
    limite: int,
    criterio: str = "score",
    pesos: PesosInput | None = None,
) -> list[dict[str, object]]:
    total_nos_original = len(adj_original)
    total_volume_original = volume_restante(adj_original)
    removidos: list[str] = []
    linhas: list[dict[str, object]] = []

    for passo in range(1, limite + 1):
        adj_atual = remover_nos(adj_original, set(removidos))
        if not adj_atual:
            break

        proximo, valor = escolher_proximo_adaptativo(adj_atual, criterio, pesos)
        removidos.append(proximo)
        linhas.append(
            metricas_estado(
                adj_original=adj_original,
                removidos_ordenados=removidos,
                passo=passo,
                aeroporto_removido=proximo,
                total_nos_original=total_nos_original,
                total_volume_original=total_volume_original,
                score_no_passo=valor,
            )
        )
    return linhas


def escrever_csv(path: Path, linhas: list[dict[str, object]]) -> None:
    if not linhas:
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        escritor.writeheader()
        escritor.writerows(linhas)


def primeiro_fragmentacao(linhas: list[dict[str, object]]) -> dict[str, object] | None:
    return next((linha for linha in linhas if linha["componentes_conectados"] > 1), None)


def escrever_resumo(
    adj: dict[str, dict[str, int]],
    aeroportos: dict[str, dict[str, str]],
    limite: int,
    ataque: list[dict[str, object]] | None,
    adaptativo: list[dict[str, object]] | None,
    aleatoria: list[dict[str, object]] | None,
    ranking: list[str],
    pesos: PesosInput | None = None,
) -> None:
    with (RESULTADOS_DIR / "resumo_simulacao_falhas_2025.txt").open("w", encoding="utf-8") as f:
        f.write("Resumo da simulacao de falhas - rede aeroportuaria brasileira 2025\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Aeroportos no grafo original: {len(adj)}\n")
        f.write(f"Volume original de passageiros nas rotas: {volume_restante(adj):,}\n")
        f.write(f"Passos simulados por cenario: {limite}\n")
        if pesos is not None:
            w_b, w_d, w_v = normalizar_pesos(pesos)
            f.write(
                f"Pesos do score (BC,DC,vol): {pesos[0]},{pesos[1]},{pesos[2]} "
                f"-> normalizados ({w_b:.4f}, {w_d:.4f}, {w_v:.4f})\n"
            )
            f.write(f"Formula: score = {formatar_formula_pesos(pesos)}\n")
        f.write("\n")

        if ataque is not None:
            frag = primeiro_fragmentacao(ataque)
            f.write("Cenario 1: ataque direcionado (estatico)\n")
            f.write("Ordem de remocao: ranking de criticidade calculado na modelagem.\n")
            if frag:
                f.write(
                    f"Primeira fragmentacao: passo {frag['passo']} "
                    f"apos remover {frag['aeroporto_removido']}.\n"
                )
            else:
                f.write("Nao houve fragmentacao dentro do limite simulado.\n")
            f.write("Top 10 removidos no ataque estatico:\n")
            for posicao, codigo in enumerate(ranking[:10], start=1):
                meta = aeroportos.get(codigo, {})
                f.write(f"{posicao:02d}. {codigo} - {meta.get('municipio', '')}/{meta.get('uf', '')}\n")
            f.write("\n")

        if adaptativo is not None:
            frag = primeiro_fragmentacao(adaptativo)
            f.write("Cenario 2: ataque direcionado (adaptativo)\n")
            f.write("Ordem de remocao: recalcula o score a cada passo sobre o subgrafo restante.\n")
            if frag:
                f.write(
                    f"Primeira fragmentacao: passo {frag['passo']} "
                    f"apos remover {frag['aeroporto_removido']}.\n"
                )
            else:
                f.write("Nao houve fragmentacao dentro do limite simulado.\n")
            f.write("Top 10 removidos no ataque adaptativo:\n")
            for posicao, linha in enumerate(adaptativo[:10], start=1):
                codigo = linha["aeroporto_removido"]
                meta = aeroportos.get(codigo, {})
                score = linha.get("score_no_passo", "")
                score_txt = f" | score={float(score):.4f}" if score != "" else ""
                f.write(
                    f"{posicao:02d}. {codigo} - {meta.get('municipio', '')}/"
                    f"{meta.get('uf', '')}{score_txt}\n"
                )
            f.write("\n")

        if aleatoria is not None:
            frag = primeiro_fragmentacao(aleatoria)
            cenario = 3 if adaptativo is not None else 2
            f.write(f"Cenario {cenario}: falha aleatoria\n")
            f.write("Ordem de remocao: sorteio com semente fixa 2025 para reproducibilidade.\n")
            if frag:
                f.write(
                    f"Primeira fragmentacao: passo {frag['passo']} "
                    f"apos remover {frag['aeroporto_removido']}.\n"
                )
            else:
                f.write("Nao houve fragmentacao dentro do limite simulado.\n")
            f.write("\n")

        cenarios = [
            ("Ataque estatico", ataque),
            ("Ataque adaptativo", adaptativo),
            ("Falha aleatoria", aleatoria),
        ]
        presentes = [(nome, linhas) for nome, linhas in cenarios if linhas]
        if presentes:
            f.write("Comparacao no passo 10:\n")
            for nome, linhas in presentes:
                linha_10 = linhas[9] if len(linhas) >= 10 else linhas[-1]
                f.write(
                    f"{nome}: maior componente com {linha_10['maior_componente']} aeroportos, "
                    f"{linha_10['componentes_conectados']} componentes, "
                    f"{linha_10['aeroportos_isolados']} aeroportos isolados.\n"
                )


def resolver_pesos(args: argparse.Namespace) -> PesosInput:
    if args.pesos:
        return parsear_pesos(args.pesos)
    salvos = carregar_pesos(RESULTADOS_DIR / "pesos_score_2025.json")
    return salvos or PESOS_PADRAO


def main() -> None:
    parser = argparse.ArgumentParser(description="Simula falhas na rede aeroportuaria.")
    parser.add_argument(
        "--modo",
        choices=["todos", "estatico", "adaptativo", "aleatorio"],
        default="todos",
        help="Cenarios a executar (default: todos)",
    )
    parser.add_argument(
        "--pesos",
        metavar="BC,DC,VOL",
        default=None,
        help=(
            "Pesos do score (0-100 cada), ordem: betweenness,degree,volume. "
            "Usado no ataque estatico (re-ranking) e adaptativo. "
            "Sem --pesos, usa pesos_score_2025.json ou padrao 45,30,25"
        ),
    )
    args = parser.parse_args()
    pesos = resolver_pesos(args)

    adj, aeroportos = carregar_grafo()
    limite = min(30, len(adj))

    ataque: list[dict[str, object]] | None = None
    adaptativo: list[dict[str, object]] | None = None
    aleatoria: list[dict[str, object]] | None = None
    ranking: list[str] = []

    if args.modo in ("todos", "estatico"):
        if args.pesos:
            ranking = ranking_por_score(adj, pesos)
        else:
            ranking = carregar_ranking()
        ataque = simular_ordem(adj, ranking, limite)
        escrever_csv(RESULTADOS_DIR / "simulacao_ataque_direcionado_2025.csv", ataque)

    if args.modo in ("todos", "adaptativo"):
        adaptativo = simular_adaptativo(adj, limite, pesos=pesos)
        escrever_csv(RESULTADOS_DIR / "simulacao_ataque_adaptativo_2025.csv", adaptativo)

    if args.modo in ("todos", "aleatorio"):
        rng = random.Random(2025)
        ordem_aleatoria = list(adj)
        rng.shuffle(ordem_aleatoria)
        aleatoria = simular_ordem(adj, ordem_aleatoria, limite)
        escrever_csv(RESULTADOS_DIR / "simulacao_falha_aleatoria_2025.csv", aleatoria)

    if not ranking and ataque is None and args.modo in ("todos", "estatico"):
        ranking = carregar_ranking()
    elif not ranking:
        try:
            ranking = carregar_ranking()
        except FileNotFoundError:
            ranking = []

    if args.pesos:
        salvar_pesos(RESULTADOS_DIR / "pesos_score_2025.json", pesos)

    escrever_resumo(adj, aeroportos, limite, ataque, adaptativo, aleatoria, ranking, pesos)

    print("Simulacao concluida.")
    w_b, w_d, w_v = normalizar_pesos(pesos)
    print(f"Pesos do score: {pesos[0]},{pesos[1]},{pesos[2]} -> ({w_b:.4f}, {w_d:.4f}, {w_v:.4f})")
    if ataque is not None:
        print(f"Ataque estatico:   {RESULTADOS_DIR / 'simulacao_ataque_direcionado_2025.csv'}")
    if adaptativo is not None:
        print(f"Ataque adaptativo: {RESULTADOS_DIR / 'simulacao_ataque_adaptativo_2025.csv'}")
    if aleatoria is not None:
        print(f"Falha aleatoria:   {RESULTADOS_DIR / 'simulacao_falha_aleatoria_2025.csv'}")
    print(f"Resumo: {RESULTADOS_DIR / 'resumo_simulacao_falhas_2025.txt'}")


if __name__ == "__main__":
    main()
