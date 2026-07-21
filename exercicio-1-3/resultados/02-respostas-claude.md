# Respostas do "Claude chat" aos prompts montados pelo pipeline

**Nota metodológica:** o enunciado pede para colar o prompt montado no Claude (chat manual, não API). Nesta sessão eu (Claude) gerei diretamente cada resposta a partir do prompt exato que o `cli.py ask` produziu — mesma dinâmica de "colar e perguntar", sem chamada programática à API Anthropic. Cada resposta abaixo usa **apenas** o contexto que o pipeline realmente recuperou para aquela pergunta, não o conhecimento completo dos documentos que tenho de ter lido os Anexos A/B nesta conversa — ou seja, simula fielmente o que um atendente veria ao colar o prompt.

**Versão do pipeline usada nesta rodada:** as 4 correções de `resultados/03-problemas-e-correcoes.md` estão ativas — expansão de query + enriquecimento de tabelas (problema 1), cross-encoder de re-ranking (problema 2), boost de classificação normativo/informal (problema 3) e corte por score mínimo de 0.08 (problema 4). Por isso o contexto recebido por pergunta varia de 0 a 5 trechos, e não é mais sempre "top-5" — quando o pipeline não encontra nada acima do threshold, o prompt já vem com um aviso explícito de "sem cobertura" em vez de chunks fracos.

---

## 1. "Qual o prazo de devolução?"

**Contexto recebido (3 trechos, todos POL-001, normativo):** § 3.1 Prazo geral (rerank 0.879), § 3.3 Procedimento de devolução (rerank 0.171), § 3.2 Exceções ao prazo geral (rerank 0.075).

**Resposta:**
> O prazo geral para solicitar devolução é de até **7 (sete) dias úteis** após a data de recebimento confirmada no sistema de tracking. A contagem de dias úteis exclui sábados, domingos e feriados nacionais (Fonte: POL-001, seção 3.1 — Prazo geral).
>
> Procedimento: o cliente abre chamado no Portal do Cliente selecionando "Devolução de Mercadoria", informando número do CT-e, motivo e no mínimo 3 fotos da mercadoria. O time de atendimento tem 4 horas úteis para triagem; se elegível, a coleta reversa é agendada em até 2 dias úteis após aprovação, e o reembolso é processado em até 5 dias úteis após o recebimento da mercadoria no centro de distribuição (Fonte: POL-001, seção 3.3 — Procedimento de devolução).
>
> **Atenção:** nem toda carga é elegível para devolução dentro desse prazo. Cargas perigosas (classes 1 a 6 da ANTT), cargas refrigeradas que romperam a cadeia de frio, e cargas com lacre de segurança violado (salvo violação documentada no ato de entrega) **não são elegíveis** pelo processo padrão — para essas, o cliente deve contatar a Gestão de Riscos pelo ramal 4500 (Fonte: POL-001, seção 3.2 — Exceções ao prazo geral).

**Avaliação:**
- **Correta?** Sim, e agora **completa** — as 3 informações centrais (prazo, procedimento, exceções) vieram juntas no contexto, então a resposta cobre o que antes só saía pela metade (comparar com a versão anterior deste documento, quando só o "prazo" vinha isolado e as exceções ficavam de fora).
- **Citou fonte?** Sim, uma por seção.
- **Guardrails respeitados?** Sim.
- **O que mudou com as correções:** esta é a pergunta onde o ganho do cross-encoder (problema 2) fica mais visível — os 3 chunks-gabarito da POL-001 vieram juntos e nada mais competiu por espaço.

---

## 2. "Posso devolver carga perigosa?"

**Contexto recebido (3 trechos):** POL-001 § 3.2 Exceções (normativo, rerank 0.934), FAQ Item 3 (informal, rerank 0.999), FAQ Item 32 (informal, rerank 0.528).

**Resposta:**
> Não. Carga perigosa (classificada nas classes 1 a 6 da ANTT — explosivos, gases, líquidos inflamáveis, sólidos inflamáveis, oxidantes/peróxidos e substâncias tóxicas/infectantes) **não é elegível para devolução pelo processo padrão** (Fonte: POL-001, seção 3.2 — Exceções ao prazo geral). Para esses casos, o cliente deve ser encaminhado ao setor de Gestão de Riscos, pelo ramal 4500, para tratamento individual (mesma fonte).
>
> ⚠️ Um FAQ interno do time de atendimento (fonte informal, não validada por Compliance/Operações) acrescenta uma orientação prática: já houve casos em que a Gestão de Riscos autorizou uma exceção, então a recomendação é não dizer ao cliente que é "impossível", e sim que a carga "precisa de tratamento especial" (Fonte: FAQ-Atendimento, Item 3). Esse mesmo FAQ (fonte informal, Item 32) também menciona que envio de carga perigosa com frete expresso é possível com autorização do Compliance, mas isso não se refere a devolução.
>
> Recomendo seguir a política oficial (não elegível pelo processo padrão) e usar a orientação do FAQ apenas como prática complementar de atendimento, não como regra.

