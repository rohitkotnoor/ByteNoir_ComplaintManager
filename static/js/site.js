(() => {
  const toggle = document.querySelector('.nav-toggle');
  const nav = document.querySelector('#primary-nav');
  if (!toggle || !nav) return;
  toggle.addEventListener('click', () => {
    const expanded = toggle.getAttribute('aria-expanded') === 'true';
    toggle.setAttribute('aria-expanded', String(!expanded));
    nav.classList.toggle('nav-open', !expanded);
  });
})();

(() => {
  const eyeIcon = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M2.5 12s3.4-7 9.5-7 9.5 7 9.5 7-3.4 7-9.5 7-9.5-7-9.5-7Z"/><circle cx="12" cy="12" r="3"/></svg>';
  const eyeOffIcon = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M3 3 21 21M10.6 10.6a2 2 0 0 0 2.8 2.8M9.9 5.2A10.7 10.7 0 0 1 12 5c6.1 0 9.5 7 9.5 7a13.8 13.8 0 0 1-3.1 4.1M6.6 6.6C4 8.2 2.5 12 2.5 12s3.4 7 9.5 7a10 10 0 0 0 4.2-.9"/></svg>';

  document.querySelectorAll('input[type="password"]').forEach((input) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'password-field';
    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(input);

    const button = document.createElement('button');
    button.className = 'password-toggle';
    button.type = 'button';
    button.innerHTML = eyeIcon;
    button.setAttribute('aria-label', 'Show password');
    button.setAttribute('aria-controls', input.id);
    button.setAttribute('aria-pressed', 'false');
    wrapper.appendChild(button);

    button.addEventListener('click', () => {
      const isVisible = input.type === 'text';
      input.type = isVisible ? 'password' : 'text';
      button.innerHTML = isVisible ? eyeIcon : eyeOffIcon;
      button.setAttribute('aria-label', isVisible ? 'Show password' : 'Hide password');
      button.setAttribute('aria-pressed', String(!isVisible));
    });
  });
})();
