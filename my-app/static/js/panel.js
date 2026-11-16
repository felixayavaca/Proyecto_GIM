(() => {
  const sidebar = document.getElementById('panelSidebar');
  const menu = document.getElementById('alternarMenu');
  const layout = sidebar.closest('.panel-layout');
  const navbar = menu.closest('.panel-navbar');
  const mobile = window.matchMedia('(max-width: 767.98px)');
  const preferencesKey = 'gim.sidebarCollapsed';
  let preference;
  try {
    preference = localStorage.getItem(preferencesKey);
  } catch {}

  function setSidebar(collapsed) {
    layout.classList.toggle('is-collapsed', collapsed);
    sidebar.inert = collapsed;
    menu.setAttribute('aria-expanded', String(!collapsed));
    menu.setAttribute('aria-label', collapsed ? 'Mostrar menú' : 'Ocultar menú');
  }

  function sizeSidebar() {
    layout.style.setProperty('--navbar-height', navbar.offsetHeight + 'px');
  }

  sizeSidebar();
  new ResizeObserver(sizeSidebar).observe(navbar);
  const restoreSidebar = () => setSidebar(preference == null ? mobile.matches : preference === 'true');
  restoreSidebar();
  mobile.addEventListener('change', restoreSidebar);
  menu.addEventListener('click', () => {
    const collapsed = !layout.classList.contains('is-collapsed');
    preference = String(collapsed);
    setSidebar(collapsed);
    try {
      localStorage.setItem(preferencesKey, preference);
    } catch {}
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && mobile.matches && !sidebar.inert && !document.querySelector('.modal.show')) {
      setSidebar(true);
      menu.focus();
    }
  });

  document.querySelectorAll('[data-panel-toast]').forEach(element => {
    if (window.bootstrap?.Toast) {
      bootstrap.Toast.getOrCreateInstance(element).show();
    } else {
      const close = () => element.remove();
      element.querySelector('button').addEventListener('click', close);
      window.setTimeout(close, 4000);
    }
  });

  function normalize(value) {
    return value.normalize('NFD').replace(/\p{M}/gu, '').toLocaleLowerCase('es').trim();
  }

  function filterValue(input) {
    const value = input.value.trim();
    return input.type === 'time' && value.length === 5 ? value + ':00' : value;
  }

  function matches(cell, rule) {
    if (rule.mode === 'time') return cell.dataset.filterTime === rule.value;
    const raw = cell.dataset.filterValue ?? cell.textContent.trim();
    if (rule.mode === 'min' || rule.mode === 'max' || rule.mode === 'number') {
      if (!raw || !Number.isFinite(Number(raw))) return false;
      if (rule.mode === 'min') return Number(raw) >= Number(rule.value);
      if (rule.mode === 'max') return Number(raw) <= Number(rule.value);
      return Number(raw) === Number(rule.value);
    }
    if (rule.mode === 'exact') return raw === rule.value;
    return normalize(raw).includes(rule.value);
  }

  const tables = Array.from(document.querySelectorAll('table')).flatMap(table => {
    const header = table.tHead?.rows[1];
    const controls = Array.from(header?.querySelectorAll('input[name], select[name]') ?? []);
    if (!controls.length || !table.tBodies.length) return [];
    const form = controls[0].form;
    const clear = header.querySelector('[data-clear-filters]');
    return [{table, controls, form, clear, empty: null}];
  });
  const filterForms = new Set(tables.map(({form}) => form));
  const exportLinks = document.querySelectorAll('[data-export-filters]');
  const originalUrl = new URL(location.href);
  const needsFullList = Array.from(originalUrl.searchParams.keys()).some(key => key !== 'tab');
  let listLoadFailed = false;

  function filterParameters() {
    const params = new URLSearchParams();
    for (const {controls} of tables) {
      for (const input of controls) {
        const value = filterValue(input);
        if (value && input.validity.valid) params.set(input.name, value);
      }
    }
    return params;
  }

  function syncExports() {
    const params = filterParameters();
    for (const link of exportLinks) {
      const url = new URL(link.href);
      url.search = params;
      link.href = url.href;
    }
  }

  function applyFilters(config) {
    const {table, controls} = config;
    const rows = Array.from(table.tBodies[0].rows).filter(row => !row.hasAttribute('data-filter-empty'));
    const rules = controls.filter(input => filterValue(input) && input.validity.valid).map(input => {
      const mode = input.dataset.filterMode ||
        (input.type === 'number' ? 'number' : input.matches('select, [type="date"], [type="time"]') ? 'exact' : 'text');
      const value = filterValue(input);
      return {column: input.closest('td, th').cellIndex, mode, value: mode === 'text' ? normalize(value) : value};
    });
    let visible = 0;
    for (const row of rows) {
      if (row.cells.length === 1 && row.cells[0].colSpan > 1) continue;
      const match = rules.every(rule => row.cells[rule.column] && matches(row.cells[rule.column], rule));
      row.hidden = !match;
      if (match) visible++;
    }
    if (!config.empty) {
      config.empty = table.tBodies[0].insertRow();
      config.empty.setAttribute('data-filter-empty', '');
      const cell = config.empty.insertCell();
      cell.colSpan = table.tHead.rows[0].cells.length;
      cell.className = 'text-center text-secondary';
      cell.setAttribute('role', 'status');
      cell.textContent = 'No se encontraron resultados.';
    }
    const placeholder = rows.find(row => row.cells.length === 1 && row.cells[0].colSpan > 1);
    config.empty.hidden = visible > 0 || Boolean(placeholder);
  }

  for (const config of tables) {
    for (const control of config.controls) {
      for (const event of ['input', 'change']) {
        control.addEventListener(event, () => {
          applyFilters(config);
          syncExports();
        });
      }
    }
    config.clear?.addEventListener('click', event => {
      if (listLoadFailed) return;
      event.preventDefault();
      for (const input of config.controls) input.value = input.tagName === 'SELECT' ? input.options[0].value : '';
      applyFilters(config);
      syncExports();
    });
    applyFilters(config);
  }
  if (tables.length) {
    document.documentElement.classList.add('panel-filters-ready');
    syncExports();
  }

  // A bookmark or a POST redirect may have rendered only the matching rows.
  if (tables.length && needsFullList) {
    fetch(originalUrl.pathname, {headers: {Accept: 'text/html'}}).then(async response => {
      if (!response.ok || response.redirected) throw new Error('No se pudo cargar la tabla completa.');
      const page = new DOMParser().parseFromString(await response.text(), 'text/html');
      const bodies = tables.map(({form}) => {
        const control = Array.from(page.querySelectorAll('thead input[form], thead select[form]'))
          .find(element => element.getAttribute('form') === form.id);
        return control?.closest('table').tBodies[0];
      });
      if (bodies.some(body => !body)) throw new Error('Faltan tablas en la respuesta.');
      tables.forEach((config, index) => {
        config.table.tBodies[0].replaceChildren(...bodies[index].rows);
        config.empty = null;
        applyFilters(config);
      });
    }).catch(() => {
      listLoadFailed = true;
      document.documentElement.classList.remove('panel-filters-ready');
    });
  }

  document.addEventListener('submit', event => {
    const form = event.target;
    if (filterForms.has(form) && !listLoadFailed) {
      event.preventDefault();
      return;
    }
    if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) {
      event.preventDefault();
      return;
    }
    const action = new URL(form.action);
    if (tables.length && form.method === 'post' && action.origin === location.origin
        && action.pathname.startsWith(originalUrl.pathname + '/')) {
      action.search = filterParameters();
      form.action = action.href;
    }
  });
})();
