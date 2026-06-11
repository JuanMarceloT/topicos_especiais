#!/usr/bin/env python3
"""Gera visualização HTML interativa da rede aeroportuária brasileira."""

from __future__ import annotations

import csv
import json
import os
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

ROOT   = Path(__file__).resolve().parents[1]
RES    = ROOT / "resultados"
VENDOR = Path(__file__).resolve().parent / "vendor"
D3_PATH = VENDOR / "d3.v7.min.js"
BRASIL_PATH = VENDOR / "brasil.geojson"


def _script_d3() -> str:
    """Embute o D3 inline (offline) ou cai para o CDN se o vendor não existir."""
    if D3_PATH.exists():
        return f"<script>{D3_PATH.read_text(encoding='utf-8')}</script>"
    return '<script src="https://d3js.org/d3.v7.min.js"></script>'


def _brasil_feature() -> dict:
    """Contorno real do Brasil (Natural Earth 50m) ou fallback ao polígono simples."""
    if BRASIL_PATH.exists():
        return json.loads(BRASIL_PATH.read_text(encoding="utf-8"))
    print(
        f"AVISO: {BRASIL_PATH.name} não encontrado em vendor/; usando contorno "
        "simplificado (fronteiras aproximadas). Restaure o asset para o mapa correto.",
        file=sys.stderr,
    )
    return {
        "type": "Feature",
        "properties": {},
        "geometry": {"type": "Polygon", "coordinates": [BRASIL_POLYGON]},
    }

