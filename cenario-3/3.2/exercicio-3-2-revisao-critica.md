# Exercício 3.2 — Revisão Crítica da Arquitetura Gerada com IA
**Papel:** Tech Lead  
**Cenário:** NovaTech — Assistente de Atendimento com RAG  
**Tópico:** Revisão Crítica de Outputs de IA  

---

## Contexto

Quatro artefatos do projeto foram gerados com apoio de IA e precisam ser revisados antes do go-live em 2 semanas:

- **AGENTS.md** — gerado pelo Claude, refinado 4 vezes, 15 páginas
- **3 Skills** — Foundation refinada após testes; as outras duas usadas sem refinamento
- **Pipeline** — ingestão e query endpoint ~60-70% gerados pelo Copilot
- **System prompt** — iterado 6 vezes sem documentar o motivo de cada mudança

---

## Etapa 1 — Avaliação humana (feita antes do co-review com IA)

### AGENTS.md
**Risco identificado:** O documento está grande demais — 15 páginas é excessivo mesmo após 4 refinamentos. Um documento nesse tamanho não é lido integralmente antes de cada uso, o que significa que regras críticas podem ser ignoradas na prática.

**O que verificar:** Contradições internas acumuladas entre refinamentos. Regras duplicadas ou que se sobrepõem. Seções que poderiam ser consolidadas ou removidas.

### Skills
**Risco identificado:** As 2 skills sem refinamento são um problema — foram aceitas sem validação com casos reais. Só a Foundation tem evidência de funcionamento.

**O que verificar:** Executar casos de teste em cada skill antes do go-live. Sem isso, a primeira falha aparece em atendimento real.

### Pipeline (60-70% Copilot)
**Risco identificado:** Não mencionado na avaliação inicial — é o risco mais silencioso. Código gerado por Copilot funciona nos casos testados, mas tende a falhar em edge cases e tratamento defensivo de erros.

**O que verificar:** Qualidade das assertions nos testes de integração existentes. Cobertura de 75% mede linhas executadas, não cenários relevantes.

### System prompt
**Risco identificado:** 6 iterações sem documentação das mudanças. Sem histórico, não há como fazer rollback consciente se o comportamento regredir após o go-live.

**O que verificar:** Instruções contraditórias acumuladas entre iterações. Baseline para comparação de testes.

---

## Etapa 2 — Co-review com Claude (complementação)

### AGENTS.md — complementação

O risco não é só o tamanho, é o que o tamanho causa:

**Lost in the middle no contexto do Copilot:** Um AGENTS.md de 15 páginas sofre o mesmo efeito documentado na ADR-0002 para chunks de RAG — instruções no final do documento têm menos peso que as do início. Regras críticas enterradas na página 12 podem ser sistematicamente ignoradas pelo Copilot ao gerar código.

**Manutenção degradada:** Ninguém atualiza o que não consegue ler rápido. Com o tempo, o time vai editar seções sem ler o documento inteiro, aumentando o risco de contradições internas.

**4 refinamentos ≠ coerência:** Cada refinamento provavelmente adicionou seções sem remover o que foi substituído. O documento pode ter regras contraditórias entre versões acumuladas que nenhuma revisão isolada pegou.

**O que verificar (concreto):** Contar quantas regras existem, identificar sobreposições, medir se o documento pode ser reduzido para 5-7 páginas sem perda de cobertura.

### Skills — complementação

O risco é assimétrico: a Foundation tem evidência de funcionamento, as outras duas não. Em produção, a primeira falha vai aparecer num atendimento real.

**O que verificar (concreto):** Para cada skill sem refinamento, executar ao menos 5 casos cobrindo: caminho feliz, caso de borda, e caso onde a skill deveria recusar ou escalar. Documentar os resultados como evidência.

### Pipeline — complementação

**Cobertura ≠ qualidade de testes:** 75% de cobertura mede linhas executadas, não cenários relevantes. Um teste que envia `{ question: "prazo devolução" }` e verifica apenas `status 200` conta para a cobertura sem verificar se a resposta está correta. Esse padrão de assertion vaga é exatamente o que o Copilot tende a gerar.

**Tratamento de erros defensivo:** Código gerado por Copilot tende a não implementar circuit breakers, timeouts, ou respostas de fallback. Se o Azure AI Search ou o Azure OpenAI ficarem indisponíveis, o comportamento atual do endpoint é desconhecido.

**O que verificar (concreto):** Auditar as assertions dos testes de integração dos endpoints críticos (query e feedback). Para cada teste que só verifica status code, avaliar se há um cenário relevante não coberto.

### System prompt — complementação

**Rollback cego:** Sem documentação das 6 iterações, o time não consegue identificar qual mudança introduziu um comportamento inesperado após o go-live — e não consegue voltar para uma versão anterior com confiança. É equivalente a um repositório de código sem histórico de commits.

