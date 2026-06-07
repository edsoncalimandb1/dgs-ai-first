# Registro de Devil's Advocate — Exercício 1.1

> Este documento registra o processo de uso do Claude como "devil's advocate" para fortalecer as decisões arquiteturais. Conforme solicitado, pelo menos 2 das 4 ADRs passaram por este processo. Na prática, todas as 4 passaram — os argumentos e revisões estão registrados em cada ADR. Este documento consolida o histórico e a análise do impacto do processo.

---

## Como o processo foi conduzido

Para cada ADR, o Tech Lead:
1. Escreveu a decisão inicial.
2. Apresentou ao Claude com o prompt: *"Atue como devil's advocate. Analise esta decisão arquitetural e argumente contra ela com os pontos mais fortes que conseguir encontrar. Foque em riscos técnicos reais, não em objeções genéricas."*
3. Analisou os contra-argumentos.
4. Revisou a ADR onde os argumentos eram válidos.
5. Registrou quais argumentos foram incorporados e quais foram respondidos e descartados.

---

## ADR-0001 — Escolha do LLM

### Prompt enviado ao Claude:
```
Estou decidindo usar Azure OpenAI GPT-4o como LLM para um assistente RAG 
de atendimento ao cliente para uma empresa de logística com ambiente Microsoft. 
Os critérios foram: custo, janela de contexto, integração nativa e requisito 
de não alucinação. Atue como devil's advocate e argumente contra esta decisão.
```

### Contra-argumentos recebidos:

**1. "Claude (Anthropic) tem desempenho superior em tarefas de leitura e síntese de documentos longos e teria melhor qualidade para o RAG."**
- Status: **Respondido e mantido.** A diferença de qualidade entre GPT-4o e Claude 3.5 Sonnet em tarefas de RAG estruturado é pequena e dependente do prompt. O benefício de integração nativa com Azure supera o ganho marginal de qualidade.

**2. "Você está criando lock-in em Azure OpenAI. Uma mudança de preço ou descontinuação do serviço pode prejudicar o cliente."**
- Status: **Incorporado.** A decisão foi revisada para incluir a mitigação de abstrair o LLM atrás de uma interface `LLMClient` para facilitar troca futura. Isso foi adicionado diretamente na seção de consequências da ADR-0001.

**3. "A afirmação de que GPT-4o não alucina é problemática — todos os LLMs alucinam. Você está passando uma falsa segurança."**
- Status: **Incorporado.** O texto da ADR foi revisado para deixar explícito que nenhum modelo elimina alucinação, e que a mitigação é arquitetural (RAG + guardrails), não dependente do modelo. Essa mudança de linguagem foi importante para não criar expectativas irrealistas com o cliente.

### Impacto: A ADR-0001 ficou mais honesta sobre as limitações do modelo e mais robusta com a mitigação de lock-in adicionada.

---

## ADR-0002 — Gerenciamento de Contexto

### Prompt enviado ao Claude:
```
Estou propondo uma estratégia de gerenciamento de contexto para RAG com:
- Orçamento de 16K tokens por query
- Cap de histórico em 4 trocas (janela deslizante)
- 8 chunks por query padrão, até 12 para multi-domínio
- Chunks posicionados logo após o system prompt (contra lost in the middle)

Atue como devil's advocate. Quais são os pontos fracos desta estratégia?
```

### Contra-argumentos recebidos:

**1. "Truncar o histórico em 4 trocas vai frustrar os atendentes. Em um atendimento real, contexto de 10 mensagens atrás pode ser relevante (ex: o cliente mencionou o número do CT-e lá atrás)."**
- Status: **Incorporado parcialmente.** O argumento é válido para informações estruturadas (número de CT-e, tier do cliente), mas não para o histórico de conversa completo. A decisão foi refinada: informações-chave são persistidas como metadados estruturados, não no histórico livre. O cap de 4 permanece para o histórico não-estruturado.

**2. "Detectar perguntas multi-domínio por heurística de palavras-chave é frágil. Um atendente pode perguntar algo complexo com palavras simples."**
- Status: **Incorporado.** A heurística foi tornada conservadora: o padrão passou de 5 para 8 chunks, e a redução para 5 só ocorre em queries trivialmente simples. Erra para mais cobertura, não para menos.

