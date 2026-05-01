/**
 * app.js — Invoice System Client Logic
 * - Dark / Light theme toggle (persisted in localStorage)
 * - Autocomplete engine (items + customers)
 * - Dynamic invoice item rows with live price entry
 * - Live totals calculation
 * - New-customer modal (AJAX, no page navigation)
 */

'use strict';

// ─── THEME ─────────────────────────────────────────────────────

const THEME_KEY = 'inv-theme';

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  const btn   = document.getElementById('theme-toggle-btn');
  const icon  = document.getElementById('theme-icon');
  const label = document.getElementById('theme-label');
  if (icon)  icon.textContent  = theme === 'dark' ? '☀️' : '🌙';
  if (label && btn) {
    label.textContent = theme === 'dark'
      ? (btn.dataset.labelLight || '')   // currently dark → offer to switch to light
      : (btn.dataset.labelDark  || '');  // currently light → offer to switch to dark
  }
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'light';
  const next    = current === 'dark' ? 'light' : 'dark';
  localStorage.setItem(THEME_KEY, next);
  applyTheme(next);
}

function initTheme() {
  const saved = localStorage.getItem(THEME_KEY) || 'light';
  applyTheme(saved);
  const btn = document.getElementById('theme-toggle-btn');
  if (btn) btn.addEventListener('click', toggleTheme);
}


// ─── AUTOCOMPLETE ENGINE ────────────────────────────────────────

class Autocomplete {
  constructor(input, apiUrl, options = {}) {
    this.input   = input;
    this.apiUrl  = apiUrl;
    this.options = options;
    this._timer  = null;
    this._listEl = null;
    this._build();
    this._attach();
  }

  _build() {
    const wrap = document.createElement('div');
    wrap.className = 'autocomplete-wrap';
    this.input.parentNode.insertBefore(wrap, this.input);
    wrap.appendChild(this.input);
    this._listEl = document.createElement('div');
    this._listEl.className = 'autocomplete-list';
    wrap.appendChild(this._listEl);
  }

  _attach() {
    this.input.addEventListener('input', () => {
      clearTimeout(this._timer);
      this._timer = setTimeout(() => this._fetch(), 220);
    });
    document.addEventListener('click', (e) => {
      if (!this._listEl.contains(e.target) && e.target !== this.input) this._hide();
    });
    this.input.addEventListener('keydown', (e) => {
      const items  = [...this._listEl.querySelectorAll('.autocomplete-item')];
      const active = this._listEl.querySelector('.autocomplete-item.focused');
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        const next = active ? active.nextElementSibling : items[0];
        if (next) { active?.classList.remove('focused'); next.classList.add('focused'); }
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        const prev = active ? active.previousElementSibling : items[items.length - 1];
        if (prev) { active?.classList.remove('focused'); prev.classList.add('focused'); }
      } else if (e.key === 'Enter' && active) {
        e.preventDefault(); active.click();
      } else if (e.key === 'Escape') {
        this._hide();
      }
    });
  }

  async _fetch() {
    const q = this.input.value.trim();
    if (q.length < 1) { this._hide(); return; }
    try {
      const res   = await fetch(`${this.apiUrl}?q=${encodeURIComponent(q)}`);
      const items = await res.json();
      this._render(items, q);
    } catch (_) {}
  }

  _render(items, q) {
    if (!items.length) { this._hide(); return; }
    this._listEl.innerHTML = '';
    items.forEach(item => {
      const el = document.createElement('div');
      el.className = 'autocomplete-item';
      el.innerHTML = this.options.renderLabel
        ? this.options.renderLabel(item, q)
        : highlight(this._str(item), q);
      el.addEventListener('mousedown', (e) => e.preventDefault());
      el.addEventListener('click', () => {
        this.input.value = this.options.getValue ? this.options.getValue(item) : this._str(item);
        this._hide();
        this.options.onSelect?.(this.input.value, item);
      });
      this._listEl.appendChild(el);
    });
    this._listEl.classList.add('show');
  }

  _str(item) { return typeof item === 'string' ? item : (item.name || item.description || ''); }
  _hide()    { this._listEl.classList.remove('show'); }
}


// ─── CUSTOMER AUTOCOMPLETE (invoice form) ──────────────────────

function initCustomerAutocomplete() {
  const nameInput = document.getElementById('customer-search');
  const idInput   = document.getElementById('customer_id');
  if (!nameInput || !idInput) return;

  new Autocomplete(nameInput, '/api/autocomplete/customers', {
    renderLabel: (item, q) => {
      const name  = highlight(item.name, q);
      const phone = item.phone
        ? `<span class="text-muted" style="font-size:12px;margin-right:8px">${item.phone}</span>`
        : '';
      return `${name}${phone}`;
    },
    getValue:  (item) => item.name,
    onSelect:  (val, item) => {
      idInput.value = item.id;
    },
  });

  // Clear customer_id if user edits the name field manually
  nameInput.addEventListener('input', () => {
    idInput.value = '';
  });
}


