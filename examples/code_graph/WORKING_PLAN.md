# Working Plan — Code Graph: Structural Memory & Impact Analysis

> **Companion implementation guide for the whitepaper:**
> *"Code Graph: Structural Memory & Impact Analysis"*

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Data Models](#2-data-models)
3. [Parsers](#3-parsers)
4. [Graph Construction](#4-graph-construction)
5. [Analysis Algorithms](#5-analysis-algorithms)
6. [Metrics & Scoring](#6-metrics--scoring)
7. [Persistence & Lifecycle](#7-persistence--lifecycle)
8. [Query API](#8-query-api)
9. [Advisors & Visualization](#9-advisors--visualization)
10. [Decision Framework](#10-decision-framework)
11. [Appendix](#11-appendix)

---

## 1. Introduction

### The Problem: No Structural Memory

AI code tools treat every review as if the codebase was created five minutes ago. There is no memory of:
- Which functions are called by whom
- What breaks when `calculateTotal` changes its signature
- Which classes haven't been tested in 90 days
- Whether this PR introduces a circular dependency that didn't exist before

**Code Graph** builds a persistent, queryable graph of the entire codebase — the structural equivalent of a DOM tree for HTML, but for code.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                       CODE DOM PIPELINE                          │
│                                                                  │
│  Source Files                                                    │
│      │                                                           │
│      ▼                                                           │
│  ┌────────────┐   ┌────────────┐   ┌──────────────┐            │
│  │  Python    │   │TypeScript  │   │   Import     │            │
│  │  AST       │──▶│ tree-sitter│──▶│   Resolver   │            │
│  │  Parser    │   │  Parser    │   │              │            │
│  └────────────┘   └────────────┘   └──────┬───────┘            │
│                                           │                      │
│                                           ▼                      │
│  ┌────────────────────────────────────────────────────┐         │
│  │              CODE DOM GRAPH (NetworkX)              │         │
│  │                                                     │         │
│  │  CodeNode ──[CALLS]──▶ CodeNode                    │         │
│  │  CodeNode ──[IMPORTS]──▶ CodeNode                  │         │
│  │  ClassNode ──[INHERITS]──▶ ClassNode               │         │
│  │  FunctionNode ──[TESTS]──▶ FunctionNode            │         │
│  └──────────────────────┬─────────────────────────────┘         │
│                         │                                        │
│            ┌────────────┼────────────┐                          │
│            ▼            ▼            ▼                           │
│  ┌──────────────┐ ┌──────────┐ ┌──────────┐                    │
│  │   Impact     │ │  Dead    │ │ Circular │                    │
│  │  Analyzer    │ │  Code    │ │   Dep    │                    │
│  │              │ │  Finder  │ │ Detector │                    │
│  └──────────────┘ └──────────┘ └──────────┘                    │
│                         │                                        │
│                         ▼                                        │
│  ┌────────────────────────────────────────┐                     │
│  │          SQLite Persistence            │                     │
│  │  nodes | edges | metadata | snapshots  │                     │
│  └────────────────────────────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Data Models

### 2.1 CodeNode

```
Feature 3: CodeNode Data Model
────────────────────────────────
@dataclass
class CodeNode:
    id:           str          # sha256(file_path + ":" + name + ":" + start_line)
    type:         NodeType     # FILE | CLASS | FUNCTION | IMPORT | VARIABLE
    name:         str          # "calculateTotal"
    file_path:    str          # "src/billing/calculator.py"
    start_line:   int          # 42
    end_line:     int          # 78
    signature:    str | None   # "def calculateTotal(self, items) -> Decimal"
    docstring:    str | None   # first docstring paragraph
    children:     list[str]    # child node IDs (methods of a class)
    language:     str          # "python" | "typescript"
    metadata:     dict         # decorators, type hints, async flag, etc.
```

### 2.2 CodeEdge

```
Feature 4: CodeEdge Data Model
────────────────────────────────
@dataclass
class CodeEdge:
    source:    str       # source node ID
    target:    str       # target node ID
    type:      EdgeType  # IMPORTS | CALLS | INHERITS | OVERRIDES | TESTS
    weight:    float     # 1.0 for direct, 0.5 for conditional, etc.
    call_site: int | None  # line number where the call happens
    metadata:  dict      # context (conditional call, loop, etc.)

class EdgeType(Enum):
    IMPORTS   = "imports"   # module A imports from module B
    CALLS     = "calls"     # function X calls function Y
    INHERITS  = "inherits"  # class A extends class B
    OVERRIDES = "overrides" # method A overrides method B in parent
    TESTS     = "tests"     # test_calculate tests calculateTotal
```

---

## 3. Parsers

### 3.1 Python AST Parser

```
Feature 1: Python AST Parser
──────────────────────────────
Library: built-in `ast` module (no external deps)

Extracts:
  - Classes (name, bases, methods, decorators)
  - Functions/async functions (name, args, return type, decorators)
  - Imports (import X, from X import Y — both absolute and relative)
  - Type annotations (function signatures)
  - Docstrings (ast.get_docstring)

```python
import ast

class PythonParser:
    def parse(self, source: str, file_path: str) -> tuple[list[CodeNode], list[CodeEdge]]:
        tree = ast.parse(source)
        visitor = ASTVisitor(file_path)
        visitor.visit(tree)
        return visitor.nodes, visitor.edges
```

### 3.2 TypeScript tree-sitter Parser

```
Feature 2: TypeScript Parser
──────────────────────────────
Library: py-tree-sitter + tree-sitter-typescript

Extracts:
  - Classes (class declarations, abstract classes)
  - Functions (function declarations, arrow functions, methods)
  - Interfaces and type aliases
  - Import/export statements
  - Decorators (@Injectable, @Component, etc.)
```

### 3.3 Import Resolver

```
Feature 5: Import Resolver
────────────────────────────
Problem: `from ..utils import helper` is not a useful edge.
         We need: `shared.utils.helper`

Algorithm:
  1. Walk import node
  2. Determine anchor (the file being parsed)
  3. Resolve relative dots to absolute package path
  4. Look up in module registry (all known files)
  5. Create IMPORTS edge from current file → resolved target

Edge cases:
  - Dynamic imports (importlib.import_module) → mark as DYNAMIC_IMPORT
  - Third-party packages (not in repo) → EXTERNAL_IMPORT (no edge target)
  - Circular: defer resolution until full graph built
```

---

## 4. Graph Construction

### 4.1 Call Graph Builder

```
Feature 6: Call Graph Builder
───────────────────────────────
Phase 1: Build name registry
  Map every function/method to its fully-qualified name
  e.g., "BillingCalculator.calculateTotal" → node_id

Phase 2: Resolve call sites
  For each function, find all ast.Call nodes
  Try to resolve call target:
    - Direct call: foo() → look up "foo" in scope chain
    - Method call: self.foo() → look up in parent class
    - Chained: obj.service.foo() → partial resolution, mark as UNRESOLVED

Phase 3: Build edges
  For each resolved call: add CodeEdge(type=CALLS, source=caller, target=callee)
```

### 4.2 Inheritance Tree

```
Feature 7: Inheritance Tree
─────────────────────────────
For each class with base classes:
  - Resolve each base to a CodeNode
  - Add CodeEdge(type=INHERITS, source=child, target=parent)
  - Build MRO (Method Resolution Order) via C3 linearization

Result:
  - "which classes inherit from BaseModel?" → reverse INHERITS traversal
  - "what's the full MRO of PaymentService?" → traverse INHERITS chain
```

---

## 5. Analysis Algorithms

### 5.1 Impact Analyzer

```
Feature 8: Impact Analyzer
────────────────────────────
Query: "If I change calculateTotal, what breaks?"

Algorithm:
  1. Start from target node (calculateTotal)
  2. Traverse ALL incoming edges (who calls me?)
  3. For each caller, traverse their incoming edges
  4. Continue until no more incoming edges (or max depth 10)
  5. Score each node by distance:
     - Direct callers: blast_radius = HIGH
     - Indirect callers (depth 2): blast_radius = MEDIUM
     - Distant callers (depth 3+): blast_radius = LOW

Output:
  {
    "changed_function": "calculateTotal",
    "direct_callers": ["processOrder", "generateInvoice"],
    "indirect_callers": ["handleCheckout", "runBillingJob"],
    "test_files": ["test_calculator.py", "test_billing_integration.py"],
    "blast_radius_score": 0.72  # 0=isolated, 1=central to everything
  }
```

### 5.2 Dead Code Finder

```
Feature 9: Dead Code Finder
─────────────────────────────
Define entry points:
  - Public API endpoints (FastAPI routes, Flask views)
  - Main functions (__main__)
  - Exported symbols (TypeScript exports)
  - Test functions (test_*)

Algorithm: Graph reachability from entry points
  1. BFS/DFS from all entry point nodes
  2. Mark all reachable nodes
  3. Unreachable nodes = dead code candidates

Output categories:
  - Unreachable functions
  - Unused imports (module imported but no symbols used)
  - Orphan classes (no instantiation, no inheritance)

False positive handling:
  - Mark functions with @api_route / @export as always-reachable
  - Allow manual "keep" annotations
```

### 5.3 Circular Dependency Detector

```
Feature 10: Circular Dependency Detector
──────────────────────────────────────────
Algorithm: DFS with visited/in-stack tracking (Johnson's algorithm)

Output:
  Cycle: A → B → C → A
  Full path: [
    "billing.calculator",
    "billing.pricing",
    "billing.taxes",
    "billing.calculator"    ← back to start
  ]

Severity:
  - Self-import: CRITICAL
  - 2-node cycle (A→B→A): HIGH
  - 3+ node cycle: MEDIUM (often resolvable with dependency injection)
```

### 5.4 Test Coverage Mapper

```
Feature 11: Test Coverage Mapper
──────────────────────────────────
Approach: Naming conventions + import analysis (no runtime needed)

Rule 1 — Naming:
  test_calculator.py tests calculator.py
  BillingServiceTest.ts tests BillingService.ts

Rule 2 — Imports:
  If test_X imports Y, then Y is tested by test_X
  → Add CodeEdge(type=TESTS, source=test_function, target=tested_function)

Rule 3 — Direct call:
  If test_foo() calls calculateTotal() directly → TESTS edge

Output: "calculateTotal is tested by: test_calculateTotal (direct), test_billing_flow (integration)"
Untested: all functions with no incoming TESTS edges
```

---

## 6. Metrics & Scoring

### 6.1 Complexity Scorer

```
Feature 12: Complexity Scorer
───────────────────────────────
Per function:

Cyclomatic Complexity (McCabe):
  = 1 + number of branch points (if, elif, for, while, except, and, or)
  Scale: 1-10 = simple, 11-20 = moderate, 21+ = complex/untestable

Cognitive Complexity (SonarSource):
  More human-readable: increments for nesting, not just branches
  Each level of nesting adds +1 to each branch inside it

Nesting Depth:
  Max depth of nested blocks (if/for/with)
  >4 levels = refactor candidate

LOC:
  Lines of code (excluding blanks and comments)
```

### 6.2 Coupling Analyzer

```
Feature 13: Coupling Analyzer
───────────────────────────────
Per module:

Afferent Coupling (Ca):
  How many other modules depend on this module?
  High Ca = central/stable module — dangerous to change

Efferent Coupling (Ce):
  How many modules does this module depend on?
  High Ce = unstable module — breaks when dependencies change

Instability (I):
  I = Ce / (Ca + Ce)
  I=0 → maximally stable (everyone depends on you, you depend on no one)
  I=1 → maximally unstable (you depend on everyone, no one depends on you)

Martin's Principle:
  Stable packages should be abstract (easy to extend without changing)
  Unstable packages can be concrete
```

---

## 7. Persistence & Lifecycle

### 7.1 SQLite Schema

```
Feature 14: Persistent SQLite Store
──────────────────────────────────────
Tables:

CREATE TABLE nodes (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    signature TEXT,
    docstring TEXT,
    language TEXT,
    metadata JSON,
    content_hash TEXT,
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE edges (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES nodes(id),
    target_id TEXT NOT NULL REFERENCES nodes(id),
    type TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    call_site INTEGER,
    metadata JSON
);

CREATE TABLE snapshots (
    id TEXT PRIMARY KEY,
    commit_hash TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    node_count INTEGER,
    edge_count INTEGER
);

CREATE INDEX idx_edges_source ON edges(source_id);
CREATE INDEX idx_edges_target ON edges(target_id);
CREATE INDEX idx_nodes_file ON nodes(file_path);
```

### 7.2 Incremental Update

```
Feature 15: Incremental Update
────────────────────────────────
Trigger: git commit hook or CI step

Algorithm:
  1. git diff HEAD~1..HEAD → list of changed file paths
  2. For each changed file:
     a. Re-parse → get new nodes and edges
     b. Delete old nodes for this file from SQLite
     c. Delete all edges where source or target was from this file
     d. Insert new nodes
     e. Re-resolve edges for new nodes (may reference other files)
  3. Log: "Re-parsed 3 files, updated 47 nodes, 89 edges"
```

### 7.3 Snapshot & Diff

```
Feature 16: Snapshot & Diff
─────────────────────────────
Save snapshot:
  INSERT INTO snapshots (commit_hash, node_count, edge_count)
  + dump all current node/edge IDs to snapshot_nodes / snapshot_edges tables

Diff two snapshots:
  added_nodes   = nodes in snapshot_B not in snapshot_A
  removed_nodes = nodes in snapshot_A not in snapshot_B
  added_edges   = same for edges
  modified:     same node ID, different signature or complexity score

Output:
  "Between commit abc and def:
   - Added: processRefund(), handleCancellation()
   - Removed: legacyCalculate() [dead code]
   - Complexity increased: calculateTotal (8 → 14)"
```

---

## 8. Query API

```
Feature 18: Query API
──────────────────────
Interface: CodeDomQuery

# Find all callers of a function (direct + indirect)
dom.find_callers("calculateTotal", depth=3)

# Find all functions not covered by any test
dom.find_untested_functions()

# Find functions with cyclomatic complexity > threshold
dom.find_by_complexity(min_complexity=10)

# Find all circular import chains
dom.find_circular_dependencies()

# Get impact blast radius for a given node
dom.get_impact("calculateTotal")

# Find dead code (unreachable from entry points)
dom.find_dead_code(entry_points=["main", "app.routes"])

# Get coupling stats for a module
dom.get_coupling("billing.calculator")

# Find all functions that call a given external API
dom.find_callers_of_external("stripe.charge")
```

---

## 9. Advisors & Visualization

### 9.1 Change Advisor

```
Feature 19: Change Advisor
────────────────────────────
Input: set of changed functions (from git diff)
Output: recommended follow-up actions

"You changed calculateTotal:
  → Update these 3 direct callers:
      processOrder() at billing/orders.py:89
      generateInvoice() at billing/invoices.py:156
      runMonthlyJob() at jobs/monthly.py:34
  → Add/update these tests:
      test_calculateTotal (missing edge case for empty items)
      test_billing_integration (end-to-end smoke test)
  → Check these indirect callers:
      handleCheckout() (depth-2, may be affected by signature change)"
```

### 9.2 Mermaid Diagram Export

```
Feature 21: Mermaid Diagram Export
─────────────────────────────────────
Dependency graph (flowchart):
  graph TD
    billing_calculator --> billing_pricing
    billing_calculator --> shared_config
    billing_orders --> billing_calculator
    billing_invoices --> billing_calculator

Class diagram:
  classDiagram
    BillingBase <|-- BillingCalculator
    BillingBase <|-- BillingValidator
    BillingCalculator : +calculateTotal(items)
    BillingCalculator : +applyDiscount(total, code)

Sequence diagram (call graph for a function):
  sequenceDiagram
    handleCheckout ->> processOrder: call
    processOrder ->> calculateTotal: call
    calculateTotal ->> applyTax: call
```

### 9.3 Repo Stats Report

```
Feature 23: Repo Stats Report
───────────────────────────────
{
  "summary": {
    "total_files": 847,
    "total_functions": 3_204,
    "total_classes": 287,
    "avg_complexity": 4.2,
    "test_coverage_pct": 68.4,
    "dead_code_pct": 8.1,
    "circular_dependencies": 3
  },
  "hot_spots": [
    {"name": "calculateTotal", "complexity": 22, "callers": 14},
    {"name": "processOrder", "complexity": 18, "callers": 9}
  ],
  "coupling": {
    "most_stable": "shared.config",
    "most_unstable": "billing.legacy_adapter"
  }
}
```

---

## 10. Decision Framework

### When to use Code Graph vs codebase_context?

```
You want to...                               Use
────────────────────────────────────────     ──────────────────
Find semantically similar code               codebase_context (embeddings)
Answer "what calls X?"                       code_graph (call graph)
Answer "what does X mean / do?"              codebase_context (embeddings)
Answer "what breaks if I change X?"          code_graph (impact analyzer)
Find functions similar to a description      codebase_context
Find circular imports                        code_graph
Full PR review with context                  Both (code_graph for structure + codebase_context for semantics)
```

---

## 11. Appendix

### Dependencies

```
# Python parsing
ast  # built-in

# TypeScript parsing
py-tree-sitter>=0.21
tree-sitter-languages>=1.10

# Graph algorithms
networkx>=3.0

# Persistence
# SQLite — built-in (sqlite3)

# Visualization
# Mermaid — text output only (no library needed)

# Complexity
radon>=6.0  # cyclomatic + cognitive complexity for Python
```

### Environment Variables

```bash
CODE_DOM_DB_PATH=./code_graph.sqlite
CODE_DOM_MAX_DEPTH=10           # max traversal depth for impact analysis
CODE_DOM_COMPLEXITY_THRESHOLD=10  # flag functions above this
CODE_DOM_ENTRY_POINTS=main,app  # comma-separated for dead code analysis
```

---

## Implementation Status

| Example | Status | Key Classes |
|---------|--------|-------------|
| `python_parser/` | Implemented | `PythonParser` (AST→nodes+edges), `SQLiteCodeDOMStore`, `node_id()` hasher |
| `impact_analyzer/` | Implemented | `ImpactAnalyzer` (BFS blast radius), `CircularDependencyDetector` (DFS cycles), `TestCoverageMapper` |
| `dead_code_finder/` | Implemented | `EntryPointResolver`, `ReachabilityAnalyzer` (BFS), `DeadCodeFinder` |
| `refactor_planner/` | Implemented | `ChangeAdvisor`, `RefactorPlanner`, `MermaidExporter`, `ComplexityScorer`, `RepoStatsCollector` |

### VS Code Integration

The Code Graph is wired into the Phase 0 VS Code extension via the `@codedom` chat participant:

| Command | What It Does |
|---------|-------------|
| `@codedom /impact <symbol>` | Analyse blast radius of changing a symbol |
| `@codedom /deadcode` | Find unreachable functions and unused imports |
| `@codedom /refactor <symbol>` | Plan a rename refactor across callers |
| `@codedom /mermaid <symbol>` | Export dependency graph as Mermaid diagram |

The extension scans workspace Python files, extracts symbols, and provides this context to Copilot for structural analysis.
