#!/usr/bin/env python3
"""Modela a rede aeroportuaria brasileira de 2025 a partir dos microdados ANAC.

O script usa apenas a biblioteca padrao para conseguir rodar no ambiente atual.
Ele le os arquivos mensais combinada2025-*.txt, agrega passageiros por rota
domestica e calcula metricas basicas do grafo aeroportuario.
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DADOS_DIR = ROOT / "DADOS"
RESULTADOS_DIR = ROOT / "resultados"


@dataclass
class Aeroporto:
    codigo: str
    icao: str = ""
    nome: str = ""
    municipio: str = ""
    uf: str = ""
    regiao: str = ""
    pais: str = ""
    passageiros_embarcados: int = 0
    passageiros_desembarcados: int = 0
    partidas: int = 0
    chegadas: int = 0


@dataclass
class Rota:
    origem: str
    destino: str
    passageiros: int = 0
    passageiros_pagos: int = 0
    passageiros_gratis: int = 0
    voos: int = 0
    empresas: set[str] = field(default_factory=set)


def inteiro(valor: str) -> int:
    valor = (valor or "").strip()
    if not valor:
        return 0
    return int(float(valor.replace(",", ".")))


def normalizar_codigo(iata: str, icao: str) -> str:
    iata = (iata or "").strip().upper()
    icao = (icao or "").strip().upper()
    return iata or icao


def rota_nao_direcional(origem: str, destino: str) -> tuple[str, str]:
    return tuple(sorted((origem, destino)))


def processar_microdados() -> tuple[dict[str, Aeroporto], dict[tuple[str, str], Rota], dict[str, int]]:
    arquivos = sorted(DADOS_DIR.glob("combinada2025-*.txt"))
    if not arquivos:
        raise FileNotFoundError("Nenhum arquivo combinada2025-*.txt encontrado em DADOS/")

    aeroportos: dict[str, Aeroporto] = {}
    rotas: dict[tuple[str, str], Rota] = {}
    estatisticas = {
        "arquivos_lidos": 0,
        "linhas_lidas": 0,
        "linhas_utilizadas": 0,
        "linhas_descartadas": 0,
    }

    for arquivo in arquivos:
        estatisticas["arquivos_lidos"] += 1
        with arquivo.open("r", encoding="latin-1", newline="") as f:
            leitor = csv.DictReader(f, delimiter=";", quotechar='"')
            for linha in leitor:
                estatisticas["linhas_lidas"] += 1

                pais_origem = (linha.get("nm_pais_origem") or "").strip().upper()
                pais_destino = (linha.get("nm_pais_destino") or "").strip().upper()
                servico = (linha.get("ds_servico_tipo_linha") or "").strip().upper()
                grupo = (linha.get("ds_grupo_di") or "").strip().upper()

                if pais_origem != "BRASIL" or pais_destino != "BRASIL":
                    estatisticas["linhas_descartadas"] += 1
                    continue
                if servico != "PASSAGEIRO":
                    estatisticas["linhas_descartadas"] += 1
                    continue
                if grupo != "REGULAR":
                    estatisticas["linhas_descartadas"] += 1
                    continue

                origem = normalizar_codigo(linha.get("sg_iata_origem", ""), linha.get("sg_icao_origem", ""))
                destino = normalizar_codigo(linha.get("sg_iata_destino", ""), linha.get("sg_icao_destino", ""))
                if not origem or not destino or origem == destino:
                    estatisticas["linhas_descartadas"] += 1
                    continue

                pagos = inteiro(linha.get("nr_passag_pagos", "0"))
                gratis = inteiro(linha.get("nr_passag_gratis", "0"))
                passageiros = pagos + gratis
                if passageiros <= 0:
                    estatisticas["linhas_descartadas"] += 1
                    continue

                estatisticas["linhas_utilizadas"] += 1

                for papel, codigo in (("origem", origem), ("destino", destino)):
                    prefixo = "origem" if papel == "origem" else "destino"
                    if codigo not in aeroportos:
                        aeroportos[codigo] = Aeroporto(
                            codigo=codigo,
                            icao=(linha.get(f"sg_icao_{prefixo}") or "").strip().upper(),
                            nome=(linha.get(f"nm_aerodromo_{prefixo}") or "").strip(),
                            municipio=(linha.get(f"nm_municipio_{prefixo}") or "").strip(),
                            uf=(linha.get(f"sg_uf_{prefixo}") or "").strip(),
                            regiao=(linha.get(f"nm_regiao_{prefixo}") or "").strip(),
                            pais=(linha.get(f"nm_pais_{prefixo}") or "").strip(),
                        )

                aeroportos[origem].passageiros_embarcados += passageiros
                aeroportos[origem].partidas += 1
                aeroportos[destino].passageiros_desembarcados += passageiros
                aeroportos[destino].chegadas += 1

                chave = rota_nao_direcional(origem, destino)
                if chave not in rotas:
                    rotas[chave] = Rota(origem=chave[0], destino=chave[1])
                rota = rotas[chave]
                rota.passageiros += passageiros
                rota.passageiros_pagos += pagos
                rota.passageiros_gratis += gratis
                rota.voos += 1
                empresa = (linha.get("sg_empresa_iata") or linha.get("sg_empresa_icao") or "").strip()
                if empresa:
                    rota.empresas.add(empresa)

    return aeroportos, rotas, estatisticas


def construir_adjacencia(rotas: dict[tuple[str, str], Rota]) -> dict[str, dict[str, int]]:
    adj: dict[str, dict[str, int]] = defaultdict(dict)
    for rota in rotas.values():
        adj[rota.origem][rota.destino] = rota.passageiros
        adj[rota.destino][rota.origem] = rota.passageiros
    return adj


def componentes_conectados(adj: dict[str, dict[str, int]]) -> list[list[str]]:
    visitados: set[str] = set()
    componentes: list[list[str]] = []
    for no in adj:
        if no in visitados:
            continue
        fila = deque([no])
        visitados.add(no)
        componente = []
        while fila:
            atual = fila.popleft()
            componente.append(atual)
            for vizinho in adj[atual]:
                if vizinho not in visitados:
                    visitados.add(vizinho)
                    fila.append(vizinho)
        componentes.append(sorted(componente))
    return sorted(componentes, key=len, reverse=True)


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
    resultado = {}
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


def escrever_resultados(
    aeroportos: dict[str, Aeroporto],
    rotas: dict[tuple[str, str], Rota],
    estatisticas: dict[str, int],
) -> None:
    RESULTADOS_DIR.mkdir(exist_ok=True)
    adj = construir_adjacencia(rotas)
    componentes = componentes_conectados(adj)
    maior_componente = set(componentes[0]) if componentes else set()

    grau = {codigo: len(adj.get(codigo, {})) for codigo in aeroportos}
    grau_ponderado = {codigo: sum(adj.get(codigo, {}).values()) for codigo in aeroportos}
    degree_centrality = {
        codigo: (grau[codigo] / (len(aeroportos) - 1) if len(aeroportos) > 1 else 0.0)
        for codigo in aeroportos
    }
    betweenness = betweenness_nao_ponderada(adj)
    closeness_values = closeness(adj)

    max_passageiros = max(grau_ponderado.values()) if grau_ponderado else 1
    ranking = []
    for codigo, aeroporto in aeroportos.items():
        volume_normalizado = math.log1p(grau_ponderado[codigo]) / math.log1p(max_passageiros)
        score = (
            betweenness.get(codigo, 0.0)
            + degree_centrality.get(codigo, 0.0)
            + volume_normalizado
        ) / 3.0
        ranking.append(
            {
                "codigo": codigo,
                "nome": aeroporto.nome,
                "municipio": aeroporto.municipio,
                "uf": aeroporto.uf,
                "regiao": aeroporto.regiao,
                "grau": grau[codigo],
                "grau_ponderado_passageiros": grau_ponderado[codigo],
                "degree_centrality": degree_centrality.get(codigo, 0.0),
                "betweenness_centrality": betweenness.get(codigo, 0.0),
                "closeness_centrality": closeness_values.get(codigo, 0.0),
                "score_criticidade": score,
                "no_maior_componente": codigo in maior_componente,
            }
        )
    ranking.sort(key=lambda item: item["score_criticidade"], reverse=True)

    with (RESULTADOS_DIR / "rotas_aeroportuarias_2025.csv").open("w", encoding="utf-8", newline="") as f:
        campos = ["origem", "destino", "passageiros", "passageiros_pagos", "passageiros_gratis", "voos", "empresas"]
        escritor = csv.DictWriter(f, fieldnames=campos)
        escritor.writeheader()
        for rota in sorted(rotas.values(), key=lambda r: r.passageiros, reverse=True):
            escritor.writerow(
                {
                    "origem": rota.origem,
                    "destino": rota.destino,
                    "passageiros": rota.passageiros,
                    "passageiros_pagos": rota.passageiros_pagos,
                    "passageiros_gratis": rota.passageiros_gratis,
                    "voos": rota.voos,
                    "empresas": "|".join(sorted(rota.empresas)),
                }
            )

    with (RESULTADOS_DIR / "aeroportos_2025.csv").open("w", encoding="utf-8", newline="") as f:
        campos = [
            "codigo",
            "icao",
            "nome",
            "municipio",
            "uf",
            "regiao",
            "pais",
            "passageiros_embarcados",
            "passageiros_desembarcados",
            "partidas",
            "chegadas",
        ]
        escritor = csv.DictWriter(f, fieldnames=campos)
        escritor.writeheader()
        for aeroporto in sorted(aeroportos.values(), key=lambda a: a.codigo):
            escritor.writerow(aeroporto.__dict__)

    with (RESULTADOS_DIR / "ranking_criticidade_2025.csv").open("w", encoding="utf-8", newline="") as f:
        campos = list(ranking[0].keys()) if ranking else []
        escritor = csv.DictWriter(f, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(ranking)

    grafo = {
        "nodes": [
            {
                "id": aeroporto.codigo,
                "label": aeroporto.codigo,
                "nome": aeroporto.nome,
                "municipio": aeroporto.municipio,
                "uf": aeroporto.uf,
                "regiao": aeroporto.regiao,
            }
            for aeroporto in aeroportos.values()
        ],
        "edges": [
            {
                "source": rota.origem,
                "target": rota.destino,
                "weight": rota.passageiros,
                "voos": rota.voos,
            }
            for rota in rotas.values()
        ],
    }
    with (RESULTADOS_DIR / "grafo_aeroportuario_2025.json").open("w", encoding="utf-8") as f:
        json.dump(grafo, f, ensure_ascii=False, indent=2)

    passageiros_total = sum(rota.passageiros for rota in rotas.values())
    voos_total = sum(rota.voos for rota in rotas.values())
    top_10 = ranking[:10]
    with (RESULTADOS_DIR / "resumo_rede_2025.txt").open("w", encoding="utf-8") as f:
        f.write("Resumo da modelagem da rede aeroportuaria brasileira - 2025\n")
        f.write("=" * 64 + "\n\n")
        f.write(f"Arquivos mensais lidos: {estatisticas['arquivos_lidos']}\n")
        f.write(f"Linhas lidas: {estatisticas['linhas_lidas']:,}\n")
        f.write(f"Linhas utilizadas: {estatisticas['linhas_utilizadas']:,}\n")
        f.write(f"Linhas descartadas por filtro: {estatisticas['linhas_descartadas']:,}\n\n")
        f.write(f"Aeroportos no grafo: {len(aeroportos)}\n")
        f.write(f"Rotas nao direcionais no grafo: {len(rotas)}\n")
        f.write(f"Passageiros considerados: {passageiros_total:,}\n")
        f.write(f"Etapas/voos considerados: {voos_total:,}\n")
        f.write(f"Componentes conectados: {len(componentes)}\n")
        f.write(f"Maior componente conectado: {len(maior_componente)} aeroportos\n\n")
        f.write("Top 10 aeroportos por score de criticidade:\n")
        for posicao, item in enumerate(top_10, start=1):
            f.write(
                f"{posicao:02d}. {item['codigo']} - {item['municipio']}/{item['uf']} "
                f"| grau={item['grau']} "
                f"| passageiros={item['grau_ponderado_passageiros']:,} "
                f"| betweenness={item['betweenness_centrality']:.4f} "
                f"| score={item['score_criticidade']:.4f}\n"
            )

    print(f"Aeroportos: {len(aeroportos)}")
    print(f"Rotas: {len(rotas)}")
    print(f"Passageiros considerados: {passageiros_total:,}")
    print(f"Resumo: {RESULTADOS_DIR / 'resumo_rede_2025.txt'}")


def main() -> None:
    aeroportos, rotas, estatisticas = processar_microdados()
    escrever_resultados(aeroportos, rotas, estatisticas)


if __name__ == "__main__":
    main()