# ── Coordenadas IATA → (lat, lon) ────────────────────────────────────────────
COORDS: dict[str, tuple[float, float]] = {
    # Sudeste — SP
    "GRU": (-23.436, -46.473), "CGH": (-23.626, -46.656),
    "VCP": (-23.007, -47.135), "SJK": (-23.228, -45.862),
    "SJP": (-20.817, -49.406), "RAO": (-21.136, -47.777),
    "PPB": (-22.175, -51.424), "ARU": (-21.141, -50.425),
    "AQA": (-21.812, -48.140), "JTC": (-22.159, -49.071),
    "MII": (-22.196, -49.927), "FRC": (-20.592, -47.383),
    # Sudeste — RJ
    "GIG": (-22.810, -43.250), "SDU": (-22.910, -43.163),
    "RRJ": (-22.988, -43.370), "CAW": (-21.699, -41.302),
    "CFB": (-22.921, -42.074),
    # Sudeste — MG
    "CNF": (-19.624, -43.972), "UDI": (-18.884, -48.225),
    "UBA": (-19.764, -47.965), "MOC": (-16.706, -43.818),
    "VAG": (-21.590, -45.474), "IZA": (-21.513, -43.188),
    "GVR": (-18.895, -41.982), "IPN": (-19.471, -42.488),
    "AAX": (-19.593, -46.943), "POJ": (-18.672, -46.491),
    "DIQ": (-20.181, -44.871), "JMA": (-20.391, -42.043),
    "TFL": (-17.893, -41.511), "IAL": (-16.178, -42.317),
    "PYT": (-17.239, -46.882), "PLU": (-19.851, -43.950),
    # Sudeste — ES
    "VIX": (-20.258, -40.286), "LHN": (-19.430, -40.065),
    # Sul — PR
    "CWB": (-25.529, -49.176), "IGU": (-25.600, -54.485),
    "LDB": (-23.334, -51.130), "MGF": (-23.476, -52.012),
    "UMU": (-23.799, -53.313), "CAC": (-24.968, -53.501),
    "GPB": (-25.388, -51.520), "PGZ": (-25.184, -50.144),
    "PTO": (-26.212, -52.697), "TEC": (-24.317, -50.652),
    "GGJ": (-24.049, -54.195), "UVI": (-26.231, -51.087),
    # Sul — SC
    "FLN": (-27.670, -48.552), "JOI": (-26.224, -48.797),
    "NVT": (-26.880, -48.651), "XAP": (-27.134, -52.656),
    "JJG": (-28.675, -49.059), "EEA": (-27.593, -50.368),
    "CCM": (-28.725, -49.421),
    # Sul — RS
    "POA": (-29.994, -51.171), "CXJ": (-29.197, -51.188),
    "PFB": (-28.244, -52.326), "PET": (-31.718, -52.328),
    "URG": (-29.782, -57.038), "RIA": (-29.711, -53.688),
    "GEL": (-28.282, -54.169),
    # Centro-Oeste — MS
    "CGR": (-20.469, -54.673), "PMG": (-22.550, -55.703),
    "DOU": (-22.202, -54.926), "TJL": (-20.755, -51.683),
    "CMG": (-19.012, -57.674), "BYO": (-21.247, -56.525),
    # Centro-Oeste — MT
    "CGB": (-15.652, -56.117), "ROO": (-16.586, -54.723),
    "OPS": (-11.885, -55.586), "SMT": (-12.479, -55.672),
    "AFL": ( -9.871, -56.106), "BPG": (-15.862, -52.389),
    "AIR": (-10.188, -59.457),
    # Centro-Oeste — GO/DF
    "BSB": (-15.871, -47.919), "GYN": (-16.632, -49.221),
    "CLV": (-17.725, -48.611), "RVD": (-17.835, -50.955),
    # Nordeste — BA
    "SSA": (-12.909, -38.322), "IOS": (-14.816, -39.033),
    "BPS": (-16.439, -39.081), "VDC": (-14.863, -40.863),
    "BRA": (-12.079, -45.009), "GNM": (-14.210, -42.743),
    "LEC": (-12.482, -41.277), "UNA": (-15.355, -39.070),
    "MUU": (-14.099, -38.999), "MXQ": (-13.383, -38.928),
    "PBA": (-13.400, -38.910),
    # Nordeste — CE
    "FOR": ( -3.775, -38.533), "JDO": ( -7.219, -39.270),
    "JJD": ( -2.896, -40.469), "JSO": ( -3.688, -40.356),
    "JSB": ( -4.052, -40.870), "JCS": ( -5.113, -40.674),
    "QIG": ( -6.354, -39.297),
    # Nordeste — RN/PB/PE/AL/SE
    "NAT": ( -5.768, -35.376), "MVF": ( -5.201, -37.364),
    "REC": ( -8.127, -34.923), "JPA": ( -7.146, -34.950),
    "CPV": ( -7.269, -35.897), "CJZ": ( -6.910, -38.555),
    "JPO": ( -6.999, -37.189), "QGP": ( -8.883, -36.527),
    "PNZ": ( -9.362, -40.567), "CAU": ( -8.282, -35.975),
    "SET": ( -7.954, -38.301), "JAW": ( -7.800, -40.605),
    "MCZ": ( -9.511, -35.792), "AJU": (-10.984, -37.070),
    "FEN": ( -3.855, -32.424),
    # Nordeste — MA/PI
    "SLZ": ( -2.585, -44.234), "IMP": ( -5.531, -47.460),
    "BRB": ( -2.763, -42.774), "PHB": ( -2.894, -41.732),
    "THE": ( -5.059, -42.824), "NSR": ( -9.074, -42.817),
    # Norte — PA
    "BEL": ( -1.379, -48.476), "STM": ( -2.425, -54.786),
    "MAB": ( -5.369, -49.138), "TUR": ( -3.786, -49.720),
    "ATM": ( -3.254, -52.254), "ITB": ( -4.243, -56.001),
    "CKS": ( -6.115, -50.000), "OIA": ( -6.763, -51.050),
    "TMT": ( -1.489, -55.896), "OPP": ( -0.640, -47.356),
    "MEU": ( -0.893, -52.603), "PTQ": ( -1.744, -52.236),
    "JPE": ( -2.979, -47.369), "BVS": ( -1.655, -50.454),
    # Norte — AM
    "MAO": ( -3.039, -60.050), "TFF": ( -3.382, -64.724),
    "PIN": ( -2.673, -56.777), "MNX": ( -5.811, -61.280),
    "MBZ": ( -3.370, -57.720), "RBB": ( -4.406, -59.602),
    "LBR": ( -7.278, -64.769), "CIZ": ( -4.085, -63.133),
    "RPU": ( -4.877, -65.353), "TBT": ( -4.256, -69.936),
    "BAZ": ( -0.977, -62.920), "IUP": ( -7.200, -59.890),
    "SJL": ( -0.143, -67.087), "IRZ": ( -0.415, -65.019),
    "ERN": ( -6.639, -69.879),
    # Norte — RO/AC/AP/RR/TO
    "PVH": ( -8.709, -63.902), "JPR": (-10.870, -61.846),
    "OAL": (-11.496, -61.451), "BVH": (-12.694, -60.098),
    "RBR": ( -9.869, -67.898), "CZS": ( -7.599, -72.770),
    "MCP": ( -0.051, -51.072), "BVB": (  2.841, -60.692),
    "PMW": (-10.291, -48.357), "AUX": ( -7.228, -48.241),
}

