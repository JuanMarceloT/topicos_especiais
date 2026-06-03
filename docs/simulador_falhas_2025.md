# Simulador de Falhas da Rede Aeroportuaria - 2025

## Objetivo

Esta etapa teve como objetivo implementar um simulador experimental para avaliar como a rede
aeroportuaria brasileira se comporta quando aeroportos sao removidos do grafo. A simulacao mede
o impacto dessas remocoes sobre a conectividade da malha, o tamanho do maior componente
conectado, o surgimento de componentes separados e o isolamento de aeroportos.

## Entrada Utilizada

O simulador utiliza como entrada os arquivos gerados na etapa de modelagem:

- `resultados/grafo_aeroportuario_2025.json`;
- `resultados/ranking_criticidade_2025.csv`.

O primeiro arquivo contem o grafo da rede aeroportuaria. O segundo contem a ordem dos aeroportos
segundo o score de criticidade calculado na modelagem.

## Cenarios Simulados

Foram implementados dois cenarios:

### 1. Ataque Direcionado

Nesse cenario, os aeroportos sao removidos de acordo com o ranking de criticidade. Ou seja, o
simulador remove primeiro os aeroportos considerados estruturalmente mais importantes.

Esse cenario representa situacoes em que a falha atinge aeroportos centrais da rede, como grandes
hubs ou aeroportos com alto papel de intermediacao.

### 2. Falha Aleatoria

Nesse cenario, os aeroportos sao removidos em ordem aleatoria. Para garantir reproducibilidade,
foi utilizada uma semente fixa igual a `2025`.

Esse cenario representa falhas distribuidas sem escolha previa dos aeroportos mais importantes.

## Metricas Calculadas

A cada aeroporto removido, o simulador calcula:

- quantidade de aeroportos removidos;
- quantidade de aeroportos restantes;
- numero de componentes conectados;
- tamanho do maior componente conectado;
- fracao do maior componente em relacao ao grafo original;
- quantidade de aeroportos isolados;
- lista de aeroportos isolados;
- volume de passageiros ainda presente nas rotas restantes;
- fracao do volume de passageiros restante.

## Arquivos Gerados

A simulacao gerou os seguintes arquivos:

- `resultados/simulacao_ataque_direcionado_2025.csv`;
- `resultados/simulacao_falha_aleatoria_2025.csv`;
- `resultados/resumo_simulacao_falhas_2025.txt`.

## Resultado Geral

O grafo original possui 155 aeroportos e volume total de 100.873.591 passageiros nas rotas
consideradas. Foram simulados 30 passos de remocao para cada cenario.

No cenario de ataque direcionado, a primeira fragmentacao ocorreu ja no primeiro passo, apos a
remocao de VCP. Isso indica que VCP possui papel estrutural relevante na conexao de aeroportos
menores ou regionais a malha principal.

No cenario de falha aleatoria, a primeira fragmentacao ocorreu apenas no sexto passo, apos a
remocao de SSA. Antes disso, a rede permaneceu conectada mesmo com a retirada de cinco
aeroportos sorteados.

## Comparacao Entre Cenarios

Apos dez remocoes, os resultados foram:

- ataque direcionado: maior componente com 82 aeroportos, 47 componentes conectados e 33
  aeroportos isolados;
- falha aleatoria: maior componente com 132 aeroportos, 10 componentes conectados e 5 aeroportos
  isolados.

Essa diferenca mostra que a rede e mais vulneravel a remocao de aeroportos centrais do que a
falhas aleatorias. O comportamento observado esta alinhado com a literatura sobre redes
complexas, segundo a qual redes com concentracao de conexoes em hubs tendem a resistir melhor a
falhas aleatorias, mas sofrem maior impacto quando os nos centrais sao removidos.

## Interpretacao Academica

Os resultados indicam que a rede aeroportuaria brasileira apresenta dependencia estrutural de
determinados aeroportos. A remocao direcionada dos aeroportos mais criticos reduz rapidamente o
tamanho do maior componente conectado e aumenta o numero de aeroportos isolados. Em contraste,
a remocao aleatoria tende a preservar a conectividade global por mais tempo.

Assim, o simulador demonstra que a vulnerabilidade da malha aerea nacional nao depende apenas do
volume absoluto de passageiros, mas tambem da posicao estrutural que cada aeroporto ocupa na
rede. Aeroportos com funcao de intermediacao regional podem ser decisivos para manter conectadas
regioes mais afastadas dos principais centros economicos.
