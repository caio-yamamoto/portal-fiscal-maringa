"""
Gera os dados do portal a partir das planilhas em relatorios_locais/, confere o balancete analítico com
o simplificado e envia receita.json e despesa.json ao GitHub. O GitHub Actions monta e publica o site.

As planilhas originais NÃO são enviadas (o repositório do portal é público); vão só os dados já
agregados, que são os mesmos exibidos no portal.

Uso:  python atualizar_portal.py             (gera, confere e envia)
      python atualizar_portal.py --sem-envio (gera e confere, sem enviar)
      python atualizar_portal.py --forcar    (envia os dados já gerados, sem conferir de novo: use depois que
                                              a conferência apontou uma diferença de causa conhecida)
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import warnings
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parent
RELATORIOS = REPO / "relatorios_locais"
DADOS = REPO / "dados"
PY = sys.executable
MESES = {m: i + 1 for i, m in enumerate(["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
                                          "agosto", "setembro", "outubro", "novembro", "dezembro"])}
TOLERANCIA = 1.00   # R$


def localizar_git() -> str:
    """O Git pode não estar no PATH de um terminal aberto antes da instalação; procura nos locais usuais."""
    achado = shutil.which("git")
    if achado:
        return achado
    for pasta in (os.environ.get("LOCALAPPDATA", ""), os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", "")):
        for sub in ("Programs\\Git\\cmd\\git.exe", "Git\\cmd\\git.exe"):
            caminho = Path(pasta) / sub
            if pasta and caminho.exists():
                return str(caminho)
    raise RuntimeError("Git não encontrado. Instale o Git (git-scm.com) ou feche e abra o VS Code de novo.")


GIT = localizar_git()
# os scripts filhos imprimem em UTF-8 (senão os acentos chegam quebrados no Windows)
AMBIENTE = {**os.environ, "PYTHONIOENCODING": "utf-8"}


def rodar(*args, cwd=REPO):
    print("$", " ".join(str(a) for a in args))
    r = subprocess.run([str(a) for a in args], cwd=cwd, text=True, capture_output=True, encoding="utf-8",
                       errors="replace", env=AMBIENTE)
    saida = (r.stdout or "") + (r.stderr or "")
    linhas = [l for l in saida.splitlines() if "warn" not in l.lower()]
    print("\n".join(linhas[-12:]))
    if r.returncode != 0:
        raise RuntimeError(f"falhou: {' '.join(str(a) for a in args)}")
    return saida


def gerar():
    rodar(PY, REPO / "scripts" / "extrair_receita.py", RELATORIOS, RELATORIOS / "quadros", DADOS / "receita.json")
    rodar(PY, REPO / "scripts" / "extrair_despesa.py", RELATORIOS, DADOS / "despesa.json")


def totais_simplificado(arq: Path):
    """(mês, ano, {emp, liq, pago}) lidos da linha 'Totais' e do cabeçalho 'Período: Outubro/2026 até ...'."""
    import openpyxl
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ws = openpyxl.load_workbook(arq, data_only=True).worksheets[0]
    mes = ano = tot = None
    for r in ws.iter_rows(values_only=True):
        c = [x for x in r if x is not None]
        if not c:
            continue
        if isinstance(c[0], str) and c[0].startswith("Período:"):
            m = re.search(r"Período:\s*(\w+)/(\d{4})", c[0])
            if m:
                mes, ano = MESES.get(m.group(1).lower()), int(m.group(2))
        if c[0] == "Totais":
            tot = {"emp": float(c[2]), "liq": float(c[3]), "pago": float(c[4])}
    return mes, ano, tot


def conferir():
    """Compara, para cada simplificado disponível do exercício mais recente, o mês gerado com os totais do relatório."""
    D = json.loads((DADOS / "despesa.json").read_text(encoding="utf-8"))
    problemas, conferidos = [], 0
    for arq in sorted(Path(x) for x in glob.glob(str(RELATORIOS / "desp20??" / "*simplificado*.xlsx"))):
        mes, ano, tot = totais_simplificado(arq)
        A = D["anos"].get(str(ano))
        if not (mes and tot and A) or mes > A["meses"]:
            continue
        idx = {"emp": 5, "liq": 6, "pago": 7}
        gerado = {k: sum(it[i][mes - 1] or 0 for it in A["itens"]) for k, i in idx.items()}
        dif = {k: round(gerado[k] - tot[k], 2) for k in idx if abs(gerado[k] - tot[k]) > TOLERANCIA}
        conferidos += 1
        if dif:
            problemas.append(f"{mes:02d}/{ano}: diferença em {dif} (portal − simplificado). "
                             f"Reemita o analítico do mês anterior, se houve lançamento retroativo.")
        else:
            print(f"Conferido {mes:02d}/{ano}: empenhado, liquidado e pago batem com o simplificado.")
    if not conferidos:
        print("Aviso: nenhum balancete simplificado encontrado para conferir.")
    return problemas


def enviar_github():
    rodar(GIT, "pull", "--rebase", "--autostash", "origin", "main")
    rodar(GIT, "add", "dados/receita.json", "dados/despesa.json")
    if subprocess.run([GIT, "diff", "--cached", "--quiet"], cwd=REPO).returncode == 0:
        print("Nada mudou nos dados; nada a enviar.")
        return
    rodar(GIT, "commit", "-m", f"Atualiza dados do portal ({datetime.now():%d/%m/%Y %H:%M}) [robô]")
    rodar(GIT, "push", "origin", "HEAD:main")
    print("Dados enviados. O site é republicado pelo GitHub em cerca de 1 minuto.")


def dados_em_dia() -> bool:
    """True se receita.json e despesa.json são mais novos que todas as planilhas de relatorios_locais."""
    jsons = [DADOS / "receita.json", DADOS / "despesa.json"]
    if not all(j.exists() for j in jsons):
        return False
    gerado = min(j.stat().st_mtime for j in jsons)
    return all(p.stat().st_mtime <= gerado for p in RELATORIOS.rglob("*.xlsx"))


def main(enviar=True, forcar=False) -> bool:
    if forcar and enviar:
        # a conferência já foi feita (e a diferença vista) na execução anterior: só envia
        if dados_em_dia():
            print("Enviando os dados já gerados, sem nova conferência (--forcar).")
        else:
            print("Há relatórios mais novos que os dados: gerando de novo antes de enviar (sem conferência).")
            gerar()
        enviar_github()
        return True
    gerar()
    problemas = conferir()
    for p in problemas:
        print("ATENÇÃO:", p)
    if problemas and not forcar:
        print("\nOs dados foram gerados, mas NÃO foram enviados por causa da diferença acima. "
              "Corrija e rode de novo, ou use --forcar para enviar assim mesmo.")
        return False
    if enviar:
        enviar_github()
    return True


if __name__ == "__main__":
    ok = main(enviar="--sem-envio" not in sys.argv, forcar="--forcar" in sys.argv)
    sys.exit(0 if ok else 1)
