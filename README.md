# diag-analyzer - Multi-threaded PSSDIAG Importer

Expert Python-based assessment and import engine designed to parse and load massive Microsoft SQL Server PSSDIAG text diagnostic outputs into an optimized, query-ready SQLite database.

## Prerequisites

- **Python 3.8+** (Must be installed and added to your System PATH).
- The engine uses **100% Python Standard Library** modules, meaning no `pip install` or internet access is required to run the importer.

## Installation & Setup from Fresh Clone

1. Clone the repository to your local machine (Linux or Windows).
2. Prepare your source data:
   - Create the directory structure `output_problem/output` in the root of the cloned project folder.
   - Copy all your PSSDIAG `.OUT` files (e.g., `*__SQL Server Perf Stats_Startup.OUT`, `*__OSInfo_Startup.OUT`, etc.) into the `output_problem/output` folder.

## Running the Importer

The importer automatically detects available CPU cores and utilizes a Thread-Safe Producer-Consumer architecture to parse the `.OUT` files in parallel, bypassing SQLite concurrency locks by utilizing a dedicated background database writer thread.

To launch the importer, run:
```bash
python import_data.py
```
*(or `python3` depending on your environment).* The script is fully cross-platform and will automatically handle directory setup, clean up stale locks, and execute the import lifecycle identically on both Windows and Linux.

## Generated Artifacts

Once the script completes, the following files will be created in your root project directory:
- **`data-analysis.db`**: An optimized SQLite database containing all imported diagnostic metrics. You can query this database using any SQLite client (e.g., DBeaver, DB Browser for SQLite, or Python's `sqlite3`).
- **`import_progress.csv`**: A CSV log file recording exactly when each section/chunk of each file was parsed, which table it was inserted into, how many rows were loaded, and the source snapshot runtime.

## Troubleshooting

### Disk I/O Error or Lock on Reset
If you abruptly terminate the script while it is writing in SQLite's WAL (Write-Ahead Logging) mode, SQLite may leave active lock files behind. The startup scripts (`run_import.ps1` / `run_import.sh`) automatically handle deleting the active database `data-analysis.db` along with its temporary `-wal` and `-shm` lock files to ensure a clean reset on every run.

### Missing Tables
If you encounter unmapped headers that do not show up in the database, verify that the header identifier is listed in `TextRowsets.xml`. If it is missing, you can add it as a new `<Rowset>` tag in `TextRowsets.xml`.
