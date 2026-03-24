"""
Robô de busca de licitações do Comando da Aeronáutica no PNCP.
Consulta diariamente as contratações publicadas no dia atual.
"""

import json
import sys
from datetime import date
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

PNCP_API_BASE = "https://pncp.gov.br/api/consulta/v1"
CNPJ_COMANDO_AERONAUTICA = "00394429000100"
TAMANHO_PAGINA = 50


def buscar_contratacoes(data_consulta: date) -> list[dict]:
    """Busca todas as contratações do Comando da Aeronáutica publicadas na data informada."""
    data_formatada = data_consulta.strftime("%Y%m%d")
    todas_contratacoes = []
    pagina = 1

    while True:
        url = (
            f"{PNCP_API_BASE}/contratacoes/publicacao"
            f"?dataInicial={data_formatada}"
            f"&dataFinal={data_formatada}"
            f"&cnpj={CNPJ_COMANDO_AERONAUTICA}"
            f"&tamanhoPagina={TAMANHO_PAGINA}"
            f"&pagina={pagina}"
        )

        try:
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=30) as resp:
                dados = json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            if e.code == 404:
                break
            print(f"Erro HTTP {e.code} ao consultar página {pagina}: {e.reason}")
            break
        except URLError as e:
            print(f"Erro de conexão ao consultar página {pagina}: {e.reason}")
            break

        registros = dados.get("data", dados) if isinstance(dados, dict) else dados

        if not registros:
            break

        if isinstance(registros, list):
            todas_contratacoes.extend(registros)
            if len(registros) < TAMANHO_PAGINA:
                break
        else:
            todas_contratacoes.append(registros)
            break

        pagina += 1

    return todas_contratacoes


def formatar_contratacao(c: dict) -> str:
    """Formata uma contratação para exibição."""
    orgao = c.get("orgaoEntidade", {})
    linhas = [
        f"  Número: {c.get('numeroControlePNCP', 'N/A')}",
        f"  Órgão: {orgao.get('razaoSocial', 'N/A')}",
        f"  Objeto: {c.get('objetoCompra', 'N/A')}",
        f"  Modalidade: {c.get('modalidadeNome', 'N/A')}",
        f"  Valor Estimado: R$ {c.get('valorTotalEstimado', 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        f"  Situação: {c.get('situacaoCompraNome', 'N/A')}",
        f"  Data Publicação: {c.get('dataPublicacaoPncp', 'N/A')}",
        f"  Link: https://pncp.gov.br/app/editais/{CNPJ_COMANDO_AERONAUTICA}/{c.get('anoCompra', '')}/{c.get('sequencialCompra', '')}",
    ]
    return "\n".join(linhas)


def main():
    hoje = date.today()
    print(f"=== Licitações do Comando da Aeronáutica - PNCP ===")
    print(f"Data de consulta: {hoje.strftime('%d/%m/%Y')}\n")

    contratacoes = buscar_contratacoes(hoje)

    if not contratacoes:
        print("Nenhuma licitação publicada hoje.")
        return

    print(f"Total de licitações encontradas: {len(contratacoes)}\n")
    print("-" * 60)

    for i, c in enumerate(contratacoes, 1):
        print(f"\n[{i}]")
        print(formatar_contratacao(c))
        print("-" * 60)

    # Salva resultado em JSON para uso posterior
    arquivo_saida = f"resultado_{hoje.strftime('%Y-%m-%d')}.json"
    with open(arquivo_saida, "w", encoding="utf-8") as f:
        json.dump(contratacoes, f, ensure_ascii=False, indent=2)
    print(f"\nResultados salvos em: {arquivo_saida}")


if __name__ == "__main__":
    main()
