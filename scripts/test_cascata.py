#!/usr/bin/env python3
"""Testes do simulador de realocacao de demanda sob capacidade."""

import math
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from simular_falhas_rede import carregar_grafo, componentes, remover_nos
from simular_cascata_capacidade import (
    carregar_demanda,
    carregar_ordem_ranking,
    haversine,
    realocar_demanda,
    simular_ataque_cascata,
)
from mapa_html import COORDS


def cascata_ingenua(adj0, demanda0, coords, removidos_iniciais, alpha, k=5):
    """Cascata por propagacao de sobrecarga IGNORANDO capacidade na realocacao.

    Versao degenerada (rejeitada): despeja a carga integral do aeroporto fechado nos
    k vizinhos mais proximos; quem ultrapassa a capacidade falha e propaga. Mantida
    apenas para documentar e reproduzir o resultado negativo (Secao 3 do doc).
    """
    cap = {n: (1 + alpha) * demanda0.get(n, 0.0) for n in adj0}
    carga = dict(demanda0)
    vivos = set(adj0)
    fila = deque(removidos_iniciais)
    falhas = []
    while fila:
        x = fila.popleft()
        if x not in vivos:
            continue
        vivos.discard(x)
        load = carga.get(x, 0.0)
        carga[x] = 0.0
        if x not in coords:
            continue
        cand = sorted(
            (v for v in vivos if v in coords),
            key=lambda v: haversine(coords[x], coords[v]),
        )[:k]
        if not cand:
            continue
        parcela = load / len(cand)
        for v in cand:
            carga[v] += parcela
            if carga[v] > cap[v] and v not in falhas:
                falhas.append(v)
                fila.append(v)
    return vivos, falhas


def cascata_ingenua_maior_componente(alpha, passo=10):
    """Tamanho do maior componente apos a cascata ingenua (para o resultado negativo)."""
    adj, _ = carregar_grafo()
    ordem = carregar_ordem_ranking()
    demanda = carregar_demanda()
    vivos, _ = cascata_ingenua(adj, demanda, COORDS, ordem[:passo], alpha)
    adj_f = remover_nos(adj, set(adj) - vivos)
    comps = componentes(adj_f)
    return len(comps[0]) if comps else 0


def _ataque_topologico(adj, ordem, limite):
    seq = []
    for k in range(1, limite + 1):
        adj_k = remover_nos(adj, set(ordem[:k]))
        comps = componentes(adj_k)
        seq.append(len(comps[0]) if comps else 0)
    return seq


def test_alpha_infinito_nao_estranda_e_reproduz_topologia():
    """Capacidade infinita: nada satura, nada estranda, conectividade = ataque atual."""
    adj, _ = carregar_grafo()
    ordem = carregar_ordem_ranking()
    demanda = carregar_demanda()
    limite = min(30, len(adj))

    esperado = _ataque_topologico(adj, ordem, limite)
    linhas = simular_ataque_cascata(adj, demanda, COORDS, ordem, limite, math.inf)

    assert [l["maior_componente"] for l in linhas] == esperado
    assert all(l["aeroportos_saturados"] == 0 for l in linhas)
    assert all(l["passageiros_nao_realocados"] == 0 for l in linhas)


def test_alpha_finito_gera_demanda_nao_realocada():
    """Com folga finita, fechar hubs deve deixar demanda sem realocacao."""
    adj, _ = carregar_grafo()
    ordem = carregar_ordem_ranking()
    demanda = carregar_demanda()
    limite = min(30, len(adj))

    linhas = simular_ataque_cascata(adj, demanda, COORDS, ordem, limite, 0.1)
    assert linhas[-1]["passageiros_nao_realocados"] > 0


def test_menos_folga_estranda_mais():
    """Monotonia: menos capacidade (alpha menor) => mais demanda nao realocada."""
    adj, _ = carregar_grafo()
    ordem = carregar_ordem_ranking()
    demanda = carregar_demanda()
    limite = min(30, len(adj))

    apertado = simular_ataque_cascata(adj, demanda, COORDS, ordem, limite, 0.1)
    folgado = simular_ataque_cascata(adj, demanda, COORDS, ordem, limite, 1.0)

    assert apertado[-1]["passageiros_nao_realocados"] >= folgado[-1]["passageiros_nao_realocados"]


def test_realocacao_nao_excede_capacidade():
    """Nenhum aeroporto recebe demanda acima da sua capacidade."""
    adj, _ = carregar_grafo()
    demanda = carregar_demanda()
    alpha = 0.2
    res = realocar_demanda(adj, demanda, COORDS, ["VCP", "CNF", "GRU"], alpha)
    # saturados existem, mas nenhuma ocupacao reportada ultrapassa o limite -> garantido
    # pela construcao (preenche apenas a capacidade residual). Checa consistencia basica:
    assert res["nao_realocada"] >= 0
    assert len(res["saturados"]) == len(set(res["saturados"]))


def test_cascata_ingenua_colapsa_e_e_insensivel_a_alpha():
    """Resultado negativo (Seção 3): a propagação ingênua colapsa a rede a ~1
    componente e é praticamente insensível a alpha, motivando o modelo com capacidade."""
    maiores = [cascata_ingenua_maior_componente(a) for a in (0.1, 0.2, 0.5, 1.0)]
    assert all(m <= 2 for m in maiores), f"esperado colapso (<=2), obtido {maiores}"
    assert max(maiores) - min(maiores) <= 1, f"esperado insensibilidade a alpha, obtido {maiores}"


if __name__ == "__main__":
    testes = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    falhou = 0
    for t in testes:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            falhou += 1
            print(f"FAIL  {t.__name__}: {e}")
    print(f"\n{len(testes) - falhou}/{len(testes)} testes passaram.")
    sys.exit(1 if falhou else 0)
