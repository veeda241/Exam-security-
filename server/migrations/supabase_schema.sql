-- =============================================================================
-- ExamGuard Pro — Full Supabase Schema
-- =============================================================================
-- Run once in: Supabase Dashboard → SQL Editor → New query → Run
-- Or locally:  python setup_database.py
--
-- Backend tip: set SUPABASE_KEY to the **service_role** key (Settings → API)
-- so the FastAPI server can read/write all tables (custom JWT auth, not Supabase Auth).
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -----------------------------------------------------------------------------
-- 1. Authentication (used by server/auth/service.py)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id              BIGSERIAL PRIMARY KEY,
  email           TEXT NOT NULL UNIQUE,
  username        TEXT NOT NULL UNIQUE,
  hashed_password TEXT NOT NULL,
  full_name       TEXT,
  role            TEXT NOT NULL DEFAULT 'student'
                  CHECK (role IN ('admin', 'proctor', 'instructor', 'student')),
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  is_verified     BOOLEAN NOT NULL DEFAULT FALSE,
  failed_login_attempts INT NOT NULL DEFAULT 0,
  locked_until    TIMESTAMPTZ,
  last_login      TIMESTAMPTZ,
  password_changed_at TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
  id          BIGSERIAL PRIMARY KEY,
  user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash  TEXT NOT NULL,
  expires_at  TIMESTAMPTZ NOT NULL,
  user_agent  TEXT,
  ip_address  TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  revoked     BOOLEAN NOT NULL DEFAULT FALSE,
  revoked_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON refresh_tokens(token_hash);