# ── Centroides por UF (fallback para aeroportos sem coordenada exata) ─────────
UF_COORDS: dict[str, tuple[float, float]] = {
    "AC": (-9.97, -67.81),  "AL": (-9.57, -36.78),
    "AM": (-3.47, -65.10),  "AP": (1.41, -51.77),
    "BA": (-12.50, -42.00), "CE": (-5.20, -39.53),
    "DF": (-15.83, -47.86), "ES": (-20.32, -40.34),
    "GO": (-16.03, -49.33), "MA": (-4.87, -45.28),
    "MG": (-18.51, -44.86), "MS": (-20.51, -54.65),
    "MT": (-14.23, -56.07), "PA": (-4.24, -52.12),
    "PB": (-7.08, -36.52),  "PE": (-8.51, -37.47),
    "PI": (-7.53, -42.93),  "PR": (-24.56, -51.53),
    "RJ": (-22.50, -43.18), "RN": (-5.85, -36.54),
    "RO": (-10.59, -62.55), "RR": (2.22, -61.03),
    "RS": (-30.17, -53.42), "SC": (-27.40, -50.95),
    "SE": (-10.57, -37.45), "SP": (-22.94, -48.66),
    "TO": (-10.15, -48.43),
}

# ── Polígono simplificado do Brasil ──────────────────────────────────────────
# Formato GeoJSON: [longitude, latitude]
BRASIL_POLYGON = [
    [-60.0, 4.5],  [-59.0, 3.8],  [-60.7, 2.8],  [-61.0, 1.5],
    [-60.0, 1.0],  [-59.0, 0.5],  [-51.5, 4.1],  [-51.1, 3.8],
    [-50.5, 1.8],  [-50.0, 0.5],  [-50.0, -1.0], [-49.0, -1.5],
    [-44.4, -2.5], [-42.8, -2.5], [-41.5, -3.0], [-38.5, -3.7],
    [-37.5, -4.8], [-35.2, -5.8], [-35.0, -6.0], [-34.8, -7.2],
    [-34.9, -8.3], [-35.2, -9.5], [-37.1, -10.9],[-38.3, -12.9],
    [-38.9, -13.0],[-39.0, -15.3],[-39.1, -16.4],[-39.2, -17.9],
    [-39.6, -19.0],[-40.3, -20.3],[-41.1, -21.7],[-43.2, -22.9],
    [-44.3, -23.0],[-46.5, -24.0],[-47.9, -25.2],[-48.5, -26.5],
    [-48.6, -27.5],[-49.5, -28.5],[-51.2, -30.0],[-52.1, -31.3],
    [-52.4, -32.0],[-53.4, -33.5],[-53.5, -33.8],[-55.0, -33.0],
    [-57.5, -30.5],[-57.5, -28.0],[-58.6, -27.0],[-58.0, -25.0],
    [-57.5, -22.5],[-58.0, -20.0],[-57.5, -19.5],[-57.5, -17.8],
    [-58.5, -16.5],[-60.0, -15.0],[-60.5, -13.5],[-61.5, -11.0],
    [-62.8, -9.8], [-63.9, -8.5], [-65.3, -7.5], [-67.0, -5.0],
    [-68.8, -4.0], [-69.5, -2.2], [-70.0,  0.0], [-69.7,  1.0],
    [-69.5,  2.0], [-64.0,  1.5], [-61.0,  2.0], [-60.5,  3.5],
    [-60.0,  4.5],
]


def _resolver_coord(codigo: str, uf: str) -> tuple[float, float] | None:
    if codigo in COORDS:
        return COORDS[codigo]
    if uf in UF_COORDS:
        # Jitter determinístico para não empilhar aeroportos do mesmo estado
        h = sum(ord(c) * (i + 1) for i, c in enumerate(codigo))
        dlat = ((h % 17) - 8) * 0.3
        dlon = ((h % 13) - 6) * 0.3
        lat, lon = UF_COORDS[uf]
        return (lat + dlat, lon + dlon)
    return None


