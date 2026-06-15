import os
import sqlite3
import csv

db_path = "data-analysis.db"
output_dir = "diagnostics"

os.makedirs(output_dir, exist_ok=True)

# List existing CSV files (report names)
existing_csvs = {f.replace('.csv', '').lower() for f in os.listdir(output_dir) if f.endswith('.csv')}

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all user tables (cust_* and tbl_*)
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'temp_%'")
tables = sorted([row[0] for row in cursor.fetchall()])

generated_count = 0

for tbl in tables:
    csv_name = tbl.lower()
    report_exists = False
    
    checks = [csv_name, csv_name.replace('cust_', ''), csv_name.replace('tbl_', ''), 'get' + csv_name.replace('cust_', ''), 'get' + csv_name.replace('tbl_', '')]
    for c in checks:
        if c in existing_csvs or ('get' + c) in existing_csvs:
            report_exists = True
            break
            
    if not report_exists:
        try:
            cursor.execute(f"SELECT * FROM {tbl}")
            data = cursor.fetchall()
            if data:
                headers = [col[0] for col in cursor.description]
                csv_path = os.path.join(output_dir, f"{tbl}.csv")
                with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(headers)
                    writer.writerows(data)
                print(f"Exported {tbl} -> {tbl}.csv ({len(data)} rows)")
                generated_count += 1
        except Exception as e:
            print(f"Error exporting {tbl}: {e}")

conn.close()
print(f"\nSuccessfully exported {generated_count} additional tables as CSV reports.")
