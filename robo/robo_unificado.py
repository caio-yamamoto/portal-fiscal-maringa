"""
Robô unificado: numa única sessão do Chrome, emite no sistema contábil (Elotech) os relatórios do robô do
Power BI (automacao_relatorios_bi.py) e os do robô do portal (robo_portal.py), e no fim atualiza o portal
(atualizar_portal.py: gera os dados e envia ao GitHub, sem a conferência com o balancete simplificado, que o
usuário faz depois comparando os PDFs emitidos com o Power BI e o portal).

Relatórios emitidos, para o mês vigente e o anterior:
  - Receita Realizada por Fonte (XLSX): emitida UMA vez e salva nas duas pastas
      -> Power BI: DIRETORIO_DESTINO_XLSX/receita_realizada_fonte - <MÊS>_<ano>.xlsx
      -> portal:   relatorios_locais/<ano>/receita_realizada_fonte_-_<MÊS>_<ano>.xlsx
  - Receita e Despesa por Fonte de Recurso (PDF), de 01/01 ao fim do mês vigente (só Power BI)
      -> DIRETORIO_DESTINO_PDF/receita_despesa_por_fonte_recurso - <MÊS>_<ano>.pdf
  - Balancetes da Despesa do Power BI (como em gerar_relatorios_balancete_despesa)
      -> XLSX simplificado de cada mês, XLSX e PDF analíticos de 01/01 ao fim do mês vigente
  - Balancetes da Despesa do portal (como em robo_portal.emitir_balancetes, com "Emitir Desdobramento")
      -> só o analítico acumulado de cada mês, em relatorios_locais/desp<ano>/ (sem o simplificado)
  - Demonstrativo de Crédito Adicional do portal (excesso de arrecadação), de 01/01 ao fim do mês vigente
      -> relatorios_locais/creditos/credito_adicional_excesso_<ano>-<mm>.xlsx (uma falha só gera aviso)

Em janeiro, o mês anterior é dezembro do exercício anterior, que o sistema só emite logado naquele exercício:
o robô emite primeiro os relatórios do exercício vigente e depois troca o sistema para 12/<ano anterior>
(pela URL, como bi.garantir_periodo_correto) e emite os de dezembro. As pastas de cada ano são criadas
sozinhas.

Uma falha numa etapa não impede as seguintes; no fim aparece o resumo. O portal só é atualizado se todos os
relatórios dele foram salvos.

Uso:  python robo_unificado.py             (emite tudo, atualiza e envia o portal)
      python robo_unificado.py --sem-envio (emite tudo e gera os dados do portal, sem enviar)
      python robo_unificado.py --so-bi     (só os relatórios do Power BI)
      python robo_unificado.py --so-portal (só os relatórios do portal, como o robo_portal.py)
"""
import calendar
import re
import shutil
import sys
import threading
import time
import traceback
from datetime import date
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import automacao_relatorios_bi as bi
import atualizar_portal
import robo_portal as portal

MESES = bi.MESES_PT                                      # JANEIRO, FEVEREIRO, MARÇO...

falhas = {"bi": [], "portal": [], "creditos": []}   # "creditos": só aviso, não impede o portal


def salvar(baixado: Path, destinos):
    """Copia o arquivo baixado para cada (grupo, pasta, nome); um destino com erro não impede os demais."""
    for grupo, pasta, nome in destinos:
        destino = pasta / nome

        def copiar():
            destino.unlink(missing_ok=True)
            shutil.copy2(baixado, destino)

        try:
            pasta.mkdir(parents=True, exist_ok=True)
            portal.com_novas_tentativas(copiar)
            print(f"Arquivo salvo como: {destino}")
        except Exception as erro:
            print(f"ERRO ao salvar {destino}: {erro}")
            falhas[grupo].append(f"salvar {destino}: {erro}")
    portal.com_novas_tentativas(lambda: baixado.unlink(missing_ok=True))


def emitir_e_salvar(driver, nome_relatorio, formato, destinos):
    """Gera o relatório no formato indicado, baixa pelas Notificações e salva em todos os destinos."""
    bi.gerar_relatorio(driver, formato=formato)
    salvar(portal.baixar_arquivo(driver, nome_relatorio, f".{formato}"), destinos)


def abrir_relatorio(driver, nome_relatorio):
    bi.abrir_menu_por_busca(driver, "Relatórios")
    bi.filtrar_relatorio(driver, nome_relatorio)
    bi.selecionar_relatorio_filtrado(driver)


