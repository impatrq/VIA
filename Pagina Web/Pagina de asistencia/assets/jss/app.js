/* assets/js/app.js */

/* Inicializar EmailJS*/
emailjs.init('5o0oirlCIaC5KwqQq'); 

// Función de lectura
function leerTexto(texto) {
  const synth = window.speechSynthesis;
  if (synth.speaking) synth.cancel();
  const utter = new SpeechSynthesisUtterance(texto);
  utter.lang = 'es-ES';
  synth.speak(utter);
}

// Asignar eventos después del DOM
window.addEventListener('DOMContentLoaded', () => {
  // elementos
  const btnCompartir = document.getElementById('btn-compartir');
  const btnDonde = document.getElementById('btn-donde');
  const btnContinuarUsuario = document.getElementById('btn-continuar-usuario');
  const btnContinuarMate = document.getElementById('btn-continuar-mate');

  // leer texto al focus / hover para botones y labels
  document.querySelectorAll('button').forEach(btn => {
    btn.addEventListener('focus', () => leerTexto(btn.textContent));
    btn.addEventListener('mouseenter', () => leerTexto(btn.textContent));
  });
  document.querySelectorAll('label').forEach(lbl => {
    lbl.addEventListener('focus', () => leerTexto(lbl.textContent));
    lbl.addEventListener('mouseenter', () => leerTexto(lbl.textContent));
  });
  document.querySelectorAll('input').forEach(inp => {
    inp.addEventListener('focus', () => leerTexto(inp.placeholder));
  });

  // asignar acciones
  btnContinuarUsuario.addEventListener('click', guardarUsuario);
  btnContinuarMate.addEventListener('click', guardarMate);
  btnCompartir.addEventListener('click', compartirUbicacion);
  btnDonde.addEventListener('click', abrirUbicacion);
});

/* Variables globales (usuario y guía) */
let usuarioNombre = "";
let usuarioEmail = "";
let mateNombre = "";
let mateEmail = "";

function guardarUsuario() {
  const nombreInput = document.getElementById('usuario-nombre');
  const emailInput = document.getElementById('usuario-email');
  if (nombreInput.value.trim() === "") {
    alert("Por favor, escribe tu nombre.");
    return;
  }
  if (emailInput.value.trim() === "" || !emailInput.value.includes('@')) {
    alert("Por favor, escribe un correo electrónico válido.");
    return;
  }
  usuarioNombre = nombreInput.value.trim();
  usuarioEmail = emailInput.value.trim();
  document.getElementById('usuario-form').style.display = 'none';
  document.getElementById('mate-form').style.display = '';
}

function guardarMate() {
  const input = document.getElementById('mate');
  const emailInput = document.getElementById('mate-email');
  if (input.value.trim() === "") {
    alert("Por favor, escribe el nombre de tu guía o persona de confianza.");
    return;
  }
  if (emailInput.value.trim() === "" || !emailInput.value.includes('@')) {
    alert("Por favor, escribe un correo electrónico válido.");
    return;
  }
  mateNombre = input.value.trim();
  mateEmail = emailInput.value.trim();

  // EMAILJS: actualizar service/template si es necesario
  emailjs.send('service_granata', 'template_120f5nn', {
    to_name: mateNombre,
    to_email: mateEmail,
    from_name: usuarioNombre,
    from_email: usuarioEmail
  })
  .then(function(response) {
    alert('Correo de confirmación enviado a ' + mateEmail);
    document.getElementById('mate-form').style.display = 'none';
    document.getElementById('titulo').style.display = '';
    document.getElementById('botones').style.display = '';
  }, function(error) {
    alert('No se pudo enviar el correo de confirmación. Intenta nuevamente.');
  });
}

function compartirUbicacion() {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(function(position) {
      const lat = position.coords.latitude;
      const lon = position.coords.longitude;
      const url = `https://www.google.com/maps?q=${lat},${lon}`;
      emailjs.send('YOUR_SERVICE_ID', 'YOUR_TEMPLATE_ID', {
        to_name: mateNombre,
        to_email: mateEmail,
        from_name: usuarioNombre,
        from_email: usuarioEmail,
        location_url: url
      })
      .then(function(response) {
        alert('¡Ubicación enviada por correo a ' + mateEmail + '!');
      }, function(error) {
        alert('No se pudo enviar la ubicación por correo. Intenta nuevamente.');
      });
    }, function() {
      alert('No se pudo obtener la ubicación.');
    });
  } else {
    alert('La geolocalización no está soportada en este navegador.');
  }
}

function abrirUbicacion() {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(function(position) {
      const lat = position.coords.latitude;
      const lon = position.coords.longitude;
      const url = `https://www.google.com/maps?q=${lat},${lon}`;
      window.open(url, '_blank');
    }, function() {
      alert('No se pudo obtener la ubicación.');
    });
  } else {
    alert('La geolocalización no está soportada en este navegador.');
  }
}