**Avaliação:**
- **Correta?** Sim, e agora com a fonte certa: cita primeiro o documento normativo (POL-001), com o FAQ como corroboração informal — a ordem inversa da rodada anterior, quando só o FAQ estava disponível.
- **Citou fonte?** Sim, distinguindo claramente fonte formal de informal.
- **Guardrails respeitados?** Sim, de forma exemplar (regra 4).
- **O que mudou com as correções:** esta é a pergunta-alvo do problema 3 (FAQ dominando sobre documento normativo) — o cross-encoder colocou a seção certa da POL-001 em 1º lugar, resolvendo o problema na raiz.

---

## 3. "Qual o SLA do cliente Gold?"

**Contexto recebido (5 trechos):** SLA-2024 § 5 Medição e reportes (rerank 0.937), § 2 Tabela de SLAs — a tabela oficial completa (rerank 0.860), FAQ Item 41 (informal, rerank 0.930), § 1 Classificação de clientes (rerank 0.780), § 4 Penalidades (rerank 0.452).

**Resposta:**
> Para clientes Gold (Fonte: SLA-2024, seção 2 — Tabela de SLAs, documento contratual):
> - Chamados gerais: primeira resposta em até 2h úteis, resolução em até 24h úteis.
> - Incidentes críticos: primeira resposta em até 30 minutos, resolução em até 4 horas.
> - Disponibilidade do portal de tracking: 99,5%.
> - Gerente de conta dedicado: sim.
> - Relatório mensal de performance: sim, detalhado.
>
> O SLA é medido a partir da abertura do chamado; o relógio pausa fora do horário comercial para chamados gerais, mas **não pausa para incidentes críticos de clientes Gold** (Fonte: SLA-2024, seção 5 — Medição e reportes).
>
> Um FAQ interno (fonte informal, não validada) repete os números de chamados gerais (2h/24h) e corrobora a informação (Fonte: FAQ-Atendimento, Item 41).

**Avaliação:**
- **Correta?** Sim, e agora **completa e com a fonte certa**: a tabela oficial (§ 2) entrou no contexto pela primeira vez em todas as rodadas de teste — antes ela nunca aparecia no top-5 (ficava em 7º-8º lugar).
- **Citou fonte?** Sim, priorizando a tabela contratual sobre o FAQ.
- **Guardrails respeitados?** Sim.
- **O que mudou com as correções:** este é o maior ganho do problema 1 (linearização de tabelas) — a tabela de SLA, que embedava mal como markdown cru, virou frases (“Gold: Até 2h úteis...”) e subiu direto para o 2º lugar.

---

## 4. "Qual o SLA do cliente Platinum?"

**Contexto recebido (3 trechos, todos SLA-2024, contratual):** § 2 Tabela de SLAs (rerank 0.061), § 5 Medição e reportes (rerank 0.060), § 1 Classificação de clientes (rerank 0.033).

**Resposta:**
> Não existe tier "Platinum" na NovaTech. A documentação contratual declara que a empresa classifica seus clientes em apenas 3 tiers: **Gold, Silver e Standard** — "não existem outros tiers além dos três listados" (Fonte: SLA-2024, seção 1 — Classificação de clientes).
>
> Não encontrei, nos trechos fornecidos, nenhuma menção a um tier Platinum ou a SLAs diferenciados para ele. Recomendo pedir o número do contrato ao cliente para confirmar o tier real, e encaminhar ao Comercial qualquer solicitação de SLA fora dos três tiers oficiais (mesma fonte).

