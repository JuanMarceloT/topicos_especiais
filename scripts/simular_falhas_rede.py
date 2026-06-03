#!/usr/bin/env python3
"""Simula falhas na rede aeroportuaria modelada.

Entradas esperadas:
- resultados/grafo_aeroportuario_2025.json
- resultados/ranking_criticidade_2025.csv

Saidas:
- resultados/simulacao_ataque_direcionado_2025.csv
- resultados/simulacao_falha_aleatoria_2025.csv
- resultados/resumo_simulacao_falhas_2025.txt
"""

from __future__ import annotations

import csv
import json
import random
from collections import defaultdict, deque
from pathlib import Path


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
) -> dict[str, object]:
    removidos = set(removidos_ordenados)
    adj = remover_nos(adj_original, removidos)
    comps = componentes(adj)
    maior = comps[0] if comps else []
    isolados = sorted([comp[0] for comp in comps if len(comp) == 1])
    volume = volume_restante(adj)

    return {
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


def escrever_csv(path: Path, linhas: list[dict[str, object]]) -> None:
    if not linhas:
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        escritor.writeheader()
        escritor.writerows(linhas)


def main() -> None:
    adj, aeroportos = carregar_grafo()
    ranking = carregar_ranking()

    limite = min(30, len(adj))

    ataque = simular_ordem(adj, ranking, limite)

    rng = random.Random(2025)
    ordem_aleatoria = list(adj)
    rng.shuffle(ordem_aleatoria)
    aleatoria = simular_ordem(adj, ordem_aleatoria, limite)

    escrever_csv(RESULTADOS_DIR / "simulacao_ataque_direcionado_2025.csv", ataque)
    escrever_csv(RESULTADOS_DIR / "simulacao_falha_aleatoria_2025.csv", aleatoria)

    primeiro_ataque_fragmenta = next((linha for linha in ataque if linha["componentes_conectados"] > 1), None)
    primeiro_aleatorio_fragmenta = next((linha for linha in aleatoria if linha["componentes_conectados"] > 1), None)

    with (RESULTADOS_DIR / "resumo_simulacao_falhas_2025.txt").open("w", encoding="utf-8") as f:
        f.write("Resumo da simulacao de falhas - rede aeroportuaria brasileira 2025\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Aeroportos no grafo original: {len(adj)}\n")
        f.write(f"Volume original de passageiros nas rotas: {volume_restante(adj):,}\n")
        f.write(f"Passos simulados por cenario: {limite}\n\n")

        f.write("Cenario 1: ataque direcionado\n")
        f.write("Ordem de remocao: ranking de criticidade calculado na modelagem.\n")
        if primeiro_ataque_fragmenta:
            f.write(
                "Primeira fragmentacao: passo "
                f"{primeiro_ataque_fragmenta['passo']} "
                f"apos remover {primeiro_ataque_fragmenta['aeroporto_removido']}.\n"
            )
        else:
            f.write("Nao houve fragmentacao dentro do limite simulado.\n")
        f.write("Top 10 removidos no ataque direcionado:\n")
        for posicao, codigo in enumerate(ranking[:10], start=1):
            meta = aeroportos.get(codigo, {})
            f.write(f"{posicao:02d}. {codigo} - {meta.get('municipio', '')}/{meta.get('uf', '')}\n")

        f.write("\nCenario 2: falha aleatoria\n")
        f.write("Ordem de remocao: sorteio com semente fixa 2025 para reproducibilidade.\n")
        if primeiro_aleatorio_fragmenta:
            f.write(
                "Primeira fragmentacao: passo "
                f"{primeiro_aleatorio_fragmenta['passo']} "
                f"apos remover {primeiro_aleatorio_fragmenta['aeroporto_removido']}.\n"
            )
        else:
            f.write("Nao houve fragmentacao dentro do limite simulado.\n")

        f.write("\nComparacao no passo 10:\n")
        ataque_10 = ataque[9] if len(ataque) >= 10 else ataque[-1]
        aleatoria_10 = aleatoria[9] if len(aleatoria) >= 10 else aleatoria[-1]
        f.write(
            f"Ataque direcionado: maior componente com {ataque_10['maior_componente']} aeroportos, "
            f"{ataque_10['componentes_conectados']} componentes, "
            f"{ataque_10['aeroportos_isolados']} aeroportos isolados.\n"
        )
        f.write(
            f"Falha aleatoria: maior componente com {aleatoria_10['maior_componente']} aeroportos, "
            f"{aleatoria_10['componentes_conectados']} componentes, "
            f"{aleatoria_10['aeroportos_isolados']} aeroportos isolados.\n"
        )

    print("Simulacao concluida.")
    print(f"Ataque direcionado: {RESULTADOS_DIR / 'simulacao_ataque_direcionado_2025.csv'}")
    print(f"Falha aleatoria: {RESULTADOS_DIR / 'simulacao_falha_aleatoria_2025.csv'}")
    print(f"Resumo: {RESULTADOS_DIR / 'resumo_simulacao_falhas_2025.txt'}")


if __name__ == "__main__":
    main()
