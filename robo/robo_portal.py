"""
Robô do portal: emite no sistema contábil (Elotech) os relatórios usados pelo Portal de Gestão
Orçamentária e Fiscal, salva em relatorios_locais/ e chama atualizar_portal.py, que gera os dados,
confere com o balancete simplificado e envia ao GitHub (o site é republicado em seguida).

Reaproveita as funções do robô do Power BI (automacao_relatorios_bi.py), que deve estar nesta mesma
pasta, sem alterações (o download pelas Notificações é feito aqui, em baixar_para). O login continua manual na janela do Chrome (verificação do Cloudflare); com o perfil
persistente, ele só é pedido quando a sessão expira.

Relatórios emitidos, para o mês vigente e o anterior (o anterior pega lançamentos retroativos):
  - Receita Realizada por Fonte (XLSX), do dia 1º ao fim do mês
      -> relatorios_locais/<ano>/receita_realizada_fonte_-_<MÊS>_<ano>.xlsx
  - Balancete da Despesa ANALÍTICO (XLSX), de 01/01 até o fim do mês
      -> relatorios_locais/desp<ano>/contabil_balancete_despesa_-_<mês>_<ano>_-_analitico.xlsx
  - Balancete da Despesa SIMPLIFICADO (XLSX), do dia 1º ao fim do mês (só para conferência)
      -> relatorios_locais/desp<ano>/contabil_balancete_despesa_-_<mês>_<ano>_-_simplificado.xlsx
E, só para o mês vigente:
  - Demonstrativo de Crédito Adicional (XLSX), tipo de recurso "Excesso de arrecadação", de 01/01 ao fim do mês
      -> relatorios_locais/creditos/credito_adicional_excesso_<ano>-<mm>.xlsx (uma falha aqui só gera aviso)

Uso:  python robo_portal.py            (emite, gera os dados e envia ao GitHub)
      python robo_portal.py --sem-envio (emite e gera os dados, mas não envia)
"""
import calendar
import shutil
import sys
import time
from datetime import date
from pathlib import Path

from selenium.common.exceptions import NoSuchWindowException, StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

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

    def aba_contabilidade(d):
        # A aba do módulo costuma ser nova, mas o Chrome pode ter restaurado abas de uma execução
        # interrompida (algumas ainda sem URL); procura em todas, começando pelas novas.
        abas = [a for a in d.window_handles if a not in abas_antes] + list(abas_antes)
        for aba in abas:
            try:
                d.switch_to.window(aba)
                if "/home" in (d.current_url or ""):
                    return True
            except Exception:
                pass
        return False

    WebDriverWait(driver, bi.WAIT_TIMEOUT).until(aba_contabilidade)
    bi.garantir_periodo_correto(driver)


XPATH_CARDS = "//notification-message//li"
XPATH_PRIMEIRO_CARD = "//notification-message[1]//li"
XPATH_BTN_NOTIFICACAO = ("//*[@id='notification'] | //*[@id='class-notification'] | "
                         "//li[contains(@class, 'notification')]//a | //a[contains(., 'Notificações')]")


def concluido(texto: str) -> bool:
    return "Concluído" in texto or "Concluido" in texto


def baixar_para(driver, nome_relatorio, pasta_destino: Path, nome_final: str) -> Path:
    """
    Aguarda o relatório recém-solicitado ficar 'Concluído' no painel de Notificações, clica nele e move o
    arquivo baixado para pasta_destino/nome_final.

    Versão própria do download do robô do BI (que não é alterado), com três cuidados a mais:
      - o primeiro card do painel pode ser um relatório ANTERIOR já concluído, se o card da nova solicitação
        ainda não apareceu: só aceita o 'Concluído' de um card com o mesmo título que foi visto em andamento
        ou que surgiu depois de abrir o painel;
      - erros depois do clique aparecem, em vez de provocar um segundo clique;
      - o antivírus pode manter o arquivo recém-baixado aberto por alguns segundos: tenta mover de novo.
    """
    pasta_destino.mkdir(parents=True, exist_ok=True)
    baixado = baixar_arquivo(driver, nome_relatorio, Path(nome_final).suffix)
    destino = pasta_destino / nome_final

    def mover():
        destino.unlink(missing_ok=True)
        shutil.move(str(baixado), str(destino))

    com_novas_tentativas(mover)
    print(f"Arquivo salvo como: {destino}")
    return destino


def com_novas_tentativas(acao, tentativas=15):
    """Executa acao(); se o arquivo estiver preso (antivírus), espera e tenta de novo."""
    for tentativa in range(tentativas):
        try:
            return acao()
        except PermissionError:
            if tentativa == tentativas - 1:
                raise
            time.sleep(2)


