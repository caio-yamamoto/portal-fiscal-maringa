"""Lê o RGF e o RREO de Maringá pela API de dados abertos do Siconfi (apidatalake.tesouro.gov.br, sem captcha) e
devolve os mesmos campos que extrair_divida.py, extrair_limites.py e extrair_metas.py tiram das planilhas .xls.

A API não traz as notas explicativas: os períodos lidos por aqui ficam sem elas.

Uso: python3 siconfi_api.py <pasta dados>            acrescenta a divida.json, limites.json e metas.json os períodos
                                                     publicados no Siconfi que ainda não estão neles
     python3 siconfi_api.py <pasta dados> --revisar  também relê os períodos já existentes do exercício atual e do
                                                     anterior e atualiza os que foram retificados no Siconfi"""
import json, os, re, sys, time, unicodedata, urllib.parse, urllib.request
from datetime import date

API = 'https://apidatalake.tesouro.gov.br/ords/siconfi/tt/'
ENTE = 4115200            # código IBGE de Maringá
# campos da dívida que a planilha deixa vazios (e não zero) quando a linha não tem valor
DIV_NONE = {'parc_soc', 'parc_fgts', 'parc_nf', 'aro', 'ppp', 'depjud'}
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def consultar(rel, **filtros):
    """Todos os itens de uma consulta (a API devolve em páginas)."""
    itens, offset = [], 0
    while True:
        url = API + rel + '?' + urllib.parse.urlencode({'id_ente': ENTE, **filtros, 'offset': offset})
        for tentativa in range(4):
            try:
                with urllib.request.urlopen(url, timeout=120) as r:
                    pagina = json.load(r)
                break
            except Exception:
                if tentativa == 3: raise
                time.sleep(5 * (tentativa + 1))
        itens += pagina['items']
        if not pagina.get('hasMore'): return itens
        offset += len(pagina['items'])


def anexo_rgf(ano, q, anexo):
    return consultar('rgf', an_exercicio=ano, in_periodicidade='Q', nr_periodo=q, co_tipo_demonstrativo='RGF',
                     no_anexo=anexo, co_esfera='M', co_poder='E')


def anexo_rreo(ano, b, anexo):
    return consultar('rreo', an_exercicio=ano, nr_periodo=b, co_tipo_demonstrativo='RREO', no_anexo=anexo, co_esfera='M')


