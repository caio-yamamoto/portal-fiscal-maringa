# Portal de Gestão Orçamentária e Fiscal — Prefeitura de Maringá

Painel independente (não oficial) com a execução orçamentária e os indicadores fiscais de Maringá/PR.
Site: https://caio-yamamoto.github.io/portal-fiscal-maringa/ (GitHub Pages, publicado pelo workflow
`.github/workflows/publicar.yml` a cada push em `dados/`, `src/`, `scripts/`).

Responda sempre em português do Brasil. O usuário é contador público (orçamento da Prefeitura).

## Abas e fontes de dados

| Aba | Fonte | Recorte |
|---|---|---|
| Receita | Elotech: "Receita Realizada por Fonte" (mensal, xlsx) + Previsão Orçamentária do ano + Anexo 2 (quadro da receita por natureza, só para nomes) | Prefeitura, sem a Maringá Previdência |
| Despesa | Elotech: "Balancete da Despesa" ANALÍTICO de 01/01 até o fim de cada mês (xlsx); cada mês = acumulado do mês − acumulado do anterior. O reservado é posição (estoque). | Prefeitura |
| Receita × Despesa | receita e despesa acima, por fonte de recursos | Prefeitura |
| Dívida consolidada | Siconfi: RGF Anexos 2 e 4 | Município |
| Metas fiscais | Siconfi: RREO Anexo 6 | Município, sem RPPS |
| Limites legais | Siconfi: RGF Anexos 1 e 6, RREO Anexo 14 | Poder Executivo |

Regras de fonte de recursos (já implementadas nos scripts/portal):
- Superávit (exercícios anteriores): 4 dígitos começando com 2 → equivale à 1xxx; 5 dígitos começando com 1 ou 2 usam o 1º dígito; demais, o 2º dígito.
- Exceções: 99999 = Reserva de Contingência; 4101 e 4102 são recursos do exercício das fontes 1101 e 1102 ("… – Educação Integral"); no Receita × Despesa somam-se a 1101/1102.

## Estrutura

- `src/portal.html`, `src/base.css` — o portal (HTML/CSS/JS num arquivo só). Receita e despesa entram compactadas (gzip + base64) e o navegador descompacta: o arquivo final fica ~1,3 MB.
- `scripts/` — leitores (`ler_*.py`, `extrair_*.py`, `lim_load.py`) e montagem (`montar.py`, `atualizar.sh`).
- `dados/*.json` — dados extraídos (públicos, os mesmos do portal).
- `robo/` — robô que emite os relatórios no Elotech e atualiza o portal (ver abaixo).
- `relatorios_locais/` — planilhas originais do Elotech, só no computador do usuário (no `.gitignore`; o repositório é público).

Montar localmente: `bash scripts/atualizar.sh` (gera `site/index.html`). No Windows, sem bash:
`python scripts/montar.py src/portal.html src/base.css dados/receita.json site/index.html dados/despesa.json`
(o atualizar.sh também envolve o resultado num documento HTML completo, necessário no GitHub Pages).

## Robô (`robo/`) — testado no computador do usuário em 16/10/2026

- `robo/robo_portal.py`: reaproveita a navegação e o login do robô do Power BI do usuário
  (`robo/automacao_relatorios_bi.py`, cópia do original em `Desktop\Python\Automacao_Relatorio_BI`, que NÃO vai
  para o GitHub e NÃO deve ser alterada — correções para o portal vão no `robo_portal.py`). O download pelo painel
  de Notificações é próprio do `robo_portal.py` (`baixar_para`). Abre o Chrome com perfil persistente; o login é
  MANUAL (Cloudflare "Confirme que é humano" — não tentar contornar). Emite, para o mês vigente e o anterior:
  receita realizada por fonte (mês), balancete analítico (01/01 até o fim do mês) e balancete simplificado (mês),
  os dois balancetes com "Emitir Desdobramento" marcado. Salva em `relatorios_locais/`.
- Diferença no mês vigente só em liquidado/pago, em horário de expediente, costuma ser lançamento feito entre a
  emissão do analítico e a do simplificado (o mês está aberto); rodar fora do expediente ou usar `--forcar`.
- `robo/atualizar_portal.py`: roda `extrair_receita.py` e `extrair_despesa.py`, confere empenhado/liquidado/pago de
  cada mês com o simplificado (tolerância R$ 1) e, se bater, faz commit e push só de `dados/receita.json` e
  `dados/despesa.json`. Se não bater, não envia e explica (causa usual: lançamento retroativo no mês anterior →
  reemitir o analítico do mês anterior).
- Pontos a verificar no primeiro teste: seletores do Elotech (vêm do robô do BI e funcionam lá); nomes dos
  arquivos; troca de exercício em janeiro (o mês anterior é de outro ano e hoje fica de fora); tempo do
  `extrair_despesa.py` na primeira execução (lê todos os balancetes; depois usa cache em `cache_desp/`).

## Conferências que devem continuar valendo

- Despesa: totais mensais do analítico = balancete simplificado do mês (empenhado, liquidado, pago, dotação atualizada).
- Saldo a empenhar = dotação atualizada − empenhado − reservado.
- Receita: soma das linhas por fonte = total da fonte no relatório.
