(() => {
  const grasa = document.getElementById('porcentaje_grasa');
  if (!grasa) return;
  const socio = document.getElementById('valoracionSocio');
  const fecha = document.getElementById('valoracionFecha');
  const peso = document.getElementById('peso_kg');
  const estatura = document.getElementById('estatura_cm');
  const modo = document.getElementById('grasaModo');
  const ayuda = document.getElementById('grasaAyuda');
  let manual = false;
  grasa.setAttribute('aria-describedby', 'grasaAyuda');
  function calcular() {
    if (manual) return;
    const opcion = socio.selectedOptions[0];
    const nacimiento = opcion?.dataset.nacimiento;
    const genero = opcion?.dataset.genero;
    const hoy = new Intl.DateTimeFormat('en-CA', {timeZone: 'America/Guayaquil'}).format(new Date());
    const referencia = fecha.value || hoy;
    const [anio, mes, dia] = referencia.split('-').map(Number);
    const [nAnio, nMes, nDia] = (nacimiento || '').split('-').map(Number);
    const edad = anio - nAnio - (mes < nMes || (mes === nMes && dia < nDia) ? 1 : 0);
    const kg = Number(peso.value);
    const cm = Number(estatura.value);
    let mensaje = 'Calculado por IMC/Edad/Género · Editable';
    let valor = '';
    if (!nacimiento || !['M', 'F'].includes(genero) || edad < 18) {
      mensaje = 'Estimación no disponible sin fecha de nacimiento, para menores de 18 años o género Otro. Ingresa una medición manual.';
    } else if (kg >= 25 && kg <= 300 && cm >= 100 && cm <= 230) {
      const imc = kg / ((cm / 100) ** 2);
      const estimada = Math.round((1.2 * imc + .23 * edad - 10.8 * (genero === 'M' ? 1 : 0) - 5.4) * 10) / 10;
      if (estimada >= 3 && estimada <= 60) valor = estimada.toFixed(1);
      else mensaje = 'Estimación fuera de 3–60 %. Ingresa una medición manual.';
    }
    if (grasa.value !== valor) grasa.value = valor;
    ayuda.textContent = mensaje;
    grasa.dispatchEvent(new Event('change', {bubbles: true}));
  }
  grasa.addEventListener('input', () => {
    manual = grasa.value !== '';
    modo.value = manual ? 'manual' : 'auto';
    ayuda.textContent = manual ? 'Medición manual · Se conservará al cambiar peso o estatura' : 'Calculado por IMC/Edad/Género · Editable';
  });
  for (const campo of [peso, estatura, fecha]) {
    campo.addEventListener('input', calcular);
    campo.addEventListener('change', calcular);
  }
  socio.addEventListener('change', () => { manual = false; modo.value = 'auto'; calcular(); });
  calcular();
})();