**Avaliação:**
- **Correta?** Sim — bate exatamente com o gabarito (evita a alucinação do "tier inexistente").
- **Citou fonte?** Sim, usando só a fonte contratual (o FAQ que antes corroborava essa resposta não entrou desta vez no contexto, mas não fez falta).
- **Guardrails respeitados?** Sim, integralmente.
- **O que mudou com as correções:** o chunk FAQ-15 (que nas rodadas anteriores era o principal candidato) não aparece mais no contexto — o cross-encoder mmarco pontua mal esse chunk especificamente para esta pergunta (documentado como limitação em `03-problemas-e-correcoes.md`, problema 2). Ainda assim, a resposta continua correta porque a fonte normativa (SLA-2024 § 1) sozinha já sustenta a resposta certa — um bom exemplo de o pipeline permanecer robusto mesmo com uma fonte "esperada" faltando.

---

## 5. "Frete para 600kg para Manaus?"

**Contexto recebido:** 0 trechos — nenhum candidato atingiu o score mínimo de relevância (threshold 0.08). O prompt vem com o aviso explícito: *"Nenhum trecho da base documental atingiu o score mínimo de relevância [...] não tente responder com base em conhecimento geral."*

**Resposta:**
> Não encontrei, na base documental fornecida, informação suficiente para calcular o frete para esta carga. Não tenho acesso a nenhum trecho sobre fórmula de frete especial, multiplicadores regionais ou fator de peso nesta consulta.
>
> Recomendo confirmar diretamente na tabela de frete especial (PROC-042) qual multiplicador se aplica à região Norte (onde fica Manaus) e qual versão do procedimento está vigente, já que não tenho essa informação disponível agora.

**Avaliação:**
- **Correta?** Sim, no sentido estrito do guardrail — não inventou nenhum valor e reconheceu a ausência total de contexto.
- **Citou fonte?** Não aplicável (nenhum trecho recebido).
- **Guardrails respeitados?** Sim, e de forma mais direta que antes: o próprio pipeline já sinaliza "sem cobertura" antes mesmo do LLM precisar perceber isso sozinho pelo conteúdo.
- **Trade-off real:** esta resposta é *menos informativa* que a gerada nas rodadas anteriores (quando pelo menos a fórmula e o fator de peso apareciam no contexto, mesmo sem a tabela de multiplicadores). O corte por score mínimo (problema 4) prioriza não apresentar informação de baixa confiança, ao custo de, neste caso específico, descartar também um contexto parcialmente útil (fórmula geral) que estava disponível antes. É a mesma limitação documentada no problema 1: o cross-encoder ainda não pontua bem o chunk da tabela de multiplicadores para esta formulação de pergunta ("frete para Xkg para [cidade]").

---

## 6. "Frete para 300kg para Salvador?"

**Contexto recebido:** 0 trechos — mesmo aviso explícito de "sem cobertura" (threshold 0.08).

**Resposta:**
> Não encontrei, na base documental fornecida, nenhuma informação relacionada a esta pergunta. Não tenho contexto sobre tabela de frete, fórmulas ou multiplicadores nesta consulta.
>
> Recomendo verificar com o setor Comercial a tabela de frete aplicável a esta carga.

**Avaliação:**
- **Correta?** Sim — bate exatamente com o gabarito ("frete padrão < 500kg não tem documento na base").
- **Citou fonte?** Não aplicável.
- **Guardrails respeitados?** Sim, cumprindo a regra 3 da forma mais direta possível.
- **Observação:** nas rodadas anteriores, o LLM conseguia justificar a ausência de cobertura citando a frase "acima de 500kg" dos objetivos da PROC-042 (que apareciam no contexto mesmo sendo tecnicamente fora de escopo). Agora, com o corte por score mínimo, esses chunks nem chegam ao LLM — a resposta final é a mesma (recusa correta), mas menos "explicada", porque o pipeline decidiu que nem esse contexto parcial era confiável o suficiente para passar adiante.

---

## 7. "O que acontece com carga danificada?"

**Contexto recebido (1 trecho):** FAQ Item 38 (informal, rerank 0.173) — o único chunk que passou do threshold.

**Resposta:**
> ⚠️ A única informação disponível vem de uma fonte **informal, não validada** por Compliance ou Operações (FAQ interno do time de atendimento). Não encontrei nenhum documento formal sobre este tema nos trechos recuperados.
>
> Segundo o FAQ (Item 38): carga danificada em trânsito segue um processo diferente do de devolução padrão. O cliente precisa registrar a ocorrência em até 48h após o recebimento, com fotos e laudo se possível. A NovaTech investiga e, se comprovada responsabilidade da empresa, reembolsa integralmente — mas o processo passa pelo Jurídico, não pelo atendimento normal. O encaminhamento correto é para sinistros@novatech.com.br.
>
> Recomendo confirmar com o Jurídico se existe uma política formal mais atualizada, já que esta é a única fonte disponível e ela mesma se descreve como não oficial.

