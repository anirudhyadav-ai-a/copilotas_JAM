import * as vscode from 'vscode';
import {
    JUDGE_REVIEW_SYSTEM,
    JUDGE_SECURITY_SYSTEM,
    ADVOCATE_ADR_SYSTEM,
    ADVOCATE_DEVIL_SYSTEM,
    MEDIATOR_DESIGN_SYSTEM,
    MEDIATOR_DEPS_SYSTEM,
    CODEDOM_SYSTEM,
} from './prompts';

// ─────────────────────────────────────────────────────────────────
//  Model Preferences per Role
//
//  Your org has Claude, Gemini, and GPT-4o available via Copilot.
//  Each role is assigned the model best suited to its task:
//
//  ⚖  Judge     → Claude   (nuanced reasoning, catches subtle logic errors)
//  📐  Advocate  → GPT-4o   (structured document generation, ADR format)
//  👿  Devil     → Claude   (adversarial reasoning, identifying hidden assumptions)
//  🤝  Mediator  → Claude   (synthesis, finding common ground across positions)
//
//  All models piggyback your existing Copilot licence — no extra API keys.
//  Override ROLE_MODEL_PREFERENCES below to change per-role assignments.
// ─────────────────────────────────────────────────────────────────

type ModelFamily = 'claude' | 'gpt-4o' | 'gemini' | 'gpt-4';
type Role = 'judge' | 'judge-security' | 'advocate-adr' | 'advocate-devil' | 'mediator-design' | 'mediator-deps' | 'codedom';

/**
 * Preferred model family per role. Change these to reassign models.
 * The extension will try each preference in order, then fall back
 * to any available Copilot model.
 */
const ROLE_MODEL_PREFERENCES: Record<Role, ModelFamily[]> = {
    'judge':           ['claude', 'gpt-4o', 'gemini'],   // Claude: best at nuanced code judgment
    'judge-security':  ['claude', 'gpt-4o', 'gemini'],   // Claude: strong OWASP reasoning
    'advocate-adr':    ['gpt-4o', 'claude', 'gemini'],   // GPT-4o: reliable ADR structure
    'advocate-devil':  ['claude', 'gpt-4o', 'gemini'],   // Claude: adversarial reasoning
    'mediator-design': ['claude', 'gpt-4o', 'gemini'],   // Claude: synthesis and common ground
    'mediator-deps':   ['gpt-4o', 'claude', 'gemini'],   // GPT-4o: precise version constraint logic
    'codedom':         ['claude', 'gemini', 'gpt-4o'],   // Claude: structural analysis and graph reasoning
};

/** Maps our short family names to Copilot model id substrings */
const FAMILY_ID_MAP: Record<ModelFamily, string[]> = {
    'claude':  ['claude-3.5-sonnet', 'claude-3.5', 'claude-3', 'claude'],
    'gpt-4o':  ['gpt-4o'],
    'gemini':  ['gemini-2', 'gemini-1.5', 'gemini'],
    'gpt-4':   ['gpt-4'],
};

// ─────────────────────────────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────────────────────────────

/**
 * Get the active editor's code — either the selection or the full file.
 */
function getActiveCode(): { code: string; fileName: string } | undefined {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        return undefined;
    }
    const selection = editor.selection;
    const code = selection.isEmpty
        ? editor.document.getText()
        : editor.document.getText(selection);
    const fileName = editor.document.fileName;
    return { code, fileName };
}

/**
 * Select the best available Copilot model for a given role.
 *
 * Resolution order:
 *   1. Role's preferred model families (in order)
 *   2. Any Copilot vendor model
 *   3. Any available model
 */
