# ADR-0001: Escolha do Modelo de LLM para o Assistente NovaTech

## Status: Aceito

## Contexto

O assistente de atendimento da NovaTech precisa de um LLM capaz de responder perguntas em linguagem natural sobre a documentação interna da empresa. Os parâmetros que orientam esta decisão são:

- **Volume operacional:** 320 chamados/dia × 60% com consulta à documentação = ~192 queries/dia ao LLM. Projeção mensal: ~4.200 queries.
- **Contexto por query:** system prompt (~2K tokens) + chunks (~3K tokens) + histórico (~1K tokens) + pergunta (~200 tokens) ≈ 6.000–8.000 tokens por query. O modelo precisa suportar pelo menos 16K tokens de forma confiável.
- **Requisito crítico de qualidade:** O assistente nunca deve inventar prazos, valores ou procedimentos. Respostas incorretas geram problemas operacionais e de compliance para os atendentes.
- **Ecossistema existente:** A NovaTech já tem licenças Microsoft 365 E3 e está disposta a provisionar Azure AI Services. O assistente será integrado ao Teams e SharePoint.
- **Restrição de dados:** A documentação interna é sensível (procedimentos operacionais, regras comerciais). O processamento deve ocorrer em ambiente com contrato de dados adequado (DPA/BAA).

**Forças em tensão:**
- Integração nativa no ecossistema Azure vs. melhor qualidade técnica disponível
- Custo operacional vs. qualidade das respostas
- Facilidade de contratação vs. flexibilidade técnica

---

## Decisão

**Adotar Azure OpenAI Service com modelo GPT-4o** como LLM principal para geração de respostas.

Justificativa dos critérios:

**1. Custo por token para o volume estimado**
- GPT-4o (Azure): ~$5/1M tokens input, ~$15/1M tokens output.
- Com 4.200 queries/mês × 8K tokens input = ~33.6M tokens input/mês ≈ **$168/mês**.
- Output estimado (400 tokens/resposta): 4.200 × 400 = 1.68M tokens ≈ **$25/mês**.
- **Total estimado: ~$193/mês** — custo viável dentro do orçamento do projeto.
- Claude API (Anthropic): custo similar, mas exigiria contrato separado sem integração nativa ao Azure.
- Ollama/open-source local: custo de infra + complexidade operacional tornam o TCO comparável ou superior sem benefício proporcional.

**2. Janela de contexto**
- GPT-4o suporta 128K tokens — mais do que suficiente para o orçamento de 8K por query e para acomodar históricos de conversas longas no Teams sem truncamento.

**3. Aderência ao requisito de não alucinação**
- GPT-4o com temperatura 0 e instrução explícita de grounding ("responda somente com base nos documentos fornecidos") demonstra comportamento adequado para tarefas de RAG em produção.
- **Importante:** nenhum modelo elimina alucinação por completo. A mitigação é arquitetural (RAG + guardrails), não dependente apenas do modelo escolhido.

**4. Integração com o stack Azure**
- Azure OpenAI se integra nativamente com Azure AI Search, Azure Functions, Microsoft Teams (via Bot Framework) e o ambiente Microsoft 365 E3 já licenciado.
- Reduz complexidade operacional: um único plano de suporte, um único fornecedor, conformidade com contratos Microsoft já existentes.

---

## Consequências

**Positivas:**
- Stack unificado: Azure OpenAI + Azure AI Search + Teams Bot Framework — menos friction operacional.
- Contrato de dados (DPA) já coberto pelo acordo Microsoft existente da NovaTech.
- Suporte ao nível enterprise da Microsoft.
- Custo previsível e dentro do orçamento.

**Negativas / Riscos:**
- Vendor lock-in em Azure OpenAI. Se a Microsoft descontinuar ou alterar preços significativamente, a migração é custosa.
- Qualidade do modelo é dependente das atualizações da Microsoft/OpenAI — atualizações automáticas podem alterar comportamento do assistente entre versões.
- O modelo não elimina alucinação; o pipeline de RAG e os guardrails são responsabilidade da DB1, não do fornecedor.
- Latência pode ser afetada por disponibilidade da região Azure escolhida.

**Mitigações adotadas:**
- Abstrair a chamada ao LLM atrás de uma interface (ex: classe `LLMClient`) para facilitar troca futura de modelo.
- Fixar a versão do modelo no deployment (ex: `gpt-4o-2024-05-13`) para evitar comportamento inesperado por atualização automática.
- Implementar guardrails determinísticos fora do modelo (ver ADR-0002).

---

## Alternativas Consideradas

| Alternativa | Motivo de descarte |
|---|---|
| **Claude API (Anthropic)** | Qualidade técnica comparável ou superior em tarefas de RAG, mas requer contrato separado, DPA adicional, e não tem integração nativa com Teams/SharePoint. Aumenta complexidade sem benefício proporcional dado o ecossistema Azure da NovaTech. Pode ser reavaliado em projetos futuros. |
| **Ollama + LLaMA 3 / Mistral (local)** | Custo zero de inferência, sem dependência de fornecedor externo. Porém: requer infraestrutura de GPU própria (custo de capital), manutenção do modelo, qualidade inferior ao GPT-4o em tarefas de instrução e grounding. Não recomendado para produção em prazo de 3 meses. |
| **Azure AI Studio com Phi-3 (Microsoft SLM)** | Menor custo, menor latência. Porém: janela de contexto menor e qualidade de instrução inferior para documentos complexos com tabelas e exceções de regras. Pode ser reconsiderado para camadas de triagem no futuro. |

---

## Devil's Advocate — Argumentos Contra (gerados com Claude)

*O Tech Lead apresentou esta decisão ao Claude e pediu que argumentasse contra. Os argumentos e as respostas estão registrados abaixo para documentar o raciocínio.*

**Argumento 1:** "Claude (Anthropic) tem desempenho superior em tarefas de leitura e síntese de documentos longos. Para um RAG com documentos contraditórios, a capacidade de raciocínio nuançado é mais importante que a integração com o ecossistema."

*Resposta:* A diferença de qualidade entre GPT-4o e Claude 3.5 Sonnet em tarefas de RAG com contexto estruturado é pequena e depende fortemente do prompt. Dado que o ganho marginal de qualidade não compensa a complexidade adicional de contrato e integração, a decisão se mantém. Se testes pilotos mostrarem degradação significativa de qualidade, a decisão deve ser revisada antes do go-live.

**Argumento 2:** "Fixar o vendor em Azure OpenAI cria lock-in. Daqui a 6 meses o contrato pode mudar e a NovaTech fica refém."

*Resposta:* Argumento válido. A mitigação (abstrair o LLM atrás de uma interface) foi adicionada diretamente à seção de consequências como resultado deste contra-argumento.

---

*Data da decisão: Junho/2025 | Autor: Tech Lead DB1 | Revisores: DM, Dev*
