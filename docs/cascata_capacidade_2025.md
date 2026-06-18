# Realocação de Demanda sob Capacidade: Modelo, Verificação e Protocolo de Validação

## 1. Objetivo

Este documento descreve o módulo de **realocação de demanda sob restrição de
capacidade** da rede aeroportuária brasileira, distinguindo de forma explícita o que
foi **verificado** (consistência interna do modelo) do que ainda **pode ser validado**
(correspondência com o mundo real). O módulo estende a análise topológica de
vulnerabilidade (remoção de nós e fragmentação) com uma camada que estima, quando um
aeroporto é fechado, quanto de sua demanda de passageiros consegue ser reabsorvida pelo
restante do sistema e quanto fica sem realocação viável.

## 2. Fundamentação e posicionamento

Albert, Jeong e Barabási (2000) mostram que redes *scale-free* resistem a falhas
aleatórias mas são frágeis a ataques direcionados aos nós centrais. Essa análise é
puramente topológica: mede o efeito da remoção sobre a conectividade, não sobre a
capacidade de absorver fluxo.

Cumelles, Lordan e Sallan (2021) observam que modelos clássicos de falha em cascata,
formulados para **fluxo contínuo**, são inadequados para redes aeroportuárias: o fluxo
aéreo é composto por eventos programados (voos), e a carga de um aeroporto fechado deve
ser redistribuída para **aeroportos próximos**, e não propagada pelas conexões da rede.
O modelo aqui descrito adota esse princípio — realocação para alternativas geográficas
próximas com capacidade disponível — mas **não reproduz o algoritmo de Cumelles et al.**
(cuja formulação completa, em nível de voos e com comparação de múltiplas regras de
seleção, não foi acessada). As definições operacionais abaixo (carga = demanda de
passageiros, capacidade $C=(1+\alpha)L$, realocação gulosa por proximidade) são deste
trabalho, e Cumelles et al. é citado apenas para o princípio qualitativo.

## 3. Resultado negativo que motiva o desenho

A primeira tentativa seguiu a forma clássica de cascata por propagação de sobrecarga:
ao fechar um aeroporto, sua carga era despejada sobre os vizinhos mais próximos
**ignorando a capacidade**, e todo aeroporto cuja carga ultrapassasse o limite falhava,
propagando a falha. O resultado é degenerado e está reproduzido abaixo (passo 10 do
ataque direcionado, varredura de $\alpha$):

| $\alpha$ | aeroportos que falham por sobrecarga | maior componente |
|---------:|-------------------------------------:|-----------------:|
| 0,1 | 145 | 1 |
| 0,2 | 145 | 1 |
| 0,5 | 144 | 1 |
| 1,0 | 144 | 1 |

A rede colapsa quase por completo (resta um único aeroporto) e o desfecho é praticamente
**insensível a $\alpha$**: dar 10% ou 100% de folga não muda o colapso. Isso é
consistente com a observação de Cumelles et al. (2021) de que a propagação de fluxo
contínuo é inadequada para redes aéreas. Esse resultado negativo motiva a substituição
do mecanismo por uma **realocação que respeita a capacidade** (Seção 4). A degenerescência
é reproduzível e fica registrada como asserção em
`scripts/test_cascata.py::test_cascata_ingenua_colapsa_e_e_insensivel_a_alpha`.

## 4. Modelo

**Grafo.** A malha é o grafo ponderado $G=(V,E)$ da modelagem (155 aeroportos, 622
rotas), com peso de aresta igual ao volume de passageiros.

**Carga e capacidade.** A carga de cada aeroporto $i$ é a sua demanda observada
$L_i$ = passageiros embarcados + desembarcados (de `aeroportos_2025.csv`). A capacidade é
modelada como

$$C_i = (1 + \alpha)\,L_i,$$

onde $\alpha \ge 0$ é a **folga operacional**: a fração de demanda adicional que o
aeroporto consegue absorver acima da sua operação normal. A ocupação inicial de cada
aeroporto é a própria $L_i$, de modo que a capacidade residual inicial é $\alpha L_i$.

**Realocação.** Removido um aeroporto $f$ (ataque), sua demanda $L_f$ é realocada para
as alternativas vivas, segundo uma **regra de seleção** (Seção 5), preenchendo a
capacidade residual de cada candidato até esgotar $L_f$. A demanda que não encontra
capacidade disponível é contabilizada como **demanda não realocada** (*stranded*).
Nenhum aeroporto recebe carga acima de $C_i$ (não há propagação de sobrecarga).

**Sequência de ataque.** A cada passo $k$ são removidos os $k$ aeroportos de maior
criticidade (ordem do ranking), e a realocação é recomputada a partir da rede íntegra.
Cada passo é independente, o que torna o caso-limite verificável (Seção 6).

