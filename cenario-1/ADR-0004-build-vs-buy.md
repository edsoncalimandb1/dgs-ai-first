# ADR-0004: Build vs Buy para o Pipeline de RAG

## Status: Aceito

## Contexto

O pipeline de RAG é o coração técnico do projeto. Ele precisa:
1. Extrair texto de PDFs (incluindo tabelas complexas e documentos escaneados com OCR), páginas do Confluence (com links internos e macros), e planilhas XLSX com fórmulas.
2. Dividir o texto em chunks, gerar embeddings e armazenar num vector store.
3. Receber perguntas, gerar embeddings da query, buscar chunks por similaridade, e montar o contexto para o LLM.
4. Rodar com pipeline de atualização automático: novos documentos publicados no SharePoint devem estar disponíveis no assistente em até 24h.

**As duas opções principais:**

**Opção A — Build com open-source (LangChain/LlamaIndex + ChromaDB ou FAISS)**
- Controle total sobre cada etapa do pipeline.
- Código versionado no repositório da DB1.
- Custo zero de licença para o pipeline (somente infra).
- Requer: implementar extração de PDFs (PyMuPDF, pdfplumber), OCR (Tesseract ou Azure Vision), conector Confluence, conector XLSX, gerenciar o vector store, implementar re-ranking, monitoramento, etc.

**Opção B — Buy com Azure managed (Azure AI Search + Azure OpenAI + Azure Document Intelligence)**
- Azure AI Search: serviço gerenciado de busca vetorial com skillsets de extração de documentos.
- Azure Document Intelligence: OCR e extração de tabelas de PDFs gerenciados pela Microsoft.
- Indexers nativos para SharePoint e OneDrive — atualização automática nativa.
- Custo: Azure AI Search (S1, ~$250/mês) + Document Intelligence (pay-per-use, ~$1.50/1K páginas).
- A NovaTech já tem Azure AI Services provisionados (licença E3 + disposição para Azure).

**Forças em tensão:**
- Controle técnico total vs. velocidade de entrega e menor risco operacional
- Custo zero de licença open-source vs. custo gerenciado mas com TCO potencialmente menor
- Flexibilidade ilimitada vs. integração nativa com o ecossistema existente da NovaTech
- Prazo de 3 meses vs. complexidade de construir extração robusta do zero

---

## Decisão

**Adotar Opção B — Azure AI Search + Azure Document Intelligence como base do pipeline**, com LangChain como camada de orquestração sobre os serviços Azure para manter portabilidade.

**Justificativa por dimensão:**

### 1. Custo

| Componente | Build (open-source) | Buy (Azure managed) |
|---|---|---|
| Vector store (ChromaDB self-hosted) | Custo de VM (~$100/mês) + manutenção | Azure AI Search S1: ~$250/mês |
| OCR de documentos escaneados (~15% de 800 docs = 120 docs) | Tesseract (gratuito, mas qualidade inferior) ou Azure Vision (pay-per-use) | Azure Document Intelligence (incluso no pipeline) |
| Conectores SharePoint + Confluence | Desenvolvimento custom (estimativa: 3 semanas) | Indexer nativo SharePoint (0 desenvolvimento) |
| Atualização automática de documentos | Desenvolvimento custom (pipeline, scheduler, delta sync) | Change tracking nativo do indexer Azure |
| **Estimativa TCO 3 meses** | **~$300 infra + ~15 dias dev** | **~$750 serviços + ~5 dias config** |

O custo de licença do Azure é maior, mas o custo de desenvolvimento e manutenção do build é significativamente superior dentro do prazo de 3 meses.

### 2. Complexidade operacional

O problema mais crítico identificado pelo desenvolvedor foi a extração de PDFs com tabelas complexas e documentos escaneados. Azure Document Intelligence é treinado especificamente para extração de tabelas de documentos comerciais — qualidade superior ao Tesseract para o tipo de documento da NovaTech (tabelas de frete com 15+ colunas, formulários de SLA).

