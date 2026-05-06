import sqlite3
import os
import sys


def get_app_dir():
    """
    Returns the install directory of the app.
    Priority:
      1. INVOICES_APP_DIR environment variable (set by run.vbs / run.bat)
      2. install_path.txt file next to this script
      3. Directory of this script (fallback for development)
    """
    # 1. Environment variable set by launcher
    env_dir = os.environ.get('INVOICES_APP_DIR')
    if env_dir and os.path.isdir(env_dir):
        return env_dir

    # 2. install_path.txt written during installation
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path_file  = os.path.join(script_dir, 'install_path.txt')
    if os.path.exists(path_file):
        try:
            with open(path_file, 'r') as f:
                stored = f.read().strip()
            if stored and os.path.isdir(stored):
                return stored
        except Exception:
            pass

    # 3. Fallback — directory of this script
    return script_dir


def get_db_path():
    return os.path.join(get_app_dir(), 'invoices.db')


def get_backup_dir():
    d = os.path.join(get_app_dir(), 'backups')
    os.makedirs(d, exist_ok=True)
    return d


def get_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')      # crash-safe writes
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA synchronous=NORMAL')    # safe + faster than FULL
    return conn


def init_db():
    conn = get_connection()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS customers (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            address    TEXT    NOT NULL DEFAULT '',
            phone      TEXT    NOT NULL DEFAULT '',
            notes      TEXT    NOT NULL DEFAULT '',
            created_at TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT    NOT NULL UNIQUE,
            customer_id    INTEGER NOT NULL REFERENCES customers(id),
            date           TEXT    NOT NULL,
            currency       TEXT    NOT NULL DEFAULT 'USD',
            total_amount   REAL    NOT NULL DEFAULT 0,
            first_payment  REAL    NOT NULL DEFAULT 0,
            paid_amount    REAL    NOT NULL DEFAULT 0,
            remaining      REAL    NOT NULL DEFAULT 0,
            status         TEXT    NOT NULL DEFAULT 'unpaid',
            notes          TEXT    NOT NULL DEFAULT '',
            created_at     TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS invoice_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id  INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
            description TEXT    NOT NULL,
            quantity    REAL    NOT NULL DEFAULT 1,
            unit_price  REAL    NOT NULL DEFAULT 0,
            total       REAL    NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS payments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id  INTEGER NOT NULL REFERENCES invoices(id),
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            date        TEXT    NOT NULL,
            amount      REAL    NOT NULL DEFAULT 0,
            currency    TEXT    NOT NULL,
            method      TEXT    NOT NULL DEFAULT 'cash',
            note        TEXT    NOT NULL DEFAULT '',
            created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        );

        -- Autocomplete pool: grows automatically as new items are entered
        CREATE TABLE IF NOT EXISTS item_lookup (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT    NOT NULL UNIQUE COLLATE NOCASE,
            last_used   TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        );
    ''')
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────
# CUSTOMERS
# ─────────────────────────────────────────────────────────────────

def get_customers(search=''):
    conn = get_connection()
    if search:
        rows = conn.execute(
            "SELECT * FROM customers WHERE name LIKE ? ORDER BY name",
            (f'%{search}%',)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM customers ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_customer(cid):
    conn = get_connection()
    row = conn.execute("SELECT * FROM customers WHERE id=?", (cid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_customer(data):
    conn = get_connection()
    conn.execute(
        "INSERT INTO customers (name, address, phone, notes) VALUES (?,?,?,?)",
        (data['name'], data['address'], data['phone'], data['notes'])
    )
    conn.commit()
    conn.close()


def create_customer_return_id(data):
    """Same as create_customer but returns the new row id (used by AJAX modal)."""
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO customers (name, address, phone, notes) VALUES (?,?,?,?)",
        (data['name'], data['address'], data['phone'], data['notes'])
    )
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return new_id


def update_customer(cid, data):
    conn = get_connection()
    conn.execute(
        "UPDATE customers SET name=?, address=?, phone=?, notes=? WHERE id=?",
        (data['name'], data['address'], data['phone'], data['notes'], cid)
    )
    conn.commit()
    conn.close()


def get_customer_invoices(cid):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM invoices WHERE customer_id=? ORDER BY date DESC",
        (cid,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_customer_totals(cid):
    """Returns debt summary grouped by currency for one customer."""
    conn = get_connection()
    rows = conn.execute('''
        SELECT currency,
               SUM(total_amount) AS total_amount,
               SUM(paid_amount)  AS paid_amount,
               SUM(remaining)    AS remaining
        FROM invoices
        WHERE customer_id = ?
        GROUP BY currency
    ''', (cid,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_customers_autocomplete(q):
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name, phone FROM customers WHERE name LIKE ? ORDER BY name LIMIT 10",
        (f'%{q}%',)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────
# INVOICES
# ─────────────────────────────────────────────────────────────────

def get_invoices(status='', search=''):
    conn = get_connection()
    query = '''
        SELECT i.*, c.name AS customer_name
        FROM invoices i
        JOIN customers c ON i.customer_id = c.id
        WHERE 1=1
    '''
    params = []
    if status:
        query += ' AND i.status = ?'
        params.append(status)
    if search:
        query += ' AND (i.invoice_number LIKE ? OR c.name LIKE ?)'
        params += [f'%{search}%', f'%{search}%']
    query += ' ORDER BY i.date DESC, i.id DESC'
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_invoice(inv_id):
    conn = get_connection()
    row = conn.execute('''
        SELECT i.*, c.name AS customer_name
        FROM invoices i
        JOIN customers c ON i.customer_id = c.id
        WHERE i.id = ?
    ''', (inv_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def invoice_number_exists(number, exclude_id=None):
    conn = get_connection()
    if exclude_id:
        row = conn.execute(
            "SELECT id FROM invoices WHERE invoice_number=? AND id!=?",
            (number, exclude_id)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT id FROM invoices WHERE invoice_number=?", (number,)
        ).fetchone()
    conn.close()
    return row is not None


def _compute_status(total, paid):
    if paid >= total:
        return 'paid'
    if paid > 0:
        return 'partial'
    return 'unpaid'


def create_invoice(data):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO invoices
            (invoice_number, customer_id, date, currency,
             total_amount, first_payment, paid_amount, remaining, status, notes)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    ''', (
        data['invoice_number'], data['customer_id'], data['date'], data['currency'],
        data['total_amount'], data['first_payment'],
        data['paid_amount'], data['remaining'], data['status'], data['notes']
    ))
    invoice_id = c.lastrowid

    for item in data['items']:
        c.execute('''
            INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, total)
            VALUES (?,?,?,?,?)
        ''', (invoice_id, item['description'], item['quantity'],
              item['unit_price'], item['total']))
        # Auto-learn item for future autocomplete
        c.execute('''
            INSERT INTO item_lookup (description, last_used)
            VALUES (?, datetime('now','localtime'))
            ON CONFLICT(description)
            DO UPDATE SET last_used = datetime('now','localtime')
        ''', (item['description'],))

    conn.commit()
    conn.close()
    return invoice_id


