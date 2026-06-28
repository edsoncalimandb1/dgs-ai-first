# Exercício 3.1 — Design do Harness do Projeto

**Papel:** Tech Lead  
**Cenário:** NovaTech — Assistente de Atendimento com RAG  
**Tópico:** Harness Engineering

---

## Contexto de partida

O assistente está em staging com os seguintes fatos confirmados:

- 12% das respostas incorretas nos testes internos
- Respostas retornadas em texto livre — nenhum campo obrigatório (fonte, confiança) é garantido estruturalmente
- Um módulo de feedback gerado pelo Copilot violou o AGENTS.md (sem Zod, console.log em vez de pino, require dinâmico, e-mail do atendente logado)
- Demo para a diretoria da NovaTech em 2 semanas

As ADRs do Cenário 1 são a base deste design:

- **ADR-0001:** GPT-4o via Azure OpenAI, versão fixada, abstraída atrás de `LLMClient`
- **ADR-0002:** Context budget de 16K tokens por query, janela deslizante de 4 trocas, chunks posicionados logo após o system prompt
- **ADR-0003:** Ambas as versões da PROC-042 no índice, penalização de score para versão legada, instrução explícita no prompt sobre conflito de versões
- **ADR-0004:** Azure AI Search + Azure Document Intelligence + LangChain como orquestração

---

## Design do Harness — 5 Camadas

---

### Camada 1 — Tool Orchestration

**O que coordena:** ingestão (SharePoint → Azure Document Intelligence → Azure AI Search), retrieval (query → embedding → busca vetorial → re-ranking), e geração (contexto montado → GPT-4o → resposta).

#### O que já está implementado

- Pipeline de ingestão processando 847 documentos no Azure AI Search
- Query endpoint funcional via POST: recebe pergunta, busca chunks, retorna resposta com citação de fonte
- Indexer do Azure AI Search com change tracking para atualização automática dos documentos do SharePoint

#### O que está faltando

- **Detecção de perguntas multi-domínio** definida na ADR-0002 (seção 5): a decomposição em sub-perguntas com MMR ainda não foi implementada
- **Penalização de score para chunks de versão legada** definida na ADR-0003 (Camada 3): o filtro before_llm que penaliza a PROC-042-v1 em 40% quando a v2 também é recuperada
- **Timeout e circuit breaker** no pipeline: se o Azure AI Search ou o Azure OpenAI ficarem indisponíveis, não há resposta degradada definida

#### Como fechar os gaps

| Gap                         | Ação                                                                                                      | Prioridade         |
| --------------------------- | --------------------------------------------------------------------------------------------------------- | ------------------ |
| Detecção multi-domínio      | Implementar heurística de palavras-chave como primeiro passo; adiar decomposição por LLM para pós go-live | Alta               |
| Penalização de score legado | Implementar filtro no retrieval antes da montagem do contexto, conforme ADR-0003                          | Bloqueante go-live |
| Circuit breaker             | Definir resposta padrão de fallback e implementar timeout de 10s                                          | Média              |

---

### Camada 2 — Verification Loops

**O que verifica:** outputs do modelo antes de chegarem ao atendente. É a camada que transforma o pipeline de "probabilístico puro" em "probabilístico com rede de segurança determinística".

#### O que já está implementado

- Nenhuma verificação automática de output está implementada. As respostas chegam ao atendente como texto livre do modelo.

#### O que está faltando

**Verificação 1 — Structured output (bloqueante):**  
Forçar o modelo a responder em JSON com schema fixo:

```json
{
  "answer": "string",
  "source_document": "string (identificador curto: POL-001, PROC-042, etc.)",
  "confidence_score": "number (0.0 a 1.0)"
}
```

Respostas que não seguem o schema são rejeitadas e substituídas por mensagem padrão.

**Verificação 2 — Fonte válida (bloqueante):**  
Verificar se o `source_document` retornado existe na lista de documentos válidos da NovaTech. Implementada no `response-validator.ts`.

**Verificação 3 — Conteúdo de risco (encaminha para HITL):**  
Se a resposta mencionar "carga perigosa" junto com afirmação de que devolução é possível, bloquear e encaminhar para revisão humana. Regra derivada da exceção da POL-001 seção 3.2.

#### Como fechar os gaps

| Verificação                    | Onde implementar                     | Prioridade         |
| ------------------------------ | ------------------------------------ | ------------------ |
| Structured output + schema Zod | `src/services/response-validator.ts` | Bloqueante go-live |
| Fonte válida                   | `src/services/response-validator.ts` | Bloqueante go-live |
| Conteúdo de risco              | `src/services/response-validator.ts` | Bloqueante go-live |

---

### Camada 3 — Context & Memory

**O que gerencia:** o contexto que o modelo recebe a cada query, respeitando o context budget definido na ADR-0002.

#### O que já está implementado

- O query endpoint monta o contexto (system prompt + chunks + pergunta), mas sem respeito formal ao orçamento definido na ADR-0002
- Não há controle de histórico de conversa — cada query é tratada como independente

#### O que está faltando

A ADR-0002 define orçamento de 16K tokens com distribuição precisa:

| Parte                    | Tokens reservados       | Status                  |
| ------------------------ | ----------------------- | ----------------------- |
| System prompt (estático) | 1.500                   | ✅ Implementado         |
| Metadados do cliente     | 200                     | ❌ Não implementado     |
| Chunks recuperados       | 6.000 (8–10 chunks)     | ⚠️ Implementado sem cap |
| Histórico de conversa    | 3.000 (janela 4 trocas) | ❌ Não implementado     |
| Pergunta atual           | 500                     | ✅ Implementado         |
| Buffer de segurança      | 4.800                   | ❌ Não implementado     |

