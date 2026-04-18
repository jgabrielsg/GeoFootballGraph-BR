# GeoFootGraph-BR 

---

**Autor:** João Gabriel Machado  
**Instituição:** FGV - Ciência de Dados e Inteligência Artificial  

## 📋 Descrição do Projeto
Este projeto propõe a aplicação de algoritmos de **Teoria dos Grafos** e **Geoprocessamento** para reestruturar o sistema de ligas do futebol brasileiro. O foco central é solucionar o paradoxo logístico do Brasil: como manter uma pirâmide esportiva profunda e competitiva em um território de dimensões continentais.

Através do mapeamento de sedes (vértices) e distâncias/modais de transporte (arestas), o trabalho utiliza técnicas de **Graph Machine Learning** e **Otimização Combinatória** para reduzir o deslocamento total das equipes, priorizando a saúde financeira dos clubes e o rendimento fisiológico dos atletas.

## Base de Dados
O dataset principal é derivado do **Mapa das OSCs (IPEA)** e dados do **CNPJ (Receita Federal)**, filtrados especificamente para entidades com atividade econômica voltada ao futebol e situação cadastral ativa.
- **Nós:** Clubes (coordenadas geográficas extraídas).
- **Arestas:** Matriz de conectividade baseada no REGIC 2018 (IBGE).
