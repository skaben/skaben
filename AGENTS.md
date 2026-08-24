# Agent Bootstrap

Before implementation or review:

1. Identify every owning roadmap work-package ID.
2. Render mandatory task context with intended/touched repository-relative paths:
   `.venv/bin/python .agents/context_loader.py render --work-package P4-W2 --path server/alert/models.py`
3. Repeat `--work-package` and `--path` as needed. Add every applicable semantic
   `--condition` defined by the matched manifest routes.
4. Read the rendered authority, shared context, roadmap, review, and target-plan sections
   before changing or assessing files.

Do not treat `.agent-review` as automatic Codex instructions or load every review. The
loader is the required bridge to [planning authority](.agents/plans/README.md) and
[routing rules](.agents/context-routing.yml); it has no persistent active-phase state.

After changing plans, reviews, routing, or this bootstrap, run:
`.venv/bin/python .agents/context_loader.py check`
