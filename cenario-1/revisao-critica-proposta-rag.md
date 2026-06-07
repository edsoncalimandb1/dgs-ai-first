# Exercício 1.3 — Revisão Crítica da Proposta de RAG

**Autor:** Tech Lead DB1  
**Data:** Junho/2025

---

## Proposta original recebida

> "Vamos usar Azure AI Search com embeddings do ada-002. Todos os documentos serão indexados num único índice. Chunking fixo de 512 tokens sem overlap. O LLM recebe os 3 chunks mais similares. Usaremos GPT-4o para geração. O pipeline de ingestão roda manualmente quando alguém lembra de atualizar."

---

## Parte 1 — Revisão do Tech Lead (feita antes de consultar o Claude)

### Problema 1: Chunking fixo de 512 tokens sem overlap

**Por quê é um problema:**  
Chunking fixo por contagem de tokens ignora a estrutura semântica do documento. Em documentos da NovaTech, uma seção sobre "Procedimento de devolução" pode ter 3 sub-itens: se o chunk cortar no meio do item 2, a informação do item 3 vai para o próximo chunk sem o contexto dos itens anteriores. O retriever pode retornar o chunk do item 3 sem o item 1 e 2, gerando resposta incompleta.

A ausência de overlap agrava o problema: informação em fronteiras de chunk é perdida nos dois lados. Uma frase que começa no chunk N e termina no chunk N+1 nunca aparece completa em nenhum chunk.

**Proposta de correção:**  
Chunking por seção lógica (header H2/H3 como delimitador), com overlap de 10% (aproximadamente 50 tokens do chunk anterior são repetidos no início do próximo). Para seções muito longas (>800 tokens), dividir com overlap maior.

---

### Problema 2: Apenas 3 chunks por query

**Por quê é um problema:**  
Perguntas sobre o domínio de logística frequentemente cruzam múltiplos documentos. A pergunta "posso devolver carga perigosa com frete especial de uma empresa Gold?" exige chunks da POL-001 (devolução + exceção carga perigosa), PROC-042-v2 (frete especial) e SLA-2024 (tier Gold). São 3 domínios diferentes — 3 chunks pode cobrir apenas um deles, gerando resposta parcial ou incorreta.

Além disso, se o pipeline retornar 2 chunks de versões diferentes de um mesmo documento (v1 e v2 do PROC-042), esses 2 chunks já "consomem" a cota de 3, deixando apenas 1 chunk para o resto da pergunta.

**Proposta de correção:**  
Recuperar 8 chunks por padrão, até 12 para perguntas detectadas como multi-domínio. Ver ADR-0002 para estratégia completa.

---

### Problema 3: Ingestão manual "quando alguém lembra"

**Por quê é um problema:**  
Este é o risco operacional mais crítico da proposta. Se a NovaTech publicar uma nova versão do PROC-042 e o pipeline não for atualizado, os atendentes continuarão recebendo respostas baseadas na versão antiga. Isso é exatamente o tipo de problema que o assistente deveria resolver — mas com ingestão manual, o assistente se torna uma nova fonte de desatualização.

O requisito do Product Specialist é explícito: "atualização máxima de 24h após publicação de novo documento". Ingestão manual não atende esse requisito.

**Proposta de correção:**  
Azure AI Search tem indexer nativo com conector para SharePoint Online e change tracking automático. Quando um documento é atualizado no SharePoint, o indexer detecta e re-indexa em até 5 minutos. Para Confluence e planilhas, implementar webhook ou scheduled job (a cada 6h) que detecta mudanças por hash do conteúdo.

---

### Problema 4: Índice único para todos os documentos

**Por quê é um problema:**  
Um único índice mistura documentos de naturezas diferentes: políticas normativas (POL-001), procedimentos operacionais (PROC-042), tabelas de SLA, FAQ informal, planilhas. O embedding de "cargas perigosas não elegíveis" (POL-001) pode ter alta similaridade com "carga perigosa pode ser devolvida com autorização" (FAQ-03, que é informal e não confiável).