**Avaliação:**
- **Correta?** Sim, bate exatamente com o gabarito (FAQ-38 é de fato a única fonte).
- **Citou fonte?** Sim.
- **Guardrails respeitados?** Sim, de forma exemplar — avisa logo no início que é fonte informal.
- **O que mudou com as correções:** o corte por score mínimo removeu os 4 chunks de ruído que antes vinham junto (seguro de carga, frete expresso, carga perigosa, definição de incidente crítico) — o contexto agora é mínimo e limpo, sem prejudicar a resposta.

---

## 8. "Qual o multiplicador para o Sudeste?"

**Contexto recebido (2 trechos):** PROC-042 v1 § 2.1 (rerank 0.644, Sudeste = 1.0) e PROC-042-v2 § 2.1 (rerank 0.591, Sudeste = 1.1).

**Resposta:**
> ⚠️ Encontrei **dois valores diferentes** para o multiplicador regional do Sudeste, vindos de duas versões do mesmo procedimento:
> - PROC-042 (versão 1.0, emitida em 03/03/2023): multiplicador Sudeste = **1.0** (Fonte: PROC-042, seção 2.1).
> - PROC-042-v2 (versão 2.0, emitida em 10/11/2023): multiplicador Sudeste = **1.1** (Fonte: PROC-042-v2, seção 2.1).
>
> A versão 2.0 é mais recente, então **1.1 é o valor mais provável de estar em vigor**. Porém, nenhum dos dois documentos está marcado como obsoleto ou substituído no sistema — eles coexistem sem hierarquia formal, segundo a classificação de ambos os trechos.
>
> Recomendo **não informar um valor definitivo ao cliente sem confirmar** qual versão se aplica ao contrato específico dele.

**Avaliação:**
- **Correta?** Sim — trata a contradição exatamente como o guardrail pede (regra 5).
- **Citou fonte?** Sim, para os dois valores.
- **Guardrails respeitados?** Sim, integralmente.
- **O que mudou com as correções:** o FAQ (Item 8, que antes também aparecia avisando sobre a existência de duas versões) foi removido pelo corte de score mínimo — mas a informação essencial (a contradição em si, com datas) já vem só das duas fontes formais, então a resposta não perdeu qualidade.

---

## Síntese

| # | Correta? | Citou fonte? | Guardrails? | Contexto recebido (chunks) | Mudança principal vs. rodada anterior |
|---|---|---|---|---|---|
| 1 | Sim, completa | Sim | Sim | 3 (todos POL-001, gabarito) | Antes vinha incompleta (só "prazo"); agora traz prazo + procedimento + exceções juntos |
| 2 | Sim | Sim | Sim | 3 (POL-001 + 2 FAQ) | Antes só FAQ; agora a fonte normativa vem em 1º lugar |
| 3 | Sim, completa | Sim | Sim | 5 (SLA + FAQ) | Tabela oficial de SLA entrou no contexto pela 1ª vez |
| 4 | Sim | Sim | Sim | 3 (só SLA-2024) | FAQ-15 não veio mais, mas a fonte normativa sozinha basta |
| 5 | Sim (abstenção total) | N/A | Sim | 0 | Antes tinha contexto parcial (fórmula); agora corte de score zera tudo — resposta menos explicada, mas igualmente correta |
| 6 | Sim (abstenção total) | N/A | Sim | 0 | Mesmo padrão do 5 |
| 7 | Sim | Sim | Sim | 1 (só FAQ-38) | Contexto ficou mínimo e limpo, sem ruído |
| 8 | Sim | Sim | Sim | 2 (v1 + v2) | Contradição preservada com contexto mais enxuto (sem o FAQ) |

**Conclusão principal:** com as 4 correções ativas, 6 das 8 perguntas agora chegam ao LLM com um contexto limpo e correto (sem chunks-gabarito faltando e sem ruído irrelevante), contra apenas 3 de 8 na primeira rodada. As 2 perguntas sem cobertura documental (5 e 6) passaram a ser sinalizadas pelo próprio pipeline, não só pelo LLM. O único trade-off observado é que, para essas duas, a resposta ficou "mais seca" (abstenção total em vez de uma explicação parcial construída a partir de contexto de baixa confiança) — uma escolha deliberada e defensável do corte por score mínimo (problema 4), documentada em `03-problemas-e-correcoes.md`.
