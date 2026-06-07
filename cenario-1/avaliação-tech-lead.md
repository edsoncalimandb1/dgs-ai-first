# Avaliação — Cenário 1 | Tech Lead | Trilha AI First DGS

> **Programa:** Trilha de Certificação AI First — DGS / DB1 Global Software  
> **Papel:** Tech Lead  
> **Cenário:** 1 — Fase de Entendimento e Contexto  
> **Exercícios avaliados:** 1.1 (ADRs), 1.2 (Prompt Engineering), 1.3 (Revisão Crítica de RAG)  
> **Score geral:** 3.0 — Aprovado com distinção

---

## Contexto do Projeto (NovaTech)

A NovaTech é uma empresa de médio porte do setor de logística com 1.200 funcionários. Sua operação depende de documentação interna espalhada em três fontes: SharePoint (~800 documentos PDF/DOCX), wiki Confluence (~400 páginas) e pasta de rede (~50 planilhas XLSX).

O problema: o time de atendimento (45 pessoas) gasta em média 12 minutos por chamado buscando informações para responder dúvidas de clientes. A DB1 foi contratada para construir um assistente de IA integrado ao ambiente Microsoft (Teams + SharePoint) que responda em linguagem natural com base na documentação oficial.

---

## Avaliação do Exercício 1.1 — Decisões Arquiteturais Documentadas como ADRs

### Resumo

O entregável é excepcionalmente completo e demonstra domínio técnico real do conteúdo da trilha. As quatro ADRs são independentes, autossuficientes e fundamentadas em trade-offs explícitos com dados concretos do projeto NovaTech. O processo de devil's advocate foi executado com rigor real — não foi cosmético — e gerou revisões verificáveis nas decisões. É o nível de entregável que outro membro do time poderia usar diretamente em um kickoff.

### Scores por Dimensão

| Dimensão                       | Score | Justificativa                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------------------------ | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 — Domínio Conceitual        | 3     | Demonstra compreensão profunda e específica ao domínio. ADR-0002 trata context rot, lost in the middle, perguntas multi-domínio e context overflow com precisão técnica — não são menções superficiais. ADR-0003 identifica corretamente que "documentos contraditórios é um problema de dados, não de modelo" e propõe solução em três camadas. ADR-0001 corrige explicitamente a falácia de que um modelo "não alucina", reforçando que a mitigação é arquitetural.                                     |
| D2 — Uso de Ferramentas        | 3     | Todas as 4 ADRs passaram pelo processo de devil's advocate com o Claude. O registro consolida os prompts enviados, os contra-argumentos recebidos, a classificação de cada argumento (incorporado vs. respondido e mantido) e a análise de impacto. Há diferença verificável entre versão antes e depois do devil's advocate em ADR-0001 (lock-in), ADR-0002 (cap de histórico e detecção multi-domínio), ADR-0003 (risco de governança adicionado). Não é iteração cosmética.                            |
| D3 — Qualidade do Entregável   | 3     | Cada ADR segue o formato exato solicitado, com as seções Contexto, Decisão, Consequências e Alternativas consideradas. A ADR-0002 inclui uma tabela de orçamento de contexto com tokens por componente, justificativa de posicionamento contra lost in the middle, e política de janela deslizante com exceção para metadados estruturados. A ADR-0003 inclui tabela comparativa de todos os parâmetros contraditórios entre PROC-042 v1 e v2. Nível utilizável diretamente como documentação de projeto. |
| D4 — Pensamento Crítico        | 3     | A análise dos contra-argumentos do devil's advocate é honesta e diferenciada: alguns foram incorporados, outros respondidos e descartados com justificativa explícita. O participante reconhece a limitação do Claude como devil's advocate ("tende a ser menos crítico em relação a estimativas de custo e prazo") — demonstra uso como ferramenta, não como autoridade. O registro de devil's advocate nomeia explicitamente qual argumento gerou qual mudança na ADR, tornando o raciocínio auditável. |
| D5 — Aplicabilidade ao Projeto | 3     | As decisões referenciam consistentemente os dados do projeto: 320 chamados/dia × 60% = 192 queries, cálculo de custo mensal (~$193/mês), as licenças E3 da NovaTech, o prazo de 3 meses, as contradições específicas PROC-042 v1 vs v2, a pergunta exemplo "posso devolver carga perigosa com frete especial de uma empresa Gold?" para ilustrar perguntas multi-domínio. Não é uma ADR genérica adaptada — foi construída para este projeto.                                                             |

**Score do exercício: 3.0**

### Verificação de Armadilhas

Este exercício não possui armadilhas intencionais no formato de respostas incorretas para identificar (as armadilhas são do domínio NovaTech, relevantes para outros exercícios como QA 1.2). O exercício avalia qualidade de raciocínio arquitetural. Não aplicável.

