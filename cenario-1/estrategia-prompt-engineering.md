# Estratégia de Prompt Engineering — NovaTech Assistente

**Versão:** 1.0  
**Data:** Junho/2025  
**Autor:** Tech Lead DB1  
**Status:** Aceito para piloto

---

## 1. Princípio: Prompt é Código

O system prompt do assistente NovaTech não é um texto de configuração informal — é um artefato de software com impacto direto no comportamento do sistema em produção. Ele deve ser tratado com o mesmo rigor que qualquer outro componente de código:

- **Versionado** no repositório Git do projeto.
- **Testado** com suite de casos automatizados antes de qualquer mudança ir para produção.
- **Revisado** via Pull Request, com aprovação obrigatória do Tech Lead.
- **Auditável** — cada versão do prompt deve ter rastreabilidade de quem mudou o quê e por quê.

---

## 2. Estrutura de Armazenamento no Repositório

```
/prompts/
  system/
    v1.0.0-novatech-atendimento.md       ← versão atual em produção
    v0.9.0-novatech-atendimento.md       ← versão anterior
    v0.8.0-novatech-atendimento.md
  templates/
    context-customer-metadata.md        ← template do bloco de metadados do cliente
    context-chunks-section.md           ← template do bloco de chunks recuperados
    context-history-section.md          ← template do bloco de histórico
  tests/
    prompt-test-suite.json              ← casos de teste automatizados
    expected-outputs/
      test-001-prazo-devolucao.txt
      test-002-sla-gold.txt
      ...
  CHANGELOG.md                          ← histórico de mudanças com justificativa
```

### Convenção de nomenclatura:
`v{MAJOR}.{MINOR}.{PATCH}-{projeto}-{uso}.md`

- **MAJOR**: mudança na identidade, guardrails fundamentais, ou estrutura de resposta.
- **MINOR**: adição de nova regra ou domínio coberto.
- **PATCH**: correção de comportamento específico sem mudança estrutural.

### Quem pode alterar:
- **Qualquer desenvolvedor:** pode propor via PR com casos de teste adicionados.
- **Tech Lead:** aprovação obrigatória para MAJOR e MINOR.
- **Product Specialist:** deve ser consultado para mudanças que afetam comportamento visível ao atendente.
- **Ninguém** altera o prompt diretamente em produção sem passar pelo processo.

---

## 3. Anatomia do Contexto — Orçamento por Parte

O "contexto" que o LLM recebe não é apenas o system prompt — é a composição de múltiplas partes, cada uma com tamanho e prioridade definidos. O orçamento total é de **16.000 tokens** por query (ver ADR-0002).

```
┌─────────────────────────────────────────────────────────────┐
│  CONTEXTO TOTAL: ~16.000 tokens                             │
│                                                             │
│  [A] SYSTEM PROMPT (ESTÁTICO)           ~1.500 tokens       │
│      - Identidade do assistente         ~100 tokens         │
│      - Guardrails e regras              ~600 tokens         │
│      - Formato de resposta              ~300 tokens         │
│      - Tratamento de contradições       ~300 tokens         │
│      - Tratamento de ausência de info   ~200 tokens         │
│                                                             │
│  [B] METADADOS DO CLIENTE (DINÂMICO)    ~200 tokens         │
│      - Tier (Gold/Silver/Standard)                          │
│      - Número do contrato                                   │
│      - Flags especiais (ex: em transição de tabela)         │
│                                                             │
│  [C] CHUNKS RECUPERADOS (DINÂMICO)      ~6.000 tokens       │
│      - 8–12 chunks de ~500–750 tokens cada                  │
│      - Ordenados do mais para o menos relevante             │
│      - Com metadados de fonte e versão                      │
│                                                             │
│  [D] HISTÓRICO DE CONVERSA (DINÂMICO)   ~3.000 tokens       │
│      - Cap: últimas 4 trocas                                │
│      - Truncado pela janela deslizante                      │
│                                                             │
│  [E] PERGUNTA ATUAL (DINÂMICO)          ~500 tokens         │
│      - Pergunta do atendente                                │
│      - Contexto imediato (ex: número do chamado)            │
│                                                             │
│  [F] BUFFER DE SEGURANÇA                ~4.800 tokens       │
│      - Acomoda variações + resposta do modelo               │
└─────────────────────────────────────────────────────────────┘
```

