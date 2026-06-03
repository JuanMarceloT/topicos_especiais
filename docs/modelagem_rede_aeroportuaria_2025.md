# Modelagem da Rede Aeroportuaria Brasileira - 2025

## Objetivo

Esta etapa teve como objetivo transformar os microdados mensais de demanda e oferta da ANAC em
uma representacao computacional da rede aeroportuaria brasileira. A rede foi modelada como um
grafo, no qual os aeroportos representam os nos e as rotas domesticas regulares representam as
arestas.

## Fonte dos Dados

Foram utilizados os arquivos mensais localizados em `DADOS/`:

- `combinada2025-01.txt`
- `combinada2025-02.txt`
- `combinada2025-03.txt`
- `combinada2025-04.txt`
- `combinada2025-05.txt`
- `combinada2025-06.txt`
- `combinada2025-07.txt`
- `combinada2025-08.txt`
- `combinada2025-09.txt`
- `combinada2025-10.txt`
- `combinada2025-11.txt`
- `combinada2025-12.txt`

Esses arquivos contem microdados mais detalhados do que o arquivo anual agregado `2025.csv`.
Por isso, eles foram usados como fonte principal da modelagem.

## Criterios de Filtragem

Para manter a rede coerente com o objetivo do projeto, foram considerados apenas registros que
atendem aos seguintes criterios:

- origem no Brasil;
- destino no Brasil;
- servico de passageiro;
- grupo de voo regular;
- origem e destino validos;
- quantidade de passageiros maior que zero.

Foram descartados registros internacionais, registros de carga, voos improdutivos, registros sem
passageiros e linhas sem origem ou destino identificavel.

## Estrutura do Grafo

O grafo foi modelado como nao direcionado, pois o objetivo inicial e analisar a conectividade
estrutural entre aeroportos, independentemente do sentido operacional da rota.

Cada no representa um aeroporto, identificado preferencialmente pelo codigo IATA. Quando o codigo
IATA nao estava disponivel, foi utilizado o codigo ICAO.

Cada aresta representa uma rota entre dois aeroportos brasileiros. O peso da aresta corresponde
ao total de passageiros transportados naquela conexao ao longo de 2025.

## Metricas Calculadas

Foram calculadas as seguintes metricas:

- `grau`: quantidade de aeroportos diretamente conectados a um aeroporto;
- `grau_ponderado_passageiros`: soma de passageiros transportados nas rotas ligadas ao aeroporto;
- `degree_centrality`: grau normalizado pelo tamanho da rede;
- `betweenness_centrality`: importancia do aeroporto como ponto intermediario entre caminhos da rede;
- `closeness_centrality`: proximidade estrutural do aeroporto em relacao aos demais nos;
- `score_criticidade`: indice combinado para ordenar os aeroportos mais relevantes.

O score de criticidade combina tres fatores:

- 45% centralidade de intermediacao;
- 30% centralidade de grau;
- 25% volume normalizado de passageiros.

Essa composicao privilegia aeroportos que atuam como conectores estruturais, mas tambem considera
conectividade direta e volume de demanda.

## Resultados Gerados

O processamento gerou os seguintes arquivos:

- `resultados/rotas_aeroportuarias_2025.csv`: rotas agregadas entre aeroportos;
- `resultados/aeroportos_2025.csv`: lista de aeroportos identificados;
- `resultados/ranking_criticidade_2025.csv`: ranking de criticidade aeroportuaria;
- `resultados/grafo_aeroportuario_2025.json`: grafo em formato JSON;
- `resultados/resumo_rede_2025.txt`: resumo estatistico da rede.

## Resultado Geral

Foram lidos 12 arquivos mensais, totalizando 2.350.330 linhas. Apos os filtros, 1.430.477 linhas
foram utilizadas na construcao da rede.

A rede final possui:

- 155 aeroportos;
- 622 rotas nao direcionais;
- 100.873.591 passageiros considerados;
- 1 componente conectado;
- maior componente conectado contendo todos os 155 aeroportos.

O fato de a rede possuir apenas um componente conectado indica que todos os aeroportos considerados
estao ligados direta ou indiretamente a malha domestica regular de passageiros.

## Aeroportos Mais Criticos

Os dez aeroportos mais criticos segundo o score calculado foram:

1. VCP - Campinas/SP
2. CNF - Confins/MG
3. GRU - Guarulhos/SP
4. REC - Recife/PE
5. MAO - Manaus/AM
6. CGH - Sao Paulo/SP
7. BSB - Brasilia/DF
8. GIG - Rio de Janeiro/RJ
9. SSA - Salvador/BA
10. BEL - Belem/PA

Esses aeroportos se destacam por combinarem alta conectividade, alto volume de passageiros ou
papel relevante como intermediarios entre diferentes partes da rede.

## Interpretacao Inicial

A modelagem indica que a rede aeroportuaria brasileira apresenta forte dependencia de aeroportos
centrais. Aeroportos como VCP, CNF e GRU aparecem em posicoes elevadas por conectarem grande
quantidade de destinos e concentrarem volume significativo de passageiros. Outros aeroportos,
como MAO, REC e BEL, aparecem com destaque por sua funcao regional, especialmente na conexao de
areas mais distantes aos principais centros da malha.

Essa base permite avancar para a proxima etapa do projeto: a simulacao de falhas. Nessa etapa,
serao removidos aeroportos da rede para medir o impacto sobre a conectividade, a fragmentacao e
o isolamento de regioes.
