# Option B — Copilotas JAM VS Code Extension

> A Copilot Chat Participant extension that registers `@judge`, `@advocate`, `@mediator`, and `@codedom` as commands in GitHub Copilot Chat. Piggybacks your org's Copilot LLM — no separate API keys required.

---

## What It Does

| Command | Role | What Happens |
|---|---|---|
| `@judge` | ⚖ Judge | Reviews the active file / selection against the baked-in rubric. Returns APPROVE / REQUEST_CHANGES / BLOCK. |
| `@judge /review` | ⚖ Judge | Same as above — explicit review command. |
| `@judge /security` | ⚖ Judge | Focused security audit against OWASP Top-10 patterns. |
| `@advocate /adr` | 📐 Advocate | Generates a complete Architecture Decision Record from your proposal. |
| `@advocate /devil` | 👿 Advocate | Stress-tests your proposal. Returns PROCEED / REVISE / RECONSIDER. |
| `@mediator /design` | 🤝 Mediator | Mediates a design conflict between two positions. Finds synthesis. |
| `@mediator /deps` | 📦 Mediator | Resolves dependency version conflicts. |
| `@codedom /impact` | 🧬 Code DOM | Analyse blast radius of changing a symbol. |
| `@codedom /deadcode` | 🧬 Code DOM | Find unreachable functions and unused imports. |
| `@codedom /refactor` | 🧬 Code DOM | Plan a rename refactor across callers. |
| `@codedom /mermaid` | 🧬 Code DOM | Export dependency graph as Mermaid diagram. |

The four `@codedom` commands are also available from the **Command Palette** (`Ctrl+Shift+P`) as:
- `JAM: Impact Analysis`
- `JAM: Dead Code Finder`
- `JAM: Refactor Planner`
- `JAM: Export Mermaid Diagram`

---

## Prerequisites

- **VS Code** 1.93.0 or later
- **GitHub Copilot** extension installed and authenticated
- **GitHub Copilot Chat** extension installed
- **Node.js** 18+ (for building)

---

## Build & Install

```bash
# 1. Install dependencies
cd copilotas_JAM/vscodebase
npm install

# 2. Compile TypeScript
npm run compile

# 3. Package as .vsix
npm run package
# → produces copilotas-jam-0.1.0.vsix

# 4. Install in VS Code
code --install-extension copilotas-jam-0.1.0.vsix
```

---

## Usage Examples

### Judge — Review a file

Open any code file, then in Copilot Chat:

```
@judge is this implementation correct?
```

Or explicitly:

```
@judge /review check for security issues and test coverage gaps
```

The Judge reads the active file, evaluates it against the rubric, and returns a structured verdict.

You can also reference specific files with `#file`:

```
@judge /review #file:src/auth.ts
```

### Judge — Security audit

```
@judge /security
```

Focused OWASP Top-10 audit of the active file.

### Advocate — Generate ADR

```
@advocate /adr We should migrate from REST to GraphQL for our client-facing API
because mobile clients are over-fetching data and making too many round trips.
The backend already has a schema-first design that maps well to GraphQL types.
```

### Advocate — Devil's Advocate

```
@advocate /devil We should replace our PostgreSQL database with MongoDB because
our data model is becoming more document-oriented and we need horizontal scaling.
```

### Code DOM — Impact analysis

```
@codedom /impact UserService.authenticate
```

Analyses which callers, tests, and downstream modules would be affected.

### Code DOM — Dead code

```
@codedom /deadcode
```

Scans workspace for unreachable functions, unused imports, and orphan classes.

### Code DOM — Mermaid diagram

```
@codedom /mermaid auth module
```

Exports a Mermaid flowchart of the call graph.

### Mediator — Resolve design conflict

```
@mediator /design
Position A: We should use in-process caching with Redis fallback because it
reduces latency for hot paths and we already have the in-process cache library.

Position B: We should use Redis-only caching with a thin client because it
simplifies our architecture and gives us a single source of truth for cache state.
```

