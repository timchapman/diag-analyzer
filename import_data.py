import os
import re
import sqlite3
import xml.etree.ElementTree as ET
import glob
import sys
import collections
import queue
import threading
import concurrent.futures
import time
import csv
import json
import argparse
from datetime import datetime

class MappingContext:
    def __init__(self, mappings):
        self.mappings = mappings
        self.ident_lowers_tuple = tuple(m[3] for m in mappings)
        self.ident_norms_tuple = tuple(m[4] for m in mappings)

def parse_xml_config(xml_path):
    print(f"Loading mapping config from {xml_path}...")
    tree = ET.parse(xml_path)
    root = tree.getroot()
    mappings = []
    for rowset in root.findall('.//Rowset'):
        enabled = rowset.attrib.get('enabled', 'true').lower() == 'true'
        if enabled:
            ident = rowset.attrib.get('identifier')
            name = rowset.attrib.get('name')
            rtype = rowset.attrib.get('type')
            if ident and name:
                ident_lower = ident.lower()
                ident_norm = re.sub(r'\s+', '', ident_lower)
                mappings.append((ident, name, rtype, ident_lower, ident_norm))
    mappings.sort(key=lambda x: len(x[0]), reverse=True)
    print(f"Loaded {len(mappings)} enabled rowset mappings.")
    return mappings

def determine_col_ranges(separator_line):
    separator_line = separator_line.rstrip('\n')
    col_ranges = []
    start = 0
    while start < len(separator_line):
        while start < len(separator_line) and separator_line[start] == ' ':
            start += 1
        if start >= len(separator_line):
            break
        end = start
        while end < len(separator_line) and separator_line[end] != ' ':
            end += 1
        col_ranges.append((start, end))
        start = end
    return col_ranges

def match_identifier(line, ctx: MappingContext):
    line_lower = line.lower()
    if line_lower.startswith(ctx.ident_lowers_tuple):
        for ident, table_name, rowset_type, ident_lower, ident_norm in ctx.mappings:
            if line_lower.startswith(ident_lower):
                return {'identifier': ident, 'name': table_name, 'type': rowset_type}
    line_norm = re.sub(r'\s+', '', line_lower)
    if line_norm.startswith(ctx.ident_norms_tuple):
        for ident, table_name, rowset_type, ident_lower, ident_norm in ctx.mappings:
            if line_norm.startswith(ident_norm):
                return {'identifier': ident, 'name': table_name, 'type': rowset_type}
    return None

def is_end_of_section(line, ctx: MappingContext):
    if not line.strip():
        return True
    if line.startswith('Start time:'):
        return True
    if line.startswith('DebugPrint:'):
        return True
    if match_identifier(line, ctx):
        return True
    if line.startswith('--') and any(c.isalpha() for c in line.strip()):
        return True
    return False

def clean_tag_to_table_name(tag):
    name = tag.strip('- ')
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    name = re.sub(r'_+', '_', name)
    name = name.strip('_')
    return f"tg_{name}"

def load_simple_message_direct(table_name, value, conn, file_name, run_time):
    cursor = conn.cursor()
    create_sql = f"CREATE TABLE IF NOT EXISTS [{table_name}] (Message TEXT, _file_name TEXT, _run_time TEXT)"
    cursor.execute(create_sql)
    insert_sql = f"INSERT INTO [{table_name}] (Message, _file_name, _run_time) VALUES (?, ?, ?)"
    cursor.execute(insert_sql, (value, file_name, run_time))
    conn.commit()

def align_table_schema(table_name, headers, conn):
    cursor = conn.cursor()
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    if not cursor.fetchone():
        return
    cursor.execute(f"PRAGMA table_info([{table_name}])")
    current_cols = {row[1].lower() for row in cursor.fetchall()}
    for h in headers:
        if h.lower() not in current_cols:
            print(f"\n  [Schema Evolution] Adding column [{h}] to table [{table_name}]")
            try:
                cursor.execute(f"ALTER TABLE [{table_name}] ADD COLUMN [{h}] TEXT")
            except sqlite3.OperationalError as e:
                print(f"Error adding column {h} to {table_name}: {e}")
                raise e
            current_cols.add(h.lower())
    conn.commit()

