-- =====================================================================
-- Log Analyser : schéma PostgreSQL (même contenu que storage/schema.py)
-- A exécuter dans DBeaver (Ctrl+Entrée par requête, Alt+X pour tout)
-- 1) connecté à la base "postgres"   : partie 1
-- 2) connecté à la base "log_analysis" : partie 2
-- (python main.py import fait les deux automatiquement)
-- =====================================================================

-- ---------- partie 1 : utilisateur + base (connexion postgres / superuser) ----------
-- à sauter si l'utilisateur et la base existent déjà
CREATE ROLE nasser LOGIN PASSWORD 'nasser' CREATEDB;   -- même valeurs que .env
CREATE DATABASE log_analysis OWNER nasser;

-- ---------- partie 2 : table, index, commentaires, vues (connexion log_analysis) ----------
CREATE TABLE IF NOT EXISTS t_ssh_events (
    id SERIAL PRIMARY KEY,
    date_time TIMESTAMP NOT NULL,
    host VARCHAR(100),
    status VARCHAR(10) NOT NULL CHECK (status IN ('FAILED', 'ACCEPTED')),
    username VARCHAR(255),
    invalid_user BOOLEAN NOT NULL DEFAULT FALSE,
    ip_address INET NOT NULL,
    port INTEGER CHECK (port BETWEEN 0 AND 65535),
    country VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_status ON t_ssh_events (status);
CREATE INDEX IF NOT EXISTS idx_country ON t_ssh_events (country);
CREATE INDEX IF NOT EXISTS idx_username ON t_ssh_events (username);
CREATE INDEX IF NOT EXISTS idx_date_time ON t_ssh_events (date_time);

COMMENT ON TABLE t_ssh_events IS 'Tentatives de connexion SSH (Failed/Accepted) extraites des fichiers auth.log';
COMMENT ON COLUMN t_ssh_events.date_time IS 'Date et heure de la tentative (année ajoutée par le pipeline)';
COMMENT ON COLUMN t_ssh_events.host IS 'Serveur qui a écrit le log';
COMMENT ON COLUMN t_ssh_events.status IS 'FAILED ou ACCEPTED';
COMMENT ON COLUMN t_ssh_events.username IS 'Utilisateur utilisé pour la connexion';
COMMENT ON COLUMN t_ssh_events.invalid_user IS 'TRUE si le log contient "invalid user" (user inexistant)';
COMMENT ON COLUMN t_ssh_events.ip_address IS 'Adresse IP source';
COMMENT ON COLUMN t_ssh_events.port IS 'Port source';
COMMENT ON COLUMN t_ssh_events.country IS 'Code pays ipinfo (ex : CN, US) ; NULL si non géolocalisé';

CREATE OR REPLACE VIEW v_failed_by_country AS
    SELECT COALESCE(NULLIF(country, ''), 'Inconnu') AS pays, COUNT(*) AS total
    FROM t_ssh_events WHERE status = 'FAILED'
    GROUP BY 1 ORDER BY total DESC;

CREATE OR REPLACE VIEW v_success_by_user AS
    SELECT username, COUNT(*) AS total
    FROM t_ssh_events WHERE status = 'ACCEPTED'
    GROUP BY username ORDER BY total DESC;

CREATE OR REPLACE VIEW v_failed_invalid_users AS
    SELECT username, COUNT(*) AS total
    FROM t_ssh_events WHERE status = 'FAILED' AND invalid_user
    GROUP BY username ORDER BY total DESC;

CREATE OR REPLACE VIEW v_summary AS
    SELECT COUNT(*) AS total, COUNT(DISTINCT ip_address) AS ip_uniques,
           COUNT(*) FILTER (WHERE status = 'FAILED') AS echecs,
           ROUND(COUNT(*) FILTER (WHERE status = 'FAILED') * 100.0 / NULLIF(COUNT(*), 0), 2) AS taux_echec
    FROM t_ssh_events;

-- ---------- vérifications ----------
SELECT * FROM v_summary;
SELECT * FROM v_failed_by_country LIMIT 15;
SELECT * FROM v_success_by_user;
SELECT * FROM v_failed_invalid_users LIMIT 15;
