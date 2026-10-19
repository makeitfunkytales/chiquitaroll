import sqlite3
from pathlib import Path

CAMINHO_BANCO = Path(__file__).resolve().parent.parent / "colecao.db"

def conectar():
    conexao = sqlite3.connect(CAMINHO_BANCO, timeout=10)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao

def inicializar_banco():
    with conectar() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id TEXT UNIQUE,
            name TEXT NOT NULL COLLATE NOCASE,
            origin TEXT NOT NULL,
            image_url TEXT,
            rarity TEXT NOT NULL DEFAULT 'comum'
        );

        CREATE TABLE IF NOT EXISTS user_characters (
            character_id INTEGER PRIMARY KEY,
            owner_id TEXT NOT NULL,
            favorite INTEGER NOT NULL DEFAULT 0,
            married INTEGER NOT NULL DEFAULT 0,
            acquired_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(character_id) REFERENCES characters(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_user_characters_owner
        ON user_characters(owner_id);

        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user TEXT NOT NULL,
            to_user TEXT NOT NULL,
            from_character INTEGER NOT NULL,
            to_character INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(from_character) REFERENCES characters(id),
            FOREIGN KEY(to_character) REFERENCES characters(id)
        );
        """)
