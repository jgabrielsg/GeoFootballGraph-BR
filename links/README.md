### Captura de dados

---

Todos os dados vieram de um scraping do site do [ogol.com](https://www.ogol.com.br/), que possui resultados de todos os estaduais de todas as federações do futebol brasileiro, com resultados, de maneira organizada, de campeonatos de divisões inferiores, até de estados menos acompanhados, como Tocantins e Rondônia.

A forma mais simples de capturar os resultados, já com data, gols, e organizado por divisão, é através da aba de `/calendario` das edições do campeonato (ex: [Alagoano-Serie-B](https://www.ogol.com.br/edicao/alagoano-2-divisao-2024/189360/calendario/)), onde temos uma tabela organizada, que permite uma leitura mais fácil pelo nosso método de scraping.

Para pegar as edições dos campeonatos e os links de todas as edições disponíveis
Todos começam com: https://www.ogol.com.br/edicao/
e terminam com /calendario