**Gaps críticos:**

- Sem cap de tokens nos chunks: contexto pode ultrapassar o orçamento silenciosamente
- Sem posicionamento explícito: chunks devem ficar logo após o system prompt (combate lost in the middle — ADR-0002)
- Sem histórico de sessão: para go-live, tratar cada query como independente é mais seguro que context rot

#### Como fechar os gaps

| Gap                             | Ação                                                                                 | Prioridade         |
| ------------------------------- | ------------------------------------------------------------------------------------ | ------------------ |
| Cap de tokens nos chunks        | Implementar contador antes de montar o contexto; descartar chunks que ultrapassem 6K | Bloqueante go-live |
| Posicionamento de chunks        | Auditar template de montagem e corrigir ordem                                        | Alta               |
| Histórico com janela deslizante | Adiar para pós go-live                                                               | Pós go-live        |

---

### Camada 4 — Guardrails

**O que limita:** o que o assistente pode e não pode fazer, combinando mecanismos probabilísticos (prompt) e determinísticos (código), com pontos de HITL.

#### Guardrails probabilísticos (via prompt)

Já definidos no system prompt, sem verificação de que estão sendo respeitados:

- Sempre citar fonte
- Nunca inventar prazos ou valores
- Quando não encontrar resposta, dizer explicitamente
- Responder em português formal
- Priorizar versão mais recente em documentos contraditórios (ADR-0003)

#### Guardrails determinísticos (via código — faltam)

| Guardrail                                       | Mecanismo                                        | Status   |
| ----------------------------------------------- | ------------------------------------------------ | -------- |
| Structured output obrigatório                   | Schema Zod + rejeição se não bater               | ❌ Falta |
| Fonte deve ser documento válido                 | Função de verificação no `response-validator.ts` | ❌ Falta |
| Carga perigosa + devolução deve conter negativa | Regex + bloqueio                                 | ❌ Falta |
| Resposta em idioma diferente do português       | Detector de idioma + rejeição                    | ❌ Falta |

#### Pontos de Human-in-the-Loop (HITL)

**HITL 1 — Respostas de baixa confiança sobre temas sensíveis:**  
Se `confidence_score < 0.6` E a resposta mencionar carga perigosa, cálculo de frete ou prazo de devolução, a resposta vai para fila de revisão do supervisor antes de chegar ao atendente.

**HITL 2 — Mudanças no system prompt ou documentos indexados:**  
Qualquer alteração no system prompt ou adição de documento novo requer aprovação do Tech Lead + PS via PR antes de ir a produção.

#### Como fechar os gaps

| Gap                            | Ação                                          | Prioridade         |
| ------------------------------ | --------------------------------------------- | ------------------ |
| Guardrails determinísticos     | Implementar `response-validator.ts`           | Bloqueante go-live |
| HITL para baixa confiança      | Fila de revisão via canal Teams do supervisor | Bloqueante go-live |
| HITL para mudanças no pipeline | PR obrigatório com aprovação TL + PS          | Bloqueante go-live |

---

### Camada 5 — Observability

**O que monitora:** uso, qualidade, erros técnicos e conteúdo das respostas em produção.

#### O que já está implementado

- Testes de integração cobrindo ~75% do código
- Logs básicos via console.log (violação do AGENTS.md — deve ser substituído por pino)

#### O que está faltando

**Métricas de uso:** queries/dia, tempo médio de resposta, taxa de timeout

**Métricas de qualidade:** % respostas rejeitadas pelo validator, % enviadas para HITL, % feedback negativo, % escalações para supervisor

**Métricas técnicas:** latência por etapa (retrieval / montagem / geração / validação), taxa de erro por componente, tamanho médio do contexto em tokens

**Métricas de conteúdo:** documentos mais citados, perguntas sem resposta, queries com chunks de versões conflitantes (alerta da ADR-0003)

**Alertas com threshold concreto:**
| Alerta | Threshold | Ação |
|--------|-----------|------|
| Feedback negativo alto | > 15% em 24h | Notificar TL + PS via Teams |
| Taxa de rejeição pelo validator | > 20% em 1h | Investigar imediatamente |
| Chunks de versão conflitante | > 5 ocorrências/hora | Alerta para revisão do pipeline |
| Latência end-to-end | > 8s p95 | Investigar gargalo por etapa |

#### Como fechar os gaps

| Gap                   | Ação                                                 | Prioridade         |
| --------------------- | ---------------------------------------------------- | ------------------ |
| Logging estruturado   | Substituir console.log por pino em todos os módulos  | Bloqueante go-live |
| Dashboard de métricas | Azure Application Insights + queries KQL             | Alta               |
| Alertas               | Alert rules no Azure Monitor com os thresholds acima | Alta               |

---

## Resumo de prioridades

### Bloqueantes para go-live

1. Implementar `response-validator.ts` com structured output, verificação de fonte válida e conteúdo de risco
2. Implementar penalização de score para chunks de versão legada (ADR-0003)
3. Implementar cap de tokens no contexto (ADR-0002)
4. Substituir console.log por pino em todos os módulos
5. Definir HITL para respostas de baixa confiança
6. Definir processo de aprovação para mudanças em prompt e documentos

### Desejáveis (podem ir ao ar sem)

- Janela deslizante de histórico
- Decomposição de perguntas multi-domínio
- Dashboard completo de métricas
- Metadados do cliente no contexto

---

_Exercício 3.1 — Tech Lead | Cenário 3 — Fase de Governança e Validação | Junho/2025_
