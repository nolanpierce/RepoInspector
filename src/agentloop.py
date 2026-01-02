# src/agentloop.py
import json
import os
from typing import Any, Dict

from config import vultr_model
from llm import client
from tools.dirscanner import DirScanner
from tools.filewrite import FileWriter

MAX_STEPS = 10
MAX_READ_CHARS = 12000


def load_prompt(prompt_path: str) -> str:
    with open(prompt_path, "r", encoding="utf-8") as f:
        s = f.read()
    if not s.strip():
        raise RuntimeError(f"Prompt file is empty: {prompt_path}")
    return s


def safe_json_loads(text: str) -> Dict[str, Any]:
    s = (text or "").strip()
    if not s:
        raise ValueError("Empty model response")

    try:
        obj = json.loads(s)
        if not isinstance(obj, dict):
            raise ValueError("Model output JSON must be an object")
        return obj
    except json.JSONDecodeError:
        start = s.find("{")
        end = s.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Could not find JSON object in model output")
        obj = json.loads(s[start : end + 1])
        if not isinstance(obj, dict):
            raise ValueError("Model output JSON must be an object")
        return obj


def build_relative_tree(abs_tree: dict, repo_root: str) -> dict:
    rel_tree: Dict[str, Any] = {}
    repo_root = os.path.abspath(repo_root)
    for abs_dir, entry in abs_tree.items():
        abs_dir = os.path.abspath(abs_dir)
        rel_dir = os.path.relpath(abs_dir, repo_root)
        rel_tree[rel_dir] = {
            "dirs": entry.get("dirs", []),
            "files": entry.get("files", []),
        }
    return rel_tree


def pick_high_signal_files(rel_tree: dict) -> list[str]:
    preferred = [
        "README.md", "README.rst", "README.txt",
        "package.json", "pyproject.toml", "requirements.txt", "Pipfile",
        "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
        "Dockerfile", "docker-compose.yml", "compose.yaml", "Makefile",
        ".env.example", ".env.sample",
    ]
    all_files: list[str] = []
    for rel_dir, entry in rel_tree.items():
        for fn in entry.get("files", []):
            rel_path = fn if rel_dir == "." else os.path.join(rel_dir, fn)
            all_files.append(rel_path.replace(os.sep, "/"))

    file_set = set(all_files)
    selected: list[str] = []
    for name in preferred:
        if name in file_set and name not in selected:
            selected.append(name)

    # some common entry points
    for name in ["src/main.py", "src/app.py", "src/server.py", "src/index.ts", "src/index.js", "main.py", "app.py", "server.py", "index.ts", "index.js"]:
        if name in file_set and name not in selected:
            selected.append(name)

    return selected[:12]


def read_file(scanner: DirScanner, rel_path: str) -> Dict[str, Any]:
    rel_path = rel_path.replace("\\", "/")
    content = scanner.file_contents(rel_path)  # expects repo-relative
    truncated = False
    if len(content) > MAX_READ_CHARS:
        content = content[:MAX_READ_CHARS]
        truncated = True
    return {"event": "read_file", "path": rel_path, "truncated": truncated, "content": content}


def llm(messages, max_tokens=900, temperature=0.2) -> str:
    resp = client.chat.completions.create(
        model=vultr_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


def force_write_docs(system_prompt: str, memory: dict, evidence: dict, writer: FileWriter) -> None:
    # Force README
    msg = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps({
            "TASK": "Write README.generated.md now.",
            "MEMORY": memory,
            "EVIDENCE": evidence
        })}
    ]
    out = llm(msg, max_tokens=1400, temperature=0.2)
    action = safe_json_loads(out)
    if action.get("action") == "write_doc" and action.get("doc_name") == "README.generated.md":
        writer.write_md(action["doc_name"], action.get("content", ""))
        memory["docs_written"].append("README.generated.md")

    # Force ARCH
    msg = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps({
            "TASK": "Write ARCHITECTURE.generated.md now.",
            "MEMORY": memory,
            "EVIDENCE": evidence
        })}
    ]
    out = llm(msg, max_tokens=1600, temperature=0.2)
    action = safe_json_loads(out)
    if action.get("action") == "write_doc" and action.get("doc_name") == "ARCHITECTURE.generated.md":
        writer.write_md(action["doc_name"], action.get("content", ""))
        memory["docs_written"].append("ARCHITECTURE.generated.md")