### Por que essa ordem importa (Lost in the Middle)

O modelo processa melhor informação no início e no fim do contexto. Por isso:
- **[A] System prompt** vem primeiro — os guardrails ficam na posição de maior atenção.
- **[C] Chunks** vêm logo depois — a informação mais relevante para responder fica próxima ao início.
- **[E] Pergunta atual** vem por último — segunda posição de maior atenção, garantindo que o modelo "chegue" à pergunta com o contexto fresco.
- **[D] Histórico** fica no meio — é importante para continuidade, mas não é crítico que o modelo o processe com máxima atenção.

---

## 4. System Prompt v1.0.0 — Versão de Produção

```markdown
## IDENTIDADE

Você é o Assistente de Atendimento da NovaTech, empresa de logística.
Seu papel é ajudar os atendentes da NovaTech a encontrar informações sobre 
procedimentos, políticas, SLAs e regras de frete com base na documentação oficial.

Você NÃO atende clientes finais diretamente. Você apoia os atendentes internos.

---

## REGRAS FUNDAMENTAIS (GUARDRAILS)

**R1 — Grounding obrigatório:**
Responda SOMENTE com base nos documentos fornecidos no contexto desta mensagem.
Nunca invente prazos, valores, multiplicadores, nomes de procedimentos ou 
qualquer dado que não esteja explicitamente nos documentos fornecidos.

**R2 — Citação de fonte obrigatória:**
Toda resposta que contenha um dado factual (prazo, valor, multiplicador, 
nome de procedimento, SLA) deve citar a fonte no formato:
[Fonte: {NOME_DO_DOCUMENTO}, seção {SEÇÃO}, versão {VERSÃO}]

**R3 — Ausência de informação:**
Se a informação necessária para responder não estiver nos documentos fornecidos,
responda exatamente assim:
"Não encontrei essa informação na documentação disponível. Recomendo escalar 
para o supervisor ou consultar diretamente a área responsável."
NUNCA tente responder "com base no senso comum" ou "provavelmente".

**R4 — Documentos contraditórios:**
Se você receber chunks de documentos com o mesmo nome mas versões diferentes:
1. Use SEMPRE os valores da versão mais recente (verifique o campo "emission_date").
2. Informe ao atendente que existe uma versão anterior com valores diferentes.
3. Se a pergunta envolver chamados abertos antes de 01/12/2023, alerte o atendente 
   para verificar manualmente qual versão se aplica ao caso.
4. NUNCA misture valores de versões diferentes no mesmo cálculo.

**R5 — Idioma e tom:**
Responda em português formal e acessível. Evite jargão técnico desnecessário.
Seja direto: forneça a informação que o atendente precisa, não uma introdução longa.

---

## FORMATO DE RESPOSTA

Para perguntas factuais simples:
```
[Resposta direta em 1–3 frases]
[Fonte: Documento X, seção Y, versão Z]
```

Para perguntas que exigem procedimento:
```
[Resposta direta]

Passos:
1. [passo 1]
2. [passo 2]
...

[Fonte: Documento X, seção Y, versão Z]
```

Para situações com contradição entre versões:
```
[Resposta com a versão mais recente]
[Fonte: versão mais recente]

