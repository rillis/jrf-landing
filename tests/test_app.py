import time

import pytest

from app import main


@pytest.fixture(autouse=True)
def _limpar_estado(monkeypatch):
    main._envios_ip.clear()
    main._envios_global.clear()
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.example/webhook")
    yield


@pytest.fixture
def client():
    main.app.config["TESTING"] = True
    return main.app.test_client()


class FakeResp:
    def __init__(self, status):
        self.status_code = status


@pytest.fixture
def discord(monkeypatch):
    chamadas = []

    def fake_post(url, json, timeout):
        chamadas.append(json)
        return FakeResp(204)

    monkeypatch.setattr(main.requests, "post", fake_post)
    return chamadas


def form(**extra):
    dados = {
        "nome": "Fulano",
        "email": "fulano@example.com",
        "telefone": "",
        "assunto": "Garantia",
        "mensagem": "Quero saber sobre a garantia do produto.",
        "website": "",
        "t": str(int(time.time()) - 10),
    }
    dados.update(extra)
    return dados


JSON = {"Accept": "application/json"}


def test_paginas(client):
    for rota in ("/", "/garantia", "/en"):
        r = client.get(rota)
        assert r.status_code == 200
        assert "66.062.242/0001-18" in r.text
        assert "mercadolivre.com.br/pagina/jrferramentas" in r.text
    assert client.get("/nao-existe").status_code == 404
    assert client.get("/health").json == {"ok": True}


def test_contato_envia_ao_discord(client, discord):
    r = client.post("/contato", data=form(), headers=JSON)
    assert r.status_code == 200 and r.json["ok"]
    assert len(discord) == 1
    embed = discord[0]["embeds"][0]
    assert embed["description"] == "Quero saber sobre a garantia do produto."
    assert discord[0]["allowed_mentions"] == {"parse": []}


def test_contato_sem_js_redireciona(client, discord):
    r = client.post("/contato", data=form())
    assert r.status_code == 302
    assert "contato=enviado" in r.headers["Location"]


@pytest.mark.parametrize("campos", [
    {"nome": ""},
    {"email": "invalido"},
    {"mensagem": "curta"},
])
def test_contato_valida_campos(client, discord, campos):
    r = client.post("/contato", data=form(**campos), headers=JSON)
    assert r.status_code == 400 and not r.json["ok"]
    assert discord == []


def test_robo_nao_envia(client, discord):
    assert client.post("/contato", data=form(website="spam"), headers=JSON).json["ok"]
    assert client.post("/contato", data=form(t=str(int(time.time()))), headers=JSON).json["ok"]
    assert discord == []


def test_limite_por_ip(client, discord):
    for _ in range(main.POR_IP[0]):
        assert client.post("/contato", data=form(), headers=JSON).status_code == 200
    assert client.post("/contato", data=form(), headers=JSON).status_code == 429
    assert len(discord) == main.POR_IP[0]


def test_sem_webhook(client, monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "")
    r = client.post("/contato", data=form(), headers=JSON)
    assert r.status_code == 503 and not r.json["ok"]


def test_assunto_fora_da_lista(client, discord):
    client.post("/contato", data=form(assunto="<script>"), headers=JSON)
    campos = {c["name"]: c["value"] for c in discord[0]["embeds"][0]["fields"]}
    assert campos["Assunto"] == main.ASSUNTOS[-1]


def test_pagina_em_ingles(client):
    r = client.get("/en")
    assert '<html lang="en">' in r.text
    assert 'hreflang="pt-BR"' in r.text
    assert 'href="/en"' in client.get("/").text
