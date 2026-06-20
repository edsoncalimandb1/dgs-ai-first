# AGENTS.md — NovaTech Assistant

> **v2 — atualizado após teste com GitHub Copilot (health check endpoint).** Melhorias: (1) regra de `ConfigurationError` para falhas de config; (2) isenção documentada de retry para endpoints sem chamadas externas; (3) sugestão de commit message como parte do fluxo de geração.
>
> **Constitution do projeto.** Este arquivo é lido por todo agente de IA (GitHub Copilot, Claude Code) antes de gerar qualquer artefato neste repositório. As regras aqui são decisões duráveis — não sugestões. Se uma instrução deste arquivo conflitar com uma instrução inline de um prompt, este arquivo vence, salvo indicação explícita do Tech Lead.
>
> **Seções e responsáveis:**
>
> - Project Overview → Tech Lead
> - Tech Stack & Architecture → Tech Lead
> - Coding Standards → Tech Lead
> - Product Rules & Guardrails → Product Specialist _(a preencher)_
> - Testing Standards → QA _(a preencher)_
> - Project Management Rules → Delivery Manager _(a preencher)_
> - Build & Deploy → Tech Lead

---

## Project Overview

**Projeto:** NovaTech Assistant
**Cliente:** NovaTech Logística
**Squad DB1:** 1 Tech Lead, 1 Dev Sênior, 1 Dev Pleno, 1 QA, 1 Product Specialist, 1 Delivery Manager

### O que é este sistema

Assistente de IA integrado ao Microsoft Teams que permite aos 45 atendentes da NovaTech consultarem a documentação operacional da empresa em linguagem natural. O assistente recebe uma pergunta, recupera trechos relevantes da base documental via Azure AI Search (RAG), e gera uma resposta fundamentada com citação obrigatória de fonte.

### O que este sistema NÃO é

- Não é um chatbot de uso geral. Responde exclusivamente sobre a documentação indexada da NovaTech.
- Não toma decisões operacionais. Fornece informação para que o atendente decida.
- Não substitui documentos oficiais. É uma interface de consulta, não uma fonte de verdade autônoma.
- Não tem acesso a sistemas transacionais (ERP, tracking em tempo real, chamados abertos).

### Base documental indexada

847 documentos válidos após deduplicação e limpeza (discovery fase 1). Fontes originais: SharePoint (~800 docs PDF/DOCX), Confluence wiki (~400 páginas), planilhas de referência (~50 XLSX). 12 documentos com contradições pendentes de resolução pelo Compliance da NovaTech.

Para fins de desenvolvimento e teste local, a documentação está em:

- `docs/novatech/` — documentos fonte (Anexo A do projeto)
- `data/retrieval-corpus/` — chunks de referência para testes de retrieval (Anexo B)

### Métricas de sucesso

- Tempo médio de busca por atendente: de 12 min → < 2 min por chamado
- Volume: 320 chamados/dia, ~60% envolvem consulta documental
- Toda resposta deve incluir identificador de fonte e seção

---

## Tech Stack & Architecture

### Stack de produção

| Camada            | Tecnologia                      | Decisão     |
| ----------------- | ------------------------------- | ----------- |
| LLM               | Azure OpenAI GPT-4o             | ADR-0001    |
| Vector store      | Azure AI Search                 | ADR-0004    |
| Backend           | TypeScript + Azure Functions v4 | ADR-0001    |
| Bot               | Microsoft Bot Framework (Teams) | —           |
| Frontend          | React (painel interno)          | —           |
| Infra como código | Bicep                           | —           |
| Logger            | pino                            | ADR interno |
| Validação         | Zod                             | ADR interno |
| Testes            | Vitest                          | ADR interno |

> **Nota de fase:** Nesta fase de estruturação não há recursos Azure provisionados. O desenvolvimento usa tools locais. Os arquivos Bicep em `/infra/` são estado narrativo — não executá-los.

### Arquitetura: 4 componentes

```
[Teams Bot]  ←→  [API do Assistente]  ←→  [Azure AI Search]
                         ↑                        ↑
                  [Azure OpenAI]        [Pipeline de Ingestão]
                         ↑
                  [Painel Web Interno]
```

