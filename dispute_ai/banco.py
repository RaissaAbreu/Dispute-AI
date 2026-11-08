"""Persistência em SQLite: casos analisados e seus documentos."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from .config import CAMINHO_DB
from .extracao import DocumentoCarregado

ESQUEMA = """
CREATE TABLE IF NOT EXISTS casos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    criado_em       TEXT NOT NULL,
    atualizado_em   TEXT NOT NULL,
    provedor        TEXT NOT NULL,
    modelo          TEXT NOT NULL,
    status          TEXT NOT NULL,
    nivel_risco     TEXT,
    valor           REAL,
    motivo          TEXT,
    resumo          TEXT,
    analise_json    TEXT NOT NULL,
    decisao_analista TEXT DEFAULT 'pendente',
    notas_analista  TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS documentos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    caso_id         INTEGER NOT NULL REFERENCES casos(id) ON DELETE CASCADE,
    nome_arquivo    TEXT NOT NULL,
    mime            TEXT NOT NULL,
    tamanho_bytes   INTEGER NOT NULL,
    sha256          TEXT NOT NULL,
    tipo_documento  TEXT,
    texto_extraido  TEXT,
    conteudo        BLOB NOT NULL,
    criado_em       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_documentos_caso ON documentos(caso_id);
"""

DECISOES = {
    "pendente": "Pendente",
    "defender": "Defender (contestar o chargeback)",
    "aceitar": "Aceitar o chargeback",
    "aguardando_docs": "Aguardando documentos",
}


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


@contextmanager
def conexao(caminho: Path | str = CAMINHO_DB):
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(caminho)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def inicializar(caminho: Path | str = CAMINHO_DB) -> None:
    with conexao(caminho) as con:
        con.executescript(ESQUEMA)


def numero_caso(caso_id: int) -> str:
    return f"#{caso_id:03d}"


def salvar_caso(analise: dict, docs: list[DocumentoCarregado], caminho: Path | str = CAMINHO_DB) -> int:
    agora = _agora()
    meta = analise.get("meta", {})
    tipos = {d["arquivo"]: d["tipo"] for d in analise.get("documentos", [])}
    with conexao(caminho) as con:
        cur = con.execute(
            """INSERT INTO casos (criado_em, atualizado_em, provedor, modelo, status, nivel_risco,
                                  valor, motivo, resumo, analise_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (agora, agora, meta.get("provedor", ""), meta.get("modelo", ""), analise["status"],
             analise.get("nivel_risco"), analise.get("transacao", {}).get("valor"),
             analise.get("motivo", {}).get("categoria"), analise.get("resumo", ""), "{}"),
        )
        caso_id = cur.lastrowid
        analise["numero"] = numero_caso(caso_id)
        analise["id"] = caso_id
        con.execute("UPDATE casos SET analise_json = ? WHERE id = ?",
                    (json.dumps(analise, ensure_ascii=False), caso_id))
        con.executemany(
            """INSERT INTO documentos (caso_id, nome_arquivo, mime, tamanho_bytes, sha256,
                                       tipo_documento, texto_extraido, conteudo, criado_em)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [(caso_id, d.nome, d.mime, len(d.dados), d.hash, tipos.get(d.nome), d.texto, d.dados, agora)
             for d in docs],
        )
    return caso_id


def listar_casos(caminho: Path | str = CAMINHO_DB) -> list[dict]:
    with conexao(caminho) as con:
        linhas = con.execute(
            """SELECT c.id, c.criado_em, c.provedor, c.modelo, c.status, c.nivel_risco, c.valor,
                      c.motivo, c.resumo, c.decisao_analista,
                      (SELECT COUNT(*) FROM documentos d WHERE d.caso_id = c.id) AS qtd_documentos
               FROM casos c ORDER BY c.id DESC"""
        ).fetchall()
    return [dict(l) for l in linhas]


def obter_caso(caso_id: int, caminho: Path | str = CAMINHO_DB) -> dict | None:
    with conexao(caminho) as con:
        linha = con.execute("SELECT * FROM casos WHERE id = ?", (caso_id,)).fetchone()
    if not linha:
        return None
    analise = json.loads(linha["analise_json"])
    analise["id"] = linha["id"]
    analise["numero"] = numero_caso(linha["id"])
    analise["decisao_analista"] = linha["decisao_analista"]
    analise["notas_analista"] = linha["notas_analista"]
    return analise


def obter_documento(caso_id: int, nome_arquivo: str, caminho: Path | str = CAMINHO_DB) -> dict | None:
    with conexao(caminho) as con:
        linha = con.execute(
            "SELECT nome_arquivo, mime, conteudo, texto_extraido FROM documentos "
            "WHERE caso_id = ? AND nome_arquivo = ?", (caso_id, nome_arquivo)
        ).fetchone()
    return dict(linha) if linha else None


def atualizar_decisao(caso_id: int, decisao: str, notas: str, caminho: Path | str = CAMINHO_DB) -> None:
    if decisao not in DECISOES:
        raise ValueError(f"Decisão inválida: {decisao}")
    with conexao(caminho) as con:
        con.execute("UPDATE casos SET decisao_analista = ?, notas_analista = ?, atualizado_em = ? WHERE id = ?",
                    (decisao, notas, _agora(), caso_id))


def excluir_caso(caso_id: int, caminho: Path | str = CAMINHO_DB) -> None:
    with conexao(caminho) as con:
        con.execute("DELETE FROM casos WHERE id = ?", (caso_id,))


def estatisticas(caminho: Path | str = CAMINHO_DB) -> dict:
    with conexao(caminho) as con:
        total, valor = con.execute("SELECT COUNT(*), COALESCE(SUM(valor), 0) FROM casos").fetchone()
        por_status = dict(con.execute("SELECT status, COUNT(*) FROM casos GROUP BY status").fetchall())
        pendentes = con.execute(
            "SELECT COUNT(*) FROM casos WHERE decisao_analista IN ('pendente', 'aguardando_docs')"
        ).fetchone()[0]
        por_decisao = dict(con.execute(
            "SELECT decisao_analista, COUNT(*) FROM casos GROUP BY decisao_analista").fetchall())
    return {"total": total, "valor_total": valor, "por_status": por_status, "pendentes": pendentes,
            "por_decisao": por_decisao}
