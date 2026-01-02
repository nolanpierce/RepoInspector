from agentloop import run_agent


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python src/agentloop.py <repo_path>")
    run_agent(sys.argv[1], prompt_path="prompts.txt", out_dir="outputs")
