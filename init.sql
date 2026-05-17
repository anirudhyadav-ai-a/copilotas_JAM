-- copilotas_JAM — PostgreSQL initialization
-- Runs automatically when the postgres container first starts.

-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- ── Code DOM: structural graph ──────────────────────────────────
CREATE TABLE IF NOT EXISTS nodes (
    node_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    signature TEXT,
    docstring TEXT,
    language TEXT DEFAULT 'python',
    content_hash TEXT,
    metadata JSONB,
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_nodes_file ON nodes(file_path);

CREATE TABLE IF NOT EXISTS edges (
    edge_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES nodes(node_id) ON DELETE CASCADE,
    target_id TEXT NOT NULL REFERENCES nodes(node_id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    call_site INTEGER,
    metadata JSONB
);
CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);

-- ── Codebase Context: chunk embeddings ─────────────────────────
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    file_path TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    language TEXT,
    chunk_type TEXT,
    name TEXT,
    parent_class TEXT,
    signature TEXT,
    docstring TEXT,
    content TEXT NOT NULL,
    embedding vector(1536),
    content_hash TEXT NOT NULL,
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks
    USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_file_idx ON chunks(file_path);

-- ── CI/CD Governance: reviews + verdicts ───────────────────────
CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    pr_number INTEGER,
    repo TEXT,
    commit_sha TEXT,
    verdict TEXT NOT NULL,
    score REAL,
    files_reviewed INTEGER,
    duration_seconds REAL,
    model TEXT,
    rubric_version TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS review_findings (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    file_path TEXT,
    line_number INTEGER,
    severity TEXT,
    category TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS overrides (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL REFERENCES reviews(id),
    pr_number INTEGER,
    github_user TEXT,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