def run_agent(repo_path: str, prompt_path: str = "prompts.txt", out_dir: str = "outputs") -> None:
    system_prompt = load_prompt(prompt_path)
    print(f"[agent] loaded prompt: {len(system_prompt)} chars")

    scanner = DirScanner(repo_path)
    writer = FileWriter(out_dir=out_dir)

    abs_tree = scanner.tree()
    rel_tree = build_relative_tree(abs_tree, repo_path)
    candidates = pick_high_signal_files(rel_tree)

    memory: Dict[str, Any] = {
        "repo_root": os.path.abspath(repo_path).replace(os.sep, "/"),
        "files_read": [],
        "docs_written": [],
        "notes": [],
    }

    evidence: Dict[str, Any] = {
        "tree_root": rel_tree.get(".", {}),
        "high_signal_files": candidates,
        "file_snippets": {},  # path -> snippet
    }

    observation: Dict[str, Any] = {
        "event": "start",
        "tree_root_dirs": evidence["tree_root"].get("dirs", []),
        "tree_root_files": evidence["tree_root"].get("files", []),
        "high_signal_files": candidates,
    }

    for step in range(1, MAX_STEPS + 1):
        payload = {
            "STEP": step,
            "REPO_ROOT": memory["repo_root"],
            "TREE": {
                "root_dirs": observation.get("tree_root_dirs", []),
                "root_files": observation.get("tree_root_files", []),
                "high_signal_files": candidates,
            },
            "MEMORY": memory,
            "OBSERVATION": observation,
        }

        raw = llm([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ])

        print(f"\n[agent] step {step} raw:\n{raw}\n")

        try:
            action = safe_json_loads(raw)
        except Exception as e:
            print(f"[agent] JSON parse error: {e}")
            observation = {"event": "error", "error": f"json_parse: {e}", "raw": raw[:500]}
            continue

        print(f"[agent] step {step} action: {action.get('action')}")

        act = action.get("action")
        if act == "read_file":
            path = action.get("path")
            if not isinstance(path, str) or not path:
                observation = {"event": "error", "error": "read_file missing path"}
                continue

            norm = path.replace("\\", "/")
            if norm in memory["files_read"]:
                observation = {"event": "read_file_skipped", "path": norm, "reason": "already_read"}
                continue

            try:
                observation = read_file(scanner, norm)
                memory["files_read"].append(observation["path"])
                evidence["file_snippets"][observation["path"]] = observation["content"]
                print(f"[agent] read_file ok: {observation['path']} (truncated={observation['truncated']})")
            except Exception as e:
                observation = {"event": "error", "error": f"read_file failed: {type(e).__name__}: {e}", "path": norm}
                print(f"[agent] read_file failed: {e}")

        elif act == "write_doc":
            doc_name = action.get("doc_name")
            content = action.get("content")
            if doc_name not in ("README.generated.md", "ARCHITECTURE.generated.md"):
                observation = {"event": "error", "error": "write_doc invalid doc_name"}
                continue
            if not isinstance(content, str) or not content.strip():
                observation = {"event": "error", "error": "write_doc empty content"}
                continue

            out_path = writer.write_md(doc_name, content)
            memory["docs_written"].append(doc_name)
            observation = {"event": "write_doc", "doc_name": doc_name, "out_path": out_path.replace(os.sep, "/")}
            print(f"[agent] wrote: {observation['out_path']}")

            if "README.generated.md" in memory["docs_written"] and "ARCHITECTURE.generated.md" in memory["docs_written"]:
                print("[agent] done: both docs written")
                return

        elif act == "finish":
            print(f"[agent] finish: {action.get('reason','')}")
            break

        else:
            observation = {"event": "error", "error": f"unknown action: {act}"}
            print(f"[agent] unknown action: {act}")

    # Fallback: force docs if model never wrote them
    print("\n[agent] max steps reached or finished without both docs; forcing doc generation...")
    force_write_docs(system_prompt, memory, evidence, writer)
    print(f"[agent] docs_written: {memory['docs_written']}")

