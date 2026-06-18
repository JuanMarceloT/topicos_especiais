# Análise de Vulnerabilidade da Rede Aeroportuária Brasileira

## Visão geral

Este projeto investiga **quais aeroportos são estruturalmente mais críticos para a
malha aérea brasileira** e **o que acontece com a conectividade da rede quando esses
aeroportos deixam de operar**. A ideia central vem da teoria das redes complexas: redes
concentradas em poucos *hubs* (como a aérea) costumam aguentar bem falhas aleatórias,
mas se desmontam rapidamente quando os nós mais centrais são atingidos de forma
direcionada. O projeto mede exatamente essa fragilidade na malha brasileira.

A partir dos microdados públicos de voos da **ANAC**, a malha aérea é representada como
um **grafo ponderado** — cada aeroporto é um nó, cada rota é uma aresta, e o peso da
aresta é o volume de passageiros. Sobre esse grafo, o projeto calcula um **ranking de
criticidade** dos aeroportos e **simula falhas**, removendo aeroportos um a um e
medindo, a cada passo, o quanto a rede se fragmenta.

O resultado é uma **ferramenta aberta e reproduzível** (a contribuição central do
trabalho): enquanto a literatura existente sobre a rede brasileira são artigos de
análise e as soluções de mercado são proprietárias, aqui o artefato em si — código,
dados tratados e visualização — é aberto e executável por qualquer pessoa.

Tudo é implementado em **Python puro, usando apenas a biblioteca padrão da linguagem**
(sem `pip install`); os algoritmos de grafo são escritos do zero. A visualização é um
mapa interativo em HTML com D3.js, incluído offline no repositório.

## O que o projeto entrega

- Uma **base de dados tratada** da malha aérea (aeroportos e rotas).
- Um **grafo computacional** da rede nacional.
- Um **ranking de criticidade** dos aeroportos, por um índice composto de centralidade.
- Um **simulador de falhas** com três cenários: falha aleatória, ataque direcionado
  estático (ranking fixo) e ataque adaptativo (recalcula criticidade a cada passo).
- Um **módulo de realocação de demanda sob capacidade** (modelo de Cumelles et al., 2021):
  quando um aeroporto fecha, sua demanda é realocada para as alternativas próximas com
  capacidade disponível, e a fração de passageiros sem realocação viável é medida ao
  longo de uma varredura do parâmetro de folga α.
- Uma **interface de linha de comando** e um **mapa interativo** para explorar tudo.

## Como funciona (o pipeline)

O projeto é uma cadeia de quatro scripts, cada um com um papel claro:

1. **`modelar_rede_aeroportuaria.py`** — lê os microdados crus da ANAC, monta o grafo
   ponderado e calcula as centralidades e o índice de criticidade de cada aeroporto.
   Gera o grafo (`.json`), o ranking e as tabelas de aeroportos e rotas.
2. **`simular_falhas_rede.py`** — a partir do grafo e do ranking, executa as simulações
   de remoção de aeroportos (estático, adaptativo e aleatório) e registra, passo a passo,
   a degradação da conectividade.
3. **`simular_cascata_capacidade.py`** — modelo de realocação de demanda sob capacidade
   (Cumelles et al., 2021): a cada aeroporto fechado, realoca a demanda para as
   alternativas mais próximas com capacidade disponível e mede a demanda sem realocação
   viável, varrendo o parâmetro de folga α.
4. **`rede_cli.py`** — interface de terminal para consultar o ranking, ver detalhes de
   um aeroporto e rodar/comparar as simulações.
5. **`mapa_html.py`** — gera o mapa geográfico interativo, com playback do ataque
   mostrando os aeroportos caindo e a rede se fragmentando.

## Requisitos

- **Python 3.11+** — nenhuma dependência externa (apenas a biblioteca padrão).
- O mapa usa D3.js, já incluído em `scripts/vendor/d3.v7.min.js` e funcionando offline.
  Caso o arquivo não exista, `make mapa` o baixa automaticamente.

## Como rodar

A forma mais simples é pelo **Makefile**:

```bash
make          # mostra todos os comandos
make cli      # abre a interface interativa de análise
make mapa     # gera e abre o mapa interativo no navegador
make clean    # remove caches e mapas gerados
```

Os resultados já processados estão versionados em `resultados/`, então `make cli` e
`make mapa` funcionam **imediatamente, sem precisar dos dados crus da ANAC**.

