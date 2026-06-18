# Roteiro para a Banca — Vulnerabilidade da Rede Aeroportuária Brasileira

Guia de estudo: o que dizer, o que cada parte faz, e respostas prontas. Leia antes da
defesa.

---

## 1. O pitch (decore)

> "Construímos uma ferramenta aberta que modela a malha aérea brasileira a partir dos
> microdados da ANAC, identifica os aeroportos estruturalmente mais críticos e simula o
> impacto de removê-los — tanto sobre a conectividade da rede quanto sobre a capacidade
> do sistema de reabsorver a demanda dos aeroportos fechados."

**Objetivo:** identificar aeroportos críticos + simular o impacto da remoção sobre a
conectividade. **Para quem serve:** ferramenta acadêmica aberta e reproduzível.
**O que há de novo:** não a descoberta (a rede BR já foi estudada), mas o **artefato
aberto e reproduzível** — código, dados tratados e visualização.

## 2. Os números (decore)

- 155 aeroportos, 622 rotas, 100,87 milhões de passageiros.
- 1,43 milhão de voos, dos 12 arquivos mensais da ANAC (2025).
- Aeroporto mais crítico: **VCP (Viracopos)** — bate com a literatura (Couto et al., 2015).

## 3. As peças do projeto

| Arquivo | Papel |
|---|---|
| `modelar_rede_aeroportuaria.py` | ANAC → grafo ponderado → centralidades + score de criticidade |
| `simular_falhas_rede.py` | Simulação topológica: ataque direcionado vs. falha aleatória |
| `simular_cascata_capacidade.py` | Realocação de demanda sob capacidade (adaptado de Cumelles) |
| `sensibilidade_score.py` | Mostra que o top-10 é estável aos pesos do score |
| `rede_cli.py` | Terminal interativo (todos os comandos) |
| `mapa_html.py` | Mapa interativo com **dois modos** de simulação |
| `test_cascata.py` | 5 testes de verificação |
| `docs/cascata_capacidade_2025.md` | Metodologia científica do modelo de capacidade |

## 4. O que o front-end (mapa) faz — agora com DOIS modos

Mapa do Brasil (contorno real) com os 155 aeroportos por lat/lon, coloridos por
criticidade, e as 200 maiores rotas. Zoom, pan, clique no aeroporto. **Tudo offline**
(D3 e contorno embutidos). O painel de simulação tem um seletor de modo:

- **Modo "Ataque topológico"** (Albert, 2000): remove aeroportos por criticidade e mostra
  a fragmentação — aeroportos removidos, **isolados** (contorno laranja), nº de
  componentes e % de volume de passageiros ainda conectado.
- **Modo "Realocação (capacidade)"** (adaptado de Cumelles, 2021): a cada aeroporto
  fechado, mostra os aeroportos **saturados** (vermelho), a **demanda não realocada (%)**
  e o nº de saturados. É a camada de capacidade visualizada.

> **Importante:** são duas simulações distintas. O modo topológico mede *conectividade*;
> o modo realocação mede *capacidade*. Saiba dizer qual é qual.

## 5. As três análises (e o que cada uma responde)

1. **Ranking de criticidade** — quais aeroportos são mais importantes? Índice composto
   (Seção 8). Resposta: VCP, CNF, GRU, REC...
2. **Ataque × falha aleatória** (`comp`) — a rede é frágil a ataque dirigido? Sim: a falha
   aleatória preserva muito mais conectividade. Confirma Albert et al. (2000).
3. **Realocação sob capacidade** (`cascata`) — o sistema absorve a demanda dos aeroportos
   fechados? Não totalmente: ao remover os 10 maiores hubs, 29%–61% da demanda fica sem
   realocação viável, conforme a folga de capacidade (α de 1,0 a 0,1).

## 6. Como usamos cada paper de referência

| Paper | Uso |
|---|---|
| **Albert, Jeong & Barabási (2000)** | Base: scale-free resiste a falha aleatória, frágil a ataque dirigido. É o que `comp` demonstra. |
| **Cumelles, Lordan & Sallan (2021)** | Princípio do modo realocação (alternativas próximas com capacidade) e o argumento do resultado negativo. **Adaptado, não reproduzido.** |
| **Couto et al. (2015)** | Coerência: a literatura já aponta VCP como crítico — bate com nosso ranking. |
| **Correia et al. (Huff)** | Fundamenta a realocação por demanda; Huff completo (tempos de viagem) é futuro. |
| **ANAC** | Fonte dos microdados. |

## 7. Como foi testado e por que é confiável

Distinção-chave (decore): **verificação ≠ validação.**

- **Verificação** (feita): 5 testes automatizados de consistência interna —
  (1) α→∞ reproduz o ataque topológico; (2) menos folga → mais demanda perdida
  (monotonicidade); (3) ninguém recebe acima da capacidade; (4) a cascata ingênua colapsa
  (resultado negativo); (5) α finito gera demanda não realocada.