-- -----------------------------------------------------------------------------
-- 2. V2 core (used by server/api/*.py — exams, sessions, events, reports)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS profiles (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    BIGINT UNIQUE REFERENCES users(id) ON DELETE SET NULL,
  role       TEXT NOT NULL DEFAULT 'student'
             CHECK (role IN ('student', 'proctor', 'admin')),
  full_name  TEXT,
  email      TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS exams (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title            TEXT NOT NULL,
  created_by       BIGINT REFERENCES users(id) ON DELETE SET NULL,
  starts_at        TIMESTAMPTZ,
  duration_minutes INT,
  ruleset          JSONB NOT NULL DEFAULT '{}',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sessions (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  exam_id          UUID REFERENCES exams(id) ON DELETE CASCADE,
  student_id       BIGINT REFERENCES users(id) ON DELETE SET NULL,
  status           TEXT NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending', 'active', 'completed', 'terminated')),
  started_at       TIMESTAMPTZ,
  ended_at         TIMESTAMPTZ,
  risk_score       NUMERIC NOT NULL DEFAULT 0,
  risk_level       TEXT NOT NULL DEFAULT 'safe'
                   CHECK (risk_level IN ('safe', 'review', 'suspicious')),
  consent_metadata JSONB NOT NULL DEFAULT '{}',
  monitoring_tier  TEXT NOT NULL DEFAULT 'full',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS v2_events (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id     UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  type           TEXT NOT NULL,
  payload        JSONB NOT NULL DEFAULT '{}',
  weight         NUMERIC NOT NULL DEFAULT 0,
  screenshot_url TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_configs (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  version    INT NOT NULL,
  weights    JSONB NOT NULL,
  thresholds JSONB NOT NULL,
  active     BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reports (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id   UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  storage_path TEXT,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_exams_created_by ON exams(created_by);
CREATE INDEX IF NOT EXISTS idx_sessions_exam_id ON sessions(exam_id);
CREATE INDEX IF NOT EXISTS idx_sessions_student_id ON sessions(student_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_v2_events_session_id ON v2_events(session_id);
CREATE INDEX IF NOT EXISTS idx_v2_events_created_at ON v2_events(created_at);
CREATE INDEX IF NOT EXISTS idx_risk_configs_active ON risk_configs(active) WHERE active = TRUE;
CREATE INDEX IF NOT EXISTS idx_reports_session_id ON reports(session_id);

-- Default risk weights (V2 risk engine)
INSERT INTO risk_configs (version, weights, thresholds, active)
SELECT 1,
  '{
    "tab_switch": 10, "window_blur": 5, "copy_paste": 15,
    "face_missing": 20, "multiple_faces": 25, "gaze_away": 15,
    "ocr_flag": 40, "object_flag": 25, "text_similarity": 35,
    "forbidden_site": 40, "page_hidden": 8
  }'::jsonb,
  '{"review": 30, "suspicious": 60}'::jsonb,
  TRUE
WHERE NOT EXISTS (SELECT 1 FROM risk_configs WHERE version = 1);

-- -----------------------------------------------------------------------------
-- 3. V1 legacy (dashboard, extension, analysis pipeline)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS students (
  id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  name        TEXT NOT NULL,
  email       TEXT,
  department  TEXT,
  year        TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_students_email ON students(email);

CREATE TABLE IF NOT EXISTS exam_sessions (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id           TEXT,
  exam_id              TEXT,
  is_active            BOOLEAN NOT NULL DEFAULT TRUE,
  started_at           TIMESTAMPTZ,
  ended_at             TIMESTAMPTZ,
  status               TEXT DEFAULT 'recording',
  risk_score           NUMERIC NOT NULL DEFAULT 0,
  risk_level           TEXT DEFAULT 'safe',
  engagement_score     NUMERIC DEFAULT 100,
  content_relevance    NUMERIC DEFAULT 100,
  effort_alignment     NUMERIC DEFAULT 100,
  forbidden_site_count INT DEFAULT 0,
  face_absence_count   INT DEFAULT 0,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_exam_sessions_student ON exam_sessions(student_id);
CREATE INDEX IF NOT EXISTS idx_exam_sessions_exam ON exam_sessions(exam_id);
CREATE INDEX IF NOT EXISTS idx_exam_sessions_active ON exam_sessions(is_active);

CREATE TABLE IF NOT EXISTS events (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id       UUID REFERENCES exam_sessions(id) ON DELETE CASCADE,
  event_type       TEXT NOT NULL,
  client_timestamp BIGINT,
  data             JSONB NOT NULL DEFAULT '{}',
  risk_weight      INT NOT NULL DEFAULT 0,
  timestamp        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_session_id ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);

CREATE TABLE IF NOT EXISTS analysis_results (
  id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id               UUID,
  timestamp                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  risk_score_added         NUMERIC DEFAULT 0,
  face_detected            BOOLEAN,
  detected_text            TEXT,
  forbidden_keywords_found JSONB DEFAULT '[]',
  similarity_score         NUMERIC DEFAULT 0,
  result_data              JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_analysis_results_session ON analysis_results(session_id);

CREATE TABLE IF NOT EXISTS research_journey (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id       UUID,
  url              TEXT,
  title            TEXT,
  timestamp        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  duration_seconds INT DEFAULT 0,
  category         TEXT,
  risk_level       TEXT
);

CREATE INDEX IF NOT EXISTS idx_research_journey_session ON research_journey(session_id);

-- -----------------------------------------------------------------------------
-- 4. Row Level Security (optional — backend should use service_role key)
-- -----------------------------------------------------------------------------
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE exams ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE v2_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE students ENABLE ROW LEVEL SECURITY;
ALTER TABLE exam_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_journey ENABLE ROW LEVEL SECURITY;

-- Service role bypasses RLS automatically. These policies allow read for authenticated Supabase Auth users if added later.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'users' AND policyname = 'users_service_all') THEN
    CREATE POLICY users_service_all ON users FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'sessions' AND policyname = 'sessions_service_all') THEN
    CREATE POLICY sessions_service_all ON sessions FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'exams' AND policyname = 'exams_service_all') THEN
    CREATE POLICY exams_service_all ON exams FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'v2_events' AND policyname = 'v2_events_service_all') THEN
    CREATE POLICY v2_events_service_all ON v2_events FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END $$;

-- -----------------------------------------------------------------------------
-- 5. Storage buckets (reports & screenshots) — safe to re-run
-- -----------------------------------------------------------------------------
INSERT INTO storage.buckets (id, name, public)
VALUES ('reports', 'reports', false)
ON CONFLICT (id) DO NOTHING;

INSERT INTO storage.buckets (id, name, public)
VALUES ('screenshots', 'screenshots', false)
ON CONFLICT (id) DO NOTHING;
