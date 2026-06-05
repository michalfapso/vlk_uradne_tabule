# Skill: Update Project Memory

Invoke this skill manually at the end of a working session to capture insights that will save
future AI agents time.

## When to Invoke

After completing meaningful work in this project — debugging, implementing a feature, exploring
an unfamiliar subsystem, discovering non-obvious behavior.

## Process

### Step 1 — Identify what's worth saving

Review what happened in this session. For each thing you discovered or changed, ask:
**"Would this save a future agent 5+ minutes of exploration?"**

Save it if yes. Skip it if:
- It's already obvious from reading the code
- It's a temporary workaround that should be reverted
- It's ephemeral session state (current task, in-progress work)
- It's already documented in the memory files

Examples of things worth saving:
- A non-obvious field name difference (`paragrafy` vs `zakony` in analysis.json)
- A gotcha (never nest two `ConvexClientProvider` — causes auth desync)
- A new env var or entry point script
- A schema change or new data file format
- A key debugging variable (`PROCESS_SPECIFIC_DOC_IDS` in run_processing.py)

### Step 2 — Update relevant memory files

Read `docs/memory/INDEX.md` to find the right file for each insight.

For each insight:
1. Open the relevant `docs/memory/*.md` file
2. Add the insight to the appropriate section
3. Do not duplicate content already present
4. Keep entries concise — one short paragraph or a table row

### Step 3 — Add new memory files if needed

If no existing file covers the topic:
1. Create `docs/memory/{topic-name}.md` with a clear heading and content
2. Add a row to `docs/memory/INDEX.md`

### Step 4 — Update subdirectory AGENTS.md if the interface changed

Update `analyzer/AGENTS.md`, `data/AGENTS.md`, or `website/AGENTS.md` if:
- A new entry point script was added
- An env var was added or renamed
- A data schema field was added or changed
- A key component was added or restructured

### Step 5 — Commit

```bash
git add docs/memory/ analyzer/AGENTS.md data/AGENTS.md website/AGENTS.md AGENTS.md skills/
git commit -m "docs: update project memory"
```

If only memory files changed (no AGENTS.md changes):
```bash
git add docs/memory/
git commit -m "docs: update project memory"
```

## What NOT to Save

- Code patterns derivable by reading the files
- Git history (use `git log` / `git blame` instead)
- Debugging solutions where the fix is already in the code
- Anything already in AGENTS.md or CLAUDE.md
- In-progress task state or temporary notes
