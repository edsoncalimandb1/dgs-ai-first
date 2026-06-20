"""
mcp-health-check.py — NovaTech Assistant
Verifica se os MCP servers configurados em .mcp/mcp.json estão respondendo.

Uso:
    python scripts/mcp-health-check.py
    python scripts/mcp-health-check.py --verbose

Retorna:
    Exit code 0 — todos os servers OK
    Exit code 1 — um ou mais servers com falha

Nota: este script NÃO sobe os servers — ele verifica se os pacotes npm
estão disponíveis e se as pastas de escopo existem e são acessíveis.
Para verificação de protocolo MCP completa, use Claude Desktop ou
VS Code com Copilot Chat com os servers configurados.
"""

import json
import os
import subprocess
import sys
import argparse
from pathlib import Path
from datetime import datetime

# ── Configuração ────────────────────────────────────────────────────────────

MCP_CONFIG_PATH = Path(".mcp/mcp.json")
REPO_ROOT = Path(".")

# No Windows, npm é instalado como npm.cmd — subprocess.run(["npm"]) falha
# porque procura npm.exe. Detectamos qual forma usar uma vez e reutilizamos.
def _resolve_npm_cmd() -> tuple[list[str], bool]:
    """Retorna (comando_npm, usar_shell). Shell=True é fallback para Windows."""
    if sys.platform == "win32":
        # Tenta npm.cmd primeiro (forma correta no Windows)
        for candidate in ["npm.cmd", "npm"]:
            try:
                r = subprocess.run([candidate, "--version"],
                                   capture_output=True, text=True, timeout=10)
                if r.returncode == 0:
                    return [candidate], False
            except FileNotFoundError:
                continue
        # Último recurso: shell=True deixa o CMD resolver o PATH
        return ["npm"], True
    return ["npm"], False

_NPM_CMD, _NPM_SHELL = _resolve_npm_cmd()

# Cores para terminal Windows (funciona no Windows Terminal e PowerShell 7+)
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
GRAY   = "\033[90m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def color(text: str, code: str) -> str:
    """Aplica cor se o terminal suportar."""
    if sys.stdout.isatty() or os.environ.get("FORCE_COLOR"):
        return f"{code}{text}{RESET}"
    return text

def ok(msg: str) -> str:
    return color(f"  ✓ {msg}", GREEN)

def fail(msg: str) -> str:
    return color(f"  ✗ {msg}", RED)

def warn(msg: str) -> str:
    return color(f"  ⚠ {msg}", YELLOW)

def info(msg: str) -> str:
    return color(f"  → {msg}", GRAY)

# ── Verificações por server ──────────────────────────────────────────────────

def check_npm_package_available(package_name: str) -> tuple[bool, str]:
    """Verifica se um pacote npm pode ser resolvido (sem instalar)."""
    try:
        result = subprocess.run(
            [*_NPM_CMD, "show", package_name, "version"],
            capture_output=True, text=True, timeout=15,
            shell=_NPM_SHELL
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return True, f"versão {version} disponível no registry"
        return False, f"pacote não encontrado: {result.stderr.strip()[:80]}"
    except subprocess.TimeoutExpired:
        return False, "timeout ao consultar npm registry (sem internet?)"
    except FileNotFoundError:
        return False, f"npm não encontrado no PATH — tente rodar 'npm --version' no terminal para confirmar instalação"

def check_directory_readable(path: str) -> tuple[bool, str]:
    """Verifica se um diretório existe e é legível."""
    p = REPO_ROOT / path
    if not p.exists():
        return False, f"diretório não existe: {p.resolve()}"
    if not p.is_dir():
        return False, f"não é um diretório: {p.resolve()}"
    try:
        files = list(p.iterdir())
        return True, f"{len(files)} itens em {p.resolve()}"
    except PermissionError:
        return False, f"sem permissão de leitura: {p.resolve()}"

def check_directory_writable(path: str) -> tuple[bool, str]:
    """Verifica se um diretório existe e é gravável (cria e remove arquivo temporário)."""
    p = REPO_ROOT / path
    if not p.exists():
        return False, f"diretório não existe: {p.resolve()}"
    test_file = p / ".mcp-healthcheck-tmp"
    try:
        test_file.write_text("health check")
        test_file.unlink()
        return True, f"leitura e escrita OK em {p.resolve()}"
    except PermissionError:
        return False, f"sem permissão de escrita: {p.resolve()}"
    except Exception as e:
        return False, f"erro inesperado: {e}"

def check_git_repo() -> tuple[bool, str]:
    """Verifica se o diretório atual é um repositório Git válido."""
    use_shell = sys.platform == "win32"
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=10,
            shell=use_shell
        )
        if result.returncode == 0:
            root = result.stdout.strip()
            log = subprocess.run(
                ["git", "log", "--oneline", "-1"],
                capture_output=True, text=True, timeout=10,
                shell=use_shell
            )
            last_commit = log.stdout.strip() or "(sem commits ainda)"
            return True, f"repo em {root} | último commit: {last_commit}"
        return False, "não é um repositório Git"
    except FileNotFoundError:
        return False, "git não encontrado no PATH"
    except subprocess.TimeoutExpired:
        return False, "timeout ao consultar git"

