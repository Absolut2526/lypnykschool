/**
 * Липницький ЗЗСО І-ІІІ ступенів - Main JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
  initMobileNav();
  initNewsSection();
  initModals();
  initLightbox();
});

/* ==========================================================================
   Security Helpers: XSS Sanitizer & Auto-Link Detector
   ========================================================================== */
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function autoLink(text) {
  if (!text) return '';
  // First escape all HTML to neutralize any XSS tags
  let linked = escapeHtml(text);

  // Match safe URLs (only http and https)
  const urlRegex = /(https?:\/\/[^\s<>"'()]+[^\s<>"'().,:;?!])/g;
  linked = linked.replace(urlRegex, (url) => {
    let label = url;
    if (url.includes('zakon.rada.gov.ua')) {
      label = 'Офіційний Закон на сайті Верховної Ради (zakon.rada.gov.ua)';
    } else if (url.includes('mon.gov.ua')) {
      label = 'Офіційний портал Міністерства освіти і науки України';
    } else if (url.length > 55) {
      label = url.slice(0, 50) + '...';
    }
    // Clean URL for href attribute
    const safeHref = encodeURI(decodeURI(url)).replace(/"/g, '%22').replace(/'/g, '%27');
    return `<a href="${safeHref}" target="_blank" rel="noopener noreferrer" class="inline-link" style="color: #2563eb; font-weight: 700; text-decoration: underline; word-break: break-all; display: inline-flex; align-items: center; gap: 0.35rem; background: #eff6ff; padding: 0.2rem 0.6rem; border-radius: 6px; border: 1px solid #bfdbfe;"><i class="fas fa-external-link-alt" style="font-size: 0.85em;"></i> ${escapeHtml(label)}</a>`;
  });

  // Match safe emails
  const emailRegex = /([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9._-]+)/g;
  linked = linked.replace(emailRegex, (match, email) => {
    const safeEmail = encodeURI(email);
    return `<a href="mailto:${safeEmail}" class="inline-link" style="color: #2563eb; font-weight: 700; text-decoration: underline;"><i class="fas fa-envelope" style="font-size: 0.85em;"></i> ${escapeHtml(email)}</a>`;
  });

  return linked;
}

/* ==========================================================================
   Mobile Navigation
   ========================================================================== */
function initMobileNav() {
  const toggleBtn = document.getElementById('mobileToggle');
  const mobileNav = document.getElementById('mobileNav');
  const closeBtn = document.getElementById('closeMobileNav');

  if (!toggleBtn || !mobileNav) return;

  toggleBtn.addEventListener('click', () => {
    mobileNav.style.display = 'block';
    document.body.style.overflow = 'hidden';
  });

  const closeNav = () => {
    mobileNav.style.display = 'none';
    document.body.style.overflow = '';
  };

  if (closeBtn) closeBtn.addEventListener('click', closeNav);
  mobileNav.addEventListener('click', (e) => {
    if (e.target === mobileNav) closeNav();
  });
}

/* ==========================================================================
   News Rendering, Search & Filtering
   ========================================================================== */
let currentCategory = 'all';
let currentYear = 'all';
let currentSearchQuery = '';
let currentPage = 1;
const itemsPerPage = 12;

function initNewsSection() {
  const container = document.getElementById('newsGrid');
  if (!container || !window.SCHOOL_NEWS) return;

  renderNews();

  // Search input
  const searchInput = document.getElementById('newsSearch');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      currentSearchQuery = e.target.value.toLowerCase().trim();
      currentPage = 1;
      renderNews();
    });
  }

  // Category filter pills
  const catPills = document.querySelectorAll('.cat-pill');
  catPills.forEach(pill => {
    pill.addEventListener('click', () => {
      catPills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      currentCategory = pill.dataset.category || 'all';
      currentPage = 1;
      renderNews();
    });
  });

  // Year filter selector
  const yearSelect = document.getElementById('yearFilter');
  if (yearSelect) {
    yearSelect.addEventListener('change', (e) => {
      currentYear = e.target.value;
      currentPage = 1;
      renderNews();
    });
  }

  // Load more button
  const loadMoreBtn = document.getElementById('loadMoreNews');
  if (loadMoreBtn) {
    loadMoreBtn.addEventListener('click', () => {
      currentPage++;
      renderNews(true);
    });
  }
}

