# SKILL — azure-functions-endpoint

**Nível:** Domain  
**Caminho:** `skills/domain/azure-functions-endpoint.md`  
**Versão:** 1.0  

## Quando usar esta skill

Use esta skill sempre que for criar ou modificar um endpoint HTTP no projeto NovaTech Assistant. Frases que ativam esta skill:

- "crie um endpoint para..."
- "implemente o handler de..."
- "adicione uma Azure Function que..."
- "gere o arquivo handler.ts para..."

## Dependências — leia antes de gerar

Antes de gerar qualquer endpoint, leia estas skills Foundation:

1. `skills/foundation/typescript-conventions.md` — tipos, imports, naming
2. `skills/foundation/error-handling.md` — custom errors, retry, logging
3. `skills/foundation/project-structure.md` — onde cada arquivo vai

E estas seções do AGENTS.md:
- `## Coding Standards > Azure Functions v4` — estrutura obrigatória
- `## Coding Standards > Validação com Zod` — schemas de input/output
- `## Coding Standards > Logging com pino` — nunca console.log
- `## Tech Stack & Architecture > Gerenciamento de contexto` — context budget

---

## Estrutura obrigatória de um endpoint

Todo endpoint tem exatamente 3 arquivos. Nunca menos, nunca mais em um único módulo:

```
src/functions/<nome-do-endpoint>/
├── handler.ts          → ponto de entrada HTTP, orquestra, ≤ 50 linhas
├── validator.ts        → schemas Zod de input e output, sem lógica condicional
└── response-builder.ts → monta o objeto de resposta final tipado
```

### Responsabilidades por arquivo

**`handler.ts`** — orquestra, não processa:
- Recebe o `HttpRequest`
- Chama `validator.ts` para validar input
- Chama serviços em `src/services/` para lógica de negócio
- Chama `response-builder.ts` para montar a resposta
- Retorna `HttpResponseInit`
- Registra a rota com `app.http()`
- **Nunca** contém lógica de negócio
- **Nunca** chama Azure AI Search ou Azure OpenAI diretamente
- **Máximo 50 linhas**

**`validator.ts`** — schemas puros, sem lógica:
- Define e exporta schemas Zod de input e output
- Exporta os tipos TypeScript inferidos dos schemas
- **Nunca** contém `if`, `for`, ou lógica condicional
- **Nunca** importa serviços ou outros módulos além de `zod`

**`response-builder.ts`** — monta respostas tipadas:
- Recebe dados processados e monta o objeto de resposta
- Garante que `source_document` está presente quando obrigatório
- Lida com casos de confiança baixa e ausência de resposta
- **Nunca** chama serviços externos

---

## Regras prescritivas

### DEVE

**Estrutura do handler:**
```typescript
// handler.ts — estrutura completa obrigatória
import { app, HttpRequest, HttpResponseInit, InvocationContext } from '@azure/functions';
import { logger } from '../../shared/logger';
import { FeedbackInputSchema } from './validator';
import { buildFeedbackResponse } from './response-builder';
import { feedbackService } from '../../services/feedback';
import { ValidationError } from '../../shared/errors';

export async function feedbackHandler(
  request: HttpRequest,
  context: InvocationContext,
): Promise<HttpResponseInit> {
  const log = logger.child({
    invocationId: context.invocationId,
    operation: 'feedback',
  });

  // 1. Validar input — sempre primeiro
  const body = await request.json().catch(() => null);
  const parsed = FeedbackInputSchema.safeParse(body);
  if (!parsed.success) {
    log.warn({ issues: parsed.error.issues }, 'Invalid feedback input');
    return {
      status: 400,
      jsonBody: { error: 'Invalid input', details: parsed.error.issues },
    };
  }

  log.info({ queryId: parsed.data.queryId }, 'Processing feedback');

  // 2. Chamar serviço — toda lógica de negócio fica aqui
  try {
    const result = await feedbackService.record(parsed.data);
    log.info({ queryId: parsed.data.queryId }, 'Feedback recorded');
    return buildFeedbackResponse(result);
  } catch (err) {
    log.error({ err, queryId: parsed.data.queryId }, 'Feedback service failed');
    return { status: 503, jsonBody: { error: 'Service temporarily unavailable' } };
  }
}

// Registro da rota — sempre no final do arquivo
app.http('feedback', {
  methods: ['POST'],
  authLevel: 'function',
  handler: feedbackHandler,
});
```