def norm(s):
    s = unicodedata.normalize('NFD', str(s)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', s).strip().upper()


class Tabela:
    """Linhas do anexo na ordem da API: (cod_conta, conta, {coluna normalizada: valor})."""
    def __init__(self, itens):
        self.linhas, idx = [], {}
        for i in itens:
            chave = (i['cod_conta'], i['conta'])
            if chave not in idx:
                idx[chave] = len(self.linhas); self.linhas.append((i['cod_conta'], re.sub(r'\s+', ' ', i['conta']).strip(), {}))
            if i['valor'] is not None: self.linhas[idx[chave]][2][norm(i['coluna'])] = float(i['valor'])

    def linha(self, cod=None, prefixo=None, filtro=None):
        for c, conta, vals in self.linhas:
            if (cod is None or c == cod) and (prefixo is None or conta.startswith(prefixo)) and (filtro is None or filtro(vals)):
                return vals
        return None

    def valor(self, coluna, cod=None, prefixo=None, padrao=None, filtro=None):
        """Valor da primeira coluna cujo nome começa com `coluna` (sem acentos, maiúsculas)."""
        vals = self.linha(cod, prefixo, filtro)
        if vals is None: return padrao
        for nome, v in vals.items():
            if nome.startswith(norm(coluna)): return v
        return padrao


# ---------------------------------------------------------------- RGF (quadrimestral)

def rgf(ano, q):
    """{'div', 'ant', 'opc', 'lim'} do quadrimestre, ou None se ainda não foi publicado."""
    a2 = Tabela(anexo_rgf(ano, q, 'RGF-Anexo 02'))
    if not a2.linhas: return None
    a1, a4, a6 = (Tabela(anexo_rgf(ano, q, a)) for a in ('RGF-Anexo 01', 'RGF-Anexo 04', 'RGF-Anexo 06'))
    from campos_siconfi import DK
    col_q = 'ATE O %dº QUADRIMESTRE' % q
    div = {k: a2.valor(col_q, prefixo=p, padrao=None if k in DIV_NONE else 0.0) for k, p in DK}
    ant = {k: a2.valor('SALDO DO EXERCICIO ANTERIOR', prefixo=p, padrao=None if k in DIV_NONE else 0.0) for k, p in DK}
    tot = lambda col: a4.valor(col, cod='RGF4OperacoesDeCreditoTotal', padrao=0.0)
    opc = {'no_quad': tot('NO QUADRIMESTRE'), 'ate_quad': tot('ATE O QUADRIMESTRE'),
           'considerado': a4.valor('VALOR', prefixo='TOTAL CONSIDERADO'), 'pct': a4.valor('% SOBRE', prefixo='TOTAL CONSIDERADO'),
           'limite': a4.valor('VALOR', prefixo='LIMITE GERAL'), 'alerta': a4.valor('VALOR', prefixo='LIMITE DE ALERTA'),
           'rcl_aj': a4.valor('VALOR', prefixo='RECEITA CORRENTE LÍQUIDA AJUSTADA')}

    v6 = lambda cod, pct=False: a6.valor('% SOBRE' if pct else 'VALOR', cod=cod + 'DemonstrativoSimplificado', padrao=0.0)
    lim = {'rcl': a6.valor('VALOR', cod='ReceitaCorrenteLiquida'),
           'rcl_end': a6.valor('VALOR', cod='ReceitaCorrenteLiquidaAjustadaParaCalculoDosLimitesDeEndividamentoDemonstrativoSimplificado'),
           'rcl_pes': a6.valor('VALOR', cod='ReceitaCorrenteLiquidaAjustada')}
    for k, cod in (('dtp', 'DespesaTotalComPessoal'), ('dtp_lim', 'LimiteMaximoDespesaComPessoal'), ('dtp_prud', 'LimitePrudencialDespesaComPessoal'),
                   ('dtp_al', 'LimiteDeAlertaDespesaComPessoal'), ('dcl', 'DividaConsolidadaLiquida'),
                   ('dcl_lim', 'LimiteDefinidoPorResolucaoDoSenadoFederalDividaConsolidada'), ('gar', 'TotalDasGarantiasConcedidas'),
                   ('gar_lim', 'LimiteDefinidoPorResolucaoDoSenadoFederalGarantias'), ('oc', 'OperacoesDeCreditoInternasEExternas'),
                   ('oc_lim', 'LimiteDefinidoPeloSenadoFederalParaOperacoesDeCreditoExternasEInternas'),
                   ('aro', 'OperacoesDeCreditoPorAntecipacaoDaReceitaOrcamentaria'),
                   ('aro_lim', 'LimiteDefinidoPeloSenadoFederalParaOperacoesDeCreditoPorAntecipacaoDaReceita')):
        lim[k], lim[k + '_p'] = v6(cod), v6(cod, True)
    rp = a6.linha(cod='ValorTotalRestosAPagarDemonstrativoSimplificado')
    lim['rpnp'] = a6.valor('RESTOS A PAGAR', cod='ValorTotalRestosAPagarDemonstrativoSimplificado', padrao=0.0) if rp is not None else None
    lim['caixa_rp'] = a6.valor('DISPONIBILIDADE', cod='ValorTotalRestosAPagarDemonstrativoSimplificado', padrao=0.0) if rp is not None else None
    for k, p in (('ded_emi', '(-) Transferências Obrigatórias da União Relativas às Emendas Individuais'),
                 ('ded_ban', '(-) Transferências obrigatórias da União relativas às emendas de bancada'),
                 ('ded_acs', '(-) Transferências da União relativas à remuneração')):
        lim[k] = a1.valor('VALOR', prefixo=p, padrao=0.0)

    from campos_siconfi import PES
    meses = ['<MR-%d>' % i for i in range(11, 0, -1)] + ['<MR>']
    def pos(p):
        vals = a1.linha(prefixo=p)
        if vals is None: vals = {}
        g = lambda nome: next((v for c, v in vals.items() if c == norm(nome) or c.startswith(norm(nome))), 0.0)
        return [g('TOTAL (ULTIMOS 12 MESES)'), g('INSCRITAS EM RESTOS A PAGAR'), [vals.get(m, 0.0) for m in meses]]
    lim['pes'] = {k: pos(p) for k, p in PES}
    return {'div': div, 'ant': ant, 'opc': opc, 'lim': lim}


# ---------------------------------------------------------------- RREO (bimestral)

def rreo(ano, b):
    """{'met', 'lim'} do bimestre, ou None se ainda não foi publicado."""
    a6 = Tabela(anexo_rreo(ano, b, 'RREO-Anexo 06'))
    if not a6.linhas: return None
    a14 = Tabela(anexo_rreo(ano, b, 'RREO-Anexo 14'))
    from campos_siconfi import REC, DES
    eh_rec = lambda vals: any(c.startswith(('PREVISAO ATUALIZADA', 'RECEITAS REALIZADAS')) for c in vals)
    eh_des = lambda vals: any(c.startswith(('DOTACAO', 'DESPESAS ')) for c in vals)
    COL_REC = ['PREVISAO ATUALIZADA', 'RECEITAS REALIZADAS']
    COL_DES = ['DOTACAO ATUALIZADA', 'DESPESAS EMPENHADAS', 'DESPESAS LIQUIDADAS', 'DESPESAS PAGAS', 'RESTOS A PAGAR PROCESSADOS', 'LIQUIDADOS', 'PAGOS']
    def cols(prefixo, nomes, filtro):
        return [a6.valor(c, prefixo=prefixo, padrao=0.0, filtro=filtro) for c in nomes]
    um = lambda cod, col='VALOR': a6.valor(col, cod=cod, padrao=0.0)
    ab = lambda cod: [a6.valor('EM 31/12', cod=cod, padrao=0.0), a6.valor('ATE O BIMESTRE', cod=cod, padrao=0.0)]
    met = {'rec': {k: cols(p, COL_REC, eh_rec) for k, p, nv in REC}, 'des': {k: cols(p, COL_DES, eh_des) for k, p, nv in DES},
           'prim_rpps': um('ResultadoPrimarioComRPPSAcimaDaLinha'), 'prim': um('ResultadoPrimarioSemRPPSAcimaDaLinha'),
           'meta_prim': um('RREO6MetaDeResultadoPrimarioFixadaNoAnexoDeMetasFiscaisDaLDOParaOExercicioDeReferencia', 'VALOR CORRENTE'),
           'jur_at': um('JurosEncargosEVariacoesMonetariasAtivosExcetoRPPS', 'VALOR INCORRIDO'),
           'jur_pas': um('JurosEncargosEVariacoesMonetariasPassivosExcetoRPPS', 'VALOR INCORRIDO'),
           'nom': um('ResultadoNominalAcimaDaLinhaSemRPPS'),
           'meta_nom': um('MetaDeResultadoNominalFixadaNoAnexoDeMetasFiscaisDaLDOParaOExercicioDeReferencia', 'VALOR CORRENTE'),
           'dc': ab('DividaConsolidada'), 'ded': ab('DeducoesDaDividaConsolidada'), 'caixa': ab('DisponibilidadeDeCaixaBruta'),
           'rpp': ab('RestosAPagarProcessadosExcetoPrecatorios'), 'dep': ab('DepositosRestituiveisEValoresVinculados'), 'dcl': ab('DividaConsolidadaLiquida'),
           'nom_ab': um('ResultadoNominalAbaixoDaLinhaSemRPPS'), 'aj_rpp': um('VariacaoSaldoRPP'), 'aj_camb': um('VariacaoCambial'),
           'nom_ab_aj': um('ResultadoNominalAbaixoDaLinhaSemRPPSAjustado'), 'prim_ab': um('ResultadoPrimarioAbaixoDaLinhaSemRPPS'),
           'sup': um('SuperavitFinanceiro', 'PREVISAO')}
    v14 = lambda cod, col: a14.valor(col, cod=cod)
    MDE, FUN, SAU = ('MinimoAnualDasReceitasDeImpostosNaManutencaoEDesenvolvimentoDoEnsinoDemonstrativoSimplificado',
                     'MinimoAnualDoFUNDEBNaRemuneracaoDoMagisterioComEducacaoInfantilEnsinoFundamentalEMedioDemonstrativoSimplificado',
                     'AplicacaoTotalDasDespesasComAcoesEServicosPublicosDeSaude')
    lim = {}
    for k, cod in (('mde', MDE), ('fundeb', FUN), ('asps', SAU)):
        lim[k], lim[k + '_min'], lim[k + '_p'] = v14(cod, 'VALOR APURADO ATE O BIMESTRE'), v14(cod, '% MINIMO'), v14(cod, '% APLICADO')
    for k, cod in (('oc_rec', 'ReceitaDeOperacoesDeCreditoDemonstrativoSimplificado'), ('dcap', 'DespesaDeCapitalLiquidaDemonstrativoSimplificado')):
        lim[k], lim[k + '_sal'] = v14(cod, 'VALOR APURADO NO EXERCICIO'), v14(cod, 'SALDO NAO REALIZADO')
    return {'met': met, 'lim': lim}


# ---------------------------------------------------------------- atualização dos JSON do portal

def conferir_rgf(r):
    d = r['div']; erros = []
    def chk(a, b, nome):
        if a is None or b is None or abs(a - b) > 1: erros.append('%s (%s x %s)' % (nome, a, b))
    chk((d['dc'] or 0) - (d['ded'] or 0), d['dcl'], 'DC - deduções = DCL')
    chk((d['mob'] or 0) + (d['contr'] or 0) + (d['prec'] or 0) + (d['outras'] or 0), d['dc'], 'componentes = DC')
    L = r['lim']; liq = L['pes']['liquida']
    chk(liq[0] + liq[1], L['dtp'], 'DTP = líquida + RPNP')
    chk(L['pes']['bruta'][0] - L['pes']['naocomp'][0], liq[0], 'bruta - não computadas = líquida')
    return erros


def conferir_rreo(r):
    m = r['met']; dp = m['des']['dpt']; erros = []
    calc = m['rec']['rpt'][1] - (dp[3] + dp[4] + dp[6])
    if abs(calc - m['prim']) > 1: erros.append('primário (%s x %s)' % (calc, m['prim']))
    if abs(m['prim'] + m['jur_at'] - m['jur_pas'] - m['nom']) > 1: erros.append('nominal')
    return erros


def diferente(a, b):
    """True se os valores diferem em mais de R$ 0,01 (vazio e zero contam como iguais; notas não entram)."""
    if isinstance(a, dict):
        return any(diferente(a.get(k), (b or {}).get(k)) for k in set(a) | set(b or {}) if k not in ('nota', 'notas'))
    if isinstance(a, list):
        return not isinstance(b, list) or len(a) != len(b) or any(diferente(x, y) for x, y in zip(a, b))
    return abs((a or 0) - (b or 0)) > 0.01


def atualizar(dados, revisar=False):
    """Acrescenta (e, com revisar, atualiza) os períodos do exercício atual e do anterior. Devolve o que mudou."""
    J = {n: json.load(open(os.path.join(dados, n + '.json'), encoding='utf8')) for n in ('divida', 'limites', 'metas')}
    mudou = []
    for ano in (date.today().year - 1, date.today().year):
        a = str(ano)
        D = J['divida']['anos'].get(a) or {'quads': [], 'anterior': None, 'q': {}, 'opc': {}, 'notas': {}}
        L = J['limites']['anos'].get(a) or {'quads': [], 'q': {}, 'bims': [], 'b': {}}
        M = J['metas']['anos'].get(a) or {'bims': [], 'b': {}}
        for q in (1, 2, 3):
            existe = q in D['quads'] and q in L['quads']
            if existe and not revisar: continue
            r = rgf(ano, q)
            if r is None: break
            if existe and not (diferente(D['q'][str(q)], r['div']) or diferente(D['opc'][str(q)], r['opc'])
                               or diferente({k: v for k, v in L['q'][str(q)].items()}, r['lim'])):
                continue
            erros = conferir_rgf(r)
            if erros: raise RuntimeError('RGF %dº quadrimestre de %d: conferência falhou: %s' % (q, ano, '; '.join(erros)))
            D['q'][str(q)], D['opc'][str(q)], L['q'][str(q)] = r['div'], r['opc'], r['lim']
            if D['anterior'] is None: D['anterior'] = r['ant']
            for lista in (D['quads'], L['quads']):
                if q not in lista: lista.append(q); lista.sort()
            mudou.append('RGF %dº quadrimestre de %d %s' % (q, ano, 'retificado' if existe else 'novo'))
        for b in range(1, 7):
            existe = b in M['bims'] and b in L['bims']
            if existe and not revisar: continue
            r = rreo(ano, b)
            if r is None: break
            if existe and not (diferente(M['b'][str(b)], r['met']) or diferente(L['b'][str(b)], r['lim'])):
                continue
            erros = conferir_rreo(r)
            if erros: raise RuntimeError('RREO %dº bimestre de %d: conferência falhou: %s' % (b, ano, '; '.join(erros)))
            nota = M['b'].get(str(b), {}).get('nota')
            M['b'][str(b)], L['b'][str(b)] = r['met'], r['lim']
            if nota: M['b'][str(b)]['nota'] = nota   # a API não traz as notas: mantém as da planilha
            for lista in (M['bims'], L['bims']):
                if b not in lista: lista.append(b); lista.sort()
            mudou.append('RREO %dº bimestre de %d %s' % (b, ano, 'retificado' if existe else 'novo'))
        # só grava o exercício se ele tiver algum período (o portal lista os anos que existem nos dados)
        if D['quads']: J['divida']['anos'][a] = D
        if L['quads'] or L['bims']: J['limites']['anos'][a] = L
        if M['bims']: J['metas']['anos'][a] = M
    if mudou:
        for n, d in J.items():
            d['anos'] = dict(sorted(d['anos'].items()))
            json.dump(d, open(os.path.join(dados, n + '.json'), 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
    return mudou


if __name__ == '__main__':
    mudou = atualizar(sys.argv[1], revisar='--revisar' in sys.argv)
    print('Siconfi: ' + (', '.join(mudou) if mudou else 'nenhum relatório novo.'))
