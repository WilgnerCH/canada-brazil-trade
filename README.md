# canada-brazil-trade

Pipeline de dados + dashboard do comércio bilateral **Canadá – Brasil**, em um
**único repositório**, totalmente automatizado e **100% na nuvem** (não depende
de nenhuma máquina local). Substitui a antiga configuração espalhada em vários
repositórios.

- **Atualização:** mensal, automática, via GitHub Actions.
- **Armazenamento do dataset:** sem HuggingFace — o parquet acumulado vive como
  *asset* de uma GitHub Release. Isso usa apenas o `GITHUB_TOKEN` automático, ou
  seja, **nenhum secret e nenhuma conta externa**.
- **Publicação:** GitHub Pages, a partir da pasta `site/`.

---

## Como funciona (um job, em ordem)

O workflow `.github/workflows/update.yml` roda todo mês e executa:

1. **Recupera** o parquet acumulado da Release `data-store`.
2. **Extrai** da Statistics Canada só os meses que ainda faltam (incremental).
3. **Mescla** os dados novos no parquet (*merge*, nunca *overwrite*).
4. **Persiste** o parquet de volta na Release.
5. **Agrega** o parquet nos CSVs do dashboard (`site/data_csv/*.csv`).
6. **Commita** os CSVs atualizados.
7. **Publica** a pasta `site/` no GitHub Pages.

```
StatCan ──► extract.py ──► transform.py ──► [parquet na Release]
                                               │
                                               ▼
                                         aggregate.py ──► site/data_csv/*.csv
                                                               │
                                                               ▼
                                                         GitHub Pages
```

Por que o parquet não fica no git: ele é grande e muda todo mês. Guardá-lo na
Release mantém o repositório leve e o histórico limpo.

---

## Estrutura

```
.github/workflows/update.yml   Workflow mensal (a automação inteira)
pipeline/extract.py            Baixa da StatCan (incremental)
pipeline/transform.py          Mescla no parquet (merge + dedup por row_type)
analytics/aggregate.py         Parquet -> CSVs do dashboard
site/index.html                Dashboard (página de teste; trocar pelo real)
site/data_csv/                 CSVs que o dashboard lê
requirements.txt               Dependências Python
```

---

## Setup inicial (uma vez, dá pra fazer tudo pelo navegador)

1. **Crie o repositório** na sua conta e suba estes arquivos.
2. **Ative o GitHub Pages:** *Settings → Pages → Build and deployment → Source: **GitHub Actions***.
3. **Rode uma vez manualmente:** aba *Actions → update-trade-data → Run workflow*.
   - Com `DEMO=1` (padrão), o pipeline roda com dados sintéticos e você vê tudo
     verde de ponta a ponta, incluindo o Pages publicando.
4. Abra a URL do Pages (*Settings → Pages* mostra o link, algo como
   `https://SEU-USUARIO.github.io/canada-brazil-trade/`).

Pronto: a partir daqui, com a máquina desligada, o site se atualiza sozinho todo mês.

---

## Ligando a lógica real (saindo do modo DEMO)

Enquanto `DEMO=1`, nada de internet é acessado — é só para validar o encanamento.
Para colocar os dados reais:

1. **`pipeline/extract.py`** → preencha `baixar_real()` com a extração da StatCan
   do antigo `canada-trade-data` (URLs dos ZIPs, `CNAMES`, `hs_lookup`). Grave
   cada mês em `data_raw/<mes>.parquet` com a coluna `month` (YYYY-MM) e
   `row_type`.
2. **`analytics/aggregate.py`** → replique o `gerar_monthly()` para os demais
   CSVs (países, HS2, províncias, matriz Brasil), reaproveitando o `src/` do
   `canada-trade-kpi-lab`.
3. **`site/`** → troque a página de teste pelo seu dashboard real (o `index.html`
   + `data_csv/` do `canada-trade-kpi-lab`). **Mantenha os caminhos dos CSVs
   relativos** (`./data_csv/...`) para funcionar em qualquer conta.
4. No `update.yml`, troque **`DEMO: "1"` para `DEMO: "0"`**.

> Se você usa `=IMPORTDATA()` no Google Sheets, atualize as URLs para apontar
> aos CSVs deste repositório novo.

---

## Entrega para a FCBB (clonar na outra conta)

Este repositório é autocontido. Para a conta da FCBB assumir:

```bash
# Na conta/máquina da FCBB, com um repo novo e vazio criado em FCBB/canada-brazil-trade:
git clone --bare https://github.com/SEU-USUARIO/canada-brazil-trade.git
cd canada-brazil-trade.git
git push --mirror https://github.com/ORG-FCBB/canada-brazil-trade.git
```

Depois, na conta da FCBB: ative o Pages (passo 2 acima) e rode o workflow uma vez.
Como não há secret nenhum, não há nada a reconfigurar além do Pages.

---

## Rodar localmente (opcional)

```bash
pip install -r requirements.txt
DEMO=1 PARQUET_PATH=data/canada_trade_full.parquet python pipeline/extract.py
DEMO=1 PARQUET_PATH=data/canada_trade_full.parquet python pipeline/transform.py
PARQUET_PATH=data/canada_trade_full.parquet python analytics/aggregate.py
# Sirva a pasta site/ para ver o dashboard:
python -m http.server -d site 8000   # http://localhost:8000
```

---

## Licença

MIT — veja [LICENSE](LICENSE).
