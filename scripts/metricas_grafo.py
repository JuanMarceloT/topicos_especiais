"""Metricas de centralidade e criticidade para o grafo aeroportuario."""

from __future__ import annotations

import json
import math
from collections import deque
from pathlib import Path
from typing import TypeAlias

PesosInput: TypeAlias = tuple[int, int, int]
PESOS_PADRAO: PesosInput = (45, 30, 25)


def validar_pesos(pesos: PesosInput) -> None:
    nomes = ("betweenness", "degree centrality", "volume")
    for nome, valor in zip(nomes, pesos):
        if not 0 <= valor <= 100:
            raise ValueError(f"Peso de {nome} deve estar entre 0 e 100 (recebido {valor}).")


def normalizar_pesos(pesos: PesosInput) -> tuple[float, float, float]:
    """Converte pesos informados (0-100) em coeficientes que somam 1."""
    validar_pesos(pesos)
    total = sum(pesos)
    if total <= 0:
        raise ValueError("A soma dos pesos deve ser maior que zero.")
    return (pesos[0] / total, pesos[1] / total, pesos[2] / total)


def parsear_pesos(texto: str) -> PesosInput:
    """Interpreta '45,30,25' ou '45 30 25' na ordem BC, DC, volume."""
    partes = texto.replace(",", " ").split()
    if len(partes) != 3:
        raise ValueError(
            "Informe tres pesos na ordem betweenness,degree,volume (0-100 cada), "
            "ex: 45,30,25"
        )
    try:
        valores = tuple(int(p) for p in partes)
    except ValueError as exc:
        raise ValueError("Os pesos devem ser numeros inteiros entre 0 e 100.") from exc
    validar_pesos(valores)
    return valores


def formatar_formula_pesos(pesos: PesosInput | None = None) -> str:
    p = pesos or PESOS_PADRAO
    w_b, w_d, w_v = normalizar_pesos(p)
    return f"{w_b:.0%}·BC + {w_d:.0%}·DC + {w_v:.0%}·vol"


def salvar_pesos(path: Path, pesos: PesosInput) -> None:
    w_b, w_d, w_v = normalizar_pesos(pesos)
    path.write_text(
        json.dumps(
            {
                "betweenness": pesos[0],
                "degree": pesos[1],
                "volume": pesos[2],
                "normalizados": {
                    "betweenness": w_b,
                    "degree": w_d,
                    "volume": w_v,
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def carregar_pesos(path: Path) -> PesosInput | None:
    if not path.exists():
        return None
    dados = json.loads(path.read_text(encoding="utf-8"))
    return (int(dados["betweenness"]), int(dados["degree"]), int(dados["volume"]))


def betweenness_nao_ponderada(adj: dict[str, dict[str, int]]) -> dict[str, float]:
    """Brandes nao ponderado para ranking estrutural."""
    nodes = list(adj)
    cb = {v: 0.0 for v in nodes}

    for s in nodes:
        stack: list[str] = []
        pred = {w: [] for w in nodes}
        sigma = dict.fromkeys(nodes, 0.0)
        dist = dict.fromkeys(nodes, -1)
        sigma[s] = 1.0
        dist[s] = 0
        queue = deque([s])

        while queue:
            v = queue.popleft()
            stack.append(v)
            for w in adj[v]:
                if dist[w] < 0:
                    queue.append(w)
                    dist[w] = dist[v] + 1
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    pred[w].append(v)

        delta = dict.fromkeys(nodes, 0.0)
        while stack:
            w = stack.pop()
            for v in pred[w]:
                if sigma[w]:
                    delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
            if w != s:
                cb[w] += delta[w]

    n = len(nodes)
    if n > 2:
        escala = 1.0 / ((n - 1) * (n - 2))
        for v in cb:
            cb[v] *= escala
    return cb


def closeness(adj: dict[str, dict[str, int]]) -> dict[str, float]:
    resultado: dict[str, float] = {}
    n = len(adj)
    for origem in adj:
        dist = {origem: 0}
        fila = deque([origem])
        while fila:
            atual = fila.popleft()
            for vizinho in adj[atual]:
                if vizinho not in dist:
                    dist[vizinho] = dist[atual] + 1
                    fila.append(vizinho)
        soma = sum(dist.values())
        if soma == 0:
            resultado[origem] = 0.0
        else:
            resultado[origem] = ((len(dist) - 1) / soma) * ((len(dist) - 1) / (n - 1))
    return resultado


def calcular_metricas_nos(
    adj: dict[str, dict[str, int]],
    pesos: PesosInput | None = None,
) -> dict[str, dict[str, float | int]]:
    """Calcula grau, centralidades e score de criticidade sobre o subgrafo atual."""
    w_b, w_d, w_v = normalizar_pesos(pesos or PESOS_PADRAO)
    nos = list(adj)
    n = len(nos)
    grau = {codigo: len(adj.get(codigo, {})) for codigo in nos}
    grau_ponderado = {codigo: sum(adj.get(codigo, {}).values()) for codigo in nos}
    degree_centrality = {
        codigo: (grau[codigo] / (n - 1) if n > 1 else 0.0)
        for codigo in nos
    }
    betweenness = betweenness_nao_ponderada(adj)
    closeness_values = closeness(adj)

    max_passageiros = max(grau_ponderado.values()) if grau_ponderado else 1
    resultado: dict[str, dict[str, float | int]] = {}
    for codigo in nos:
        volume_norm = math.log1p(grau_ponderado[codigo]) / math.log1p(max_passageiros)
        score = (
            w_b * betweenness.get(codigo, 0.0)
            + w_d * degree_centrality.get(codigo, 0.0)
            + w_v * volume_norm
        )
        resultado[codigo] = {
            "grau": grau[codigo],
            "grau_ponderado_passageiros": grau_ponderado[codigo],
            "degree_centrality": degree_centrality[codigo],
            "betweenness_centrality": betweenness[codigo],
            "closeness_centrality": closeness_values[codigo],
            "score_criticidade": score,
        }
    return resultado


def calcular_scores(
    adj: dict[str, dict[str, int]],
    pesos: PesosInput | None = None,
) -> dict[str, float]:
    return {
        codigo: float(metricas["score_criticidade"])
        for codigo, metricas in calcular_metricas_nos(adj, pesos).items()
    }


def ranking_por_score(
    adj: dict[str, dict[str, int]],
    pesos: PesosInput | None = None,
) -> list[str]:
    metricas = calcular_metricas_nos(adj, pesos)
    return sorted(
        metricas.keys(),
        key=lambda codigo: (metricas[codigo]["score_criticidade"], codigo),
        reverse=True,
    )
