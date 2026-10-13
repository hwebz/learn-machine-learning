#!/usr/bin/env python3
"""
Clean up test data from pc_chatbots.

This script removes:
1. Test jobs from the database (unit tests + integration test patterns)
2. Associated provider runs, sources, events, subtasks, reports
3. Artifact folders created by test runs (empty or with test patterns)
"""

import argparse
import asyncio
import re
import shutil
import sqlite3
from pathlib import Path
from typing import List, Set

# Test query patterns to identify test jobs
TEST_QUERY_PATTERNS = [
    r"^Test ",           # "Test health...", "Test sync...", etc.
    r"^Cancel this test",
    r"Explain a test topic",
    r"Test across new providers",
    r"Test granular SSE",
    r"Test failing provider",
    r"Test async concurrent",
    r"Test sync sequential",
]

# Test job ID patterns (some tests use predictable IDs)
TEST_JOB_ID_PATTERNS = []

# Artifact folder patterns that indicate test runs
TEST_ARTIFACT_PATTERNS = [
    r"^ui-[a-z]+-\d+$",           # e.g., ui-chatgpt-1791898395
    r"^.*-debug$",                 # debug folders
]

# Patterns that indicate real user data (to keep)
KEEP_ARTIFACT_PATTERNS = [
    r"^manual-",                   # manual browser debug
    r"^grok-debug$",               # specific debug folder
    r"^copilot-debug$",            # specific debug folder
]


def is_test_query(query: str) -> bool:
    """Check if a query matches test patterns."""
    for pattern in TEST_QUERY_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            return True
    return False


def is_test_artifact_folder(name: str) -> bool:
    """Check if an artifact folder matches test patterns."""
    # First check if it should be kept
    for pattern in KEEP_ARTIFACT_PATTERNS:
        if re.search(pattern, name, re.IGNORECASE):
            return False

    # Then check if it matches test patterns
    for pattern in TEST_ARTIFACT_PATTERNS:
        if re.search(pattern, name, re.IGNORECASE):
            return True
    return False