- **Confiabilidade** apoia-se em três pilares: verificação automatizada + coerência com a
  literatura (Couto, Albert) + reprodutibilidade (todo número sai de script versionado).
- **Validação empírica** (contra dados reais de capacidade): **trabalho futuro** —
  declarado, não escondido.

Está no PDF (Seção 6.5 "Verificação e Confiabilidade") e detalhado em
`docs/cascata_capacidade_2025.md`.

## 8. O score de criticidade

$$\text{score} = \frac{\text{BC} + \text{DC} + \text{Vol}}{3}\quad(\text{média simples})$$

- **BC** = betweenness (intermediação nas rotas), **DC** = degree (conexões diretas),
  **Vol** = volume de passageiros (log-normalizado).
- **Por que média simples (pesos iguais)?** É a escolha **neutra** quando não há base para
  privilegiar uma métrica. **Calibrar os pesos é trabalho futuro.**
- **Os pesos dirigem o resultado?** Não: VCP é sempre #1, e o top-10 é estável — idêntico ao
  base (pesos iguais) em metade das perturbações (Jaccard 1,00) e, no resto, 9/10 mantidos
  (Jaccard 0,82; troca de 1 aeroporto na fronteira, entre MAO e FOR conforme o peso da
  betweenness). (`sensibilidade_score.py`.)
- **Betweenness é ponderada?** Não — mede intermediação estrutural; o volume entra como
  termo separado.

## 9. Está alinhado com o objetivo?

Sim. O objetivo (identificar críticos + simular impacto na conectividade) está cumprido.
O modo de capacidade vai **além** do objetivo original — é exploratório, e está marcado
como tal no PDF (§8) e no doc de metodologia.

## 10. O que falta / fraquezas conhecidas

1. **Capa do PDF** ainda genérica (universidade/curso/disciplina). — preencher.
2. **Validação empírica** do modelo de capacidade (capacidade real, calibração de α) —
   trabalho futuro, declarado.
3. A capacidade é um **proxy** $(1+\alpha)L$; os números absolutos de demanda perdida são
   comparativos entre cenários, não previsões.

## 11. Banco de perguntas e respostas

**"O mapa mostra a realocação do paper?"**
Sim, no modo "Realocação (capacidade)". O outro modo é o ataque topológico. São análises
distintas — conectividade vs. capacidade.

**"Vocês implementaram o algoritmo do Cumelles?"**
Adaptamos o princípio (realocar para alternativas próximas com capacidade). Não
reproduzimos o algoritmo exato — não tivemos acesso ao texto completo (é pago). Por isso
dizemos "adaptado de", não "implementa Cumelles".

**"Por que média simples no score (pesos iguais)?"**
É a escolha neutra na ausência de calibração — calibrar os pesos é trabalho futuro. E os pesos
não determinam o resultado: VCP é sempre #1; o top-10 é idêntico ao base em metade das
perturbações (Jaccard 1,00) e, no resto, 9/10 são mantidos (Jaccard 0,82). Argumento de
robustez, não calibração.

**"A betweenness é ponderada ou não?"**
Não ponderada — intermediação estrutural; o volume entra como termo próprio.

**"Por que 144 aeroportos saturam mesmo com 100% de folga (α=1,0)?"**
A demanda dos grandes hubs (só GRU ≈ 50M) supera a capacidade residual do resto do
sistema. O sinal informativo é a demanda não realocada (29%→61%), não a contagem de
saturados.

**"Como sabem que está certo?"**
Verificação por testes (consistência interna) + coerência com a literatura (VCP crítico,
Couto 2015; assimetria ataque/aleatório, Albert 2000) + reprodutibilidade. Validação
empírica é trabalho futuro.

**"Vocês realocam por geografia mesmo com a rede fragmentada em 48 componentes?"**
Sim — a realocação é por proximidade geográfica (simplificação das "alternativas próximas"
do Cumelles), independente do componente. É uma premissa declarada nas limitações.

**"O que tem de novo / qual a inovação?"**
Inovação de processo: a análise da rede BR já existe em artigos; a contribuição é o
artefato aberto, reproduzível e auditável (código + dados + visualização).

**"Quais ferramentas/bibliotecas usaram?"**
Python puro, só biblioteca padrão — os algoritmos de grafo (componentes, betweenness)
são implementados do zero. Visualização em D3.js. Sem `pip install`.

**"Como rodar?"**
`make cli` (análise), `make mapa` (mapa), `make cascata` (capacidade), `make test`
(testes). Os resultados já vêm processados; só reprocessa do zero quem tiver os microdados
da ANAC em `DADOS/`.

## 12. Se travar, volte ao essencial

"O trabalho descobre quais aeroportos derrubam mais a malha aérea brasileira se fecharem,
e mede tanto a quebra de conexões quanto a demanda de passageiros que fica sem
alternativa. É uma ferramenta aberta, testada e reproduzível, fundamentada em Albert
(2000), Couto (2015) e Cumelles (2021)."
