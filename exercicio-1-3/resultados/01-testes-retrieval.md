# Testes de Retrieval — Pipeline RAG NovaTech

Pipeline: `python -m src.cli ask "<pergunta>" --k 5`, embeddings `all-MiniLM-L6-v2`, ChromaDB (espaço cosseno). Score = 1 − distância cosseno (1.0 = idêntico).

Gabarito: mapa de cobertura do Anexo B. Para cada pergunta, além do top-5 real, também rodei `--k 32` (toda a coleção) para verificar em que posição os chunks esperados pelo gabarito realmente ficam — isso mostra se o problema é "não existe no top-5 por pouco" ou "a busca falhou de forma grave".

## Legenda
- ✅ chunk esperado apareceu no top-5
- ⚠️ chunk esperado existe na coleção mas ficou fora do top-5 (posição real indicada)
- ❌ nenhum chunk relevante existe na base (esperado para perguntas sem cobertura)

---

### 1. "Qual o prazo de devolução?"
Esperado (gabarito): `POL-001-A` (3.1 Prazo geral), `POL-001-B` (3.2 Exceções). Pode aparecer: `POL-001-C` (3.3).

Top-5 recuperado:
| Chunk | Score | É esperado? |
|---|---|---|
| POL-001 § 3.5 Custos de devolução | 0.633 | não (mas cita "7 dias úteis" de passagem) |
| FAQ Item 3 (carga perigosa) | 0.571 | não |
| POL-001 § 3.3 Procedimento | 0.558 | parcialmente (chunk "pode aparecer") |
| PROC-042 v1 § 3 Prazo de entrega (frete especial) | 0.548 | não — domínio errado (frete, não devolução) |
| FAQ Item 41 (SLA resposta/resolução) | 0.532 | não |

**⚠️ Falha de retrieval:** § 3.1 "Prazo geral" (o chunk mais importante) ficou em **11º lugar** (score 0.477); § 3.2 "Exceções" ficou em **26º lugar** (score 0.371). Nenhum dos dois chunks-gabarito entrou no top-5.

---

### 2. "Posso devolver carga perigosa?"
Esperado: `POL-001-B` (3.2 Exceções). Pode aparecer: `FAQ-03`, `POL-001-A`.

Top-5 recuperado:
| Chunk | Score | É esperado? |
|---|---|---|
| FAQ Item 3 (carga perigosa) | 0.618 | ✅ (chunk "pode aparecer") |
| FAQ Item 22 (seguro de carga) | 0.579 | não |
| FAQ Item 38 (carga danificada) | 0.546 | não |
| FAQ Item 32 (carga perigosa + expresso) | 0.524 | não |
| PROC-042 v1 § 4 Condições especiais | 0.508 | não |

**⚠️ Falha de retrieval:** o chunk normativo POL-001 § 3.2 (a única fonte formal que diz que carga perigosa **não é elegível** para devolução padrão) ficou em **11º lugar** (score 0.472) — fora do top-5. O pipeline só devolve a fonte informal (FAQ).

---

### 3. "Qual o SLA do cliente Gold?"
Esperado: `SLA-2024-B` (§ 2 Tabela de SLAs). Pode aparecer: `SLA-2024-A`, `SLA-2024-C`.

> Nota: no documento fonte, "chamados gerais" e "incidentes críticos" estão na **mesma** tabela dentro de "## 2. Tabela de SLAs" (sem subheading própria) — então meu chunking (por header) gera 1 chunk único que cobre o que o gabarito trata como B+C.

Top-5 recuperado:
| Chunk | Score | É esperado? |
|---|---|---|
| SLA-2024 § 5 Medição e reportes | 0.549 | não |
| FAQ Item 41 (SLA resposta/resolução) | 0.549 | não (mas repete os números certos) |
| FAQ Item 15 (tier Platinum) | 0.543 | não |
| SLA-2024 § 1 Classificação de clientes | 0.514 | ✅ ("pode aparecer") |
| FAQ Item 27 (tracking) | 0.465 | não |

**⚠️ Falha de retrieval:** o chunk § 2 "Tabela de SLAs" (que tem a tabela oficial com os números de Gold) ficou em **8º lugar** (score 0.407) — fora do top-5.

---

### 4. "Qual o SLA do cliente Platinum?"
Esperado: `SLA-2024-A` (§ 1, contém "não existem outros tiers"). Pode aparecer: `FAQ-15`.

Top-5 recuperado:
| Chunk | Score | É esperado? |
|---|---|---|
| FAQ Item 15 (tier Platinum) | 0.596 | ✅ |
| SLA-2024 § 5 Medição e reportes | 0.502 | não |
| SLA-2024 § 1 Classificação de clientes | 0.496 | ✅ |
| FAQ Item 3 (carga perigosa) | 0.493 | não |
| FAQ Item 41 (SLA resposta/resolução) | 0.491 | não |

