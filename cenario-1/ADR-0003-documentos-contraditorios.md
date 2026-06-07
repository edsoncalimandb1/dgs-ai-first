# ADR-0003: Tratamento de Documentos Contraditórios no Pipeline de RAG

## Status: Aceito

## Contexto

A documentação da NovaTech contém contradições reais identificadas durante o discovery:

**Contradição confirmada — PROC-042 v1 vs PROC-042-v2:**

| Parâmetro | PROC-042 v1 (março/2023) | PROC-042-v2 (novembro/2023) |
|---|---|---|
| Fator de peso 1.001–3.000kg | 1.2 | 1.15 |
| Fator de peso acima de 3.000kg | 1.5 | 1.4 |
| Multiplicador Sul | 1.2 | 1.3 |
| Multiplicador Sudeste | 1.0 | 1.1 |
| Multiplicador Norte | 1.6 | 1.8 |
| Prazo adicional | +2 dias úteis | +3 dias úteis |

**O problema:** Nenhum dos dois documentos está marcado como obsoleto no SharePoint. A PROC-042-v2 menciona disposições transitórias (chamados anteriores a 01/12/2023 usam v1), mas essa data já passou. A v1 continua acessível e sem indicação de que foi substituída.

**O risco concreto:** Se o pipeline de RAG retornar chunks de ambas as versões na mesma query, o LLM pode:
- Usar o multiplicador da v1 para uma parte do cálculo e o da v2 para outra (mistura silenciosa).
- Responder com o valor da v1 por ser o primeiro chunk recuperado (relevância de embedding pode favorecer o mais antigo por coincidência de vocabulário).
- Apresentar ambos os valores sem indicar qual é o vigente, gerando confusão no atendente.

Qualquer um desses cenários resulta em cálculo de frete incorreto, com impacto financeiro direto para o cliente ou para a NovaTech.

**Forças em tensão:**
- Manter ambas as versões preserva histórico e atende contratos em transição vs. gera risco de mistura na geração
- Marcar a v1 como obsoleta resolve o problema técnico vs. pode invalidar cálculos para chamados antigos ainda em processamento
- Delegar a decisão ao LLM é simples de implementar vs. é probabilístico e pode falhar silenciosamente

---

## Decisão

**Manter ambas as versões no índice, com metadados de vigência explícitos, e instruir o modelo a priorizar a versão mais recente com divulgação transparente ao atendente.**

### Implementação em três camadas:

**Camada 1 — Metadados de ingestão (pipeline de dados)**

Cada chunk ingerido recebe metadados estruturados:
```json
{
  "doc_id": "PROC-042-v2",
  "doc_title": "Procedimento de Cálculo de Frete Especial",
  "version": "2.0",
  "emission_date": "2023-11-10",
  "supersedes": "PROC-042-v1",
  "status": "vigente",
  "transition_rule": "chamados_a_partir_de_2023-12-01"
}
```

Para a PROC-042 v1:
```json
{
  "doc_id": "PROC-042-v1",
  "version": "1.0",
  "emission_date": "2023-03-03",
  "status": "legado",
  "superseded_by": "PROC-042-v2",
  "transition_rule": "chamados_anteriores_a_2023-12-01"
}
```

**Camada 2 — Instrução no system prompt**

O system prompt contém seção explícita:
```
## Conflito entre versões de documentos

Quando você receber chunks de documentos com o mesmo nome mas versões diferentes:
1. Identifique as versões pelos metadados (campo "version" e "emission_date").
2. Use SEMPRE os valores da versão mais recente para novos cálculos.
3. Se a pergunta envolver um chamado aberto antes de 01/12/2023, alerte o atendente 
   para verificar manualmente qual versão se aplica.
4. NUNCA misture valores de versões diferentes no mesmo cálculo.
5. Sempre informe ao atendente qual versão foi usada na resposta.
```

**Camada 3 — Filtro no retrieval (before_llm guardrail)**

Antes de montar o contexto, o pipeline verifica:
- Se dois chunks do mesmo `doc_id` com versões diferentes foram recuperados, o chunk da versão mais antiga tem seu score penalizado em 40%.
- Se o chunk legado ainda entrar no contexto (score alto por similaridade), ele é marcado com tag `[VERSÃO LEGADA]` no texto inserido no contexto.

