"""Testes automatizados do Dispute AI (executar com: pytest)."""

import json
from pathlib import Path

import pymupdf
import pytest

from dispute_ai import banco
from dispute_ai.analisador import analisar_caso, extrair_json, normalizar_analise
from dispute_ai.catalogo import avaliar_checklist
from dispute_ai.extracao import FormatoNaoSuportado, carregar_documento
from dispute_ai.llm import ErroLLM
from dispute_ai.relatorio import gerar_pdf

EXEMPLOS = Path(__file__).resolve().parent.parent / "exemplos"


@pytest.fixture(scope="module")
def docs_exemplo():
    if not any(EXEMPLOS.glob("*.pdf")):
        from scripts.gerar_exemplos import main
        main()
    return [carregar_documento(p.name, p.read_bytes()) for p in sorted(EXEMPLOS.iterdir())
            if p.suffix in {".pdf", ".txt", ".eml", ".png"}]


def test_extracao_formatos(docs_exemplo):
    metodos = {d.nome.rsplit(".", 1)[1]: d for d in docs_exemplo}
    assert "R$ 850,00" in metodos["pdf"].texto
    assert "Assunto:" in metodos["eml"].texto
    assert metodos["png"].imagens and not metodos["png"].texto


def test_formato_invalido():
    with pytest.raises(FormatoNaoSuportado):
        carregar_documento("planilha.xlsx", b"123")


def test_pdf_digitalizado_vira_imagem():
    doc = pymupdf.open()
    doc.new_page()
    resultado = carregar_documento("scan.pdf", doc.tobytes())
    assert resultado.imagens and "digitalizado" in resultado.metodo


def test_modo_demo_caso_850(docs_exemplo):
    a = analisar_caso(docs_exemplo, "demo", "regras-v1")
    assert a["transacao"]["valor"] == 850.0
    assert a["transacao"]["cartao_final"] == "4821"
    assert a["motivo"]["categoria"] == "nao_reconhecida"
    assert a["status"] == "revisao"
    ausentes = [d["documento"] for d in a["documentos_ausentes"] if d["obrigatorio"]]
    assert ausentes == ["Comprovante de entrega"]
    assert "análise humana" in a["recomendacao"]


def test_checklist_completo():
    r = avaliar_checklist("nao_recebido", {"registro_transacao", "nota_fiscal", "comprovante_entrega"})
    assert r["cobertura"] == 100 and not r["ausentes_obrigatorios"]


def test_normalizacao_impede_suficiente_com_lacunas(docs_exemplo):
    bruta = {"status": "suficiente", "nivel_risco": "baixo", "motivo": {"categoria": "xpto"},
             "transacao": {"valor": "R$ 1.234,56"},
             "documentos": [{"arquivo": docs_exemplo[0].nome, "tipo": "tipo_invalido"}]}
    a = normalizar_analise(bruta, docs_exemplo)
    assert a["status"] == "revisao"
    assert a["motivo"]["categoria"] == "outro"
    assert a["transacao"]["valor"] == 1234.56
    assert a["documentos"][0]["tipo"] == "outro"
    assert len(a["documentos"]) == len(docs_exemplo)


def test_extrair_json_com_cercas():
    assert extrair_json('```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(ErroLLM):
        extrair_json("sem json")


def test_fallback_quando_llm_falha(docs_exemplo):
    a = analisar_caso(docs_exemplo, "anthropic", "claude-sonnet-5-5", chave_api="", fallback_demo=True)
    assert a["meta"]["fallback"] and a["meta"]["modo"] == "demo"
    with pytest.raises(ErroLLM):
        analisar_caso(docs_exemplo, "openai", "gpt-4.1", chave_api="", fallback_demo=False)


def test_llm_simulado(docs_exemplo, monkeypatch):
    resposta = {"resumo": "Teste.", "transacao": {"valor": 850},
                "motivo": {"categoria": "nao_reconhecida", "descricao": "Compra não reconhecida."},
                "documentos": [{"arquivo": d.nome, "tipo": "nota_fiscal"} for d in docs_exemplo],
                "status": "revisao", "nivel_risco": "medio", "recomendacao": "Encaminhar para análise humana."}
    monkeypatch.setattr("dispute_ai.analisador.gerar_resposta", lambda *a, **k: json.dumps(resposta))
    a = analisar_caso(docs_exemplo, "gemini", "gemini-2.5-flash", chave_api="x")
    assert a["meta"]["modo"] == "llm" and a["resumo"] == "Teste."
    assert any("registro da transação" in p.lower() for p in a["pontos_atencao"])


def test_banco_e_relatorio(docs_exemplo, tmp_path):
    db = tmp_path / "teste.db"
    banco.inicializar(db)
    a = analisar_caso(docs_exemplo, "demo", "regras-v1")
    caso_id = banco.salvar_caso(a, docs_exemplo, db)
    salvo = banco.obter_caso(caso_id, db)
    assert salvo["numero"] == "#001"
    banco.atualizar_decisao(caso_id, "aguardando_docs", "Pedir rastreio.", db)
    assert banco.obter_caso(caso_id, db)["decisao_analista"] == "aguardando_docs"
    assert banco.obter_documento(caso_id, docs_exemplo[0].nome, db)["conteudo"] == docs_exemplo[0].dados
    pdf = pymupdf.open("pdf", gerar_pdf(salvo))
    texto = "".join(p.get_text() for p in pdf)
    assert "CASO #001" in texto and "Comprovante de entrega" in texto
    banco.excluir_caso(caso_id, db)
    assert banco.listar_casos(db) == []
