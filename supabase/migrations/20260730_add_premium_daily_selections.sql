-- ============================================================
-- PE1-006
-- Premium Daily Selection
-- Additive Migration
-- ============================================================

CREATE TABLE IF NOT EXISTS premium_daily_selections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL,

    market_day DATE NOT NULL,

    selected_forecast TEXT NOT NULL CHECK (
        selected_forecast IN (
            'lowest',
            'expected',
            'highest'
        )
    ),

    locked BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS
idx_premium_daily_selection_user_day
ON premium_daily_selections (
    user_id,
    market_day
);

CREATE INDEX IF NOT EXISTS
idx_premium_daily_selection_market_day
ON premium_daily_selections (
    market_day
);

ALTER TABLE premium_daily_selections
ENABLE ROW LEVEL SECURITY;

CREATE POLICY premium_daily_selection_owner
ON premium_daily_selections
FOR ALL
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

CREATE OR REPLACE FUNCTION update_premium_daily_selection_timestamp()
RETURNS TRIGGER AS
$$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$
LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS
premium_daily_selection_timestamp
ON premium_daily_selections;

CREATE TRIGGER premium_daily_selection_timestamp
BEFORE UPDATE
ON premium_daily_selections
FOR EACH ROW
EXECUTE FUNCTION update_premium_daily_selection_timestamp();