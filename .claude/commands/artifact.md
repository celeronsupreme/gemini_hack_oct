---
description: Improve an existing claude.ai artifact (plan, brief, or a design prototype)
argument-hint: <artifact url or name> <what to change>
---

Artifact task: $ARGUMENTS

1. Find the artifact. If no URL is given, use `Artifact` `action: "list"`; the known ones are listed under "Source docs" in CLAUDE.md.
2. Read the **live** version first (`Artifact` `action: "read"`, or the Claude Docs tools if it is a Doc). Never republish from the snapshots in `docs/`, because the live copy may have newer edits.
3. Make the change on top of what you read. Keep its existing structure and voice unless asked otherwise. Numbers must match `analysis/*_results.json` and the demo numbers in CLAUDE.md.
4. Privacy: no real names, no NHS number, no unredacted diary notes. Use role words ("she", "carer").
5. Publish to the **same URL** (pass `url`), then give the link and a two-line summary of what changed. If it is a Doc, also refresh the matching snapshot in `docs/` so the repo stays current.
