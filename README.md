# JRF — Site

Site institucional da empresa JRF, servido por um container Nginx.

## Estrutura

- `site/` — arquivos estáticos do site (HTML, CSS, imagens)
- `Dockerfile` — imagem baseada em `nginx:alpine` que copia `site/`
- `docker-compose.yml` — serviço `jrf-site`

## Configuração

Nenhuma variável de ambiente é necessária por enquanto. A porta exposta no host é a `51006` (definida em `docker-compose.yml`).

## Como rodar

```bash
docker compose up -d --build
```

O site fica disponível em `http://<host>:51006`.

## Deploy

Publicado em https://jrf.rillis.com.br via Cloudflare Tunnel, apontando para a porta `51006`. Para testes após alterações, use o endereço local, pois o Cloudflare pode servir conteúdo em cache.

## Atualizar o conteúdo

Edite os arquivos em `site/` e reconstrua a imagem:

```bash
docker compose up -d --build
```

## Testes

```bash
curl -I http://localhost:51006
```

Deve retornar `HTTP/1.1 200 OK`.
