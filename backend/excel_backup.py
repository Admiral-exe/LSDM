"""
Excel backup manager: creates timestamped backups in .backups/ with rolling retention.
"""
import shutil
import datetime
from pathlib import Path
import config
from backend.database import log_audit

MAX_BACKUPS = 50

def get_backup_directory() -> Path:
    backup_dir = config.BACKUP_DIR
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir

def create_backup(file_path: Path | str, action_tag: str = "sync") -> Path | None:
    """
    Creates a timestamped snapshot of the target file in .backups/.
    Maintains maximum MAX_BACKUPS files by pruning oldest.
    """
    src_path = Path(file_path)
    if not src_path.exists():
        return None

    backup_dir = get_backup_directory()
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_filename = f"{src_path.stem}_{now_str}_{action_tag}{src_path.suffix}"
    backup_target = backup_dir / backup_filename

    try:
        shutil.copy2(src_path, backup_target)
        log_audit(
            action=f"BACKUP_{action_tag.upper()}",
            target_file=str(src_path.name),
            backup_path=str(backup_target),
            details="Automated pre-write snapshot"
        )
        prune_old_backups(backup_dir)
        return backup_target
    except Exception as e:
        print(f"[Backup Error] Failed to create backup for {src_path}: {e}")
        return None

def prune_old_backups(backup_dir: Path):
    """Retains the MAX_BACKUPS newest files, removing older ones."""
    try:
        backups = sorted(backup_dir.glob("*.xlsx"), key=lambda p: p.stat().st_mtime)
        if len(backups) > MAX_BACKUPS:
            to_remove = backups[: len(backups) - MAX_BACKUPS]
            for p in to_remove:
                try:
                    p.unlink()
                except OSError:
                    pass
    except Exception as e:
        print(f"[Prune Error] Failed to prune backups: {e}")
