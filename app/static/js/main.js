(function () {
  var form = document.querySelector("[data-form-contato]");
  if (!form || !window.fetch) return;

  var aviso = form.querySelector("[data-aviso]");
  var botao = form.querySelector("button[type=submit]");

  function mostrar(ok, texto) {
    aviso.hidden = false;
    aviso.textContent = texto;
    aviso.className = "form__aviso " + (ok ? "form__aviso--ok" : "form__aviso--erro");
    aviso.setAttribute("role", ok ? "status" : "alert");
  }

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    form.querySelectorAll(".form__aviso:not([data-aviso])").forEach(function (el) { el.remove(); });

    if (!form.checkValidity()) {
      mostrar(false, "Preencha nome, um e-mail válido e a mensagem (mínimo de 10 caracteres).");
      return;
    }

    botao.disabled = true;
    botao.textContent = "Enviando...";

    fetch(form.action, {
      method: "POST",
      headers: { "Accept": "application/json" },
      body: new FormData(form)
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        mostrar(d.ok, d.mensagem);
        if (d.ok) form.reset();
      })
      .catch(function () {
        mostrar(false, "Não foi possível enviar agora. Tente novamente em instantes.");
      })
      .finally(function () {
        botao.disabled = false;
        botao.textContent = "Enviar mensagem";
      });
  });
})();
