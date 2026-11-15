# JRF Ferramentas — Site

Landing page da JRF Ferramentas, loja de ferramentas automotivas no Mercado Livre. Apresenta a empresa, leva o cliente para a loja no ML, traz FAQ e política de garantia, e tem um formulário de contato que envia as mensagens para um canal do Discord.

Publicado em https://jrf.rillis.com.br.

## Estrutura

```
app/
├── main.py          rotas (/, /garantia, /contato, /health) e envio ao Discord
├── templates/       páginas (Jinja2)
└── static/          CSS, JS e favicon
tests/               testes (pytest)
```

Os dados da empresa (CNPJ, e-mail, link da loja) ficam no dicionário `SITE`, no início de `app/main.py`.

## Configuração

```bash
cp .env.example .env   # e preencha
```

| Variável | O que é |
|---|---|
| `DISCORD_WEBHOOK_URL` | Webhook do canal do Discord que recebe as mensagens do formulário |

Sem o webhook o site funciona normalmente, mas o formulário responde que não foi possível enviar.

## Como rodar

```bash
docker compose up -d --build
```

O site fica em `http://<host>:51006`. Depois de alterar qualquer arquivo, rode o mesmo comando para reconstruir a imagem.

Para rodar fora do Docker:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/flask --app app.main run --port 8000
```

## Deploy

O container `jrf-site` escuta na porta `51006` do host. Para testes após alterações, use o endereço local (`http://localhost:51006`), pois o Cloudflare pode servir conteúdo em cache.

## Testes

```bash
.venv/bin/python -m pytest -q
```

Verificação rápida do container:

```bash
curl -s http://localhost:51006/health
```