def flush_buffer(table_name, headers, data, conn, file_name, run_time):
    if not data or not headers:
        return
    align_table_schema(table_name, headers, conn)
    cursor = conn.cursor()
    create_cols = [f"[{h}] TEXT" for h in headers]
    create_cols.append("[_file_name] TEXT")
    create_cols.append("[_run_time] TEXT")
    create_sql = f"CREATE TABLE IF NOT EXISTS [{table_name}] ({', '.join(create_cols)})"
    try:
        cursor.execute(create_sql)
    except sqlite3.OperationalError as e:
        print(f"\nError creating table {table_name}: {e}")
        print(f"Headers: {headers}")
        raise e
    placeholders = ', '.join(['?'] * (len(headers) + 2))
    insert_sql = f"INSERT INTO [{table_name}] ({', '.join([f'[{h}]' for h in headers])}, [_file_name], [_run_time]) VALUES ({placeholders})"
    rows_to_insert = []
    for r in data:
        if len(r) < len(headers):
            r = list(r) + [''] * (len(headers) - len(r))
        elif len(r) > len(headers):
            r = r[:len(headers)]
        rows_to_insert.append(list(r) + [file_name, run_time])
    cursor.executemany(insert_sql, rows_to_insert)
    conn.commit()

STATE_SEEKING = 0
STATE_EXPECTING_HEADERS = 1
STATE_EXPECTING_SEPARATOR = 2
STATE_READING_DATA = 3

def process_file_threaded(file_path, ctx: MappingContext, write_queue: queue.Queue, enabled_tables):
    file_name = os.path.basename(file_path)
    state = STATE_SEEKING
    current_table = None
    current_headers = None
    current_buffer = []
    raw_headers_line = None
    col_ranges = []
    current_run_time = None
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line_stripped = line.strip()
                if line.startswith('Start time:'):
                    current_run_time = line[len('Start time:'):].strip()
                processed = False
                while not processed:
                    if state == STATE_SEEKING:
                        matched_rowset = match_identifier(line, ctx)
                        if matched_rowset:
                            is_dynamic = False
                            if matched_rowset['type'] == 'RowsetImportEngine.TextRowset':
                                current_table = matched_rowset['name']
                                state = STATE_EXPECTING_HEADERS
                            elif matched_rowset['type'] == 'RowsetImportEngine.SimpleMessageRowset':
                                val = line[len(matched_rowset['identifier']):].strip()
                                write_queue.put({
                                    'action': 'simple_msg',
                                    'table_name': matched_rowset['name'],
                                    'value': val,
                                    'file_name': file_name,
                                    'run_time': current_run_time
                                })
                        elif line.startswith('--') and any(c.isalpha() for c in line_stripped):
                            is_dynamic = True
                            potential_dynamic_tag = line_stripped
                            current_table = clean_tag_to_table_name(line_stripped)
                            state = STATE_EXPECTING_HEADERS
                        processed = True
                    elif state == STATE_EXPECTING_HEADERS:
                        if not line_stripped:
                            processed = True
                            continue
                        raw_headers_line = line
                        state = STATE_EXPECTING_SEPARATOR
                        processed = True
                    elif state == STATE_EXPECTING_SEPARATOR:
                        if not line_stripped:
                            state = STATE_SEEKING
                            processed = True
                            continue
                        if re.match(r'^[- ]+$', line_stripped):
                            col_ranges = determine_col_ranges(line)
                            current_headers = [raw_headers_line[s:e].strip() for s, e in col_ranges]
                            current_buffer = []
                            state = STATE_READING_DATA
                        else:
                            state = STATE_SEEKING
                        processed = True
                    elif state == STATE_READING_DATA:
                        if is_end_of_section(line, ctx):
                            if current_buffer and current_headers and current_table:
                                write_queue.put({
                                    'action': 'flush',
                                    'table_name': current_table,
                                    'headers': current_headers,
                                    'data': current_buffer,
                                    'file_name': file_name,
                                    'run_time': current_run_time
                                })
                            current_buffer = []
                            state = STATE_SEEKING
                            continue
                        if col_ranges:
                            row = [line[s:e].strip() for s, e in col_ranges]
                            if any(cell for cell in row):
                                current_buffer.append(row)
                        processed = True
            if current_buffer and current_headers and current_table:
                write_queue.put({
                    'action': 'flush',
                    'table_name': current_table,
                    'headers': current_headers,
                    'data': current_buffer,
                    'file_name': file_name,
                    'run_time': current_run_time
                })
    except Exception as e:
        print(f"\nError processing file {file_name}: {e}")

