#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lud-suite.settings')
    
    # Restore any freshly generated migrations (0010+) and inspect database state
    try:
        from pathlib import Path
        import sqlite3

        base_dir = Path(__file__).resolve().parent
        mig_dir = base_dir / "core" / "migrations"
        
        # Restore 0010 if it was archived
        bak_0010 = mig_dir / "0010_alter_rolepermission_role.py.bak"
        if bak_0010.exists():
            target_0010 = mig_dir / "0010_alter_rolepermission_role.py"
            bak_0010.rename(target_0010)
            sys.stderr.write(f"[RESTORE] Restored {target_0010.name}\n")

        # Archive any leftover legacy migrations (0011 through 0027)
        for p in sorted(mig_dir.iterdir()):
            if p.is_file() and p.name.endswith(".py") and not p.name.startswith("__"):
                # If migration starts with 0011_ up to 0027_, it is from the old repo
                if any(p.name.startswith(f"00{i:02d}_") for i in range(11, 28)):
                    bak_path = p.with_name(p.name + ".bak")
                    p.rename(bak_path)
                    sys.stderr.write(f"[AUTO-FIX] Archived orphaned legacy migration {p.name}\n")

        # Clear stale bytecode in __pycache__
        pycache = mig_dir / "__pycache__"
        if pycache.exists():
            for c in pycache.glob("*.pyc"):
                try:
                    c.unlink()
                except Exception:
                    pass

        # Inspect and synchronize sqlite3 database state with migrations
        db_path = base_dir / "db.sqlite3"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            existing_tables = set(r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'"))
            
            # Check if django_migrations table exists
            if "django_migrations" in existing_tables:
                applied_migs = set(r[0] for r in cursor.execute("SELECT name FROM django_migrations WHERE app='core'"))
                sys.stderr.write(f"[DB STATUS] Applied core migrations: {sorted(applied_migs)}\n")
                core_tables = [t for t in sorted(existing_tables) if t.startswith("core_")]
                sys.stderr.write(f"[DB STATUS] Existing core_* tables: {core_tables}\n")

                # Map migrations to their primary table; if the table already exists but migration isn't recorded, auto-fake it
                table_mig_map = [
                    ("core_program", "0002_program_location_chapter_cohort_cohortmembership"),
                    ("core_term", "0003_term_termresource"),
                    ("core_changehistory", "0004_changehistory"),
                    ("core_cohortactivity", "0005_senior_member_and_cohort_activity"),
                    ("core_rolepermission", "0006_rolepermission"),
                    ("core_useractivityreport", "0007_useractivityreport"),
                    ("core_termtask", "0008_termtask_termquestion_submissions"),
                    ("core_mentorassignment", "0009_mentorassignment"),
                ]
                for tbl, mig in table_mig_map:
                    if tbl in existing_tables and mig not in applied_migs:
                        cursor.execute(
                            "INSERT INTO django_migrations (app, name, applied) VALUES (?, ?, datetime('now'))",
                            ("core", mig),
                        )
                        conn.commit()
                        sys.stderr.write(f"[AUTO-FAKE] Recorded {mig} as applied (table '{tbl}' already exists in database)\n")
            conn.close()

    except Exception as e:
        sys.stderr.write(f"[INFO] {e}\n")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