O retriever não tem como distinguir "isso veio de documento normativo oficial" vs. "isso veio do FAQ informal criado organicamente pelo time". O resultado pode ser respostas baseadas no FAQ que contradizem a política oficial.

**Proposta de correção:**  
Criar índice com campo de metadados `document_type` (normativo, procedimento, sla, faq_informal) e `reliability_tier` (1=normativo, 2=procedimento, 3=informal). Aplicar filtro de boost no retrieval: chunks de documentos normativos recebem boost de relevância. Chunks do FAQ são incluídos apenas quando não existe cobertura em documentos formais.

---

### Problema 5 (bônus): Sem estratégia para documentos contraditórios

**Por quê é um problema:**  
A proposta não menciona como tratar PROC-042 v1 e PROC-042-v2, que coexistem no SharePoint com multiplicadores diferentes. Com índice único e sem metadados de versão, o retriever pode retornar chunks das duas versões e o LLM vai misturar os valores silenciosamente.

**Proposta de correção:**  
Ver ADR-0003 — abordagem em três camadas (metadados + penalização de score + instrução no prompt).

---

## Parte 2 — Revisão do Claude

*Prompt enviado ao Claude:*

> "Revise criticamente a seguinte proposta de arquitetura de RAG para o projeto NovaTech (empresa de logística com ~1.250 fontes documentais). Identifique problemas técnicos reais — não genéricos. A proposta é: 'Azure AI Search com embeddings do ada-002. Todos os documentos indexados num único índice. Chunking fixo de 512 tokens sem overlap. LLM recebe 3 chunks mais similares. GPT-4o para geração. Pipeline de ingestão roda manualmente quando alguém lembra de atualizar.'"

### Problemas identificados pelo Claude (sumarizados):

**C1. ada-002 pode ser subótimo para domínio específico**  
O Claude identificou que text-embedding-ada-002 é um modelo de embedding genérico. Para domínio especializado como logística com terminologia específica (CT-e, ANTT, multiplicador regional, fator de peso), modelos de embedding mais recentes (text-embedding-3-large ou modelos fine-tunados) podem ter recall superior. Ada-002 pode não capturar bem a similaridade semântica entre "frete especial acima de 500kg" e "carga pesada com tarifa diferenciada".

**C2. Sem estratégia de re-ranking**  
O Claude apontou que busca por similaridade de embedding (primeira fase) é imprecisa — retorna candidatos por proximidade vetorial, mas não necessariamente por relevância real para a pergunta. Um re-ranker (ex: cross-encoder) na segunda fase melhora a precisão significativamente. A proposta não menciona re-ranking.

**C3. Sem avaliação de qualidade do retrieval**  
O Claude observou que a proposta não define como medir se o retrieval está funcionando bem. Sem métricas (precision@k, recall@k, MRR), é impossível saber se os chunks recuperados são os corretos ou se são apenas os mais similares em embedding — que pode não ser a mesma coisa.

**C4. Sem tratamento de consultas ambíguas**  
O Claude identificou que queries como "qual o prazo?" são ambíguas — prazo de devolução? prazo de entrega? prazo de SLA? O sistema não tem mecanismo para detectar ambiguidade e pedir clarificação.

---

## Parte 3 — Comparação entre as revisões

| # | Problema | Encontrado pelo TL | Encontrado pelo Claude |
|---|---|---|---|
| 1 | Chunking fixo sem overlap | ✅ | ✅ (com menos detalhe sobre fronteiras) |
| 2 | Apenas 3 chunks insuficiente | ✅ | ✅ |
| 3 | Ingestão manual | ✅ (como risco principal) | ✅ (mencionou, menos ênfase) |
| 4 | Índice único mistura confiabilidade | ✅ | ✅ |
| 5 | Documentos contraditórios | ✅ | ✅ |
| C1 | ada-002 subótimo para domínio | ❌ | ✅ |
| C2 | Sem re-ranking | ❌ | ✅ |
| C3 | Sem métricas de qualidade do retrieval | ❌ | ✅ |
| C4 | Consultas ambíguas sem tratamento | ❌ | ✅ |

