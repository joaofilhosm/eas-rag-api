-- ================================================
-- EAS - Base de Conhecimento RAG
-- Schema PostgreSQL + pgvector (Supabase)
-- ================================================

-- Extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ================================================
-- Tabela: api_keys
-- Armazena chaves de acesso à API
-- ================================================
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_hash VARCHAR(32) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    email VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    request_count INTEGER DEFAULT 0
);

CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_is_active ON api_keys(is_active);

-- ================================================
-- Tabela: sources
-- Fontes de dados (sites, APIs, etc)
-- ================================================
CREATE TABLE IF NOT EXISTS sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    url VARCHAR(500) NOT NULL,
    type VARCHAR(50) DEFAULT 'general',
    is_active BOOLEAN DEFAULT true,
    last_scraped_at TIMESTAMPTZ,
    scrape_frequency_hours INTEGER DEFAULT 24,
    total_items INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    config JSONB DEFAULT '{}'
);

CREATE INDEX idx_sources_type ON sources(type);
CREATE INDEX idx_sources_is_active ON sources(is_active);

-- ================================================
-- Tabela: knowledge_base
-- Base de conhecimento principal
-- ================================================
CREATE TABLE IF NOT EXISTS knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES sources(id) ON DELETE SET NULL,
    titulo VARCHAR(500) NOT NULL,
    conteudo TEXT NOT NULL,
    categoria VARCHAR(100),
    tags TEXT[],
    url_original VARCHAR(1000),
    metadata JSONB DEFAULT '{}',
    embedding_status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_knowledge_base_categoria ON knowledge_base(categoria);
CREATE INDEX idx_knowledge_base_source_id ON knowledge_base(source_id);
CREATE INDEX idx_knowledge_base_created_at ON knowledge_base(created_at DESC);
GIN INDEX idx_knowledge_base_tags ON knowledge_base USING GIN(tags);

-- ================================================
-- Tabela: embeddings
-- Embeddings vetoriais (pgvector)
-- ================================================
CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_id UUID REFERENCES knowledge_base(id) ON DELETE CASCADE,
    embedding VECTOR(1536),
    model VARCHAR(100) DEFAULT 'text-embedding-3-small',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índice HNSW para busca vetorial (mais rápido que IVFFlat)
CREATE INDEX idx_embeddings_vector ON embeddings USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_embeddings_knowledge_id ON embeddings(knowledge_id);

-- ================================================
-- Tabela: scrape_logs
-- Histórico de execuções do scraper
-- ================================================
CREATE TABLE IF NOT EXISTS scrape_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES sources(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,
    items_extracted INTEGER DEFAULT 0,
    items_failed INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_seconds FLOAT
);

CREATE INDEX idx_scrape_logs_source_id ON scrape_logs(source_id);
CREATE INDEX idx_scrape_logs_started_at ON scrape_logs(started_at DESC);

-- ================================================
-- Tabela: search_logs
-- Histórico de buscas (analytics)
-- ================================================
CREATE TABLE IF NOT EXISTS search_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_id UUID REFERENCES api_keys(id) ON DELETE SET NULL,
    query TEXT NOT NULL,
    results_count INTEGER DEFAULT 0,
    avg_similarity FLOAT,
    search_type VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_search_logs_created_at ON search_logs(created_at DESC);

-- ================================================
-- Funções
-- ================================================

-- Função para busca semântica (cosine similarity)
CREATE OR REPLACE FUNCTION search_knowledge(
    query_embedding VECTOR(1536),
    limit_count INTEGER DEFAULT 10,
    min_similarity FLOAT DEFAULT 0.5,
    filter_category VARCHAR DEFAULT NULL,
    filter_tags TEXT[] DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    titulo VARCHAR(500),
    conteudo TEXT,
    categoria VARCHAR(100),
    tags TEXT[],
    url_original VARCHAR(1000),
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        kb.id,
        kb.titulo,
        kb.conteudo,
        kb.categoria,
        kb.tags,
        kb.url_original,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM knowledge_base kb
    JOIN embeddings e ON kb.id = e.knowledge_id
    WHERE
        (filter_category IS NULL OR kb.categoria = filter_category)
        AND (filter_tags IS NULL OR kb.tags && filter_tags)
        AND 1 - (e.embedding <=> query_embedding) >= min_similarity
    ORDER BY e.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Função para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para knowledge_base
CREATE TRIGGER update_knowledge_base_updated_at
    BEFORE UPDATE ON knowledge_base
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger para sources
CREATE TRIGGER update_sources_updated_at
    BEFORE UPDATE ON sources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ================================================
-- Dados iniciais
-- ================================================

-- Fontes padrão
INSERT INTO sources (name, url, type, scrape_frequency_hours, config) VALUES
('Dicas de Treino', 'https://www.dicasdetreino.com.br', 'fitness', 24, '{"priority": "high", "language": "pt-BR"}'),
('Hipertrofia.org', 'https://www.hipertrofia.org', 'fitness', 24, '{"priority": "high", "language": "pt-BR"}'),
('SciELO', 'https://scielo.org', 'scientific', 168, '{"priority": "medium", "language": "multi"}'),
('PubMed', 'https://pubmed.ncbi.nlm.nih.gov', 'scientific', 168, '{"priority": "medium", "language": "en"}'),
('LILACS', 'https://lilacs.bvsalud.org', 'scientific', 168, '{"priority": "medium", "language": "multi"}')
ON CONFLICT DO NOTHING;

-- ================================================
-- Views úteis
-- ================================================

-- View para estatísticas gerais
CREATE OR REPLACE VIEW v_stats AS
SELECT
    (SELECT COUNT(*) FROM knowledge_base) AS total_knowledge,
    (SELECT COUNT(*) FROM sources WHERE is_active = true) AS active_sources,
    (SELECT COUNT(*) FROM api_keys WHERE is_active = true) AS active_api_keys,
    (SELECT COUNT(*) FROM embeddings) AS total_embeddings,
    (SELECT MAX(created_at) FROM knowledge_base) AS last_knowledge_added,
    (SELECT MAX(started_at) FROM scrape_logs) AS last_scrape_run;

-- View para fontes que precisam de scraping
CREATE OR REPLACE VIEW v_sources_needing_scrape AS
SELECT
    s.id,
    s.name,
    s.url,
    s.type,
    s.last_scraped_at,
    s.scrape_frequency_hours
FROM sources s
WHERE
    s.is_active = true
    AND (
        s.last_scraped_at IS NULL
        OR s.last_scraped_at < NOW() - (s.scrape_frequency_hours || ' hours')::INTERVAL
    );

-- ================================================
-- Comentários
-- ================================================
COMMENT ON TABLE api_keys IS 'Chaves de acesso à API RAG';
COMMENT ON TABLE sources IS 'Fontes de dados para scraping';
COMMENT ON TABLE knowledge_base IS 'Base de conhecimento principal';
COMMENT ON TABLE embeddings IS 'Embeddings vetoriais para busca semântica';
COMMENT ON TABLE scrape_logs IS 'Histórico de execuções do scraper';
COMMENT ON TABLE search_logs IS 'Histórico de buscas para analytics';

COMMENT ON FUNCTION search_knowledge IS 'Busca semântica na base de conhecimento usando similaridade de cosseno';