def baixar_arquivo(driver, nome_relatorio, extensao=".xlsx") -> Path:
    """Aguarda o relatório ficar 'Concluído' nas Notificações, clica nele e devolve o arquivo baixado em DOWNLOADS."""
    arquivos_antes = {p: p.stat().st_mtime for p in DOWNLOADS.glob(f"*{extensao}")}
    janela_original = driver.current_window_handle

    print("Abrindo painel de Notificações...")
    botao = WebDriverWait(driver, bi.WAIT_TIMEOUT).until(EC.presence_of_element_located((By.XPATH, XPATH_BTN_NOTIFICACAO)))
    driver.execute_script("arguments[0].click();", botao)
    time.sleep(1)
    qtd_inicial = len(driver.find_elements(By.XPATH, XPATH_CARDS))
    viu_em_andamento = False

    print(f"Aguardando a conclusão da emissão do relatório '{nome_relatorio}'...")
    limite = time.time() + bi.DOWNLOAD_TIMEOUT
    while True:
        if time.time() > limite:
            raise TimeoutException(f"O relatório não foi concluído em {bi.DOWNLOAD_TIMEOUT} segundos.")
        try:
            texto = driver.find_element(By.XPATH, XPATH_PRIMEIRO_CARD).text
            if nome_relatorio in texto:
                if not concluido(texto):
                    viu_em_andamento = True
                elif viu_em_andamento or len(driver.find_elements(By.XPATH, XPATH_CARDS)) > qtd_inicial:
                    print("Relatório processado com sucesso!")
                    break
        except Exception:
            pass
        time.sleep(1)

    time.sleep(2)
    abas_antes = set(driver.window_handles)
    # o card é buscado de novo a cada tentativa, pois a lista pode ter sido redesenhada
    for tentativa in range(3):
        try:
            card = driver.find_element(By.XPATH, XPATH_PRIMEIRO_CARD)
            alvo = card.find_elements(By.XPATH, f".//p[contains(@class, 'title') or contains(text(), '{nome_relatorio}')]")
            driver.execute_script("arguments[0].click();", alvo[0] if alvo else card)
            break
        except StaleElementReferenceException:
            if tentativa == 2:
                raise
            time.sleep(1)
    print(f"Download do relatório '{nome_relatorio}' iniciado.")

    # se o clique abrir uma aba nova com o arquivo, fecha só ela (pode já ter fechado sozinha) e volta
    time.sleep(1)
    for aba in set(driver.window_handles) - abas_antes:
        try:
            driver.switch_to.window(aba)
            driver.close()
        except NoSuchWindowException:
            pass
    driver.switch_to.window(janela_original)

    limite = time.time() + bi.DOWNLOAD_TIMEOUT
    while True:
        if time.time() > limite:
            raise TimeoutException(f"O arquivo não chegou em {DOWNLOADS} em {bi.DOWNLOAD_TIMEOUT} segundos.")
        novos = [p for p in DOWNLOADS.glob(f"*{extensao}") if arquivos_antes.get(p) != p.stat().st_mtime]
        if novos and not list(DOWNLOADS.glob("*.crdownload")):
            break
        time.sleep(1)

    baixado = max(novos, key=lambda p: p.stat().st_mtime)
    for duplicata in set(novos) - {baixado}:   # às vezes o sistema dispara um download a mais
        duplicata.unlink(missing_ok=True)
    return baixado


XPATH_DESDOBRAMENTO = ("//elo-form-label-column[.//label[contains(normalize-space(.), 'Emitir Desdobramento')]]"
                       " | //*[@id='content']/div[7]/elo-form-label-column")


def desdobramento_marcado(campo):
    """Lê o estado do 'Emitir Desdobramento' pelo HTML do campo (input, aria-checked ou classe)."""
    entradas = campo.find_elements(By.XPATH, ".//input[@type='checkbox']")
    if entradas:
        return entradas[0].is_selected()
    for el in campo.find_elements(By.XPATH, ".//*[@aria-checked]"):
        return el.get_attribute("aria-checked") == "true"
    for el in campo.find_elements(By.XPATH, ".//*[contains(@class, 'checked') or contains(@class, 'active')]"):
        return True
    return None


def emitir_desdobramento(driver, marcado: bool):
    """Marca ou desmarca a opção 'Emitir Desdobramento' do balancete (o portal usa os dois tipos com ela marcada)."""
    campos = driver.find_elements(By.XPATH, XPATH_DESDOBRAMENTO)
    if not campos:
        if marcado:
            raise RuntimeError("Opção 'Emitir Desdobramento' não encontrada na tela do balancete.")
        return
    campo = campos[0]
    estado = desdobramento_marcado(campo)
    if estado is None:
        print("Aviso: não consegui ler o estado do 'Emitir Desdobramento'. HTML do campo:\n"
              + campo.get_attribute("outerHTML")[:1500])
    if estado == marcado:
        return
    label = campo.find_elements(By.XPATH, ".//label[contains(normalize-space(.), 'Emitir Desdobramento')]") \
        or campo.find_elements(By.XPATH, "./div/div/label[2]")
    driver.execute_script("arguments[0].click();", label[0] if label else campo)
    time.sleep(0.3)
    if estado is not None and desdobramento_marcado(campo) != marcado:
        raise RuntimeError("Não foi possível alterar a opção 'Emitir Desdobramento'.")
    print(f"Emitir Desdobramento: {'marcado' if marcado else 'desmarcado'}.")


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


