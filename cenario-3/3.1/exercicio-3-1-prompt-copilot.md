# Prompt para GitHub Copilot — response-validator.ts

## Como usar
Abra o arquivo `src/services/response-validator.ts` no seu repositório (crie se não existir) e cole este prompt como comentário no topo. O Copilot vai sugerir o código linha a linha conforme você der Enter.

Alternativamente, use o Copilot Chat (Ctrl+I ou painel lateral) e cole o prompt diretamente.

---

## Prompt

```
Crie um módulo TypeScript chamado response-validator.ts seguindo rigorosamente as regras do AGENTS.md do projeto:
- TypeScript strict mode
- Zod para validação de schema (nunca usar "as any")
- pino para logging (nunca console.log)
- Nunca logar dados pessoais (e-mail, nome do atendente)
- Imports estáticos no topo (nunca require dinâmico)

O módulo deve exportar:

1. Um schema Zod chamado AssistantResponseSchema com três campos obrigatórios:
   - answer: string não vazia
   - source_document: string não vazia (identificador curto do documento)
   - confidence_score: number entre 0 e 1

2. O tipo TypeScript AssistantResponse inferido do schema.

3. Uma constante VALID_SOURCE_DOCUMENTS do tipo Set<string> com os identificadores válidos:
   POL-001, PROC-042, PROC-042-v2, SLA-2024, FAQ-Atendimento

4. Uma interface ValidationResult com os campos:
   - valid: boolean
   - response: AssistantResponse
   - rejectionReason?: string (opcional, presente quando valid é false)
   - requiresHumanReview?: boolean (opcional, true quando deve ir para fila de revisão humana)

5. Uma constante FALLBACK_RESPONSE do tipo AssistantResponse usada quando a validação falha:
   - answer: "Não foi possível processar esta resposta com segurança. Por favor, escale para o supervisor."
   - source_document: "N/A"
   - confidence_score: 0

6. Uma função exportada validateResponse(rawResponse: unknown): ValidationResult que aplica três verificações em sequência, parando na primeira falha:

   Verificação 1 — Schema:
   Usa AssistantResponseSchema.safeParse(rawResponse).
   Se falhar: loga com pino (warn) o motivo e o rawResponse, retorna ValidationResult com valid: false e a FALLBACK_RESPONSE.

   Verificação 2 — Fonte válida:
   Verifica se response.source_document está em VALID_SOURCE_DOCUMENTS.
   Se não estiver: loga com pino (warn) o source_document inválido, retorna ValidationResult com valid: false e a FALLBACK_RESPONSE.
   Nunca logar o campo "answer" completo nesta etapa (pode conter dados sensíveis).

   Verificação 3 — Conteúdo de risco:
   Chama uma função interna detectDangerousCargoReturnClaim(answer: string): boolean.
   Esta função retorna true se a resposta mencionar carga perigosa E afirmar que devolução é possível SEM conter uma negativa explícita.
   A função deve usar expressões regulares que cubram variações em português:
   - Variações de "carga perigosa": carga perigosa, cargas perigosas, produto perigoso, produtos perigosos
   - Variações de devolução: devolução, devolver, devolvida, devolvido, retorno, retornar
   - Negativas que indicam que a devolução NÃO é possível: "não pode", "não é possível", "não será possível", "impossível", "vedado", "proibido"
   Se detectDangerousCargoReturnClaim retornar true: loga com pino (warn) indicando conteúdo de risco, retorna ValidationResult com valid: false, FALLBACK_RESPONSE e requiresHumanReview: true.

   Se passar nas três verificações: retorna ValidationResult com valid: true e a response parseada.

O logger pino deve ser instanciado com name: "response-validator".
Todos os logs de rejeição devem ter nível warn.
Nenhum log deve conter e-mail, nome ou qualquer dado pessoal do atendente.
```

---

## O que revisar após o Copilot gerar

Verifique estes pontos antes de aceitar o código:

**1. O schema aceita campos extras?**
O Zod por padrão ignora campos extras no objeto. Se o Copilot não usar `.strict()`, adicione manualmente:
```typescript
export const AssistantResponseSchema = z.object({ ... }).strict();
```

**2. O regex cobre variações com acento?**
Verifique se o regex para "devolução" cobre também "devolucao" (sem cedilha) e se usa flags case-insensitive (`/regex/i` ou `.toLowerCase()` antes de testar).

**3. O log da verificação 2 expõe o campo `answer`?**
O `source_document` pode ser logado (é o identificador do documento, não dado pessoal). O `answer` não deve aparecer em logs nesta etapa.

**4. O import do pino está estático no topo?**
```typescript
// CORRETO
import pino from 'pino';

// ERRADO — Copilot às vezes gera isso
const pino = require('pino');
```

**5. A função detectDangerousCargoReturnClaim está como função interna (não exportada)?**
Ela é um detalhe de implementação — não precisa ser exportada.

---

## Após implementar — teste manual rápido

Cole isso num arquivo de teste temporário para verificar os três caminhos:

```typescript
import { validateResponse } from './response-validator';

// Deve passar: fonte válida, sem conteúdo de risco
console.log(validateResponse({
  answer: "O prazo de devolução é de 7 dias úteis.",
  source_document: "POL-001",
  confidence_score: 0.9
}));

// Deve falhar: fonte inválida
console.log(validateResponse({
  answer: "Resposta qualquer.",
  source_document: "DOCUMENTO-INEXISTENTE",
  confidence_score: 0.8
}));

// Deve falhar com requiresHumanReview: true
console.log(validateResponse({
  answer: "Cargas perigosas podem ser devolvidas em até 7 dias.",
  source_document: "POL-001",
  confidence_score: 0.85
}));

// Deve passar: menciona carga perigosa mas com negativa
console.log(validateResponse({
  answer: "Cargas perigosas não podem ser devolvidas pelo processo padrão.",
  source_document: "POL-001",
  confidence_score: 0.95
}));
```

---

*Prompt para Copilot — Exercício 3.1 Tech Lead | Cenário 3 | Junho/2025*
