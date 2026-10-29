"""Créditos adicionais por excesso de arrecadação, a partir do "Demonstrativo de Crédito Adicional" do Elotech.

Uso: python scripts/extrair_creditos.py <pasta com as planilhas> dados/creditos.json

Lê todas as planilhas .xlsx da pasta (emitidas de 01/01 até o fim de um mês, filtradas pelo tipo de recurso
"Excesso de arrecadação"). Para cada exercício, usa a planilha de emissão mais recente. Em cada decreto guarda as
receitas indicadas como recurso (fonte, natureza, valor) e a data de lançamento, que o portal usa para considerar
só os créditos abertos até o mês escolhido.

Conferências: em cada decreto, total das dotações = total das receitas = "Total Suplementação"; soma geral =
"Total Suplementações" do relatório.
"""
import glob, json, os, re, sys
from datetime import datetime
import openpyxl


def ler(caminho):
    ws = openpyxl.load_workbook(caminho).active
    info = {'arquivo': os.path.basename(caminho), 'decretos': [], 'total': None, 'ano': None, 'emissao': None, 'periodo': None}
    d = None
    for r in ws.iter_rows(values_only=True):
        r = list(r) + [None] * 30
        if info['emissao'] is None:
            dt = next((x for x in r if isinstance(x, datetime)), None)
            if dt: info['emissao'] = dt
        txt = ' | '.join(str(x) for x in r if x is not None)
        if txt.startswith('Exercício:'):
            info['ano'] = re.search(r'\d{4}', txt).group(0); continue
        if txt.startswith('Período:'):
            info['periodo'] = txt.split(':', 1)[1].strip(); continue
        if txt.startswith('Lei:') and 'Decreto:' in txt:
            d = {'lei': re.search(r'Lei: ([^|]+)', txt).group(1).strip(),
                 'decreto': re.search(r'Decreto: ([^|]+)', txt).group(1).strip(),
                 'lanc': re.search(r'Lançamento: ([\d/]+)', txt).group(1),
                 'dot': 0.0, 'rec': [], 'tot': None, 'tot_rec': None}
            info['decretos'].append(d); continue
        if r[15] == 'Total Suplementações':
            info['total'] = float(r[19]); continue
        if d is None:
            continue
        if txt.startswith('Data Lei:'):
            m = re.search(r'Data Decreto: ([\d/]+)', txt); d['data'] = m.group(1) if m else None; continue
        if txt.startswith('Tipo de Crédito:'):
            d['tipo'] = re.search(r'Tipo de Crédito: ([^|]+)', txt).group(1).strip()
            d['recurso'] = re.search(r'Tipo de Recurso: ([^|]+)', txt).group(1).strip(); continue
        # lado esquerdo: dotação suplementada
        if isinstance(r[0], (int, float)) and r[3]:
            d['dot'] += float(r[8])
        elif r[5] == 'Total Suplementação':
            d['tot'] = float(r[8])
        # lado direito: receita indicada como recurso
        if r[14] and re.match(r'^\d\.\d', str(r[14])):
            d['rec'].append([str(r[21]).strip(), str(r[14]).strip(), round(float(r[24]), 2)])
        elif r[17] == 'Total':
            d['tot_rec'] = float(r[24])
    return info


def conferir(info):
    erros = []
    for d in info['decretos']:
        sr = sum(x[2] for x in d['rec'])
        if d.get('recurso') != 'Excesso de arrecadação':
            erros.append(f"decreto {d['decreto']}: tipo de recurso '{d.get('recurso')}' (esperado excesso de arrecadação)")
        for nome, v in (('dotações', d['dot']), ('total do decreto', d['tot']), ('total das receitas', d['tot_rec'])):
            if v is None or abs(v - sr) > 0.01:
                erros.append(f"decreto {d['decreto']}: receitas {sr:.2f} ≠ {nome} {v}")
    soma = sum(x[2] for d in info['decretos'] for x in d['rec'])
    if info['total'] is None or abs(soma - info['total']) > 0.01:
        erros.append(f"soma dos decretos {soma:.2f} ≠ Total Suplementações {info['total']}")
    return erros


def main(pasta, saida):
    arqs = sorted(glob.glob(os.path.join(pasta, '*.xlsx')))
    if not arqs:
        print('Nenhuma planilha de créditos adicionais em', pasta); return
    por_ano = {}
    for a in arqs:
        info = ler(a)
        if not info['ano']:
            print('Ignorada (sem exercício):', a); continue
        atual = por_ano.get(info['ano'])
        if atual is None or (info['emissao'] or datetime.min) > (atual['emissao'] or datetime.min):
            por_ano[info['ano']] = info
    out = {'anos': {}}
    if os.path.exists(saida):
        out = json.load(open(saida, encoding='utf-8'))
    for ano, info in sorted(por_ano.items()):
        erros = conferir(info)
        if erros:
            print('ERRO na conferência de', info['arquivo']); print('\n'.join(erros[:20])); sys.exit(1)
        out['anos'][ano] = {
            'emissao': info['emissao'].strftime('%d/%m/%Y %H:%M') if info['emissao'] else None,
            'periodo': info['periodo'], 'total': round(info['total'], 2),
            'decretos': [{'decreto': d['decreto'], 'data': d.get('data'), 'lanc': d['lanc'], 'rec': d['rec']} for d in info['decretos']]}
        print(f"{ano}: {len(info['decretos'])} decretos, R$ {info['total']:,.2f} ({info['arquivo']}) — conferido")
    json.dump(out, open(saida, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'), sort_keys=True)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
