// Carrusel tipo Netflix con autoplay continuo en loop y más pancartas

document.addEventListener('DOMContentLoaded', function() {
    // Carrusel Netflix: movimiento automático y continuo en loop
    const track = document.querySelector('#glideCarrusel .glide__track');
    const slidesContainer = document.querySelector('.glide__slides');
    let slides = Array.from(document.querySelectorAll('.glide__slide.feature-item'));
    const perView = 3;


    // --- Duplica slides para loop visual ---
    slides = Array.from(document.querySelectorAll('.glide__slide.feature-item'));
    slides.forEach(slide => {
        slidesContainer.appendChild(slide.cloneNode(true));
    });
    slides = Array.from(document.querySelectorAll('.glide__slide.feature-item'));

    let currentIndex = 0;
    const totalSlides = slides.length / 2; // Solo cuenta los originales

    function updateCarousel() {
        const slideWidth = slides[0].offsetWidth + 32; // 32px gap
        track.scrollTo({
            left: slideWidth * currentIndex,
            behavior: 'smooth'
        });
    }

    // Loop continuo automático
    setInterval(() => {
        currentIndex++;
        if (currentIndex >= totalSlides) {
            // Salto instantáneo al inicio del loop duplicado
            currentIndex = 0;
            track.scrollTo({
                left: 0,
                behavior: 'auto'
            });
        }
        updateCarousel();
    }, 2200);

    updateCarousel();

    // Popup descriptivo al clickear una pancarta
    slidesContainer.addEventListener('click', function(e) {
        const item = e.target.closest('.feature-item');
        if (!item) return;

        const title = item.getAttribute('data-title') || item.querySelector('h3')?.textContent || '';
        const desc = item.getAttribute('data-desc') || item.querySelector('p')?.textContent || '';
        const img = item.querySelector('img');
        const imageUrl = img ? img.getAttribute('src') : '';
        const imageAlt = img ? img.getAttribute('alt') : '';

        Swal.fire({
            title: title,
            text: desc,
            imageUrl: imageUrl,
            imageWidth: 320,
            imageHeight: 180,
            imageAlt: imageAlt,
            background: "#222",
            color: "#ffe066",
            confirmButtonColor: "#ff4081"
        });
    });

    // Botón scroll top (sin cambios)
    const scrollTopBtn = document.getElementById('scrollTopBtn');
    window.addEventListener('scroll', function() {
        if ((window.innerHeight + window.scrollY) >= (document.body.offsetHeight - 40)) {
            scrollTopBtn.style.opacity = '1';
            scrollTopBtn.style.pointerEvents = 'auto';
        } else {
            scrollTopBtn.style.opacity = '0';
            scrollTopBtn.style.pointerEvents = 'none';
        }
    });
    scrollTopBtn.addEventListener('click', function() {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    // Fondo dinámico de puntos (sin cambios)
    const canvas = document.getElementById('futuristic-canvas');
    const ctx = canvas.getContext('2d');
    let width = window.innerWidth;
    let height = window.innerHeight;
    canvas.width = width;
    canvas.height = height;
    canvas.style.position = 'fixed';
    canvas.style.top = 0;
    canvas.style.left = 0;
    canvas.style.zIndex = 0;
    canvas.style.pointerEvents = 'none';
    canvas.style.background = 'black';

    function resizeCanvas() {
        width = window.innerWidth;
        height = window.innerHeight;
        canvas.width = width;
        canvas.height = height;
    }
    window.addEventListener('resize', resizeCanvas);

    const POINTS = 100;
    const points = [];
    const FADE_IN_DURATION = 600;

    function random(min, max) {
        return Math.random() * (max - min) + min;
    }

    function createPoint() {
        const angle = random(0, Math.PI * 2);
        const speed = random(0.5, 2);
        const now = Date.now();
        return {
            x: random(0, width),
            y: random(0, height),
            vx: Math.cos(angle) * speed,
            vy: Math.sin(angle) * speed,
            radius: random(3, 7),
            angle: angle,
            angularSpeed: random(-0.02, 0.02),
            created: now,
            opacity: 0
        };
    }

    for (let i = 0; i < POINTS; i++) {
        points.push(createPoint());
    }

    let cursor = { x: -1000, y: -1000 };
    window.addEventListener('mousemove', e => {
        cursor.x = e.clientX;
        cursor.y = e.clientY;
    });
    window.addEventListener('mouseleave', () => {
        cursor.x = -1000;
        cursor.y = -1000;
    });

    function isOutOfBounds(p) {
        return (
            p.x < -p.radius ||
            p.x > width + p.radius ||
            p.y < -p.radius ||
            p.y > height + p.radius
        );
    }

    function draw() {
        ctx.clearRect(0, 0, width, height);

        const now = Date.now();

        for (let i = 0; i < points.length; i++) {
            const p = points[i];
            p.angle += p.angularSpeed;
            p.x += p.vx + Math.cos(p.angle) * 0.5;
            p.y += p.vy + Math.sin(p.angle) * 0.5;

            let elapsed = now - p.created;
            if (elapsed < FADE_IN_DURATION) {
                p.opacity = elapsed / FADE_IN_DURATION;
            } else {
                p.opacity = 1;
            }

            ctx.save();
            ctx.globalAlpha = p.opacity;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
            ctx.fillStyle = 'yellow';
            ctx.shadowColor = 'yellow';
            ctx.shadowBlur = 15 * p.opacity;
            ctx.fill();
            ctx.restore();

            const dist = Math.hypot(cursor.x - p.x, cursor.y - p.y);
            if (dist < 120) {
                ctx.save();
                ctx.globalAlpha = p.opacity * 0.7;
                ctx.beginPath();
                ctx.moveTo(p.x, p.y);
                ctx.lineTo(cursor.x, cursor.y);
                ctx.strokeStyle = 'rgba(255,255,0,0.7)';
                ctx.lineWidth = 2;
                ctx.stroke();
                ctx.restore();
            }

            if (isOutOfBounds(p)) {
                points[i] = createPoint();
            }
        }

        requestAnimationFrame(draw);
    }

    draw();
});

// Carrusel Glide
document.addEventListener('DOMContentLoaded', function() {
    // Glide con tipo 'carousel' para repetición infinita
    new Glide('#glideCarrusel', {
        type: 'carousel', // Esto hace que el carrusel sea infinito
        perView: 3,
        gap: 32,
        focusAt: 'center',
        breakpoints: { 900: { perView: 2 }, 600: { perView: 1 } }
    }).mount();

    // Carrusel scroll con mouse en bordes
    const glideTrack = document.querySelector('#glideCarrusel .glide__track');
    let scrollInterval = null;
    glideTrack.addEventListener('mousemove', function(e) {
        const rect = glideTrack.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const width = rect.width;
        const edge = 80;
        clearInterval(scrollInterval);
        if (x < edge) {
            scrollInterval = setInterval(() => { glideTrack.scrollLeft -= 2; }, 10);
        } else if (x > width - edge) {
            scrollInterval = setInterval(() => { glideTrack.scrollLeft += 2; }, 10);
        }
    });
    glideTrack.addEventListener('mouseleave', function() {
        clearInterval(scrollInterval);
    });

    // Botón scroll top
    const scrollTopBtn = document.getElementById('scrollTopBtn');
    let popupOpen = false;

    window.addEventListener('scroll', function() {
        if (!popupOpen && (window.innerHeight + window.scrollY) >= (document.body.offsetHeight - 40)) {
            scrollTopBtn.style.opacity = '1';
            scrollTopBtn.style.pointerEvents = 'auto';
        } else {
            scrollTopBtn.style.opacity = '0';
            scrollTopBtn.style.pointerEvents = 'none';
        }
    });
    scrollTopBtn.addEventListener('click', function() {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    // --- POPUP PERSONALIZADO PARA CADA PANCARTA (delegación) ---
    document.querySelector('.glide__slides').addEventListener('click', function(e) {
        const item = e.target.closest('.feature-item');
        if (!item) return;

        const rect = item.getBoundingClientRect();
        const scrollY = window.scrollY || window.pageYOffset;
        const pancartaY = rect.top + scrollY;

        const title = item.getAttribute('data-title') || item.querySelector('h3')?.textContent || 'Sweet!';
        const desc = item.getAttribute('data-desc') || item.querySelector('p')?.textContent || 'Modal with a custom image.';
        const img = item.querySelector('img');
        const imageUrl = img ? img.getAttribute('src') : "https://unsplash.it/400/200";
        const imageAlt = img ? img.getAttribute('alt') : "Custom image";

        popupOpen = true;
        scrollTopBtn.style.opacity = '0';
        scrollTopBtn.style.pointerEvents = 'none';

        Swal.fire({
            title: title,
            text: desc,
            imageUrl: imageUrl,
            imageWidth: 400,
            imageHeight: 200,
            imageAlt: imageAlt,
            background: "#222",
            color: "#ffe066",
            backdrop: `rgba(0,0,0,0.6) blur(6px)`,
            confirmButtonColor: "#ff4081",
            willClose: () => {
                window.scrollTo({ top: pancartaY - 40, behavior: 'auto' });
                popupOpen = false;
                window.dispatchEvent(new Event('scroll'));
            }
        });
    });
});

// --- CANVAS DE PUNTOS FUTURISTAS ---
document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('futuristic-canvas');
    const ctx = canvas.getContext('2d');
    let width = window.innerWidth;
    let height = window.innerHeight;
    canvas.width = width;
    canvas.height = height;
    canvas.style.position = 'fixed';
    canvas.style.top = 0;
    canvas.style.left = 0;
    canvas.style.zIndex = 0;
    canvas.style.pointerEvents = 'none';
    canvas.style.background = 'black';

    function resizeCanvas() {
        width = window.innerWidth;
        height = window.innerHeight;
        canvas.width = width;
        canvas.height = height;
    }
    window.addEventListener('resize', resizeCanvas);

    // Puntos
    const POINTS = 100;
    const points = [];
    const FADE_IN_DURATION = 600; // ms

    function random(min, max) {
        return Math.random() * (max - min) + min;
    }

    function createPoint() {
        const angle = random(0, Math.PI * 2);
        const speed = random(0.5, 2);
        const now = Date.now();
        return {
            x: random(0, width),
            y: random(0, height),
            vx: Math.cos(angle) * speed,
            vy: Math.sin(angle) * speed,
            radius: random(3, 7),
            angle: angle,
            angularSpeed: random(-0.02, 0.02),
            created: now,
            opacity: 0
        };
    }

    for (let i = 0; i < POINTS; i++) {
        points.push(createPoint());
    }

    // Cursor
    let cursor = { x: -1000, y: -1000 };
    window.addEventListener('mousemove', e => {
        cursor.x = e.clientX;
        cursor.y = e.clientY;
    });
    window.addEventListener('mouseleave', () => {
        cursor.x = -1000;
        cursor.y = -1000;
    });

    function isOutOfBounds(p) {
        return (
            p.x < -p.radius ||
            p.x > width + p.radius ||
            p.y < -p.radius ||
            p.y > height + p.radius
        );
    }

    function draw() {
        ctx.clearRect(0, 0, width, height);

        const now = Date.now();

        for (let i = 0; i < points.length; i++) {
            const p = points[i];

            // Movimiento circular continuo
            p.angle += p.angularSpeed;
            p.x += p.vx + Math.cos(p.angle) * 0.5;
            p.y += p.vy + Math.sin(p.angle) * 0.5;

            // Fade in (degradé de luminosidad)
            let elapsed = now - p.created;
            if (elapsed < FADE_IN_DURATION) {
                p.opacity = elapsed / FADE_IN_DURATION;
            } else {
                p.opacity = 1;
            }

            // Dibuja el punto con opacidad
            ctx.save();
            ctx.globalAlpha = p.opacity;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
            ctx.fillStyle = 'yellow';
            ctx.shadowColor = 'yellow';
            ctx.shadowBlur = 15 * p.opacity;
            ctx.fill();
            ctx.restore();

            // Línea al cursor si está cerca
            const dist = Math.hypot(cursor.x - p.x, cursor.y - p.y);
            if (dist < 120) {
                ctx.save();
                ctx.globalAlpha = p.opacity * 0.7;
                ctx.beginPath();
                ctx.moveTo(p.x, p.y);
                ctx.lineTo(cursor.x, cursor.y);
                ctx.strokeStyle = 'rgba(255,255,0,0.7)';
                ctx.lineWidth = 2;
                ctx.stroke();
                ctx.restore();
            }

            // Si sale del área visible, reemplazar por un nuevo punto
            if (isOutOfBounds(p)) {
                points[i] = createPoint();
            }
        }

        requestAnimationFrame(draw);
    }

    draw();
});

// Mostrar/ocultar marcadores del modelo 3D
document.addEventListener('DOMContentLoaded', function() {
    const model3dContainer = document.querySelector('.model-3d-container');
    const showMarkersBtn = document.getElementById('showMarkersBtn');
    let markersVisible = false;

    if (model3dContainer && showMarkersBtn) {
        showMarkersBtn.addEventListener('click', function() {
            markersVisible = !markersVisible;
            if (markersVisible) {
                model3dContainer.classList.add('show-markers');
                showMarkersBtn.textContent = "Ocultar señalizaciones";
            } else {
                model3dContainer.classList.remove('show-markers');
                showMarkersBtn.textContent = "Mostrar señalizaciones";
            }
        });
    }
});