def db_writer_worker(db_path, write_queue: queue.Queue, log_path, total_files):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    
    csv_file = open(log_path, "w", newline="", encoding="utf-8")
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(["timestamp", "file_name", "table_name", "rows_count", "run_time"])
    
    total_written = 0
    start_time = time.time()
    files_done = set()
    
    while True:
        try:
            item = write_queue.get()
            if item.get('action') == 'close':
                break
            action = item.get('action')
            table_name = item.get('table_name')
            file_name = item.get('file_name')
            run_time = item.get('run_time')
            if action == 'flush':
                headers = item.get('headers')
                data = item.get('data')
                flush_buffer(table_name, headers, data, conn, file_name, run_time)
                total_written += len(data)
                csv_writer.writerow([datetime.now().isoformat(), file_name, table_name, len(data), run_time])
                csv_file.flush()
            elif action == 'simple_msg':
                value = item.get('value')
                load_simple_message_direct(table_name, value, conn, file_name, run_time)
            files_done.add(file_name)
            elapsed = time.time() - start_time
            speed = int(total_written / elapsed) if elapsed > 0 else 0
            print(f"\r[Progress] Files: {len(files_done)}/{total_files} | Rows: {total_written:,} | Speed: {speed:,} rows/s | Writing {len(data) if action == 'flush' else 1} to {table_name}       ", end="")
            write_queue.task_done()
        except Exception as e:
            print(f"\nError in writer thread: {e}")
    csv_file.close()
    conn.close()
    print(f"\n[Complete] Total rows written: {total_written:,} in {time.time() - start_time:.1f}s")

def main():
    parser = argparse.ArgumentParser(description="Multi-threaded PSSDIAG Import Engine")
    parser.add_argument("out_dir", nargs="?", default="output_problem/output", help="Directory containing the .OUT source files (default: output_problem/output)")
    args = parser.parse_args()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    
    # Load configuration
    if not os.path.exists(config_path):
        print(f"Error: Configuration file {config_path} not found.")
        sys.exit(1)
        
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error parsing {config_path}: {e}")
        sys.exit(1)
        
    database_name = config.get("database_name", "data-analysis.db")
    database_directory = config.get("database_directory", ".")
    max_threads = config.get("max_threads", 8)
    max_queue_size = config.get("max_queue_size", 200)
    mapping_config_path = config.get("mapping_config_path", "TextRowsets.xml")
    progress_log_path = config.get("progress_log_path", "import_progress.csv")
    sqlite_pragmas = config.get("sqlite_pragmas", {"journal_mode": "WAL", "synchronous": "NORMAL"})
    
    # Resolve paths
    xml_path = os.path.abspath(os.path.join(script_dir, mapping_config_path))
    log_path = os.path.abspath(os.path.join(script_dir, progress_log_path))
    db_dir_abs = os.path.abspath(os.path.join(script_dir, database_directory))
    db_path = os.path.join(db_dir_abs, database_name)
    input_dir = os.path.abspath(os.path.join(script_dir, args.out_dir))
    
    if not os.path.exists(xml_path):
        print(f"Error: Mapping XML config {xml_path} not found.")
        sys.exit(1)
        
    if not os.path.exists(input_dir):
        print(f"[Setup] Creating missing directory: {input_dir}")
        os.makedirs(input_dir, exist_ok=True)
        print(f"[Setup] Please place your PSSDIAG .OUT files into that directory and run this script again.")
        sys.exit(0)
        
    os.makedirs(db_dir_abs, exist_ok=True)
    
    mappings = parse_xml_config(xml_path)
    ctx = MappingContext(mappings)
    enabled_tables = {m[1] for m in mappings}
    
    out_files = glob.glob(os.path.join(input_dir, "*.OUT"))
    out_files.sort()
    
    if not out_files:
        print(f"No .OUT files found to process in {input_dir}.")
        sys.exit(0)
        
    for p in [db_path, f"{db_path}-wal", f"{db_path}-shm"]:
        if os.path.exists(p):
            print(f"Removing stale database file: {p}...")
            try:
                os.remove(p)
            except Exception as e:
                print(f"Warning: Error removing {p}: {e}")
            
    conn = sqlite3.connect(db_path)
    for pragma, val in sqlite_pragmas.items():
         try:
             conn.execute(f"PRAGMA {pragma}={val}")
         except sqlite3.OperationalError as e:
             print(f"Warning: Error setting PRAGMA {pragma}={val}: {e}")
    conn.close()
            
    print(f"Starting import of {len(out_files)} files using {max_threads} parser threads.")
    
    write_queue = queue.Queue(maxsize=max_queue_size)
    
    writer_thread = threading.Thread(
        target=db_writer_worker, 
        args=(db_path, write_queue, log_path, len(out_files)),
        daemon=True
    )
    writer_thread.start()
    
    start_time = time.time()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = [
                executor.submit(process_file_threaded, f, ctx, write_queue, enabled_tables)
                for f in out_files
            ]
            concurrent.futures.wait(futures)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Shutting down...")
    finally:
        write_queue.put({'action': 'close'})
        writer_thread.join()
        
    print(f"Finished in {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    main()
