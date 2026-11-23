/* ============================================================
   SAMAÂDI — main.js
   Navigation scroll + sélecteur de langue (i18n)
   Zéro dépendance externe
   ============================================================ */

'use strict';

/* ── Navigation au scroll ── */

(function () {
  const nav = document.getElementById('main-nav');
  if (!nav) return;

  let lastScroll = 0;

  function onScroll() {
    const scrollY = window.scrollY;

    // Ajout de la classe scrolled après 80px
    if (scrollY > 80) {
      nav.classList.add('scrolled');
    } else {
      nav.classList.remove('scrolled');
    }

    lastScroll = scrollY;
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll(); // État initial
})();


/* ── Sélecteur de langue (FR / EN) ── */

(function () {
  const STORAGE_KEY = 'samaadi_lang';

  function setLang(lang) {
    // Validation
    if (lang !== 'fr' && lang !== 'en') lang = 'fr';

    // Applique au body
    document.body.classList.toggle('lang-en', lang === 'en');

    // Met à jour les boutons
    const btnFr = document.getElementById('btn-fr');
    const btnEn = document.getElementById('btn-en');
    if (btnFr) btnFr.classList.toggle('active', lang === 'fr');
    if (btnEn) btnEn.classList.toggle('active', lang === 'en');

    // Mémorise le choix (localStorage — données strictement locales, RGPD ok)
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch (e) {
      // localStorage peut être bloqué en navigation privée — pas bloquant
    }

    // Met à jour l'attribut lang du document pour l'accessibilité
    document.documentElement.lang = lang === 'fr' ? 'fr-BE' : 'en';
  }

  // Expose globalement pour les onclick inline
  window.setLang = setLang;

  // Initialisation : langue mémorisée ou langue du navigateur
  function initLang() {
    let lang = 'fr';

    // Vérifier la préférence mémorisée
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === 'fr' || stored === 'en') {
        lang = stored;
      } else {
        // Détecter la langue du navigateur
        const browserLang = navigator.language || navigator.userLanguage || 'fr';
        if (browserLang.toLowerCase().startsWith('en')) {
          lang = 'en';
        }
      }
    } catch (e) {
      // Fallback silencieux
    }

    setLang(lang);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLang);
  } else {
    initLang();
  }
})();


/* ── Menu hamburger mobile ── */

(function () {
  const hamburger = document.getElementById('nav-hamburger');
  const mobileMenu = document.getElementById('nav-mobile-menu');
  if (!hamburger || !mobileMenu) return;

  hamburger.addEventListener('click', function () {
    const isOpen = mobileMenu.classList.toggle('is-open');
    hamburger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    hamburger.setAttribute('aria-label', isOpen ? 'Fermer le menu' : 'Ouvrir le menu');
  });

  // Fermer le menu au clic sur un lien
  mobileMenu.querySelectorAll('a').forEach(function (link) {
    link.addEventListener('click', function () {
      mobileMenu.classList.remove('is-open');
      hamburger.setAttribute('aria-expanded', 'false');
      hamburger.setAttribute('aria-label', 'Ouvrir le menu');
    });
  });

  // Fermer au clic en dehors
  document.addEventListener('click', function (e) {
    if (!hamburger.contains(e.target) && !mobileMenu.contains(e.target)) {
      mobileMenu.classList.remove('is-open');
      hamburger.setAttribute('aria-expanded', 'false');
    }
  });
})();


/* ── Navigation fluide vers les ancres ── */

(function () {
  document.querySelectorAll('a[href^="#"]').forEach(function (link) {
    link.addEventListener('click', function (e) {
      const targetId = this.getAttribute('href').slice(1);
      const target = document.getElementById(targetId);
      if (!target) return;

      e.preventDefault();

      const navHeight = document.getElementById('main-nav')
        ? document.getElementById('main-nav').offsetHeight
        : 0;

      const top = target.getBoundingClientRect().top + window.scrollY - navHeight - 24;

      window.scrollTo({ top, behavior: 'smooth' });
    });
  });
})();


/* ── Lazy loading images (fallback pour anciens navigateurs) ── */

(function () {
  // Les navigateurs modernes gèrent nativement loading="lazy"
  // Ce fallback s'active uniquement si IntersectionObserver est absent
  if ('loading' in HTMLImageElement.prototype || !('IntersectionObserver' in window)) return;

  const lazyImages = document.querySelectorAll('img[loading="lazy"]');

  const observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        const img = entry.target;
        if (img.dataset.src) {
          img.src = img.dataset.src;
        }
        observer.unobserve(img);
      }
    });
  }, { rootMargin: '200px' });

  lazyImages.forEach(function (img) {
    observer.observe(img);
  });
})();