**O que o Claude encontrou que o TL não viu:**
- A questão do modelo de embedding (ada-002) específico para domínio — válido e relevante, mas de prioridade média para o prazo de 3 meses.
- Re-ranking como segunda fase — importante para produção, havia sido considerado internamente mas não incluído na revisão inicial.
- Métricas de qualidade de retrieval — gap real que precisa ser adicionado ao plano.

**O que o TL encontrou que o Claude não mencionou com profundidade:**
- A criticidade operacional da ingestão manual (o Claude mencionou, mas não enfatizou que isso viola um requisito explícito do PS).
- O problema de confiabilidade diferenciada entre documentos normativos e FAQ informal — o Claude mencionou índice único mas não aprofundou o risco de FAQ informal contaminar respostas normativas.

**Análise honesta:** O Claude adicionou 4 problemas reais que não estavam na revisão inicial. Os problemas de re-ranking e métricas de retrieval são gaps genuínos. O problema do embedding ada-002 é válido mas de menor prioridade no prazo atual. A revisão humana foi mais aprofundada nos problemas operacionais e de dados; a revisão do Claude foi mais abrangente nos problemas técnicos de ML.

---

## Parte 4 — Proposta Reescrita

> **Versão revisada da arquitetura de RAG — NovaTech Assistente**

**Stack base:**
- Azure AI Search (S1) como vector store.
- text-embedding-3-large (Azure OpenAI) para embeddings — melhor recall em domínios especializados que ada-002.
- GPT-4o para geração de resposta.
- LangChain como camada de orquestração.

**Estratégia de ingestão:**
- Indexer nativo do Azure AI Search com conector SharePoint — atualização automática por change tracking.
- Scheduled job a cada 6h para Confluence e planilhas XLSX (webhook onde disponível).
- SLA de disponibilidade: novos documentos indexados em até 1h após publicação (bem abaixo do requisito de 24h).

**Estrutura do índice:**
- Índice único com campos de metadados obrigatórios: `doc_id`, `version`, `emission_date`, `document_type` (normativo/procedimento/sla/faq_informal), `reliability_tier` (1-3), `supersedes` (para documentos que substituem versões anteriores).
- Filtro de boost no retrieval: documentos de `reliability_tier=1` recebem multiplicador de 1.3× no score. Documentos `reliability_tier=3` (FAQ) só entram no contexto quando nenhum documento formal cobre o tema.

**Estratégia de chunking:**
- Chunking por estrutura semântica: delimitadores são headers H1/H2/H3 e fim de seção.
- Chunks entre 400–800 tokens (variável pela seção, não fixo).
- Overlap de 10% entre chunks consecutivos do mesmo documento.
- Tabelas são tratadas como chunks indivisíveis — nunca cortadas no meio.
- Documentos escaneados passam por Azure Document Intelligence antes do chunking.

**Estratégia de retrieval:**
- Fase 1 (recall): recuperar top-20 chunks por similaridade de embedding.
- Fase 2 (precision): re-ranker cross-encoder reordena os 20 candidatos.
- Fase 3 (seleção): selecionar top-8 (padrão) ou top-12 (multi-domínio) após re-ranking.
- Chunks com score < 0.60 após re-ranking são descartados.
- Detecção de queries ambíguas: se a pergunta contém termos que mapeiam para mais de 2 domínios sem especificador, o sistema solicita clarificação antes de responder.

**Monitoramento e métricas:**
- Logging de todas as queries com chunks recuperados, scores e resposta gerada.
- Métricas semanais: precision@8 (usando sample de avaliação humana), taxa de respostas sem citação detectada pelo harness, taxa de truncamento de contexto.
- Dashboard no Azure Monitor para alertas de degradação.

**Tratamento de documentos contraditórios:**
- Ver ADR-0003 — abordagem em três camadas.

---

*Exercício 1.3 — Cenário 1 | Tech Lead DB1 | Junho/2025*