**Componente 1 — Pipeline de ingestão** (`src/pipeline/`)
Extrai texto das fontes, divide em chunks, gera embeddings, indexa no Azure AI Search.
Spec: `specs/pipeline-ingestao/`

**Componente 2 — API do assistente** (`src/functions/`, `src/services/`)
Azure Functions que recebe pergunta → busca chunks → monta prompt → chama GPT-4o → retorna resposta com fonte.
Spec: `specs/query-endpoint/`, `specs/feedback-api/`

**Componente 3 — Bot do Teams** (`src/bot/`)
Interface conversacional via Microsoft Bot Framework. Envia perguntas à API e renderiza respostas como Adaptive Cards.
Spec: `specs/teams-bot/`

**Componente 4 — Painel web interno** (`src/web/`)
Dashboard React para métricas, histórico de queries e gestão de feedback.
Spec: `specs/painel-web/`

### Gerenciamento de contexto (ADR-0002) — OBRIGATÓRIO

Todo código que monta o prompt para o LLM DEVE respeitar o seguinte orçamento de contexto:

```
┌─────────────────────────────────────────────────────────┐
│  Context budget por query — HARD LIMIT: 128K tokens     │
├────────────────────────┬────────────────────────────────┤
│  System prompt         │  ~4.000 tokens  (estático)     │
│  Chunks recuperados    │  ~8.000 tokens  (5 chunks)     │
│  Histórico de conversa │  ~2.000 tokens  (3 turnos max) │
│  Pergunta do usuário   │  ~500 tokens                   │
│  Resposta esperada     │  ~1.000 tokens                 │
├────────────────────────┴────────────────────────────────┤
│  Total alocado: ~15.500 tokens  │  Reserva: 112K+       │
└─────────────────────────────────────────────────────────┘
```

Regras de implementação:

- O `prompt-builder.ts` DEVE truncar o histórico ao atingir 3 turnos — remover o turno mais antigo, nunca o mais recente.
- Se os 5 chunks recuperados excederem 8.000 tokens, truncar pelo score de similaridade mais baixo.
- Nunca enviar contexto sem system prompt — se `system-prompt.md` não carregar, lançar `SystemPromptLoadError` e retornar HTTP 503.
- O system prompt vive em `/prompts/system-prompt.md` e é carregado na inicialização da Function, não a cada request.

### Tratamento de documentos contraditórios (ADR-0003)

Quando o pipeline de busca retornar chunks de duas versões do mesmo documento:

1. O metadado `doc_version_date` do chunk determina a prioridade — data mais recente vence.
2. O prompt instrui o modelo a explicitar quando há versões conflitantes: "Existem duas versões deste procedimento. A versão de [data mais recente] indica X. A versão anterior indicava Y. Aplica-se a versão mais recente para chamados abertos após [data]."
3. Nunca descartar o chunk mais antigo do contexto — mantê-lo com lower priority para que o modelo possa comparar.

Referência de dados: os 12 documentos com contradições conhecidas estão identificados em `docs/novatech/contradictions-map.md`.

---

## Coding Standards

> Estas regras são consumidas pelo GitHub Copilot via este arquivo. Todo código gerado por agente DEVE seguir estas convenções. Código que viole estas regras não passa em code review.

### TypeScript

**DEVE:**

- Usar `strict: true` (configurado em `tsconfig.json` — nunca modificar esta flag)
- Declarar tipos explícitos em parâmetros de função e retornos — nunca `any` nem inferência implícita em interfaces públicas
- Usar `type` para tipos de domínio e `interface` para contratos de módulo (ver `src/shared/types.ts`)
- Usar `const` por padrão; `let` apenas quando reatribuição é necessária; `var` nunca
- Importar com caminhos relativos explícitos — nunca index barrel sem necessidade

```typescript
// DO: tipo explícito, sem any
async function searchChunks(query: string, topK: number): Promise<Chunk[]> { ... }

// DON'T: retorno implícito, any no parâmetro
async function searchChunks(query, topK) { ... }
```

**NÃO DEVE:**

