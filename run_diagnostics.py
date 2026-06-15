import sqlite3
import sys

db_path = "data-analysis.db"

def table_exists(table_name):
    """Check if a table exists in the SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        exists = cursor.fetchone() is not None
        return exists
    except Exception:
        return False
    finally:
        conn.close()

def run_query(query, required_tables=(), params=()):
    """Verify table existence before executing SQLite query to prevent runtime errors."""
    for tbl in required_tables:
        if not table_exists(tbl):
            print(f"Error: Required table '{tbl}' does not exist in the database.")
            print(f"Skipping this report because the required PSSDIAG metric was not captured.")
            return None, None
            
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing query: {e}")
        sys.exit(1)
    finally:
        conn.close()

def print_table(title, headers, data):
    if headers is None or data is None:
        return
        
    print(f"\n=== {title} ===")
    if not data:
        print("No results found.")
        return
        
    try:
        from tabulate import tabulate as tab
        print(tab(data, headers=headers, tablefmt="github"))
    except ImportError:
        widths = [max(len(str(x)) for x in col) for col in zip(*data)]
        header_line = " | ".join(f"{h:<{w}}" for h, w in zip(headers, widths))
        print(header_line)
        print("-" * len(header_line))
        for row in data:
            print(" | ".join(f"{str(val):<{w}}" for val, w in zip(row, widths)))

def show_memory():
    query = """
    SELECT 
        ROUND(CAST(physical_memory_kb AS BIGINT) / 1024.0 / 1024.0, 2) AS [Physical Memory (GB)],
        ROUND((SELECT CAST(value_in_use AS BIGINT) FROM cust_SPConfigure WHERE name = 'max server memory (MB)') / 1024.0, 2) AS [Max Server Memory (GB)],
        ROUND((SELECT CAST(value_in_use AS BIGINT) FROM cust_SPConfigure WHERE name = 'min server memory (MB)') / 1024.0, 2) AS [Min Server Memory (GB)],
        container_type_desc AS [Container Type]
    FROM cust_OSInfo 
    LIMIT 1;
    """
    headers, data = run_query(query, required_tables=["cust_OSInfo", "cust_SPConfigure"])
    print_table("Memory Sizing Configuration", headers, data)

def show_waits():
    query = """
    SELECT 
        WaitType, 
        WaitCount, 
        Percentage AS [Percentage (%)], 
        AvgWait_S AS [Avg Wait Time (Sec)] 
    FROM cust_Waiting 
    ORDER BY CAST(Percentage AS REAL) DESC 
    LIMIT 10;
    """
    headers, data = run_query(query, required_tables=["cust_Waiting"])
    print_table("Top 10 Wait Statistics", headers, data)

def show_expensive_queries():
    query = """
    SELECT 
        ROUND(CAST(AverageRunTimeSeconds AS REAL), 2) AS [Avg Duration (s)],
        execution_count AS [Execution Count], 
        AverageLogicalReads AS [Avg Logical Reads], 
        query_hash AS [Query Hash],
        SUBSTRING(StatementText, 1, 150) AS [Query Statement]
    FROM cust_ExpensiveQueries 
    ORDER BY CAST(AverageRunTimeSeconds AS REAL) DESC 
    LIMIT 10;
    """
    headers, data = run_query(query, required_tables=["cust_ExpensiveQueries"])
    print_table("Top 10 Expensive Queries (by Avg Run Time)", headers, data)

def show_blocking():
    query = """
    SELECT DISTINCT 
        r.runtime AS [Snapshot Time], 
        r.session_id AS [Blocked Session], 
        r.blocking_session_id AS [Blocker Session], 
        r.wait_type AS [Wait Type], 
        r.wait_duration_ms AS [Wait Duration (ms)], 
        r.resource_description AS [Resource], 
        SUBSTRING(n.stmt_text, 1, 100) AS [Blocked Query], 
        SUBSTRING(n_blocker.stmt_text, 1, 100) AS [Blocker Query] 
    FROM cust_requests r 
    JOIN cust_NotableActiveQueries n ON r.session_id = n.session_id AND r.runtime = n.runtime 
    JOIN cust_requests blocker ON r.blocking_session_id = blocker.session_id AND r.runtime = blocker.runtime 
    LEFT JOIN cust_NotableActiveQueries n_blocker ON blocker.session_id = n_blocker.session_id AND blocker.runtime = n_blocker.runtime 
    WHERE r.blocking_session_id != '0' 
      AND r.blocking_session_id IS NOT NULL 
      AND r.ecid = '0' 
    ORDER BY r.runtime, r.session_id
    LIMIT 20;
    """
    headers, data = run_query(query, required_tables=["cust_requests", "cust_NotableActiveQueries"])
    print_table("Active Blocking Instances (First 20)", headers, data)

def show_table_scans():
    query = """
    SELECT 
        idx.DatabaseName AS [DB], 
        idx.TableName AS [Table], 
        idx.IndexName AS [Index Name], 
        co.TableRowCount AS [Row Count], 
        idx.UserSeeks AS [Seeks], 
        idx.UserScans AS [Scans], 
        idx.UserLookups AS [Lookups], 
        idx.UserUpdates AS [Updates], 
        d.IndexType AS [Index Type] 
    FROM cust_UnusedIndexes idx 
    JOIN ( 
        SELECT DBName, TableName, MAX(CAST(RowCnt AS BIGINT)) AS TableRowCount 
        FROM cust_CompressionDetails 
        GROUP BY DBName, TableName 
    ) co ON co.DBName = idx.DatabaseName AND co.TableName = idx.TableName 
    JOIN cust_IndexDetail d ON idx.DatabaseName = d.DBName and d.TableName = idx.TableName and idx.IndexName = d.IndexName 
    ORDER BY CAST(idx.UserScans AS BIGINT) DESC 
    LIMIT 15;
    """
    headers, data = run_query(query, required_tables=["cust_UnusedIndexes", "cust_CompressionDetails", "cust_IndexDetail"])
    print_table("Top 15 Tables/Indexes with Highest User Scans", headers, data)

def main():
    menu = {
        "memory": show_memory,
        "waits": show_waits,
        "queries": show_expensive_queries,
        "blocking": show_blocking,
        "scans": show_table_scans,
    }
    
    if len(sys.argv) < 2 or sys.argv[1] not in menu:
        print("Usage: python3 run_diagnostics.py [report]")
        print("Available reports:")
        for key in menu.keys():
            print(f"  - {key}")
        sys.exit(1)
        
    report_func = menu[sys.argv[1]]
    report_func()

if __name__ == "__main__":
    main()
