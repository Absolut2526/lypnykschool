import glob
import re
import os
import urllib.parse
import json

# 1. Update main.js with openDocModal
main_js_path = '/Users/pc/Documents/school_site/assets/js/main.js'
with open(main_js_path, 'r', encoding='utf-8') as f:
    main_js = f.read()

doc_modal_code = '''
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
      if (cleanP.startsWith('1.') || cleanP.startsWith('2.') || cleanP.startsWith('3.') || cleanP.startsWith('4.') || cleanP.startsWith('5.') || cleanP.startsWith('•')) {
        htmlContent += `<div style="margin-bottom: 0.75rem; padding-left: 1rem; border-left: 3px solid var(--accent); font-weight: 500;">${cleanP}</div>`;
      } else if (cleanP.toLowerCase().includes('зразок заяви') || cleanP.toLowerCase().includes('заява')) {
        htmlContent += `<div style="background: var(--bg-surface); padding: 1.25rem; border-radius: var(--radius-md); border: 1px dashed var(--primary); margin: 1.25rem 0; font-family: monospace; white-space: pre-wrap;">${cleanP}</div>`;
      } else {
        htmlContent += `<p style="margin-bottom: 1rem;">${cleanP}</p>`;
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
    contentEl.innerHTML = `<p>Офіційний документ Липницького ЗЗСО І-ІІІ ступенів. Текст наразі доступний в адміністрації закладу.</p>`;
  }

  dm.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeDocModal() {
  const dm = document.getElementById('docModal');
  if (dm) dm.classList.remove('active');
  document.body.style.overflow = '';
}
'''

if 'openDocModal' not in main_js:
    main_js += '\n' + doc_modal_code
    with open(main_js_path, 'w', encoding='utf-8') as f:
        f.write(main_js)
    print('Updated main.js with document modal reader!')

# 2. Update HTML files
for hfile in glob.glob('/Users/pc/Documents/school_site/*.html'):
    with open(hfile, 'r', encoding='utf-8') as f:
        html_text = f.read()

    # Add documents-data.js script if missing
    if 'documents-data.js' not in html_text:
        html_text = html_text.replace('<script src="assets/js/main.js"></script>', '<script src="assets/js/documents-data.js"></script>\n  <script src="assets/js/main.js"></script>')
        html_text = html_text.replace('<script src="script.js"></script>', '<script src="assets/js/documents-data.js"></script>\n  <script src="script.js"></script>')

    def replacer(match):
        full_url = match.group(1)
        raw_slug = full_url.rstrip('/').split('/')[-1]
        slug = urllib.parse.unquote(raw_slug)
        return f'href="javascript:void(0)" onclick="openDocModal(\'{slug}\')"'

    updated_html = re.sub(r'href=[\"\'](https://sites\.google\.com/[^\s\"\'><]+)[\"\']', replacer, html_text)
    updated_html = re.sub(r'(onclick=\"openDocModal\([^\)]+\)\")\s+target=\"_blank\"\s+rel=\"noopener\"', r'\1', updated_html)

    with open(hfile, 'w', encoding='utf-8') as f:
        f.write(updated_html)

print('Successfully updated all HTML files to open documents internally without external redirect!')
