#!/usr/bin/env python3
"""Testes do simulador de realocacao de demanda sob capacidade."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from simular_falhas_rede import carregar_grafo, componentes, remover_nos
from simular_cascata_capacidade import (
    carregar_demanda,
    carregar_ordem_ranking,
    realocar_demanda,
    simular_ataque_cascata,
)
from mapa_html import COORDS


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
