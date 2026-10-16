"""
Pergunta, em dias úteis, se o usuário quer atualizar o Portal Fiscal e, se a resposta for Sim, roda o
robô (robo_portal.py) numa janela de terminal própria. Chamado por duas tarefas do Agendador do Windows
(criadas por agendar_no_windows.ps1):

  python iniciar_com_windows.py --logon     ao entrar no Windows: pergunta só na primeira vez do dia
  python iniciar_com_windows.py --horario   às 13:10: pergunta sempre (dias úteis)

Antes de perguntar, espera a internet chegar ao sistema contábil e ao GitHub (até 10 minutos). Se o robô
já estiver rodando, não pergunta. A janela da pergunta some sozinha após 30 minutos sem resposta (= Não).
Cada execução do robô fica registrada em robo/logs/.
"""
import ctypes
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path
from urllib.request import urlopen

AQUI = Path(__file__).resolve().parent
LOGS = AQUI / "logs"
TRAVA = AQUI / "logs" / "robo_em_execucao.txt"
MARCA_LOGON = AQUI / "logs" / "ultima_pergunta_ao_entrar.txt"
SITES = ["https://maringa.oxy.elotech.com.br", "https://github.com"]
ESPERA_INTERNET = 10 * 60      # segundos
TEMPO_PERGUNTA = 30 * 60       # segundos até a pergunta fechar sozinha
TITULO = "Portal Fiscal de Maringá"


def dia_util() -> bool:
    return date.today().weekday() < 5     # segunda (0) a sexta (4); feriados não são considerados


def internet_ok() -> bool:
    for site in SITES:
        try:
            urlopen(site, timeout=10).close()
        except Exception as erro:
            # resposta HTTP de erro (ex.: 403 do Cloudflare) também prova que há conexão
            if not hasattr(erro, "code"):
                return False
    return True


def esperar_internet() -> bool:
    limite = time.time() + ESPERA_INTERNET
    while time.time() < limite:
        if internet_ok():
            return True
        time.sleep(15)
    return False


def robo_rodando() -> bool:
    """Trava gravada pela execução do robô; uma trava com mais de 2 horas é considerada abandonada."""
    return TRAVA.exists() and time.time() - TRAVA.stat().st_mtime < 2 * 3600


def perguntar() -> bool:
    MB_YESNO, MB_ICONQUESTION, MB_TOPMOST, MB_SETFOREGROUND, IDYES = 0x4, 0x20, 0x40000, 0x10000, 6
    texto = ("Deseja atualizar o Portal Fiscal agora?\n\n"
             "O robô vai abrir o Chrome, emitir os relatórios no Elotech (pode pedir o login), "
             "conferir com o balancete simplificado e enviar os dados ao GitHub.")
    estilo = MB_YESNO | MB_ICONQUESTION | MB_TOPMOST | MB_SETFOREGROUND
    # MessageBoxTimeoutW fecha a janela sozinha depois do tempo dado (retorna 32000)
    resposta = ctypes.windll.user32.MessageBoxTimeoutW(None, texto, TITULO, estilo, 0, TEMPO_PERGUNTA * 1000)
    return resposta == IDYES


def abrir_janela_do_robo():
    """Abre um terminal novo rodando este mesmo script em modo --executar."""
    python = Path(sys.executable)
    if python.name.lower().startswith("pythonw"):
        python = python.with_name(python.name.lower().replace("pythonw", "python"))
    subprocess.Popen([str(python), str(Path(__file__).resolve()), "--executar"], cwd=AQUI,
                     creationflags=subprocess.CREATE_NEW_CONSOLE)


def executar():
    """Roda o robô nesta janela, mostra a saída e grava um registro em logs/."""
    import os
    LOGS.mkdir(exist_ok=True)
    TRAVA.write_text(datetime.now().isoformat(), encoding="utf-8")
    registro = LOGS / f"{datetime.now():%Y-%m-%d_%H%M}.log"
    print(f"{TITULO} - atualização iniciada em {datetime.now():%d/%m/%Y %H:%M}\n")
    linhas = []
    try:
        ambiente = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
        with subprocess.Popen([sys.executable, "robo_portal.py"], cwd=AQUI, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                              env=ambiente) as proc, open(registro, "w", encoding="utf-8") as log:
            for linha in proc.stdout:
                print(linha, end="")
                log.write(linha)
                linhas.append(linha)
            codigo = proc.wait()
    finally:
        TRAVA.unlink(missing_ok=True)

    saida = "".join(linhas)
    if codigo == 0 and "Dados enviados" in saida:
        resumo = "Portal atualizado. O site é republicado em cerca de 1 minuto."
    elif codigo == 0:
        resumo = "Concluído. Nada mudou nos dados; nada foi enviado."
    elif "NÃO foram enviados" in saida:
        resumo = ("A conferência apontou diferença e os dados NÃO foram enviados (veja acima).\n"
                  "Se a causa for conhecida, envie com:  python robo\\atualizar_portal.py --forcar")
    else:
        resumo = "O robô parou com erro (veja acima). Nada foi enviado."
    with open(registro, "a", encoding="utf-8") as log:
        log.write(f"\nRESUMO: {resumo}\n")
    print("\n" + "=" * 70 + "\n" + resumo + "\n" + "=" * 70)
    print(f"Registro salvo em {registro}")
    input("\nTecle Enter para fechar esta janela.")


def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else "--horario"
    if modo == "--executar":
        executar()
        return
    if not dia_util():
        return
    LOGS.mkdir(exist_ok=True)
    hoje = date.today().isoformat()
    if modo == "--logon":
        if MARCA_LOGON.exists() and MARCA_LOGON.read_text(encoding="utf-8").strip() == hoje:
            return
        MARCA_LOGON.write_text(hoje, encoding="utf-8")
    if not esperar_internet() or robo_rodando():
        return
    if perguntar():
        abrir_janela_do_robo()


if __name__ == "__main__":
    main()
