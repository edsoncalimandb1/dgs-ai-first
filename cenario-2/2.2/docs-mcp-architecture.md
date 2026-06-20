# ADR-0005 — Arquitetura de MCP do Projeto NovaTech Assistant

**Status:** Aceito  
**Data:** Fase de Estruturação (Cenário 2)  
**Responsável:** Tech Lead  
**Referências:** ADR-0001 (escolha do LLM), ADR-0004 (build vs buy), Anexo C (estrutura do repositório)

---

## Contexto

O projeto usa agentes de IA (GitHub Copilot, Claude Code) para geração de código, specs e artefatos. Para que esses agentes operem com contexto real do projeto — lendo documentação, consultando histórico Git, acessando specs — precisam de conexões estruturadas a dados e ferramentas locais.

O Model Context Protocol (MCP) padroniza essas conexões: cada server expõe **Tools** (ações que o agente pode invocar), **Resources** (dados read-only que o agente pode ler) e **Prompts** (templates pré-configurados). Todos os servers desta fase rodam **localmente via `npx`** — nenhum serviço pago ou externo é necessário.

O Tech Lead é responsável por decidir quais servers são autorizados, com quais escopos, e como o time é avisado de mudanças.

---

## Decisão: 5 servers locais em 2 grupos de permissão

### Diagrama de arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│  Agentes de IA                                                   │
│  ┌─────────────────────┐    ┌──────────────────────────────┐    │
│  │   GitHub Copilot    │    │        Claude Code           │    │
│  └──────────┬──────────┘    └──────────────┬───────────────┘    │
└─────────────┼─────────────────────────────┼───────────────────-─┘
              │ MCP Protocol                 │ MCP Protocol
              ▼                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  MCP Servers (.mcp/mcp.json)                                     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  GRUPO RW — leitura e escrita                            │   │
│  │                                                          │   │
│  │  filesystem-rw                                           │   │
│  │  Escopos: ./src  ./specs  ./skills  ./prompts            │   │
│  │           ./docs/adr  ./tests                            │   │
│  │  Tools: read_file, write_file, list_directory,           │   │
│  │         create_directory, move_file, search_files        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  GRUPO RO — somente leitura (documentação de negócio)    │   │
│  │                                                          │   │
│  │  filesystem-ro                                           │   │
│  │  Escopos: ./docs/novatech  ./data/retrieval-corpus       │   │
│  │  Tools: read_file, list_directory, search_files          │   │
│  │  Sem write_file, create_directory, move_file             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │     git      │  │    memory    │  │       everything      │ │
│  │              │  │              │  │                       │ │
│  │ Histórico,   │  │ Grafo de     │  │ Exploração de         │ │
│  │ diff,        │  │ decisões e   │  │ primitivas MCP        │ │
│  │ branches     │  │ ling. ubíqua │  │ (aprendizado)         │ │
│  └──────────────┘  └──────────────┘  └───────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
              │                    │
              ▼                    ▼
┌─────────────────┐    ┌──────────────────────────┐
│  Repositório    │    │  Grafo persistente local  │
│  local Git      │    │  (~/.mcp-memory/)         │
└─────────────────┘    └──────────────────────────┘
```

### Mapeamento: necessidade → server → escopo

| Necessidade do projeto | Server | Escopo | Permissão |
|---|---|---|---|
| Gerar/editar código fonte | `filesystem-rw` | `./src` | RW |
| Criar/editar specs SDD | `filesystem-rw` | `./specs` | RW |
| Criar/editar skills | `filesystem-rw` | `./skills` | RW |
| Gerenciar system prompts | `filesystem-rw` | `./prompts` | RW |
| Criar ADRs | `filesystem-rw` | `./docs/adr` | RW |
| Criar/editar testes | `filesystem-rw` | `./tests` | RW |
| Ler documentação NovaTech | `filesystem-ro` | `./docs/novatech` | **RO** |
| Consultar chunks de referência (RAG) | `filesystem-ro` | `./data/retrieval-corpus` | **RO** |
| Histórico de commits, diffs, branches | `git` | repositório local | RO |
| Glossário e decisões persistentes | `memory` | grafo local | RW |
| Aprendizado das primitivas MCP | `everything` | — | RO |

### Justificativa do least privilege

**Por que `docs/novatech` e `data/retrieval-corpus` são read-only?**

Esses diretórios contêm a fonte de verdade do negócio (documentação oficial da NovaTech) e o corpus de referência do pipeline de RAG. Um agente com escrita nesses diretórios poderia silenciosamente alterar a base documental que fundamenta as respostas do assistente — um risco de integridade crítico. A separação em `filesystem-ro` garante que:

1. O agente pode *consultar* a documentação para gerar código correto (ex: validar que um guardrail está alinhado com a POL-001).
2. O agente *não pode* modificar os documentos-fonte, preservando a rastreabilidade e integridade do corpus.

**Por que `filesystem-rw` não inclui `./infra`, `./data` (raiz) e `./docs` (raiz)?**

- `./infra` — contém Bicep que provisiona recursos Azure reais. Modificação por agente sem gate humano é risco operacional inaceitável.
- `./data` (raiz) — inclui `retrieval-corpus` que é RO; dar RW à raiz quebraria o least privilege.
- `./docs` (raiz) — inclui `docs/novatech` RO e `docs/runbooks`. Runbooks são documentação operacional — mudanças devem ter revisão humana.

---

## Política de aprovação para novos servers

### Fluxo de adição de um novo MCP server

```
Dev ou TL identifica necessidade
         │
         ▼
