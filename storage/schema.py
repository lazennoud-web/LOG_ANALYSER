import sys
from pathlib import Path
import psycopg2
from psycopg2 import sql
sys.path.append(str(Path(__file__).resolve().parent.parent))
import config
from storage.database import Database, connect, rollback, logger

"""
    Schéma PostgreSQL
    out : base PG_DBNAME + table t_ssh_events (une ligne = une tentative SSH)
"""
CREATE_TABLE = """
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
)
"""
CREATE_INDEXES = [
    'CREATE INDEX IF NOT EXISTS idx_status ON t_ssh_events (status)',
    'CREATE INDEX IF NOT EXISTS idx_country ON t_ssh_events (country)',
    'CREATE INDEX IF NOT EXISTS idx_username ON t_ssh_events (username)',
    'CREATE INDEX IF NOT EXISTS idx_date_time ON t_ssh_events (date_time)',
]
COMMENTS = [
    "COMMENT ON TABLE t_ssh_events IS 'Tentatives de connexion SSH (Failed/Accepted) extraites des fichiers auth.log'",
    "COMMENT ON COLUMN t_ssh_events.date_time IS 'Date et heure de la tentative (année ajoutée par le pipeline)'",
    "COMMENT ON COLUMN t_ssh_events.host IS 'Serveur qui a écrit le log'",
    "COMMENT ON COLUMN t_ssh_events.status IS 'FAILED ou ACCEPTED'",
    "COMMENT ON COLUMN t_ssh_events.username IS 'Utilisateur utilisé pour la connexion'",
    "COMMENT ON COLUMN t_ssh_events.invalid_user IS 'TRUE si le log contient \"invalid user\" (user inexistant)'",
    "COMMENT ON COLUMN t_ssh_events.ip_address IS 'Adresse IP source'",
    "COMMENT ON COLUMN t_ssh_events.port IS 'Port source'",
    "COMMENT ON COLUMN t_ssh_events.country IS 'Code pays ipinfo (ex : CN, US) ; NULL si non géolocalisé'",
]
CREATE_VIEWS = [
    """CREATE OR REPLACE VIEW v_failed_by_country AS
       SELECT COALESCE(NULLIF(country, ''), 'Inconnu') AS pays, COUNT(*) AS total
       FROM t_ssh_events WHERE status = 'FAILED'
       GROUP BY 1 ORDER BY total DESC""",
    """CREATE OR REPLACE VIEW v_success_by_user AS
       SELECT username, COUNT(*) AS total
       FROM t_ssh_events WHERE status = 'ACCEPTED'
       GROUP BY username ORDER BY total DESC""",
    """CREATE OR REPLACE VIEW v_failed_invalid_users AS
       SELECT username, COUNT(*) AS total
       FROM t_ssh_events WHERE status = 'FAILED' AND invalid_user
       GROUP BY username ORDER BY total DESC""",
    """CREATE OR REPLACE VIEW v_summary AS
       SELECT COUNT(*) AS total, COUNT(DISTINCT ip_address) AS ip_uniques,
              COUNT(*) FILTER (WHERE status = 'FAILED') AS echecs,
              ROUND(COUNT(*) FILTER (WHERE status = 'FAILED') * 100.0 / NULLIF(COUNT(*), 0), 2) AS taux_echec
       FROM t_ssh_events""",
]


def ensure_schema_ownership(connection)->None:
    """Corrige le propriétaire du schéma public si l’objet a été créé par un autre utilisateur."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_get_userbyid(n.nspowner) FROM pg_namespace n WHERE n.nspname = 'public'")
            owner = cursor.fetchone()
            if owner and owner[0] != config.PG_USER:
                cursor.execute(sql.SQL('ALTER SCHEMA {} OWNER TO {}').format(
                    sql.Identifier('public'),
                    sql.Identifier(config.PG_USER),
                ))
                logger.warning(f'Schéma public réattribué à {config.PG_USER}')
            cursor.execute(sql.SQL('GRANT ALL ON SCHEMA {} TO {}').format(
                sql.Identifier('public'),
                sql.Identifier(config.PG_USER),
            ))
    except psycopg2.Error as e:
        logger.warning(f'Impossible de corriger le propriétaire du schéma public : {e}')


def ensure_object_ownership(connection)->None:
    """Force le propriétaire de la table et des vues sur le rôle courant."""
    objects = {
        't_ssh_events': 'TABLE',
        'v_failed_by_country': 'VIEW',
        'v_success_by_user': 'VIEW',
        'v_failed_invalid_users': 'VIEW',
        'v_summary': 'VIEW',
    }
    try:
        with connection.cursor() as cursor:
            for obj, kind in objects.items():
                cursor.execute("SELECT to_regclass(%s)", (f'public.{obj}',))
                if cursor.fetchone()[0] is None:
                    continue
                if kind == 'TABLE':
                    cursor.execute(sql.SQL('ALTER TABLE {} OWNER TO {}').format(
                        sql.Identifier('public', obj),
                        sql.Identifier(config.PG_USER),
                    ))
                else:
                    cursor.execute(sql.SQL('ALTER VIEW {} OWNER TO {}').format(
                        sql.Identifier('public', obj),
                        sql.Identifier(config.PG_USER),
                    ))
    except psycopg2.Error as e:
        logger.warning(f'Impossible de corriger les propriétaires des objets PostgreSQL : {e}')


def create_database()->bool:
    connection = connect('postgres')
    if connection is None:
        return False
    connection.autocommit = True
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1 FROM pg_database WHERE datname = %s', (config.PG_DBNAME,))
            if cursor.fetchone() is None:
                cursor.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(config.PG_DBNAME)))
                logger.info(f'Base {config.PG_DBNAME} créée')
            else:
                logger.info(f'Base {config.PG_DBNAME} déjà présente')
    except psycopg2.Error as e:
        logger.error(f'Création de la base {config.PG_DBNAME} échouée : {e}')
        return False
    finally:
        connection.close()
    return create_tables()


def create_tables()->bool:
    connection = Database.getConnection()
    if connection is None:
        return False
    try:
        ensure_schema_ownership(connection)
        with connection.cursor() as cursor:
            cursor.execute(CREATE_TABLE)
            for query in CREATE_INDEXES:
                cursor.execute(query)
            ensure_object_ownership(connection)
            for query in COMMENTS + CREATE_VIEWS:
                try:
                    cursor.execute(query)
                except psycopg2.Error as e:
                    logger.warning(f'Commande SQL ignorée car l’objet existe avec un propriétaire différent : {e}')
        connection.commit()
        logger.info('Table t_ssh_events + vues prêtes')
        return True
    except psycopg2.Error as e:
        rollback(connection)
        logger.error(f'Création de la table t_ssh_events échouée : {e}')
        return False


if __name__ == '__main__':
    print('Création db + table :', create_database())
    Database.close()
