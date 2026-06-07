# ADR-0002: Estratégia de Gerenciamento de Contexto

## Status: Aceito

## Contexto

Em um sistema RAG, o LLM não "sabe" o conteúdo da documentação — ele recebe um contexto montado a cada query e gera a resposta com base nesse contexto. O contexto é um recurso limitado e escasso: a janela de contexto do GPT-4o é de 128K tokens, mas usar mais contexto não é neutro — aumenta custo, aumenta latência, e degrada qualidade.

Os problemas específicos que esta ADR endereça:

**Context rot:** Em uma conversa longa no Teams (ex: atendente faz 8 perguntas na mesma sessão), o histórico acumulado consome tokens e o modelo começa a "esquecer" ou confundir instruções do system prompt com informação do histórico. Na prática, a resposta da 7ª pergunta pode ignorar guardrails estabelecidos no início da conversa.

**Lost in the middle:** Estudos de comportamento de LLMs mostram que informação posicionada no meio de um contexto longo é menos processada do que informação no início ou no fim. Se os chunks mais relevantes forem inseridos no meio do contexto, a qualidade da resposta cai mesmo com a informação presente.

**Perguntas multi-domínio:** Um atendente pode perguntar "qual o prazo de devolução para carga perigosa com frete especial?" — uma pergunta que cruza POL-001 (devolução), PROC-042-v2 (frete especial) e potencialmente SLA-2024. O pipeline precisa recuperar chunks de múltiplos domínios sem que o contexto fique sobrecarregado.

**Context overflow:** Se a query + chunks + histórico ultrapassarem o orçamento definido, o modelo trunca o contexto silenciosamente, resultando em respostas parciais sem aviso.

**Forças em tensão:**
- Mais chunks = mais cobertura vs. mais tokens = mais custo e risco de lost in the middle
- Histórico completo = melhor continuidade de conversa vs. histórico longo = context rot
- Contexto rico = respostas mais completas vs. contexto grande = latência maior

---

## Decisão

### 1. Orçamento de contexto total: 16.000 tokens por query

Distribuição:

| Parte | Tipo | Tokens reservados | Justificativa |
|---|---|---|---|
| System prompt | Estático | 1.500 | Identidade, guardrails, formato de resposta |
| Metadados do cliente | Dinâmico | 200 | Tier (Gold/Silver/Standard), número do contrato |
| Chunks recuperados | Dinâmico | 6.000 | Espaço para 8–10 chunks de ~600 tokens cada |
| Histórico de conversa | Dinâmico, crescente | 3.000 | Cap fixo — ver política de janela deslizante abaixo |
| Pergunta atual | Dinâmico | 500 | Pergunta do atendente + contexto imediato |
| **Buffer de segurança** | — | 4.800 | Evita overflow; acomoda respostas longas |
| **Total** | — | **16.000** | Bem dentro dos 128K do GPT-4o |

*Usar 16K de 128K disponíveis é intencional: manter o contexto enxuto melhora qualidade, reduz custo e reduz latência.*

### 2. Número de chunks recuperados: 8 chunks padrão, até 12 para perguntas multi-domínio

- **Perguntas simples** (detectadas por classifier ou heurística de palavras-chave): recuperar 5 chunks, priorizar score de similaridade > 0.75.
- **Perguntas padrão:** recuperar 8 chunks.
- **Perguntas multi-domínio** (contêm termos de múltiplos temas): recuperar até 12 chunks, aplicando MMR (Maximal Marginal Relevance) para garantir diversidade de domínios sem repetição.

Chunks com score < 0.60 são descartados mesmo se dentro da cota — o modelo não deve receber contexto de baixa relevância.

### 3. Posicionamento dos chunks no contexto (contra lost in the middle)

Ordem de montagem do contexto:
```
[SYSTEM PROMPT]
[METADADOS DO CLIENTE]
[CHUNKS — ordenados do MAIS relevante para o MENOS relevante]
[HISTÓRICO DE CONVERSA — truncado pela janela deslizante]
[PERGUNTA ATUAL]
```

Os chunks mais relevantes ficam logo após o system prompt (início do contexto), não no meio. A pergunta atual fica no fim — posição de maior atenção do modelo.

### 4. Política de janela deslizante para histórico (combate context rot)