⚠️ Atenção: existe versão anterior (Documento X, vY) com valor diferente ([valor antigo]).
Para chamados abertos antes de [data de transição], verifique com o supervisor 
qual versão se aplica.
```

Para situações sem resposta na documentação:
```
Não encontrei essa informação na documentação disponível.
Recomendo escalar para o supervisor ou consultar diretamente a área responsável.
```

---

## CONTEXTO DOS DOCUMENTOS

[Os chunks recuperados pelo pipeline serão inseridos aqui em tempo de execução]
```

---

## 5. Enforcement: Probabilístico vs. Determinístico

Os guardrails do sistema não podem depender apenas do comportamento do modelo (probabilístico). Alguns devem ser enforçados por código externo ao LLM (determinístico).

### Guardrails Probabilísticos (enforçados no prompt)

Estes dependem do modelo seguir as instruções. São adequados para comportamentos que têm graus de qualidade (não são binários pass/fail):

| Guardrail | Por que probabilístico | Risco de falha |
|---|---|---|
| Tom formal e acessível | Qualidade gradual, não binária | Baixo — falha gera resposta informal, não incorreta |
| Indicar versão mais recente em contradições | Requer raciocínio sobre metadados | Médio — falha gera confusão, não dado errado |
| Estrutura de resposta (formato) | Preferência de formatação | Baixo — afeta legibilidade, não conteúdo |
| Não inventar dados | Instrução direta ao modelo | **Alto** — requer reforço determinístico |

### Guardrails Determinísticos (enforçados fora do prompt — no Harness)

Estes são verificados por código após a geração, antes de enviar ao atendente:

| Guardrail | Implementação | Ação se falhar |
|---|---|---|
| **Resposta contém citação de fonte** | Regex: detecta padrão `[Fonte: ...]` | Bloqueia resposta e retorna mensagem padrão de erro |
| **Resposta não contém afirmações sobre "Platinum"** | Regex/keyword: detecta "tier Platinum", "cliente Platinum" | Bloqueia e injeta correção ("o tier Platinum não existe") |
| **Resposta não inverte regras críticas** | Keyword: detecta "carga perigosa pode ser devolvida" sem condicional | Flag para revisão humana |
| **Resposta não excede tamanho máximo** | Count tokens do output | Trunca com aviso |
| **Resposta está em português** | Detect language | Bloqueia e solicita regeneração |

### Diagrama de fluxo do Harness:

```
Atendente faz pergunta
       ↓
Pipeline RAG recupera chunks
       ↓
Monta contexto (system prompt + chunks + histórico + pergunta)
       ↓
Envia ao LLM (GPT-4o via Azure OpenAI)
       ↓
Recebe resposta do LLM
       ↓
[HARNESS — verificações determinísticas]
  ├─ Contém citação de fonte? → NÃO → Bloqueia, retorna erro padrão
  ├─ Menciona "Platinum"? → SIM → Injeta correção
  ├─ Inverte regra crítica? → SIM → Flag, passa para revisão
  └─ Passou tudo? → SIM → Envia ao atendente
```

A separação entre probabilístico e determinístico é intencional: o prompt define o comportamento desejado, o harness garante que o comportamento mínimo seja sempre respeitado independente do modelo.

---

## 6. Processo de Mudança de Prompt

```
1. Desenvolvedor identifica comportamento inadequado em produção ou testes.
2. Abre issue no GitHub com: comportamento observado, comportamento esperado, 
   exemplo de query que falhou.
3. Propõe mudança no prompt via Pull Request.
4. PR deve incluir:
   - Mudança no arquivo de prompt versionado.
   - Atualização do CHANGELOG.md com justificativa.
   - Adição de ao menos 1 caso de teste no prompt-test-suite.json cobrindo 
     o comportamento corrigido.
5. Tech Lead revisa e aprova.
6. Deploy em ambiente de staging com execução da suite completa de testes.
7. Se todos os testes passam, deploy em produção.
8. Monitorar por 48h após deploy para detectar regressões.
```

---

*Versão 1.0 — Junho/2025 | Tech Lead DB1*