def carregar_dados() -> dict:
    # Ranking
    with (RES / "ranking_criticidade_2025.csv").open(encoding="utf-8") as f:
        ranking = list(csv.DictReader(f))

    # Aeroportos com UF
    uf_map: dict[str, str] = {}
    with (RES / "aeroportos_2025.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            uf_map[row["codigo"]] = row["uf"]

    # Montar nodos
    airports = []
    sem_coord = 0
    for i, r in enumerate(ranking):
        cod = r["codigo"]
        uf  = uf_map.get(cod, "")
        coord = _resolver_coord(cod, uf)
        if coord is None:
            sem_coord += 1
            continue
        airports.append({
            "id":    cod,
            "nome":  r["nome"],
            "municipio": r["municipio"],
            "uf":    r["uf"],
            "regiao": r["regiao"],
            "rank":  i + 1,
            "score": float(r["score_criticidade"]),
            "bc":    float(r["betweenness_centrality"]),
            "dc":    float(r["degree_centrality"]),
            "cc":    float(r["closeness_centrality"]),
            "grau":  int(r["grau"]),
            "passageiros": int(r["grau_ponderado_passageiros"]),
            "lat":   coord[0],
            "lon":   coord[1],
        })

    # Rotas (top 200 por passageiros)
    routes = []
    rota_path = RES / "rotas_aeroportuarias_2025.csv"
    if rota_path.exists():
        airport_ids = {a["id"] for a in airports}
        with rota_path.open(encoding="utf-8") as f:
            todas = sorted(csv.DictReader(f),
                           key=lambda x: int(x["passageiros"]), reverse=True)
        for r in todas[:200]:
            if r["origem"] in airport_ids and r["destino"] in airport_ids:
                routes.append({
                    "origem":  r["origem"],
                    "destino": r["destino"],
                    "passageiros": int(r["passageiros"]),
                    "voos": int(r["voos"]),
                })

    # Simulação (ataque direcionado)
    sim = []
    sim_path = RES / "simulacao_ataque_direcionado_2025.csv"
    if sim_path.exists():
        with sim_path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                sim.append({
                    "passo":     int(row["passo"]),
                    "removido":  row["aeroporto_removido"],
                    "removidos": row["removidos_acumulados"].split("|"),
                    "isolados":  row["lista_aeroportos_isolados"].split("|") if row["lista_aeroportos_isolados"] else [],
                    "maior_comp": int(row["maior_componente"]),
                    "fracao":    float(row["fracao_maior_componente"]),
                    "componentes": int(row["componentes_conectados"]),
                    "vol_restante": float(row["fracao_volume_restante"]),
                })

    return {
        "airports": airports,
        "routes":   routes,
        "sim":      sim,
        "sem_coord": sem_coord,
        "total":    len(ranking),
    }


def gerar_html(dados: dict) -> str:
    brasil_geojson = json.dumps(_brasil_feature())
    data_js = json.dumps(dados, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Rede Aeroportuária Brasileira 2025</title>
{_script_d3()}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0d1117;
    color: #e6edf3;
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-size: 13px;
    display: flex;
    height: 100vh;
    overflow: hidden;
  }}

  #map-wrap {{
    flex: 1;
    position: relative;
    overflow: hidden;
  }}

  svg#map {{
    width: 100%;
    height: 100%;
    background: #0d1117;
  }}

  .brasil-fill  {{ fill: #161b22; stroke: #3d444d; stroke-width: 1; }}
  .route        {{ stroke: #3d82f6; stroke-opacity: 0.25; fill: none; pointer-events: none; }}
  .route.bright {{ stroke: #60a5fa; stroke-opacity: 0.6; }}

  .airport      {{ cursor: pointer; transition: r 0.15s; }}
  .airport:hover {{ r: 10px; }}
  .airport.removed {{ opacity: 0.15; }}
  .airport.isolated {{ stroke: #f59e0b !important; stroke-width: 2; }}

  .a-label {{
    font-size: 9px;
    fill: #8b949e;
    pointer-events: none;
    user-select: none;
  }}
  .a-label.top {{ fill: #e6edf3; font-weight: 600; font-size: 11px; }}

  /* ── Sidebar ────────────────────────────────────── */
  #sidebar {{
    width: 300px;
    background: #161b22;
    border-left: 1px solid #30363d;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }}

  #sidebar-header {{
    padding: 16px;
    border-bottom: 1px solid #30363d;
  }}
  #sidebar-header h1 {{
    font-size: 14px;
    font-weight: 700;
    color: #e6edf3;
    line-height: 1.4;
  }}
  #sidebar-header .sub {{
    font-size: 11px;
    color: #8b949e;
    margin-top: 4px;
  }}

  #stats-row {{
    display: flex;
    gap: 8px;
    padding: 12px 16px;
    border-bottom: 1px solid #30363d;
  }}
  .stat-box {{
    flex: 1;
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px;
    text-align: center;
  }}
  .stat-box .val {{ font-size: 18px; font-weight: 700; color: #3b82f6; }}
  .stat-box .lbl {{ font-size: 10px; color: #8b949e; margin-top: 2px; }}

  #top-list {{
    flex: 1;
    overflow-y: auto;
    padding: 8px 0;
  }}
  #top-list::-webkit-scrollbar {{ width: 4px; }}
  #top-list::-webkit-scrollbar-track {{ background: transparent; }}
  #top-list::-webkit-scrollbar-thumb {{ background: #30363d; border-radius: 2px; }}

  .rank-item {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 16px;
    cursor: pointer;
    transition: background 0.1s;
    border-left: 3px solid transparent;
  }}
  .rank-item:hover {{ background: #21262d; }}
  .rank-item.active {{ background: #1f2937; border-left-color: #3b82f6; }}
  .rank-item.removed-item {{ opacity: 0.3; text-decoration: line-through; }}

  .rank-num {{
    font-size: 11px;
    color: #6e7681;
    width: 20px;
    text-align: right;
    flex-shrink: 0;
  }}
  .rank-dot {{
    width: 10px; height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
  }}
  .rank-info {{ flex: 1; min-width: 0; }}
  .rank-code {{ font-weight: 700; font-size: 13px; }}
  .rank-city {{ font-size: 11px; color: #8b949e; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .rank-score {{ font-size: 11px; color: #6e7681; flex-shrink: 0; }}

  /* ── Tooltip ────────────────────────────────────── */
  #tooltip {{
    position: fixed;
    background: #21262d;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.15s;
    z-index: 100;
    max-width: 220px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.5);
  }}
  #tooltip.visible {{ opacity: 1; }}
  #tooltip h3 {{ font-size: 14px; margin-bottom: 4px; }}
  #tooltip .city {{ font-size: 12px; color: #8b949e; margin-bottom: 10px; }}
  .tt-row {{ display: flex; justify-content: space-between; gap: 16px; margin: 3px 0; }}
  .tt-key {{ color: #8b949e; font-size: 11px; }}
  .tt-val {{ font-size: 11px; font-weight: 600; }}

  /* ── Simulação ──────────────────────────────────── */
  #sim-panel {{
    border-top: 1px solid #30363d;
    padding: 12px 16px;
  }}
  #sim-panel h2 {{
    font-size: 12px;
    font-weight: 600;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 10px;
  }}
  #sim-controls {{
    display: flex;
    gap: 6px;
    align-items: center;
    margin-bottom: 8px;
  }}
  button {{
    background: #21262d;
    border: 1px solid #30363d;
    color: #e6edf3;
    padding: 5px 10px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
    transition: background 0.1s;
  }}
  button:hover {{ background: #30363d; }}
  button:disabled {{ opacity: 0.4; cursor: default; }}
  #sim-step-label {{ font-size: 12px; color: #8b949e; }}

  #sim-progress {{
    height: 4px;
    background: #21262d;
    border-radius: 2px;
    overflow: hidden;
    margin-bottom: 8px;
  }}
  #sim-progress-bar {{
    height: 100%;
    background: #ef4444;
    border-radius: 2px;
    transition: width 0.3s;
    width: 0%;
  }}

  .sim-stat-row {{
    display: flex;
    justify-content: space-between;
    margin: 4px 0;
    font-size: 11px;
  }}
  .sim-stat-key {{ color: #8b949e; }}
  .sim-stat-val {{ font-weight: 600; }}
  .val-danger  {{ color: #ef4444; }}
  .val-warn    {{ color: #f59e0b; }}
  .val-ok      {{ color: #22c55e; }}

  /* ── Legend ─────────────────────────────────────── */
  #legend {{
    position: absolute;
    bottom: 16px;
    left: 16px;
    background: rgba(22, 27, 34, 0.9);
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 11px;
    pointer-events: none;
  }}
  .leg-item {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 4px 0;
  }}
  .leg-dot {{
    border-radius: 50%;
    flex-shrink: 0;
  }}

  /* ── Hint ────────────────────────────────────────── */
  #hint {{
    position: absolute;
    top: 12px;
    left: 16px;
    font-size: 11px;
    color: #6e7681;
    pointer-events: none;
  }}
</style>
</head>
<body>

<div id="map-wrap">
  <svg id="map"></svg>
  <div id="legend">
    <div class="leg-item"><div class="leg-dot" style="width:12px;height:12px;background:#f59e0b;"></div> Top 3 (score mais alto)</div>
    <div class="leg-item"><div class="leg-dot" style="width:9px;height:9px;background:#3b82f6;"></div> Top 4–20</div>
    <div class="leg-item"><div class="leg-dot" style="width:7px;height:7px;background:#22d3ee;"></div> Top 21–50</div>
    <div class="leg-item"><div class="leg-dot" style="width:5px;height:5px;background:#6b7280;"></div> Demais</div>
    <div class="leg-item" style="margin-top:6px;"><div style="width:20px;height:1px;background:#60a5fa;opacity:0.6;"></div> Top 50 rotas</div>
    <div class="leg-item"><div style="width:20px;height:1px;background:#3d82f6;opacity:0.25;"></div> Demais rotas</div>
  </div>
  <div id="hint">Scroll para zoom · Arraste para mover · Hover nos nodos</div>
</div>

<div id="sidebar">
  <div id="sidebar-header">
    <h1>✈ Rede Aeroportuária Brasileira</h1>
    <div class="sub">Análise de vulnerabilidade — 2025</div>
  </div>

  <div id="stats-row">
    <div class="stat-box">
      <div class="val" id="stat-airports">—</div>
      <div class="lbl">Aeroportos</div>
    </div>
    <div class="stat-box">
      <div class="val" id="stat-routes">—</div>
      <div class="lbl">Rotas</div>
    </div>
    <div class="stat-box">
      <div class="val" id="stat-comp">1</div>
      <div class="lbl">Componentes</div>
    </div>
  </div>

  <div id="top-list"></div>

  <div id="sim-panel">
    <h2>Simulação de ataque</h2>
    <div id="sim-controls">
      <button id="btn-reset">↺</button>
      <button id="btn-prev">‹</button>
      <button id="btn-next">›</button>
      <button id="btn-play">▶</button>
      <span id="sim-step-label">Passo 0 / 0</span>
    </div>
    <div id="sim-progress"><div id="sim-progress-bar"></div></div>
    <div class="sim-stat-row">
      <span class="sim-stat-key">Aeroporto removido</span>
      <span class="sim-stat-val" id="ss-removido">—</span>
    </div>
    <div class="sim-stat-row">
      <span class="sim-stat-key">Maior componente</span>
      <span class="sim-stat-val" id="ss-maior">—</span>
    </div>
    <div class="sim-stat-row">
      <span class="sim-stat-key">Componentes</span>
      <span class="sim-stat-val" id="ss-comp">—</span>
    </div>
    <div class="sim-stat-row">
      <span class="sim-stat-key">Volume restante</span>
      <span class="sim-stat-val" id="ss-vol">—</span>
    </div>
  </div>
</div>

<div id="tooltip">
  <h3 id="tt-code"></h3>
  <div class="city" id="tt-city"></div>
  <div class="tt-row"><span class="tt-key">Ranking</span><span class="tt-val" id="tt-rank"></span></div>
  <div class="tt-row"><span class="tt-key">Score</span><span class="tt-val" id="tt-score"></span></div>
  <div class="tt-row"><span class="tt-key">Betweenness</span><span class="tt-val" id="tt-bc"></span></div>
  <div class="tt-row"><span class="tt-key">Grau (rotas)</span><span class="tt-val" id="tt-grau"></span></div>
  <div class="tt-row"><span class="tt-key">Passageiros/ano</span><span class="tt-val" id="tt-pass"></span></div>
</div>

<script>
const DATA = {data_js};
const BRASIL = {brasil_geojson};

// ── Helpers ───────────────────────────────────────────────────────────────────
const fmt = n => n >= 1e6
  ? (n/1e6).toFixed(1)+'M'
  : n >= 1e3 ? (n/1e3).toFixed(0)+'K' : String(n);

function airportColor(rank) {{
  if (rank <= 3)  return '#f59e0b';
  if (rank <= 20) return '#3b82f6';
  if (rank <= 50) return '#22d3ee';
  return '#6b7280';
}}
function airportRadius(rank, score) {{
  if (rank <= 3)  return 8;
  if (rank <= 10) return 6;
  if (rank <= 30) return 4.5;
  if (rank <= 60) return 3.5;
  return 2.5;
}}

// ── Setup SVG ─────────────────────────────────────────────────────────────────
const wrap = document.getElementById('map-wrap');
const W = wrap.clientWidth, H = wrap.clientHeight;
const svg = d3.select('#map').attr('viewBox', `0 0 ${{W}} ${{H}}`);

const projection = d3.geoMercator()
  .fitExtent([[20, 20], [W - 20, H - 20]], BRASIL);
const geoPath = d3.geoPath().projection(projection);

const g = svg.append('g');

// Zoom + pan
const zoom = d3.zoom()
  .scaleExtent([0.6, 12])
  .on('zoom', e => g.attr('transform', e.transform));
svg.call(zoom);

// ── Mapa base ─────────────────────────────────────────────────────────────────
g.append('path').datum(BRASIL)
  .attr('d', geoPath)
  .attr('class', 'brasil-fill');

// ── Projetar aeroportos ───────────────────────────────────────────────────────
const airportMap = {{}};
DATA.airports.forEach(a => {{
  const [x, y] = projection([a.lon, a.lat]);
  a.x = x; a.y = y;
  airportMap[a.id] = a;
}});

// ── Rotas ─────────────────────────────────────────────────────────────────────
const maxPass = d3.max(DATA.routes, r => r.passageiros) || 1;
const routeStrokeScale = d3.scaleSqrt()
  .domain([0, maxPass])
  .range([0.3, 2.5]);

const routeLayer = g.append('g').attr('class', 'routes');
DATA.routes.forEach((r, i) => {{
  const a = airportMap[r.origem], b = airportMap[r.destino];
  if (!a || !b) return;
  routeLayer.append('line')
    .datum(r)
    .attr('class', i < 50 ? 'route bright' : 'route')
    .attr('x1', a.x).attr('y1', a.y)
    .attr('x2', b.x).attr('y2', b.y)
    .attr('stroke-width', routeStrokeScale(r.passageiros));
}});

// ── Nodos ─────────────────────────────────────────────────────────────────────
const nodeLayer = g.append('g').attr('class', 'nodes');
const labelLayer = g.append('g').attr('class', 'labels');

const tooltip = document.getElementById('tooltip');

DATA.airports.forEach(a => {{
  const r = airportRadius(a.rank, a.score);
  const c = airportColor(a.rank);

  nodeLayer.append('circle')
    .datum(a)
    .attr('class', 'airport')
    .attr('id', 'ap-' + a.id)
    .attr('cx', a.x).attr('cy', a.y)
    .attr('r', r)
    .attr('fill', c)
    .attr('fill-opacity', 0.9)
    .attr('stroke', '#0d1117')
    .attr('stroke-width', 0.8)
    .on('mouseover', function(event, d) {{
      document.getElementById('tt-code').textContent  = d.id + ' — ' + d.nome;
      document.getElementById('tt-city').textContent  = d.municipio + ', ' + d.uf + ' · ' + d.regiao;
      document.getElementById('tt-rank').textContent  = '#' + d.rank + ' de ' + DATA.airports.length;
      document.getElementById('tt-score').textContent = d.score.toFixed(4);
      document.getElementById('tt-bc').textContent    = d.bc.toFixed(4);
      document.getElementById('tt-grau').textContent  = d.grau + ' destinos';
      document.getElementById('tt-pass').textContent  = fmt(d.passageiros);
      tooltip.classList.add('visible');
      highlightAirport(d.id);
    }})
    .on('mousemove', function(event) {{
      const x = event.clientX + 14, y = event.clientY - 10;
      tooltip.style.left = Math.min(x, window.innerWidth - 240) + 'px';
      tooltip.style.top  = Math.min(y, window.innerHeight - 200) + 'px';
    }})
    .on('mouseout', function() {{
      tooltip.classList.remove('visible');
      clearHighlight();
    }})
    .on('click', function(event, d) {{
      selectRankItem(d.rank);
    }});

  if (a.rank <= 30) {{
    labelLayer.append('text')
      .attr('class', a.rank <= 10 ? 'a-label top' : 'a-label')
      .attr('x', a.x + r + 2)
      .attr('y', a.y + 4)
      .text(a.id);
  }}
}});

// ── Ranking sidebar ───────────────────────────────────────────────────────────
const topList = document.getElementById('top-list');
document.getElementById('stat-airports').textContent = DATA.airports.length;
document.getElementById('stat-routes').textContent   = DATA.routes.length;

DATA.airports.slice(0, 30).forEach(a => {{
  const item = document.createElement('div');
  item.className = 'rank-item';
  item.id = 'ri-' + a.rank;
  item.innerHTML = `
    <span class="rank-num">${{a.rank}}</span>
    <div class="rank-dot" style="background:${{airportColor(a.rank)}}"></div>
    <div class="rank-info">
      <div class="rank-code">${{a.id}}</div>
      <div class="rank-city">${{a.municipio}}, ${{a.uf}}</div>
    </div>
    <span class="rank-score">${{a.score.toFixed(3)}}</span>
  `;
  item.addEventListener('click', () => focusAirport(a.id));
  topList.appendChild(item);
}});

function selectRankItem(rank) {{
  document.querySelectorAll('.rank-item').forEach(el => el.classList.remove('active'));
  const el = document.getElementById('ri-' + rank);
  if (el) {{ el.classList.add('active'); el.scrollIntoView({{block:'nearest'}}); }}
}}

function highlightAirport(id) {{
  d3.selectAll('.route').style('opacity', r =>
    (r.origem === id || r.destino === id) ? 0.9 : 0.08);
}}
function clearHighlight() {{
  d3.selectAll('.route').style('opacity', null);
}}

function focusAirport(id) {{
  const a = airportMap[id];
  if (!a) return;
  const scale = 4;
  const tx = W/2 - scale * a.x;
  const ty = H/2 - scale * a.y;
  svg.transition().duration(600)
     .call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale));
  selectRankItem(a.rank);
}}

// ── Simulação ─────────────────────────────────────────────────────────────────
let simStep = 0;
const simLen = DATA.sim.length;
let playTimer = null;

function applySimStep(step) {{
  // Resetar todos
  d3.selectAll('.airport').classed('removed', false).classed('isolated', false);
  d3.selectAll('.rank-item').classed('removed-item', false);

  if (step === 0) {{
    document.getElementById('ss-removido').textContent = '—';
    document.getElementById('ss-maior').textContent    = '—';
    document.getElementById('ss-comp').textContent     = '—';
    document.getElementById('ss-vol').textContent      = '—';
    document.getElementById('stat-comp').textContent   = '1';
    document.getElementById('sim-progress-bar').style.width = '0%';
    document.getElementById('sim-step-label').textContent = `Passo 0 / ${{simLen}}`;
    document.getElementById('btn-prev').disabled = true;
    document.getElementById('btn-reset').disabled = true;
    return;
  }}

  const s = DATA.sim[step - 1];

  // Marcar removidos
  s.removidos.forEach(id => {{
    d3.select('#ap-' + id).classed('removed', true);
    const ri = document.querySelector('#ri-' + (DATA.airports.findIndex(a=>a.id===id)+1));
    if (ri) ri.classList.add('removed-item');
  }});

  // Marcar isolados
  s.isolados.filter(id => id).forEach(id => {{
    d3.select('#ap-' + id).classed('isolated', true);
  }});

  // Stats
  const fracColor = s.fracao > 0.8 ? 'val-ok' : s.fracao > 0.55 ? 'val-warn' : 'val-danger';
  document.getElementById('ss-removido').textContent = s.removido;
  document.getElementById('ss-maior').innerHTML =
    `<span class="${{fracColor}}">${{s.maior_comp}} (${{(s.fracao*100).toFixed(1)}}%)</span>`;
  document.getElementById('ss-comp').textContent  = s.componentes;
  document.getElementById('ss-vol').innerHTML =
    `<span class="${{fracColor}}">${{(s.vol_restante*100).toFixed(1)}}%</span>`;
  document.getElementById('stat-comp').textContent = s.componentes;
  document.getElementById('sim-progress-bar').style.width =
    ((step / simLen) * 100) + '%';
  document.getElementById('sim-step-label').textContent = `Passo ${{step}} / ${{simLen}}`;
  document.getElementById('btn-prev').disabled  = step <= 1;
  document.getElementById('btn-reset').disabled = step <= 0;
  document.getElementById('btn-next').disabled  = step >= simLen;
}}

document.getElementById('btn-reset').addEventListener('click', () => {{
  clearPlay();
  simStep = 0;
  applySimStep(0);
}});
document.getElementById('btn-prev').addEventListener('click', () => {{
  clearPlay();
  if (simStep > 0) {{ simStep--; applySimStep(simStep); }}
}});
document.getElementById('btn-next').addEventListener('click', () => {{
  clearPlay();
  if (simStep < simLen) {{ simStep++; applySimStep(simStep); }}
}});

function clearPlay() {{
  if (playTimer) {{ clearInterval(playTimer); playTimer = null; }}
  document.getElementById('btn-play').textContent = '▶';
}}
document.getElementById('btn-play').addEventListener('click', function() {{
  if (playTimer) {{
    clearPlay();
  }} else {{
    if (simStep >= simLen) simStep = 0;
    this.textContent = '⏸';
    playTimer = setInterval(() => {{
      simStep++;
      applySimStep(simStep);
      if (simStep >= simLen) clearPlay();
    }}, 800);
  }}
}});

// Init
applySimStep(0);
document.getElementById('btn-prev').disabled  = true;
document.getElementById('btn-reset').disabled = true;
document.getElementById('btn-next').disabled  = simLen === 0;
document.getElementById('btn-play').disabled  = simLen === 0;

</script>
</body>
</html>"""


def abrir_mapa() -> Path:
    dados = carregar_dados()
    html  = gerar_html(dados)
    ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
    out   = RES / f"mapa_aeroportos_{ts}.html"
    out.write_text(html, encoding="utf-8")
    webbrowser.open(f"file://{out.resolve()}")
    return out


if __name__ == "__main__":
    path = abrir_mapa()
    print(f"Mapa gerado: {path}")