- O histórico é truncado para as últimas **4 trocas** (4 perguntas + 4 respostas).
- Quando a sessão ultrapassa 4 trocas, as mais antigas são removidas do contexto.
- **Exceção:** Se uma troca mais antiga contiver informação de cliente (ex: "meu cliente é Gold") ela é preservada como metadado estruturado no bloco de metadados, não no histórico livre.
- O atendente é notificado via interface quando o histórico foi truncado: *"[Contexto da sessão foi parcialmente reiniciado para manter qualidade das respostas]"*.

### 5. Estratégia para perguntas multi-domínio

Quando a pergunta é detectada como multi-domínio:
1. A pergunta é decomposta em sub-perguntas (via LLM call prévia, barata, com modelo menor).
2. Cada sub-pergunta gera um conjunto de chunks.
3. Os conjuntos são mesclados com deduplicação e MMR.
4. O contexto é montado com seções explícitas por domínio (`## Sobre devolução:`, `## Sobre frete especial:`), ajudando o modelo a rastrear a origem de cada informação.

---

## Consequências

**Positivas:**
- Custo controlado: 16K tokens × ~$0.005/1K tokens input ≈ $0.08/query. Com 4.200 queries/mês: ~$336/mês — dentro do orçamento.
- Qualidade preservada: contexto enxuto e bem posicionado reduz lost in the middle.
- Context rot mitigado estruturalmente, não dependente de comportamento do modelo.

**Negativas / Riscos:**
- Janela deslizante pode frustrar atendentes que retomam um ponto de 5 mensagens atrás.
- Detecção de perguntas multi-domínio por heurística pode ter falsos negativos (pergunta classificada como simples quando é complexa).
- A decomposição de sub-perguntas adiciona latência (~300–500ms por call adicional).

**Mitigações:**
- Logar queries onde o histórico foi truncado para análise de frequência e ajuste do cap se necessário.
- Monitorar taxa de falsos negativos na detecção multi-domínio e refinar o classifier com exemplos reais após o piloto.

---

## Alternativas Consideradas

| Alternativa | Motivo de descarte |
|---|---|
| **Usar toda a janela de 128K sempre** | Custo 8× maior, latência 3–5× maior, qualidade potencialmente inferior (lost in the middle em escala). Não há benefício demonstrado para o domínio de uso. |
| **Recuperar sempre 3 chunks (proposta original do Dev)** | Insuficiente para perguntas complexas ou multi-domínio. Uma pergunta sobre devolução de carga perigosa com frete especial precisa de chunks da POL-001, PROC-042-v2, e potencialmente SLA-2024 — 3 chunks não cobrem isso. |
| **Sem janela deslizante (histórico completo)** | Context rot confirmado empiricamente em conversas com mais de 6 trocas. A qualidade da resposta na 8ª pergunta é significativamente inferior à da 1ª mesmo com o mesmo prompt, porque o histórico compete por atenção com o system prompt. |
| **Histórico resumido por LLM** | Abordagem válida para melhorar continuidade, mas adiciona complexidade e custo de inferência. Pode ser adotada como evolução após validação do piloto. |

---

## Devil's Advocate — Argumentos Contra (gerados com Claude)

**Argumento 1:** "Truncar o histórico em 4 trocas vai frustrar os atendentes. Em um atendimento real, o contexto de 10 mensagens atrás pode ser relevante."

*Resposta:* O problema real não é o cap de 4, mas a ausência de persistência estruturada. A mitigação correta é persistir informações-chave do cliente (tier, número do contrato, tipo de carga) como metadados estruturados, não no histórico livre. Isso preserva o que importa sem contaminar o contexto com texto não estruturado. O cap de 4 é ajustável com base em dados reais do piloto.

**Argumento 2:** "Detectar perguntas multi-domínio por heurística é frágil. O atendente pode perguntar algo complexo usando palavras simples."

*Resposta:* Argumento válido e incorporado. A estratégia foi revisada: além da heurística de palavras-chave, o sistema tentará recuperar 8 chunks por padrão (não 5), e só reduzirá para 5 quando a query for trivialmente simples (ex: "qual o SLA do Gold?"). A heurística é conservadora — erra para mais chunks, não para menos.

---

*Data da decisão: Junho/2025 | Autor: Tech Lead DB1 | Revisores: DM, Dev*
