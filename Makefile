# Makefile — Análise de Vulnerabilidade da Rede Aeroportuária Brasileira
#
#   make            mostra esta ajuda
#   make cli        abre a interface interativa (usa os resultados já gerados)
#   make mapa       gera e abre o mapa interativo no navegador
#   make pipeline   reprocessa tudo a partir dos microdados da ANAC (requer DADOS/)
#   make clean      remove caches e mapas gerados

PYTHON  ?= python3
SCRIPTS := scripts
RES     := resultados
D3      := $(SCRIPTS)/vendor/d3.v7.min.js

.DEFAULT_GOAL := help
.PHONY: help cli mapa pipeline modelar simular cascata sensibilidade test vendor clean

help: ## mostra os comandos disponíveis
	@echo "Rede Aeroportuária Brasileira — comandos:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

cli: ## abre a CLI interativa (não precisa dos dados crus)
	$(PYTHON) $(SCRIPTS)/rede_cli.py

mapa: vendor ## gera e abre o mapa interativo (HTML + D3 offline)
	$(PYTHON) $(SCRIPTS)/mapa_html.py

pipeline: modelar simular cascata ## reprocessa do zero: ANAC -> grafo -> simulações
	@echo "Pipeline concluído. Rode 'make cli' ou 'make mapa' para explorar."

modelar: ## etapa 1: microdados ANAC (DADOS/) -> grafo + ranking
	$(PYTHON) $(SCRIPTS)/modelar_rede_aeroportuaria.py

simular: ## etapa 2: grafo -> simulações de falha (topológicas)
	$(PYTHON) $(SCRIPTS)/simular_falhas_rede.py

cascata: ## etapa 3: realocação de demanda sob capacidade (varredura de α)
	$(PYTHON) $(SCRIPTS)/simular_cascata_capacidade.py

sensibilidade: ## análise de sensibilidade do score aos pesos (top-10)
	$(PYTHON) $(SCRIPTS)/sensibilidade_score.py

test: ## roda os testes (verificação do modelo de cascata)
	$(PYTHON) $(SCRIPTS)/test_cascata.py

vendor: $(D3) ## baixa o D3 (offline) caso ainda não exista

$(D3):
	mkdir -p $(SCRIPTS)/vendor
	curl -sSL -o $(D3) https://d3js.org/d3.v7.min.js

clean: ## remove __pycache__ e mapas gerados com timestamp
	rm -rf $(SCRIPTS)/__pycache__
	rm -f $(RES)/mapa_aeroportos_*.html
