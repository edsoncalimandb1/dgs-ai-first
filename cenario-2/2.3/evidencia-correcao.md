# Avaliação — Exercício 2.3: Criação e teste de skills técnicas

**Trilha:** AI First DGS — DB1 Global Software  
**Cenário:** 2 — Fase de Estruturação do Trabalho  
**Papel:** Tech Lead  
**Avaliado em:** 20/06/2026  
**Avaliador:** Claude (Anthropic) via skill `avaliacao-foundation.md` + `avaliacao-tech-lead.md`

---

## Resumo

Entregável de altíssima qualidade, consistente com os exercícios 2.1 e 2.2. A SKILL.md v1 já é prescritiva, com código real de DO/DON'T, 6 anti-padrões documentados e checklist de 12 itens. O teste com Copilot foi executado de verdade (3 arquivos gerados, `npm run build` rodado, checklist 10/12 com análise por arquivo). A iteração v1→v2 é substancial: 2 anti-padrões novos adicionados e 1 exemplo corrigido a partir de melhorias identificadas pelo Copilot. Destaque para o EXTRA documentado: o Copilot contribuiu com `{ offset: true }` que não estava na skill — o participante reconheceu e incorporou, demonstrando que skills são artefatos vivos.

---

## Scores por Dimensão

| Dimensão                       | Score | Justificativa                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ------------------------------ | :---: | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 — Domínio Conceitual        | **3** | Compreensão precisa de skills como artefatos de camada Domain — não mistura com Foundation nem com Artifact. A estrutura obrigatória de 3 arquivos (`handler.ts`, `validator.ts`, `response-builder.ts`) com responsabilidades separadas e limites prescritivos (≤50 linhas, sem lógica condicional no validator, sem serviços externos no response-builder) demonstra entendimento real do padrão. Os 5 critérios de maturidade são mensuráveis e orientados a evidência, não a percepção subjetiva.                         |
| D2 — Uso de Ferramentas        | **3** | Teste real com Copilot evidenciado: prompt documentado na skill, 3 arquivos gerados (`handler.ts`, `validator.ts`, `response-builder.ts`), `npm run build` executado (screenshot), checklist por arquivo com itens PASS/AVISO/EXTRA e pontuação 10/12. Iteração v1→v2 com 3 mudanças concretas: anti-padrão 6 (try/catch obrigatório), anti-padrão 7 (criação de dados no response-builder) e exemplo `datetime({ offset: true })` — todas rastreáveis ao checklist.                                                          |
| D3 — Qualidade do Entregável   | **3** | SKILL.md v2 é prescritiva ao longo: usa DEVE/NÃO DEVE, exemplos TypeScript compiláveis com comentários `// ❌` e `// ←` inline, checklist de 12 itens verificáveis, tabela de HTTP status codes completa, e prompt de ativação pronto para colar no Copilot. Nenhuma seção é narrativa — até o "quando usar esta skill" lista frases exatas que ativam o artefato. Os 3 arquivos gerados pelo Copilot existem e são coerentes com a skill (com os 2 desvios documentados honestamente).                                       |
| D4 — Pensamento Crítico        | **3** | O checklist distingue corretamente PASS, AVISO e EXTRA — e o EXTRA é tratado como contribuição real do Copilot, não como erro. O AVISO do `createFeedbackOutput` no response-builder é identificado com precisão: a skill define response-builder como responsável apenas por montar `HttpResponseInit`, e o Copilot mesclou responsabilidades — o participante nomeia isso como falha de separação de camada, não apenas "código errado". O "Veredicto do Tech Lead" é honesto: "aprovado com ajustes menores".              |
| D5 — Aplicabilidade ao Projeto | **3** | A skill referencia explicitamente seções do AGENTS.md (`## Coding Standards > Azure Functions v4`, `## Tech Stack & Architecture > Gerenciamento de contexto`) e as três skills Foundation por caminho. O `authLevel: 'function'` vs `'anonymous'` é explicado em termos do projeto (health check como exceção nomeada). O campo `source_document` aparece nas responsabilidades do response-builder — conecta à decisão de produto do cenário 1. Scopes e nomes de serviços referenciam a estrutura real de `src/services/`. |

**Score do exercício: 3.0 / 3.0**

---

## Classificação

> ✅ **Aprovado com distinção** (score 2.5–3.0)

