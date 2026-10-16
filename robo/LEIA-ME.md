# Robô de atualização do portal

Emite os relatórios no sistema contábil, gera os dados do portal, confere com o balancete simplificado e
envia ao GitHub. O site é republicado automaticamente.

## Preparação (uma vez)

1. Instale o **Python 3.10+**, o **Git** e o **Google Chrome**.
2. Clone o repositório: `git clone https://github.com/caio-yamamoto/portal-fiscal-maringa.git`
   (o Git pede o login do GitHub na primeira vez e guarda a credencial).
3. Instale as bibliotecas: `pip install selenium openpyxl`
4. Copie o seu `automacao_relatorios_bi.py` para a pasta `robo/` (ele não vai para o GitHub).
5. Coloque o histórico de relatórios em `relatorios_locais/`, na raiz do repositório:

   ```
   relatorios_locais/
     2025/  2026/      receita realizada por fonte (um por mês) e a Previsão Orçamentária do ano
     quadros/          Anexo 2 – quadro da receita por natureza (nomes das naturezas)
     desp2025/ desp2026/  balancetes da despesa analíticos (01/01 até o fim de cada mês) e simplificados
   ```

   Essa pasta não vai para o GitHub (está no `.gitignore`).

## Uso

```
cd portal-fiscal-maringa\robo
python robo_portal.py
```

- O Chrome abre na tela do sistema. Se pedir login, entre normalmente (usuário, senha e "Confirme que é humano").
- O robô emite, para o mês vigente e o anterior: receita realizada por fonte, balancete analítico
  (acumulado desde 01/01) e balancete simplificado.
- Em seguida gera os dados, confere com o simplificado e envia ao GitHub. Se a conferência apontar diferença,
  nada é enviado e a mensagem explica o que fazer.

Outros comandos:

- `python robo_portal.py --sem-envio` – emite e gera, sem enviar.
- `python atualizar_portal.py` – só gera, confere e envia (sem abrir o sistema), útil quando os relatórios já foram baixados.

## Agendar no Windows

Agendador de Tarefas → Criar Tarefa Básica → diariamente, por exemplo às 7h, em dias úteis →
Ação: `python`, argumentos `robo_portal.py`, iniciar em: a pasta `robo`. A tarefa precisa rodar com o usuário
conectado, porque o Chrome abre na tela (e o login pode ser pedido).
