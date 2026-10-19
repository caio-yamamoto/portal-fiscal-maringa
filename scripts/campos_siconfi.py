"""Linhas do RGF e do RREO usadas pelo portal: (campo, início do rótulo da linha[, nível]).
Compartilhadas pela leitura das planilhas do Siconfi (extrair_*.py) e pela leitura da API (siconfi_api.py)."""
DK = [('dc','DÍVIDA CONSOLIDADA - DC (I)'),('mob','Dívida Mobiliária'),('contr','Dívida Contratual'),('emp','Empréstimos'),('emp_int','Internos'),('emp_ext','Externos'),
      ('reest','Reestruturação da Dívida'),('fin','Financiamentos'),('parc','Parcelamento e Renegociação'),('parc_trib','De Tributos'),('parc_prev','De Contribuições Previdenciárias'),
      ('parc_soc','De Demais Contribuições Sociais'),('parc_fgts','Do FGTS'),('parc_nf','Com Instituição Não Financeira'),
      ('demais','Demais Dívidas Contratuais'),('prec','Precatórios Posteriores a 05/05/2000 (inclusive) Vencidos'),('outras','Outras Dívidas'),('ded','DEDUÇÕES (II)'),
      ('caixa','Disponibilidade de Caixa Bruta'),('rpp','(-) Restos a Pagar Processados'),('dep','(-) Depósitos Restituíveis'),('haveres','Demais Haveres Financeiros'),
      ('dcl','DÍVIDA CONSOLIDADA LÍQUIDA (DCL)'),('rcl','RECEITA CORRENTE LÍQUIDA - RCL (IV)'),('emendas','(-) Transferências Obrigatórias da União'),('rcl_aj','RECEITA CORRENTE LÍQUIDA AJUSTADA'),
      ('pdc','% da DC sobre'),('pdcl','% da DCL sobre'),('lim','LIMITE DEFINIDO'),('alerta','LIMITE DE ALERTA'),
      ('prec_ant','Precatórios Anteriores a 05/05/2000'),('prec_fora','Precatórios Posteriores a 05/05/2000 (Não incluídos na DC)'),('atuarial','Passivo Atuarial'),('rpnp','RP Não-Processados'),
      ('aro','Antecipações de Receita Orçamentária'),('ppp','Dívida Contratual de PPP'),('depjud','Apropriação de Depósitos Judiciais')]
PES = [('bruta','DESPESA BRUTA COM PESSOAL'),('ativo','Pessoal Ativo'),('venc','Vencimentos, Vantagens'),('patr','Obrigações Patronais'),('inat','Pessoal Inativo e Pensionistas'),
       ('apos','Aposentadorias'),('pens','Pensões'),('terc','Outras Despesas de Pessoal decorrentes de Contratos de Terceirização'),('naoexec','Despesa com Pessoal não Executada'),
       ('naocomp','DESPESAS NÃO COMPUTADAS'),('indeniz','Indenizações por Demissão'),('judic','Decorrentes de Decisão Judicial'),('dea','Despesas de Exercícios Anteriores'),
       ('inatvinc','Inativos e Pensionistas com Recursos Vinculados'),('acs','Agentes Comunitários'),('enferm','Parcela dedutível referente ao piso'),('outded','Outras Deduções Constitucionais'),
       ('liquida','DESPESA LÍQUIDA COM PESSOAL')]
REC = [('rc','RECEITAS CORRENTES (EXCETO FONTES RPPS)',0),('imp','Impostos, Taxas e Contribuições de Melhoria',1),('iptu','IPTU',2),('iss','ISS',2),('itbi','ITBI',2),('irrf','IRRF',2),('oimp','Outros Impostos',2),
       ('contr','Contribuições',1),('pat','Receita Patrimonial',1),('aplic','Aplicações Financeiras',2),('opat','Outras Receitas Patrimoniais',2),('tc','Transferências Correntes',1),('fpm','Cota-Parte do FPM',2),('icms','Cota-Parte do ICMS',2),
       ('ipva','Cota-Parte do IPVA',2),('itr','Cota-Parte do ITR',2),('lc61','Transferências da LC',2),('fundeb','Transferências do FUNDEB',2),('otc','Outras Transferências Correntes',2),('drc','Demais Receitas Correntes',1),
       ('rpc','RECEITAS PRIMÁRIAS CORRENTES (EXCETO',0),('rk','RECEITAS DE CAPITAL (EXCETO',0),('opc','Operações de Crédito',1),('alien','Alienação de Bens',1),('tk','Transferências de Capital',1),('conv','Convênios',2),('otk','Outras Transferências de Capital',2),('ork','Outras Receitas de Capital',1),
       ('rpk','RECEITAS PRIMÁRIAS DE CAPITAL (EXCETO',0),('rpt','RECEITA PRIMÁRIA TOTAL (EXCETO',0),('rpt_rpps','RECEITA PRIMÁRIA TOTAL (XVI)',0)]
DES = [('dc','DESPESAS CORRENTES (EXCETO FONTES RPPS)',0),('pes','Pessoal e Encargos Sociais',1),('jur','Juros e Encargos da Dívida',1),('odc','Outras Despesas Correntes',1),('dpc','DESPESAS PRIMÁRIAS CORRENTES (EXCETO',0),
       ('dk','DESPESAS DE CAPITAL (EXCETO',0),('inv','Investimentos',1),('invf','Inversões Financeiras',1),('amort','Amortização da Dívida',1),('dpk','DESPESAS PRIMÁRIAS DE CAPITAL (EXCETO',0),('res','RESERVA DE CONTINGÊNCIA',0),
       ('dpt','DESPESA PRIMÁRIA TOTAL (EXCETO',0),('dpt_rpps','DESPESA PRIMÁRIA TOTAL (XXXII)',0)]