def check_git_branches() -> tuple[bool, str]:
    """Lista branches do repositório."""
    use_shell = sys.platform == "win32"
    try:
        result = subprocess.run(
            ["git", "branch", "--list"],
            capture_output=True, text=True, timeout=10,
            shell=use_shell
        )
        if result.returncode == 0:
            branches = [b.strip().lstrip("* ") for b in result.stdout.strip().splitlines() if b.strip()]
            if branches:
                return True, f"branches: {', '.join(branches)}"
            return True, "repositório sem branches (apenas inicializado)"
        return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)

# ── Verificadores por server ─────────────────────────────────────────────────

def verify_filesystem_rw(config: dict, verbose: bool) -> list[tuple[bool, str]]:
    results = []

    package = None
    for arg in config.get("args", []):
        if arg.startswith("@modelcontextprotocol/server-filesystem"):
            package = arg.split("@")[0] + "@" + arg.split("@")[1] if arg.count("@") > 1 else "@modelcontextprotocol/server-filesystem"
            break

    if not package:
        package = "@modelcontextprotocol/server-filesystem"

    ok_npm, msg_npm = check_npm_package_available("@modelcontextprotocol/server-filesystem")
    results.append((ok_npm, f"pacote npm: {msg_npm}"))

    rw_scopes = [a for a in config.get("args", []) if a.startswith("./")]
    for scope in rw_scopes:
        ok_w, msg_w = check_directory_writable(scope)
        results.append((ok_w, f"escopo RW {scope}: {msg_w}"))

    return results

def verify_filesystem_ro(config: dict, verbose: bool) -> list[tuple[bool, str]]:
    results = []

    ok_npm, msg_npm = check_npm_package_available("@modelcontextprotocol/server-filesystem")
    results.append((ok_npm, f"pacote npm: {msg_npm}"))

    ro_scopes = [a for a in config.get("args", []) if a.startswith("./")]
    for scope in ro_scopes:
        ok_r, msg_r = check_directory_readable(scope)
        results.append((ok_r, f"escopo RO {scope}: {msg_r}"))

    return results

def verify_git(config: dict, verbose: bool) -> list[tuple[bool, str]]:
    results = []

    # Verifica se o pacote alternativo para Windows está disponível
    pkg = "@cyanheads/git-mcp-server"
    for arg in config.get("args", []):
        if arg.startswith("@"):
            pkg = arg
            break
    ok_npm, msg_npm = check_npm_package_available(pkg)
    results.append((ok_npm, f"pacote npm {pkg}: {msg_npm}"))

    ok_git, msg_git = check_git_repo()
    results.append((ok_git, f"repositório Git: {msg_git}"))

    ok_br, msg_br = check_git_branches()
    results.append((ok_br, f"branches: {msg_br}"))

    return results

def verify_memory(config: dict, verbose: bool) -> list[tuple[bool, str]]:
    results = []
    ok_npm, msg_npm = check_npm_package_available("@modelcontextprotocol/server-memory")
    results.append((ok_npm, f"pacote npm: {msg_npm}"))
    results.append((True, "grafo persistente: inicializado sob demanda na primeira execução"))
    return results

