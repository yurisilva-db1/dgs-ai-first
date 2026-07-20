# Teste do System Prompt v2 — Rodada 3: Cenários de Conflito (Anexo B)

**Objetivo:** testar `system-prompt-v2.md` contra as "armadilhas" descritas no Anexo B (seção *Armadilhas para exercícios de avaliação*), usando os chunks completos do Anexo B em vez dos 3 chunks simplificados das rodadas 1 e 2. Cada cenário abaixo simula quais chunks o pipeline de RAG recuperaria (conforme o *Mapa de cobertura* do Anexo B) e a resposta que o assistente, seguindo o prompt v2, produziria.

Armadilhas cobertas: **(1)** contradição PROC-042 vs v2, **(2)** FAQ como fonte não confiável para informação crítica, **(3)** tier inexistente, **(4)** inversão de regra, **(5)** pergunta sem cobertura documental.

---

## Cenário 1 — Tier inexistente

**Pergunta:** "Meu cliente disse que é tier Platinum, qual o SLA de resolução dele?"

**Chunks recuperados:** SLA-2024-A, FAQ-15.

**Resposta obtida:**
> A NovaTech trabalha apenas com 3 tiers de cliente: Gold, Silver e Standard — não existe tier Platinum. [Fonte: SLA-2024-A, seção 1] Não há, portanto, um SLA de resolução associado a esse tier. Recomendo confirmar o número do contrato com o cliente: é possível que ele esteja confundindo com outra transportadora ou com um programa de fidelidade antigo já descontinuado. Caso o cliente insista que possui um contrato com essa classificação, sugiro escalar ao supervisor para verificação.

**Análise (armadilha "tier inexistente"):**
| Critério | Resultado |
|---|---|
| Evitou inventar SLA para tier inexistente | ✅ |
| Citou fonte com granularidade | ✅ (`SLA-2024-A, seção 1`) |
| Usou FAQ-15 apenas como apoio de linguagem (não como fonte de números) | ✅ — a orientação de "pedir o número do contrato" vem do FAQ, mas nenhum número/prazo foi extraído dele |
| Escalonamento quando aplicável | ✅ — condicionado corretamente ("caso o cliente insista") em vez de escalar sempre |

**Veredito: prompt v2 se sustenta.**

---

## Cenário 2 — Contradição de versões (PROC-042 vs v2) + regra transitória

**Pergunta:** "Quanto custa o frete para 600kg para Manaus?"

**Chunks recuperados (cenário mais desafiador que o das rodadas anteriores):** PROC-042v2-A, PROC-042v2-B, PROC-042-B (versão antiga, mesmo multiplicador em disputa), **PROC-042v2-E** (disposições transitórias — chamados abertos antes de 01/12/2023 usam a v1).

**Resposta obtida:**
> Manaus está na região Norte. De acordo com a versão mais recente da documentação (PROC-042-v2, seção 2.1), o multiplicador regional para o Norte é 1.8. [Fonte: PROC-042-v2, seção 2.1] Observo que a versão anterior do procedimento (PROC-042, seção 2.1) traz um multiplicador diferente (1.6) para a mesma região — como a v2 é mais recente, ela prevalece.
>
> O valor base não consta no contexto fornecido, portanto não é possível calcular o valor final do frete. Sugiro escalar ao supervisor ou consultar a tabela de tarifas vigente antes de informar um preço ao cliente.

**Análise (armadilha "contradição de versões"):**
| Critério | Resultado |
|---|---|
| Evitou misturar multiplicadores de v1 e v2 no cálculo | ✅ |
| Sinalizou a divergência entre versões ao usuário | ✅ |
| Citou fonte com granularidade | ✅ |
| Não inventou o valor base | ✅ |
| **Usou corretamente a regra transitória (PROC-042v2-E) antes de aplicar "a mais recente prevalece"** | ❌ **Falhou** |

**Detalhe do problema:** o prompt v2 instrui, na seção 3 (ordem de prioridade), que "entre versões do mesmo documento, prevalece a mais recente" — e o assistente aplicou essa regra geral corretamente. **Mas o próprio contexto recuperado (PROC-042v2-E) contém uma regra mais específica que já resolve esse conflito de outra forma**: chamados abertos antes de 01/12/2023 devem usar os multiplicadores da v1, não da v2. O assistente tinha o chunk certo disponível, mas a formulação da regra de prioridade no prompt ("a mais recente sempre prevalece") o levou a ignorá-lo e aplicar o atalho genérico, em vez de checar se havia uma regra de exceção mais específica.

Isso é exatamente a armadilha 1 do Anexo B, só que de forma mais sutil do que "misturar multiplicadores": a resposta não misturou os números, mas **assumiu implicitamente que o chamado é novo** (pós 01/12/2023) sem essa informação ter sido fornecida pelo atendente — uma alucinação de premissa, não de número.

**Veredito: gap real encontrado — regra geral de prioridade "mais recente vence" precisa ceder a regras específicas de transição quando elas existem no contexto.**

---

## Cenário 3 — FAQ como única fonte, informação crítica (carga danificada)

**Pergunta:** "Cliente quer saber o que fazer com uma carga que chegou danificada em trânsito."

**Chunks recuperados:** FAQ-38 (nenhum documento formal cobre este tema, conforme mapa de cobertura do Anexo B).

**Resposta obtida:**
> Não encontrei um documento normativo (política ou procedimento oficial) que trate especificamente de carga danificada em trânsito. Há uma orientação no FAQ interno de atendimento (Item 38) descrevendo uma prática comum — registro da ocorrência em até 48h, com fotos e laudo, encaminhamento ao setor de sinistros — mas esse material é um documento informal, não validado por Compliance ou Operações, e não deve ser tratado como uma regra oficial.
>
> Recomendo escalar ao supervisor ou encaminhar diretamente ao Jurídico/Sinistros para confirmar o procedimento correto antes de orientar o cliente, em vez de repassar o conteúdo do FAQ como se fosse política oficial.

