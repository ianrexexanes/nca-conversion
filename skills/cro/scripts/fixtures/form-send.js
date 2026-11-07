// A page script for the form fixtures: a form marked data-js sends its fields by fetch and shows the answer in its status region.
document.querySelectorAll('form[data-js]').forEach(function (form) {
  form.addEventListener('submit', function (event) {
    event.preventDefault();
    var status = form.querySelector('[role=status]');
    var data = new FormData(form);
    var options = form.hasAttribute('data-json')
      ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(Object.fromEntries(data)) }
      : { method: 'POST', body: data };
    var send = function () { return fetch(form.getAttribute('data-to') || form.getAttribute('action'), options); };
    send().then(function (r) {
      status.textContent = r.ok ? 'Thanks, we reply within one working day.' : 'Something went wrong. Please email us instead.';
    }, function () { status.textContent = 'Something went wrong. Please email us instead.'; });
    if (form.hasAttribute('data-twice')) { send().then(function () {}, function () {}); }
  });
});