### Mediator — Resolve dependency conflict

```
@mediator /deps
Our project requires pandas>=2.0 for the new DataFrame API, but our
ML pipeline depends on scikit-learn 1.2.x which pins pandas<2.0.
```

---

## Project Structure

```
vscodebase/
├── package.json          ← Extension manifest + chat participant registration
├── tsconfig.json         ← TypeScript config
├── .gitignore
├── .vscodeignore         ← Files excluded from .vsix package
├── README.md             ← This file
└── src/
    ├── extension.ts      ← Extension entry point + handler registration
    └── prompts.ts        ← All baked-in role prompts
```

---

## How It Works

1. **Chat Participants** are registered in `package.json` under `contributes.chatParticipants`. This tells VS Code to show `@judge`, `@advocate`, `@mediator`, and `@codedom` in the Copilot Chat autocomplete.

2. **Handlers** in `extension.ts` are called when the user invokes a participant. Each handler:
   - Selects a Copilot language model via `vscode.lm.selectChatModels()`
   - Loads the appropriate system prompt from `prompts.ts`
   - Injects the active file / selection / user input as context
   - Streams the LLM response back to the chat panel

3. **No API keys needed** — the extension uses `vscode.lm.selectChatModels()` which routes through your org's configured Copilot LLM. Whatever model your firm has approved is what gets used.

---

## Customisation

### Changing the prompts

Edit `src/prompts.ts` and rebuild:

```bash
npm run compile && npm run package
```

### Changing the model preference

In `extension.ts`, the `ROLE_MODEL_PREFERENCES` map controls which model family each role tries first. The default assignments are:

| Role | Preference order |
|---|---|
| Judge / Security | Claude → GPT-4o → Gemini |
| Advocate ADR | GPT-4o → Claude → Gemini |
| Advocate Devil | Claude → GPT-4o → Gemini |
| Mediator Design | Claude → GPT-4o → Gemini |
| Mediator Deps | GPT-4o → Claude → Gemini |
| Code DOM | Claude → Gemini → GPT-4o |

Edit `ROLE_MODEL_PREFERENCES` at the top of `extension.ts` to reassign models. `selectModelForRole()` resolves preferences at runtime by matching against your org's available Copilot models and falls back to any Copilot model if none match.

### Adding new roles

1. Add a new system prompt in `src/prompts.ts`
2. Add a new chat participant in `package.json` under `contributes.chatParticipants`
3. Add a new handler function in `src/extension.ts`
4. Register it in the `activate()` function

---

## Distributing to Your Team

### Option 1 — Share the .vsix file

```bash
npm run package
# Share copilotas-jam-0.1.0.vsix via Slack, email, or internal artifact store
# Team members install with: code --install-extension copilotas-jam-0.1.0.vsix
```

### Option 2 — Internal VS Code extension marketplace

If your org has a private extension gallery, publish there for auto-updates.

### Option 3 — Development mode

Team members can clone this folder and run in development:

```bash
npm install && npm run watch
# Then press F5 in VS Code to launch Extension Development Host
```

---

## Comparison: Option A (MD Templates) vs Option B (This Extension)

| | Option A | Option B (this extension) |
|---|---|---|
| **Setup** | Zero | Build + install |
| **Customisable prompts** | Yes — edit the .md files | No — edit source + rebuild |
| **UX** | Copy/paste into Copilot Chat | `@` commands with autocomplete |
| **File context** | Manual paste | Automatic (active file + `#file`) |
| **Best for** | Evaluation, custom workflows | Daily use, consistent team UX |

**Recommendation:** Start with [Option A](../prompts/README.md) to validate the concept. Deploy this extension once the team is ready for a polished daily workflow.

---

*See [`WORKING_PLAN.md`](../WORKING_PLAN.md) for the full implementation guide and rollout plan.*