**Estrutura do validator:**
```typescript
// validator.ts — schemas e tipos, nada mais
import { z } from 'zod';

export const FeedbackInputSchema = z.object({
  queryId: z.string().uuid(),
  rating: z.enum(['correct', 'incorrect', 'incomplete']),
  comment: z.string().max(500).optional(),
  agentId: z.string().min(1),
});

export const FeedbackOutputSchema = z.object({
  feedbackId: z.string().uuid(),
  status: z.enum(['recorded', 'pending_review']),
  recordedAt: z.string().datetime(),
});

// Tipos inferidos — use estes em todo o módulo, nunca redefina manualmente
export type FeedbackInput = z.infer<typeof FeedbackInputSchema>;
export type FeedbackOutput = z.infer<typeof FeedbackOutputSchema>;
```

**Estrutura do response-builder:**
```typescript
// response-builder.ts — monta HttpResponseInit tipado
import { HttpResponseInit } from '@azure/functions';
import { FeedbackOutput, FeedbackOutputSchema } from './validator';

export function buildFeedbackResponse(data: FeedbackOutput): HttpResponseInit {
  const parsed = FeedbackOutputSchema.safeParse(data);

  if (!parsed.success) {
    return {
      status: 500,
      jsonBody: { error: 'Response validation failed' },
    };
  }

  return {
    status: 201,
    jsonBody: parsed.data,
  };
}
```

**Mapeamento de HTTP status — use sempre estes:**

| Situação | Status | Quando usar |
|---|---|---|
| Criação bem-sucedida | 201 | POST que cria recurso |
| Consulta bem-sucedida | 200 | GET, POST de query |
| Input inválido | 400 | Falha no safeParse do input |
| Não autorizado | 401 | Token ausente ou inválido |
| Recurso não encontrado | 404 | ID não existe na base |
| Serviço indisponível | 503 | Azure Search, OpenAI fora do ar |
| Erro interno | 500 | Erro inesperado não mapeado |

**Ordem obrigatória dentro do handler:**
1. Inicializar logger com child
2. Validar input (safeParse) → retornar 400 se inválido
3. Log de início da operação
4. Chamar serviço em try/catch
5. Log de sucesso ou erro
6. Retornar resposta via response-builder

---

### NÃO DEVE

**Anti-padrão 1 — lógica de negócio no handler:**
```typescript
// DON'T: handler processando dados diretamente
export async function feedbackHandler(request, context) {
  const body = await request.json();

  // ❌ lógica de negócio dentro do handler
  const feedbackId = crypto.randomUUID();
  const existing = await db.query(`SELECT * FROM feedback WHERE queryId = ?`, [body.queryId]);
  if (existing.length > 0) {
    return { status: 409, jsonBody: { error: 'Already rated' } };
  }
  await db.insert('feedback', { feedbackId, ...body });

  return { status: 201, jsonBody: { feedbackId } };
}

// DO: delegar ao serviço
export async function feedbackHandler(request, context) {
  // ... validação ...
  const result = await feedbackService.record(parsed.data); // ← serviço cuida da lógica
  return buildFeedbackResponse(result);
}
```

**Anti-padrão 2 — validação inline sem validator.ts:**
```typescript
// DON'T: schema Zod definido dentro do handler
export async function feedbackHandler(request, context) {
  const schema = z.object({ queryId: z.string() }); // ❌ schema inline
  const parsed = schema.safeParse(await request.json());
  // ...
}

// DO: importar do validator.ts
import { FeedbackInputSchema } from './validator';
const parsed = FeedbackInputSchema.safeParse(body);
```

**Anti-padrão 3 — await request.json() sem catch:**
```typescript
// DON'T: body pode ser inválido e lançar exceção não tratada
const body = await request.json();

// DO: capturar falha de parse do body
const body = await request.json().catch(() => null);
const parsed = FeedbackInputSchema.safeParse(body);
// safeParse retorna error se body for null — tratado pelo 400
```

