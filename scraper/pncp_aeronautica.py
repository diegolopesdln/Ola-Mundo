"""
Robô de busca de licitações do Comando da Aeronáutica no PNCP.
Consulta diariamente as contratações publicadas no dia atual.
"""

import json
import html
import os
import sys
from datetime import date, datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

FUSO_BRASILIA = timezone(timedelta(hours=-3))
PNCP_API_BASE = "https://pncp.gov.br/api/consulta/v1"
CNPJ_COMANDO_AERONAUTICA = "00394429000100"
TAMANHO_PAGINA = 50

# Códigos de modalidade de contratação no PNCP
MODALIDADES = {
    1: "Leilão - Eletrônico",
    2: "Diálogo Competitivo",
    3: "Concurso",
    4: "Concorrência - Eletrônica",
    5: "Concorrência - Presencial",
    6: "Pregão - Eletrônico",
    7: "Pregão - Presencial",
    8: "Dispensa de Licitação",
    9: "Inexigibilidade",
    10: "Manifestação de Interesse",
    11: "Pré-qualificação",
    12: "Credenciamento",
    13: "Leilão - Presencial",
}


def buscar_por_modalidade(data_consulta: date, codigo_modalidade: int) -> list[dict]:
    """Busca contratações de uma modalidade específica."""
    data_formatada = data_consulta.strftime("%Y%m%d")
    resultados = []
    pagina = 1

    while True:
        url = (
            f"{PNCP_API_BASE}/contratacoes/publicacao"
            f"?dataInicial={data_formatada}"
            f"&dataFinal={data_formatada}"
            f"&codigoModalidadeContratacao={codigo_modalidade}"
            f"&cnpj={CNPJ_COMANDO_AERONAUTICA}"
            f"&tamanhoPagina={TAMANHO_PAGINA}"
            f"&pagina={pagina}"
        )

        try:
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=30) as resp:
                corpo = resp.read().decode("utf-8").strip()
                if not corpo:
                    break
                dados = json.loads(corpo)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
            break

        registros = dados.get("data", dados) if isinstance(dados, dict) else dados

        if not registros:
            break

        if isinstance(registros, list):
            resultados.extend(registros)
            if len(registros) < TAMANHO_PAGINA:
                break
        else:
            resultados.append(registros)
            break

        pagina += 1

    return resultados


def buscar_contratacoes(data_consulta: date) -> list[dict]:
    """Busca todas as contratações do Comando da Aeronáutica publicadas na data informada."""
    todas_contratacoes = []

    for codigo, nome in MODALIDADES.items():
        resultados = buscar_por_modalidade(data_consulta, codigo)
        if resultados:
            print(f"  {nome}: {len(resultados)} resultado(s)")
            todas_contratacoes.extend(resultados)

    return todas_contratacoes


def formatar_valor_brl(valor) -> str:
    """Formata valor numérico para padrão BRL (R$ 1.234,56)."""
    try:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "R$ 0,00"


def extrair_uasg(c: dict) -> tuple[str, str]:
    """Extrai código e nome da UASG da contratação."""
    unidade = c.get("unidadeOrgao", {})
    codigo = unidade.get("codigoUnidade", "N/A")
    nome = unidade.get("nomeUnidade", "N/A")
    return str(codigo), nome


def formatar_contratacao(c: dict) -> str:
    """Formata uma contratação para exibição no terminal."""
    orgao = c.get("orgaoEntidade", {})
    uasg_codigo, uasg_nome = extrair_uasg(c)
    linhas = [
        f"  Número: {c.get('numeroControlePNCP', 'N/A')}",
        f"  Órgão: {orgao.get('razaoSocial', 'N/A')}",
        f"  UASG: {uasg_codigo} - {uasg_nome}",
        f"  Objeto: {c.get('objetoCompra', 'N/A')}",
        f"  Modalidade: {c.get('modalidadeNome', 'N/A')}",
        f"  Valor Estimado: {formatar_valor_brl(c.get('valorTotalEstimado', 0))}",
        f"  Situação: {c.get('situacaoCompraNome', 'N/A')}",
        f"  Data Publicação: {c.get('dataPublicacaoPncp', 'N/A')}",
        f"  Link: https://pncp.gov.br/app/editais/{CNPJ_COMANDO_AERONAUTICA}/{c.get('anoCompra', '')}/{c.get('sequencialCompra', '')}",
    ]
    return "\n".join(linhas)