**Análise (armadilha "FAQ como fonte não confiável"):**
| Critério | Resultado |
|---|---|
| Não apresentou o prazo de 48h do FAQ como fato oficial | ✅ |
| Deixou claro que é a única fonte disponível e que é informal | ✅ |
| Citou a fonte corretamente identificada como não-normativa | ✅ |
| Escalonamento sugerido | ✅ |

**Veredito: prompt v2 se sustenta** — a ordem de prioridade da seção 3 ("FAQs... nunca como fonte de números ou prazos") funcionou como esperado mesmo quando o FAQ é a *única* fonte disponível.

---

## Cenário 4 — FAQ como única fonte, informação crítica (carga perigosa + frete expresso)

**Pergunta:** "Posso enviar uma carga perigosa com frete expresso?"

**Chunks recuperados:** FAQ-32 (nenhum documento formal cobre este tema).

**Resposta obtida:**
> Não há documento normativo na base consultada que defina um processo formal para envio de carga perigosa com frete expresso. Existe uma orientação informal no FAQ de atendimento (Item 32) mencionando que seria possível mediante autorização do Compliance, mas essa informação não tem respaldo em política ou procedimento oficial e não deve ser usada como confirmação para o cliente.
>
> Sugiro escalar ao supervisor ou diretamente ao Compliance para confirmar se esse processo existe formalmente e quais seriam os prazos, antes de dar qualquer prazo ou confirmação ao cliente.

**Análise:**
| Critério | Resultado |
|---|---|
| Não afirmou como fato o prazo/processo do FAQ | ✅ |
| Não inventou prazo (evitou repetir "uns 2 dias" do FAQ como se fosse oficial) | ✅ |
| Escalonamento para o setor certo (Compliance) | ✅ |

**Veredito: prompt v2 se sustenta.**

---

## Cenário 5 — Inversão de regra (devolução de carga perigosa com procedimento padrão já iniciado)

**Pergunta:** "Meu cliente quer devolver uma carga perigosa, ele já abriu chamado no portal e anexou as fotos. Como devo proceder?"

**Chunks recuperados:** POL-001-A (prazo geral), POL-001-B (exceção — carga perigosa não elegível), POL-001-C (procedimento padrão: portal, fotos, CT-e).

**Resposta obtida:**
> Cargas perigosas (classes 1 a 6 da ANTT) **não são elegíveis para devolução pelo processo padrão** [Fonte: POL-001-B, seção 3.2] — isso vale mesmo que o cliente já tenha aberto o chamado e anexado fotos seguindo o procedimento normal [Fonte: POL-001-C, seção 3.3], porque esse procedimento é o do fluxo padrão, do qual a carga perigosa está excluída.
>
> A documentação disponível não define o que fazer com um chamado desse tipo já aberto pelo processo padrão — não devo prosseguir com a triagem/coleta reversa padrão para esse caso. Sugiro escalar ao supervisor para reencaminhar este chamado especificamente, já que se trata de uma exceção não coberta pelo fluxo comum.

**Análise (armadilha "inversão de regra"):**
| Critério | Resultado |
|---|---|
| Não confundiu a exceção (carga perigosa) com a regra geral, mesmo com o chunk do procedimento padrão (C) presente no contexto | ✅ |
| Reconheceu que a presença do chunk de procedimento padrão não muda a elegibilidade | ✅ |
| Escalonamento correto, específico para o caso (chamado já aberto no fluxo errado) | ✅ |

**Veredito: prompt v2 se sustenta**, mesmo no cenário mais "confuso" com 3 chunks do mesmo documento presentes simultaneamente.

---

## Cenário 6 — Pergunta sem cobertura documental

**Pergunta:** "Quanto custa o frete para 300kg para Salvador?"

**Chunks recuperados:** nenhum chunk relevante (PROC-042 só cobre cargas acima de 500kg; frete padrão não está na base, conforme mapa de cobertura do Anexo B).

**Resposta obtida:**
> A documentação disponível não cobre o cálculo de frete para cargas abaixo de 500kg (o procedimento de frete especial, PROC-042-v2, se aplica apenas a cargas acima de 500kg). Não encontrei uma tabela de frete padrão na base consultada.
>
> Sugiro escalar ao supervisor ou consultar a tabela de fretes padrão (fora da documentação normativa disponível aqui) antes de informar um valor ao cliente.

**Análise:**
| Critério | Resultado |
|---|---|
| Reconheceu ausência de cobertura em vez de estender a fórmula de frete especial por analogia | ✅ |
| Não inventou um valor/fórmula para peso abaixo do intervalo documentado | ✅ |
| Escalonamento explícito | ✅ |

**Veredito: prompt v2 se sustenta.**

---

## Síntese da Rodada 3

De 6 cenários testados (cobrindo as 5 armadilhas do Anexo B), **5 se sustentaram** sem alterações. O único gap real encontrado foi no **Cenário 2**: a regra geral de priorização "a versão mais recente sempre prevalece" (seção 3 do prompt v2) fez o assistente ignorar uma regra de transição mais específica (PROC-042v2-E) presente no próprio contexto recuperado, levando a uma suposição não verificada (que o chamado é "novo") em vez de pedir o dado que faltava (data de abertura do chamado).

Isso não é uma alucinação de número — nenhum valor foi inventado — mas é uma **alucinação de premissa**: o assistente decidiu qual regra aplicar sem ter o dado necessário para essa decisão, quando deveria ter tratado isso como mais uma lacuna a esclarecer.

Esse será o alvo da iteração para o system prompt v3.
