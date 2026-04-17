/* ==========================================
   CAREER INTELLIGENCE AGENT — PORTFOLIO SITE
   ========================================== */

'use strict';

// ==========================================
// HERO CANVAS — particle graph
// ==========================================
(function initCanvas() {
  const canvas = document.getElementById('hero-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const ACCENT = '0,212,255';
  const ACCENT2 = '124,58,237';

  let W, H, particles, animId;
  const COUNT = 80;
  const MAX_DIST = 140;
  const SPEED = 0.28;

  class Particle {
    constructor() { this.reset(true); }
    reset(initial) {
      this.x = Math.random() * W;
      this.y = initial ? Math.random() * H : Math.random() * H;
      this.vx = (Math.random() - 0.5) * SPEED;
      this.vy = (Math.random() - 0.5) * SPEED;
      this.r = Math.random() * 1.5 + 0.5;
      this.alpha = Math.random() * 0.4 + 0.15;
      this.color = Math.random() > 0.6 ? ACCENT2 : ACCENT;
    }
    update() {
      this.x += this.vx;
      this.y += this.vy;
      if (this.x < -10 || this.x > W + 10 || this.y < -10 || this.y > H + 10) {
        this.reset(false);
      }
    }
    draw() {
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${this.color},${this.alpha})`;
      ctx.fill();
    }
  }

  function resize() {
    W = canvas.width = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }

  function init() {
    resize();
    particles = Array.from({ length: COUNT }, () => new Particle());
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);

    // draw connections
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const d = Math.sqrt(dx * dx + dy * dy);
        if (d < MAX_DIST) {
          const alpha = (1 - d / MAX_DIST) * 0.12;
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(${ACCENT},${alpha})`;
          ctx.lineWidth = 0.6;
          ctx.stroke();
        }
      }
    }

    // draw particles
    particles.forEach(p => { p.update(); p.draw(); });

    animId = requestAnimationFrame(draw);
  }

  window.addEventListener('resize', () => {
    cancelAnimationFrame(animId);
    init();
    draw();
  });

  init();
  draw();
})();

// ==========================================
// NAVBAR — scroll state + hamburger
// ==========================================
(function initNav() {
  const navbar = document.getElementById('navbar');
  const hamburger = document.getElementById('hamburger');
  const navInner = document.querySelector('.nav-inner');

  window.addEventListener('scroll', () => {
    navbar.classList.toggle('scrolled', window.scrollY > 40);
  }, { passive: true });

  hamburger && hamburger.addEventListener('click', () => {
    const open = navInner.classList.toggle('nav-open');
    hamburger.setAttribute('aria-expanded', String(open));
    // animate hamburger to X
    const spans = hamburger.querySelectorAll('span');
    if (open) {
      spans[0].style.transform = 'translateY(7px) rotate(45deg)';
      spans[1].style.opacity = '0';
      spans[2].style.transform = 'translateY(-7px) rotate(-45deg)';
    } else {
      spans.forEach(s => { s.style.transform = ''; s.style.opacity = ''; });
    }
  });

  // close mobile nav on link click
  document.querySelectorAll('.nav-links a').forEach(link => {
    link.addEventListener('click', () => {
      navInner.classList.remove('nav-open');
      const spans = hamburger ? hamburger.querySelectorAll('span') : [];
      spans.forEach(s => { s.style.transform = ''; s.style.opacity = ''; });
    });
  });
})();

// ==========================================
// REVEAL ON SCROLL — IntersectionObserver
// ==========================================
(function initReveal() {
  const els = document.querySelectorAll('.reveal');
  if (!els.length) return;

  const io = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        // stagger children with reveal class inside grids
        const delay = entry.target.dataset.delay || 0;
        setTimeout(() => {
          entry.target.classList.add('visible');
        }, delay);
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -60px 0px' });

  // Add stagger delays to grid children
  document.querySelectorAll(
    '.cap-grid, .use-grid, .stack-grid, .status-grid, .about-pillars, .arch-sidebar, .footer-links .footer-col'
  ).forEach(grid => {
    const children = grid.querySelectorAll('.reveal');
    children.forEach((child, i) => {
      child.dataset.delay = i * 80;
    });
  });

  els.forEach(el => io.observe(el));
})();

// ==========================================
// SMOOTH SCROLL — offset for fixed nav
// ==========================================
(function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener('click', e => {
      const target = document.querySelector(link.getAttribute('href'));
      if (!target) return;
      e.preventDefault();
      const offset = 80;
      const top = target.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top, behavior: 'smooth' });
    });
  });
})();

// ==========================================
// ACTIVE NAV LINK — highlight on scroll
// ==========================================
(function initActiveNav() {
  const sections = document.querySelectorAll('section[id]');
  const links = document.querySelectorAll('.nav-links a[href^="#"]');

  function update() {
    let current = '';
    sections.forEach(s => {
      if (window.scrollY >= s.offsetTop - 140) current = s.id;
    });
    links.forEach(link => {
      link.style.color = link.getAttribute('href') === '#' + current
        ? 'var(--accent)'
        : '';
    });
  }

  window.addEventListener('scroll', update, { passive: true });
  update();
})();

// ==========================================
// CAPABILITY CARD — subtle cursor follow glow
// ==========================================
(function initCardGlow() {
  document.querySelectorAll('.cap-card, .use-card, .flow-body').forEach(card => {
    card.addEventListener('mousemove', e => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      card.style.setProperty('--mx', `${x}px`);
      card.style.setProperty('--my', `${y}px`);
    });
  });
})();

// ==========================================
// COUNTER ANIMATION — hero stats + status footer
// ==========================================
(function initCounters() {
  const counters = document.querySelectorAll('.stat-num, .big-num');
  if (!counters.length) return;

  const io = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const el = entry.target;
      const raw = el.textContent.trim();
      const match = raw.match(/^([\d,]+)/);
      if (!match) return;
      const target = parseInt(match[1].replace(/,/g, ''), 10);
      if (isNaN(target)) return;
      const suffix = raw.replace(/^[\d,]+/, '');
      const duration = 1200;
      const start = performance.now();

      function tick(now) {
        const t = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - t, 3);
        const val = Math.round(eased * target);
        el.textContent = val.toLocaleString() + suffix;
        if (t < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
      io.unobserve(el);
    });
  }, { threshold: 0.5 });

  counters.forEach(el => io.observe(el));
})();

// ==========================================
// ARCHITECTURE LAYER — hover highlight
// ==========================================
(function initArchHover() {
  document.querySelectorAll('.arch-node').forEach(node => {
    node.addEventListener('mouseenter', () => {
      node.style.background = 'rgba(0,212,255,0.1)';
      node.style.borderColor = 'rgba(0,212,255,0.3)';
    });
    node.addEventListener('mouseleave', () => {
      node.style.background = '';
      node.style.borderColor = '';
    });
  });
})();

// ==========================================
// FLOW STEPS — progress line animation
// ==========================================
(function initFlowProgress() {
  const connectors = document.querySelectorAll('.flow-connector');
  const io = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.background =
          'linear-gradient(to bottom, rgba(0,212,255,0.4), rgba(0,212,255,0.05))';
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 1 });
  connectors.forEach(c => io.observe(c));
})();
