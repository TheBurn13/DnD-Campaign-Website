/* ═══════════════════════════════════════════════════
   THE COMPENDIUM — Core JS
═══════════════════════════════════════════════════ */

// ─── Toast ────────────────────────────────────────

function showToast(msg, duration = 3000) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove('show'), duration);
}

// ─── API Helper ───────────────────────────────────

async function api(method, url, body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || 'Something went wrong');
  return data;
}

// ─── Auth State ───────────────────────────────────

async function loadNavAuth() {
  const navDashboard = document.getElementById('navDashboard');
  const navLogout    = document.getElementById('navLogout');
  const navLogin     = document.getElementById('navLogin');
  const navUser      = document.getElementById('navUser');

  try {
    const me = await api('GET', '/api/me');
    if (navDashboard) {
      navDashboard.style.display = '';
      navDashboard.href = me.role === 'dm' ? '/dm' : '/dashboard';
      navDashboard.textContent = me.role === 'dm' ? 'The Party' : 'My Characters';
    }
    if (navLogout) navLogout.style.display = '';
    if (navLogin)  navLogin.style.display = 'none';
    if (navUser)   navUser.textContent = me.role === 'dm' ? '⚔ ' + me.username : me.username;
  } catch {
    if (navDashboard) navDashboard.style.display = 'none';
    if (navLogout)    navLogout.style.display = 'none';
    if (navLogin)     navLogin.style.display = '';
    if (navUser)      navUser.textContent = '';
  }
}

// ─── Modifier Calculation ─────────────────────────

function getModifier(score) {
  return Math.floor((score - 10) / 2);
}

function formatMod(mod) {
  return mod >= 0 ? `+${mod}` : `${mod}`;
}

// ─── Modal ────────────────────────────────────────

function createModal({ title, content, onConfirm, confirmLabel = 'Confirm', confirmClass = 'btn-primary' }) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `
    <div class="modal-box">
      <div class="modal-title">${title}</div>
      <div>${content}</div>
      <div class="modal-actions">
        <button class="btn btn-secondary" id="modalCancel">Cancel</button>
        <button class="btn ${confirmClass}" id="modalConfirm">${confirmLabel}</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  overlay.querySelector('#modalCancel').addEventListener('click', () => overlay.remove());
  overlay.querySelector('#modalConfirm').addEventListener('click', () => {
    onConfirm();
    overlay.remove();
  });
  overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
  return overlay;
}

// ─── Tabs ─────────────────────────────────────────

function initTabs() {
  document.querySelectorAll('.sheet-tabs').forEach(tabBar => {
    tabBar.querySelectorAll('.sheet-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        const panel = tab.dataset.panel;
        tabBar.querySelectorAll('.sheet-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        document.querySelectorAll('.tab-panel').forEach(p => {
          p.classList.toggle('active', p.id === panel);
        });
      });
    });
  });
}

// ─── Init ─────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  loadNavAuth();
  initTabs();
});
