# Avaliação — Exercício 2.2: Arquitetura de MCP do projeto (servers locais)

**Trilha:** AI First DGS — DB1 Global Software  
**Cenário:** 2 — Fase de Estruturação do Trabalho  
**Papel:** Tech Lead  
**Avaliado em:** 20/06/2026  
**Avaliador:** Claude (Anthropic) via skill `avaliacao-foundation.md` + `avaliacao-tech-lead.md`

---

## Resumo

Entregável excepcional em todos os critérios do exercício. O documento de arquitetura trata MCP como infraestrutura gerenciada de verdade — com least privilege justificado, política de aprovação com critérios de recusa imediata, versionamento por changelog e plano de contingência diferenciado por server. O health check foi executado de fato (17/17 verificações, saída real documentada) e o script Python é funcional, cross-platform e bem estruturado. O nível de maturidade é consistente com o 3.0 do exercício 2.1.

---

## Scores por Dimensão

| Dimensão                       | Score | Justificativa                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ------------------------------ | :---: | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 — Domínio Conceitual        | **3** | Compreensão precisa das três primitivas MCP (Tools, Resources, Prompts) com distinção correta de RO vs RW por server. A justificativa de least privilege para `docs/novatech` e `data/retrieval-corpus` demonstra entendimento de que agentes com escrita na base documental representam risco de integridade do RAG — não é argumento genérico de segurança. Descarte correto de `uvx mcp-server-git` por incompatibilidade com Windows e substituição fundamentada. |
| D2 — Uso de Ferramentas        | **3** | Health check executado com saída real: 17/17 verificações passaram, com timestamp `2026-06-20 10:34:09`, paths absolutos e status por server. O script Python é funcional e foi rodado de fato em ambiente real Windows/PowerShell — a saída documenta inclusive o encoding issue de UTF-8 no path com acento.                                                                                                                                                        |
| D3 — Qualidade do Entregável   | **3** | Três artefatos completos e coerentes entre si: `docs/mcp-architecture.md` (ADR-0005 com arquitetura + política + versionamento + contingência), `scripts/mcp-health-check.py` funcional com docstring e exit codes, e `.mcp/mcp.json` com separação correta de servers e escopos. Diagrama ASCII preciso. Tabela de contingência acionável com comportamento do agente E ação do desenvolvedor por server.                                                            |
| D4 — Pensamento Crítico        | **3** | Seção de consequências honesta: identifica que `filesystem-rw` com acesso a `./src` completo é risco residual (mitigação via code review, não eliminação). Nota sobre `npx -y` sem pinagem como risco de quebra silenciosa com solução concreta (pinagem + revisão semestral). Regra de aviso para o agente quando `filesystem-ro` cai é específica ao domínio NovaTech, não genérica.                                                                                |
| D5 — Aplicabilidade ao Projeto | **3** | Documento nomeado ADR-0005, referenciando explicitamente ADR-0001, ADR-0004 e Anexo C. Escopo RO justificado em termos de integridade do RAG — conecta à decisão ADR-0004. Propagação para AGENTS.md v3 planejada explicitamente. Server `git` usa `@cyanheads/git-mcp-server` com justificativa de ambiente Windows documentada.                                                                                                                                     |

**Score do exercício: 3.0 / 3.0**

---

## Classificação

> ✅ **Aprovado com distinção** (score 2.5–3.0)

---

## Verificação do Health Check (critério obrigatório — D2)

O exercício exige evidência de execução real do script. Critério atendido:

| Verificação                          | Status | Evidência                                                                                           |
| ------------------------------------ | ------ | --------------------------------------------------------------------------------------------------- |
| Script executado de fato             | ✅     | Timestamp `2026-06-20 10:34:09` e paths absolutos Windows na saída                                  |
| 17/17 verificações passaram          | ✅     | filesystem-rw (7 escopos RW), filesystem-ro (2 escopos RO), git (repo + branch), memory, everything |
| Exit code documentado e implementado | ✅     | Código 0 (tudo OK) / 1 (falha) — docstring e implementação coerentes                                |
| Encoding UTF-8 em path com acento    | ⚠️     | `Prática` gerou `PrÃ¡tica` na saída do Git — script não falhou, mas exibiu string corrompida        |

---

## Artefatos Entregues

| Artefato                              | Tipo                     | Observação                                                         |
| ------------------------------------- | ------------------------ | ------------------------------------------------------------------ |
| `docs/mcp-architecture.md` (ADR-0005) | Documento de arquitetura | Arquitetura + política de aprovação + versionamento + contingência |
| `scripts/mcp-health-check.py`         | Script Python funcional  | Verificação por server, exit codes, suporte Windows/PowerShell     |
| `.mcp/mcp.json`                       | Configuração MCP         | 5 servers com separação correta de escopos RO/RW                   |
| `execucao-script.md`                  | Evidência de execução    | Saída real do terminal — 17/17 verificações                        |

---

## Pontos Fortes

**1. Least privilege com justificativa de negócio, não de segurança genérica**

A separação RO/RW é justificada em termos do domínio: agente com escrita em `docs/novatech` poderia corromper silenciosamente a base documental que fundamenta as respostas do RAG. Isso conecta a decisão de infraestrutura diretamente ao risco de produto.

**2. Plano de contingência diferenciado e acionável**

Cada server tem comportamento específico para o agente (o que dizer) e ação específica para o desenvolvedor (como resolver). O princípio "degradação com aviso, nunca alucinação" é a tradução correta do guardrail de RAG para o contexto de desenvolvimento — e está planejado para migrar ao AGENTS.md v3.

**3. Versionamento como processo, não como intenção**

A pinagem de versão dos pacotes com `@pacote/server@versão`, o `docs/mcp-changelog.md` com formato de entrada definido e o smoke test pós-mudança transformam versionamento em prática operacional concreta.

---

## Pontos de Melhoria

**1. Script não verifica que `filesystem-ro` rejeita escrita**

A tabela de monitoramento especifica: "Tentativa de escrita retorna erro?" para o `filesystem-ro`. O script verifica que as pastas RO são legíveis, mas não testa que escrita é bloqueada. Sugestão: adicionar teste de tentativa de escrita em `./docs/novatech` que espera falha — especialmente relevante porque a separação RO/RW é o principal guardrail de integridade do corpus.

**2. Encoding UTF-8 em paths Windows não tratado explicitamente**

O path `Prática 2 - V2` gerou saída corrompida do Git (`PrÃ¡tica`). Sugestão: adicionar `encoding="utf-8", errors="replace"` no subprocess e documentar no docstring que paths com acentos podem gerar saída ilegível em terminais sem suporte UTF-8 — relevante para outros membros do time em Windows.

**3. Política de aprovação sem SLA para emergências**

O fluxo define "1 dia útil" para revisão do Tech Lead, mas não cobre situações de bloqueio crítico. Sugestão: adicionar cláusula de aprovação expedita — ex: "para bloqueios críticos, TL pode aprovar verbalmente via canal do projeto com PR retroativo em até 24h" — tornando o processo mais ágil sem perder o controle.

---

## Tópicos da Trilha para Reforço

Nenhum. Score 3.0 — os três pontos de melhoria são refinamentos de um entregável já sólido, não gaps conceituais. Para o exercício 2.3 (Skills técnicas), o padrão de rigor e o ciclo empírico demonstrados nos exercícios 2.1 e 2.2 são o referencial correto.
