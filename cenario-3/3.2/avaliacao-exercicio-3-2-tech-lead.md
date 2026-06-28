# Avaliação do Exercício 3.2 — Tech Lead
**Programa:** Trilha de Certificação AI First — DGS / DB1 Global Software  
**Cenário:** 3 — Fase de Governança e Validação  
**Exercício:** 3.2 — Revisão Crítica da Arquitetura Gerada com IA  
**Papel:** Tech Lead  
**Data de avaliação:** 28/06/2025  

---

## Resumo

Entregável de alta qualidade que demonstra domínio real do tópico de Revisão Crítica. O participante cumpriu rigorosamente a estrutura "humano primeiro, IA depois", produziu análise própria substantiva antes do co-review, e integrou o output do Claude de forma crítica e honesta — inclusive reconhecendo riscos que não havia identificado inicialmente. A conexão com artefatos dos cenários anteriores (ADR-0002, ADR-0003) é explícita e bem fundamentada. A priorização final é pragmática e demonstra maturidade de julgamento.

---

## Scores por Dimensão

| Dimensão | Score | Justificativa |
|----------|-------|---------------|
| D1 — Domínio Conceitual | 3 | Demonstra compreensão precisa de conceitos como *lost in the middle* aplicado ao AGENTS.md no contexto do Copilot, *context rot* em system prompts iterados sem documentação, e a distinção entre cobertura de código e qualidade de assertions. Os conceitos não são genéricos — são aplicados ao projeto específico da NovaTech com exemplos concretos (ex: a contradição hipotética entre instruções de versão do documento no system prompt). |
| D2 — Uso de Ferramentas | 3 | O co-review com Claude é genuíno: há diferenciação clara entre o que veio da análise humana e o que o Claude complementou, com tabela de comparação honesta. O participante não apenas aceitou o output — avaliou onde o Claude adicionou valor real (pipeline e system prompt) versus onde a intuição humana já havia chegado (AGENTS.md e skills). A ausência de evidência do Copilot não se aplica a este exercício (3.2 não exige Copilot). |
| D3 — Qualidade do Entregável | 3 | Documento completo, com as 3 etapas exigidas (avaliação humana, co-review, priorização). A priorização tem critérios explícitos (impacto × esforço), estimativas de esforço por artefato, e distingue entre "atacar" e "residual controlado" com condições claras para cada categoria. Acionável: um engenheiro lendo o documento sabe exatamente o que fazer na próxima segunda-feira. |
| D4 — Pensamento Crítico | 3 | A análise humana (Etapa 1) é substantiva e anterior ao Claude — cobre todos os 4 artefatos com riscos não-triviais. O participante identifica o risco do pipeline (60-70% Copilot) como "o mais silencioso" mesmo sem mencionar o exercício orientando isso. A comparação com o Claude é honesta: reconhece explicitamente que o pipeline foi um ponto cego na análise humana inicial. A seção de priorização não é wishlist — aceita risco residual com justificativa. |
| D5 — Aplicabilidade ao Projeto | 3 | Conexão explícita com ADR-0002 (context budget aplicado ao AGENTS.md) e ADR-0003 (system prompt como implementação das decisões de tratamento de documentos contraditórios). Referencia o AGENTS.md não como conceito abstrato, mas como artefato concreto do projeto com problema específico (15 páginas após 4 refinamentos). O contexto da NovaTech está presente em exemplos ("multiplicadores regionais", "versão mais recente do documento"). |

**Score do exercício: 3.0**

---

## Verificação de Armadilhas

Conforme a skill de avaliação do papel (Tech Lead — Exercício 3.2):

| Armadilha | Identificada? | Evidência |
|-----------|---------------|-----------|
| Skills sem refinamento = risco de outputs inconsistentes em produção | ✅ Sim | "As 2 skills sem refinamento são um problema — foram aceitas sem validação com casos reais. Só a Foundation tem evidência de funcionamento." Complementado pelo Claude com o conceito de risco assimétrico e formato concreto de testes (5 casos por skill). |
| Prompt sem changelog = impossibilidade de rollback informado | ✅ Sim | "6 iterações sem documentação das mudanças. Sem histórico, não há como fazer rollback consciente se o comportamento regredir após o go-live." O Claude complementa com a analogia ao repositório sem histórico de commits e a conexão com a ADR-0003. |
| Análise própria ANTES do Claude | ✅ Sim | Etapa 1 cobre todos os 4 artefatos com análise específica. A Etapa 2 começa com "complementação" — deixando claro que o Claude acrescenta, não substitui. |
| Priorização pragmática (foca no que importa nas 2 semanas) | ✅ Sim | A Etapa 3 usa critério explícito (impacto × esforço), prioriza 2 artefatos para atacar e aceita 2 como residual com controles. Pipeline (risco mais silencioso) recebe prioridade máxima. |
| Comparação com Claude honesta (reconhece o que o Claude adicionou) | ✅ Sim | "Onde o humano foi mais preciso" vs "Onde o Claude complementou com mais valor" — com exemplos concretos em cada célula. O participante não afirma "já sabia tudo". |