def get_invoice_items(inv_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY id",
        (inv_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_invoice_payments(inv_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM payments WHERE invoice_id=? ORDER BY date DESC, id DESC",
        (inv_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────
# PAYMENTS
# ─────────────────────────────────────────────────────────────────

def add_payment(data):
    conn = get_connection()
    conn.execute('''
        INSERT INTO payments (invoice_id, customer_id, date, amount, currency, method, note)
        VALUES (?,?,?,?,?,?,?)
    ''', (data['invoice_id'], data['customer_id'], data['date'],
          data['amount'], data['currency'], data['method'], data['note']))

    # Recalculate invoice totals from payments table (safe against double-counting)
    conn.execute('''
        UPDATE invoices
        SET paid_amount = ROUND(first_payment + (
                SELECT COALESCE(SUM(amount), 0)
                FROM payments WHERE invoice_id = invoices.id
            ), 2),
            remaining   = ROUND(total_amount - first_payment - (
                SELECT COALESCE(SUM(amount), 0)
                FROM payments WHERE invoice_id = invoices.id
            ), 2),
            status      = CASE
                WHEN ROUND(total_amount - first_payment - (
                    SELECT COALESCE(SUM(amount), 0)
                    FROM payments WHERE invoice_id = invoices.id
                ), 2) <= 0 THEN 'paid'
                WHEN ROUND(first_payment + (
                    SELECT COALESCE(SUM(amount), 0)
                    FROM payments WHERE invoice_id = invoices.id
                ), 2) > 0 THEN 'partial'
                ELSE 'unpaid'
            END
        WHERE id = ?
    ''', (data['invoice_id'],))

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────
# AUTOCOMPLETE
# ─────────────────────────────────────────────────────────────────

def search_item_lookup(q):
    conn = get_connection()
    rows = conn.execute(
        '''SELECT description FROM item_lookup
           WHERE description LIKE ?
           ORDER BY last_used DESC LIMIT 10''',
        (f'%{q}%',)
    ).fetchall()
    conn.close()
    return [r['description'] for r in rows]


# ─────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────

def get_dashboard_stats():
    conn = get_connection()
    debt = conn.execute('''
        SELECT currency, SUM(remaining) AS remaining
        FROM invoices WHERE status != 'paid'
        GROUP BY currency
    ''').fetchall()

    counts = conn.execute('''
        SELECT
            COUNT(*) AS total,
            SUM(status='unpaid')  AS unpaid,
            SUM(status='partial') AS partial,
            SUM(status='paid')    AS paid
        FROM invoices
    ''').fetchone()

    total_customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    conn.close()

    return {
        'debt_by_currency': [dict(r) for r in debt],
        'total_invoices':   counts['total'],
        'unpaid_count':     counts['unpaid'],
        'partial_count':    counts['partial'],
        'paid_count':       counts['paid'],
        'total_customers':  total_customers,
    }


def get_recent_invoices(limit=10):
    conn = get_connection()
    rows = conn.execute('''
        SELECT i.*, c.name AS customer_name
        FROM invoices i
        JOIN customers c ON i.customer_id = c.id
        ORDER BY i.created_at DESC
        LIMIT ?
    ''', (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_customers_with_debt():
    conn = get_connection()
    rows = conn.execute('''
        SELECT c.id, c.name, c.phone,
               i.currency,
               SUM(i.remaining) AS total_remaining
        FROM customers c
        JOIN invoices i ON c.id = i.customer_id
        WHERE i.status != 'paid'
        GROUP BY c.id, i.currency
        ORDER BY total_remaining DESC
        LIMIT 20
    ''').fetchall()
    conn.close()
    return [dict(r) for r in rows]
