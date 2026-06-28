# Avaliação do Exercício 3.1 — Tech Lead
**Trilha de Certificação AI First — DGS / DB1 Global Software**
**Papel:** Tech Lead | **Cenário:** 3 — Governança e Validação
**Exercício:** 3.1 — Design do Harness do Projeto
**Data de avaliação:** 28/06/2026

---

## Resumo

O participante entregou um harness completo e de altíssima qualidade, cobrindo as 5 camadas com diagnóstico preciso do estado atual, gaps identificados e plano de fechamento priorizado. O `response-validator.ts` gerado via Copilot foi revisado criticamente com Claude e o resultado final supera o mínimo exigido pelo exercício — não apenas uma verificação de fonte, mas as três verificações do loop completo. A análise demonstra domínio sólido dos conceitos e profunda conexão com os artefatos dos cenários anteriores (ADR-0001 a ADR-0004, AGENTS.md).

---

## Scores por Dimensão

| Dimensão | Score | Justificativa |
|----------|-------|---------------|
| D1 — Domínio Conceitual | 3 | Distingue corretamente guardrails probabilísticos (prompt) de determinísticos (código), explica por que structured output com Zod é mais confiável que instrução em prompt, e posiciona HITL em dois pontos concretos e justificados (baixa confiança em temas sensíveis; mudanças em prompt/documentos). Compreensão de Harness Engineering sem ambiguidade. |
| D2 — Uso de Ferramentas | 3 | Evidência dupla: captura de tela do Copilot gerando o `response-validator.ts` no VS Code (painel CHAT visível com checklist de conformidade com AGENTS.md), e captura do Claude realizando code review estruturado do output do Copilot. O participante não aceitou o output acriticamente — usou o Claude para analisar o que o Copilot acertou, o que tem problema real e o que é discutível. |
| D3 — Qualidade do Entregável | 3 | O harness em 5 camadas é completo e acionável: cada camada tem seção "o que está implementado", "o que está faltando" e tabela de prioridades. O `response-validator.ts` é funcional: schema Zod com `.strict()`, `VALID_SOURCE_DOCUMENTS` como `Set<string>`, `ValidationResult` com `requiresHumanReview?`, `FALLBACK_RESPONSE` congelado com `Object.freeze`, e as três verificações em sequência com fail-fast. Nenhuma verificação apenas loga — todas retornam `ValidationResult` com `valid: false`. Código sem erros de compilação (TypeScript strict mode). |
| D4 — Pensamento Crítico | 3 | O harness vai além da descrição de conceitos: mapeia gaps concretos com referência às ADRs (ex: penalização de score da PROC-042-v1 faltando, conforme ADR-0003; cap de tokens nos chunks ausente, conforme ADR-0002). A revisão do Copilot com Claude identifica pontos sutis: normalização NFD antes do regex como detalhe inteligente; `sanitizeForLog` como adição além do prompt (boa surpresa); e risco da verificação 3 logar o `source_document` mas não o `answer` como decisão consciente, não omissão. |
| D5 — Aplicabilidade ao Projeto | 3 — Máximo | Referências explícitas e corretas a: ADR-0001 (GPT-4o via Azure OpenAI), ADR-0002 (context budget 16K tokens com distribuição detalhada), ADR-0003 (versões conflitantes PROC-042 v1/v2, penalização de 40%), ADR-0004 (Azure AI Search + Document Intelligence + LangChain), AGENTS.md (TypeScript strict, Zod, pino, sem console.log, sem require dinâmico, sem PII em logs). Os identificadores de documentos válidos (`POL-001`, `PROC-042`, `PROC-042-v2`, `SLA-2024`, `FAQ-Atendimento`) estão corretos e consistentes com o cenário. |

**Score do exercício: 3.0**

---

## Verificação de Armadilhas

O exercício 3.1 do Tech Lead não possui armadilhas declaradas no enunciado (diferente dos exercícios de revisão crítica). As armadilhas implícitas do harness são:

| Armadilha implícita | Identificada? |
|---|---|
| Guardrails só no prompt (sem código determinístico) | ✅ Sim — o harness distingue guardrails probabilísticos (prompt) de determinísticos (código) e marca os determinísticos como "faltam" |
| Verificação que só loga mas não bloqueia | ✅ Sim — o `response-validator.ts` retorna `ValidationResult` com `valid: false` em todas as falhas, não apenas loga |
| Context budget ignorado / reinventado | ✅ Sim — a Camada 3 referencia a ADR-0002 e usa a distribuição de tokens definida no cenário 1 sem reinventar |
| HITL sem ponto de ativação concreto | ✅ Sim — dois pontos de HITL definidos com condições precisas (confidence_score < 0.6 + tema sensível; PR obrigatório para mudanças) |
| Logging com PII | ✅ Sim — `sanitizeForLog` implementado; verificação 2 loga apenas `source_document`, não `answer` |

---

## Pontos Fortes

1. **Harness como documento de engenharia real:** A estrutura em 5 camadas com "o que tem / falta / como fechar" e tabelas de prioridade é diretamente utilizável como backlog de sprint — não é descrição de conceito, é plano de ação.

2. **`response-validator.ts` além do mínimo exigido:** O exercício pede uma verificação simples de fonte. O participante entregou as três verificações do loop completo (schema, fonte válida, conteúdo de risco), `Object.freeze` no fallback, `sanitizeForLog` para proteção de PII, e normalização NFD antes do regex — evidência de que o Copilot foi guiado por um prompt de qualidade e o output foi avaliado criteriosamente.

3. **Revisão crítica do Copilot com Claude estruturada e honesta:** A imagem do code review mostra separação clara em "o que acertou bem", "o que tem problema real" e "o que é discutível" — postura de Tech Lead que usa IA como par, não como oráculo.

---

## Pontos de Melhoria

1. **Guardrail de idioma ausente:** O harness lista na tabela de guardrails determinísticos o "Resposta em idioma diferente do português → Detector de idioma + rejeição" como faltando, mas não propõe implementação nem prioridade. Para go-live em 2 semanas, seria útil uma decisão explícita: implementar (com qual biblioteca?) ou aceitar como risco residual com justificativa.

2. **Observabilidade: thresholds sem baseline:** Os alertas estão bem definidos (> 15% feedback negativo, > 20% rejeições/hora), mas não há referência a qual baseline justifica esses números. Uma nota de calibração ("threshold inicial conservador, revisitar após 7 dias em produção") tornaria os alertas mais defensáveis perante a diretoria.

3. **Resposta degradada do circuit breaker não detalhada:** A Camada 1 menciona "definir resposta padrão de fallback e timeout de 10s" como ação, mas não especifica qual seria a mensagem de fallback quando o Azure AI Search ou Azure OpenAI ficam indisponíveis. Conectar com o `FALLBACK_RESPONSE` do `response-validator.ts` seria a solução natural.

---

## Classificação

**✅ Aprovado com distinção (Score: 3.0)**

---

## Tópicos da Trilha para Reforço

Score máximo atingido. Nenhum tópico requer reforço obrigatório.

Sugestão de aprofundamento opcional: **observabilidade de harness em produção** (calibração de alertas, análise de deriva de qualidade ao longo do tempo, KPIs para revisão do HITL threshold).

---

*Avaliação gerada em 28/06/2026 | Trilha AI First — DGS / DB1 Global Software*
