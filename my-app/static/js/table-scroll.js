document.querySelectorAll('.table-responsive').forEach(container => {
  const table = container.querySelector('table');
  if (!table) return;

  const group = document.createElement('div');
  group.className = 'panel-table-group';
  const upper = document.createElement('div');
  upper.className = 'panel-table-scroll';
  upper.setAttribute('role', 'region');
  upper.setAttribute('aria-label', 'Desplazamiento horizontal de la tabla');
  upper.tabIndex = 0;
  upper.hidden = true;
  const track = document.createElement('div');
  track.setAttribute('aria-hidden', 'true');
  upper.append(track);
  container.before(group);
  group.append(upper, container);

  function resize() {
    upper.hidden = container.scrollWidth <= container.clientWidth;
    track.style.width = container.scrollWidth + 'px';
    upper.scrollLeft = container.scrollLeft;
  }

  upper.addEventListener('scroll', () => {
    if (!upper.hidden && container.scrollLeft !== upper.scrollLeft) {
      container.scrollLeft = upper.scrollLeft;
    }
  }, {passive: true});
  container.addEventListener('scroll', () => {
    if (!upper.hidden && upper.scrollLeft !== container.scrollLeft) {
      upper.scrollLeft = container.scrollLeft;
    }
  }, {passive: true});

  const observer = new ResizeObserver(resize);
  observer.observe(table);
  observer.observe(container);
  resize();
});
