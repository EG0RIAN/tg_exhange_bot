-- users
CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  tg_id BIGINT UNIQUE NOT NULL,
  first_name TEXT,
  username TEXT,
  lang VARCHAR(5) DEFAULT 'ru',
  is_blocked BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- rates
CREATE TABLE IF NOT EXISTS rates (
  id BIGSERIAL PRIMARY KEY,
  pair VARCHAR(16) UNIQUE,
  ask NUMERIC(18,8),
  bid NUMERIC(18,8),
  source VARCHAR(16),
  updated_at TIMESTAMPTZ
);

-- faqs
CREATE TABLE IF NOT EXISTS faqs (
  id BIGSERIAL PRIMARY KEY,
  category TEXT,
  question TEXT,
  answer TEXT,
  sort INT
);

-- orders
CREATE TABLE IF NOT EXISTS orders (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT REFERENCES users(id),
  pair VARCHAR(16),
  amount NUMERIC(18,8),
  payout_method TEXT,
  contact TEXT,
  status VARCHAR(16) DEFAULT 'new',
  rate_snapshot JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- live_chats
CREATE TABLE IF NOT EXISTS live_chats (
  user_id BIGINT PRIMARY KEY,
  started_at TIMESTAMPTZ,
  is_active BOOLEAN
); 