async function selectModelForRole(role: Role): Promise<vscode.LanguageModelChat | undefined> {
    const allCopilotModels = await vscode.lm.selectChatModels({ vendor: 'copilot' });

    // Try each preferred family in order
    const preferences = ROLE_MODEL_PREFERENCES[role];
    for (const family of preferences) {
        const idSubstrings = FAMILY_ID_MAP[family];
        for (const substr of idSubstrings) {
            const match = allCopilotModels.find(m =>
                m.id.toLowerCase().includes(substr.toLowerCase()) ||
                m.family?.toLowerCase().includes(substr.toLowerCase())
            );
            if (match) {
                return match;
            }
        }
    }

    // Fall back to any Copilot model
    if (allCopilotModels.length > 0) {
        return allCopilotModels[0];
    }

    // Last resort: any model
    const allModels = await vscode.lm.selectChatModels();
    return allModels[0];
}

/**
 * Return a display label for the model being used.
 */
function modelLabel(model: vscode.LanguageModelChat): string {
    const id = model.id.toLowerCase();
    if (id.includes('claude'))  { return '🤖 Claude'; }
    if (id.includes('gpt-4o'))  { return '🤖 GPT-4o'; }
    if (id.includes('gemini'))  { return '🤖 Gemini'; }
    if (id.includes('gpt-4'))   { return '🤖 GPT-4'; }
    return `🤖 ${model.id}`;
}

/**
 * Runtime type guard for vscode.Uri reference values.
 * The VS Code API types ref.value as `unknown`; this guard confirms the
 * value has the shape we expect before we call Uri-specific methods on it.
 */
function isUri(value: unknown): value is vscode.Uri {
    return (
        value !== null &&
        value !== undefined &&
        typeof value === 'object' &&
        'fsPath' in (value as object) &&
        'scheme' in (value as object)
    );
}

/**
 * Stream LLM response to the chat panel.
 *
 * Catches vscode.LanguageModelError and surfaces a clean markdown error
 * message rather than letting the exception propagate as a VS Code popup.
 */
async function streamResponse(
    model: vscode.LanguageModelChat,
    messages: vscode.LanguageModelChatMessage[],
    stream: vscode.ChatResponseStream,
    token: vscode.CancellationToken,
): Promise<void> {
    try {
        const response = await model.sendRequest(messages, {}, token);
        for await (const chunk of response.text) {
            stream.markdown(chunk);
        }
    } catch (err) {
        if (err instanceof vscode.LanguageModelError) {
            stream.markdown(
                `**Model error (${err.code}):** ${err.message}\n\n` +
                `> Try again, or check that GitHub Copilot is active and the model is available.`
            );
        } else if (err instanceof Error) {
            stream.markdown(`**Unexpected error:** ${err.message}`);
        } else {
            stream.markdown('**An unknown error occurred.** Please try again.');
        }
    }
}

// ─────────────────────────────────────────────────────────────────
//  ⚖  Judge Handler
// ─────────────────────────────────────────────────────────────────

async function handleJudge(
    request: vscode.ChatRequest,
    _context: vscode.ChatContext,
    stream: vscode.ChatResponseStream,
    token: vscode.CancellationToken,
): Promise<void> {
    const role: Role = request.command === 'security' ? 'judge-security' : 'judge';
    const model = await selectModelForRole(role);
    if (!model) {
        stream.markdown('**Error:** No language model available. Make sure GitHub Copilot is active.');
        return;
    }

    const systemPrompt = request.command === 'security'
        ? JUDGE_SECURITY_SYSTEM
        : JUDGE_REVIEW_SYSTEM;

    const commandLabel = request.command === 'security'
        ? '🔒 Security Audit'
        : '⚖ Code Review';

    // Get code from references (#file) or active editor
    let codeContent = '';
    let fileName = 'unknown';

    const fileRefs = request.references.filter(ref => ref.id === 'vscode.file');
    if (fileRefs.length > 0) {
        for (const ref of fileRefs) {
            if (!isUri(ref.value)) { continue; }
            const uri = ref.value;
            const doc = await vscode.workspace.openTextDocument(uri);
            codeContent += `\n// File: ${uri.fsPath}\n${doc.getText()}\n`;
            fileName = uri.fsPath;
        }
    } else {
        const active = getActiveCode();
        if (!active) {
            stream.markdown('**No code to review.** Open a file or use `#file` to reference one.');
            return;
        }
        codeContent = active.code;
        fileName = active.fileName;
    }

    // Truncate very large files to stay within context limits.
    // ~12 000 chars ≈ 3 000–4 000 tokens for typical code; cut at a clean
    // line boundary so the model does not receive a syntactically broken snippet.
    const maxChars = 12000;
    if (codeContent.length > maxChars) {
        const cutPoint = codeContent.lastIndexOf('\n', maxChars);
        codeContent = codeContent.substring(0, cutPoint > 0 ? cutPoint : maxChars) + '\n\n[... truncated ...]';
    }

    stream.markdown(`**${commandLabel}** · \`${fileName}\` · ${modelLabel(model)}\n\n---\n\n`);

    const userPrompt = request.prompt
        ? `${request.prompt}\n\n## Code\n\`\`\`\n${codeContent}\n\`\`\``
        : `Review this code:\n\n\`\`\`\n${codeContent}\n\`\`\``;

    const messages = [
        vscode.LanguageModelChatMessage.User(`[SYSTEM INSTRUCTIONS]\n\n${systemPrompt}`),
        vscode.LanguageModelChatMessage.User(userPrompt),
    ];

    await streamResponse(model, messages, stream, token);
}