- Usar `any` — se o tipo é desconhecido, usar `unknown` e narrowing explícito
- Usar `// @ts-ignore` ou `// @ts-expect-error` sem comentário explicativo aprovado pelo Tech Lead
- Criar tipos locais duplicando tipos de `src/shared/types.ts`
- Usar `!` (non-null assertion) sem verificação prévia no bloco

### Estrutura de arquivos

Cada módulo segue este padrão (exemplo: query endpoint):

```
src/functions/query/
├── handler.ts          # Ponto de entrada HTTP — orquestra, não contém lógica de negócio
├── validator.ts        # Schema Zod de input/output — sem lógica condicional
└── response-builder.ts # Monta o objeto de resposta final
```

Regras:

- `handler.ts` DEVE ter no máximo 50 linhas. Lógica de negócio vai em `src/services/`.
- Nunca colocar chamadas a Azure AI Search ou Azure OpenAI diretamente em `handler.ts` — sempre via `src/services/`.
- Imports de serviços externos SEMPRE via injeção de dependência ou factory — facilita mocking nos testes.

### Azure Functions v4

**DEVE:**

```typescript
// DO: estrutura padrão de HTTP trigger v4
import {
  app,
  HttpRequest,
  HttpResponseInit,
  InvocationContext,
} from "@azure/functions";
import { z } from "zod";
import { logger } from "../../shared/logger";

const QueryInputSchema = z.object({
  question: z.string().min(1).max(500),
  clientTier: z.enum(["Gold", "Silver", "Standard"]).optional(),
  sessionId: z.string().uuid().optional(),
});

export async function queryHandler(
  request: HttpRequest,
  context: InvocationContext,
): Promise<HttpResponseInit> {
  const log = logger.child({ invocationId: context.invocationId });
  // ...
  return { status: 200, jsonBody: response };
}

app.http("query", {
  methods: ["POST"],
  authLevel: "function",
  handler: queryHandler,
});
```

**NÃO DEVE:**

```typescript
// DON'T: v3 style com module.exports
module.exports = async function(context, req) { ... }

// DON'T: console.log diretamente
console.log('Processing request...');

// DON'T: throw genérico sem tipo customizado
throw new Error('Something went wrong');
```

### Validação com Zod

- Todo endpoint DEVE validar input e output com schemas Zod definidos em `validator.ts`
- Schemas de output incluem o campo `source_document` (obrigatório — ver Product Rules)
- Parse acontece no início do handler, antes de qualquer lógica de negócio:

```typescript
// DO
const parsed = QueryInputSchema.safeParse(await request.json());
if (!parsed.success) {
  return {
    status: 400,
    jsonBody: { error: "Invalid input", details: parsed.error.issues },
  };
}

// DON'T: acessar body sem validação
const { question } = (await request.json()) as any;
```

### Logging com pino

- NUNCA usar `console.log`, `console.error` ou qualquer outro `console.*`
- O logger é inicializado em `src/shared/logger.ts` e importado pelos módulos
- Usar `logger.child()` com contexto de invocação para rastrear requests

```typescript
// DO
import { logger } from "../../shared/logger";
const log = logger.child({
  invocationId: context.invocationId,
  operation: "search",
});
log.info({ query, topK }, "Initiating chunk search");
log.error({ err, query }, "Search failed");

// DON'T
console.log("Searching for:", query);
```

Níveis:

- `log.info` — fluxo normal (início/fim de operação, resultados)
- `log.warn` — situação inesperada mas recuperável (chunk com score baixo, histórico truncado)
- `log.error` — falha com impacto (chamada Azure falhou, prompt não carregou)
- `log.debug` — apenas em desenvolvimento local — NUNCA em código commitado sem `if (process.env.NODE_ENV === 'development')`

### Tratamento de erros

Custom errors vivem em `src/shared/errors.ts`. Todo handler DEVE capturar e mapear para HTTP responses adequados:

