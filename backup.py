"""
Backup System
═════════════
Triggers:
  1. Daily      — first app launch each day (background thread)
  2. Auto       — every AUTO_BACKUP_EVERY_N_CHANGES DB operations
  3. Manual     — user clicks the backup button

Folder structure:
  backups/
    latest_backup.db        ← always the most recent backup (overwritten in place)
    daily/                  ← one per day, keeps last KEEP_DAILY files
    auto/                   ← every N ops, keeps last KEEP_AUTO files
    manual/                 ← user triggered, keeps last KEEP_MANUAL files

Each backup writes TWO files:
  1. Timestamped copy in its subfolder
  2. Overwrites latest_backup.db
"""

import os
import shutil
import threading
from datetime import datetime, date

import database as db

# ── Configuration (edit these values to change behaviour) ────────

AUTO_BACKUP_EVERY_N_CHANGES = 50   # change this number anytime

KEEP_DAILY  = 30
KEEP_AUTO   = 20
KEEP_MANUAL = 20

# ── Internal state ───────────────────────────────────────────────

_change_counter = 0
_counter_lock   = threading.Lock()

# ── Folder helpers ───────────────────────────────────────────────

def _backups_root():
    return db.get_backup_dir()

def _daily_dir():
    d = os.path.join(_backups_root(), 'daily')
    os.makedirs(d, exist_ok=True)
    return d

def _auto_dir():
    d = os.path.join(_backups_root(), 'auto')
    os.makedirs(d, exist_ok=True)
    return d

def _manual_dir():
    d = os.path.join(_backups_root(), 'manual')
    os.makedirs(d, exist_ok=True)
    return d

def _latest_backup_path():
    return os.path.join(_backups_root(), 'latest_backup.db')

def _daily_marker_path():
    """Tracks the date of the last daily backup."""
    return os.path.join(db.get_app_dir(), 'last_daily_backup.txt')

# ── Init ─────────────────────────────────────────────────────────

def init_backup():
    """Call once at app startup."""
    # Ensure all folders exist
    _backups_root()
    _daily_dir()
    _auto_dir()
    _manual_dir()
    # Trigger daily backup in background if not done today
    threading.Thread(target=_run_daily_if_needed, daemon=True).start()

# ── Daily backup ─────────────────────────────────────────────────

def _run_daily_if_needed():
    today    = date.today().isoformat()
    marker   = _daily_marker_path()
    last_day = ''

    if os.path.exists(marker):
        try:
            with open(marker, 'r') as f:
                last_day = f.read().strip()
        except Exception:
            pass

    if last_day == today:
        return  # already done today

    path = _do_backup(subfolder=_daily_dir(), label='daily')
    if path:
        try:
            with open(marker, 'w') as f:
                f.write(today)
        except Exception:
            pass

# ── Auto backup ───────────────────────────────────────────────────

def record_change():
    """
    Call after every DB write (insert / update / delete).
    Triggers an auto backup every AUTO_BACKUP_EVERY_N_CHANGES operations.
    """
    global _change_counter
    with _counter_lock:
        _change_counter += 1
        should_backup = (_change_counter >= AUTO_BACKUP_EVERY_N_CHANGES)
        if should_backup:
            _change_counter = 0

    if should_backup:
        threading.Thread(
            target=_do_backup,
            kwargs={'subfolder': _auto_dir(), 'label': 'auto'},
            daemon=True
        ).start()

# ── Manual backup ─────────────────────────────────────────────────

def do_manual_backup():
    """
    Called when user clicks the backup button.
    Returns the path of the backup file or None on failure.
    """
    return _do_backup(subfolder=_manual_dir(), label='manual')

# ── Core backup function ──────────────────────────────────────────

def _do_backup(subfolder, label):
    """
    Creates a timestamped copy in subfolder AND overwrites latest_backup.db.
    Returns the path of the timestamped file, or None on failure.
    """
    src = db.get_db_path()
    if not os.path.exists(src):
        return None

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename  = f'backup_{label}_{timestamp}.db'
    dest      = os.path.join(subfolder, filename)

    try:
        # 1. Save timestamped copy in subfolder
        shutil.copy2(src, dest)

        # 2. Overwrite latest_backup.db
        shutil.copy2(src, _latest_backup_path())

    except Exception as e:
        print(f'[backup] failed ({label}): {e}')
        return None

    # Rotate old files in the subfolder
    _rotate(subfolder, _keep_count(label))

    return dest

# ── Rotation ──────────────────────────────────────────────────────

def _keep_count(label):
    return {'daily': KEEP_DAILY, 'auto': KEEP_AUTO, 'manual': KEEP_MANUAL}.get(label, 20)

def _rotate(folder, keep):
    """Delete oldest files in folder, keeping only `keep` most recent."""
    try:
        files = sorted(
            f for f in os.listdir(folder)
            if f.startswith('backup_') and f.endswith('.db')
        )
        while len(files) > keep:
            os.remove(os.path.join(folder, files.pop(0)))
    except Exception:
        pass

# ── Info ──────────────────────────────────────────────────────────

def list_backups():
    """Return all backup filenames across all subfolders, newest first."""
    all_files = []
    for folder in [_daily_dir(), _auto_dir(), _manual_dir()]:
        label = os.path.basename(folder)
        try:
            for f in os.listdir(folder):
                if f.startswith('backup_') and f.endswith('.db'):
                    full = os.path.join(folder, f)
                    all_files.append({
                        'filename': f,
                        'label':    label,
                        'path':     full,
                        'mtime':    os.path.getmtime(full),
                    })
        except Exception:
            pass
    all_files.sort(key=lambda x: x['mtime'], reverse=True)
    return all_files


def get_last_backup_info():
    """
    Returns info about the most recent backup for display on the dashboard.
    Reads from latest_backup.db mtime for simplicity.
    """
    latest = _latest_backup_path()
    if not os.path.exists(latest):
        return {'exists': False, 'time': None, 'count': 0}

    try:
        mtime = os.path.getmtime(latest)
        dt    = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
    except Exception:
        dt = '—'

    # Count all backup files across subfolders
    total = sum(
        len([f for f in os.listdir(d) if f.startswith('backup_') and f.endswith('.db')])
        for d in [_daily_dir(), _auto_dir(), _manual_dir()]
        if os.path.exists(d)
    )

    return {'exists': True, 'time': dt, 'count': total}
