import json
import os
import threading
import webbrowser

from flask import (Flask, render_template, request,
                   redirect, url_for, jsonify, flash)

import database as db
import backup

app = Flask(__name__)
app.secret_key = 'inv-app-secret-key-2026-xZ9'

# ─────────────────────────────────────────────────────────────────
# LOCALIZATION
# ─────────────────────────────────────────────────────────────────

def _load_lang():
    lang_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'localization-ar.json')
    with open(lang_path, encoding='utf-8') as f:
        return json.load(f)

LANG = _load_lang()

@app.context_processor
def inject_lang():
    return {'t': LANG}

# ─────────────────────────────────────────────────────────────────
# TEMPLATE FILTERS
# ─────────────────────────────────────────────────────────────────

CURRENCY_SYMBOLS = {'USD': '$', 'SYP_NEW': 'ل.س ج', 'SYP_OLD': 'ل.س ق'}

@app.template_filter('currency_symbol')
def currency_symbol(code):
    return CURRENCY_SYMBOLS.get(code, code)

@app.template_filter('status_label')
def status_label_filter(code):
    return LANG['status'].get(code, code)

@app.template_filter('fmt_number')
def fmt_number(value):
    try:
        v = float(value)
        if v == int(v):
            return f'{int(v):,}'
        return f'{v:,.2f}'
    except (ValueError, TypeError):
        return value

# ─────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────

@app.route('/')
def dashboard():
    stats           = db.get_dashboard_stats()
    recent_invoices = db.get_recent_invoices(10)
    customers_debt  = db.get_customers_with_debt()
    last_backup     = backup.get_last_backup_info()
    return render_template('dashboard.html', stats=stats,
                           recent_invoices=recent_invoices,
                           customers_debt=customers_debt,
                           last_backup=last_backup)

# ─────────────────────────────────────────────────────────────────
# CUSTOMERS
# ─────────────────────────────────────────────────────────────────

@app.route('/customers')
def customers_list():
    search    = request.args.get('q', '').strip()
    customers = db.get_customers(search)
    return render_template('customers/list.html', customers=customers, search=search)


@app.route('/customers/new', methods=['GET', 'POST'])
def customer_new():
    if request.method == 'POST':
        data = _customer_from_form()
        db.create_customer(data)
        backup.record_change()
        flash(LANG['messages']['customer_created'], 'success')
        return redirect(url_for('customers_list'))
    return render_template('customers/form.html', customer=None, title=LANG['customers']['new_title'])


@app.route('/customers/<int:cid>')
def customer_detail(cid):
    customer = db.get_customer(cid)
    if not customer:
        flash(LANG['messages']['customer_not_found'], 'error')
        return redirect(url_for('customers_list'))
    invoices = db.get_customer_invoices(cid)
    totals   = db.get_customer_totals(cid)
    return render_template('customers/detail.html', customer=customer, invoices=invoices, totals=totals)


@app.route('/customers/<int:cid>/edit', methods=['GET', 'POST'])
def customer_edit(cid):
    customer = db.get_customer(cid)
    if not customer:
        return redirect(url_for('customers_list'))
    if request.method == 'POST':
        db.update_customer(cid, _customer_from_form())
        backup.record_change()
        flash(LANG['messages']['customer_updated'], 'success')
        return redirect(url_for('customer_detail', cid=cid))
    return render_template('customers/form.html', customer=customer, title=LANG['customers']['edit_title'])


@app.route('/api/customers/create', methods=['POST'])
def api_customer_create():
    """AJAX endpoint — called by the inline new-customer modal on the invoice form."""
    payload = request.get_json() or {}
    data = {
        'name':    payload.get('name', '').strip(),
        'phone':   payload.get('phone', '').strip(),
        'address': payload.get('address', '').strip(),
        'notes':   payload.get('notes', '').strip(),
    }
    if not data['name']:
        return jsonify({'error': LANG['modal']['err_name_required']}), 400
    cid = db.create_customer_return_id(data)
    backup.record_change()
    return jsonify({'id': cid, 'name': data['name']})


def _customer_from_form():
    return {
        'name':    request.form.get('name', '').strip(),
        'address': request.form.get('address', '').strip(),
        'phone':   request.form.get('phone', '').strip(),
        'notes':   request.form.get('notes', '').strip(),
    }

# ─────────────────────────────────────────────────────────────────
# INVOICES
# ─────────────────────────────────────────────────────────────────

@app.route('/invoices')
def invoices_list():
    status   = request.args.get('status', '')
    search   = request.args.get('q', '').strip()
    invoices = db.get_invoices(status, search)
    return render_template('invoices/list.html', invoices=invoices, status=status, search=search)


@app.route('/invoices/new', methods=['GET', 'POST'])
def invoice_new():
    if request.method == 'POST':
        result = _build_invoice_from_form()
        if result['error']:
            flash(result['error'], 'error')
            return render_template('invoices/form.html', invoice=None, customers=db.get_customers(''))
        inv_id = db.create_invoice(result['data'])
        backup.record_change()
        flash(LANG['messages']['invoice_created'], 'success')
        return redirect(url_for('invoice_detail', inv_id=inv_id))
    return render_template('invoices/form.html', invoice=None, customers=db.get_customers(''))