```typescript
// DO: erros tipados e mapeados
import {
  SearchServiceError,
  SystemPromptLoadError,
  ContextBudgetExceededError,
  ConfigurationError,
} from "../../shared/errors";

try {
  const chunks = await searchService.query(question, 5);
} catch (err) {
  if (err instanceof SearchServiceError) {
    log.error({ err }, "Azure AI Search unavailable");
    return {
      status: 503,
      jsonBody: { error: "Search service unavailable. Please try again." },
    };
  }
  if (err instanceof ContextBudgetExceededError) {
    log.warn({ err }, "Context budget exceeded — truncating");
    // truncate and retry — não retorna erro para o usuário
  }
  throw err; // erros não tratados propagam para o runtime do Azure Functions
}

// DON'T: catch genérico que engole o erro
try {
  // ...
} catch (e) {
  return { status: 500, jsonBody: { error: "Internal error" } };
}
```

**Regra adicional — falhas de configuração:** Handlers que detectam falha de configuração (env var ausente, arquivo não carregado, versão inválida) DEVEM lançar um `ConfigurationError` de `src/shared/errors.ts` antes de retornar HTTP 500. Nunca retornar 500 diretamente sem o custom error tipado — isso garante rastreabilidade nos logs.

```typescript
// DO: falha de configuração com custom error tipado
import { ConfigurationError } from "../../shared/errors";

const version = loadPackageVersion();
if (version === null) {
  throw new ConfigurationError(
    "Package version could not be loaded from package.json",
  );
}

// DON'T: retornar 500 direto sem custom error
if (version === null) {
  return { status: 500, jsonBody: { error: "Version unavailable" } };
}
```

**Exceção documentada — endpoints sem chamadas externas:** Endpoints que não fazem chamadas a serviços externos (ex: health check) estão isentos da regra de retry. Documentar no handler com comentário obrigatório:

```typescript
// No external calls — retry not applicable
```

### Retry com exponential backoff

Chamadas a Azure OpenAI e Azure AI Search DEVEM ter retry:

- Máximo 3 tentativas
- Backoff: 1s → 2s → 4s (exponencial)
- Retry apenas em erros transitórios (429 rate limit, 503 service unavailable)
- Nunca retry em erros de validação (400, 401, 403)

### Git e commits

- Conventional Commits obrigatório: `type(scope): description`
  - Tipos: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`
  - Scopes: `query`, `feedback`, `pipeline`, `bot`, `web`, `shared`, `infra`, `prompts`, `skills`
  - Exemplos: `feat(query): add source_document to response schema`, `fix(pipeline): handle PDF with embedded images`
- Mensagem em inglês — ver Product Management Rules para idioma de documentação
- Branch naming: `feature/<slug>`, `fix/<slug>`, `chore/<slug>`
- **Sugestão de commit ao concluir geração:** Ao gerar ou modificar um arquivo, sugerir a mensagem de commit correspondente no formato Conventional Commits. Exemplo: ao gerar `src/functions/health/handler.ts`, sugerir `feat(health): add health check endpoint with version from package.json`

> **Nota sobre PRs nesta fase:** Como o repositório é local (sem remoto), "abrir PR" significa criar a branch e escrever o arquivo `docs/pull-requests/PR-NNNN.md` com objetivo, mudanças, checklist de validation gates e screenshots/outputs relevantes. A revisão é feita localmente pelo Tech Lead.

---

## Product Rules & Guardrails

> _(Seção a ser escrita pelo Product Specialist — Exercício 2.3 do Cenário 2)_

**Placeholder:** Esta seção conterá as regras de comportamento do assistente (DEVE / NÃO DEVE / QUANDO EM DÚVIDA), o glossário de linguagem ubíqua do domínio (termos como "cliente Gold", "carga perigosa", "SLA de resolução", "multiplicador regional") e as restrições que impactam geração de código (ex: campo `source_document` obrigatório no JSON de resposta).

**Campo obrigatório no schema de resposta** (antecipado aqui pois impacta Coding Standards):
Toda resposta da API DEVE incluir o campo `source_document` mesmo quando confiança for baixa. O schema mínimo é:

```typescript
// src/shared/types.ts
export interface AssistantResponse {
  answer: string;
  source_document: {
    doc_id: string;
    doc_title: string;
    section: string;
    version_date: string;
  } | null; // null APENAS quando o modelo explicitamente não encontrou resposta
  confidence: "high" | "low" | "not_found";
  has_conflict: boolean; // true quando há versões contraditórias nos chunks recuperados
}
```

---

## Testing Standards

> _(Seção a ser escrita pelo QA — Exercício 2.1 do Cenário 2)_

**Placeholder:** Esta seção conterá: padrão de nomenclatura (describe/it), estrutura obrigatória (arrange/act/assert), padrão de mocking (msw para HTTP externo, factories para dados), e padrão de fixtures em `tests/fixtures/`.

**Configuração já definida pelo Tech Lead:**

- Framework: Vitest (configurado em `vitest.config.ts`)
- Coverage mínimo: 80% de linhas para código em `src/services/` e `src/functions/`
- Comando: `npm test` (unit + integration); `npm run test:e2e` (e2e — uso restrito, consome tokens)

---

## Project Management Rules

> _(Seção a ser escrita pelo Delivery Manager — Exercício 2.3 do Cenário 2)_

**Placeholder:** Esta seção conterá: regras de nomenclatura de tasks e issues, regras de documentação de decisões (ADRs), definição dos validation gates em formato consumível por agentes, e restrições de comunicação (código e comments em inglês; documentação de status em português).

---

## Build & Deploy

### Comandos locais

```bash
# Instalar dependências
npm install