**✅ Retrieval correto** — os dois chunks esperados aparecem no top-5, com bom score.

---

### 5. "Frete para 600kg para Manaus?"
Esperado: `PROC-042v2-B` (§ 2.1 multiplicadores), `PROC-042v2-A` (§ 2 fórmula). Risco: `PROC-042-B` (versão antiga).

Top-5 recuperado:
| Chunk | Score | É esperado? |
|---|---|---|
| PROC-042 v1 § 1 Objetivo | 0.474 | não |
| PROC-042 v2 § 4 Condições especiais | 0.466 | não |
| PROC-042 v2 § 1 Objetivo | 0.460 | não |
| PROC-042 v2 § 2 Fórmula de cálculo | 0.457 | ✅ |
| PROC-042 v1 § 2 Fórmula de cálculo | 0.455 | não (versão antiga — contradição) |

**⚠️ Falha grave de retrieval:** a tabela "§ 2.1 Multiplicadores regionais" — a informação que de fato responde "quanto custa para Manaus" — não aparece nem no top-10 (v2 fica em 23º, score 0.285; v1 em 24º, score 0.282). Além disso, chunks da v1 e da v2 aparecem misturados no top-5, confirmando o risco de contradição do gabarito.

---

### 6. "Frete para 300kg para Salvador?"
Esperado (gabarito): nenhum chunk relevante — frete padrão (<500kg) não é coberto pela documentação.

Top-5 recuperado:
| Chunk | Score |
|---|---|
| PROC-042 v2 § 4 Condições especiais | 0.448 |
| FAQ Item 27 (tracking) | 0.444 |
| PROC-042 v1 § 1 Objetivo | 0.426 |
| PROC-042 v2 § 2 Fórmula | 0.420 |
| PROC-042 v1 § 2 Fórmula | 0.419 |

**❌ Como esperado, não há chunk realmente relevante** — mas o pipeline devolve 5 chunks "candidatos" mesmo assim, todos com score visivelmente mais baixo (0.42–0.45) que o das perguntas bem cobertas (0.5–0.7). Não há nenhum corte por score mínimo — quem precisa perceber que a base não cobre isso é o LLM (via guardrail do system prompt), não o pipeline.

---

### 7. "O que acontece com carga danificada?"
Esperado: `FAQ-38`. Observação do gabarito: nenhum documento formal cobre isso.

Top-5 recuperado:
| Chunk | Score | É esperado? |
|---|---|---|
| FAQ Item 38 (carga danificada) | 0.715 | ✅ |
| FAQ Item 22 (seguro de carga) | 0.632 | não |
| FAQ Item 32 (carga perigosa + expresso) | 0.630 | não |
| FAQ Item 3 (carga perigosa) | 0.580 | não |
| SLA-2024 § 3 Definição de incidente crítico | 0.553 | não |

**✅ Retrieval correto** — maior score de todos os testes (0.715), condizente com o gabarito.

---

### 8. "Qual o multiplicador para o Sudeste?"
Esperado: `PROC-042v2-B`. Risco: `PROC-042-B` (contradição 1.0 vs 1.1).

Top-5 recuperado:
| Chunk | Score | É esperado? |
|---|---|---|
| POL-001 § 3.4 Devoluções parciais | 0.530 | não |
| FAQ Item 8 (frete especial, avisa sobre v1/v2) | 0.511 | não (mas relevante) |
| PROC-042 v1 § 2.1 Multiplicadores | 0.506 | não (versão antiga) |
| PROC-042 v2 § 2.1 Multiplicadores | 0.505 | ✅ |
| POL-001 § 3.3 Procedimento de devolução | 0.485 | não |

**✅ Chunk certo recuperado, mas exatamente como o gabarito previu, a versão antiga (v1) vem junto e com score praticamente empatado (0.506 vs 0.505)** — confirma a armadilha de contradição PROC-042 v1/v2.

---

## Resumo

| # | Pergunta | Resultado |
|---|---|---|
| 1 | Prazo de devolução | ⚠️ falha — chunk-gabarito fora do top-5 |
| 2 | Devolver carga perigosa | ⚠️ falha — só fonte informal recuperada |
| 3 | SLA Gold | ⚠️ falha — tabela oficial fora do top-5 |
| 4 | SLA Platinum | ✅ correto |
| 5 | Frete 600kg Manaus | ⚠️ falha grave — tabela de multiplicadores nem no top-10 |
| 6 | Frete 300kg Salvador | ❌ esperado (sem cobertura), pipeline não sinaliza isso sozinho |
| 7 | Carga danificada | ✅ correto |
| 8 | Multiplicador Sudeste | ✅ chunk certo vem, mas empatado com versão antiga (contradição) |

5 de 8 perguntas expõem algum problema real de retrieval (não simulado) com a stack `all-MiniLM-L6-v2` + chunking por header + top-5 sem corte de score. Detalhamento e propostas de correção em `03-problemas-e-correcoes.md`.
