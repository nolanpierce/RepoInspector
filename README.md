# RepoInspector

RepoInspector is a small agent-driven tool that analyzes a source code repository and generates human-readable documentation from it.  
Given a project directory, it walks the codebase, selectively reads high-signal files, and produces structured Markdown documentation such as a README and architecture overview.

The goal is to demonstrate **agentic behavior over real code**, not just single-prompt summarization.

---

## What It Does

RepoInspector:
- Scans a repository while skipping dependency and build directories
- Builds a structured view of the project layout
- Reads relevant files on demand (configs, entry points, etc.)
- Uses an LLM to decide what to inspect next
- Generates:
  - `README.generated.md`
  - `ARCHITECTURE.generated.md`

All output is written as plain Markdown.

---

## Why This Exists

Most “auto-docs” tools work by dumping the entire repo into a prompt.  
RepoInspector instead uses an **agent loop** that:
- Chooses actions step-by-step
- Reads only what it needs
- Tracks what it has already learned
- Produces documentation grounded in observed files

This makes the system cheaper, more controllable, and easier to reason about.

---

## Project Structure

src/
├── agentloop.py # Core agent loop and action router
├── llm.py # LLM client setup
├── config.py # Environment-based configuration
├── prompts.txt # System prompt that governs agent behavior
└── tools/
├── dirscanner.py # Repository traversal and file reading
└── filewrite.py # Markdown output writer

---

## How It Works (High Level)

1. The repository is scanned using `os.walk`, skipping known noise directories.
2. A summarized tree and list of high-signal files is provided to the agent.
3. The agent repeatedly:
   - Chooses an action (`read_file`, `write_doc`, or `finish`)
   - Executes that action via a tool
   - Receives the result as an observation
4. Once enough context is gathered, the agent writes Markdown documentation.
5. The process stops when all required docs are generated.

---

## Usage

### Prerequisites
- Python 3.12+
- An LLM endpoint compatible with the OpenAI API schema (we use vultr serverless inference in the example)
- Environment variables configured for your model provider

### Run
```bash
python src/main.py /path/to/repo
```

### Output 
It outputs generated md files into a output directory inside of RepoInspectors project root