Para **reproduzir tudo do zero** (opcional), é preciso baixar os microdados da ANAC
(<https://dados.anac.gov.br>) para a pasta `DADOS/` no formato `combinada2025-*.txt` e
então rodar:

```bash
make pipeline   # roda modelar + simular em sequência
```

> Os microdados crus (~2,1 milhões de linhas) **não são versionados** por tamanho; por
> isso o `make pipeline` exige a pasta `DADOS/`. O restante funciona sem ela.

Se preferir não usar `make`, os scripts rodam direto:
`python3 scripts/rede_cli.py`, `python3 scripts/mapa_html.py`, etc.

## Comandos da interface (`make cli`)

| Comando         | O que faz                                                     |
|-----------------|---------------------------------------------------------------|
| `resumo`        | resumo geral da rede                                          |
| `top [n]`       | ranking dos `n` aeroportos mais críticos (padrão 10)         |
| `info <CÓDIGO>` | detalhes de um aeroporto (ex.: `info VCP`)                    |
| `sim <n>`       | ataque direcionado estático — `n` passos                     |
| `sim adapt <n>` | ataque adaptativo (recalcula score) — `n` passos             |
| `sim aleat <n>` | falha aleatória — `n` passos                                  |
| `comp <n>`      | compara estático × adaptativo × aleatório                    |
| `cascata <n>`   | realocação de demanda sob capacidade (varredura de α)        |
| `mapa`          | gera o mapa interativo no navegador                          |
| `ajuda`         | lista os comandos                                            |
| `sair`          | encerra                                                      |

## Estrutura do repositório

```
topicos_especiais/
├── README.md                       este arquivo
├── Makefile                        atalhos para rodar o projeto
├── Projeto_Ciencia_Inovacao.pdf    documento do projeto (proposta)
├── Projeto_Ciencia_Inovacao.tex    fonte LaTeX
│
├── scripts/                        código-fonte
│   ├── modelar_rede_aeroportuaria.py
│   ├── metricas_grafo.py
│   ├── simular_falhas_rede.py
│   ├── simular_cascata_capacidade.py
│   ├── test_cascata.py              testes do modelo de capacidade
│   ├── rede_cli.py
│   ├── mapa_html.py
│   └── vendor/                       D3 + contorno do Brasil (offline)
│
├── resultados/                     saídas já geradas (versionadas)
│   ├── grafo_aeroportuario_2025.json
│   ├── ranking_criticidade_2025.csv
│   ├── pesos_score_2025.json
│   ├── aeroportos_2025.csv
│   ├── rotas_aeroportuarias_2025.csv
│   ├── simulacao_ataque_direcionado_2025.csv
│   ├── simulacao_ataque_adaptativo_2025.csv
│   ├── simulacao_falha_aleatoria_2025.csv
│   ├── mapa_aeroportos_2025.html
│   └── resumo_*.txt
│
└── docs/                           documentação das etapas
```

## O índice de criticidade

A criticidade de cada aeroporto é um **índice composto**, calculado em
`metricas_grafo.py` (usado por `modelar_rede_aeroportuaria.py` e pelas simulações):

```
score = w_bc · betweenness_centrality   (intermediação nas rotas)
      + w_dc · degree_centrality         (conexões diretas)
      + w_vol · volume de passageiros    (log-normalizado)
```

Os pesos de entrada são três inteiros de **0 a 100**, na ordem
`betweenness,degree,volume`. No cálculo, são **normalizados pela soma**
(ex.: `45,30,25` → 0,45 + 0,30 + 0,25). Padrão: `45,30,25`.

```bash
# Recalcular ranking com outros pesos
python scripts/modelar_rede_aeroportuaria.py --pesos 60,20,20

# Simular com pesos customizados (estático re-ranqueia; adaptativo recalcula a cada passo)
python scripts/simular_falhas_rede.py --pesos 60,20,20
```

Os pesos usados ficam em `resultados/pesos_score_2025.json`. A *betweenness* é
calculada de forma **não ponderada**: mede a intermediação estrutural,
independente do volume — que já entra como termo próprio.

## Fundamentação

- **Albert, Jeong & Barabási (2000)** — robustez de redes *scale-free*: resistentes a
  falhas aleatórias, frágeis a ataques direcionados.
- **Cumelles, Lordan & Sallan (2021)** — falhas em cascata em redes aeroportuárias.
- **Couto et al. (2015)** — propriedades estruturais da rede aérea brasileira.

## Fonte de dados

Microdados públicos de voos regulares da **ANAC** — <https://dados.anac.gov.br>.