**Instruções contraditórias acumuladas:** 6 iterações sem documentação provavelmente resultaram em instruções que se contradizem. Exemplo: uma iteração pode ter adicionado "sempre mostre ambas as versões do documento" e uma posterior "priorize sempre a versão mais recente" — e ambas coexistem no prompt atual sem que ninguém perceba. Isso é especialmente crítico porque o system prompt é a implementação das decisões da ADR-0003.

**O que verificar (concreto):** Ler o prompt atual linha a linha buscando instruções que se contradizem. Versionar o estado atual no repositório como ponto de partida. Criar changelog retroativo mínimo das 6 versões com base no que for possível reconstruir.

---

## Comparação: avaliação humana vs. co-review com Claude

| Artefato | Humano identificou | Claude complementou |
|----------|--------------------|---------------------|
| AGENTS.md | Tamanho excessivo mesmo após refinamentos | Lost in the middle no Copilot; manutenção degradada; contradições entre refinamentos acumulados |
| Skills | 2 skills sem validação são risco | Risco assimétrico — Foundation tem evidência, as outras não; formato concreto de testes |
| Pipeline | Não mencionado na avaliação inicial | Assertions vagas contam para cobertura sem testar conteúdo; ausência de tratamento defensivo de erros |
| System prompt | Falta documentação das mudanças | Risco de rollback cego; instruções contraditórias acumuladas; impacto direto na ADR-0003 |

**Onde o humano foi mais preciso:** identificação do padrão geral em AGENTS.md e skills — a intuição sobre tamanho e falta de validação estava certa.

**Onde o Claude complementou com mais valor:** no pipeline (risco não identificado inicialmente) e na conexão do system prompt com a ADR-0003 (impacto arquitetural que não era óbvio).

---

## Etapa 3 — Priorização para 2 semanas

### Critério de priorização

Dois fatores orientam a decisão: **impacto se falhar em produção** e **esforço para mitigar**. Riscos de alto impacto e baixo esforço de mitigação são atacados primeiro. Riscos de impacto médio e alto esforço são aceitos como residual com controle.

### O que atacar nas 2 semanas

**1. Pipeline — prioridade máxima**

É o risco mais silencioso e de maior impacto. Se o endpoint de query falhar em produção sem tratamento defensivo, o assistente para completamente — sem fallback, sem mensagem para o atendente. Os 75% de cobertura dão falsa segurança.

Ação: auditar as assertions dos testes de integração dos endpoints críticos (query e feedback). Para cada teste com assertion vaga, avaliar e corrigir. Implementar timeout e resposta de fallback no endpoint de query.

Esforço estimado: 3-4 dias.

**2. AGENTS.md — prioridade alta**

Afeta todos os outputs do Copilot durante o restante do desenvolvimento e manutenção futura. Um AGENTS.md com contradições internas contamina o código gerado de forma sistemática e silenciosa.

Ação: passe de auditoria buscando contradições e duplicações. Meta: reduzir para 5-7 páginas. Regras que não cabem nesse espaço provavelmente são detalhes de implementação que pertencem em comentários de código, não no AGENTS.md.

Esforço estimado: 1-2 dias.

### O que aceitar como risco residual (com controle)

**3. System prompt — residual controlado**

Aceitar como residual, mas com uma condição: versionar o estado atual no repositório e fazer um passe de 2-3 horas buscando instruções contraditórias. Isso não elimina o risco, mas transforma rollback cego em rollback possível — se o comportamento regredir após o go-live, há um ponto de referência para comparar.

Sem essa ação mínima, aceitar como residual significa aceitar que um eventual problema de comportamento em produção pode ser irrastreável.

**4. Skills — residual com testes como gate**

Aceitar como residual, mas com gate de entrada em produção: as 2 skills não refinadas só vão a produção após execução dos 5 casos de teste por skill documentados na etapa 2. Se algum caso reprovar, a skill não vai ao ar — o atendente opera sem ela até o refinamento.

Isso garante que "aceitar como residual" não significa "ignorar" — significa "controlar a exposição".

### Resumo da priorização

| Artefato | Decisão | Ação nas 2 semanas | Esforço |
|----------|---------|--------------------|---------|
| Pipeline | Atacar | Auditar assertions + implementar fallback | 3-4 dias |
| AGENTS.md | Atacar | Auditoria de contradições + redução de tamanho | 1-2 dias |
| System prompt | Residual controlado | Versionar estado atual + passe de contradições | 2-3 horas |
| Skills | Residual com gate | 5 casos de teste por skill como gate de go-live | 1 dia |

---

*Exercício 3.2 — Tech Lead | Cenário 3 — Fase de Governança e Validação | Junho/2025*
