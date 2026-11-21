(() => {
  const letters = /[^A-Za-zÁÉÍÓÚáéíóúÑñÜü\s]/g;
  const personNames = new Set(['nombre', 'apellido', 'socio', 'instructor', 'referente', 'pago_socio']);
  const examples = {
    cedula: 'Ej: 0102030405', nombre: 'Ej: Juan Carlos', apellido: 'Ej: Pérez Gómez',
    telefono: 'Ej: 0991234567', email: 'Ej: juan.perez@correo.com',
    direccion: 'Ej: Av. Solano y Remigio Crespo', contacto_emergencia: 'Ej: María Pérez - 0987654321',
    especialidad: 'Ej: Entrenamiento funcional', precio: 'Ej: 45.00', precio_pagado: 'Ej: 45.00',
    precio_max: 'Ej: 45', duracion_dias: 'Ej: 30', duracion: 'Ej: 30',
    peso_kg: 'Ej: 72.5', estatura_cm: 'Ej: 175', porcentaje_grasa: 'Ej: 18.5',
    grupo_muscular: 'Ej: Pecho y Tríceps', ejercicios_detalle: 'Ej: Press banca 4x12, Aperturas 3x15',
    observaciones: 'Ej: Mejorar movilidad de hombros', antiguedad_min: 'Ej: 30', socios_min: 'Ej: 5',
    socio: 'Ej: Juan Carlos', instructor: 'Ej: María Pérez', referente: 'Ej: Ana Gómez',
    pago_socio: 'Ej: Juan Carlos', contacto: 'Ej: 0991234567 o juan@correo.com',
    q: 'Ej: Plan Trimestral Pro'
  };
  const fields = document.querySelectorAll('input:not([type="hidden"]), textarea, select');
  const isFilter = field => Boolean(field.closest('thead'));
  const isPersonName = field => personNames.has(field.name)
    && (isFilter(field) || (['nombre', 'apellido'].includes(field.name)
      && /\/(socios|instructores)\//.test(new URL(field.form.action, location.href).pathname)));
  const numeric = field => field.type === 'number' || field.dataset.numeric === 'true';

  function sanitize(field) {
    if (field.tagName !== 'INPUT' && field.tagName !== 'TEXTAREA') return;
    if (['cedula', 'telefono'].includes(field.name)) {
      field.value = field.value.replace(/\D/g, '').slice(0, 10);
    } else if (isPersonName(field)) {
      field.value = field.value.replace(letters, '');
    } else if (numeric(field)) {
      if (isFilter(field) || field.step === '1' || !field.step) {
        field.value = field.value.replace(/\D/g, '');
      } else {
        const [whole, ...fraction] = field.value.replace(/[^\d.]/g, '').split('.');
        field.value = whole + (fraction.length ? '.' + fraction.join('') : '');
      }
    }
  }

  function cedulaValida(value) {
    const province = Number(value.slice(0, 2));
    if (province !== 30 && (province < 1 || province > 24)) return false;
    const total = [...value.slice(0, 9)].reduce((sum, digit, index) => {
      const product = Number(digit) * (index % 2 === 0 ? 2 : 1);
      return sum + (product > 9 ? product - 9 : product);
    }, 0);
    return (10 - total % 10) % 10 === Number(value[9]);
  }

  function message(field) {
    const value = field.value.trim();
    if (!value && !field.required && !field.validity.badInput) return '';
    if (field.name === 'cedula') {
      if (!/^\d{10}$/.test(value)) return 'La cédula debe tener 10 dígitos';
      if (!cedulaValida(value)) return 'Cédula ecuatoriana no válida';
    } else if (field.name === 'telefono' && !/^09\d{8}$/.test(value)) {
      return 'Debe iniciar con 09 y tener 10 dígitos';
    } else if (isPersonName(field) && !/^[A-Za-zÁÉÍÓÚáéíóúÑñÜü\s]{2,60}$/.test(value)) {
      return 'Solo se permiten letras (mínimo 2 caracteres)';
    } else if (field.type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
      return 'Ingresa un correo válido, ej. usuario@dominio.com';
    }
    if (field.validity.valueMissing) return 'Completa este campo';
    if (field.validity.badInput) return 'Ingresa un número válido';
    if (field.validity.rangeUnderflow || field.validity.rangeOverflow) {
      return 'Ingresa un valor entre ' + (field.min || '0') + ' y ' + (field.max || 'el máximo permitido');
    }
    if (field.validity.stepMismatch) return 'Usa el número de decimales permitido';
    if (field.validity.patternMismatch || field.validity.typeMismatch || field.validity.tooLong) {
      return 'Revisa el formato y la longitud del campo';
    }
    return '';
  }

  let sequence = 0;
  function validate(field) {
    if (field.disabled || !field.willValidate || isFilter(field)) return true;
    field.setCustomValidity('');
    const error = message(field);
    field.setCustomValidity(error);
    field.classList.toggle('is-invalid', Boolean(error));
    field.classList.toggle('is-valid', !error && Boolean(field.value.trim()));
    field.setAttribute('aria-invalid', String(Boolean(error)));
    let feedback = document.getElementById(field.dataset.feedbackId);
    if (!feedback) {
      feedback = document.createElement('div');
      feedback.id = 'gatutofit-feedback-' + (++sequence);
      feedback.className = 'invalid-feedback';
      field.after(feedback);
      field.dataset.feedbackId = feedback.id;
      field.setAttribute('aria-describedby', [field.getAttribute('aria-describedby'), feedback.id].filter(Boolean).join(' '));
    }
    feedback.textContent = error;
    feedback.style.display = error ? 'block' : '';
    return !error;
  }

  for (const field of fields) {
    if (!field.form || ['button', 'submit', 'checkbox', 'radio'].includes(field.type)) continue;
    if (field.matches('input, textarea') && !field.matches('[type="date"], [type="time"], [type="datetime-local"]')) {
      const planName = field.name === 'nombre' && !isPersonName(field);
      field.placeholder = planName ? 'Ej: Plan Trimestral Pro' : examples[field.name] || field.placeholder || 'Ej: Escribe un valor';
    }
    if (['cedula', 'telefono'].includes(field.name)) {
      field.maxLength = 10;
      field.inputMode = 'numeric';
    }
    if (isFilter(field) && field.type === 'number') {
      field.type = 'text';
      field.dataset.numeric = 'true';
      field.inputMode = 'numeric';
      field.pattern = '[0-9]*';
    }
    if (!isFilter(field) && field.name === 'peso_kg') { field.min = '25'; field.max = '300'; }
    if (!isFilter(field) && field.name === 'estatura_cm') { field.min = '100'; field.max = '250'; }
    field.addEventListener('blur', () => validate(field));
    field.addEventListener('change', () => validate(field));
    if (numeric(field)) {
      field.addEventListener('keydown', event => {
        if (!event.ctrlKey && !event.metaKey && ['e', 'E', '+', '-'].includes(event.key)) event.preventDefault();
      });
      field.addEventListener('paste', event => {
        const text = event.clipboardData.getData('text');
        if (!/^\d*(\.\d*)?$/.test(text)) event.preventDefault();
      });
    }
  }
  // Capture runs before the table's live filtering listeners.
  document.addEventListener('input', event => {
    if (!event.target.matches('input, textarea')) return;
    sanitize(event.target);
    validate(event.target);
  }, true);

  for (const form of document.forms) {
    if (form.method.toLowerCase() !== 'post') continue;
    form.noValidate = true;
    form.addEventListener('submit', event => {
      let firstInvalid;
      for (const field of form.elements) {
        if (field.matches('input, textarea, select') && !validate(field) && !firstInvalid) firstInvalid = field;
      }
      if (firstInvalid) {
        event.preventDefault();
        event.stopImmediatePropagation();
        firstInvalid.focus();
      }
    });
  }
  document.addEventListener('show.bs.modal', event => {
    event.target.querySelectorAll('input, textarea, select').forEach(field => {
      field.setCustomValidity('');
      field.classList.remove('is-valid', 'is-invalid');
      field.removeAttribute('aria-invalid');
      const feedback = document.getElementById(field.dataset.feedbackId);
      if (feedback) { feedback.textContent = ''; feedback.style.display = ''; }
    });
  });
})();
