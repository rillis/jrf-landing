import logging
import os
import re
import threading
import time
from collections import defaultdict, deque

import requests
from flask import Flask, jsonify, redirect, render_template, request, url_for

SITE = {
    "nome": "JRF Ferramentas",
    "cnpj": "66.062.242/0001-18",
    "cidade": "São Paulo - SP",
    "email": "rillismlivre@gmail.com",
    "loja_ml": "https://www.mercadolivre.com.br/pagina/jrferramentas",
    "url": "https://jrf.rillis.com.br",
}

ASSUNTOS = [
    "Dúvida sobre um produto",
    "Garantia",
    "Troca ou devolução",
    "Outro assunto",
]

LIMITES = {"nome": 100, "email": 254, "telefone": 30, "mensagem": 2000}
TEMPO_MINIMO = 3            # segundos entre abrir a página e enviar
POR_IP = (3, 600)           # 3 envios a cada 10 min por IP
GLOBAL = (30, 3600)         # 30 envios por hora no total

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

log = logging.getLogger("jrf-site")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024
ASSET_VERSION = str(int(time.time()))

_lock = threading.Lock()
_envios_ip: dict[str, deque] = defaultdict(deque)
_envios_global: deque = deque()


def _dentro_do_limite(fila: deque, maximo: int, janela: int, agora: float) -> bool:
    while fila and agora - fila[0] > janela:
        fila.popleft()
    return len(fila) < maximo


def _registrar_envio(ip: str) -> bool:
    agora = time.time()
    with _lock:
        fila_ip = _envios_ip[ip]
        if not _dentro_do_limite(fila_ip, *POR_IP, agora):
            return False
        if not _dentro_do_limite(_envios_global, *GLOBAL, agora):
            return False
        fila_ip.append(agora)
        _envios_global.append(agora)
        return True


def _ip_cliente() -> str:
    return request.headers.get("CF-Connecting-IP") or request.remote_addr or "?"


def _limpar(valor: str, limite: int) -> str:
    valor = (valor or "").replace("\r\n", "\n").strip()
    valor = "".join(c for c in valor if c == "\n" or c.isprintable())
    return valor[:limite]


def _enviar_discord(dados: dict) -> bool:
    webhook = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook:
        log.error("DISCORD_WEBHOOK_URL não configurada")
        return False
    campos = [
        {"name": "Nome", "value": dados["nome"], "inline": True},
        {"name": "E-mail", "value": dados["email"], "inline": True},
        {"name": "Assunto", "value": dados["assunto"], "inline": False},
    ]
    if dados["telefone"]:
        campos.insert(2, {"name": "Telefone", "value": dados["telefone"], "inline": True})
    payload = {
        "username": "Site JRF",
        "allowed_mentions": {"parse": []},
        "embeds": [{
            "title": "Novo contato pelo site",
            "description": dados["mensagem"],
            "color": 0xE11D2A,
            "fields": campos,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }],
    }
    try:
        r = requests.post(webhook, json=payload, timeout=10)
    except requests.RequestException as e:
        log.error("falha ao enviar ao Discord: %s", type(e).__name__)
        return False
    if r.status_code >= 300:
        log.error("Discord respondeu %s", r.status_code)
        return False
    return True


def _resposta(ok: bool, mensagem: str, status: int):
    if request.accept_mimetypes.best == "application/json" or request.is_json:
        return jsonify(ok=ok, mensagem=mensagem), status
    return redirect(url_for("index", contato="enviado" if ok else "erro") + "#contato")


@app.context_processor
def _contexto():
    return {"site": SITE, "assuntos": ASSUNTOS, "v": ASSET_VERSION, "ano": time.localtime().tm_year}


@app.after_request
def _cabecalhos(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; style-src 'self' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; img-src 'self' data:; "
        "form-action 'self'; frame-ancestors 'none'; base-uri 'self'",
    )
    return resp


@app.get("/")
def index():
    return render_template("index.html", agora=int(time.time()), status=request.args.get("contato"))


@app.get("/garantia")
def garantia():
    return render_template("garantia.html")


@app.get("/en")
def en():
    return render_template("en.html")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/contato")
def contato():
    f = request.form if not request.is_json else (request.get_json(silent=True) or {})

    # Campo invisível e tempo mínimo: robôs recebem "sucesso" sem nada ser enviado.
    try:
        aberto_em = int(f.get("t", "0"))
    except (TypeError, ValueError):
        aberto_em = 0
    if f.get("website") or time.time() - aberto_em < TEMPO_MINIMO:
        return _resposta(True, "Mensagem enviada! Responderemos pelo e-mail informado.", 200)

    dados = {k: _limpar(f.get(k, ""), lim) for k, lim in LIMITES.items()}
    dados["assunto"] = f.get("assunto") if f.get("assunto") in ASSUNTOS else ASSUNTOS[-1]

    if not dados["nome"] or not dados["mensagem"]:
        return _resposta(False, "Preencha seu nome e a mensagem.", 400)
    if not EMAIL_RE.match(dados["email"]):
        return _resposta(False, "Informe um e-mail válido para podermos responder.", 400)
    if len(dados["mensagem"]) < 10:
        return _resposta(False, "Conte um pouco mais na mensagem.", 400)

    if not _registrar_envio(_ip_cliente()):
        return _resposta(False, "Muitas mensagens em pouco tempo. Tente novamente mais tarde.", 429)

    if not _enviar_discord(dados):
        return _resposta(False, f"Não foi possível enviar agora. Escreva para {SITE['email']}.", 503)

    return _resposta(True, "Mensagem enviada! Responderemos pelo e-mail informado.", 200)


@app.errorhandler(404)
def nao_encontrado(_):
    return render_template("404.html"), 404


@app.errorhandler(413)
def grande_demais(_):
    return _resposta(False, "Mensagem grande demais.", 413)