---

## Verificação de Prescritividade (machine-readable)

A SKILL.md v2 foi verificada quanto à aderência ao critério de prescritividade — instruções que um agente consegue seguir sem interpretação.

| Regra                                                         | Status              | Evidência                                                         |
| ------------------------------------------------------------- | ------------------- | ----------------------------------------------------------------- |
| `handler.ts` DEVE ter no máximo 50 linhas                     | ✅ Prescritiva      | Limite numérico verificável — Copilot gerou handler com 43 linhas |
| `validator.ts` NUNCA contém `if`, `for` ou lógica condicional | ✅ Prescritiva      | Proibição explícita de construções sintáticas específicas         |
| `await request.json()` DEVE ter `.catch(() => null)`          | ✅ Prescritiva      | Forma exata do código prescrita — sem ambiguidade                 |
| `app.http()` DEVE estar no final do arquivo                   | ✅ Prescritiva      | Posição no arquivo especificada — anti-padrão 4 com DO/DON'T      |
| `authLevel: 'function'` para endpoints de negócio             | ✅ Prescritiva      | Valor exato do campo especificado com exceção nomeada             |
| `response-builder` não deve conter lógica de criação de dados | ✅ Prescritiva (v2) | Anti-padrão 7 adicionado após o Copilot violar a regra implícita  |
| try/catch obrigatório em chamadas a `src/services/`           | ✅ Prescritiva (v2) | Anti-padrão 6 com isenção documentada e comentário obrigatório    |

Nenhuma seção narrativa identificada na v2. O "Quando usar esta skill" lista frases exatas de ativação — acionável pelo agente.

---

## Evidências do Ciclo de Teste com Copilot

### Processo documentado

| Etapa                                        | Evidência                                                                           |
| -------------------------------------------- | ----------------------------------------------------------------------------------- |
| Prompt enviado ao Copilot                    | Screenshot com prompt completo (AGENTS.md + skill + 3 arquivos + requisitos)        |
| Copilot leu AGENTS.md e skill antes de gerar | Log do Copilot: "Reviewed 3 files", "Reviewed 5 files", "Reviewed 6 files"          |
| 3 arquivos gerados e build rodado            | Screenshot do VS Code com `npm run build` executando                                |
| Checklist aplicado por arquivo               | Análise item a item com PASS/AVISO/EXTRA para handler, validator e response-builder |
| Pontuação documentada                        | 10/12 corretos · 2 avisos · 2 extras (melhorias não previstas)                      |

### O que o Copilot seguiu (skill v1)

- ✅ Estrutura v4 completa — imports corretos, `app.http()` no final
- ✅ Logger com `logger.child({ invocationId, operation })`
- ✅ `await request.json().catch(() => null)` — anti-padrão 3 respeitado
- ✅ Input validado com `safeParse` antes de qualquer lógica
- ✅ `authLevel: "function"` — anti-padrão 6 (v1) respeitado
- ✅ `app.http()` no final do arquivo — anti-padrão 4 respeitado
- ✅ Handler ≤ 50 linhas (43 linhas)
- ✅ `validator.ts` com schemas Zod puros, sem lógica condicional
- ✅ Tipos inferidos exportados com `z.infer`
- ✅ `response-builder.ts` valida output com `safeParse` antes de retornar

### O que o Copilot não seguiu / identificou como melhoria

| Item                                                                  | Tipo  | Ação tomada no v2                                                                             |
| --------------------------------------------------------------------- | ----- | --------------------------------------------------------------------------------------------- |
| Sem try/catch em torno de `createFeedbackOutput`                      | AVISO | Anti-padrão 6 reescrito com regra explícita de obrigatoriedade e isenção documentada          |
| `createFeedbackOutput` (lógica de negócio) dentro do response-builder | AVISO | Anti-padrão 7 adicionado: response-builder recebe dados prontos, nunca gera IDs ou timestamps |
| `z.string().datetime({ offset: true })` em vez de `.datetime()`       | EXTRA | Exemplo do `validator.ts` na skill atualizado para `{ offset: true }`                         |

---

## Pontos Fortes

**1. EXTRA documentado como contribuição, não como falha**