Implementar extração robusta do zero em 3 meses, com qualidade adequada para produção, é tecnicamente arriscado.

### 3. Prazo de 3 meses

O prazo inclui discovery + desenvolvimento + go-live. Com build open-source, estima-se:
- Semana 1–2: conectores de extração (PDF, OCR, Confluence, XLSX)
- Semana 3: chunking, embeddings, vector store
- Semana 4: retrieval, re-ranking, montagem de contexto
- Semana 5–6: integração Teams, testes, ajustes
- Semana 7–8: piloto com atendentes reais
- Semana 9–12: correções e go-live

Com Azure managed, as semanas 1–3 são substituídas por configuração de indexers e skillsets, liberando as semanas para refinamento do pipeline e integração.

### 4. Integração nativa com Microsoft 365

O indexer do Azure AI Search tem conector nativo para SharePoint Online. Quando um documento é atualizado no SharePoint, o indexer detecta a mudança automaticamente (change tracking) e re-indexa o documento em até 5 minutos — muito abaixo do SLA de 24h definido pelo PS.

### 5. Flexibilidade preservada via LangChain

A camada de orquestração (montagem do contexto, estratégia de retrieval, re-ranking, montagem do prompt) será implementada em LangChain sobre os serviços Azure. Isso significa que, se no futuro a NovaTech quiser migrar o vector store para Pinecone ou o LLM para Claude API, as mudanças ficam restritas às classes de adapter, não ao pipeline inteiro.

---

## Consequências

**Positivas:**
- Prazo viável: go-live em 3 meses é realista com Azure managed.
- Atualização automática de documentos nativa — não requer desenvolvimento custom.
- Extração de tabelas e OCR com qualidade superior ao que seria construído no prazo.
- Stack unificada com o ambiente Microsoft existente da NovaTech — operação mais simples pós go-live.

**Negativas / Riscos:**
- Vendor lock-in parcial em Azure AI Search. Migração futura exige re-indexação completa.
- Custo recorrente de ~$250–400/mês pelos serviços gerenciados.
- Customizações profundas no pipeline de retrieval (ex: re-ranking customizado, hybrid search com filtros de metadados) exigem conhecimento da API do Azure AI Search, que tem curva de aprendizado.
- O comportamento do indexer automático pode gerar re-indexações desnecessárias se documentos forem editados frequentemente (ex: planilhas salvas com pequenas alterações).

**Mitigações:**
- Abstrair Azure AI Search atrás de interface `VectorStoreClient` — facilita troca futura.
- Implementar filtro no indexer para detectar mudanças significativas (hash do conteúdo) antes de disparar re-indexação completa.
- Monitorar custo mensal dos serviços Azure e revisar tier do AI Search se volume crescer.

---

## Alternativas Consideradas

| Alternativa | Motivo de descarte |
|---|---|
| **LangChain + ChromaDB + PyMuPDF (build completo)** | Viável tecnicamente, mas o prazo de 3 meses não acomoda extração robusta de PDFs com tabelas, OCR de 120 documentos escaneados, E conectores de SharePoint/Confluence com atualização automática. O risco de qualidade de extração é alto. |
| **LlamaIndex + Pinecone** | Pinecone tem excelente qualidade como vector store, mas adiciona um terceiro fornecedor sem integração com o ecossistema Azure. Custo similar ao Azure AI Search sem os benefícios de integração. |
| **Azure AI Studio (Prompt Flow nativo)** | Menor flexibilidade para customizar o pipeline de retrieval e a estratégia de contexto definida na ADR-0002. O Prompt Flow é adequado para protótipos, não para produção com as regras de gerenciamento de contexto que o projeto requer. |
| **Híbrido: Azure Document Intelligence para extração + ChromaDB local** | Captura o benefício do OCR/tabelas do Azure mas perde a atualização automática do indexer. Aumenta complexidade sem benefício proporcional. |

---

*Data da decisão: Junho/2025 | Autor: Tech Lead DB1 | Revisores: DM, Dev*
