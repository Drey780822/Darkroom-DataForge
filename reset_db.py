"""
Quick utility script to reset Darkroom DataForge SQLite database to a 100% fresh start.
Usage:
    python reset_db.py
    python reset_db.py --clear-files
"""
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import argparse
from backend.app.database import clear_database

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Darkroom DataForge Database Reset Utility")
    parser.add_argument("--clear-files", action="store_true", help="Also remove uploaded files and exports")
    args = parser.parse_args()

    print("==================================================")
    print("DARKROOM DATAFORGE - DATABASE RESET")
    print("==================================================")
    print("Clearing all tables, sequences, and relationships...")

    result = clear_database(clear_files=args.clear_files)

    print(f"Status:            {result['status'].upper()}")
    print(f"Message:           {result['message']}")
    print(f"Tables Recreated:  {result['tables_recreated']}")
    if args.clear_files:
        print(f"Files Removed:     {result['files_removed']}")
    print("==================================================")
    print("Ready for a completely fresh start!")
