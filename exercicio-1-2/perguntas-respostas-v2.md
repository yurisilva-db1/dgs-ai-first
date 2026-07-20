# Teste do System Prompt v2 — Rodada 2

**Ambiente de teste:** mesma conversa nova no Claude, agora com `system-prompt-v2.md` como instrução inicial, seguido dos mesmos 3 chunks simulados do enunciado (Chunk A — POL-001 seção 3.2; Chunk B — Tabela SLA-2024; Chunk C — PROC-042-v2 seção 2). Mesmas 3 perguntas, na mesma ordem.

---

## Pergunta 1 — "Qual o prazo de devolução para carga perigosa?"

**Resposta obtida:**
> Cargas classificadas como perigosas (classes 1 a 6 da ANTT) não são elegíveis para devolução pelo processo padrão de 7 dias úteis — essa é uma exceção explícita à regra geral. [Fonte: Chunk A]
>
> A documentação disponível não define um procedimento ou prazo alternativo para devolução de carga perigosa. Sugiro escalar ao supervisor para orientação sobre como tratar este caso antes de responder ao cliente.

**Análise:**
| Critério | Rodada 1 | Rodada 2 |
|---|---|---|
| Correta / sem alucinação | ✅ | ✅ |
| Citou a fonte com granularidade | ⚠️ ("Política de Devolução") | ✅ (`Chunk A`, identificador explícito do trecho fornecido) |
| Guardrail 3 (escalonamento explícito) | ❌ ausente | ✅ presente, em linha própria |
| Diferencia "não se aplica o padrão" de "não há solução" | ⚠️ implícito | ✅ explícito ("não define um procedimento... antes de responder ao cliente") |

**Correção confirmada.**

---

## Pergunta 2 — "Meu cliente é Gold, qual o SLA de resolução?"

**Resposta obtida:**
> Para o cliente Gold, o SLA de resolução é de até 24 horas úteis. [Fonte: Chunk B — Tabela SLA-2024]

**Análise:**
| Critério | Rodada 1 | Rodada 2 |
|---|---|---|
| Correta / sem alucinação | ✅ | ✅ (sem mudança) |
| Citou a fonte | ✅ | ✅ (levemente mais completa) |
| Guardrails | ✅ | ✅ |

**Sem regressão.** Como esperado, uma pergunta com resposta totalmente coberta pelo contexto não é afetada pelas mudanças da v2 — as correções eram direcionadas aos casos de lacuna, e este caso não tinha lacuna.

---

## Pergunta 3 — "Quanto custa o frete para 600kg para Manaus?"

**Resposta obtida:**
> Manaus está na região Norte. Para cargas acima de 500kg, a fórmula é: valor do frete = valor base × multiplicador regional, com multiplicador 1.8 para a região Norte. [Fonte: Chunk C — PROC-042-v2, seção 2]
>
> O valor base não consta na documentação disponível, portanto não é possível calcular o valor final do frete. Sugiro escalar ao supervisor ou consultar a tabela de tarifas vigente para obter o valor base antes de informar um preço ao cliente.

**Análise:**
| Critério | Rodada 1 | Rodada 2 |
|---|---|---|
| Correta / sem alucinação | ✅ | ✅ |
| Citou a fonte com granularidade | ⚠️ ("PROC-042-v2") | ✅ (`Chunk C — PROC-042-v2, seção 2`) |
| Guardrail 3 (escalonamento explícito) | ❌ ausente | ✅ presente |
| Linguagem sem ambiguidade ("não no momento" vs. "não consta na documentação") | ❌ ambígua | ✅ corrigida ("não consta na documentação disponível") |

**Correção confirmada.**

---

## Síntese da Rodada 2

Os três problemas identificados na análise crítica da v1 foram corrigidos sem introduzir regressões:

1. **Escalonamento explícito** passou a aparecer de forma consistente sempre que há lacuna (total ou parcial) — o protocolo de 3 passos da seção 5 (v2) fechou a lacuna de comportamento que existia na v1.
2. **Citação com granularidade** (documento + seção, ou identificador do chunk) tornou as respostas auditáveis — o atendente agora sabe exatamente qual trecho da documentação embasa a resposta.
3. **Linguagem sem ambiguidade** eliminou a confusão entre "não tenho agora" (parece temporário) e "não consta na documentação" (é uma lacuna real da fonte).
4. **Pergunta 2** (caso sem lacuna) permaneceu correta nas duas rodadas — confirma que as mudanças da v2 foram cirúrgicas e não degradaram o caso que já funcionava.

**Possível próxima iteração (não testada nesta rodada):** validar o comportamento quando o pipeline de RAG real recupera chunks conflitantes (ex.: PROC-042 v1 e v2 simultaneamente, ou perguntas sobre o tier "Platinum" inexistente) — cenários descritos no mapa de cobertura do Anexo B, mas fora do escopo das 3 perguntas desta atividade.