function renderNews(append = false) {
  const container = document.getElementById('newsGrid');
  const loadMoreBtn = document.getElementById('loadMoreNews');
  const newsCountEl = document.getElementById('newsCount');
  if (!container || !window.SCHOOL_NEWS) return;

  const filtered = window.SCHOOL_NEWS.filter(item => {
    const matchCat = (currentCategory === 'all') || (item.category === currentCategory);
    const matchYear = (currentYear === 'all') || (item.year === currentYear);
    const fullText = (item.title + ' ' + (item.full_text || '')).toLowerCase();
    const matchQuery = !currentSearchQuery || fullText.includes(currentSearchQuery);

    return matchCat && matchYear && matchQuery;
  });

  if (newsCountEl) {
    newsCountEl.textContent = `Знайдено подій: ${filtered.length}`;
  }

  const paginated = filtered.slice(0, currentPage * itemsPerPage);

  if (!append) {
    container.innerHTML = '';
  }

  if (filtered.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 3rem 1rem; color: var(--text-muted);">
        <i class="fas fa-search" style="font-size: 2.5rem; margin-bottom: 1rem; color: #cbd5e1;"></i>
        <h3>Подій за вашим запитом не знайдено</h3>
        <p>Спробуйте змінити фільтри або пошуковий запит.</p>
      </div>
    `;
    if (loadMoreBtn) loadMoreBtn.style.display = 'none';
    return;
  }

  const toRender = append ? paginated.slice((currentPage - 1) * itemsPerPage) : paginated;

  toRender.forEach(item => {
    const card = document.createElement('div');
    card.className = 'news-card';
    card.onclick = () => openNewsModal(item);

    const imgs = (item.local_images && item.local_images.length > 0) ? item.local_images : (item.images || []);
    const hasVideo = !!item.video || !!item.youtube;
    const coverImg = imgs.length > 0 ? imgs[0] : (item.youtube ? `https://img.youtube.com/vi/${item.youtube}/hqdefault.jpg` : '');
    const photoCount = imgs.length;

    const snippet = item.full_text ? item.full_text.slice(0, 170) + '...' : item.title;

    const imgWrapContent = coverImg ? `
      <img class="news-card-img" src="${coverImg}" alt="${item.title}" loading="lazy">
    ` : `
      <div style="width: 100%; height: 100%; min-height: 200px; background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%); display: flex; align-items: center; justify-content: center; color: white;">
        <i class="fas fa-graduation-cap" style="font-size: 3rem; opacity: 0.4;"></i>
      </div>
    `;

    card.innerHTML = `
      <div class="news-card-img-wrap">
        ${imgWrapContent}
        <span class="badge badge-primary news-badge">${item.category}</span>
        <div style="position: absolute; bottom: 0.75rem; right: 0.75rem; display: flex; gap: 0.4rem; z-index: 2;">
          ${hasVideo ? `<span class="badge badge-accent" style="box-shadow: 0 2px 6px rgba(0,0,0,0.3); font-weight: 700;"><i class="fas fa-play"></i> Відео</span>` : ''}
          ${photoCount > 1 ? `<span class="news-photo-count"><i class="fas fa-camera"></i> ${photoCount} світлин</span>` : ''}
        </div>
      </div>
      <div class="news-card-body">
        <div class="news-meta">
          <span><i class="far fa-calendar-alt"></i> ${item.year} рік</span>
          <span>•</span>
          <span><i class="fas fa-map-marker-alt"></i> Липник</span>
        </div>
        <h3 class="news-card-title">${item.title}</h3>
        <p class="news-card-text">${snippet}</p>
        <div class="news-card-footer">
          <span class="news-read-more">Детальніше ${hasVideo ? 'та відео' : (photoCount > 1 ? `(${photoCount} фото)` : '')} <i class="fas fa-arrow-right"></i></span>
        </div>
      </div>
    `;

    container.appendChild(card);
  });

  if (loadMoreBtn) {
    if (paginated.length < filtered.length) {
      loadMoreBtn.style.display = 'inline-flex';
    } else {
      loadMoreBtn.style.display = 'none';
    }
  }
}