def gerar_html(contratacoes: list[dict], data_consulta: date) -> str:
    """Gera relatório HTML estilizado com as contratações."""
    data_fmt = data_consulta.strftime("%d/%m/%Y")
    total = len(contratacoes)

    linhas_tabela = []
    for i, c in enumerate(contratacoes, 1):
        orgao = c.get("orgaoEntidade", {})
        uasg_codigo, uasg_nome = extrair_uasg(c)
        link = (
            f"https://pncp.gov.br/app/editais/{CNPJ_COMANDO_AERONAUTICA}"
            f"/{c.get('anoCompra', '')}/{c.get('sequencialCompra', '')}"
        )
        linhas_tabela.append(f"""        <tr>
          <td>{i}</td>
          <td>{html.escape(str(c.get('numeroControlePNCP', 'N/A')))}</td>
          <td><span class="uasg-code">{html.escape(uasg_codigo)}</span><br>{html.escape(uasg_nome)}</td>
          <td>{html.escape(str(c.get('objetoCompra', 'N/A')))}</td>
          <td>{html.escape(str(c.get('modalidadeNome', 'N/A')))}</td>
          <td class="valor">{formatar_valor_brl(c.get('valorTotalEstimado', 0))}</td>
          <td><span class="badge badge-{html.escape(str(c.get('situacaoCompraNome', 'N/A')).lower().replace(' ', '-'))}">{html.escape(str(c.get('situacaoCompraNome', 'N/A')))}</span></td>
          <td>{html.escape(str(c.get('dataPublicacaoPncp', 'N/A')[:10]))}</td>
          <td><a href="{link}" target="_blank">Abrir</a></td>
        </tr>""")

    corpo_tabela = "\n".join(linhas_tabela)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Licitações Comando da Aeronáutica - {data_fmt}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background: #f0f2f5;
      color: #1a1a2e;
    }}
    .header {{
      background: linear-gradient(135deg, #001f3f, #003366);
      color: #ffffff;
      padding: 28px 40px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}
    .header-left {{
      display: flex;
      align-items: center;
      gap: 20px;
    }}
    .header-logo {{
      width: 72px;
      height: 72px;
      flex-shrink: 0;
      filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
    }}
    .header h1 {{
      font-size: 22px;
      font-weight: 600;
      letter-spacing: 0.5px;
    }}
    .header .subtitle {{
      font-size: 13px;
      opacity: 0.85;
      margin-top: 4px;
    }}
    .header .stats {{
      text-align: right;
    }}
    .header .stats .count {{
      font-size: 36px;
      font-weight: 700;
    }}
    .header .stats .label {{
      font-size: 12px;
      opacity: 0.8;
      text-transform: uppercase;
      letter-spacing: 1px;
    }}
    .container {{
      max-width: 1280px;
      margin: 24px auto;
      padding: 0 20px;
    }}
    .table-wrapper {{
      background: #ffffff;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0, 31, 63, 0.10);
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    thead {{
      background: #001f3f;
      color: #ffffff;
    }}
    thead th {{
      padding: 14px 12px;
      text-align: left;
      font-weight: 600;
      text-transform: uppercase;
      font-size: 11px;
      letter-spacing: 0.8px;
      white-space: nowrap;
    }}
    tbody tr {{
      border-bottom: 1px solid #e8ecf1;
      transition: background 0.15s;
    }}
    tbody tr:hover {{
      background: #eef2f7;
    }}
    tbody td {{
      padding: 12px;
      vertical-align: top;
    }}
    .uasg-code {{
      display: inline-block;
      background: #001f3f;
      color: #fff;
      font-size: 11px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 4px;
      margin-bottom: 2px;
    }}
    .valor {{
      font-weight: 600;
      white-space: nowrap;
      color: #001f3f;
    }}
    .badge {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 600;
      white-space: nowrap;
    }}
    .badge-divulgada {{ background: #d4edda; color: #155724; }}
    .badge-publicada {{ background: #d4edda; color: #155724; }}
    .badge-aberta {{ background: #cce5ff; color: #004085; }}
    .badge-encerrada {{ background: #f8d7da; color: #721c24; }}
    .badge-suspensa {{ background: #fff3cd; color: #856404; }}
    a {{
      color: #003366;
      font-weight: 600;
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    .footer {{
      text-align: center;
      padding: 20px;
      font-size: 11px;
      color: #6c757d;
    }}
  </style>
</head>
<body>
  <div class="header">
    <div class="header-left">
      <img class="header-logo" src="https://upload.wikimedia.org/wikipedia/commons/thumb/4/4f/Coat_of_arms_of_the_Brazilian_Air_Force.svg/200px-Coat_of_arms_of_the_Brazilian_Air_Force.svg.png" alt="Gládio Alado - Força Aérea Brasileira">
      <div>
        <h1>Licitações do Comando da Aeronáutica</h1>
        <div class="subtitle">Portal Nacional de Contratações Públicas (PNCP) &mdash; {data_fmt}</div>
      </div>
    </div>
    <div class="stats">
      <div class="count">{total}</div>
      <div class="label">licitações encontradas</div>
    </div>
  </div>
  <div class="container">
    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Nº Controle PNCP</th>
            <th>UASG</th>
            <th>Objeto</th>
            <th>Modalidade</th>
            <th>Valor Estimado</th>
            <th>Situação</th>
            <th>Publicação</th>
            <th>Link</th>
          </tr>
        </thead>
        <tbody>
{corpo_tabela}
        </tbody>
      </table>
    </div>
  </div>
  <div class="footer">
    Gerado automaticamente em {datetime.now(FUSO_BRASILIA).strftime('%d/%m/%Y %H:%M')} (horário de Brasília) &mdash; Fonte: PNCP
  </div>
</body>
</html>"""


def enviar_telegram(arquivo_html: str, total: int, data_consulta: date):
    """Envia o relatório HTML via Telegram Bot API."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        print("TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não configurados. Envio ignorado.")
        return

    import http.client
    import mimetypes

    data_fmt = data_consulta.strftime("%d/%m/%Y")
    caption = (
        f"Licitações Comando da Aeronáutica - {data_fmt}\n"
        f"Total: {total} licitação(ões) encontrada(s)"
    )

    # Monta requisição multipart para enviar o arquivo
    boundary = "----PNCPBoundary"
    nome_arquivo = os.path.basename(arquivo_html)

    with open(arquivo_html, "rb") as f:
        conteudo_arquivo = f.read()

    corpo = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
        f"{chat_id}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="caption"\r\n\r\n'
        f"{caption}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="document"; filename="{nome_arquivo}"\r\n'
        f"Content-Type: text/html\r\n\r\n"
    ).encode("utf-8") + conteudo_arquivo + f"\r\n--{boundary}--\r\n".encode("utf-8")

    conn = http.client.HTTPSConnection("api.telegram.org", timeout=30)
    try:
        conn.request(
            "POST",
            f"/bot{token}/sendDocument",
            body=corpo,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Content-Length": str(len(corpo)),
            },
        )
        resp = conn.getresponse()
        resultado = json.loads(resp.read().decode("utf-8"))
        if resultado.get("ok"):
            print("Relatório enviado com sucesso via Telegram!")
        else:
            print(f"Erro ao enviar via Telegram: {resultado.get('description', 'Erro desconhecido')}")
    except Exception as e:
        print(f"Falha ao conectar com Telegram: {e}")
    finally:
        conn.close()


def main():
    hoje = datetime.now(FUSO_BRASILIA).date()
    print("=== Licitações do Comando da Aeronáutica - PNCP ===")
    print(f"Data de consulta: {hoje.strftime('%d/%m/%Y')}\n")

    contratacoes = buscar_contratacoes(hoje)

    if not contratacoes:
        print("Nenhuma licitação publicada hoje.")
        return

    print(f"\nTotal de licitações encontradas: {len(contratacoes)}\n")
    print("-" * 60)

    for i, c in enumerate(contratacoes, 1):
        print(f"\n[{i}]")
        print(formatar_contratacao(c))
        print("-" * 60)

    # Salva resultado em JSON
    arquivo_json = f"resultado_{hoje.strftime('%Y-%m-%d')}.json"
    with open(arquivo_json, "w", encoding="utf-8") as f:
        json.dump(contratacoes, f, ensure_ascii=False, indent=2)
    print(f"\nResultados salvos em: {arquivo_json}")

    # Gera relatório HTML
    arquivo_html = f"resultado_{hoje.strftime('%Y-%m-%d')}.html"
    with open(arquivo_html, "w", encoding="utf-8") as f:
        f.write(gerar_html(contratacoes, hoje))
    print(f"Relatório HTML salvo em: {arquivo_html}")

    # Envia para o Telegram
    enviar_telegram(arquivo_html, len(contratacoes), hoje)


if __name__ == "__main__":
    main()
