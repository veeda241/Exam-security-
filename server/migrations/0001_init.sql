-- ExamGuard Pro V2 — initial schema (additive alongside V1 tables)

-- Profiles extend Supabase Auth users (or legacy users table)
CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY,
  role TEXT CHECK (role IN ('student', 'proctor', 'admin')) NOT NULL DEFAULT 'student',
  full_name TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS exams (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  created_by BIGINT,
  starts_at TIMESTAMPTZ,
  duration_minutes INT,
  ruleset JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  exam_id UUID REFERENCES exams(id),
  student_id BIGINT,
  status TEXT CHECK (status IN ('pending', 'active', 'completed', 'terminated')) DEFAULT 'pending',
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  risk_score NUMERIC DEFAULT 0,
  risk_level TEXT CHECK (risk_level IN ('safe', 'review', 'suspicious')) DEFAULT 'safe',
  consent_metadata JSONB DEFAULT '{}',
  monitoring_tier TEXT DEFAULT 'full',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS v2_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
  type TEXT NOT NULL,
  payload JSONB DEFAULT '{}',
  weight NUMERIC DEFAULT 0,
  screenshot_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_configs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  version INT NOT NULL,
  weights JSONB NOT NULL,
  thresholds JSONB NOT NULL,
  active BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
  storage_path TEXT,
  generated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_exam_id ON sessions(exam_id);
CREATE INDEX IF NOT EXISTS idx_sessions_student_id ON sessions(student_id);
CREATE INDEX IF NOT EXISTS idx_v2_events_session_id ON v2_events(session_id);
CREATE INDEX IF NOT EXISTS idx_v2_events_created_at ON v2_events(created_at);
CREATE INDEX IF NOT EXISTS idx_risk_configs_active ON risk_configs(active) WHERE active = TRUE;

-- Seed default risk config (V1 weights ported)
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

-- RLS
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE exams ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE v2_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;

-- Service role bypasses RLS; policies for authenticated users
CREATE POLICY IF NOT EXISTS profiles_self ON profiles
  FOR SELECT USING (auth.uid() = id);

CREATE POLICY IF NOT EXISTS exams_proctor_read ON exams
  FOR SELECT USING (
    created_by = auth.uid()
    OR EXISTS (SELECT 1 FROM profiles p WHERE p.id = auth.uid() AND p.role = 'admin')
  );

CREATE POLICY IF NOT EXISTS sessions_student_own ON sessions
  FOR SELECT USING (student_id = auth.uid());

CREATE POLICY IF NOT EXISTS sessions_proctor_exam ON sessions
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM exams e
      WHERE e.id = sessions.exam_id
      AND (e.created_by = auth.uid() OR EXISTS (
        SELECT 1 FROM profiles p WHERE p.id = auth.uid() AND p.role = 'admin'
      ))
    )
  );

CREATE POLICY IF NOT EXISTS events_session_access ON v2_events
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM sessions s
      WHERE s.id = v2_events.session_id
      AND (
        s.student_id = auth.uid()
        OR EXISTS (
          SELECT 1 FROM exams e
          WHERE e.id = s.exam_id AND e.created_by = auth.uid()
        )
        OR EXISTS (SELECT 1 FROM profiles p WHERE p.id = auth.uid() AND p.role = 'admin')
      )
    )
  );

CREATE POLICY IF NOT EXISTS risk_configs_admin ON risk_configs
  FOR ALL USING (
    EXISTS (SELECT 1 FROM profiles p WHERE p.id = auth.uid() AND p.role = 'admin')
  );

CREATE POLICY IF NOT EXISTS reports_session_access ON reports
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM sessions s
      WHERE s.id = reports.session_id
      AND (
        s.student_id = auth.uid()
        OR EXISTS (
          SELECT 1 FROM exams e
          WHERE e.id = s.exam_id AND e.created_by = auth.uid()
        )
        OR EXISTS (SELECT 1 FROM profiles p WHERE p.id = auth.uid() AND p.role = 'admin')
      )
    )
  );