**Anti-padrão 4 — registro de rota no meio do arquivo:**
```typescript
// DON'T: app.http() no meio do arquivo confunde a leitura
app.http('feedback', { methods: ['POST'], handler: feedbackHandler });

export async function feedbackHandler(...) { ... }

// DO: app.http() sempre no final
export async function feedbackHandler(...) { ... }

app.http('feedback', {
  methods: ['POST'],
  authLevel: 'function',
  handler: feedbackHandler,
});
```

**Anti-padrão 5 — retornar erro genérico sem log:**
```typescript
// DON'T: engole o erro sem registrar
} catch (err) {
  return { status: 500, jsonBody: { error: 'Internal error' } };
}

// DO: log antes de retornar
} catch (err) {
  log.error({ err, queryId: parsed.data.queryId }, 'Feedback service failed');
  return { status: 503, jsonBody: { error: 'Service temporarily unavailable' } };
}
```

**Anti-padrão 6 — `authLevel: 'anonymous'` em endpoints de negócio:**
```typescript
// DON'T: endpoint de negócio sem autenticação
app.http('feedback', {
  methods: ['POST'],
  authLevel: 'anonymous', // ❌ só o health check usa anonymous
  handler: feedbackHandler,
});

// DO: authLevel function para endpoints de negócio
app.http('feedback', {
  methods: ['POST'],
  authLevel: 'function', // ← requer function key no header
  handler: feedbackHandler,
});
```

---

## Checklist antes de considerar o endpoint pronto

Antes de commitar, verifique cada item:

- [ ] `handler.ts` tem ≤ 50 linhas
- [ ] `validator.ts` existe e contém todos os schemas Zod
- [ ] `response-builder.ts` existe e valida o output antes de retornar
- [ ] `await request.json()` tem `.catch(() => null)`
- [ ] Input validado com `safeParse` antes de qualquer lógica
- [ ] Logger inicializado com `logger.child({ invocationId, operation })`
- [ ] Todos os catch blocks têm `log.error` antes do return
- [ ] `app.http()` está no final do `handler.ts`
- [ ] `authLevel: 'function'` (exceto health check que usa `anonymous`)
- [ ] HTTP status correto para cada caso (201 para criação, 503 para serviço indisponível)
- [ ] Nenhum `console.log` ou `console.error`
- [ ] Nenhum `any` nos tipos

---

## Exemplo de uso desta skill no Copilot

Prompt sugerido para gerar um endpoint novo:

```
Read AGENTS.md and skills/domain/azure-functions-endpoint.md before generating.

Generate the feedback endpoint for this project following the skill exactly.
Files to create:
- src/functions/feedback/handler.ts
- src/functions/feedback/validator.ts  
- src/functions/feedback/response-builder.ts

The feedback endpoint receives: queryId (UUID), rating (correct/incorrect/incomplete),
comment (optional string max 500), agentId (string).
Returns: feedbackId (UUID), status, recordedAt (ISO datetime).
Auth level: function.
HTTP method: POST.
```

---

## Critérios de maturidade desta skill

Esta skill está madura e pronta para uso pelo time quando:

**Critério 1 — Cobertura de anti-padrões validada**
O Copilot gerou ao menos 3 endpoints diferentes usando esta skill e nenhum deles continha os 6 anti-padrões listados acima.

**Critério 2 — Checklist passando sem intervenção**
Os endpoints gerados passam no checklist de 12 itens sem o dev precisar corrigir nenhum manualmente.

**Critério 3 — Consistência entre devs**
Dois devs diferentes geraram endpoints para o mesmo requisito e os outputs são estruturalmente idênticos (mesma organização de arquivos, mesmo padrão de error handling, mesmo mapeamento de status codes).

**Critério 4 — Testes geráveis**
O código gerado pela skill é testável sem refatoração — serviços injetáveis, sem dependências hard-coded, schemas exportados do validator.ts.

**Critério 5 — Sem regressão após atualização**
Quando a skill for atualizada (nova regra, novo anti-padrão), endpoints gerados com a versão anterior continuam funcionando — a skill não quebra código existente.

---

*Skill criada na fase de Estruturação (Cenário 2) — Tech Lead*  
*Próxima revisão: após geração dos 5 endpoints do projeto*