## 5. Regras de seleção (selection rules)

Foram implementadas três regras transparentes para escolher a alternativa que recebe a
demanda:

- **proximidade** — alternativa geograficamente mais próxima primeiro (distância de
  Haversine);
- **conectado** — aeroportos diretamente ligados ao fechado (vizinhos de rota) primeiro,
  depois por proximidade;
- **capacidade** — alternativa de maior capacidade residual primeiro, ignorando distância.

**Resultado** (passo 10, $\alpha = 0{,}2$):

| regra | demanda não realocada | passageiro-km de realocação |
|-------|----------------------:|----------------------------:|
| proximidade | 115.920.483 | 15.061.378.073 |
| conectado | 115.920.483 | 15.105.656.992 |
| capacidade | 115.920.483 | 15.880.868.234 |

A **demanda não realocada é idêntica nas três regras**: ela é limitada pela capacidade
residual *total* do sistema ($\alpha \sum_i L_i$), que independe da ordem de
preenchimento. A regra afeta a **distância total de realocação** (passageiro-km): a regra
`proximidade` minimiza o deslocamento; `capacidade` o aumenta em cerca de 5%. Em outras
palavras, sob escassez de capacidade a escolha da regra não recupera mais passageiros —
apenas torna a realocação mais ou menos eficiente em distância.

## 6. Verificação (consistência interna)

Os testes a seguir (`scripts/test_cascata.py`) são de **verificação**: confirmam que a
implementação corresponde à especificação do modelo. Não são, e não devem ser lidos
como, validação empírica contra dados reais de operação.

| Teste | Propriedade verificada | Resultado |
|-------|------------------------|-----------|
| `test_alpha_infinito_nao_estranda_e_reproduz_topologia` | Com $\alpha\to\infty$ nada satura, nada fica sem realocação, e a conectividade reproduz exatamente o ataque topológico | passa |
| `test_alpha_finito_gera_demanda_nao_realocada` | Com folga finita, fechar hubs gera demanda não realocada | passa |
| `test_menos_folga_estranda_mais` | Monotonicidade: menos capacidade ($\alpha$ menor) ⇒ mais demanda não realocada | passa |
| `test_realocacao_nao_excede_capacidade` | Nenhum aeroporto recebe carga acima de $C_i$; cada aeroporto satura no máximo uma vez | passa |

O teste do caso-limite ($\alpha\to\infty$) é o discriminador: ele garante que a camada de
capacidade é uma extensão coerente da análise topológica, e não um modelo paralelo.

## 7. Resultados (sob as premissas do modelo)

Varredura de $\alpha$ no passo 10 (remoção dos 10 aeroportos mais críticos):

| $\alpha$ | aeroportos saturados | demanda não realocada | % da demanda |
|---------:|---------------------:|----------------------:|-------------:|
| 0,1 | 144 | 123.072.667 | 61,0% |
| 0,2 | 144 | 115.920.483 | 57,5% |
| 0,5 | 144 | 94.463.930 | 46,8% |
| 1,0 | 144 | 58.703.010 | 29,1% |

Dois achados, sempre **condicionados às premissas** (Seção 9):

1. A fração de demanda sem realocação é alta e cresce ao se reduzir a folga: de 29% com
   100% de folga a 61% com apenas 10%. A remoção dos grandes hubs introduz demanda em
   escala muito superior à capacidade residual do restante do sistema.
2. O número de aeroportos saturados é praticamente constante (≈144) na faixa de $\alpha$
   examinada: a demanda agregada dos hubs satura quase todos os destinos com capacidade,
   independentemente da folga. O sinal informativo é, portanto, a **demanda não
   realocada**, não a contagem de saturados.

## 8. O score de criticidade e sua robustez

O ranking de criticidade que define a ordem de ataque é um índice composto:

$$\text{score}_i = \frac{\text{BC}_i + \text{DC}_i + \widehat{V}_i}{3},$$

onde $\text{BC}_i$ é a *betweenness centrality* (intermediação nas rotas), $\text{DC}_i$
é a *degree centrality* (conexões diretas) e $\widehat{V}_i$ é o volume de passageiros
normalizado por $\log$. As três dimensões capturam papéis complementares: intermediação,
conectividade direta e relevância operacional. Adota-se a **média simples** (pesos iguais),
por ser a escolha neutra na ausência de calibração; ajustar os pesos é trabalho futuro.

A pergunta natural — *"e se os pesos fossem outros?"* — foi tratada por **análise de
sensibilidade**: o top-10 foi recomputado perturbando-se os pesos para enfatizar cada
componente e sob ponderações alternativas (base = pesos iguais).

