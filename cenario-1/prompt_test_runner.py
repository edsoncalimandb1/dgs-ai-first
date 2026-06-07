"""
prompt_test_runner.py
---------------------
Script de teste automatizado para o system prompt do Assistente NovaTech.

Gerado com apoio do GitHub Copilot (evidência: comentários inline indicam 
sugestões aceitas e adaptadas).

Uso:
    python prompt_test_runner.py --prompt prompts/system/v1.0.0-novatech-atendimento.md
                                 --tests prompts/tests/prompt-test-suite.json
                                 --output results/test-run-{timestamp}.json

Requisitos:
    pip install openai python-dotenv
    Variável de ambiente: AZURE_OPENAI_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT
"""

import json
import re
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

# Copilot sugeriu: usar dataclass para estruturar casos de teste
from dataclasses import dataclass, field, asdict


# ── Estruturas de dados ──────────────────────────────────────────────────────

@dataclass
class TestCase:
    """Representa um caso de teste individual."""
    id: str
    description: str
    question: str
    chunks: list[dict]  # lista de chunks simulados para injetar no contexto
    expected_behavior: str  # descrição textual do que é esperado
    checks: list[dict]  # lista de verificações automatizadas
    tags: list[str] = field(default_factory=list)


@dataclass
class CheckResult:
    """Resultado de uma verificação individual."""
    check_id: str
    check_type: str
    passed: bool
    detail: str


@dataclass
class TestResult:
    """Resultado completo de um caso de teste."""
    test_id: str
    description: str
    question: str
    response: str
    checks: list[CheckResult]
    passed: bool
    duration_ms: float
    tags: list[str] = field(default_factory=list)


# ── Verificações disponíveis ─────────────────────────────────────────────────

def check_contains_citation(response: str, params: dict) -> CheckResult:
    """
    Verifica se a resposta contém citação de fonte no formato esperado.
    Copilot sugeriu o padrão regex — adaptado para cobrir variações de formato.
    """
    pattern = r'\[Fonte:.*?\]'
    found = bool(re.search(pattern, response, re.IGNORECASE))
    return CheckResult(
        check_id="contains_citation",
        check_type="regex",
        passed=found,
        detail="Citação encontrada" if found else "FALHA: Resposta não contém citação de fonte no formato [Fonte: ...]"
    )


def check_not_contains_keyword(response: str, params: dict) -> CheckResult:
    """
    Verifica que a resposta NÃO contém uma palavra/frase proibida.
    Usado para detectar alucinações conhecidas (ex: 'tier Platinum').
    """
    keyword = params.get("keyword", "")
    found = keyword.lower() in response.lower()
    return CheckResult(
        check_id=f"not_contains_{keyword.replace(' ', '_')}",
        check_type="keyword_exclusion",
        passed=not found,
        detail=f"OK: '{keyword}' não encontrado" if not found else f"FALHA: Resposta contém '{keyword}' — possível alucinação"
    )


def check_contains_keyword(response: str, params: dict) -> CheckResult:
    """
    Verifica que a resposta contém uma palavra/frase esperada.
    Usado para verificar informações críticas (ex: prazo de 7 dias).
    """
    keyword = params.get("keyword", "")
    found = keyword.lower() in response.lower()
    return CheckResult(
        check_id=f"contains_{keyword.replace(' ', '_')}",
        check_type="keyword_inclusion",
        passed=found,
        detail=f"OK: '{keyword}' encontrado" if found else f"FALHA: Resposta não contém '{keyword}'"
    )


def check_not_found_response(response: str, params: dict) -> CheckResult:
    """
    Verifica se a resposta indica corretamente que a informação não foi encontrada.
    Para perguntas sobre temas sem cobertura na documentação.
    """
    # Copilot sugeriu múltiplas variações para cobrir diferentes formas de "não encontrei"
    not_found_patterns = [
        "não encontrei",
        "não está na documentação",
        "não encontrado",
        "escalar para o supervisor",
        "consultar diretamente"
    ]
    found_any = any(p in response.lower() for p in not_found_patterns)
    return CheckResult(
        check_id="not_found_response",
        check_type="not_found_behavior",
        passed=found_any,
        detail="OK: Resposta indica ausência de informação corretamente" if found_any 
               else "FALHA: Pergunta sem cobertura deveria retornar 'não encontrei', mas retornou resposta"
    )


