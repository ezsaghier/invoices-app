# Invoice Management System
### نظام إدارة الفواتير والمدفوعات
**Electrical Parts & Solar Panels Store**

---

## Overview

A fully offline desktop web application for managing customer invoices and payments.
Built with Python + Flask + SQLite. No internet required after installation.
Runs on Windows 10 (64-bit) by double-clicking a shortcut — no technical knowledge needed.

---

## Features

- **Customer management** — name, address, phone, notes
- **Invoice management** — manual invoice numbers, multiple line items, first payment option
- **Multi-currency** — USD / Syrian Pound (new) / Syrian Pound (old)
- **Payments tracking** — cash or Sham Cash, full payment history per invoice
- **Item autocomplete** — learns item descriptions as you type, no manual catalog needed
- **New customer modal** — create a new customer from within the invoice form without losing data
- **Dark / Light theme** — toggle from the sidebar
- **Arabic UI** — fully localized, all text in `localization-ar.json`
- **Decimal support** — prices and amounts support up to 2 decimal places

---

## Backup System

Three automatic backup triggers, all stored in `D:\InvoicesApp\backups\`:

```
backups/
  latest_backup.db        ← always the most recent backup (overwritten each time)
  daily/                  ← one backup per day on first app launch (keeps last 30)
  auto/                   ← every 50 DB operations (keeps last 20)
  manual/                 ← user triggered via sidebar button (keeps last 20)
```

**To change the auto backup threshold**, open `backup.py` and edit line 24:
```python
AUTO_BACKUP_EVERY_N_CHANGES = 50   # change this number anytime
```

**To restore from a backup**, copy any `.db` file from the `backups/` folder
and rename it to `invoices.db` in `D:\InvoicesApp\`.

---

## Tech Stack

| Component | Technology |
|---|---|
| Backend | Python 3.11 + Flask |
| Database | SQLite (WAL mode — crash safe) |
| Frontend | HTML + CSS + Vanilla JavaScript |
| Localization | JSON file (`localization-ar.json`) |
| Launcher | VBScript (`run.vbs`) — no terminal window |

---

## Project Structure

```
invoices-app/
  app.py                    Flask application + all routes
  database.py               SQLite setup, all queries
  backup.py                 Backup system (daily / auto / manual)
  localization-ar.json      All Arabic UI text — edit freely in Notepad
  seed.py                   Test data generator (development only)
  run.vbs                   Silent launcher for Windows
  update.bat                Pull latest updates from GitHub + restart app
  install.bat               First-time installer launcher
  install.ps1               Full installer script (PowerShell)
  static/
    css/style.css           Light + dark theme styles
    js/app.js               Autocomplete, invoice items, theme toggle, modal
  templates/
    base.html               Layout, sidebar, theme toggle, new-customer modal
    dashboard.html          Stats, debt summary, recent invoices
    customers/
      list.html             Customer list with search
      form.html             Add / edit customer
      detail.html           Customer profile + invoice history
    invoices/
      list.html             Invoice list with filter and search
      form.html             New invoice form
      detail.html           Invoice detail + payment form + payment history
```

---

## Localization

All visible Arabic text lives in `localization-ar.json`.
To change any label, button, or message — open the file in Notepad and edit the value.
No code changes needed. Changes take effect on next app restart.

```json
{
  "btn": {
    "save": "حفظ",
    "cancel": "إلغاء"
  },
  "messages": {
    "invoice_created": "تم إنشاء الفاتورة بنجاح"
  }
}
```

---

## Developer Guide

### Prerequisites
- Python 3.11+
- pip

### Run locally (Mac / Windows)
```bash
pip install flask
python app.py
# Opens at http://127.0.0.1:5001
```

> **Mac note:** Port 5001 is used instead of 5000 because macOS AirPlay blocks port 5000.

### Fill with test data
```bash
python seed.py
# type 'yes' when prompted
```

### Push an update
```bash
cd /Users/ezzedeen/Documents/GitHub/invoices-app
git add .
git commit -m "feat: describe what changed"
git push
```

---

## Customer Update Process

When a new version is pushed to GitHub, the customer runs one file:

```
Double-click  D:\InvoicesApp\update.bat
```

The script automatically:
1. Stops the running app
2. Pulls latest code from GitHub (`git pull`)
3. Restarts the app silently

> **Important:** `update.bat` never touches `invoices.db` or the `backups/` folder.
> Customer data is always safe during updates.

---

## First-time Installation (Customer)

1. Download `install.bat` and `install.ps1` from this repo
2. Place both files in the same folder
3. Double-click `install.bat`
4. The script installs Python, Git, Flask, clones the repo, and creates a Desktop shortcut

Requirements: Windows 10, internet connection, drive D: available.

---

## File Locations (Customer Machine)

| Path | Contents |
|---|---|
| `D:\InvoicesApp\` | All app files |
| `D:\InvoicesApp\invoices.db` | The database — never delete |
| `D:\InvoicesApp\backups\` | All backup files |
| `D:\InvoicesApp\backups\latest_backup.db` | Most recent backup |
| `D:\InvoicesApp\run.vbs` | Silent launcher |
| `D:\InvoicesApp\update.bat` | Update script |

---

## GitHub

**Repository:** https://github.com/ezsaghier/invoices-app
**Developer:** ezsaghier