### Pontos Fortes

**1. ADR-0002 trata engenharia de contexto com precisão de produção.** A tabela de orçamento (1.500 + 200 + 6.000 + 3.000 + 500 + 4.800 = 16.000 tokens), a justificativa de posicionamento dos chunks logo após o system prompt, a distinção entre metadados estruturados e histórico livre, e a estratégia conservadora de detecção multi-domínio mostram que o conceito foi internalizado, não decorado.

**2. ADR-0003 resolve o problema real de dados, não o problema percebido.** A proposta em três camadas (metadados de ingestão + filtro de retrieval + instrução no prompt) reconhece que depender apenas do prompt para um problema crítico de precisão financeira é insuficiente. O registro do devil's advocate mostra que a camada de retrieval foi fortalecida exatamente porque o Claude apontou a fragilidade do prompt sozinho.

**3. O registro de devil's advocate é um artefato de raciocínio, não burocracia.** A tabela de síntese final ("o que mudou em cada ADR") e o aprendizado sobre os limites do Claude como devil's advocate demonstram que o processo foi usado para melhorar as decisões, não para cumprir requisito formal.

### Pontos de Melhoria

**1. ADR-0004 não passou por devil's advocate formal.** O próprio participante reconhece isso. Para uma decisão de build vs. buy com impacto financeiro e operacional relevante, a ausência do processo é um gap. Contra-argumentos como "o Azure Document Intelligence pode não extrair corretamente tabelas de PDFs escaneados gerados por software legado" ou "o lock-in do Azure AI Search pode ser mais custoso de reverter do que construir do zero" não foram testados.

**2. A estratégia de decomposição de perguntas multi-domínio em sub-perguntas (ADR-0002, ponto 5) não foi validada empiricamente.** A proposta de usar uma "LLM call prévia, barata, com modelo menor" adiciona latência e custo que não foram estimados. Um nível de detalhe adicional (qual modelo menor, qual custo estimado, qual latência adicional aceitável) fortaleceria a decisão.

**3. A mitigação de "abstrair atrás de interface" aparece em ADR-0001 e ADR-0004 sem exemplo concreto.** A proposta é correta, mas o entregável se beneficiaria de uma assinatura de método ou referência a um padrão de design, tornando a mitigação mais acionável para o desenvolvedor que vai implementar.

### Classificação

**✅ Aprovado com distinção (3.0)**

### Tópicos da Trilha para Reforço

Não aplicável — score 3.0. O participante demonstra domínio completo dos tópicos avaliados neste exercício.

---

## Avaliação do Exercício 1.2 — Prompt Engineering como Artefato de Arquitetura

### Resumo

O entregável entrega uma estratégia de prompt engineering como artefato de arquitetura de alta qualidade, com convenções de versionamento concretas, anatomia de contexto com orçamento por componente, separação clara entre enforcement probabilístico e determinístico, e um script de teste funcional. O diagrama do harness e o processo de mudança de prompt são os pontos mais fortes — mostram maturidade de engenharia que vai além do exercício imediato.

### Scores por Dimensão

| Dimensão                       | Score | Justificativa                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ------------------------------ | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 — Domínio Conceitual        | 3     | A seção de enforcement probabilístico vs. determinístico demonstra compreensão precisa do conceito de harness. A anatomia de contexto é exatamente o que a skill pede: não "o prompt" — é a composição de partes estáticas e dinâmicas com orçamento por componente e justificativa do posicionamento (lost in the middle explicado na seção "Por que essa ordem importa").                                                                                           |
| D2 — Uso de Ferramentas        | 3     | O script `prompt_test_runner.py` está completo, funcional e contém 6 casos de teste reais do domínio NovaTech — incluindo os cenários críticos (carga perigosa, tier Platinum, documentos contraditórios, pergunta sem cobertura). Os comentários inline indicam explicitamente quais partes foram sugeridas pelo Copilot e quais foram escritas manualmente, tornando a evidência de uso rastreável.                                                                 |
| D3 — Qualidade do Entregável   | 3     | O documento de estratégia cobre todas as dimensões pedidas: estrutura de repositório com convenção de nomenclatura semântica (MAJOR.MINOR.PATCH), política de quem pode alterar o prompt, o system prompt v1.0.0 completo com guardrails numerados (R1–R5), formatos de resposta para cada cenário, e o processo de mudança em 8 passos. É um artefato que um desenvolvedor novo no projeto poderia seguir sem pedir esclarecimentos.                                 |
| D4 — Pensamento Crítico        | 3     | A tabela de enforcement probabilístico vs. determinístico não é uma lista mecânica — o participante justifica por que cada guardrail pertence a cada categoria. Por exemplo, "não inventar dados" está marcado como probabilístico com risco "Alto" e nota de que requer reforço determinístico, demonstrando que a limitação do modelo foi internalizada. O diagrama de fluxo do harness mostra que o participante pensou no sistema completo, não apenas no prompt. |
| D5 — Aplicabilidade ao Projeto | 3     | O system prompt usa guardrails específicos ao domínio NovaTech (R4 trata explicitamente a regra de vigência de 01/12/2023 das PROC-042). O script de testes usa as perguntas e chunks do Anexo B do projeto. A tabela de enforcement lista "menciona Platinum" e "inverte regra crítica sobre carga perigosa" — referências diretas às armadilhas reais da documentação NovaTech.                                                                                     |

