// A page script for the form fixtures that show "Sending…" at once: a form marked data-sending posts its fields to its action
// address after data-delay milliseconds and shows its answer in the status region 150 ms after the answer arrives.
document.querySelectorAll('form[data-sending]').forEach(function (form) {
  form.addEventListener('submit', function (event) {
    event.preventDefault();
    var button = form.querySelector('button');
    var status = form.querySelector('[role=status]');
    var label = button.textContent;
    var data = new FormData(form);
    var show = function (text) { setTimeout(function () { status.textContent = text; button.textContent = label; }, 150); };
    button.textContent = 'Sending…';
    setTimeout(function () {
      fetch(form.getAttribute('action'), { method: 'POST', body: data }).then(function (r) {
        show(r.ok ? 'Thanks, we reply within one working day.' : 'Something went wrong. Please email us instead.');
      }, function () { show('Something went wrong. Please email us instead.'); });
    }, Number(form.getAttribute('data-delay') || 0));
  });
});
