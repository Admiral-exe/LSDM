"""
Excel file lock detection module.
Checks for ~$ temporary lockfiles and attempts non-blocking OS file locks via msvcrt on Windows.
"""
import os
import sys
from pathlib import Path

def is_file_locked(file_path: Path | str) -> tuple[bool, str]:
    """
    Checks if an Excel file is locked or open in Microsoft Excel.
    Returns (is_locked: bool, reason: str).
    """
    path = Path(file_path)
    if not path.exists():
        return False, ""

    # 1. Check for standard Microsoft Excel ~$ lockfile
    lockfile_name = f"~${path.name}"
    lockfile_path = path.parent / lockfile_name
    if lockfile_path.exists():
        return True, f"Microsoft Excel lockfile detected ('{lockfile_name}'). The file is currently open in Excel."

    # 2. Check for alternative prefix lockfile (e.g. ~$X.xlsx for short names)
    if len(path.name) > 2:
        alt_lock = path.parent / f"~${path.name[2:]}"
        if alt_lock.exists():
            return True, f"Excel temporary lockfile detected ('{alt_lock.name}')."

    # 3. Test OS file handle access (exclusive read-write attempt)
    try:
        # Try opening for read/write without truncating
        handle = open(path, "r+b")
    except (PermissionError, IOError) as e:
        return True, f"Cannot acquire write handle: {str(e)}. The file is in use by another program."

    # 4. On Windows, use msvcrt for explicit OS-level locking verification
    if sys.platform == "win32":
        try:
            import msvcrt
            # Attempt a 1-byte non-blocking lock
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            # Immediately unlock if successful
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        except (IOError, OSError) as e:
            handle.close()
            return True, f"Windows OS lock violation: {str(e)}. The file is currently locked."
        finally:
            handle.close()
    else:
        handle.close()

    return False, ""