**Todas as armadilhas identificadas.**

---

## Pontos Fortes

1. **Estrutura "humano primeiro" executada com rigor:** A Etapa 1 é substantiva o suficiente para ser entregável por si só. Não é uma análise superficial feita para cumprir protocolo antes de usar a IA — é uma revisão real que teria valor independente do co-review.

2. **Integração honesta do co-review:** A tabela de comparação é um dos melhores exemplos possíveis de como usar IA como par de revisão sem abdicar do julgamento. O participante credita o Claude pelo que o Claude realmente adicionou (pipeline como ponto cego) sem inflar a contribuição da IA.

3. **Priorização com trade-off explícito:** A distinção entre "atacar" e "residual controlado com gate" é madura. Especialmente o ponto das skills: "aceitar como residual não significa ignorar — significa controlar a exposição" com gate de go-live definido. Isso é pensamento de engenharia de produção, não de exercício acadêmico.

---

## Pontos de Melhoria

1. **Pipeline: ausência de menção ao comportamento atual em falha de dependência:** O participante identifica a ausência de tratamento defensivo e recomenda implementar timeout e fallback, mas não especifica qual deveria ser o comportamento de fallback — retornar erro genérico para o atendente? Mensagem de "assistente indisponível"? Redirecionar para o supervisor? Para um artefato de revisão crítica com foco em go-live, essa especificação importa.

   *Sugestão:* Acrescentar à ação do pipeline: "Definir e documentar o comportamento esperado do endpoint de query em caso de falha do Azure AI Search ou Azure OpenAI (ex: retornar HTTP 503 com mensagem 'assistente temporariamente indisponível — escale para supervisor')."

2. **AGENTS.md: meta de "5-7 páginas" sem critério para decidir o que cortar:** A recomendação de reduzir para 5-7 páginas é razoável, mas o critério para decidir o que permanece e o que sai é vago ("regras que não cabem provavelmente são detalhes de implementação"). Para um Tech Lead conduzindo a auditoria, seria útil um critério mais operacional.

   *Sugestão:* Propor critério de permanência explícito — por exemplo: "cada regra no AGENTS.md deve ser verificável pelo Copilot a cada geração de código; regras que dependem de contexto de runtime (ex: 'use a versão mais recente do documento') pertencem ao system prompt, não ao AGENTS.md."

3. **System prompt: changelog retroativo sem método:** A recomendação de "criar changelog retroativo mínimo das 6 versões" é correta, mas a viabilidade depende de como as versões foram salvas. Se não houver registro das versões anteriores, o changelog retroativo é impossível — e o participante deveria ter mencionado esse risco.

   *Sugestão:* Adicionar: "Se as versões anteriores não estiverem salvas, o changelog retroativo é inviável — nesse caso, o estado atual é o novo baseline, e o processo de versionamento começa agora. Não tentar reconstruir o histórico por memória."

---

## Classificação

**✅ Aprovado com distinção** (Score: 3.0 / 3.0)

---

## Tópicos da Trilha para Reforço

Nenhum tópico prioritário para reforço — o entregável demonstra domínio do tema. Para aprofundamento opcional:

- **Harness Engineering:** O exercício 3.2 não avalia harness diretamente, mas a menção ao sistema prompt como implementação da ADR-0003 abre a pergunta de quais guardrails são enforçados probabilisticamente (no prompt) versus deterministicamente (no harness). Explorar essa distinção no exercício 3.1 se ainda não foi feito.
- **Revisão Crítica de Outputs de IA:** O nível demonstrado já está acima do esperado para o cenário 3. A evolução natural é aplicar o mesmo framework de revisão a artefatos de outros papéis (ex: revisar especificações do Product Specialist ou planos de teste do QA com o mesmo rigor).

---

*Avaliação gerada com base nas skills `avaliacao-foundation.md` e `avaliacao-tech-lead.md` (Cenário 3) e no enunciado `exercicio-fase-1-entendimento.md` (seção Tech Lead, Exercício 1.3 como referência de contexto acumulado). Exercício avaliado: `exercicio-3-2-revisao-critica.md`.*
