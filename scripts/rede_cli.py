#!/usr/bin/env python3
"""CLI da rede aeroportuaria brasileira 2025.

Uso:
    python rede_cli.py
    python rede_cli.py --help

Comandos disponíveis no prompt:
    top [n]          ranking dos n mais criticos (default 10)
    info <CODIGO>    detalhes de um aeroporto
    sim <n>          simula n remocoes (ataque por score)
    sim grau <n>     simula n remocoes (ataque por grau)
    sim aleat <n>    simula n remocoes (falha aleatoria)
    comp <n>         compara os 3 cenarios em n passos
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
    print(f"\n  {BOLD}Aeroportos:{RESET}  {len(ranking)}")
    total_pass = sum(int(r["grau_ponderado_passageiros"]) for r in ranking)
    print(f"  {BOLD}Passageiros:{RESET} {fmt_num(total_pass)}")
    print(f"  {BOLD}Rotas:{RESET}       622 não-direcionais")
    print(f"  {BOLD}E_glob:{RESET}      0,4422")
    print(f"\n  {DIM}Baseado em Albert et al. (2000), Latora & Marchiori (2001),")
    print(f"  Cumelles et al. (2021){RESET}")
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
          f"{'Compon.':>8}  {'Isolados':>8}  {'E_glob':>7}  {'Vol.':>6}")
    print(linha())

    for row in sim_rows[:n]:
        passo = int(row["passo"])
        code  = row["aeroporto_removido"]
        maior = int(row["maior_componente"])
        frac  = float(row["fracao_maior_componente"])
        comp  = int(row["componentes_conectados"])
        iso   = int(row["aeroportos_isolados"])
        eg    = float(row.get("eficiencia_global_normalizada", 0))
        vol   = float(row["fracao_volume_restante"])

        # Cor por degradação
        if frac > 0.80:
            cor = GREEN
        elif frac > 0.55:
            cor = YELLOW
        else:
            cor = RED

        eg_str = f"{eg:.3f}" if eg else "  —  "
        print(f"  {passo:>3}  {BOLD}{code:<6}{RESET}  "
              f"{cor}{maior:>12}{RESET}  {cor}{frac:>6.1%}{RESET}  "
              f"{comp:>8}  {iso:>8}  {eg_str:>7}  {vol:>6.1%}")

    print(linha())
    ultimo = sim_rows[n-1]
    frac_f = float(ultimo["fracao_maior_componente"])
    print(f"\n  {BOLD}Passo {n}:{RESET} {int(ultimo['maior_componente'])} aeroportos no maior componente "
          f"({frac_f:.1%}), {ultimo['componentes_conectados']} componentes, "
          f"{ultimo['aeroportos_isolados']} isolados.\n")


def cmd_comp(n: int) -> None:
    score = carregar_sim("ataque_direcionado")
    grau  = carregar_sim("ataque_grau")
    aleat = carregar_sim("falha_aleatoria")

    if not score or not grau or not aleat:
        print(f"\n  {RED}Arquivos de simulação incompletos.{RESET}\n")
        return

    n = min(n, 30, len(score), len(grau), len(aleat))
    print(titulo(f"Comparação — {n} passos"))
    print(linha())
    print(f"  {'#':>3}  {'Score maior':>12}  {'Grau maior':>11}  {'Aleat. maior':>12}  {'Δ score-aleat':>13}")
    print(linha())

    for i in range(n):
        p    = i + 1
        ms   = int(score[i]["maior_componente"])
        mg   = int(grau[i]["maior_componente"])
        ma   = int(aleat[i]["maior_componente"])
        delta = ma - ms
        cor_delta = GREEN if delta >= 0 else RED
        print(f"  {p:>3}  {BLUE}{ms:>12}{RESET}  {YELLOW}{mg:>11}{RESET}  "
              f"{GREEN}{ma:>12}{RESET}  {cor_delta}{delta:>+13}{RESET}")

    print(linha())

    def get_R(rows: list[dict]) -> float:
        s = 1.0
        for r in rows[:30]:
            s += int(r["maior_componente"]) / 155
        return s / 155

    rs = get_R(score)
    rg = get_R(grau)
    ra = get_R(aleat)
    print(f"\n  {BOLD}Índice de robustez R (Schneider et al., 2011):{RESET}")
    print(f"    Ataque score:   {BLUE}{rs:.4f}{RESET}  {barra(rs, 0.5, 20, BLUE)}")
    print(f"    Ataque grau:    {YELLOW}{rg:.4f}{RESET}  {barra(rg, 0.5, 20, YELLOW)}")
    print(f"    Falha aleat.:   {GREEN}{ra:.4f}{RESET}  {barra(ra, 0.5, 20, GREEN)}")
    print(f"\n  {DIM}R_aleat / R_ataque ≈ {ra/rs:.2f}×  "
          f"— confirma predição de Albert et al. (2000) para redes scale-free.{RESET}\n")


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


def cmd_ajuda() -> None:
    print(titulo("Comandos disponíveis"))
    print(linha())
    cmds = [
        ("resumo",        "resumo geral da rede"),
        ("top [n]",       "ranking dos n aeroportos mais críticos (default 10)"),
        ("info <CODIGO>", "detalhes de um aeroporto (ex: info VCP)"),
        ("sim <n>",       "ataque direcionado por score — n passos"),
        ("sim grau <n>",  "ataque por grau (degree) — n passos"),
        ("sim aleat <n>", "falha aleatória — n passos"),
        ("comp <n>",      "comparação dos 3 cenários em n passos"),
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
    print(f"  {DIM}Albert (2000) · Latora (2001) · Cumelles (2021){RESET}\n")

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
            if len(partes) >= 3 and partes[1] == "grau":
                n = int(partes[2]) if partes[2].isdigit() else 10
                cmd_sim(carregar_sim("ataque_grau"), "Ataque por grau", n)
            elif len(partes) >= 3 and partes[1] == "aleat":
                n = int(partes[2]) if partes[2].isdigit() else 10
                cmd_sim(carregar_sim("falha_aleatoria"), "Falha aleatória", n)
            else:
                n = int(partes[1]) if len(partes) > 1 and partes[1].isdigit() else 10
                cmd_sim(carregar_sim("ataque_direcionado"), "Ataque por score", n)

        elif cmd == "comp":
            n = int(partes[1]) if len(partes) > 1 and partes[1].isdigit() else 10
            cmd_comp(n)

        elif cmd == "mapa":
            cmd_mapa()

        elif cmd in ("ajuda", "help", "?"):
            cmd_ajuda()

        else:
            print(f"\n  {RED}Comando desconhecido: {raw!r}{RESET}")
            print(f"  {DIM}Digite 'ajuda' para ver os comandos.{RESET}\n")


if __name__ == "__main__":
    main()