@app.route('/invoices/<int:inv_id>')
def invoice_detail(inv_id):
    invoice = db.get_invoice(inv_id)
    if not invoice:
        flash(LANG['messages']['invoice_not_found'], 'error')
        return redirect(url_for('invoices_list'))
    items    = db.get_invoice_items(inv_id)
    payments = db.get_invoice_payments(inv_id)
    return render_template('invoices/detail.html', invoice=invoice, items=items, payments=payments)


@app.route('/invoices/<int:inv_id>/payment', methods=['POST'])
def add_payment(inv_id):
    invoice = db.get_invoice(inv_id)
    if not invoice:
        return redirect(url_for('invoices_list'))
    try:
        amount = round(float(request.form.get('amount', 0)), 2)
    except ValueError:
        flash(LANG['errors']['invalid_amount'], 'error')
        return redirect(url_for('invoice_detail', inv_id=inv_id))
    if amount <= 0:
        flash(LANG['errors']['amount_zero'], 'error')
        return redirect(url_for('invoice_detail', inv_id=inv_id))
    if amount > invoice['remaining']:
        flash(LANG['errors']['amount_exceeds'], 'error')
        return redirect(url_for('invoice_detail', inv_id=inv_id))
    db.add_payment({
        'invoice_id':  inv_id,
        'customer_id': invoice['customer_id'],
        'date':        request.form.get('date', ''),
        'amount':      amount,
        'currency':    invoice['currency'],
        'method':      request.form.get('method', 'cash'),
        'note':        request.form.get('note', '').strip(),
    })
    backup.record_change()
    flash(LANG['messages']['payment_added'], 'success')
    return redirect(url_for('invoice_detail', inv_id=inv_id))


def _build_invoice_from_form():
    inv_number = request.form.get('invoice_number', '').strip()
    if not inv_number:
        return {'error': LANG['errors']['inv_number_required'], 'data': None}
    if db.invoice_number_exists(inv_number):
        return {'error': f"{LANG['errors']['inv_number_exists']}: {inv_number}", 'data': None}
    try:
        customer_id = int(request.form.get('customer_id', 0))
        if customer_id <= 0: raise ValueError
    except ValueError:
        return {'error': LANG['errors']['no_customer'], 'data': None}

    items, i = [], 0
    while True:
        desc = request.form.get(f'items[{i}][description]', '').strip()
        if not desc: break
        try:
            qty   = round(float(request.form.get(f'items[{i}][quantity]', 1)), 4)
            price = round(float(request.form.get(f'items[{i}][unit_price]', 0)), 2)
        except (ValueError, TypeError):
            qty, price = 1, 0
        items.append({'description': desc, 'quantity': qty, 'unit_price': price, 'total': round(qty * price, 2)})
        i += 1

    if not items:
        return {'error': LANG['errors']['no_items'], 'data': None}

    total_amount = round(sum(it['total'] for it in items), 2)
    try:
        first_payment = round(float(request.form.get('first_payment', 0) or 0), 2)
    except ValueError:
        first_payment = 0

    if first_payment > total_amount:
        return {'error': LANG['errors']['first_payment_exceeds'], 'data': None}

    paid_amount = first_payment
    remaining   = round(total_amount - first_payment, 2)
    status = 'paid' if remaining <= 0 else ('partial' if paid_amount > 0 else 'unpaid')

    return {'error': None, 'data': {
        'invoice_number': inv_number, 'customer_id': customer_id,
        'date': request.form.get('date', ''), 'currency': request.form.get('currency', 'USD'),
        'total_amount': total_amount, 'first_payment': first_payment,
        'paid_amount': paid_amount, 'remaining': remaining,
        'status': status, 'notes': request.form.get('notes', '').strip(), 'items': items,
    }}

# ─────────────────────────────────────────────────────────────────
# AUTOCOMPLETE
# ─────────────────────────────────────────────────────────────────

@app.route('/api/autocomplete/items')
def api_autocomplete_items():
    q = request.args.get('q', '').strip()
    return jsonify(db.search_item_lookup(q))

@app.route('/api/autocomplete/customers')
def api_autocomplete_customers():
    q = request.args.get('q', '').strip()
    return jsonify(db.search_customers_autocomplete(q))

# ─────────────────────────────────────────────────────────────────
# BACKUP
# ─────────────────────────────────────────────────────────────────

@app.route('/backup', methods=['POST'])
def manual_backup():
    path = backup.do_manual_backup()
    if path:
        filename = os.path.basename(path)
        flash(f"{LANG['messages']['backup_done']}: {filename}", 'success')
    else:
        flash(LANG['messages']['backup_failed'], 'error')
    return redirect(request.referrer or url_for('dashboard'))

# ─────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────

# Port 5001 — port 5000 is blocked by macOS AirPlay Receiver.
# On Windows this makes no difference — both ports work fine.
PORT = 5001

def open_browser():
    webbrowser.open(f'http://127.0.0.1:{PORT}')

if __name__ == '__main__':
    db.init_db()
    backup.init_backup()
    threading.Timer(1.2, open_browser).start()
    app.run(debug=False, port=PORT, use_reloader=False, host='127.0.0.1')