Abrir PR com proposta (docs/pull-requests/PR-NNNN.md) contendo:
  - Nome e pacote npm do server
  - Justificativa da necessidade
  - Escopos solicitados (pastas/recursos)
  - Nível de permissão (RO ou RW) por escopo
  - Análise de least privilege: por que não usar um server já existente?
  - Riscos identificados (ex: acesso a .env, escrita em arquivos críticos)
         │
         ▼
Tech Lead revisa em até 1 dia útil:
  - Verifica se o escopo solicitado é o mínimo suficiente
  - Verifica se o pacote npm é mantido ativamente (último release < 6 meses)
  - Verifica se não há sobreposição com servers existentes
  - Testa o server localmente antes de aprovar
         │
    ┌────┴────┐
    │         │
  Aprova   Recusa (propor alternativa ou escopo menor)
    │
    ▼
Merge do PR → mcp.json atualizado → notificar time no canal do projeto
```

### Critérios de recusa imediata

Um server é recusado imediatamente se:
- Solicita escopo de escrita em `.env`, `infra/`, `docs/novatech/` ou `data/retrieval-corpus/`
- O pacote npm não tem manutenção ativa ou tem vulnerabilidades conhecidas
- Duplica funcionalidade de server já aprovado (usar escopo menor no existente)
- Requer credenciais ou tokens externos (esta fase é 100% local)

---

## Monitoramento e health check

### O que verificar

Para cada server no `mcp.json`, o health check valida:

| Server | Verificação |
|---|---|
| `filesystem-rw` | Consegue listar `./src` e `./specs`? Consegue criar e deletar um arquivo temporário em `./src`? |
| `filesystem-ro` | Consegue listar `./docs/novatech`? Tentativa de escrita retorna erro? |
| `git` | Consegue retornar o hash do último commit? Consegue listar branches? |
| `memory` | Server responde ao handshake MCP? |
| `everything` | Server responde e lista suas tools? |

### Script de health check

Ver arquivo `scripts/mcp-health-check.py` — execução com `python scripts/mcp-health-check.py`.

O script verifica cada server de forma sequencial, reporta status por server, e retorna exit code 0 (tudo OK) ou 1 (algum server falhou).

### Quando rodar o health check

- **Obrigatório:** antes de iniciar uma sessão de desenvolvimento que usa agentes (Copilot, Claude Code)
- **Obrigatório:** após qualquer mudança no `mcp.json`
- **Recomendado:** ao retomar o trabalho após reboot da máquina

---

## Versionamento do mcp.json

### Estratégia

O `mcp.json` é versionado no Git como qualquer outro arquivo do repositório. Toda mudança de escopo passa pelo fluxo de PR descrito acima.

### Como garantir que mudanças não quebram fluxos existentes

**1. Changelog de escopos**

Toda mudança no `mcp.json` DEVE ser acompanhada de entrada no arquivo `docs/mcp-changelog.md`:

```markdown
## 2025-06-20 — filesystem-rw: adicionado ./docs/adr ao escopo
- Motivo: agentes precisam ler ADRs existentes antes de criar novos
- Impacto: nenhum fluxo existente afetado (só adição de escopo)
- Aprovado por: Tech Lead
- PR: PR-0003
```

**2. Smoke test pós-mudança**

Após qualquer mudança, rodar `python scripts/mcp-health-check.py` e confirmar que todos os servers passam antes de fazer merge.

**3. Pinagem de versão dos pacotes**

Os servidores são invocados via `npx -y @pacote/server` — o `-y` aceita automaticamente a versão mais recente. Para evitar quebras silenciosas por atualização de pacote, fixar versão explicitamente após validação inicial:

```json
"args": ["-y", "@modelcontextprotocol/server-filesystem@0.6.2", ...]
```

Revisão semestral das versões pinadas para incorporar atualizações de segurança.

---

## Plano de contingência — server indisponível

### Princípio: degradação com aviso, nunca alucinação

Quando um server MCP fica indisponível durante o desenvolvimento, o agente NÃO deve tentar completar a tarefa inventando informação. Deve parar, avisar, e aguardar resolução humana.

### Por server

| Server indisponível | Comportamento esperado do agente | Ação do desenvolvedor |
|---|---|---|
| `filesystem-rw` | Parar geração de código. Avisar: *"Não consigo acessar o código-fonte. Verifique o server filesystem-rw."* | Rodar health check. Verificar se pasta `./src` existe. Reiniciar Copilot/Claude Code. |
| `filesystem-ro` | Avisar: *"Não consigo acessar a documentação NovaTech. Respostas sobre domínio de logística podem estar incompletas."* Continuar com o que sabe do contexto da sessão, mas **sem inventar regras de negócio**. | Verificar se `./docs/novatech/` e `./data/retrieval-corpus/` existem no repo. |
| `git` | Continuar sem contexto de histórico. Avisar: *"Histórico Git indisponível — não consigo verificar decisões anteriores."* | Rodar health check. Verificar se o diretório é um repositório Git válido (`git status`). |
| `memory` | Continuar sem persistência de decisões. Avisar: *"Memória de projeto indisponível — decisões desta sessão não serão persistidas."* | Reiniciar o server manualmente via `npx @modelcontextprotocol/server-memory`. |
| `everything` | Ignorar — server de aprendizado, não crítico para desenvolvimento. | Nenhuma ação necessária. |

### Regra geral para o agente

> Se um MCP server que fornece contexto de domínio (filesystem-ro, memory) estiver indisponível, o agente DEVE prefixar qualquer resposta relacionada ao domínio NovaTech com: *"⚠️ Documentação de domínio indisponível. Esta resposta é baseada apenas no contexto da sessão atual e pode estar incompleta ou imprecisa."*

Essa regra deve ser incluída no AGENTS.md (seção a ser adicionada na v3 após o exercício 2.3).

---

## Consequências desta decisão

**Positivo:**
- Agentes operam com contexto real e atualizado do projeto sem acesso à internet
- Least privilege concreto: documentação de negócio protegida de escrita acidental
- Observabilidade via health check executável — falhas detectadas antes de afetar produtividade
- Versionamento no Git garante rastreabilidade de toda mudança de escopo

**Negativo / riscos residuais:**
- `filesystem-rw` com acesso a `./src` completo ainda permite ao agente modificar qualquer arquivo de código sem gate adicional — mitigação via code review obrigatório (Gate 3 do AGENTS.md)
- Server `git` via `@cyanheads/git-mcp-server` é alternativa ao `uvx mcp-server-git` — validar funcionamento no Windows antes de assumir paridade total
- `npx -y` sem versão pinada pode baixar versão incompatível — mitigar com pinagem após validação inicial

## Alternativas consideradas

**uvx mcp-server-git (descartado para Windows sem uv)**  
O Anexo C referencia `uvx mcp-server-git` como server Git padrão. Como o ambiente é Windows sem `uv`/`uvx` instalado, substituído por `@cyanheads/git-mcp-server` via `npx`. Funcionalidade equivalente.

**Um único filesystem server com todos os escopos (descartado)**  
Simplificaria o `mcp.json`, mas eliminaria o least privilege sobre a documentação de negócio. O risco de um agente modificar `docs/novatech/` acidentalmente é inaceitável dado que esses documentos são a fonte de verdade do RAG.

**Docker containers para cada server (descartado nesta fase)**  
Melhoraria o isolamento e o controle de versão dos servers, mas adiciona complexidade operacional desnecessária para uma equipe pequena em fase de estruturação. Reavaliar quando o projeto escalar para múltiplos devs.