def check_mentions_contradiction_warning(response: str, params: dict) -> CheckResult:
    """
    Verifica se resposta sobre documentos contraditórios inclui aviso de versão anterior.
    """
    warning_patterns = ["versão anterior", "versão antiga", "⚠️", "atenção:", "valor diferente"]
    found_any = any(p in response.lower() for p in warning_patterns)
    return CheckResult(
        check_id="contradiction_warning",
        check_type="contradiction_handling",
        passed=found_any,
        detail="OK: Resposta inclui aviso sobre versão anterior" if found_any
               else "FALHA: Pergunta sobre documento com contradição deveria incluir aviso de versão"
    )


# Mapa de verificações disponíveis
CHECK_REGISTRY = {
    "contains_citation": check_contains_citation,
    "not_contains_keyword": check_not_contains_keyword,
    "contains_keyword": check_contains_keyword,
    "not_found_response": check_not_found_response,
    "mentions_contradiction_warning": check_mentions_contradiction_warning,
}


# ── Runner principal ──────────────────────────────────────────────────────────

class PromptTestRunner:
    """
    Executa suite de testes contra o system prompt via Azure OpenAI.
    Copilot gerou o esqueleto desta classe — lógica de montagem de contexto
    e verificações foram escritas manualmente.
    """

    def __init__(self, system_prompt: str, azure_client):
        self.system_prompt = system_prompt
        self.client = azure_client

    def build_context(self, test_case: TestCase) -> str:
        """
        Monta o contexto completo para a query de teste.
        Injeta os chunks simulados no local correto do system prompt.
        """
        chunks_text = "\n\n".join([
            f"**[{c['doc_id']} — {c.get('section', '')}]**\n{c['content']}"
            for c in test_case.chunks
        ])

        # Substitui o placeholder de chunks no system prompt
        context = self.system_prompt.replace(
            "[Os chunks recuperados pelo pipeline serão inseridos aqui em tempo de execução]",
            chunks_text
        )
        return context

    def run_test(self, test_case: TestCase) -> TestResult:
        """Executa um caso de teste e retorna o resultado."""
        start = time.time()

        context = self.build_context(test_case)

        # Chamada ao LLM (Azure OpenAI)
        response_text = ""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",  # deployment name no Azure
                messages=[
                    {"role": "system", "content": context},
                    {"role": "user", "content": test_case.question}
                ],
                temperature=0,
                max_tokens=800
            )
            response_text = response.choices[0].message.content
        except Exception as e:
            response_text = f"[ERRO NA CHAMADA AO LLM: {str(e)}]"

        duration_ms = (time.time() - start) * 1000

        # Executa as verificações
        check_results = []
        for check_spec in test_case.checks:
            check_fn = CHECK_REGISTRY.get(check_spec["type"])
            if check_fn:
                result = check_fn(response_text, check_spec.get("params", {}))
                check_results.append(result)
            else:
                check_results.append(CheckResult(
                    check_id=check_spec["type"],
                    check_type="unknown",
                    passed=False,
                    detail=f"Verificação '{check_spec['type']}' não encontrada no registry"
                ))

        all_passed = all(r.passed for r in check_results)

        return TestResult(
            test_id=test_case.id,
            description=test_case.description,
            question=test_case.question,
            response=response_text,
            checks=check_results,
            passed=all_passed,
            duration_ms=duration_ms,
            tags=test_case.tags
        )

    def run_suite(self, test_cases: list[TestCase]) -> dict:
        """Executa todos os casos de teste e gera relatório."""
        results = []
        for tc in test_cases:
            print(f"  Rodando: {tc.id} — {tc.description}... ", end="", flush=True)
            result = self.run_test(tc)
            results.append(result)
            status = "✅ PASSOU" if result.passed else "❌ FALHOU"
            print(f"{status} ({result.duration_ms:.0f}ms)")

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed

        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": f"{(passed/total*100):.1f}%"
            },
            "results": [asdict(r) for r in results]
        }