// ─── INVOICE ITEMS ─────────────────────────────────────────────

let _rowIdx = 0;

function addItemRow(data = {}) {
  const tbody = document.getElementById('items-tbody');
  if (!tbody) return;

  const i   = _rowIdx++;
  const row = document.createElement('tr');
  row.dataset.rowIdx = i;

  row.innerHTML = `
    <td style="min-width:240px;position:relative">
      <input type="text"
             name="items[${i}][description]"
             class="item-desc"
             placeholder="${document.getElementById('item-desc-placeholder')?.dataset.ph || ''}"
             value="${escHtml(data.description || '')}"
             autocomplete="off">
      <div class="autocomplete-list" style="position:absolute;top:100%;right:0;left:0;z-index:300"></div>
    </td>
    <td style="width:95px">
      <input type="number"
             name="items[${i}][quantity]"
             class="item-qty"
             value="${data.quantity ?? 1}"
             min="0.01" step="0.01" lang="en">
    </td>
    <td style="width:140px">
      <input type="number"
             name="items[${i}][unit_price]"
             class="item-price"
             value="${data.unit_price ?? ''}"
             min="0" step="0.01" lang="en"
             placeholder="0">
    </td>
    <td class="td-total" id="rtotal-${i}">0</td>
    <td class="td-action">
      <button type="button" class="btn btn-danger btn-sm btn-icon remove-row" title="حذف">✕</button>
    </td>
  `;

  tbody.appendChild(row);

  // Attach description autocomplete
  const descInput = row.querySelector('.item-desc');
  const listEl    = row.querySelector('.autocomplete-list');
  _attachItemAC(descInput, listEl);

  // Recalculate on qty/price change
  row.querySelector('.item-qty').addEventListener('input',   () => _updateRowTotal(row));
  row.querySelector('.item-price').addEventListener('input', () => _updateRowTotal(row));

  // Remove row
  row.querySelector('.remove-row').addEventListener('click', () => {
    row.remove();
    _updateGrandTotal();
  });

  if (data.unit_price) _updateRowTotal(row);
}

function _attachItemAC(input, listEl) {
  let timer;
  input.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      const q = input.value.trim();
      if (q.length < 1) { listEl.classList.remove('show'); return; }
      try {
        const res   = await fetch(`/api/autocomplete/items?q=${encodeURIComponent(q)}`);
        const items = await res.json();
        if (!items.length) { listEl.classList.remove('show'); return; }
        listEl.innerHTML = '';
        items.forEach(desc => {
          const el = document.createElement('div');
          el.className = 'autocomplete-item';
          el.innerHTML = highlight(desc, q);
          el.addEventListener('mousedown', (e) => e.preventDefault());
          el.addEventListener('click', () => {
            input.value = desc;
            listEl.classList.remove('show');
            // Focus price field after selecting description
            input.closest('tr')?.querySelector('.item-price')?.focus();
          });
          listEl.appendChild(el);
        });
        listEl.classList.add('show');
      } catch (_) {}
    }, 200);
  });
  document.addEventListener('click', (e) => {
    if (!listEl.contains(e.target) && e.target !== input) listEl.classList.remove('show');
  });
}

function _updateRowTotal(row) {
  const qty   = parseFloat(row.querySelector('.item-qty')?.value)   || 0;
  const price = parseFloat(row.querySelector('.item-price')?.value) || 0;
  const total = Math.round(qty * price * 100) / 100;
  const idx   = row.dataset.rowIdx;
  const el    = document.getElementById(`rtotal-${idx}`);
  if (el) el.textContent = fmtNum(total);
  _updateGrandTotal();
}

function _updateGrandTotal() {
  let total = 0;
  document.querySelectorAll('#items-tbody tr').forEach(row => {
    const qty   = parseFloat(row.querySelector('.item-qty')?.value)   || 0;
    const price = parseFloat(row.querySelector('.item-price')?.value) || 0;
    total += qty * price;
  });
  total = Math.round(total * 100) / 100;

  const fp        = Math.round((parseFloat(document.getElementById('first_payment')?.value) || 0) * 100) / 100;
  const remaining = Math.round(Math.max(0, total - fp) * 100) / 100;

  _setText('summary-total',     fmtNum(total));
  _setText('summary-fp',        fmtNum(fp));
  _setText('summary-remaining', fmtNum(remaining));
}

function _setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}


// ─── NEW CUSTOMER MODAL ─────────────────────────────────────────