async def cleanup_database(db_path: Path, dry_run: bool = False) -> dict:
    """Remove test jobs and related data from the database."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    results = {
        "jobs_removed": 0,
        "provider_runs_removed": 0,
        "sources_removed": 0,
        "events_removed": 0,
        "subtasks_removed": 0,
        "reports_removed": 0,
        "test_job_ids": [],
    }

    # Find test job IDs
    cur.execute("SELECT id, query FROM job")
    all_jobs = cur.fetchall()

    test_job_ids = []
    for job in all_jobs:
        if is_test_query(job["query"] or ""):
            test_job_ids.append(job["id"])

    results["test_job_ids"] = test_job_ids
    results["jobs_removed"] = len(test_job_ids)

    if dry_run:
        print(f"[DRY RUN] Would remove {len(test_job_ids)} test jobs")
        for job_id in test_job_ids[:20]:
            job = next((j for j in all_jobs if j["id"] == job_id), None)
            if job:
                print(f"  - {job_id[:16]}... query={job['query'][:50]}")
        if len(test_job_ids) > 20:
            print(f"  ... and {len(test_job_ids) - 20} more")
        conn.close()
        return results

    if not test_job_ids:
        print("No test jobs found to remove")
        conn.close()
        return results

    print(f"Removing {len(test_job_ids)} test jobs and associated data...")

    # Build placeholders for IN clause
    placeholders = ",".join("?" * len(test_job_ids))

    # Remove in correct order (foreign keys)
    # 1. JobEvent (has job_id)
    cur.execute(f"DELETE FROM jobevent WHERE job_id IN ({placeholders})", test_job_ids)
    results["events_removed"] = cur.rowcount
    print(f"  Removed {cur.rowcount} job events")

    # 2. ProviderRun (has job_id indirectly through subtask)
    # First get subtask IDs for these jobs
    cur.execute(f"SELECT id FROM subtask WHERE job_id IN ({placeholders})", test_job_ids)
    subtask_ids = [row["id"] for row in cur.fetchall()]

    if subtask_ids:
        sub_placeholders = ",".join("?" * len(subtask_ids))
        cur.execute(f"DELETE FROM providerrun WHERE subtask_id IN ({sub_placeholders})", subtask_ids)
        results["provider_runs_removed"] = cur.rowcount
        print(f"  Removed {cur.rowcount} provider runs")

        # 3. Source (has job_id and run_id)
        cur.execute(f"DELETE FROM source WHERE job_id IN ({placeholders})", test_job_ids)
        results["sources_removed"] = cur.rowcount
        print(f"  Removed {cur.rowcount} sources")

        # 4. Subtask
        cur.execute(f"DELETE FROM subtask WHERE job_id IN ({placeholders})", test_job_ids)
        results["subtasks_removed"] = cur.rowcount
        print(f"  Removed {cur.rowcount} subtasks")
    else:
        # No subtasks, but provider runs might still exist with job_id in other ways
        cur.execute(f"DELETE FROM providerrun WHERE subtask_id IN (SELECT id FROM subtask WHERE job_id IN ({placeholders}))", test_job_ids)
        results["provider_runs_removed"] = cur.rowcount
        print(f"  Removed {cur.rowcount} provider runs")

        cur.execute(f"DELETE FROM source WHERE job_id IN ({placeholders})", test_job_ids)
        results["sources_removed"] = cur.rowcount
        print(f"  Removed {cur.rowcount} sources")

    # 5. Report
    cur.execute(f"DELETE FROM report WHERE job_id IN ({placeholders})", test_job_ids)
    results["reports_removed"] = cur.rowcount
    print(f"  Removed {cur.rowcount} reports")

    # 6. Job (finally)
    cur.execute(f"DELETE FROM job WHERE id IN ({placeholders})", test_job_ids)
    print(f"  Removed {cur.rowcount} jobs")

    conn.commit()
    conn.close()

    return results


def cleanup_artifacts(artifacts_dir: Path, dry_run: bool = False) -> dict:
    """Remove test artifact folders."""
    if not artifacts_dir.exists():
        return {"folders_removed": 0, "folders_kept": 0, "space_freed_kb": 0}

    results = {
        "folders_removed": 0,
        "folders_kept": 0,
        "space_freed_kb": 0,
        "removed_folders": [],
    }

    for folder in artifacts_dir.iterdir():
        if not folder.is_dir():
            continue

        if is_test_artifact_folder(folder.name):
            # Calculate size
            total_size = sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())

            if dry_run:
                print(f"[DRY RUN] Would remove artifact folder: {folder.name} ({total_size / 1024:.1f} KB)")
            else:
                shutil.rmtree(folder)
                print(f"Removed artifact folder: {folder.name} ({total_size / 1024:.1f} KB)")

            results["folders_removed"] += 1
            results["space_freed_kb"] += total_size / 1024
            results["removed_folders"].append(folder.name)
        else:
            results["folders_kept"] += 1

    return results


async def main():
    parser = argparse.ArgumentParser(description="Clean up test data from pc_chatbots")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be removed without actually removing")
    parser.add_argument("--db-only", action="store_true", help="Only clean database, skip artifacts")
    parser.add_argument("--artifacts-only", action="store_true", help="Only clean artifacts, skip database")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent
    db_path = base_dir / "data" / "app.db"
    artifacts_dir = base_dir / "data" / "artifacts"

    print("=" * 60)
    print("pc_chatbots Test Data Cleanup")
    print("=" * 60)

    if not db_path.exists() and not args.artifacts_only:
        print(f"Database not found: {db_path}")
        return 1

    if not artifacts_dir.exists() and not args.db_only:
        print(f"Artifacts directory not found: {artifacts_dir}")
        return 1

    # Show summary first
    if not args.dry_run and not args.yes:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM job")
        total_jobs = cur.fetchone()[0]

        cur.execute("SELECT id, query FROM job")
        all_jobs = cur.fetchall()
        test_job_ids = [j["id"] for j in all_jobs if is_test_query(j["query"] or "")]
        conn.close()

        # Count artifact folders
        test_folders = 0
        keep_folders = 0
        if artifacts_dir.exists():
            for f in artifacts_dir.iterdir():
                if f.is_dir() and is_test_artifact_folder(f.name):
                    test_folders += 1
                elif f.is_dir():
                    keep_folders += 1

        print(f"\nDatabase: {total_jobs} total jobs, {len(test_job_ids)} test jobs to remove")
        print(f"Artifacts: {test_folders} test folders to remove, {keep_folders} folders to keep")
        print()

        confirm = input("Proceed with cleanup? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Cancelled")
            return 0

    all_results = {}

    # Clean database
    if not args.artifacts_only:
        print("\n--- Cleaning Database ---")
        db_results = await cleanup_database(db_path, dry_run=args.dry_run)
        all_results["database"] = db_results

    # Clean artifacts
    if not args.db_only:
        print("\n--- Cleaning Artifacts ---")
        artifact_results = cleanup_artifacts(artifacts_dir, dry_run=args.dry_run)
        all_results["artifacts"] = artifact_results

    # Summary
    print("\n" + "=" * 60)
    print("CLEANUP SUMMARY")
    print("=" * 60)

    if "database" in all_results:
        r = all_results["database"]
        print(f"Database:")
        print(f"  Jobs removed: {r['jobs_removed']}")
        print(f"  Provider runs removed: {r['provider_runs_removed']}")
        print(f"  Sources removed: {r['sources_removed']}")
        print(f"  Events removed: {r['events_removed']}")
        print(f"  Subtasks removed: {r['subtasks_removed']}")
        print(f"  Reports removed: {r['reports_removed']}")

    if "artifacts" in all_results:
        r = all_results["artifacts"]
        print(f"Artifacts:")
        print(f"  Folders removed: {r['folders_removed']}")
        print(f"  Folders kept: {r['folders_kept']}")
        print(f"  Space freed: {r['space_freed_kb']:.1f} KB")

    if args.dry_run:
        print("\n[DRY RUN] No actual changes made. Run without --dry-run to execute.")

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))