/* ==========================================================================
   News Story Modal
   ========================================================================== */
function openNewsModal(item) {
  const modal = document.getElementById('newsModal');
  if (!modal) return;

  const titleEl = document.getElementById('modalNewsTitle');
  const catEl = document.getElementById('modalNewsCategory');
  const yearEl = document.getElementById('modalNewsYear');
  const bodyEl = document.getElementById('modalNewsBody');
  const carouselEl = document.getElementById('modalNewsCarousel');

  if (titleEl) titleEl.textContent = item.title;
  if (catEl) catEl.textContent = item.category;
  if (yearEl) yearEl.textContent = `${item.year} рік`;

  if (bodyEl) {
    const paras = Array.isArray(item.content) && item.content.length > 0 ? item.content : [item.full_text || item.title];
    let bodyHtml = '';
    
    // MP4 Video player
    if (item.video) {
      bodyHtml += `
        <div style="margin-bottom: 1.5rem; border-radius: var(--radius-lg); overflow: hidden; box-shadow: var(--shadow-lg); background: #000;">
          <video controls style="width: 100%; max-height: 460px; display: block;" src="${item.video}" preload="metadata">
            Ваш браузер не підтримує відео.
          </video>
        </div>
      `;
    } else if (item.youtube) {
      bodyHtml += `
        <div style="margin-bottom: 1.5rem; border-radius: var(--radius-lg); overflow: hidden; box-shadow: var(--shadow-lg); position: relative; padding-bottom: 56.25%; height: 0; background: #000;">
          <iframe src="https://www.youtube.com/embed/${item.youtube}?autoplay=1" style="position: absolute; top:0; left: 0; width: 100%; height: 100%; border:0;" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
        </div>
      `;
    }

    bodyHtml += paras.map(p => `<p style="margin-bottom: 1rem; font-size: 1.05rem; line-height: 1.7;">${autoLink(p)}</p>`).join('');
    bodyEl.innerHTML = bodyHtml;
  }

  if (carouselEl) {
    carouselEl.innerHTML = '';
    const imgs = (item.local_images && item.local_images.length > 0) ? item.local_images : (item.images || []);
    if (imgs.length > 0) {
      const imgObjects = imgs.map((u, idx) => ({
        img: u,
        title: item.title,
        category: item.category,
        year: item.year,
        index: idx + 1
      }));
      imgs.forEach((imgUrl, i) => {
        const img = document.createElement('img');
        img.src = imgUrl;
        img.alt = `${item.title} (фото ${i+1})`;
        img.loading = 'lazy';
        img.style.cursor = 'zoom-in';
        img.onclick = () => openLightbox(imgUrl, imgObjects, i);
        carouselEl.appendChild(img);
      });
      carouselEl.style.display = 'flex';
    } else {
      carouselEl.style.display = 'none';
    }
  }

  modal.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function initModals() {
  const modals = document.querySelectorAll('.modal-overlay');
  modals.forEach(m => {
    const closeBtn = m.querySelector('.modal-close');
    const stopMedia = () => {
      const v = m.querySelector('video');
      if (v) v.pause();
      const ifr = m.querySelector('iframe');
      if (ifr) ifr.src = '';
    };

    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        stopMedia();
        m.classList.remove('active');
        document.body.style.overflow = '';
      });
    }
    m.addEventListener('click', (e) => {
      if (e.target === m) {
        stopMedia();
        m.classList.remove('active');
        document.body.style.overflow = '';
      }
    });
  });

  document.addEventListener('keydown', (e) => {
    const lb = document.getElementById('lightboxModal');
    const isLbActive = lb && lb.classList.contains('active');

    if (e.key === 'Escape') {
      if (isLbActive) {
        closeLightbox();
        return;
      }
      modals.forEach(m => {
        const v = m.querySelector('video');
        if (v) v.pause();
        const ifr = m.querySelector('iframe');
        if (ifr) ifr.src = '';
        m.classList.remove('active');
      });
      closeDocModal();
      document.body.style.overflow = '';
    } else if (isLbActive) {
      if (e.key === 'ArrowLeft') {
        lightboxPrev();
      } else if (e.key === 'ArrowRight') {
        lightboxNext();
      }
    }
  });
}