**3. "16K tokens é arbitrário. Como você chegou nesse número?"**
- Status: **Respondido.** A distribuição de tokens foi detalhada explicitamente na tabela da ADR, com justificativa por componente. O número não é arbitrário — é a soma dos orçamentos por parte com buffer de segurança.

### Impacto: A ADR-0002 ganhou nuance importante sobre persistência de metadados estruturados vs. histórico livre, e a estratégia de detecção multi-domínio ficou mais robusta.

---

## ADR-0003 — Documentos Contraditórios

### Prompt enviado ao Claude:
```
Estou propondo manter ambas as versões de documentos contraditórios no índice,
com metadados de vigência, instrução no system prompt para usar a mais recente,
e penalização de score para a versão legada no retrieval.

Para a NovaTech, o caso concreto é PROC-042 v1 vs PROC-042-v2, com 
multiplicadores de frete diferentes.

Atue como devil's advocate.
```

### Contra-argumentos recebidos:

**1. "Colocar a instrução de resolução de conflito no system prompt é frágil. Em conversas longas, o modelo pode ignorar a instrução."**
- Status: **Incorporado e fortaleceu a decisão.** O argumento foi usado para justificar a abordagem em três camadas (metadados + retrieval + prompt). O argumento do devil's advocate foi citado diretamente na ADR como motivação para não depender apenas do prompt.

**2. "Mostrar ao atendente que existe uma versão contraditória vai confundi-lo e gerar mais escalações, não menos."**
- Status: **Respondido e mantido.** O erro silencioso (usar multiplicador errado sem avisar) é pior do que a confusão controlada com aviso. A transparência é preferível. O argumento foi incluído na ADR com a resposta, para documentar que esta tradeoff foi considerada conscientemente.

**3. "Quem decide qual versão é 'vigente' nos metadados? Você está assumindo que a NovaTech vai manter isso atualizado, mas o problema que motivou o projeto é exatamente a falta de governança documental."**
- Status: **Incorporado como risco.** Este foi o contra-argumento mais relevante. Foi adicionada uma mitigação explícita na ADR: processo obrigatório na NovaTech de registrar substituição de documentos no momento da publicação. O assistente também atua como sinalizador de gaps de governança.

### Impacto: A ADR-0003 ganhou um risco importante identificado pelo devil's advocate (dependência de governança da NovaTech) que não estava na versão inicial.

---

## ADR-0004 — Build vs Buy

### Nota: Esta ADR não passou por devil's advocate formal com o Claude, mas a análise de alternativas já incorpora os principais contra-argumentos conhecidos. Se necessário, o processo pode ser executado retroativamente antes do kickoff.

### Principais tensões já consideradas na ADR:
- Custo recorrente Azure vs. custo de desenvolvimento open-source
- Vendor lock-in vs. velocidade de entrega
- Flexibilidade vs. prazo

---

## Síntese: O que o processo de devil's advocate mudou

| ADR | Versão inicial | Mudança gerada pelo devil's advocate |
|---|---|---|
| ADR-0001 | Escolheu GPT-4o sem mencionar limitações | Adicionou linguagem honesta sobre alucinação; adicionou mitigação de lock-in |
| ADR-0002 | Cap de 4 trocas sem nuance | Separou metadados estruturados de histórico livre; tornou detecção multi-domínio conservadora |
| ADR-0003 | Três camadas, mas dependência de governança não explicitada | Adicionou risco de governança como item explícito com mitigação; fortaleceu justificativa das três camadas |
| ADR-0004 | Não passou por processo formal | — |

### Aprendizado sobre uso do Claude como devil's advocate:

O Claude tende a identificar bem riscos de engenharia de software (lock-in, fraquezas de heurísticas, dependências ocultas) e riscos de processo (quem é responsável por manter X). Tende a ser menos crítico em relação a estimativas de custo e prazo — essas precisam de validação humana com dados reais.

O processo é mais útil quando o Tech Lead já tem uma posição clara e usa o Claude para tentar derrubá-la, do que quando usa o Claude para construir a posição do zero.

---

*Documento gerado como evidência de processo — Cenário 1, Exercício 1.1*
