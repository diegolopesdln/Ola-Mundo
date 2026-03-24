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
                dados = json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            if e.code == 404:
                break
            if e.code == 400:
                break
            print(f"  Erro HTTP {e.code} na modalidade {codigo_modalidade}, página {pagina}")
            break
        except URLError as e:
            print(f"  Erro de conexão na modalidade {codigo_modalidade}: {e.reason}")
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