// ─────────────────────────────────────────────────────────────────
//  📐  Advocate Handler
// ─────────────────────────────────────────────────────────────────

async function handleAdvocate(
    request: vscode.ChatRequest,
    _context: vscode.ChatContext,
    stream: vscode.ChatResponseStream,
    token: vscode.CancellationToken,
): Promise<void> {
    const isDevil = request.command === 'devil';
    const role: Role = isDevil ? 'advocate-devil' : 'advocate-adr';
    const model = await selectModelForRole(role);
    if (!model) {
        stream.markdown('**Error:** No language model available. Make sure GitHub Copilot is active.');
        return;
    }

    const systemPrompt = isDevil ? ADVOCATE_DEVIL_SYSTEM : ADVOCATE_ADR_SYSTEM;
    const commandLabel = isDevil ? '👿 Devil\'s Advocate' : '📐 ADR Generator';

    if (!request.prompt || request.prompt.trim().length === 0) {
        stream.markdown(isDevil
            ? '**Provide a proposal to stress-test.** Example:\n\n`@advocate /devil We should migrate from REST to GraphQL for our client-facing API because...`'
            : '**Provide a proposal for the ADR.** Example:\n\n`@advocate /adr We should adopt Redis Streams instead of Kafka for our event pipeline because...`');
        return;
    }

    stream.markdown(`**${commandLabel}** · ${modelLabel(model)}\n\n---\n\n`);

    // Include any referenced file content as codebase context
    let context = '';
    const fileRefs = request.references.filter(ref => ref.id === 'vscode.file');
    for (const ref of fileRefs) {
        if (!isUri(ref.value)) { continue; }
        const uri = ref.value;
        const doc = await vscode.workspace.openTextDocument(uri);
        let fileText = doc.getText();
        const maxFileChars = 6000;
        if (fileText.length > maxFileChars) {
            const cutPoint = fileText.lastIndexOf('\n', maxFileChars);
            fileText = fileText.substring(0, cutPoint > 0 ? cutPoint : maxFileChars) + '\n[... truncated ...]';
        }
        context += `\n## Codebase Context (${uri.fsPath})\n${fileText}\n`;
    }

    const userPrompt = context
        ? `${context}\n\n## Proposal\n${request.prompt}`
        : `## Proposal\n${request.prompt}`;

    const messages = [
        vscode.LanguageModelChatMessage.User(`[SYSTEM INSTRUCTIONS]\n\n${systemPrompt}`),
        vscode.LanguageModelChatMessage.User(userPrompt),
    ];

    await streamResponse(model, messages, stream, token);
}

// ─────────────────────────────────────────────────────────────────
//  🤝  Mediator Handler
// ─────────────────────────────────────────────────────────────────

