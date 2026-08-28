#!/usr/bin/env python3
"""
Cliente MCP mínimo (stdio, JSON-RPC 2.0) usado como EVIDÊNCIA de execução real
dos MCP servers configurados em .mcp/mcp.json (Exercício 2.1).

Ele faz exatamente o que um agente (Claude / Copilot) faria ao consumir um
MCP server: spawna o processo do servidor via stdio, executa o handshake
`initialize` -> `notifications/initialized`, lista as tools expostas e
chama tools específicas (`tools/call`), imprimindo requisição e resposta
JSON-RPC cruas para conferência.

Uso:
    python3 mcp_client.py <config.json> <server_name> <cmd1> [cmd2 ...]

Cada "cmd" é uma das:
    list_tools
    call:<tool_name>:<json_arguments>

Exemplo:
    python3 mcp_client.py ../../../.mcp/mcp.json filesystem-docs-novatech \
        list_tools \
        'call:list_directory:{"path": "."}' \
        'call:read_text_file:{"path": "POL-001-politica-devolucao.md"}'
"""
import json
import subprocess
import sys
import threading
import queue


def start_server(command, args, env=None, cwd=None):
    full_env = None
    if env:
        import os
        full_env = os.environ.copy()
        full_env.update(env)
    proc = subprocess.Popen(
        [command, *args],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=full_env,
        cwd=cwd,
    )
    return proc


def reader_thread(pipe, q):
    for line in iter(pipe.readline, ""):
        q.put(line)
    pipe.close()


def send(proc, msg):
    line = json.dumps(msg)
    print(f">>> SEND: {line}")
    proc.stdin.write(line + "\n")
    proc.stdin.flush()


def recv(q, timeout=30):
    line = q.get(timeout=timeout)
    print(f"<<< RECV: {line.strip()}")
    return json.loads(line)


def main():
    config_path, server_name, *cmds = sys.argv[1:]
    with open(config_path) as f:
        config = json.load(f)
    server = config["mcpServers"][server_name]

    print(f"=== Subindo MCP server '{server_name}': {server['command']} {' '.join(server['args'])} ===")
    proc = start_server(server["command"], server["args"], env=server.get("env"))

    out_q = queue.Queue()
    err_q = queue.Queue()
    threading.Thread(target=reader_thread, args=(proc.stdout, out_q), daemon=True).start()
    threading.Thread(target=reader_thread, args=(proc.stderr, err_q), daemon=True).start()

    try:
        # 1. initialize
        send(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "exercicio-2-1-evidence-client", "version": "0.1.0"},
            },
        })
        init_resp = recv(out_q)
        assert "result" in init_resp, f"initialize falhou: {init_resp}"

        # 2. initialized notification
        send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        next_id = 2
        for cmd in cmds:
            if cmd == "list_tools":
                send(proc, {"jsonrpc": "2.0", "id": next_id, "method": "tools/list"})
                resp = recv(out_q)
                if "result" in resp:
                    names = [t["name"] for t in resp["result"]["tools"]]
                    print(f"### Tools expostas por '{server_name}': {names}")
                next_id += 1
            elif cmd.startswith("call:"):
                _, tool_name, args_json = cmd.split(":", 2)
                args = json.loads(args_json)
                send(proc, {
                    "jsonrpc": "2.0",
                    "id": next_id,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": args},
                })
                resp = recv(out_q)
                print(f"### Resultado de tools/call '{tool_name}': "
                      f"{'ERRO/negado' if resp.get('result', {}).get('isError') or 'error' in resp else 'OK'}")
                next_id += 1
            else:
                print(f"Comando desconhecido: {cmd}")
    finally:
        proc.stdin.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        # drenar stderr para diagnóstico
        while not err_q.empty():
            sys.stderr.write("[stderr] " + err_q.get())


if __name__ == "__main__":
    main()
