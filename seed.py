"""
seed.py — Fill the database with realistic test data.
Run once: python3 seed.py
Safe to re-run: clears existing data first.
"""

import sqlite3
import os
import sys

# ── Make sure we can import database.py from same folder ──────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import database as db

def clear_and_seed():
    # Init schema first
    db.init_db()

    conn = db.get_connection()

    # ── Clear existing data (order matters for FK constraints) ──
    conn.execute("DELETE FROM payments")
    conn.execute("DELETE FROM invoice_items")
    conn.execute("DELETE FROM invoices")
    conn.execute("DELETE FROM customers")
    conn.execute("DELETE FROM item_lookup")
    conn.execute("DELETE FROM sqlite_sequence")   # reset autoincrement
    conn.commit()
    conn.close()

    print("✓ Cleared existing data")

    # ── CUSTOMERS ───────────────────────────────────────────────
    customers = [
        {"name": "أحمد الخطيب",    "phone": "0991234567", "address": "حلب — الميدان",        "notes": "زبون دائم"},
        {"name": "محمد علي حسن",   "phone": "0981234567", "address": "حلب — الشهباء",        "notes": ""},
        {"name": "خالد المصطفى",   "phone": "0971234567", "address": "حلب — العزيزية",       "notes": "يفضل التواصل مساءً"},
        {"name": "سامر الرفاعي",   "phone": "0961234567", "address": "حلب — السريان",        "notes": ""},
        {"name": "يوسف الإبراهيم", "phone": "0951234567", "address": "حلب — حمص الصغيرة",   "notes": "شركة مقاولات"},
        {"name": "حسام الدين نور", "phone": "0941234567", "address": "إدلب — مركز المدينة", "notes": ""},
        {"name": "رامي الشيخ",     "phone": "0931234567", "address": "حلب — بستان الباشا",  "notes": "زبون جديد"},
    ]

    customer_ids = []
    for c in customers:
        cid = db.create_customer_return_id(c)
        customer_ids.append(cid)
    print(f"✓ Created {len(customers)} customers")

    # ── HELPER ──────────────────────────────────────────────────
    def make_invoice(number, cid, date, currency, items, first_payment=0, notes=""):
        total = round(sum(it["quantity"] * it["unit_price"] for it in items), 2)
        for it in items:
            it["total"] = round(it["quantity"] * it["unit_price"], 2)
        first_payment = round(first_payment, 2)
        paid    = first_payment
        remaining = round(total - paid, 2)
        status  = "paid" if remaining <= 0 else ("partial" if paid > 0 else "unpaid")
        return db.create_invoice({
            "invoice_number": number,
            "customer_id":    cid,
            "date":           date,
            "currency":       currency,
            "total_amount":   total,
            "first_payment":  first_payment,
            "paid_amount":    paid,
            "remaining":      remaining,
            "status":         status,
            "notes":          notes,
            "items":          items,
        })

    def pay(inv_id, cid, date, amount, currency, method="cash", note=""):
        db.add_payment({
            "invoice_id":  inv_id,
            "customer_id": cid,
            "date":        date,
            "amount":      round(amount, 2),
            "currency":    currency,
            "method":      method,
            "note":        note,
        })

    c = customer_ids  # shorthand: c[0]=أحمد, c[1]=محمد, ...

    # ── INVOICES ────────────────────────────────────────────────

    # ── أحمد الخطيب — USD, مسددة بالكامل ─────────────────────
    inv1 = make_invoice("2026-001", c[0], "2026-01-10", "USD", [
        {"description": "لوحة شمسية 400W",   "quantity": 4,   "unit_price": 120.00},
        {"description": "إنفرتر 3KW هايبرد", "quantity": 1,   "unit_price": 350.00},
        {"description": "كابل شمسي 6mm — متر","quantity": 20,  "unit_price": 2.50},
    ], first_payment=200.00, notes="تركيب منزلي")
    pay(inv1, c[0], "2026-02-01", 300.00, "USD", "sham_cash", "تحويل رقم 44512")
    pay(inv1, c[0], "2026-02-20", 280.00, "USD", "cash")

    # ── أحمد الخطيب — USD, جزئية ──────────────────────────────
    inv2 = make_invoice("2026-008", c[0], "2026-03-05", "USD", [
        {"description": "بطارية ليثيوم 100Ah",  "quantity": 2, "unit_price": 280.00},
        {"description": "حامل لوحات — 4 وحدة", "quantity": 1, "unit_price": 95.00},
    ], first_payment=150.00)
    pay(inv2, c[0], "2026-03-20", 200.00, "USD", "cash")

    # ── محمد علي — ليرة جديدة, معلقة ─────────────────────────
    inv3 = make_invoice("2026-002", c[1], "2026-01-15", "SYP_NEW", [
        {"description": "قاطع كهربائي 63A",    "quantity": 3,  "unit_price": 45000},
        {"description": "علبة توزيع 12 خط",    "quantity": 1,  "unit_price": 120000},
        {"description": "سلك نحاس 4mm — متر",  "quantity": 50, "unit_price": 3500},
    ])

    # ── محمد علي — ليرة جديدة, جزئية ─────────────────────────
    inv4 = make_invoice("2026-009", c[1], "2026-03-12", "SYP_NEW", [
        {"description": "لوحة شمسية 550W",      "quantity": 6, "unit_price": 380000},
        {"description": "إنفرتر 5KW ثلاثي",    "quantity": 1, "unit_price": 850000},
        {"description": "بطارية جل 200Ah",      "quantity": 4, "unit_price": 220000},
    ], first_payment=500000)
    pay(inv4, c[1], "2026-04-01", 300000, "SYP_NEW", "sham_cash", "تحويل شام كاش")

    # ── خالد المصطفى — USD, مسددة ─────────────────────────────
    inv5 = make_invoice("2026-003", c[2], "2026-01-22", "USD", [
        {"description": "لوحة شمسية 400W",      "quantity": 8,  "unit_price": 118.00},
        {"description": "إنفرتر 6KW أوف غريد", "quantity": 1,  "unit_price": 520.00},
        {"description": "بطارية ليثيوم 200Ah",  "quantity": 4,  "unit_price": 310.00},
        {"description": "هيكل تركيب — سطح",    "quantity": 2,  "unit_price": 85.00},
    ], first_payment=1000.00, notes="مشروع سكني كامل")
    pay(inv5, c[2], "2026-02-10", 500.00,  "USD", "cash")
    pay(inv5, c[2], "2026-03-01", 500.00,  "USD", "sham_cash", "تحويل 78234")
    pay(inv5, c[2], "2026-03-15", 384.00,  "USD", "cash")

    # ── سامر الرفاعي — ليرة قديمة, معلقة ─────────────────────
    inv6 = make_invoice("2026-004", c[3], "2026-02-01", "SYP_OLD", [
        {"description": "كشاف ليد خارجي 50W",  "quantity": 10, "unit_price": 85000},
        {"description": "سبوت ليد 12W",        "quantity": 20, "unit_price": 22000},
        {"description": "توصيلة كهرباء مقاومة","quantity": 5,  "unit_price": 35000},
    ])

    # ── سامر الرفاعي — USD, جزئية ─────────────────────────────
    inv7 = make_invoice("2026-010", c[3], "2026-04-01", "USD", [
        {"description": "كابل شمسي 6mm — متر", "quantity": 100, "unit_price": 2.75},
        {"description": "موصل MC4 زوج",        "quantity": 20,  "unit_price": 3.50},
        {"description": "فيوز شمسي 15A",       "quantity": 10,  "unit_price": 4.25},
    ], first_payment=100.00)

    # ── يوسف الإبراهيم — USD, مسددة ──────────────────────────
    inv8 = make_invoice("2026-005", c[4], "2026-02-10", "USD", [
        {"description": "لوحة شمسية 550W",      "quantity": 20, "unit_price": 145.50},
        {"description": "إنفرتر 10KW شبكي",    "quantity": 2,  "unit_price": 980.00},
        {"description": "عداد طاقة ذكي",        "quantity": 2,  "unit_price": 75.00},
    ], first_payment=2000.00, notes="مشروع تجاري — مستودع")
    pay(inv8, c[4], "2026-03-05", 2000.00, "USD", "sham_cash", "تحويل مصرفي 99001")
    pay(inv8, c[4], "2026-04-01", 1020.00, "USD", "cash")

    # ── حسام الدين — ليرة جديدة, جزئية ───────────────────────
    inv9 = make_invoice("2026-006", c[5], "2026-02-20", "SYP_NEW", [
        {"description": "لوحة شمسية 400W",     "quantity": 2, "unit_price": 350000},
        {"description": "شاحن شمسي MPPT 40A",  "quantity": 1, "unit_price": 180000},
        {"description": "بطارية جل 150Ah",     "quantity": 2, "unit_price": 195000},
    ], first_payment=200000)
    pay(inv9, c[5], "2026-03-10", 150000, "SYP_NEW", "cash")

    # ── رامي الشيخ — USD, معلقة (جديد) ───────────────────────
    inv10 = make_invoice("2026-007", c[6], "2026-04-20", "USD", [
        {"description": "لوحة شمسية 400W",      "quantity": 6, "unit_price": 119.99},
        {"description": "إنفرتر 5KW هايبرد",   "quantity": 1, "unit_price": 445.00},
        {"description": "بطارية ليثيوم 100Ah",  "quantity": 4, "unit_price": 275.50},
        {"description": "كابل شمسي 6mm — متر",  "quantity": 30, "unit_price": 2.75},
    ], notes="عرض سعر مبدئي — بانتظار الموافقة")

    print(f"✓ Created 10 invoices with payments")

    # ── Summary ─────────────────────────────────────────────────
    stats = db.get_dashboard_stats()
    print()
    print("─" * 40)
    print("  Database Summary")
    print("─" * 40)
    print(f"  Customers : {stats['total_customers']}")
    print(f"  Invoices  : {stats['total_invoices']}")
    print(f"  Paid      : {stats['paid_count']}")
    print(f"  Partial   : {stats['partial_count']}")
    print(f"  Unpaid    : {stats['unpaid_count']}")
    print()
    print("  Outstanding debt by currency:")
    for row in stats['debt_by_currency']:
        print(f"    {row['currency']:10} {row['remaining']:>15,.2f}")
    print("─" * 40)
    print()
    print("✓ Seed complete — run python3 app.py to start")


if __name__ == "__main__":
    seed_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'invoices.db')
    if os.path.exists(seed_path):
        confirm = input("⚠️  This will DELETE all existing data. Type 'yes' to continue: ")
        if confirm.strip().lower() != 'yes':
            print("Cancelled.")
            sys.exit(0)
    clear_and_seed()
