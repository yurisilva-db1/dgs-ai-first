#### Exercício 1.2 — Prototipação de prompt com engenharia de contexto

**Contexto:** Você precisa prototipar o system prompt do assistente e testar com cenários reais. Além do conteúdo do prompt, você precisa pensar em como o contexto é estruturado: o que é estático, o que é dinâmico, e como a ordem da informação afeta a resposta.

**Ferramentas a utilizar:** Claude (chat) — o próprio Claude serve como ambiente de teste do prompt

**Inputs fornecidos:**
- O cenário completo.
- Guardrails definidos pelo Product Specialist: *"O assistente deve (1) sempre citar a fonte do documento, (2) nunca inventar prazos ou valores que não estejam na documentação, (3) quando não encontrar resposta, dizer explicitamente que não encontrou e sugerir escalar para o supervisor, (4) responder em português formal mas acessível."*
- 3 chunks simulados de documentação (extraídos do **Anexo B** — o Anexo B contém o conjunto completo de chunks e o mapa de cobertura para validação):
  - Chunk A: *"Política de Devolução POL-001, seção 3.2: Mercadorias podem ser devolvidas em até 7 dias úteis após o recebimento, exceto cargas classificadas como perigosas (classes 1 a 6 da ANTT). O cliente deve abrir chamado no portal e anexar fotos da mercadoria."*
  - Chunk B: *"Tabela SLA-2024: Cliente Gold — resposta em até 2h, resolução em até 24h. Cliente Silver — resposta em até 4h, resolução em até 48h. Cliente Standard — resposta em até 8h, resolução em até 72h."*
  - Chunk C: *"PROC-042-v2, seção 2: Frete especial para cargas acima de 500kg: valor base × multiplicador regional. Região Sul: 1.3. Região Sudeste: 1.1. Região Norte: 1.8. Região Nordeste: 1.5. Região Centro-Oeste: 1.4."*
- Conceito de contexto estático vs dinâmico: *"Em um prompt de produção, algumas partes são estáticas (system prompt, guardrails — raramente mudam) e outras são dinâmicas (chunks recuperados, dados do cliente, histórico da conversa — mudam a cada query). A engenharia de contexto decide como essas partes se compõem: em que ordem, com que prioridade, e o que fazer quando o contexto total ultrapassa o orçamento."*

**Tarefa:**
1. Escreva um system prompt completo para o assistente, incorporando os guardrails e o contexto do projeto. Organize o prompt em seções claras: identidade, regras, formato de resposta, e instruções para uso dos chunks. Defina explicitamente a ordem de prioridade quando houver conflito entre fontes.

2. Documente a estrutura de contexto do prompt: identifique quais partes são estáticas (vão em toda query) e quais são dinâmicas (mudam por query). Estime o tamanho em tokens de cada parte.

3. Teste o prompt diretamente no **Claude**: abra uma conversa nova, cole o system prompt como instrução inicial junto com os chunks simulados, e faça estas 3 perguntas como se fosse o atendente:
   - "Qual o prazo de devolução para carga perigosa?"
   - "Meu cliente é Gold, qual o SLA de resolução?"
   - "Quanto custa o frete para 600kg para Manaus?"

4. Analise cada resposta: está correta? Citou a fonte? Respeitou os guardrails? Onde errou?

5. Itere o system prompt: reescreva partes que geraram respostas inadequadas e teste novamente.

**Entregável:** O system prompt v1 com mapeamento de contexto estático/dinâmico, as respostas obtidas, a análise crítica, o system prompt v2 (iterado), e as respostas da segunda rodada.