-- Run this once to set up the database.
-- psql -U postgres -f schema.sql

CREATE DATABASE failure_prediction_ai;

\c failure_prediction_ai;

CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    startup_name VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    business_model VARCHAR(100),
    target_market VARCHAR(100),
    budget VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Stores the AI-generated analysis so results persist and don't need
-- to be recomputed every time the founder revisits their dashboard.
CREATE TABLE IF NOT EXISTS analyses (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES projects(id) ON DELETE CASCADE,
    sector_growth VARCHAR(20),
    overall_risk NUMERIC(5,2),
    market_risk NUMERIC(5,2),
    capital_risk NUMERIC(5,2),
    execution_risk NUMERIC(5,2),
    competition_risk NUMERIC(5,2),
    regulatory_risk NUMERIC(5,2),
    success_probability NUMERIC(5,2),
    failure_probability NUMERIC(5,2),
    revenue_projection JSONB,       -- array of 6 monthly figures
    positioning_summary TEXT,
    audience_profile TEXT,
    market_maturity VARCHAR(20),    -- Emerging / Growing / Mature / Declining
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- TAM / SAM / SOM market sizing, one row per analysis run.
CREATE TABLE IF NOT EXISTS market_sizing (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES projects(id) ON DELETE CASCADE,
    tam NUMERIC(18,2),
    sam NUMERIC(18,2),
    som NUMERIC(18,2),
    methodology_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Key market trends relevant to the startup's sector, one row per trend.
CREATE TABLE IF NOT EXISTS market_trends (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES projects(id) ON DELETE CASCADE,
    trend VARCHAR(150),
    description TEXT,
    impact VARCHAR(20),             -- High / Medium / Low
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Target customer segments and their estimated share of the addressable market.
CREATE TABLE IF NOT EXISTS customer_segments (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES projects(id) ON DELETE CASCADE,
    segment VARCHAR(150),
    description TEXT,
    percentage NUMERIC(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Competitor benchmarking, one row per competitor per analysis run.
CREATE TABLE IF NOT EXISTS competitors (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES projects(id) ON DELETE CASCADE,
    competitor_name VARCHAR(150),
    market_share_estimate NUMERIC(5,2),
    positioning_notes TEXT,
    funding_stage VARCHAR(50),
    threat_level VARCHAR(20),       -- High / Medium / Low
    strengths JSONB,                -- array of short strings
    weaknesses JSONB,               -- array of short strings
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- One mitigation step per risk category, one row per analysis run.
CREATE TABLE IF NOT EXISTS risk_mitigations (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES projects(id) ON DELETE CASCADE,
    category VARCHAR(50),           -- Market / Capital / Execution / Competition / Regulatory
    mitigation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- SWOT-style recommendations, one row per item per analysis run.
CREATE TABLE IF NOT EXISTS recommendations (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES projects(id) ON DELETE CASCADE,
    category VARCHAR(20),           -- Strength / Weakness / Opportunity / Threat
    recommendation_text TEXT,
    priority VARCHAR(20),           -- High / Medium / Low
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 30/60/90-day action roadmap, one row per phase per analysis run.
CREATE TABLE IF NOT EXISTS action_plan (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES projects(id) ON DELETE CASCADE,
    phase VARCHAR(30),              -- e.g. "0-30 days"
    focus TEXT,
    actions JSONB,                  -- array of short strings
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Technology adoption lifecycle distribution, one row per segment per analysis run.
CREATE TABLE IF NOT EXISTS adoption_distribution (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES projects(id) ON DELETE CASCADE,
    segment VARCHAR(50),            -- Innovators / Early Adopters / Early Majority / Late Majority / Laggards
    percentage NUMERIC(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5-year historical market size trend, one row per year per analysis run.
CREATE TABLE IF NOT EXISTS market_growth_history (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES projects(id) ON DELETE CASCADE,
    year INT,
    market_size NUMERIC(18,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sector-wide challenges (not specific to one competitor), one row per item per analysis run.
CREATE TABLE IF NOT EXISTS industry_challenges (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES projects(id) ON DELETE CASCADE,
    challenge VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Composite growth potential score and its sub-dimensions, one row per analysis run.
CREATE TABLE IF NOT EXISTS growth_potential (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES projects(id) ON DELETE CASCADE,
    score NUMERIC(5,2),
    explanation TEXT,
    market_validation NUMERIC(5,2),
    competitive_position NUMERIC(5,2),
    financial_model NUMERIC(5,2),
    technical_readiness NUMERIC(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Concrete, startup-specific market opportunities, one row per item per analysis run.
CREATE TABLE IF NOT EXISTS market_opportunities (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES projects(id) ON DELETE CASCADE,
    opportunity VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
