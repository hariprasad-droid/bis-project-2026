-- Enable the pgvector extension to work with embedding vectors
create extension if not exists vector;

-- Create a table to store your documents
create table if not exists documents (
  id bigserial primary key,
  content text, -- corresponds to Document.pageContent
  metadata jsonb, -- corresponds to Document.metadata
  embedding vector(768) -- 1536 is the dimension for OpenAI text-embedding-3-small
);

-- Create a function to search for documents
create or replace function match_documents (
  query_embedding vector(768),
  match_threshold float,
  match_count int
)
returns table (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
language sql stable
as $$
  select
    documents.id,
    documents.content,
    documents.metadata,
    1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  where 1 - (documents.embedding <=> query_embedding) > match_threshold
  order by documents.embedding <=> query_embedding
  limit match_count;
$$;

-- =====================================================================
-- ULTRA RAG MIGRATION: Hybrid search (keyword + vector, fused with RRF)
-- Safe to run multiple times. Run in the Supabase SQL editor.
-- =====================================================================

-- Full-text search column (content + title), auto-maintained by Postgres
alter table documents
  add column if not exists fts tsvector
  generated always as (
    to_tsvector('english', coalesce(content, '') || ' ' || coalesce(metadata->>'title', ''))
  ) stored;

create index if not exists documents_fts_idx on documents using gin (fts);

-- Approximate nearest-neighbour index for fast cosine search
create index if not exists documents_embedding_hnsw_idx
  on documents using hnsw (embedding vector_cosine_ops);

-- Hybrid search: Reciprocal Rank Fusion of full-text rank and vector rank.
-- query_text should be an OR-joined keyword string, e.g. 'hallmarking or huid or 10500'
create or replace function hybrid_search (
  query_text text,
  query_embedding vector(768),
  match_count int,
  full_text_weight float default 1.0,
  semantic_weight float default 1.0,
  rrf_k int default 50
)
returns table (
  id bigint,
  content text,
  metadata jsonb,
  similarity float,
  keyword_rank int,
  semantic_rank int,
  score float
)
language sql stable
as $$
  with full_text as (
    select
      d.id,
      row_number() over (
        order by ts_rank_cd(d.fts, websearch_to_tsquery('english', query_text)) desc
      )::int as rank_ix
    from documents d
    where d.fts @@ websearch_to_tsquery('english', query_text)
    order by rank_ix
    limit least(match_count, 50) * 2
  ),
  semantic as (
    select
      d.id,
      row_number() over (order by d.embedding <=> query_embedding)::int as rank_ix
    from documents d
    order by rank_ix
    limit least(match_count, 50) * 2
  )
  select
    d.id,
    d.content,
    d.metadata,
    1 - (d.embedding <=> query_embedding) as similarity,
    full_text.rank_ix as keyword_rank,
    semantic.rank_ix as semantic_rank,
    coalesce(1.0 / (rrf_k + full_text.rank_ix), 0.0) * full_text_weight +
    coalesce(1.0 / (rrf_k + semantic.rank_ix), 0.0) * semantic_weight as score
  from full_text
  full outer join semantic on full_text.id = semantic.id
  join documents d on d.id = coalesce(full_text.id, semantic.id)
  order by score desc
  limit match_count;
$$;