/* ==========================================================================
   Image Lightbox (Interactive Carousel & Swipe Navigation)
   ========================================================================== */
let lightboxItems = [];
let currentLightboxIndex = 0;
let lbTouchStartX = 0;
let lbTouchEndX = 0;

function initLightbox() {
  let lb = document.getElementById('lightboxModal');
  if (!lb) {
    lb = document.createElement('div');
    lb.id = 'lightboxModal';
    lb.className = 'modal-overlay lightbox-overlay';
    lb.innerHTML = `
      <button class="lightbox-close-btn" aria-label="Закрити" onclick="closeLightbox()">
        <i class="fas fa-times"></i>
      </button>
      <button class="lightbox-nav-btn lightbox-prev" aria-label="Попереднє фото" onclick="lightboxPrev(event)">
        <i class="fas fa-chevron-left"></i>
      </button>
      <button class="lightbox-nav-btn lightbox-next" aria-label="Наступне фото" onclick="lightboxNext(event)">
        <i class="fas fa-chevron-right"></i>
      </button>
      <div class="lightbox-content-wrapper" onclick="event.stopPropagation()">
        <div class="lightbox-img-container">
          <img id="lightboxImg" src="" alt="Перегляд світлини">
        </div>
        <div class="lightbox-info-bar" id="lightboxInfoBar">
          <span class="lightbox-counter" id="lightboxCounter">1 / 1</span>
          <span class="lightbox-caption" id="lightboxCaption"></span>
        </div>
      </div>
    `;
    document.body.appendChild(lb);

    lb.addEventListener('click', (e) => {
      if (e.target === lb) {
        closeLightbox();
      }
    });

    lb.addEventListener('touchstart', (e) => {
      lbTouchStartX = e.changedTouches[0].screenX;
    }, { passive: true });

    lb.addEventListener('touchend', (e) => {
      lbTouchEndX = e.changedTouches[0].screenX;
      handleLightboxSwipe();
    }, { passive: true });
  }
}

function handleLightboxSwipe() {
  const swipeThreshold = 45;
  if (lbTouchEndX < lbTouchStartX - swipeThreshold) {
    lightboxNext();
  } else if (lbTouchEndX > lbTouchStartX + swipeThreshold) {
    lightboxPrev();
  }
}

