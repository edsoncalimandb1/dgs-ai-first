# Avaliação — Exercício 2.1: Construção e teste do AGENTS.md

**Trilha:** AI First DGS — DB1 Global Software  
**Cenário:** 2 — Fase de Estruturação do Trabalho  
**Papel:** Tech Lead  
**Avaliado em:** 20/06/2026  
**Avaliador:** Claude (Anthropic) via skill `avaliacao-foundation.md` + `avaliacao-tech-lead.md`

---

## Resumo

Entregável de altíssima qualidade. O AGENTS.md é prescritivo, machine-readable e fortemente conectado às ADRs do cenário 1. O ciclo de teste com o GitHub Copilot foi executado de verdade — há evidência de geração real (handler V1 e V2 com código funcional) e análise crítica documentada (checklist 7/10 com itens PASS/AVISO). A iteração v1→v2 produziu melhorias concretas e rastreáveis. O participante demonstra maturidade ao reconhecer os três avisos sem tentar mascarar as limitações.

---

## Scores por Dimensão

| Dimensão                       | Score | Justificativa                                                                                                                                                                                                                                                                                                                                                                         |
| ------------------------------ | :---: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 — Domínio Conceitual        | **3** | Compreensão profunda do AGENTS.md como "constitution" — separa explicitamente decisões duráveis de placeholders. Incorpora ADR-0002 (context budget com tabela de tokens por slot) e ADR-0003 (doc_version_date, conflito explicitado). Trata retry, custom errors e least-privilege de forma correta e específica ao stack Azure Functions v4.                                       |
| D2 — Uso de Ferramentas        | **3** | Evidência de teste real com Copilot: handler.ts V1 gerado, analisado com checklist 7/10, identificação de 3 avisos concretos, AGENTS.md v2 com as três seções corrigidas. Handler V2 e validator-V2 demonstram que a segunda geração realmente melhorou (separação de responsabilidades, ConfigurationError tipado, route explícita). Screenshots documentam sessão ativa no VS Code. |
| D3 — Qualidade do Entregável   | **3** | AGENTS.md v2 usa DEVE/NÃO DEVE/NUNCA de forma consistente. Exemplos de código DO/DON'T reais e compiláveis. Regra de ≤50 linhas para handler.ts verificável. Context budget como tabela com hard limits. Campo `source_document` tipado com interface completa. Nenhuma seção é puramente narrativa.                                                                                  |
| D4 — Pensamento Crítico        | **3** | Checklist honesto com código-evidência por item. Identifica AVISO com explicação do porquê (ex: "aceitável para health check, mas inconsistente com o padrão"). O "Veredicto do Tech Lead" reconhece que o v1 estava bem escrito (7/10 sem violações graves) sem superestimar. Limitações documentadas explicitamente.                                                                |
| D5 — Aplicabilidade ao Projeto | **3** | Referencia ADR-0001, ADR-0002, ADR-0003, ADR-0004 na tabela de stack. Context budget usa os números exatos das ADRs (~4K system, ~8K chunks). Tratamento de contradições cita `doc_version_date` e os 12 documentos identificados no discovery. Scopes de Conventional Commits mapeados para a arquitetura real do projeto.                                                           |

**Score do exercício: 3.0 / 3.0**

---

## Classificação

> ✅ **Aprovado com distinção** (score 2.5–3.0)

---

## Verificação de Prescritividade (machine-readable)

As regras abaixo foram verificadas quanto à aderência ao critério de prescritividade — instruções que um agente consegue seguir, não descrições do projeto.

| Regra                                                                            | Status         | Evidência                                                                  |
| -------------------------------------------------------------------------------- | -------------- | -------------------------------------------------------------------------- |
| `handler.ts` DEVE ter no máximo 50 linhas                                        | ✅ Prescritiva | Verificável por contagem; Copilot gerou handler com ~30 linhas             |
| Nunca enviar contexto sem system prompt → `SystemPromptLoadError` + HTTP 503     | ✅ Prescritiva | Ação, erro e código HTTP especificados sem ambiguidade                     |
| `prompt-builder.ts` trunca histórico ao atingir 3 turnos — remover o mais antigo | ✅ Prescritiva | Comportamento de truncagem inequívoco e implementável                      |
| Seções Product Rules, Testing Standards, Project Management                      | ⚠️ Placeholder | Esperado nesta fase; documentado corretamente com indicação de responsável |

---

## Evidências do Ciclo de Teste com Copilot

### O que o Copilot seguiu (AGENTS.md v1 → geração V1)

