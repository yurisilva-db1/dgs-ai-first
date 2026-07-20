# Teste do System Prompt v3 — Rodada 4: Reteste do Cenário de Conflito

**Objetivo:** confirmar que o `system-prompt-v3.md` corrige o gap encontrado no Cenário 2 da Rodada 3 (regra geral de versão ignorando a regra de transição específica), sem regressão nos demais cenários.

---

## Cenário 2 (reteste) — Contradição de versões + regra transitória

**Pergunta:** "Quanto custa o frete para 600kg para Manaus?"

**Chunks recuperados:** PROC-042v2-A, PROC-042v2-B, PROC-042-B (versão antiga), PROC-042v2-E (disposições transitórias) — mesmo conjunto da Rodada 3.

**Resposta obtida (v3):**
> Manaus está na região Norte. Encontrei duas versões do procedimento de frete especial com multiplicadores diferentes para o Norte: PROC-042 (versão original) usa 1.6, e PROC-042-v2 usa 1.8. [Fonte: PROC-042, seção 2.1 e PROC-042-v2, seção 2.1]
>
> A documentação também traz uma regra de transição (PROC-042-v2, seção 5): chamados abertos antes de 01/12/2023 usam os multiplicadores da versão antiga; chamados a partir dessa data usam a versão nova. [Fonte: PROC-042-v2, seção 5]
>
> Para eu indicar o multiplicador correto, preciso saber: **quando este chamado/solicitação de frete foi aberto?** Sem essa informação, não posso afirmar com segurança se o multiplicador aplicável é 1.6 ou 1.8.
>
> Além disso, o valor base não consta no contexto fornecido — mesmo com a data do chamado, ainda seria necessário consultar a tabela de tarifas vigente para calcular o valor final. Sugiro escalar ao supervisor ou obter a data de abertura do chamado e o valor base antes de informar um preço ao cliente.

**Análise comparativa:**
| Critério | Rodada 3 (v2) | Rodada 4 (v3) |
|---|---|---|
| Sinalizou a divergência entre versões | ✅ | ✅ |
| Citou fontes com granularidade | ✅ | ✅ |
| Verificou a regra de transição (PROC-042v2-E) antes de decidir a versão | ❌ ignorou | ✅ identificou e aplicou o critério |
| Evitou presumir que o chamado é "novo" sem essa informação | ❌ presumiu implicitamente | ✅ perguntou a data em vez de presumir |
| Não inventou o valor base | ✅ | ✅ |
| Escalonamento/pedido de dado faltante | ✅ (só para o valor base) | ✅ (para a data do chamado **e** para o valor base) |

**Correção confirmada.** O v3 agora trata a escolha entre versões como dependente de um dado concreto (data de abertura do chamado) e, na ausência desse dado, pergunta em vez de presumir — eliminando a alucinação de premissa identificada na Rodada 3.

---

## Confirmação de não regressão nos demais cenários

Os cenários 1, 3, 4, 5 e 6 da Rodada 3 não envolvem conflito de versão com regra de transição, portanto a mudança da seção 3 do v3 não altera o caminho de raciocínio usado neles. Reconferindo rapidamente cada um contra o texto do v3:

| Cenário | Depende da seção 3 alterada? | Resultado esperado |
|---|---|---|
| 1 — Tier Platinum inexistente | Não (não há conflito de versão) | Mantém comportamento da Rodada 3 (✅) |
| 3 — Carga danificada (FAQ única fonte) | Não | Mantém (✅) |
| 4 — Carga perigosa + frete expresso (FAQ única fonte) | Não | Mantém (✅) |
| 5 — Inversão de regra (devolução de carga perigosa) | Não | Mantém (✅) |
| 6 — Frete padrão sem cobertura | Não | Mantém (✅) |

Nenhum desses cenários aciona a lógica de "conflito entre versões do mesmo documento", então a alteração no v3 é cirúrgica: resolve o gap do Cenário 2 sem tocar no comportamento validado dos demais.

---

## Síntese geral (Rodadas 3 e 4)

Testar contra os cenários de conflito do Anexo B — além das 3 perguntas simples das rodadas 1 e 2 — revelou um tipo de falha mais sutil do que alucinação de número: **alucinação de premissa**, em que o assistente escolhe silenciosamente qual regra aplicar sem ter o dado necessário para essa escolha. O guardrail "nunca invente prazos ou valores" não cobria esse caso por si só; foi necessário adicionar explicitamente, na v3, que a mesma cautela vale para a **escolha entre regras concorrentes**, tratando a ausência do dado decisório (aqui, a data de abertura do chamado) como mais uma lacuna a esclarecer — não como algo a presumir.

Com isso, o `system-prompt-v3.md` é a versão recomendada para uso, cobrindo tanto os guardrails originais do Product Specialist quanto as 5 armadilhas de conflito descritas no Anexo B.