def verify_everything(config: dict, verbose: bool) -> list[tuple[bool, str]]:
    results = []
    ok_npm, msg_npm = check_npm_package_available("@modelcontextprotocol/server-everything")
    results.append((ok_npm, f"pacote npm: {msg_npm}"))
    results.append((True, "server de aprendizado — não crítico para desenvolvimento"))
    return results

# ── Dispatcher ───────────────────────────────────────────────────────────────

SERVER_VERIFIERS = {
    "filesystem-rw":  verify_filesystem_rw,
    "filesystem-ro":  verify_filesystem_ro,
    "filesystem":     verify_filesystem_rw,   # alias para config com server único
    "git":            verify_git,
    "memory":         verify_memory,
    "everything":     verify_everything,
}

# ── Runner principal ─────────────────────────────────────────────────────────

def run_health_check(verbose: bool = False) -> int:
    print()
    print(color("=" * 60, BLUE))
    print(color(f"  NovaTech Assistant — MCP Health Check", BOLD))
    print(color(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", GRAY))
    print(color("=" * 60, BLUE))
    print()

    # Carrega mcp.json
    if not MCP_CONFIG_PATH.exists():
        print(fail(f"Arquivo não encontrado: {MCP_CONFIG_PATH}"))
        print(info("Crie o arquivo .mcp/mcp.json antes de rodar o health check."))
        return 1

    with open(MCP_CONFIG_PATH, encoding="utf-8") as f:
        config = json.load(f)

    servers = config.get("mcpServers", {})
    if not servers:
        print(warn("Nenhum server configurado em mcpServers"))
        return 1

    total_checks = 0
    failed_checks = 0
    server_results: dict[str, tuple[bool, list]] = {}

    for server_name, server_config in servers.items():
        print(color(f"  [{server_name}]", BOLD))

        verifier = SERVER_VERIFIERS.get(server_name)
        if not verifier:
            print(warn(f"Nenhum verificador definido para '{server_name}' — pulando"))
            print()
            continue

        checks = verifier(server_config, verbose)
        server_ok = True

        for check_ok, check_msg in checks:
            total_checks += 1
            if check_ok:
                print(ok(check_msg))
            else:
                print(fail(check_msg))
                failed_checks += 1
                server_ok = False

        server_results[server_name] = (server_ok, checks)
        print()

    # Resumo
    print(color("─" * 60, GRAY))
    passed = total_checks - failed_checks
    status_color = GREEN if failed_checks == 0 else RED
    print(color(f"  Resultado: {passed}/{total_checks} verificações passaram", status_color))
    print()

    # Servidores com falha
    failed_servers = [name for name, (ok_s, _) in server_results.items() if not ok_s]
    if failed_servers:
        print(color("  Servers com problemas:", YELLOW))
        for name in failed_servers:
            print(color(f"    • {name}", RED))
            # Plano de contingência
            contingency = {
                "filesystem-rw": "Verifique se as pastas ./src ./specs ./skills ./prompts ./docs/adr ./tests existem no repositório.",
                "filesystem-ro": "Verifique se ./docs/novatech e ./data/retrieval-corpus existem. Rode o starter repo setup se necessário.",
                "git":           "Verifique se o diretório é um repositório Git válido. Rode 'git init' se necessário.",
                "memory":        "Server inicializado sob demanda. Se falhar, verifique npm e conectividade.",
                "everything":    "Server não crítico. Pode ser ignorado para desenvolvimento normal.",
            }
            if name in contingency:
                print(info(f"  → {contingency[name]}"))
        print()
        print(color("  ⚠ Agente deve degradar com aviso — não inventar informação.", YELLOW))
        print(color("    Ver docs/mcp-architecture.md seção 'Plano de contingência'.", GRAY))
        print()
        return 1

    print(color("  ✓ Todos os servers prontos. Sessão de desenvolvimento pode iniciar.", GREEN))
    print()
    return 0

# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP Health Check — NovaTech Assistant")
    parser.add_argument("--verbose", "-v", action="store_true", help="Saída detalhada")
    args = parser.parse_args()

    # Garante que rodamos da raiz do repositório
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    os.chdir(repo_root)

    sys.exit(run_health_check(verbose=args.verbose))