| pesos (BC/DC/Vol) | nó #1 | interseção com o top-10 base | Jaccard |
|-------------------|:-----:|:---------------------------:|:-------:|
| 1/3 / 1/3 / 1/3 (base) | VCP | — | — |
| 0,50 / 0,25 / 0,25 (+BC) | VCP | 9/10 | 0,82 |
| 0,25 / 0,50 / 0,25 (+DC) | VCP | 10/10 | 1,00 |
| 0,25 / 0,25 / 0,50 (+Vol) | VCP | 10/10 | 1,00 |
| 0,45 / 0,30 / 0,25 | VCP | 9/10 | 0,82 |
| 0,40 / 0,30 / 0,30 | VCP | 9/10 | 0,82 |

**VCP permanece como nó mais crítico em todas as perturbações.** O **conjunto** dos 10
aeroportos mais críticos é idêntico ao base em metade das perturbações (Jaccard 1,00) e, no
restante, 9 dos 10 são mantidos (Jaccard 0,82, com a troca de um único aeroporto na fronteira
— entre Manaus e Fortaleza, conforme se reforce ou não a *betweenness*). Ou seja, o resultado
**não é dirigido pela escolha
exata dos pesos**: os aeroportos estruturalmente centrais emergem sob qualquer ponderação
razoável das três dimensões. Esse é um argumento de robustez, não uma calibração — a
calibração empírica dos pesos permanece como trabalho futuro. A tabela é reproduzível por
`scripts/sensibilidade_score.py`.

## 9. Premissas e limitações

O modelo é **exploratório** e seus resultados são condicionais às seguintes premissas:

1. **Capacidade como proxy.** Não há dado público de capacidade real de pista/*slots*; a
   capacidade é aproximada por $(1+\alpha)L_i$, e $\alpha$ é um parâmetro, não uma
   medida. Os números absolutos de demanda não realocada devem ser lidos como
   comparativos entre cenários, não como previsões.
2. **Demanda agregada, não voos.** A realocação opera sobre demanda anual de passageiros,
   não sobre voos programados; não há dimensão temporal (horário, dia).
3. **Realocação por geografia.** A demanda é realocada para os aeroportos mais próximos
   independentemente de o destino estar no mesmo componente conexo da rede fragmentada —
   simplificação da noção de "alternativa próxima".
4. **Sem propagação de sobrecarga.** Por construção (Seção 3), a restrição de capacidade
   se manifesta como demanda não realocada, e não como falência em cascata de aeroportos.

## 10. Protocolo de validação proposto (trabalho futuro)

A verificação da Seção 6 não estabelece correspondência com a realidade. Uma validação
científica do modelo exigiria, como trabalho futuro:

1. **Capacidade real.** Substituir o proxy $(1+\alpha)L_i$ por capacidades declaradas de
   pista/*slots* (fontes oficiais da ANAC/INFRAERO) e comparar a demanda não realocada
   estimada com a observada.
2. **Calibração de $\alpha$.** Estimar $\alpha$ empiricamente a partir de episódios reais
   de interrupção (por exemplo, fechamentos temporários de aeroportos) e da realocação de
   tráfego efetivamente observada.
3. **Verificação retrospectiva.** Confrontar a previsão do modelo para um fechamento
   histórico conhecido com a redistribuição de passageiros de fato ocorrida.
4. **Modelo de Huff.** Substituir a realocação por proximidade pelo modelo de Huff
   (Correia et al.), que pondera atração e tempo de viagem, e avaliar se a distribuição
   prevista se aproxima mais da observada.

Enquanto esses passos não forem executados, os resultados devem ser apresentados como
**exploratórios e condicionais às premissas**, úteis para comparar cenários relativos
(qual aeroporto, qual folga), não como estimativas absolutas validadas.

## 11. Referências

- ALBERT, R.; JEONG, H.; BARABÁSI, A.-L. Error and attack tolerance of complex networks.
  *Nature*, v. 406, p. 378–382, 2000.
- CORREIA, A. R.; NIYAMA, L. E.; NOGUEIRA, S. A. F. Estimativa da distribuição da demanda
  na Região Metropolitana de São Paulo com cenários de um novo aeroporto. *Journal of
  Transport Literature*, 2013.
- COUTO, G. S.; SILVA, A. P. C. da; RUIZ, L. B.; BENEVENUTO, F. Structural properties of
  the Brazilian air transportation network. *Anais da Academia Brasileira de Ciências*,
  v. 87, n. 3, p. 1653–1674, 2015.
- CUMELLES, J.; LORDAN, O.; SALLAN, J. M. Cascading failures in airport networks.
  *Journal of Air Transport Management*, v. 92, 2021.
- AGÊNCIA NACIONAL DE AVIAÇÃO CIVIL (ANAC). Microdados de voos regulares.
  https://dados.anac.gov.br.