async function handleMediator(
    request: vscode.ChatRequest,
    _context: vscode.ChatContext,
    stream: vscode.ChatResponseStream,
    token: vscode.CancellationToken,
): Promise<void> {
    const isDeps = request.command === 'deps';
    const role: Role = isDeps ? 'mediator-deps' : 'mediator-design';
    const model = await selectModelForRole(role);
    if (!model) {
        stream.markdown('**Error:** No language model available. Make sure GitHub Copilot is active.');
        return;
    }

    const systemPrompt = isDeps ? MEDIATOR_DEPS_SYSTEM : MEDIATOR_DESIGN_SYSTEM;
    const commandLabel = isDeps
        ? '📦 Dependency Conflict Resolution'
        : '🤝 Design Conflict Mediation';

    if (!request.prompt || request.prompt.trim().length === 0) {
        stream.markdown(isDeps
            ? '**Describe the dependency conflict.** Example:\n\n`@mediator /deps Package A requires lodash >=4.17.21 but Package B pins lodash@4.17.15`'
            : '**Provide both positions.** Example:\n\n`@mediator /design Position A: We should use in-process caching because... Position B: We should use Redis-only because...`');
        return;
    }

    stream.markdown(`**${commandLabel}** · ${modelLabel(model)}\n\n---\n\n`);

    // Include any referenced files as context
    let context = '';
    const fileRefs = request.references.filter(ref => ref.id === 'vscode.file');
    for (const ref of fileRefs) {
        if (!isUri(ref.value)) { continue; }
        const uri = ref.value;
        const doc = await vscode.workspace.openTextDocument(uri);
        let mediatorText = doc.getText();
        const maxMediatorChars = 6000;
        if (mediatorText.length > maxMediatorChars) {
            const cutPoint = mediatorText.lastIndexOf('\n', maxMediatorChars);
            mediatorText = mediatorText.substring(0, cutPoint > 0 ? cutPoint : maxMediatorChars) + '\n[... truncated ...]';
        }
        context += `\n## Context from ${uri.fsPath}\n${mediatorText}\n`;
    }

    const userPrompt = context
        ? `${context}\n\n${request.prompt}`
        : request.prompt;

    const messages = [
        vscode.LanguageModelChatMessage.User(`[SYSTEM INSTRUCTIONS]\n\n${systemPrompt}`),
        vscode.LanguageModelChatMessage.User(userPrompt),
    ];

    await streamResponse(model, messages, stream, token);
}

// ─────────────────────────────────────────────────────────────────
//  🧬  Code DOM Handler
// ─────────────────────────────────────────────────────────────────

async function handleCodeDOM(
    request: vscode.ChatRequest,
    _context: vscode.ChatContext,
    stream: vscode.ChatResponseStream,
    token: vscode.CancellationToken,
): Promise<void> {
    const model = await selectModelForRole('codedom');
    if (!model) {
        stream.markdown('**Error:** No language model available. Make sure GitHub Copilot is active.');
        return;
    }

    const command = request.command ?? 'impact';
    const commandLabels: Record<string, string> = {
        'impact': '💥 Impact Analysis',
        'deadcode': '🗑 Dead Code Finder',
        'refactor': '🔧 Refactor Planner',
        'mermaid': '📊 Mermaid Export',
    };

    const label = commandLabels[command] ?? '🧬 Code DOM';
    stream.markdown(`**${label}** · ${modelLabel(model)}\n\n---\n\n`);

    // Build workspace context from actual files
    const workspaceContext = await buildCodeContext();
    const userPrompt = request.prompt || 'Analyse the codebase structure.';

    const commandPrompts: Record<string, string> = {
        'impact': `Analyse the blast radius of changing "${userPrompt}". Identify all direct callers, transitive callers, and affected test files. Compute a blast radius score (0=isolated, 1=central).`,
        'deadcode': `Find dead code in the workspace: unreachable functions, unused imports, orphan classes. Report with file paths and symbol names. ${userPrompt}`,
        'refactor': `Plan a refactor for "${userPrompt}". Identify all callers, imports, and tests that need updating. Generate a step-by-step plan.`,
        'mermaid': `Generate a Mermaid diagram showing the dependency graph for "${userPrompt}". Use flowchart LR format with clear node labels.`,
    };

    const prompt = commandPrompts[command] ?? userPrompt;

    const messages = [
        vscode.LanguageModelChatMessage.User(`[SYSTEM INSTRUCTIONS]\n\n${CODEDOM_SYSTEM}`),
        vscode.LanguageModelChatMessage.User(`## Workspace Context\n${workspaceContext}\n\n## Request\n${prompt}`),
    ];

    await streamResponse(model, messages, stream, token);
}

