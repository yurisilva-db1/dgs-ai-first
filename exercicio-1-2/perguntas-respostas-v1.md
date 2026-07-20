# Teste do System Prompt v1 — Rodada 1

**Ambiente de teste:** conversa nova no Claude, com o `system-prompt-v1.md` colado como instrução inicial, seguido dos 3 chunks simulados fornecidos no enunciado:

> **Chunk A** (POL-001, seção 3.2): prazo geral de devolução de 7 dias úteis, exceto cargas perigosas (classes 1–6 ANTT); abertura de chamado no portal com fotos.
> **Chunk B** (Tabela SLA-2024): SLA de resposta/resolução por tier (Gold, Silver, Standard).
> **Chunk C** (PROC-042-v2, seção 2): fórmula de frete especial = valor base × multiplicador regional, com multiplicadores por região (Sul 1.3, Sudeste 1.1, Norte 1.8, Nordeste 1.5, Centro-Oeste 1.4).

As perguntas foram feitas como se fosse o atendente, em mensagens separadas na mesma conversa.

---

## Pergunta 1 — "Qual o prazo de devolução para carga perigosa?"

**Resposta obtida:**
> Cargas classificadas como perigosas (classes 1 a 6 da ANTT) não seguem o prazo padrão de devolução de 7 dias úteis — essa categoria é uma exceção à regra geral, ou seja, não é elegível para devolução pelo processo padrão. A documentação fornecida não especifica um prazo alternativo para esse tipo de carga. [Fonte: Política de Devolução]

**Análise:**
| Critério | Avaliação |
|---|---|
| Correta / sem alucinação | ✅ Sim — não inventou um prazo alternativo, respeitou a exceção. |
| Citou a fonte | ⚠️ Parcial — cita "Política de Devolução" mas não o código/seção (POL-001, seção 3.2). |
| Guardrail 3 (dizer que não encontrou + sugerir supervisor) | ❌ Falhou — identificou a lacuna, mas **não sugeriu explicitamente escalar ao supervisor**, como o guardrail exige. |
| Guardrail 4 (tom) | ✅ Adequado |

---

## Pergunta 2 — "Meu cliente é Gold, qual o SLA de resolução?"

**Resposta obtida:**
> Para o cliente Gold, o SLA de resolução é de até 24 horas úteis. [Fonte: Tabela SLA-2024]

**Análise:**
| Critério | Avaliação |
|---|---|
| Correta / sem alucinação | ✅ Sim — bate exatamente com o Chunk B. |
| Citou a fonte | ✅ Sim, nome do documento indicado. |
| Guardrails | ✅ Todos respeitados. |
| Observação | Resposta ideal — não precisou de escalonamento, e não há ambiguidade nos dados. Serve de referência do que "dar certo" parece. |

---

## Pergunta 3 — "Quanto custa o frete para 600kg para Manaus?"

**Resposta obtida:**
> Manaus está na região Norte, cujo multiplicador regional é 1.8. O frete especial é calculado como valor base × multiplicador regional. Não tenho o valor base tabelado disponível no momento, mas o multiplicador aplicável seria 1.8. [Fonte: PROC-042-v2]

**Análise:**
| Critério | Avaliação |
|---|---|
| Correta / sem alucinação | ✅ Sim — corretamente **não inventou** o "valor base", que não está em nenhum chunk. |
| Citou a fonte | ⚠️ Parcial — cita o documento mas não a seção (seção 2). |
| Guardrail 3 (dizer que não encontrou + sugerir supervisor) | ❌ Falhou — disse que "não tem o valor base no momento" (soa como uma limitação temporária/técnica) em vez de declarar claramente que a informação **não está disponível na documentação** e sugerir escalonamento/consulta à tabela de tarifas. |
| Guardrail 4 (tom) | ✅ Adequado |

---

## Síntese da análise crítica

- **O que funcionou bem:** o prompt v1 conteve a alucinação nos dois casos mais arriscados (Q1: não inventou prazo para carga perigosa; Q3: não inventou o valor base do frete). O guardrail 2 ("nunca inventar prazos ou valores") está sendo respeitado de forma consistente.
- **Onde errou:**
  1. **Escalonamento inconsistente (guardrail 3):** nas duas perguntas com lacuna de informação (Q1 e Q3), o modelo identificou a ausência de dado mas não formulou a sugestão explícita de escalar ao supervisor. A seção 2 do prompt lista a regra, mas a seção 5 (instruções de uso dos chunks) não a reforça no momento exato em que uma lacuna é detectada — a regra fica "solta" no prompt em vez de acoplada ao comportamento esperado.
  2. **Citação de fonte imprecisa:** o formato `[Fonte: nome do documento]` foi seguido, mas sem código/seção, o que dificulta auditoria (o atendente não sabe se é a seção 3.1, 3.2 etc.). O guardrail 1 diz "citar a fonte", mas o prompt não define o nível de granularidade exigido.
  3. **Ambiguidade de linguagem em Q3:** "não tenho o valor base disponível no momento" pode ser lido como uma limitação passageira do assistente, e não como "essa informação não existe na documentação consultada" — isso é uma diferença importante para o atendente, que pode achar que basta perguntar de novo depois.

Esses três pontos serão o alvo da iteração para o system prompt v2.
