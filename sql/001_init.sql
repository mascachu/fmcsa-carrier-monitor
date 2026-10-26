CREATE TABLE IF NOT EXISTS monitored_companies (
    id BIGSERIAL PRIMARY KEY,
    external_company_key TEXT NOT NULL UNIQUE,
    company_name TEXT NOT NULL,
    zoho_account_id TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Separate identifiers allow one business to have multiple USDOT/MC (docket) numbers.
CREATE TABLE IF NOT EXISTS monitored_company_identifiers (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES monitored_companies(id) ON DELETE CASCADE,
    identifier_type TEXT NOT NULL CHECK (identifier_type IN ('usdot', 'mc')),
    identifier_value TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT monitored_identifier_unique UNIQUE (identifier_type, identifier_value)
);
CREATE INDEX IF NOT EXISTS idx_monitored_identifiers_lookup ON monitored_company_identifiers (identifier_type, identifier_value);
CREATE INDEX IF NOT EXISTS idx_monitored_companies_active ON monitored_companies (is_active);

CREATE TABLE IF NOT EXISTS source_snapshots (
    id BIGSERIAL PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_record_key TEXT NOT NULL,
    usdot_number TEXT,
    docket_number TEXT,
    payload JSONB NOT NULL,
    payload_hash CHAR(64) NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_name, source_record_key)
);
CREATE INDEX IF NOT EXISTS idx_source_snapshots_usdot ON source_snapshots (usdot_number);
CREATE INDEX IF NOT EXISTS idx_source_snapshots_docket ON source_snapshots (docket_number);

CREATE TABLE IF NOT EXISTS change_events (
    id BIGSERIAL PRIMARY KEY,
    event_key CHAR(64) NOT NULL UNIQUE,
    company_id BIGINT NOT NULL REFERENCES monitored_companies(id),
    source_name TEXT NOT NULL,
    source_record_key TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_date DATE,
    severity TEXT NOT NULL DEFAULT 'medium',
    summary TEXT NOT NULL,
    changed_fields JSONB NOT NULL DEFAULT '{}'::jsonb,
    old_payload JSONB,
    new_payload JSONB NOT NULL,
    zoho_status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_change_events_company_date ON change_events (company_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_change_events_zoho_status ON change_events (zoho_status, created_at);
CREATE INDEX IF NOT EXISTS idx_change_events_type ON change_events (event_type, created_at DESC);

CREATE TABLE IF NOT EXISTS daily_runs (
    id BIGSERIAL PRIMARY KEY,
    run_key TEXT NOT NULL UNIQUE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running',
    source_counts JSONB NOT NULL DEFAULT '{}'::jsonb,
    rows_matched INTEGER NOT NULL DEFAULT 0,
    events_created INTEGER NOT NULL DEFAULT 0,
    errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    report_path TEXT
);

CREATE TABLE IF NOT EXISTS delivery_attempts (
    id BIGSERIAL PRIMARY KEY,
    event_id BIGINT NOT NULL REFERENCES change_events(id),
    destination TEXT NOT NULL,
    status TEXT NOT NULL,
    response_detail TEXT,
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_delivery_attempts_event ON delivery_attempts (event_id, attempted_at DESC);