function initCustomerModal() {
  const overlay    = document.getElementById('new-customer-modal');
  const form       = document.getElementById('invoice-form');
  const idInput    = document.getElementById('customer_id');
  const nameInput  = document.getElementById('customer-search');
  const modalName  = document.getElementById('modal-customer-name');
  const modalErr   = document.getElementById('modal-error');
  const closeBtn   = document.getElementById('modal-close-btn');
  const cancelBtn  = document.getElementById('modal-cancel-btn');
  const saveBtn    = document.getElementById('modal-save-btn');

  if (!overlay || !form) return;

  let _pendingSubmit = false;

  // Intercept invoice form submit
  form.addEventListener('submit', (e) => {
    if (_pendingSubmit) return; // already validated — let it through

    // If customer_id is empty, a new customer must be created first
    if (!idInput.value || idInput.value === '') {
      e.preventDefault();
      _openModal();
    }
  });

  function _openModal() {
    // Pre-fill name from what user typed
    if (modalName && nameInput) modalName.value = nameInput.value.trim();
    if (modalErr) { modalErr.textContent = ''; modalErr.classList.remove('show'); }
    overlay.classList.add('show');
    modalName?.focus();
  }

  function _closeModal() {
    overlay.classList.remove('show');
  }

  closeBtn?.addEventListener('click', _closeModal);
  cancelBtn?.addEventListener('click', _closeModal);

  // Close on overlay background click
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) _closeModal();
  });

  // Save new customer via AJAX then submit invoice
  saveBtn?.addEventListener('click', async () => {
    const name    = document.getElementById('modal-customer-name')?.value.trim()   || '';
    const phone   = document.getElementById('modal-customer-phone')?.value.trim()  || '';
    const address = document.getElementById('modal-customer-address')?.value.trim()|| '';
    const notes   = document.getElementById('modal-customer-notes')?.value.trim()  || '';

    if (!name) {
      if (modalErr) { modalErr.textContent = saveBtn.dataset.errName || 'الاسم مطلوب'; modalErr.classList.add('show'); }
      return;
    }

    saveBtn.disabled = true;
    saveBtn.textContent = '...';

    try {
      const res  = await fetch('/api/customers/create', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ name, phone, address, notes }),
      });
      const json = await res.json();

      if (!res.ok) {
        if (modalErr) { modalErr.textContent = json.error || 'خطأ'; modalErr.classList.add('show'); }
        saveBtn.disabled = false;
        saveBtn.textContent = saveBtn.dataset.label || 'حفظ';
        return;
      }

      // Success — populate hidden fields and re-submit the invoice form
      idInput.value   = json.id;
      if (nameInput) nameInput.value = json.name;
      _closeModal();
      _pendingSubmit = true;
      form.submit();

    } catch (err) {
      if (modalErr) { modalErr.textContent = 'حدث خطأ — حاول مجدداً'; modalErr.classList.add('show'); }
      saveBtn.disabled = false;
      saveBtn.textContent = saveBtn.dataset.label || 'حفظ';
    }
  });

  // Allow Enter key in modal fields to trigger save
  overlay.querySelectorAll('input').forEach(inp => {
    inp.addEventListener('keydown', (e) => { if (e.key === 'Enter') saveBtn?.click(); });
  });
}


// ─── UTILS ─────────────────────────────────────────────────────

function fmtNum(n) {
  const v = parseFloat(n);
  if (isNaN(v)) return '0';
  if (v === Math.floor(v)) return Math.floor(v).toLocaleString('en');
  return v.toLocaleString('en', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function highlight(text, q) {
  if (!q) return text;
  const re = new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  return text.replace(re, '<mark>$1</mark>');
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}


// ─── INIT ───────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Theme
  initTheme();

  // Add item button
  document.getElementById('add-item-btn')?.addEventListener('click', () => addItemRow());

  // First payment live recalc
  document.getElementById('first_payment')?.addEventListener('input', _updateGrandTotal);

  // Start with one empty row on new invoice
  const tbody = document.getElementById('items-tbody');
  if (tbody && tbody.children.length === 0) addItemRow();

  // Autocomplete
  initCustomerAutocomplete();

  // New customer modal
  initCustomerModal();

  // Active nav
  const seg = window.location.pathname.split('/')[1] || '';
  document.querySelectorAll('.nav-item[data-page]').forEach(el => {
    if (el.dataset.page === seg) el.classList.add('active');
  });

  // Set today's date on any date input that is empty
  document.querySelectorAll('input[type="date"]').forEach(inp => {
    if (!inp.value) inp.value = new Date().toISOString().split('T')[0];
  });

  // Flash auto-dismiss after 4s
  setTimeout(() => {
    document.querySelectorAll('.flash').forEach(el => {
      el.style.transition = 'opacity 0.4s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 400);
    });
  }, 4000);
});