def etapa(titulo, grupos, funcao, driver) -> bool:
    """Executa uma etapa; se der erro, registra nos grupos afetados e segue para a próxima."""
    print(f"\n######## {titulo} ########")
    try:
        funcao(driver)
        return True
    except Exception as erro:
        traceback.print_exc()
        for grupo in grupos:
            falhas[grupo].append(f"{titulo}: {type(erro).__name__}: {erro}")
        return False


def mudar_periodo_sistema(driver, url_home, mes, ano):
    """Leva o sistema para mes/ano trocando o trecho e{entidade}m{mes}a{ano} da URL da tela inicial do módulo."""
    entidade, _, _ = bi.extrair_periodo_da_url(url_home)
    nova_url = re.sub(r"e\d+m\d+a\d+", f"e{entidade}m{mes}a{ano}", url_home, count=1)
    print(f"Trocando o sistema para {mes:02d}/{ano}: {nova_url}")
    driver.get(nova_url)
    WebDriverWait(driver, bi.WAIT_TIMEOUT).until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'Início')]")))
    periodo = bi.extrair_periodo_da_url(driver.current_url)
    if periodo is None or periodo[1:] != (mes, ano):
        raise RuntimeError(f"O sistema não ficou em {mes:02d}/{ano} (URL atual: {driver.current_url}).")
    time.sleep(2)


def receita(driver, periodos, com_bi, com_portal):
    nome = "Receita Realizada por Fonte"
    abrir_relatorio(driver, nome)
    for inicio, fim in periodos:
        mes = MESES[inicio.month - 1]
        destinos = []
        if com_bi:
            destinos.append(("bi", bi.DIRETORIO_DESTINO_XLSX, f"receita_realizada_fonte - {mes}_{inicio.year}.xlsx"))
        if com_portal:
            destinos.append(("portal", portal.RELATORIOS / str(inicio.year),
                             f"receita_realizada_fonte_-_{mes}_{inicio.year}.xlsx"))
        print(f"\n=== Receita realizada por fonte - {inicio:%m/%Y} ===")
        bi.preencher_periodo_relatorio(driver, inicio, fim)
        emitir_e_salvar(driver, nome, "xlsx", destinos)


def receita_despesa_fonte_pdf(driver):
    nome = "Receita e Despesa por Fonte de Recurso"
    abrir_relatorio(driver, nome)
    mes, ano = bi.obter_mes_ano_vigente()
    inicio, fim = date(ano, 1, 1), date(ano, mes, calendar.monthrange(ano, mes)[1])
    print(f"\n=== {nome} - {inicio:%d/%m/%Y} a {fim:%d/%m/%Y} ===")
    bi.preencher_periodo_por_id_duplicado(driver, inicio, fim)
    emitir_e_salvar(driver, nome, "pdf", [
        ("bi", bi.DIRETORIO_DESTINO_PDF, f"receita_despesa_por_fonte_recurso - {MESES[fim.month - 1]}_{fim.year}.pdf"),
    ])


def balancetes_bi(driver, periodos, com_analiticos):
    """
    Balancetes do robô do Power BI: o simplificado de cada período e, se com_analiticos, o analítico (XLSX e
    PDF) de 01/01 ao fim do mês vigente. O 'Emitir Desdobramento' fica como o sistema abre a tela.
    """
    nome = "Balancete da Despesa"
    abrir_relatorio(driver, nome)
    xlsx, pdf = bi.DIRETORIO_DESTINO_XLSX, bi.DIRETORIO_DESTINO_PDF

    for inicio, fim in periodos:
        print(f"\n=== Balancete da Despesa (Power BI): XLSX Simplificado - {inicio:%m/%Y} ===")
        bi.preencher_periodo_relatorio(driver, inicio, fim)
        bi.selecionar_tipo_relatorio(driver, "simplificado")
        emitir_e_salvar(driver, nome, "xlsx", [
            ("bi", xlsx, f"contabil_balancete_despesa - {MESES[inicio.month - 1]}_{inicio.year}.xlsx"),
        ])

    if not com_analiticos:
        return
    mes, ano = bi.obter_mes_ano_vigente()
    fim_atual = date(ano, mes, calendar.monthrange(ano, mes)[1])
    for formato, pasta in [("xlsx", xlsx), ("pdf", pdf)]:
        print(f"\n=== Balancete da Despesa (Power BI): {formato.upper()} Analítico - "
              f"01/01/{ano} a {fim_atual:%d/%m/%Y} ===")
        bi.preencher_periodo_relatorio(driver, date(ano, 1, 1), fim_atual)
        bi.selecionar_tipo_relatorio(driver, "analitico")
        emitir_e_salvar(driver, nome, formato, [("bi", pasta, f"contabil_balancete_despesa_orcado_{ano}.{formato}")])