def emitir_balancetes(driver, lista_periodos=None, com_simplificado=True):
    """Balancetes analítico e (se com_simplificado) simplificado de cada período (padrão: periodos())."""
    nome = "Balancete da Despesa"
    bi.abrir_menu_por_busca(driver, "Relatórios")
    bi.filtrar_relatorio(driver, nome)
    bi.selecionar_relatorio_filtrado(driver)
    for inicio, fim in periodos() if lista_periodos is None else lista_periodos:
        pasta = RELATORIOS / f"desp{inicio.year}"
        base = f"contabil_balancete_despesa_-_{MESES_MINUSC[inicio.month - 1]}_{inicio.year}"
        # analítico acumulado: 01/01 até o fim do mês (o portal calcula cada mês pela diferença)
        print(f"\n=== Balancete da despesa analítico - 01/01 a {fim:%d/%m/%Y} ===")
        bi.preencher_periodo_relatorio(driver, date(inicio.year, 1, 1), fim)
        bi.selecionar_tipo_relatorio(driver, "analitico")
        emitir_desdobramento(driver, True)
        bi.gerar_relatorio(driver, formato="xlsx")
        baixar_para(driver, nome, pasta, base + "_-_analitico.xlsx")
        if not com_simplificado:
            continue
        # simplificado do mês: usado só para conferir os totais
        print(f"\n=== Balancete da despesa simplificado - {inicio:%m/%Y} ===")
        bi.preencher_periodo_relatorio(driver, inicio, fim)
        bi.selecionar_tipo_relatorio(driver, "simplificado")
        emitir_desdobramento(driver, True)
        bi.gerar_relatorio(driver, formato="xlsx")
        baixar_para(driver, nome, pasta, base + "_-_simplificado.xlsx")


def selecionar_tipo_recurso(driver, texto="Excesso de arrecadação"):
    """Seleciona o 'Tipo de recurso' do Demonstrativo de Crédito Adicional (select #tipoRecursoCreditoAdicional)."""
    campo = WebDriverWait(driver, bi.WAIT_TIMEOUT).until(
        EC.presence_of_element_located((By.ID, "tipoRecursoCreditoAdicional")))
    select = Select(campo)
    alvo = texto.lower()
    opcao = next((o for o in select.options if o.text.strip().lower() == alvo), None) \
        or next((o for o in select.options if alvo.split()[0] in o.text.lower()), None)
    if opcao is None:
        raise RuntimeError(f"Opção '{texto}' não encontrada no Tipo de recurso: {[o.text for o in select.options]}")
    select.select_by_visible_text(opcao.text)
    time.sleep(0.3)
    print(f"Tipo de recurso selecionado: {opcao.text.strip()}")


def emitir_creditos(driver):
    """Demonstrativo de Crédito Adicional por excesso de arrecadação, de 01/01 ao fim do mês vigente
    (coluna 'Suplementado por excesso' da seção Excesso de arrecadação, aba Receita)."""
    nome = "Demonstrativo de Crédito Adicional"
    mes, ano = bi.obter_mes_ano_vigente()
    inicio, fim = date(ano, 1, 1), date(ano, mes, calendar.monthrange(ano, mes)[1])
    bi.abrir_menu_por_busca(driver, "Relatórios")
    bi.filtrar_relatorio(driver, nome)
    bi.selecionar_relatorio_filtrado(driver)
    print(f"\n=== {nome} (excesso de arrecadação) - {inicio:%d/%m/%Y} a {fim:%d/%m/%Y} ===")
    bi.preencher_periodo_relatorio(driver, inicio, fim)
    selecionar_tipo_recurso(driver)
    bi.gerar_relatorio(driver, formato="xlsx")
    baixar_para(driver, nome, RELATORIOS / "creditos", f"credito_adicional_excesso_{ano}-{mes:02d}.xlsx")


def main():
    enviar = "--sem-envio" not in sys.argv
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    driver = bi.criar_driver(diretorio_download=DOWNLOADS)
    try:
        abrir_contabilidade(driver)
        emitir_receita(driver)
        emitir_balancetes(driver)
        try:
            emitir_creditos(driver)
        except Exception as erro:   # opcional: sem ele, os créditos continuam como estavam
            print(f"AVISO: não foi possível emitir o Demonstrativo de Crédito Adicional: {erro}")
        time.sleep(3)
    finally:
        bi.fechar_driver(driver)
    print("\nRelatórios emitidos. Atualizando os dados do portal...\n")
    ok = atualizar_portal.main(enviar=enviar)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
