# Portal de Gestão Orçamentária e Fiscal

Painel independente com a execução orçamentária e os indicadores fiscais do Município de Maringá, montado a partir de relatórios do sistema contábil da Prefeitura (Elotech) e dos relatórios publicados no Siconfi. **Não é um site oficial da Prefeitura.**

Abas: Receita · Despesa · Receita × Despesa · Dívida consolidada · Metas fiscais · Limites legais.

## Como atualizar

Coloque os relatórios na pasta `relatorios/`, seguindo esta organização, e envie (pelo site do GitHub: *Add file → Upload files*). O portal é reconstruído e publicado automaticamente em alguns minutos.

| Pasta | O que colocar |
|---|---|
| `relatorios/2026/` | Receita realizada por fonte (um arquivo por mês) e a Previsão Orçamentária do ano |
| `relatorios/quadros/` | Anexo 2 – quadro da receita por natureza (um por mês) |
| `relatorios/desp2026/` | Balancete da despesa **analítico** (um por mês, emitido de 01/01 até o fim do mês) |
| `relatorios/rgf/2026/` | RGF e RREO baixados do Siconfi (`SICONFI_RGF_..._QUADRIMESTRAL_n.xls`, `SICONFI_RREO_..._BIMESTRAL_n.xls`). Opcional: o robô (`robo/`) já busca os períodos novos pela API do Siconfi (`scripts/siconfi_api.py`) |

Para outro ano, crie as pastas equivalentes (`relatorios/2027/`, `relatorios/desp2027/`, `relatorios/rgf/2027/`).

Se a pasta `relatorios/` não existir, o portal é montado com os dados já extraídos em `dados/`.

## Estrutura

- `src/` – o portal (HTML, CSS e JavaScript); os dados entram compactados na montagem.
- `scripts/` – leitura dos relatórios (`extrair_*.py`, `ler_*.py`) e montagem (`montar.py`, `atualizar.sh`).
- `dados/` – dados extraídos, em JSON.
- `index.html` – o portal pronto.

## Rodar localmente

```bash
pip install openpyxl xlrd
bash scripts/atualizar.sh   # gera site/index.html
```