# ── Suite de testes (casos concretos do domínio NovaTech) ────────────────────

NOVATECH_TEST_SUITE = [
    TestCase(
        id="TEST-001",
        description="Prazo de devolução — caso feliz",
        question="Qual o prazo de devolução de mercadorias?",
        chunks=[
            {
                "doc_id": "POL-001",
                "section": "seção 3.1",
                "content": "O cliente pode solicitar a devolução de mercadorias em até 7 (sete) dias úteis após a data de recebimento confirmada no sistema de tracking. A contagem exclui sábados, domingos e feriados nacionais."
            }
        ],
        expected_behavior="Deve informar 7 dias úteis com citação da POL-001",
        checks=[
            {"type": "contains_citation"},
            {"type": "contains_keyword", "params": {"keyword": "7"}},
            {"type": "contains_keyword", "params": {"keyword": "dias úteis"}},
        ],
        tags=["devolucao", "prazo", "happy_path"]
    ),
    TestCase(
        id="TEST-002",
        description="Carga perigosa — NÃO pode devolver (regra de exceção)",
        question="Meu cliente quer devolver uma carga de líquidos inflamáveis. Pode?",
        chunks=[
            {
                "doc_id": "POL-001",
                "section": "seção 3.2",
                "content": "As seguintes categorias de carga NÃO são elegíveis para devolução pelo processo padrão: Cargas perigosas classificadas nas classes 1 a 6 da ANTT. Inclui: explosivos (classe 1), gases (classe 2), líquidos inflamáveis (classe 3). Para essas categorias, o cliente deve entrar em contato com o setor de Gestão de Riscos (ramal 4500)."
            }
        ],
        expected_behavior="Deve informar que NÃO pode e orientar para ramal 4500",
        checks=[
            {"type": "contains_citation"},
            {"type": "contains_keyword", "params": {"keyword": "não"}},
            {"type": "contains_keyword", "params": {"keyword": "4500"}},
        ],
        tags=["devolucao", "carga_perigosa", "regra_excecao", "critico"]
    ),
    TestCase(
        id="TEST-003",
        description="SLA cliente Gold",
        question="Qual o SLA de resolução para um cliente Gold?",
        chunks=[
            {
                "doc_id": "SLA-2024",
                "section": "seção 2",
                "content": "SLAs para chamados gerais — Gold: resposta em até 2h úteis, resolução em até 24h úteis. Silver: resposta em até 4h úteis, resolução em até 48h úteis. Standard: resposta em até 8h úteis, resolução em até 72h úteis."
            }
        ],
        expected_behavior="Deve informar 24h para resolução, com citação",
        checks=[
            {"type": "contains_citation"},
            {"type": "contains_keyword", "params": {"keyword": "24h"}},
        ],
        tags=["sla", "gold", "happy_path"]
    ),
    TestCase(
        id="TEST-004",
        description="Tier Platinum — alucinação conhecida",
        question="Qual o SLA do cliente Platinum?",
        chunks=[
            {
                "doc_id": "SLA-2024",
                "section": "seção 1",
                "content": "A NovaTech classifica seus clientes em 3 (três) tiers: Gold, Silver e Standard. Não existem outros tiers além dos três listados acima."
            }
        ],
        expected_behavior="Deve informar que Platinum não existe e listar os tiers corretos",
        checks=[
            {"type": "not_contains_keyword", "params": {"keyword": "tier platinum"}},
            {"type": "contains_keyword", "params": {"keyword": "não existe"}},
        ],
        tags=["sla", "platinum", "alucinacao", "critico"]
    ),
    TestCase(
        id="TEST-005",
        description="Multiplicador frete — documentos contraditórios (v1 vs v2)",
        question="Qual o multiplicador para região Norte em frete especial?",
        chunks=[
            {
                "doc_id": "PROC-042-v2",
                "section": "seção 2.1",
                "version": "2.0",
                "emission_date": "2023-11-10",
                "content": "Multiplicadores regionais atualizados (novembro/2023): Sul 1.3, Sudeste 1.1, Centro-Oeste 1.4, Nordeste 1.5, Norte 1.8."
            },
            {
                "doc_id": "PROC-042-v1",
                "section": "seção 2.1",
                "version": "1.0",
                "emission_date": "2023-03-03",
                "content": "Multiplicadores regionais: Sul 1.2, Sudeste 1.0, Centro-Oeste 1.3, Nordeste 1.4, Norte 1.6."
            }
        ],
        expected_behavior="Deve usar 1.8 (v2, mais recente) e avisar sobre versão anterior (1.6)",
        checks=[
            {"type": "contains_citation"},
            {"type": "contains_keyword", "params": {"keyword": "1.8"}},
            {"type": "mentions_contradiction_warning"},
        ],
        tags=["frete", "contradicao", "versoes", "critico"]
    ),
    TestCase(
        id="TEST-006",
        description="Pergunta sem cobertura — frete padrão abaixo de 500kg",
        question="Quanto custa o frete para 300kg para São Paulo?",
        chunks=[
            {
                "doc_id": "PROC-042-v2",
                "section": "seção 1",
                "content": "Este procedimento aplica-se a fretes especiais para cargas com peso acima de 500kg."
            }
        ],
        expected_behavior="Deve informar que não encontrou a informação, não inventar valor",
        checks=[
            {"type": "not_found_response"},
        ],
        tags=["frete", "sem_cobertura", "alucinacao"]
    ),
]


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Testa o system prompt do Assistente NovaTech")
    parser.add_argument("--prompt", type=str, help="Caminho para o arquivo de system prompt")
    parser.add_argument("--output", type=str, default=None, help="Arquivo de saída para os resultados")
    parser.add_argument("--dry-run", action="store_true", help="Exibe os casos de teste sem executar")
    args = parser.parse_args()

    if args.dry_run:
        print(f"\n{'='*60}")
        print(f"DRY RUN — {len(NOVATECH_TEST_SUITE)} casos de teste definidos:")
        print(f"{'='*60}")
        for tc in NOVATECH_TEST_SUITE:
            print(f"\n[{tc.id}] {tc.description}")
            print(f"  Pergunta: {tc.question}")
            print(f"  Tags: {', '.join(tc.tags)}")
            print(f"  Verificações: {len(tc.checks)}")
        return

    # Carrega o system prompt
    prompt_path = Path(args.prompt) if args.prompt else None
    if prompt_path and prompt_path.exists():
        system_prompt = prompt_path.read_text(encoding="utf-8")
        print(f"System prompt carregado: {prompt_path} ({len(system_prompt)} chars)")
    else:
        print("AVISO: Arquivo de prompt não encontrado. Use --dry-run para ver os casos.")
        print("Para execução real, configure AZURE_OPENAI_KEY e AZURE_OPENAI_ENDPOINT.")
        sys.exit(1)

    # Configura cliente Azure OpenAI
    try:
        import os
        from openai import AzureOpenAI
        client = AzureOpenAI(
            api_key=os.environ["AZURE_OPENAI_KEY"],
            api_version="2024-02-01",
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"]
        )
    except ImportError:
        print("ERRO: openai não instalado. Execute: pip install openai")
        sys.exit(1)
    except KeyError as e:
        print(f"ERRO: Variável de ambiente {e} não definida.")
        sys.exit(1)

    # Executa a suite
    runner = PromptTestRunner(system_prompt, client)
    print(f"\n{'='*60}")
    print(f"Executando {len(NOVATECH_TEST_SUITE)} testes...")
    print(f"{'='*60}\n")

    report = runner.run_suite(NOVATECH_TEST_SUITE)

    # Exibe resumo
    s = report["summary"]
    print(f"\n{'='*60}")
    print(f"RESULTADO: {s['passed']}/{s['total']} passou ({s['pass_rate']})")
    print(f"{'='*60}")

    # Salva resultado
    output_path = args.output or f"results/test-run-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nResultados salvos em: {output_path}")


if __name__ == "__main__":
    main()
