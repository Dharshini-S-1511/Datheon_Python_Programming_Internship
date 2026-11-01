"""Automated File Organizer & Cleanup Utility.

Sorts files in a directory into category subfolders based on file extension,
handles name collisions and permission errors, and logs everything.

Usage:
    python organizer.py                 # organizes your Downloads folder
    python organizer.py "C:\\path\\dir"   # organizes a specific folder
    python organizer.py "C:\\path\\dir" --dry-run   # preview, moves nothing
"""
import argparse
import logging
import os
import shutil
import sys
from pathlib import Path

EXTENSION_MAP = {
    # Documents
    ".pdf": "Documents", ".doc": "Documents", ".docx": "Documents",
    ".txt": "Documents", ".rtf": "Documents", ".odt": "Documents",
    ".xls": "Documents", ".xlsx": "Documents", ".csv": "Documents",
    ".ppt": "Documents", ".pptx": "Documents",
    # Images
    ".jpg": "Images", ".jpeg": "Images", ".png": "Images", ".gif": "Images",
    ".bmp": "Images", ".svg": "Images", ".webp": "Images",
    # Videos
    ".mp4": "Videos", ".mkv": "Videos", ".avi": "Videos", ".mov": "Videos",
    ".wmv": "Videos", ".flv": "Videos",
    # Audio
    ".mp3": "Audio", ".wav": "Audio", ".aac": "Audio", ".flac": "Audio",
    # Archives
    ".zip": "Archives", ".rar": "Archives", ".7z": "Archives",
    ".tar": "Archives", ".gz": "Archives",
    # Code
    ".py": "Code", ".java": "Code", ".c": "Code", ".cpp": "Code",
    ".js": "Code", ".html": "Code", ".css": "Code", ".sql": "Code",
    ".json": "Code", ".ipynb": "Code",
}
DEFAULT_CATEGORY = "Others"
LOG_FILE = "organizer.log"


def setup_logging(log_path):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def get_category(filename):
    """Return the category folder name for a file based on its extension."""
    ext = Path(filename).suffix.lower()
    return EXTENSION_MAP.get(ext, DEFAULT_CATEGORY)


def unique_destination(dest_dir, filename):
    """Return a path that doesn't exist yet: name.ext -> name (1).ext, ..."""
    candidate = dest_dir / filename
    if not candidate.exists():
        return candidate
    stem, suffix = Path(filename).stem, Path(filename).suffix
    counter = 1
    while True:
        candidate = dest_dir / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def organize(target, dry_run=False):
    """Organize files in `target`. Returns a stats dictionary."""
    stats = {"moved": 0, "renamed": 0, "skipped": 0, "errors": 0}
    by_category = {}
    category_folders = set(EXTENSION_MAP.values()) | {DEFAULT_CATEGORY}
    this_script = Path(__file__).resolve()

    with os.scandir(target) as entries:
        files = [e for e in entries if e.is_file(follow_symlinks=False)]

    for entry in files:
        path = Path(entry.path)

        # never move this script or its log file
        if path.resolve() == this_script or entry.name == LOG_FILE:
            stats["skipped"] += 1
            continue

        category = get_category(entry.name)
        dest_dir = Path(target) / category
        try:
            if not dry_run:
                dest_dir.mkdir(exist_ok=True)
            dest = unique_destination(dest_dir, entry.name)
            if dest.name != entry.name:
                stats["renamed"] += 1
                logging.warning("Name collision: '%s' -> '%s'",
                                entry.name, dest.name)
            if dry_run:
                logging.info("[DRY RUN] %s -> %s/%s",
                             entry.name, category, dest.name)
            else:
                shutil.move(str(path), str(dest))
                logging.info("Moved '%s' -> %s/", entry.name, category)
            stats["moved"] += 1
            by_category[category] = by_category.get(category, 0) + 1
        except PermissionError:
            stats["errors"] += 1
            logging.error("Permission denied: '%s' (file may be open or "
                          "protected)", entry.name)
        except FileExistsError:
            stats["errors"] += 1
            logging.error("File already exists, skipped: '%s'", entry.name)
        except OSError as exc:
            stats["errors"] += 1
            logging.error("Could not move '%s': %s", entry.name, exc)

    return stats, by_category


def print_summary(stats, by_category, dry_run):
    title = "EXECUTION SUMMARY (DRY RUN)" if dry_run else "EXECUTION SUMMARY"
    line = "=" * 40
    print(f"\n{line}\n{title:^40}\n{line}")
    for category, count in sorted(by_category.items()):
        print(f"  {category:<12} : {count}")
    print("-" * 40)
    print(f"  Total files {'to move' if dry_run else 'relocated'} : "
          f"{stats['moved']}")
    print(f"  Renamed (collisions)    : {stats['renamed']}")
    print(f"  Skipped                 : {stats['skipped']}")
    print(f"  Errors                  : {stats['errors']}")
    print(line)
    logging.info("Summary: %s", stats)


def main():
    parser = argparse.ArgumentParser(description="Organize files by type.")
    parser.add_argument("directory", nargs="?",
                        default=str(Path.home() / "Downloads"),
                        help="folder to organize (default: Downloads)")
    parser.add_argument("--dry-run", action="store_true",
                        help="show what would happen without moving files")
    args = parser.parse_args()

    target = Path(args.directory).expanduser()
    if not target.is_dir():
        print(f"Error: '{target}' is not a valid folder.")
        sys.exit(1)

    setup_logging(Path(__file__).resolve().parent / LOG_FILE)
    logging.info("Organizing: %s%s", target,
                 " (dry run)" if args.dry_run else "")
    stats, by_category = organize(target, args.dry_run)
    print_summary(stats, by_category, args.dry_run)


if __name__ == "__main__":
    main()