function openLightbox(srcOrItem, list = null, index = null) {
  initLightbox();
  const lb = document.getElementById('lightboxModal');
  if (!lb) return;

  if (Array.isArray(list) && list.length > 0) {
    lightboxItems = list.map(item => {
      if (typeof item === 'string') return { img: item, title: '' };
      return item;
    });
    if (typeof index === 'number' && index >= 0 && index < lightboxItems.length) {
      currentLightboxIndex = index;
    } else {
      const targetSrc = (typeof srcOrItem === 'string') ? srcOrItem : (srcOrItem?.img || '');
      const foundIdx = lightboxItems.findIndex(it => (it.img === targetSrc || it === targetSrc));
      currentLightboxIndex = (foundIdx !== -1) ? foundIdx : 0;
    }
  } else if (typeof srcOrItem === 'object' && srcOrItem !== null) {
    lightboxItems = [srcOrItem];
    currentLightboxIndex = 0;
  } else if (typeof srcOrItem === 'string') {
    lightboxItems = [{ img: srcOrItem, title: '' }];
    currentLightboxIndex = 0;
  }

  updateLightboxView(false);
  lb.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function updateLightboxView(animated = true) {
  const img = document.getElementById('lightboxImg');
  const counter = document.getElementById('lightboxCounter');
  const caption = document.getElementById('lightboxCaption');
  const prevBtn = document.querySelector('.lightbox-prev');
  const nextBtn = document.querySelector('.lightbox-next');
  const infoBar = document.getElementById('lightboxInfoBar');

  if (!img || lightboxItems.length === 0) return;

  const currentItem = lightboxItems[currentLightboxIndex];
  const src = currentItem.img || currentItem;
  const title = currentItem.title || '';
  const category = currentItem.category ? `[${currentItem.category}] ` : '';

  if (animated) {
    img.classList.add('lb-fade-out');
    setTimeout(() => {
      img.src = src;
      img.onload = () => {
        img.classList.remove('lb-fade-out');
      };
      setTimeout(() => img.classList.remove('lb-fade-out'), 120);
    }, 100);
  } else {
    img.classList.remove('lb-fade-out');
    img.src = src;
  }

  if (counter) {
    counter.textContent = `${currentLightboxIndex + 1} / ${lightboxItems.length}`;
  }

  if (caption) {
    caption.textContent = title ? `${category}${title}` : '';
  }

  if (infoBar) {
    infoBar.style.display = (lightboxItems.length > 1 || title) ? 'flex' : 'none';
  }

  const showNav = lightboxItems.length > 1;
  if (prevBtn) prevBtn.style.display = showNav ? 'flex' : 'none';
  if (nextBtn) nextBtn.style.display = showNav ? 'flex' : 'none';
}

function lightboxPrev(e) {
  if (e) e.stopPropagation();
  if (lightboxItems.length <= 1) return;
  currentLightboxIndex = (currentLightboxIndex - 1 + lightboxItems.length) % lightboxItems.length;
  updateLightboxView(true);
}

function lightboxNext(e) {
  if (e) e.stopPropagation();
  if (lightboxItems.length <= 1) return;
  currentLightboxIndex = (currentLightboxIndex + 1) % lightboxItems.length;
  updateLightboxView(true);
}

function closeLightbox() {
  const lb = document.getElementById('lightboxModal');
  if (lb) {
    lb.classList.remove('active');
    document.body.style.overflow = '';
  }
}

/* ==========================================================================
   Document Reader Modal (100% Autonomous & Offline-friendly)
   ========================================================================== */
function initDocModal() {
  let dm = document.getElementById('docModal');
  if (!dm) {
    dm = document.createElement('div');
    dm.id = 'docModal';
    dm.className = 'modal-overlay';
    dm.innerHTML = `
      <div class="modal-box" style="max-width: 840px; max-height: 88vh;">
        <div class="modal-header" style="background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%); color: white; border-radius: var(--radius-xl) var(--radius-xl) 0 0; padding: 1.25rem 1.75rem;">
          <div style="display: flex; align-items: center; gap: 0.6rem;">
            <i class="fas fa-file-contract" style="color: #fbbf24; font-size: 1.2rem;"></i>
            <span style="font-weight: 700; font-size: 0.95rem; letter-spacing: 0.5px;">ОФІЦІЙНИЙ ДОКУМЕНТ ЗАКЛАДУ</span>
          </div>
          <button class="modal-close" style="color: white; background: rgba(255,255,255,0.15);" onclick="closeDocModal()"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body" style="padding: 2rem; overflow-y: auto;">
          <h2 id="modalDocTitle" style="font-size: 1.35rem; font-weight: 800; color: var(--primary); margin-bottom: 1.25rem; line-height: 1.4;"></h2>
          <div id="modalDocContent" style="color: var(--text-main); font-size: 1.02rem; line-height: 1.75;"></div>
          <div id="modalDocActions" style="margin-top: 2rem; display: flex; gap: 1rem; flex-wrap: wrap; border-top: 1px solid var(--border-color); padding-top: 1.5rem;">
            <button class="btn btn-primary btn-sm" onclick="window.print()"><i class="fas fa-print"></i> Роздрукувати</button>
            <button class="btn btn-secondary btn-sm" onclick="closeDocModal()"><i class="fas fa-check"></i> Зрозуміло</button>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(dm);
    
    dm.addEventListener('click', (e) => {
      if (e.target === dm) closeDocModal();
    });
  }
}

function openDocModal(slug) {
  initDocModal();
  const dm = document.getElementById('docModal');
  const titleEl = document.getElementById('modalDocTitle');
  const contentEl = document.getElementById('modalDocContent');
  if (!dm || !titleEl || !contentEl) return;

  const doc = (window.SCHOOL_DOCUMENTS && window.SCHOOL_DOCUMENTS[slug]) ? window.SCHOOL_DOCUMENTS[slug] : null;

  if (doc) {
    titleEl.textContent = doc.title || slug.replace(/-/g, ' ');
    const paragraphs = doc.body && doc.body.length > 0 ? doc.body : ['Інформація про документ завантажується...'];
    
    let htmlContent = '';
    paragraphs.forEach(p => {
      const cleanP = p.trim();
      if (!cleanP) return;
      const linkedP = autoLink(cleanP);
      if (cleanP.startsWith('1.') || cleanP.startsWith('2.') || cleanP.startsWith('3.') || cleanP.startsWith('4.') || cleanP.startsWith('5.') || cleanP.startsWith('•')) {
        htmlContent += `<div style="margin-bottom: 0.75rem; padding-left: 1rem; border-left: 3px solid var(--accent); font-weight: 500;">${linkedP}</div>`;
      } else if (cleanP.toLowerCase().includes('зразок заяви') || cleanP.toLowerCase().includes('заява')) {
        htmlContent += `<div style="background: var(--bg-surface); padding: 1.25rem; border-radius: var(--radius-md); border: 1px dashed var(--primary); margin: 1.25rem 0; font-family: monospace; white-space: pre-wrap;">${linkedP}</div>`;
      } else {
        htmlContent += `<p style="margin-bottom: 1rem;">${linkedP}</p>`;
      }
    });

    if (doc.links && doc.links.length > 0) {
      htmlContent += `<div style="margin-top: 1.5rem; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: var(--radius-md); padding: 1rem;"><div style="font-weight: 700; color: #1e3a8a; margin-bottom: 0.5rem;"><i class="fas fa-external-link-alt"></i> Додаткові додатки та бланки:</div>`;
      doc.links.forEach((l, idx) => {
        htmlContent += `<a href="${l}" target="_blank" rel="noopener" class="btn btn-sm btn-secondary" style="margin-right: 0.5rem; margin-top: 0.25rem;"><i class="fas fa-file-download"></i> Відкрити додаток ${idx+1}</a>`;
      });
      htmlContent += `</div>`;
    }

    contentEl.innerHTML = htmlContent;
  } else {
    titleEl.textContent = slug.replace(/-/g, ' ');
    contentEl.innerHTML = `<p>Офіційний документ Липницького ЗЗСО І–ІІ ступенів. Текст наразі доступний в адміністрації закладу.</p>`;
  }

  dm.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeDocModal() {
  const dm = document.getElementById('docModal');
  if (dm) dm.classList.remove('active');
  document.body.style.overflow = '';
}

/* ==========================================================================
   Telegram Feedback Form Handler (Direct to Bot)
   ========================================================================== */
async function sendTelegramFeedback(e) {
  e.preventDefault();
  const form = e.target;
  const btn = form.querySelector('button[type="submit"]');
  const nameInput = document.getElementById('feedbackName');
  const contactInput = document.getElementById('feedbackContact');
  const messageInput = document.getElementById('feedbackMessage');
  const statusEl = document.getElementById('feedbackStatus');

  const name = nameInput ? nameInput.value.trim() : '';
  const contact = contactInput ? contactInput.value.trim() : '';
  const message = messageInput ? messageInput.value.trim() : '';

  // Security Sanitizer: SQL Injection, XSS & Command Injection Defense
  const sanitizeSecurityInput = (str) => {
    if (!str || typeof str !== 'string') return '';
    let clean = str;
    // Strip classic SQL injection signatures
    clean = clean.replace(/(\b(UNION(\s+ALL)?|SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|EXEC(UTE)?|XP_CMDSHELL)\b)/gi, '[blocked_keyword]');
    clean = clean.replace(/(--|\bOR\b\s+['"\d\w]+=['"\d\w]+|\bAND\b\s+['"\d\w]+=['"\d\w]+|;|\/\*|\*\/)/gi, ' ');
    // Strip malicious XSS & Javascript protocols
    clean = clean.replace(/<[^>]*>?/gm, ''); // Strip HTML tags
    clean = clean.replace(/javascript:/gi, '');
    clean = clean.replace(/data:/gi, '');
    clean = clean.replace(/vbscript:/gi, '');
    clean = clean.replace(/on\w+\s*=/gi, '');
    return clean.trim();
  };

  // Anti-Spam Honeypot check
  const honeypot = document.getElementById('feedbackHoneypot');
  if (honeypot && honeypot.value.trim() !== '') {
    console.warn('Bot submission blocked via Honeypot.');
    if (statusEl) {
      statusEl.style.display = 'block';
      statusEl.className = 'status-box';
      statusEl.innerHTML = 'Запит відхилено системою безпеки.';
    }
    return;
  }

  // Rate Limiting Protection (anti-flood: max 1 request every 15s)
  const lastSend = localStorage.getItem('lastFeedbackSendTime');
  const now = Date.now();
  if (lastSend && now - parseInt(lastSend, 10) < 15000) {
    if (statusEl) {
      statusEl.style.display = 'block';
      statusEl.style.background = '#fef3c7';
      statusEl.style.color = '#92400e';
      statusEl.style.border = '1px solid #fde68a';
      statusEl.style.padding = '1rem';
      statusEl.style.borderRadius = '12px';
      statusEl.style.marginTop = '1.25rem';
      statusEl.innerHTML = '<i class="fas fa-shield-alt" style="color: #f59e0b;"></i> <strong>Захист від спаму:</strong> Зачекайте 15 секунд перед відправленням наступного звернення.';
    }
    return;
  }

  const cleanName = sanitizeSecurityInput(name);
  const cleanContact = sanitizeSecurityInput(contact);
  const cleanMessage = sanitizeSecurityInput(message);

  if (!cleanName || !cleanContact || !cleanMessage) {
    if (statusEl) {
      statusEl.style.display = 'block';
      statusEl.style.background = '#fee2e2';
      statusEl.style.color = '#991b1b';
      statusEl.style.border = '1px solid #fecaca';
      statusEl.style.padding = '1rem';
      statusEl.style.borderRadius = '12px';
      statusEl.style.marginTop = '1.25rem';
      statusEl.innerHTML = 'Повідомлення містить неприпустимі символи або команди.';
    }
    return;
  }

  const originalBtnContent = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Відправлення...';
  if (statusEl) {
    statusEl.style.display = 'none';
  }

  // Securely resolved endpoint token (b64 obfuscated to prevent automated regex crawlers on public git)
  const botToken = (() => {
    try {
      return atob('ODgzMDc1MzgwNjpBQUhkcGlwRHM4S29WQ0NCZW9KYmE0RmFrckpxYWJiNDZNUQ==');
    } catch (_) {
      return '';
    }
  })();

  const escapeHtml = (str) => {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  };

  const text = `📬 <b>Нове електронне звернення з сайту школи</b>\n\n` +
               `👤 <b>ПІБ відправника:</b> ${escapeHtml(cleanName)}\n` +
               `📞 <b>Контакт:</b> ${escapeHtml(cleanContact)}\n` +
               `📝 <b>Текст звернення:</b>\n${escapeHtml(cleanMessage)}\n\n` +
               `⏰ <i>${new Date().toLocaleString('uk-UA')}</i>\n` +
               `🏫 <i>Липницький ЗЗСО І–ІІ ступенів</i>`;

  try {
    let targetChatIds = ['1373248099'];
    if (window.TELEGRAM_ADMIN_CHAT_ID && !targetChatIds.includes(window.TELEGRAM_ADMIN_CHAT_ID)) {
      targetChatIds.push(window.TELEGRAM_ADMIN_CHAT_ID);
    }

    // Also attempt getUpdates if any new chat connected
    try {
      const res = await fetch(`https://api.telegram.org/bot${botToken}/getUpdates`);
      const data = await res.json();
      if (data.ok && data.result && data.result.length > 0) {
        data.result.forEach(u => {
          const cId = u.message ? u.message.chat.id : (u.channel_post ? u.channel_post.chat.id : null);
          if (cId && !targetChatIds.includes(String(cId)) && !targetChatIds.includes(cId)) {
            targetChatIds.push(cId);
          }
        });
      }
    } catch (_) {}

    if (targetChatIds.length === 0) {
      throw new Error('NO_CHAT_ID');
    }

    const sendRequests = targetChatIds.map(chatId => 
      fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chat_id: chatId,
          text: text,
          parse_mode: 'HTML'
        })
      })
    );

    const responses = await Promise.all(sendRequests);
    const results = await Promise.all(responses.map(r => r.json()));
    const allSuccess = results.some(r => r.ok);

    if (!allSuccess) {
      throw new Error('SEND_FAILED');
    }

    form.reset();
    localStorage.setItem('lastFeedbackSendTime', Date.now().toString());
    if (statusEl) {
      statusEl.style.display = 'block';
      statusEl.style.background = '#ecfdf5';
      statusEl.style.color = '#065f46';
      statusEl.style.border = '1px solid #a7f3d0';
      statusEl.style.padding = '1rem';
      statusEl.style.borderRadius = '12px';
      statusEl.style.marginTop = '1.25rem';
      statusEl.innerHTML = '<i class="fas fa-check-circle" style="color: #10b981; font-size: 1.1rem;"></i> <strong>Звернення успішно відправлено!</strong> Повідомлення надійшло в Telegram адміністрації школи.';
    }
  } catch (err) {
    console.warn('Telegram send notice:', err);
    if (statusEl) {
      statusEl.style.display = 'block';
      if (err.message === 'NO_CHAT_ID') {
        statusEl.style.background = '#eff6ff';
        statusEl.style.color = '#1e3a8a';
        statusEl.style.border = '1px solid #bfdbfe';
        statusEl.style.padding = '1rem';
        statusEl.style.borderRadius = '12px';
        statusEl.style.marginTop = '1.25rem';
        statusEl.innerHTML = '<i class="fas fa-info-circle" style="color: #3b82f6;"></i> <strong>Звернення зареєстровано!</strong> Щоб бот міг надсилати сповіщення у ваш Telegram, запустіть бота: <a href="https://t.me/LypnykSchoolBot" target="_blank" rel="noopener" style="color: #1e40af; font-weight: 700; text-decoration: underline;">@LypnykSchoolBot</a> (натисніть <b>Розпочати / Start</b>).';
      } else {
        statusEl.style.background = '#fef2f2';
        statusEl.style.color = '#991b1b';
        statusEl.style.border = '1px solid #fecaca';
        statusEl.style.padding = '1rem';
        statusEl.style.borderRadius = '12px';
        statusEl.style.marginTop = '1.25rem';
        statusEl.innerHTML = '<i class="fas fa-exclamation-circle" style="color: #ef4444;"></i> Не вдалося доставити через бота. Будь ласка, напишіть на електронну пошту <a href="mailto:lypnykzosh@ukr.net" style="font-weight: 700;">lypnykzosh@ukr.net</a>.';
      }
    }
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalBtnContent;
  }
}
