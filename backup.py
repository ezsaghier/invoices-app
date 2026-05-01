"""
Backup system — three layers:
  Layer 1: SQLite WAL (handled by DB engine itself — always on)
  Layer 2: Timestamped .db copies in /backups folder (this module)
  Layer 3: USB auto-copy when a removable drive is detected
"""
import os
import shutil
import ctypes
from datetime import datetime

import database as db

_change_counter = 0
BACKUP_EVERY_N_CHANGES = 10
MAX_BACKUPS = 30


def init_backup():
    """Call once at app startup."""
    db.get_backup_dir()  # ensure folder exists


def record_change():
    """Call after every DB write. Triggers backup every N changes."""
    global _change_counter
    _change_counter += 1
    if _change_counter >= BACKUP_EVERY_N_CHANGES:
        do_backup()
        _change_counter = 0


def do_backup():
    """
    Copy the live .db file to /backups with a timestamp.
    Also copies to any connected USB drive.
    Returns the path of the backup file created, or None.
    """
    src = db.get_db_path()
    if not os.path.exists(src):
        return None

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename  = f'backup_{timestamp}.db'
    dest      = os.path.join(db.get_backup_dir(), filename)

    try:
        shutil.copy2(src, dest)
    except Exception as e:
        print(f'[backup] local copy failed: {e}')
        return None

    _cleanup_old_backups()
    _try_usb_backup(src, filename)

    return dest


def _cleanup_old_backups():
    """Keep only the latest MAX_BACKUPS files in /backups."""
    backup_dir = db.get_backup_dir()
    files = sorted(
        f for f in os.listdir(backup_dir)
        if f.startswith('backup_') and f.endswith('.db')
    )
    while len(files) > MAX_BACKUPS:
        try:
            os.remove(os.path.join(backup_dir, files.pop(0)))
        except Exception:
            pass


def _try_usb_backup(src, filename):
    """Silently try to copy the backup to every connected USB drive."""
    for drive in _detect_usb_drives():
        try:
            usb_dir = os.path.join(drive, 'InvoicesBackup')
            os.makedirs(usb_dir, exist_ok=True)
            shutil.copy2(src, os.path.join(usb_dir, filename))
            print(f'[backup] USB copy → {usb_dir}')
        except Exception as e:
            print(f'[backup] USB copy failed ({drive}): {e}')


def _detect_usb_drives():
    """
    Return list of removable drive root paths on Windows.
    Uses ctypes (built-in) — no extra packages required.
    DRIVE_REMOVABLE = 2
    """
    drives = []
    try:
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            if bitmask & 1:
                root = f'{letter}:\\'
                if ctypes.windll.kernel32.GetDriveTypeW(root) == 2:
                    drives.append(root)
            bitmask >>= 1
    except Exception:
        pass  # non-Windows dev environment — skip silently
    return drives


def list_backups():
    """Return list of backup filenames (newest first)."""
    backup_dir = db.get_backup_dir()
    files = sorted(
        (f for f in os.listdir(backup_dir)
         if f.startswith('backup_') and f.endswith('.db')),
        reverse=True
    )
    return files