### Formato da resposta quando há contradição identificada:

```
[Fonte: PROC-042-v2, versão 2.0, emitida em 10/11/2023]
O multiplicador regional para a região Norte é **1.8**.

⚠️ Nota: existe uma versão anterior deste documento (PROC-042 v1, março/2023) 
com valor diferente (1.6). A versão vigente para chamados a partir de 01/12/2023 
é a v2. Se este chamado foi aberto antes dessa data, confirme com o supervisor 
qual versão se aplica.
```

---

## Consequências

**Positivas:**
- O atendente recebe informação completa e contexto para tomar decisão consciente.
- Chamados em transição (abertos antes de 01/12/2023) são tratados corretamente.
- O histórico documental é preservado — auditoria futura pode reconstruir o raciocínio.

**Negativas / Riscos:**
- A instrução no prompt é probabilística: o modelo pode ignorá-la em casos de edge case ou quando o contexto está muito carregado.
- Metadados de "versão mais recente" dependem de processo correto de ingestão — se o time de Operações publicar um novo documento sem atualizar os metadados, o pipeline não saberá qual é o vigente.
- A penalização de score no retrieval é uma heurística, não uma garantia.

**Mitigações:**
- Criar processo obrigatório na NovaTech: ao publicar nova versão de documento, a área responsável deve registrar a substituição no sistema de ingestão (formulário simples ou campo no SharePoint).
- Implementar alerta no dashboard de monitoramento quando dois chunks do mesmo documento com versões diferentes forem recuperados na mesma query — permite detectar casos onde a instrução no prompt pode ter falhado.
- Testar o comportamento do modelo com os cenários de contradição definidos pelo QA antes do go-live.

---

## Alternativas Consideradas

| Alternativa | Motivo de descarte |
|---|---|
| **Manter apenas a versão mais recente no índice** | Inviabiliza tratamento de chamados em transição (abertos antes de 01/12/2023). Pode gerar problemas legais se um chamado for calculado com a versão errada. |
| **Delegar inteiramente ao LLM** ("o modelo vai resolver") | Solução probabilística para um problema que exige precisão. O LLM pode misturar versões silenciosamente sem avisar o atendente. Inaceitável para cálculo de frete com impacto financeiro. |
| **Criar um único documento mesclado** | Não é função do pipeline de RAG editar documentos da NovaTech. Criaria um "documento fantasma" sem responsável formal, piorando o problema de governança. |
| **Bloquear o assistente para perguntas sobre documentos contraditórios** | O atendente ficaria sem suporte para 25% das queries de frete — derrota o propósito do projeto. |

---

## Devil's Advocate — Argumentos Contra (gerados com Claude)

**Argumento 1:** "Colocar a instrução de resolução de conflito no system prompt é frágil. Em conversas longas, o modelo pode 'esquecer' a instrução e misturar versões de qualquer forma."

*Resposta:* Correto — e por isso a solução é em três camadas, não só no prompt. A penalização de score no retrieval e a marcação `[VERSÃO LEGADA]` no texto dos chunks são mecanismos que atuam antes do LLM e são determinísticos. O system prompt é a terceira linha de defesa, não a única. O argumento reforça a importância de não depender apenas do prompt.

**Argumento 2:** "Mostrar ao atendente que existe uma versão contraditória vai confundi-lo. Ele vai ligar para o supervisor de qualquer jeito, derrotando o propósito do assistente."

*Resposta:* O atendente que recebe uma resposta aparentemente correta mas baseada na versão errada e cobra o cliente com o multiplicador 1.6 (v1) em vez de 1.8 (v2) gera um problema financeiro real. A confusão controlada (com aviso) é preferível ao erro silencioso. A frequência desse cenário deve cair rapidamente quando a NovaTech resolver a governança documental — o assistente é também um sinalizador de gaps no processo da empresa.

---

*Data da decisão: Junho/2025 | Autor: Tech Lead DB1 | Revisores: DM, PS, Dev*