/**
 * Scan workspace Python files and build a structural context string
 * for the Code DOM commands.
 */
async function buildCodeContext(): Promise<string> {
    const sourceFiles = await vscode.workspace.findFiles(
        '**/*.{py,ts,js,tsx,jsx}',
        '**/node_modules/**',
        50,
    );
    if (sourceFiles.length === 0) {
        return '(No source files found in workspace)';
    }

    const parts: string[] = [`Found ${sourceFiles.length} source files:\n`];

    // Python and TypeScript/JavaScript symbol extraction patterns
    const symbolPattern = /^(?:(?:export\s+)?(?:class|def|async def|function|async function|const|interface|type|enum)\s+(\w+))/;

    for (const uri of sourceFiles.slice(0, 20)) {
        try {
            const doc = await vscode.workspace.openTextDocument(uri);
            const text = doc.getText();
            const relativePath = vscode.workspace.asRelativePath(uri);
            const lang = uri.fsPath.endsWith('.py') ? 'python' : 'typescript';
            const symbols: string[] = [];

            for (const line of text.split('\n')) {
                const match = line.match(symbolPattern);
                if (match) {
                    symbols.push(match[1]);
                }
            }

            parts.push(`### ${relativePath}`);
            if (symbols.length > 0) {
                parts.push(`Symbols: ${symbols.join(', ')}`);
            }
            const snippet = text.length > 500 ? text.slice(0, 500) + '\n// ...' : text;
            parts.push('```' + lang + '\n' + snippet + '\n```\n');
        } catch {
            // skip unreadable files
        }
    }

    return parts.join('\n');
}

// ─────────────────────────────────────────────────────────────────
//  Extension Lifecycle
// ─────────────────────────────────────────────────────────────────

export function activate(context: vscode.ExtensionContext): void {
    // ⚖ Judge
    const judge = vscode.chat.createChatParticipant(
        'copilotas-jam.judge',
        handleJudge,
    );
    judge.iconPath = new vscode.ThemeIcon('scale');

    // 📐 Advocate
    const advocate = vscode.chat.createChatParticipant(
        'copilotas-jam.advocate',
        handleAdvocate,
    );
    advocate.iconPath = new vscode.ThemeIcon('megaphone');

    // 🤝 Mediator
    const mediator = vscode.chat.createChatParticipant(
        'copilotas-jam.mediator',
        handleMediator,
    );
    mediator.iconPath = new vscode.ThemeIcon('git-merge');

    // 🧬 Code DOM
    const codedom = vscode.chat.createChatParticipant(
        'copilotas-jam.codedom',
        handleCodeDOM,
    );
    codedom.iconPath = new vscode.ThemeIcon('symbol-structure');

    // Register Code DOM command palette entries
    context.subscriptions.push(
        judge, advocate, mediator, codedom,
        vscode.commands.registerCommand('copilotas-jam.impact', () =>
            vscode.commands.executeCommand('workbench.action.chat.open', { query: '@codedom /impact ' }),
        ),
        vscode.commands.registerCommand('copilotas-jam.deadcode', () =>
            vscode.commands.executeCommand('workbench.action.chat.open', { query: '@codedom /deadcode ' }),
        ),
        vscode.commands.registerCommand('copilotas-jam.refactor', () =>
            vscode.commands.executeCommand('workbench.action.chat.open', { query: '@codedom /refactor ' }),
        ),
        vscode.commands.registerCommand('copilotas-jam.mermaid', () =>
            vscode.commands.executeCommand('workbench.action.chat.open', { query: '@codedom /mermaid ' }),
        ),
    );
}

export function deactivate(): void {
    // Nothing to clean up
}
