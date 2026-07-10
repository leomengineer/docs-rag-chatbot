CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunks (
  id              bigserial PRIMARY KEY,
  source_filename text NOT NULL,
  doc_title       text NOT NULL,
  chunk           text NOT NULL,
  embedding       vector(384),
  tsv             tsvector GENERATED ALWAYS AS (to_tsvector('english', chunk)) STORED
);

CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw
  ON chunks USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS chunks_tsv_gin
  ON chunks USING gin (tsv);
