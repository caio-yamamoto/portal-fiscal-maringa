"""
Robô do portal: emite no sistema contábil (Elotech) os relatórios usados pelo Portal de Gestão
Orçamentária e Fiscal, salva em relatorios_locais/ e chama atualizar_portal.py, que gera os dados,
confere com o balancete simplificado e envia ao GitHub (o site é republicado em seguida).

Reaproveita as funções do robô do Power BI (automacao_relatorios_bi.py), que deve estar nesta mesma
pasta. O login continua manual na janela do Chrome (verificação do Cloudflare); com o perfil
persistente, ele só é pedido quando a sessão expira.

Relatórios emitidos, para o mês vigente e o anterior (o anterior pega lançamentos retroativos):
  - Receita Realizada por Fonte (XLSX), do dia 1º ao fim do mês
      -> relatorios_locais/<ano>/receita_realizada_fonte_-_<MÊS>_<ano>.xlsx
  - Balancete da Despesa ANALÍTICO (XLSX), de 01/01 até o fim do mês
      -> relatorios_locais/desp<ano>/contabil_balancete_despesa_-_<mês>_<ano>_-_analitico.xlsx
  - Balancete da Despesa SIMPLIFICADO (XLSX), do dia 1º ao fim do mês (só para conferência)
      -> relatorios_locais/desp<ano>/contabil_balancete_despesa_-_<mês>_<ano>_-_simplificado.xlsx

Uso:  python robo_portal.py            (emite, gera os dados e envia ao GitHub)
      python robo_portal.py --sem-envio (emite e gera os dados, mas não envia)
"""
import sys
import time
from datetime import date
from pathlib import Path

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import automacao_relatorios_bi as bi
import atualizar_portal

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parent
RELATORIOS = REPO / "relatorios_locais"      # planilhas originais: ficam só neste computador (.gitignore)
DOWNLOADS = AQUI / "downloads_temp"           # pasta onde o Chrome baixa antes de mover

MESES_MAIUSC = bi.MESES_PT                     # JANEIRO, FEVEREIRO, MARÇO...
MESES_MINUSC = [m.lower() for m in MESES_MAIUSC]


def abrir_contabilidade(driver):
    """Entra no módulo Contabilidade e garante que o sistema está no mês vigente."""
    abas_antes = driver.window_handles
    bi.selecionar_modulo(driver, "Contabilidade")
    time.sleep(1)
    novas = [a for a in driver.window_handles if a not in abas_antes]
    if novas:
        driver.switch_to.window(novas[0])
    WebDriverWait(driver, bi.WAIT_TIMEOUT).until(EC.url_contains("/home"))
    bi.garantir_periodo_correto(driver)


def baixar_para(driver, nome_relatorio, pasta_destino: Path, nome_final: str) -> Path:
    """Usa o download do robô do BI, trocando só a pasta de destino final."""
    pasta_destino.mkdir(parents=True, exist_ok=True)
    original = bi.DIRETORIO_DESTINO_XLSX
    bi.DIRETORIO_DESTINO_XLSX = pasta_destino
    try:
        return bi.baixar_relatorio_notificacoes(driver, nome_relatorio, DOWNLOADS, nome_final)
    finally:
        bi.DIRETORIO_DESTINO_XLSX = original


def periodos():
    """[(início, fim) do mês vigente, (início, fim) do mês anterior], só do exercício vigente.
    Em janeiro, o mês anterior é de outro exercício e fica de fora (o sistema está logado no ano novo)."""
    _, ano = bi.obter_mes_ano_vigente()
    return [(i, f) for i, f in bi.obter_periodos_atual_e_anterior() if i.year == ano]


def emitir_receita(driver):
    nome = "Receita Realizada por Fonte"
    bi.abrir_menu_por_busca(driver, "Relatórios")
    bi.filtrar_relatorio(driver, nome)
    bi.selecionar_relatorio_filtrado(driver)
    for inicio, fim in periodos():
        print(f"\n=== Receita realizada por fonte - {inicio:%m/%Y} ===")
        bi.preencher_periodo_relatorio(driver, inicio, fim)
        bi.gerar_relatorio(driver, formato="xlsx")
        arq = f"receita_realizada_fonte_-_{MESES_MAIUSC[inicio.month - 1]}_{inicio.year}.xlsx"
        baixar_para(driver, nome, RELATORIOS / str(inicio.year), arq)


def emitir_balancetes(driver):
    nome = "Balancete da Despesa"
    bi.abrir_menu_por_busca(driver, "Relatórios")
    bi.filtrar_relatorio(driver, nome)
    bi.selecionar_relatorio_filtrado(driver)
    for inicio, fim in periodos():
        pasta = RELATORIOS / f"desp{inicio.year}"
        base = f"contabil_balancete_despesa_-_{MESES_MINUSC[inicio.month - 1]}_{inicio.year}"
        # analítico acumulado: 01/01 até o fim do mês (o portal calcula cada mês pela diferença)
        print(f"\n=== Balancete da despesa analítico - 01/01 a {fim:%d/%m/%Y} ===")
        bi.preencher_periodo_relatorio(driver, date(inicio.year, 1, 1), fim)
        bi.selecionar_tipo_relatorio(driver, "analitico")
        bi.gerar_relatorio(driver, formato="xlsx")
        baixar_para(driver, nome, pasta, base + "_-_analitico.xlsx")
        # simplificado do mês: usado só para conferir os totais
        print(f"\n=== Balancete da despesa simplificado - {inicio:%m/%Y} ===")
        bi.preencher_periodo_relatorio(driver, inicio, fim)
        bi.selecionar_tipo_relatorio(driver, "simplificado")
        bi.gerar_relatorio(driver, formato="xlsx")
        baixar_para(driver, nome, pasta, base + "_-_simplificado.xlsx")


def main():
    enviar = "--sem-envio" not in sys.argv
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    driver = bi.criar_driver(diretorio_download=DOWNLOADS)
    try:
        abrir_contabilidade(driver)
        emitir_receita(driver)
        emitir_balancetes(driver)
        time.sleep(3)
    finally:
        bi.fechar_driver(driver)
    print("\nRelatórios emitidos. Atualizando os dados do portal...\n")
    ok = atualizar_portal.main(enviar=enviar)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