**Score do exercício: 3.0**

### Verificação de Armadilhas

Não há armadilhas no formato de exercício 1.2 — mas o script de testes do participante cobre explicitamente as armadilhas do domínio: TEST-002 (carga perigosa NÃO pode devolver), TEST-004 (tier Platinum não existe), TEST-005 (multiplicadores contraditórios v1 vs v2). O participante demonstra compreensão das armadilhas como casos de teste prioritários.

### Pontos Fortes

**1. O script de testes é funcional e demonstra o conceito com clareza de produção.** O `CHECK_REGISTRY` como mapa de funções, a separação entre `TestCase` (o que testar) e `CheckResult` (o resultado), e o `PromptTestRunner.build_context()` que injeta chunks no placeholder do system prompt — são escolhas de design deliberadas, não código gerado e aceito cegamente.

**2. O sistema de versionamento semântico (MAJOR.MINOR.PATCH) aplicado a prompts é preciso e acionável.** A definição do que constitui cada nível (MAJOR = mudança de guardrails fundamentais; PATCH = correção de comportamento específico) resolve um problema real de governança de prompt que a maioria dos times não trata formalmente.

**3. O diagrama de fluxo do harness fecha o ciclo completo** do sistema: desde a pergunta do atendente até a resposta verificada, com os pontos de intervenção determinística nomeados. Esse artefato, combinado com a ADR-0002, forma um par coeso de decisão arquitetural + implementação.

### Pontos de Melhoria

**1. O script não inclui casos de teste para o cenário de contradição com metadados de versão explícitos.** O TEST-005 testa a contradição corretamente, mas os chunks não incluem os campos `emission_date` e `version` no formato JSON definido na ADR-0003. Um caso de teste que valide que o modelo usa o campo `emission_date` para escolher a versão correta fortaleceria a cobertura.

**2. O processo de mudança (seção 6) não define o que acontece quando Product Specialist e Tech Lead discordam.** Para um documento que afeta o comportamento visível ao atendente, um critério de desempate ou escalação tornaria o processo mais robusto.

### Classificação

**✅ Aprovado com distinção (3.0)**

### Tópicos da Trilha para Reforço

Não aplicável — score 3.0.

---

## Avaliação do Exercício 1.3 — Revisão Crítica de Proposta de RAG

### Resumo

O entregável executa o exercício de revisão crítica com excelente rigor metodológico: a análise humana é substantiva e anterior ao uso do Claude, a comparação entre as duas revisões é honesta — incluindo reconhecimento explícito do que cada lado viu e não viu — e a proposta reescrita resolve os problemas identificados sem overengineering. A análise crítica da revisão do Claude ("identificou C1-C4, mas foi menos enfático no risco operacional mais crítico") é o ponto mais valioso do entregável.

### Scores por Dimensão