- ✅ Azure Functions v4 style (`app.http()`, imports corretos)
- ✅ Tipos TypeScript explícitos em tudo — sem `any`, sem `unknown` no parse do JSON
- ✅ Pino logger com `logger.child({ invocationId, operation })`
- ✅ Validação com Zod — input e output com `safeParse`
- ✅ Auth level `anonymous`
- ✅ Handler com menos de 50 linhas
- ✅ Erros mapeados para HTTP responses adequados

### O que o Copilot não seguiu (avisos identificados)

| Aviso                 | Descrição                                                        | Ação tomada no v2                                                                                                 |
| --------------------- | ---------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Custom errors tipados | Handler retornou HTTP 500 direto sem lançar `ConfigurationError` | Adicionada regra explícita: handlers que detectam falha de config DEVEM lançar custom error antes de retornar 500 |
| Isenção de retry      | Sem comentário `// No external calls — retry not applicable`     | Adicionada sub-regra de isenção documentada com comentário obrigatório                                            |
| Commit message        | Copilot não sugeriu mensagem no formato Conventional Commits     | Adicionada instrução: ao gerar/modificar arquivo, sugerir commit message correspondente                           |

**Pontuação do checklist: 7/10 regras seguidas · 3 oportunidades de melhoria · 0 violações graves**

### Melhoria verificada na geração V2

O handler V2 demonstra as melhorias:

- `ConfigurationError` importado e lançado corretamente
- `validator.ts` separado com `loadPackageVersion()` e `buildHealthOutput()`
- Comentário `// No external calls — retry not applicable` presente
- `route: "health"` explícito no registro do `app.http`

---

## Pontos Fortes

**1. Ciclo de teste empírico completo**
Prompt → geração V1 → checklist com evidências de código → 3 itens de melhoria identificados → AGENTS.md v2 com seções reescritas → geração V2 com melhoria verificável. O loop é fechado e documentado.

**2. Context budget como artefato de arquitetura**
A tabela de tokens não é decorativa — é uma regra com consequências de implementação (`prompt-builder.ts` com truncagem por turno, chunks por score, falha para HTTP 503). Conecta diretamente à ADR-0002 e é machine-readable pelo Copilot.

**3. Reconhecimento honesto de limitações**
O participante documenta que "Conventional Commit message não foi sugerido pelo Copilot" e adiciona a regra na v2 sem afirmar que isso resolve o problema definitivamente — postura alinhada com o critério de que "nem tudo será seguido, e isso é esperado".

---

## Pontos de Melhoria

**1. Teste de geração de testes (não apenas endpoints)**
O exercício pede que o Copilot gere (a) endpoint e (b) teste para o endpoint. Os entregáveis evidenciam handler V1 e V2, mas não há arquivo de teste gerado pelo Copilot. Um `handler.spec.ts` teria completado o ciclo e revelado aderência à seção Testing Standards.

**2. Regra de isenção de retry poderia ser sub-regra explícita**
A correção no v2 (`// No external calls — retry not applicable`) está correta, mas o padrão de isenção poderia ser elevado para uma sub-regra própria no AGENTS.md, facilitando que o Copilot identifique automaticamente quando a isenção se aplica — em vez de aparecer apenas nos exemplos de código.

**3. Ausência de regra sobre estratégia de resolução de paths**
O handler V1 usa `import.meta.url` (ESM) e o V2 usa `resolve(process.cwd(), ...)`. A mudança é correta mas não está documentada como regra — um agente futuro pode regredir ao padrão ESM sem instrução explícita sobre qual estratégia usar em Azure Functions v4.

---

## Tópicos da Trilha para Reforço

Nenhum. Score 3.0 — o participante demonstra domínio de AGENTS.md como artefato de engenharia, ciclo empírico de validação e conexão com decisões arquiteturais anteriores. Para o exercício 2.2 (Arquitetura de MCP), o nível de rigor evidenciado aqui é o esperado.

---

## Artefatos Avaliados

| Artefato                | Tipo                       | Observação                                 |
| ----------------------- | -------------------------- | ------------------------------------------ |
| `AGENTS-V1.md`          | AGENTS.md inicial          | Gerado com Claude, testado com Copilot     |
| `AGENTS-V2.md`          | AGENTS.md iterado          | 3 seções reescritas após análise do teste  |
| `handler-V1.ts`         | Código gerado pelo Copilot | Primeira geração — 7/10 regras seguidas    |
| `handler-V2.ts`         | Código gerado pelo Copilot | Segunda geração — melhorias verificadas    |
| `validator-V2.ts`       | Código gerado pelo Copilot | Separação de responsabilidades aplicada    |
| Screenshots (6 imagens) | Evidência de execução      | Sessões Copilot no VS Code documentadas    |
| Checklist PASS/AVISO    | Análise crítica            | 10 itens avaliados com evidência de código |
