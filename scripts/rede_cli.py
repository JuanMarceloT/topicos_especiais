#!/usr/bin/env python3
"""CLI da rede aeroportuaria brasileira 2025.

Uso:
    python rede_cli.py
    python rede_cli.py --help

Comandos disponíveis no prompt:
    top [n]          ranking dos n mais criticos (default 10)
    info <CODIGO>    detalhes de um aeroporto
    sim <n>          simula n remocoes (ataque direcionado por criticidade)
    sim aleat <n>    simula n remocoes (falha aleatoria)
    comp <n>         compara ataque direcionado x falha aleatoria
    cascata <n>      realocacao de demanda sob capacidade (varredura de alpha)
    mapa             gera o mapa interativo no browser
    resumo           resumo geral da rede
    ajuda            lista os comandos
    sair             encerra
"""

from __future__ import annotations
import csv
import json
import math
import os
import sys
import textwrap
from pathlib import Path

try:
    import mapa_html as _mapa_html
    _MAPA_OK = True
except ImportError:
    _MAPA_OK = False

ROOT   = Path(__file__).resolve().parents[1]
RES    = ROOT / "resultados"

BLUE   = "\033[94m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"
CYAN   = "\033[96m"


# ── Carregamento ──────────────────────────────────────────────────────────────

def carregar_ranking() -> list[dict]:
    with (RES / "ranking_criticidade_2025.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def carregar_sim(nome: str) -> list[dict]:
    path = RES / f"simulacao_{nome}_2025.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def carregar_resumo() -> str:
    p = RES / "resumo_rede_2025.txt"
    return p.read_text(encoding="utf-8") if p.exists() else ""


# ── Formatação ────────────────────────────────────────────────────────────────

def barra(valor: float, total: float, largura: int = 20, cor: str = BLUE) -> str:
    preenchido = round(largura * valor / total) if total else 0
    preenchido = max(0, min(largura, preenchido))
    return cor + "█" * preenchido + DIM + "░" * (largura - preenchido) + RESET


def linha(char: str = "─", largura: int = 64) -> str:
    return DIM + char * largura + RESET


def titulo(texto: str) -> str:
    return f"\n{BOLD}{BLUE}{texto}{RESET}"


def fmt_num(n: int | float) -> str:
    try:
        return f"{int(n):,}".replace(",", ".")
    except (ValueError, TypeError):
        return str(n)


# ── Comandos ──────────────────────────────────────────────────────────────────

def cmd_resumo(ranking: list[dict]) -> None:
    print(titulo("Rede aeroportuária brasileira — 2025"))
    print(linha())
    res = carregar_resumo()
    if res:
        for ln in res.splitlines():
            if ln.startswith("Top"):
                break
            print(f"  {ln}")
    print(f"\n  {DIM}Métricas calculadas em modelar_rede_aeroportuaria.py.")
    print(f"  Fundamentação: Albert et al. (2000), Cumelles et al. (2021).{RESET}")
    print()


def cmd_top(ranking: list[dict], n: int = 10) -> None:
    n = min(n, len(ranking))
    print(titulo(f"Top {n} — score = 0,45·BC + 0,30·DC + 0,25·vol"))
    print(linha())
    print(f"  {'#':>3}  {'Cód':<5}  {'Cidade/UF':<22}  {'Score':>6}  {'Betweenness':>11}  {'Grau':>5}  Barra")
    print(linha())
    max_score = float(ranking[0]["score_criticidade"])
    for i, r in enumerate(ranking[:n]):
        score = float(r["score_criticidade"])
        bc    = float(r["betweenness_centrality"])
        grau  = int(r["grau"])
        cidade = f"{r['municipio']}/{r['uf']}"
        cor = YELLOW if i == 0 else (BLUE if i < 3 else RESET)
        bar = barra(score, max_score, 16, cor)
        print(f"  {i+1:>3}  {cor}{r['codigo']:<5}{RESET}  "
              f"{cidade:<22}  {score:>6.4f}  {bc:>11.4f}  {grau:>5}  {bar}")
    print()


def cmd_info(ranking: list[dict], codigo: str) -> None:
    codigo = codigo.upper().strip()
    r = next((x for x in ranking if x["codigo"] == codigo), None)
    if not r:
        print(f"\n  {RED}Aeroporto {codigo!r} não encontrado.{RESET}")
        print(f"  {DIM}Use 'top' para ver os códigos disponíveis.{RESET}\n")
        return

    score = float(r["score_criticidade"])
    bc    = float(r["betweenness_centrality"])
    dc    = float(r["degree_centrality"])
    cc    = float(r["closeness_centrality"])
    grau  = int(r["grau"])
    gp    = int(r["grau_ponderado_passageiros"])
    pos   = next(i+1 for i, x in enumerate(ranking) if x["codigo"] == codigo)
    max_gp = max(int(x["grau_ponderado_passageiros"]) for x in ranking)

    print(titulo(f"{codigo}  —  {r['nome']}"))
    print(f"  {DIM}{r['municipio']}, {r['uf']} · {r['regiao']}{RESET}")
    print(linha())
    print(f"  {BOLD}Ranking de criticidade:{RESET} #{pos} de {len(ranking)}")
    print()
    print(f"  Score composto       {YELLOW}{score:.4f}{RESET}")
    print(f"  {barra(score, float(ranking[0]['score_criticidade']), 30, YELLOW)}")
    print()
    print(f"  Betweenness BC       {bc:.4f}  {DIM}(% caminhos mínimos que passam aqui){RESET}")
    print(f"  {barra(bc, float(ranking[0]['betweenness_centrality']), 30, BLUE)}")
    print()
    print(f"  Degree centrality    {dc:.4f}  {DIM}({grau} destinos diretos de 154 possíveis){RESET}")
    print(f"  {barra(dc, 1.0, 30, CYAN)}")
    print()
    print(f"  Closeness            {cc:.4f}  {DIM}(proximidade média na rede){RESET}")
    print(f"  {barra(cc, 1.0, 30, GREEN)}")
    print()
    print(f"  Passageiros/ano      {fmt_num(gp)}")
    print(f"  {barra(gp, max_gp, 30, GREEN)}")
    print()

    # Nota de interpretação
    if pos == 1:
        print(f"  {YELLOW}→ Ponto mais crítico da rede. Fragmenta no passo 1 do ataque.{RESET}")
        print(f"  {YELLOW}  6 aeroportos dependem exclusivamente de VCP (grau 1).{RESET}")
    elif bc > 0.05:
        print(f"  {BLUE}→ Alto betweenness: função de intermediação regional relevante.{RESET}")
    elif grau > 40:
        print(f"  {CYAN}→ Hub de conectividade: muitos destinos diretos.{RESET}")
    print()


def cmd_sim(sim_rows: list[dict], nome_cenario: str, n: int) -> None:
    if not sim_rows:
        print(f"\n  {RED}Arquivo de simulação não encontrado.{RESET}\n")
        return

    n = min(n, len(sim_rows))
    print(titulo(f"Simulação — {nome_cenario} — {n} passos"))
    print(linha())
    print(f"  {'#':>3}  {'Removido':<6}  {'Maior comp.':>12}  {'S(Q)':>6}  "
          f"{'Compon.':>8}  {'Isolados':>8}  {'Vol.':>6}")
    print(linha())

    for row in sim_rows[:n]:
        passo = int(row["passo"])
        code  = row["aeroporto_removido"]
        maior = int(row["maior_componente"])
        frac  = float(row["fracao_maior_componente"])
        comp  = int(row["componentes_conectados"])
        iso   = int(row["aeroportos_isolados"])
        vol   = float(row["fracao_volume_restante"])

        # Cor por degradação
        if frac > 0.80:
            cor = GREEN
        elif frac > 0.55:
            cor = YELLOW
        else:
            cor = RED

        print(f"  {passo:>3}  {BOLD}{code:<6}{RESET}  "
              f"{cor}{maior:>12}{RESET}  {cor}{frac:>6.1%}{RESET}  "
              f"{comp:>8}  {iso:>8}  {vol:>6.1%}")

    print(linha())
    ultimo = sim_rows[n-1]
    frac_f = float(ultimo["fracao_maior_componente"])
    print(f"\n  {BOLD}Passo {n}:{RESET} {int(ultimo['maior_componente'])} aeroportos no maior componente "
          f"({frac_f:.1%}), {ultimo['componentes_conectados']} componentes, "
          f"{ultimo['aeroportos_isolados']} isolados.\n")


def cmd_comp(n: int) -> None:
    score = carregar_sim("ataque_direcionado")
    aleat = carregar_sim("falha_aleatoria")

    if not score or not aleat:
        print(f"\n  {RED}Arquivos de simulação não encontrados.{RESET}\n")
        return

    n = min(n, 30, len(score), len(aleat))
    print(titulo(f"Comparação — ataque direcionado × falha aleatória — {n} passos"))
    print(linha())
    print(f"  {'#':>3}  {'Removido':<8}  {'Ataque maior':>12}  {'Aleat. maior':>12}  {'Δ (aleat−ataq)':>15}")
    print(linha())

    for i in range(n):
        p     = i + 1
        rem   = score[i]["aeroporto_removido"]
        ms    = int(score[i]["maior_componente"])
        ma    = int(aleat[i]["maior_componente"])
        delta = ma - ms
        cor_delta = GREEN if delta >= 0 else RED
        print(f"  {p:>3}  {BOLD}{rem:<8}{RESET}  {BLUE}{ms:>12}{RESET}  "
              f"{GREEN}{ma:>12}{RESET}  {cor_delta}{delta:>+15}{RESET}")

    print(linha())

    # Robustez = fração média do maior componente ao longo dos passos (dados reais)
    def robustez(rows: list[dict]) -> float:
        fr = [float(r["fracao_maior_componente"]) for r in rows[:n]]
        return sum(fr) / len(fr) if fr else 0.0

    rs = robustez(score)
    ra = robustez(aleat)
    print(f"\n  {BOLD}Robustez média (fração média do maior componente em {n} passos):{RESET}")
    print(f"    Ataque direcionado: {BLUE}{rs:>6.1%}{RESET}  {barra(rs, 1.0, 20, BLUE)}")
    print(f"    Falha aleatória:    {GREEN}{ra:>6.1%}{RESET}  {barra(ra, 1.0, 20, GREEN)}")
    if rs:
        print(f"\n  {DIM}A falha aleatória preserva {ra/rs:.2f}× mais conectividade que o ataque")
        print(f"  direcionado — comportamento esperado de redes scale-free (Albert et al., 2000).{RESET}\n")


def cmd_mapa() -> None:
    if not _MAPA_OK:
        print(f"\n  {RED}Módulo mapa_html.py não encontrado na mesma pasta.{RESET}\n")
        return
    print(f"\n  {DIM}Gerando mapa interativo…{RESET}")
    try:
        path = _mapa_html.abrir_mapa()
        print(f"  {GREEN}Mapa aberto no browser:{RESET} {DIM}{path}{RESET}\n")
    except Exception as exc:
        print(f"\n  {RED}Erro ao gerar mapa: {exc}{RESET}\n")


def cmd_cascata(n: int) -> None:
    rows = carregar_sim("cascata_capacidade")
    if not rows:
        print(f"\n  {RED}Arquivo de cascata não encontrado.{RESET}")
        print(f"  {DIM}Execute primeiro simular_cascata_capacidade.py{RESET}\n")
        return

    alpha = rows[0].get("alpha", "?")
    n = min(n, len(rows))
    print(titulo(f"Realocação sob capacidade — α={alpha} — {n} passos"))
    print(f"  {DIM}Capacidade C = (1+α)·demanda. Adaptado de Cumelles et al. (2021).{RESET}")
    print(linha())
    print(f"  {'#':>3}  {'Removido':<8}  {'Maior comp.':>12}  {'Saturados':>9}  "
          f"{'Não realocados':>15}  {'% dem.':>6}")
    print(linha())
    for row in rows[:n]:
        passo = int(row["passo"])
        code  = row["aeroporto_removido"]
        maior = int(row["maior_componente"])
        sat   = int(row["aeroportos_saturados"])
        nrea  = int(row["passageiros_nao_realocados"])
        frac  = float(row["fracao_demanda_nao_realocada"])
        cor = GREEN if frac < 0.25 else (YELLOW if frac < 0.5 else RED)
        print(f"  {passo:>3}  {BOLD}{code:<8}{RESET}  {maior:>12}  {sat:>9}  "
              f"{cor}{fmt_num(nrea):>15}{RESET}  {cor}{frac:>6.1%}{RESET}")
    print(linha())

    res = carregar_resumo_cascata()
    if res:
        print()
        for ln in res:
            print(f"  {ln}")
    print()


def carregar_resumo_cascata() -> list[str]:
    p = RES / "resumo_cascata_capacidade_2025.txt"
    if not p.exists():
        return []
    linhas = p.read_text(encoding="utf-8").splitlines()
    try:
        inicio = next(i for i, ln in enumerate(linhas) if ln.startswith("Varredura"))
    except StopIteration:
        return []
    return linhas[inicio:]


def cmd_ajuda() -> None:
    print(titulo("Comandos disponíveis"))
    print(linha())
    cmds = [
        ("resumo",        "resumo geral da rede"),
        ("top [n]",       "ranking dos n aeroportos mais críticos (default 10)"),
        ("info <CODIGO>", "detalhes de um aeroporto (ex: info VCP)"),
        ("sim <n>",       "ataque direcionado por criticidade — n passos"),
        ("sim aleat <n>", "falha aleatória — n passos"),
        ("comp <n>",      "compara ataque direcionado × falha aleatória"),
        ("cascata <n>",   "realocação de demanda sob capacidade (varredura de α)"),
        ("mapa",          "gera mapa interativo no browser (HTML + D3.js)"),
        ("ajuda",         "esta lista"),
        ("sair",          "encerra o programa"),
    ]
    for cmd, desc in cmds:
        print(f"  {CYAN}{cmd:<20}{RESET}  {desc}")
    print()


# ── Loop principal ────────────────────────────────────────────────────────────

def prompt() -> str:
    try:
        return input(f"{BOLD}{BLUE}rede>{RESET} ").strip()
    except (EOFError, KeyboardInterrupt):
        return "sair"


def main() -> None:
    os.system("clear" if os.name == "posix" else "cls")

    # Banner
    print(f"\n{BOLD}{BLUE}  ✈  Rede Aeroportuária Brasileira 2025{RESET}")
    print(f"  {DIM}CLI de análise de vulnerabilidade{RESET}")
    print(f"  {DIM}Albert et al. (2000) · Cumelles et al. (2021){RESET}\n")

    # Carregar dados
    try:
        ranking = carregar_ranking()
    except FileNotFoundError:
        print(f"  {RED}Arquivo ranking_criticidade_2025.csv não encontrado.")
        print(f"  Execute primeiro modelar_rede_aeroportuaria.py{RESET}\n")
        sys.exit(1)

    cmd_ajuda()

    # REPL
    while True:
        raw = prompt()
        if not raw:
            continue

        partes = raw.lower().split()
        cmd    = partes[0] if partes else ""

        if cmd in ("sair", "exit", "quit", "q"):
            print(f"\n  {DIM}Até logo.{RESET}\n")
            break

        elif cmd == "resumo":
            cmd_resumo(ranking)

        elif cmd == "top":
            n = int(partes[1]) if len(partes) > 1 and partes[1].isdigit() else 10
            cmd_top(ranking, n)

        elif cmd == "info":
            if len(partes) < 2:
                print(f"\n  {RED}Use: info <CODIGO>  (ex: info VCP){RESET}\n")
            else:
                cmd_info(ranking, partes[1])

        elif cmd == "sim":
            if len(partes) >= 3 and partes[1] == "aleat":
                n = int(partes[2]) if partes[2].isdigit() else 10
                cmd_sim(carregar_sim("falha_aleatoria"), "Falha aleatória", n)
            else:
                n = int(partes[1]) if len(partes) > 1 and partes[1].isdigit() else 10
                cmd_sim(carregar_sim("ataque_direcionado"), "Ataque direcionado", n)

        elif cmd == "comp":
            n = int(partes[1]) if len(partes) > 1 and partes[1].isdigit() else 10
            cmd_comp(n)

        elif cmd == "cascata":
            n = int(partes[1]) if len(partes) > 1 and partes[1].isdigit() else 10
            cmd_cascata(n)

        elif cmd == "mapa":
            cmd_mapa()

        elif cmd in ("ajuda", "help", "?"):
            cmd_ajuda()

        else:
            print(f"\n  {RED}Comando desconhecido: {raw!r}{RESET}")
            print(f"  {DIM}Digite 'ajuda' para ver os comandos.{RESET}\n")


if __name__ == "__main__":
    main()