| Dimensão                       | Score | Justificativa                                                                                                                                                                                                                                                                                                                                                                                               |
| ------------------------------ | ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 — Domínio Conceitual        | 3     | Os 5 problemas da revisão humana demonstram compreensão técnica real de RAG: chunking sem overlap em fronteiras semânticas, insuficiência de 3 chunks para perguntas multi-domínio, risco operacional de ingestão manual, contaminação de confiabilidade por índice único misturando FAQ informal com documentos normativos, e documentos contraditórios sem metadados. Nenhum desses problemas é genérico. |
| D2 — Uso de Ferramentas        | 3     | A evidência de uso do Claude é clara: o prompt enviado está transcrito, os contra-argumentos recebidos estão sumarizados, e a tabela de comparação (problemas encontrados pelo TL vs. pelo Claude) é explícita sobre quem encontrou o quê. A análise é honesta — não apaga os 4 problemas que o Claude encontrou e o participante não viu.                                                                  |
| D3 — Qualidade do Entregável   | 3     | A proposta reescrita é completa e específica: stack revisada (text-embedding-3-large em vez de ada-002), estratégia de retrieval em três fases (recall → re-ranking → seleção), campos de metadados obrigatórios definidos, SLA de indexação (1h vs. requisito de 24h), e detecção de queries ambíguas. Resolve todos os problemas identificados sem adicionar complexidade desnecessária.                  |
| D4 — Pensamento Crítico        | 3     | A revisão humana tem 5 problemas detalhados com "por quê é um problema" e "proposta de correção" para cada um — isso foi claramente escrito antes de consultar o Claude, não é uma lista vaga depois expandida pela IA. A tabela comparativa e a "análise honesta" ao final mostram autoconsciência sobre os limites da própria revisão.                                                                    |
| D5 — Aplicabilidade ao Projeto | 3     | Os problemas identificados referenciam especificamente a documentação NovaTech: a pergunta "posso devolver carga perigosa com frete especial de uma empresa Gold?" como exemplo de por que 3 chunks é insuficiente, o FAQ informal vs. POL-001 como caso concreto de contaminação de confiabilidade por índice único, e a PROC-042 v1 vs v2 como caso concreto de documentos contraditórios sem metadados.  |

**Score do exercício: 3.0**

### Verificação de Armadilhas

A proposta original contém 5 problemas intencionais que o participante deveria identificar:

| Armadilha                                                                  | Identificada?                                                         |
| -------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Chunking fixo 512 tokens sem overlap perde contexto em fronteiras          | ✅ Problema 1, com explicação de por que fronteiras de seção importam |
| 3 chunks insuficiente para perguntas multi-domínio                         | ✅ Problema 2, com exemplo específico de 3 domínios simultâneos       |
| Ingestão manual "quando alguém lembra" viola requisito de 24h              | ✅ Problema 3, identificado como "risco operacional mais crítico"     |
| Índice único mistura confiabilidade de fontes (normativo vs. FAQ informal) | ✅ Problema 4, com solução de `reliability_tier`                      |
| Sem estratégia para documentos contraditórios                              | ✅ Problema 5 (bônus)                                                 |

Todas as armadilhas identificadas. Os 4 problemas adicionais do Claude (ada-002 genérico, sem re-ranking, sem métricas, queries ambíguas) foram incorporados na proposta reescrita.

### Pontos Fortes

**1. A identificação do índice único como problema de confiabilidade diferenciada é o insight mais original do entregável.** A proposta de `reliability_tier` (1=normativo, 2=procedimento, 3=informal) com filtro de boost no retrieval é uma solução elegante que não estava nos materiais do exercício — foi derivada da análise do domínio NovaTech.

**2. A análise honesta da comparação TL vs. Claude é metodologicamente exemplar.** O participante reconhece que o Claude foi mais abrangente nos problemas técnicos de ML (embedding, re-ranking, métricas) enquanto a revisão humana foi mais profunda nos problemas operacionais e de dados. Essa autoconsciência sobre os pontos cegos de cada abordagem é exatamente o que o exercício testa.

**3. A proposta reescrita tem SLA de indexação concreto (1h).** O requisito do PS era 24h — a proposta entrega 1h com change tracking nativo do Azure AI Search. Mostrar que a solução técnica supera o requisito com margem é uma contribuição adicional ao projeto.

### Pontos de Melhoria

**1. O re-ranking (C2 do Claude) foi incluído na proposta reescrita, mas sem estimativa de impacto em latência.** A fase de re-ranking com cross-encoder adiciona uma chamada de modelo extra. Uma nota sobre latência esperada (tipicamente 100–300ms adicionais) ou sobre usar um re-ranker leve fortaleceria a proposta.

**2. A detecção de queries ambíguas (C4 do Claude) foi incluída como "solicita clarificação", mas sem definir o mecanismo de UX.** Em um bot do Teams, pedir clarificação pode frustrar atendentes em situações de alta pressão. Uma proposta de como apresentar as opções (ex: botões rápidos) tornaria a solução mais concreta.

### Classificação

**✅ Aprovado com distinção (3.0)**

### Tópicos da Trilha para Reforço

Não aplicável — score 3.0.

---

## Resultado Consolidado

| Exercício                    | Score   | Classificação              |
| ---------------------------- | ------- | -------------------------- |
| 1.1 — ADRs                   | 3.0     | Aprovado com distinção     |
| 1.2 — Prompt Engineering     | 3.0     | Aprovado com distinção     |
| 1.3 — Revisão Crítica de RAG | 3.0     | Aprovado com distinção     |
| **Cenário 1 — Geral**        | **3.0** | **Aprovado com distinção** |

---

_Avaliação gerada em 07/06/2026 | Trilha AI First DGS — DB1 Global Software_