def emitir_exercicio(driver, periodos, com_bi, com_portal, vigente):
    """Etapas de um exercício. vigente=False é o dezembro do exercício anterior (em janeiro): sem o PDF e os
    analíticos do Power BI, que são do exercício vigente."""
    grupos = [g for g, ativo in (("bi", com_bi), ("portal", com_portal)) if ativo]
    rotulo = "" if vigente else f" - {periodos[0][0]:%m/%Y}"
    etapa("Receita Realizada por Fonte" + rotulo, grupos,
          lambda d: receita(d, periodos, com_bi, com_portal), driver)
    if com_bi:
        if vigente:
            etapa("Receita e Despesa por Fonte de Recurso (PDF)", ["bi"], receita_despesa_fonte_pdf, driver)
        # antes dos do portal, para o 'Emitir Desdobramento' ficar como no robô do Power BI
        etapa("Balancetes da Despesa - Power BI" + rotulo, ["bi"],
              lambda d: balancetes_bi(d, periodos, com_analiticos=vigente), driver)
    if com_portal:
        etapa("Balancetes da Despesa - portal" + rotulo, ["portal"],
              lambda d: portal.emitir_balancetes(d, periodos, com_simplificado=False), driver)
        if vigente:
            etapa("Demonstrativo de Crédito Adicional - portal", ["creditos"], portal.emitir_creditos, driver)


def main():
    enviar = "--sem-envio" not in sys.argv
    com_bi = "--so-portal" not in sys.argv
    com_portal = "--so-bi" not in sys.argv
    grupos = [g for g, ativo in (("bi", com_bi), ("portal", com_portal)) if ativo]

    _, ano_vigente = bi.obter_mes_ano_vigente()
    periodos = bi.obter_periodos_atual_e_anterior()
    do_exercicio = [p for p in periodos if p[0].year == ano_vigente]
    do_anterior = [p for p in periodos if p[0].year != ano_vigente]   # só em janeiro: dezembro do ano anterior

    portal.DOWNLOADS.mkdir(parents=True, exist_ok=True)
    for arquivo in list(portal.DOWNLOADS.glob("*.xlsx")) + list(portal.DOWNLOADS.glob("*.pdf")):
        arquivo.unlink(missing_ok=True)   # sobras de uma execução interrompida

    # o Siconfi não depende dos relatórios do sistema: é consultado em paralelo, enquanto o Chrome trabalha
    siconfi = threading.Thread(target=atualizar_portal.atualizar_siconfi, daemon=True) if com_portal else None
    if siconfi:
        siconfi.start()

    driver = bi.criar_driver(diretorio_download=portal.DOWNLOADS)
    try:
        portal.abrir_contabilidade(driver)
        url_home = driver.current_url
        emitir_exercicio(driver, do_exercicio, com_bi, com_portal, vigente=True)

        if do_anterior:
            inicio = do_anterior[0][0]
            if etapa(f"Troca do sistema para {inicio:%m/%Y}", grupos,
                     lambda d: mudar_periodo_sistema(d, url_home, inicio.month, inicio.year), driver):
                emitir_exercicio(driver, do_anterior, com_bi, com_portal, vigente=False)
        time.sleep(3)
    finally:
        bi.fechar_driver(driver)

    print("\n######## Resumo ########")
    for grupo, titulo in (("bi", "Power BI"), ("portal", "Portal")):
        if grupo not in grupos:
            continue
        if falhas[grupo]:
            print(f"{titulo}: {len(falhas[grupo])} problema(s):")
            for falha in falhas[grupo]:
                print("  -", falha)
        else:
            print(f"{titulo}: todos os relatórios salvos.")
    for falha in falhas["creditos"]:
        print("AVISO (os créditos do portal continuam como estavam):", falha)

    ok = not falhas["bi"]
    if com_portal:
        if falhas["portal"]:
            print("\nO portal NÃO foi atualizado porque faltaram relatórios dele. Rode de novo "
                  "(python robo_unificado.py --so-portal).")
            ok = False
        else:
            print("\nRelatórios emitidos. Atualizando os dados do portal...\n")
            siconfi.join()
            ok = atualizar_portal.main(enviar=enviar, conferencia=False, siconfi=False) and ok
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