# Build TypeScript
npm run build

# Testes unitários + integração
npm test

# Testes e2e (usar com cautela — consome tokens reais em staging)
npm run test:e2e

# Lint
npm run lint

# Type check sem build
npm run typecheck
```

### Pipeline de CI (`.github/workflows/ci.yml`)

Roda em todo push e PR. Gates obrigatórios — build falha se qualquer um falhar:

1. `npm run lint` — zero warnings tolerados
2. `npm run typecheck` — zero erros TypeScript
3. `npm test` — coverage ≥ 80% em `src/services/` e `src/functions/`
4. Build final: `npm run build`

**Nenhum código com falha de lint ou typecheck chega à branch main.**

### Pipeline de CD (`.github/workflows/cd.yml`)

> Estado narrativo nesta fase — não há recursos Azure provisionados.

Fluxo planejado:

- Push em `main` → deploy automático em `staging`
- Deploy em `production` → manual, aprovação do Tech Lead obrigatória
- Rollback: re-deploy do commit anterior via workflow dispatch

### Variáveis de ambiente

Nunca commitar secrets. O arquivo `.env` está no `.gitignore`. Para desenvolvimento local, copiar `.env.example` e preencher:

```
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_KEY=
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_SEARCH_ENDPOINT=
AZURE_SEARCH_KEY=
AZURE_SEARCH_INDEX=novatech-docs
```

Para staging e produção, variáveis são injetadas via Azure Key Vault — nunca via arquivo `.env` no servidor.

### Infra como código

Recursos Azure definidos em `/infra/`. Aplicar via:

```bash
# Deploy de infra (staging)
az deployment group create \
  --resource-group rg-novatech-staging \
  --template-file infra/main.bicep \
  --parameters infra/parameters/staging.bicepparam
```

Toda mudança em `/infra/` requer aprovação do Tech Lead antes de apply em produção.

---

## Referências rápidas

| O que procuro                       | Onde está                                                  |
| ----------------------------------- | ---------------------------------------------------------- |
| Decisões arquiteturais              | `docs/adr/`                                                |
| System prompt do assistente         | `prompts/system-prompt.md`                                 |
| Histórico de mudanças no prompt     | `prompts/prompt-changelog.md`                              |
| Perguntas de referência para testes | `prompts/eval/golden-queries.json`                         |
| Specs de cada módulo                | `specs/<nome-do-modulo>/`                                  |
| Skills de geração de código         | `skills/foundation/`, `skills/domain/`, `skills/artifact/` |
| Documentação NovaTech (fonte)       | `docs/novatech/`                                           |
| Chunks de referência (teste RAG)    | `data/retrieval-corpus/`                                   |
| Tipos TypeScript do domínio         | `src/shared/types.ts`                                      |
| Custom errors                       | `src/shared/errors.ts`                                     |
| Fixtures de teste                   | `tests/fixtures/`                                          |

---

_Última atualização: Fase de Estruturação (Cenário 2) — Tech Lead_
_Próxima revisão prevista: ao final do Cenário 3 (Harness Engineering)_