O participante identificou que o Copilot gerou `z.string().datetime({ offset: true })`, que é mais preciso do que o exemplo da skill v1. Em vez de ignorar ou marcar como desvio, incorporou na skill v2 — demonstrando que o fluxo de teste não é apenas validação do Copilot contra a skill, mas também validação da skill contra o que o Copilot sabe. Essa inversão é o comportamento correto para manutenção de skills como artefatos vivos.

**2. Checklist formal por arquivo com distinção de severidade**

A análise pós-geração é estruturada por arquivo (handler, validator, response-builder) com níveis distintos: PASS (seguiu), AVISO (não seguiu — corrigível), EXTRA (melhorou além do prescrito). Essa granularidade é o que permite iterar a skill com precisão — em vez de "o output estava bom ou ruim".

**3. Critérios de maturidade mensuráveis e orientados a evidência**

Os 5 critérios de maturidade têm números concretos (3 endpoints diferentes, 12 itens do checklist, 2 devs diferentes) e condições verificáveis (sem regressão após atualização). Isso torna a pergunta "a skill está pronta?" respondível com dados, não com opinião.

---

## Pontos de Melhoria

**1. Checklist não atualizado para refletir os 8 anti-padrões da v2**

A skill v2 tem 8 anti-padrões (adicionados anti-padrões 6 e 7 após o teste), mas o checklist de 12 itens não foi atualizado para incluir verificações correspondentes. Sugestão: adicionar dois itens ao checklist — "[ ] Chamadas a `src/services/` estão dentro de try/catch (ou têm comentário de isenção)" e "[ ] `response-builder.ts` não contém `randomUUID()`, `new Date()` ou qualquer lógica de geração de dados".

**2. Critério de maturidade 1 ainda referencia "6 anti-padrões" da v1**

O Critério 1 de maturidade diz "nenhum deles continha os 6 anti-padrões listados acima", mas a v2 tem 8. É uma inconsistência menor que pode gerar confusão quando outro dev usar a skill. Sugestão: atualizar para "os N anti-padrões" ou referenciar o número da versão.

**3. Skill não documenta como testar o anti-padrão 7 em geração futura**

O anti-padrão 7 (criação de dados no response-builder) foi identificado neste teste porque o participante sabia o que procurar. O exemplo DO/DON'T está correto, mas o checklist não tem item verificável para esse anti-padrão. Sugestão: adicionar ao checklist "[ ] `response-builder.ts` não importa `randomUUID`, `crypto`, `Date` ou qualquer utilitário de geração de dados".

---

## Resumo do Cenário 2 — Tech Lead

| Exercício                                |  Score  | Classificação              |
| ---------------------------------------- | :-----: | -------------------------- |
| 2.1 — Construção e teste do AGENTS.md    |   3.0   | Aprovado com distinção     |
| 2.2 — Arquitetura de MCP                 |   3.0   | Aprovado com distinção     |
| 2.3 — Criação e teste de skills técnicas |   3.0   | Aprovado com distinção     |
| **Média do cenário**                     | **3.0** | **Aprovado com distinção** |

---

## Tópicos da Trilha para Reforço

Nenhum. Score 3.0 em todos os exercícios do cenário 2. O participante demonstra domínio consistente de AGENTS.md, MCP como infraestrutura gerenciada e skills como artefatos vivos com ciclo empírico de refinamento. Pronto para o Cenário 3 (Harness Engineering e Revisão Crítica de Outputs).

---

## Artefatos Avaliados

| Artefato                         | Tipo                       | Observação                                                  |
| -------------------------------- | -------------------------- | ----------------------------------------------------------- |
| `azure-functions-endpoint-V1.md` | SKILL.md inicial           | 6 anti-padrões, checklist 12 itens, critérios de maturidade |
| `azure-functions-endpoint-V2.md` | SKILL.md iterada           | +2 anti-padrões, exemplo `datetime` corrigido               |
| `handler.ts`                     | Código gerado pelo Copilot | 43 linhas, 10/12 itens da skill seguidos                    |
| `validator.ts`                   | Código gerado pelo Copilot | Schemas Zod puros, `{ offset: true }` incorporado           |
| `response-builder.ts`            | Código gerado pelo Copilot | AVISO: `createFeedbackOutput` com lógica de negócio         |
| Screenshots (5 imagens)          | Evidência de execução      | Prompt, execução, checklist Pt1/Pt2/Pt3 documentados        |
