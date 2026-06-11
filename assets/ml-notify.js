'use strict';
/**
 * MyLab — Modale « prévenez-moi du retour en stock ».
 * Ouverte via un clic sur [data-ml-notify-open] (data-handle / data-variant / data-title).
 * POST vers window.MlNotify.webhook. Dégrade proprement si pas de webhook configuré.
 */
(function () {
  var modal = document.getElementById('ml-notify');
  if (!modal) return;
  var emailEl = document.getElementById('ml-notify-email');
  var handleEl = document.getElementById('ml-notify-handle');
  var variantEl = document.getElementById('ml-notify-variant');
  var prodEl = document.getElementById('ml-notify-prod');
  var msgEl = document.getElementById('ml-notify-msg');
  var form = document.getElementById('ml-notify-form');

  function open(data) {
    handleEl.value = data.handle || '';
    variantEl.value = data.variant || '';
    prodEl.textContent = data.title || '';
    msgEl.textContent = ''; msgEl.className = 'ml-notify__msg';
    modal.classList.add('is-open');
    modal.removeAttribute('inert');
    modal.setAttribute('aria-hidden', 'false');
    setTimeout(function () { emailEl.focus(); }, 50);
  }
  function close() {
    modal.classList.remove('is-open');
    modal.setAttribute('inert', '');
    modal.setAttribute('aria-hidden', 'true');
  }

  document.addEventListener('click', function (e) {
    var trigger = e.target.closest('[data-ml-notify-open]');
    if (trigger) {
      e.preventDefault();
      open({ handle: trigger.dataset.handle, variant: trigger.dataset.variant, title: trigger.dataset.title });
    }
    if (e.target.closest('[data-ml-notify-close]')) close();
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var webhook = (window.MlNotify && window.MlNotify.webhook) || '';
    if (!webhook) { msgEl.textContent = 'Indisponible pour le moment.'; msgEl.className = 'ml-notify__msg is-err'; return; }
    var btn = form.querySelector('.ml-notify__submit');
    btn.disabled = true;
    fetch(webhook, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: emailEl.value, handle: handleEl.value,
        variant_id: variantEl.value, product_title: prodEl.textContent
      })
    })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); })
    .then(function () {
      msgEl.textContent = 'C’est noté ! Vous serez prévenu(e) dès le retour en stock.';
      msgEl.className = 'ml-notify__msg is-ok';
      form.reset();
      setTimeout(close, 2200);
    })
    .catch(function () {
      msgEl.textContent = 'Erreur — réessayez.'; msgEl.className = 'ml-notify__msg is-err';
    })
    .finally(function () { btn.disabled = false; });
  });

  window.MlNotifyOpen = open;
})();
