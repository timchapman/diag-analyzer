import os
import sqlite3
import csv
import sys

db_path = "data-analysis.db"
output_dir = "diagnostics"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. Create DiagAnalyzerFindings table if not exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS DiagAnalyzerFindings (
    [Title] TEXT,
    [Category] TEXT,
    [Severity] TEXT,
    [Impact] TEXT,
    [Recommendation] TEXT,
    [Reading] TEXT,
    [SummaryCategory] TEXT
)
""")
cursor.execute("DELETE FROM DiagAnalyzerFindings")
conn.commit()

rules = [
    # Database Settings Rules
    ("""
    INSERT INTO DiagAnalyzerFindings ([Title],[Category],[Severity],[Recommendation])
    SELECT 
        'User database is set to compatibility level lower than the default installation level.',
        'Database Settings',
        'Critical',
        'Database ' || name || ' has compat level ' || compatibility_level || '.'
    FROM cust_Databases
    WHERE CAST(compatibility_level AS INT) < 130 
      AND name NOT IN ('master', 'tempdb', 'model', 'msdb');
    """, "Check Database Compatibility Levels"),

    ("""
    INSERT INTO DiagAnalyzerFindings ([Title],[Category],[Severity],[Recommendation])
    SELECT 
        'Databases found that have collations different from master/model databases.',
        'Database Settings',
        'Critical',
        'Database ' || name || ' has collation ' || collation_name || ' (master is ' || (SELECT collation_name FROM cust_Databases WHERE database_id=1) || ').'
    FROM cust_Databases
    WHERE collation_name <> (SELECT collation_name FROM cust_Databases WHERE database_id=1)
      AND name NOT LIKE '%ReportServer%'
      AND database_id > 4;
    """, "Check Database Collations"),

    # Operational Excellence Rules
    ("""
    INSERT INTO DiagAnalyzerFindings ([Title],[Category],[Severity],[Recommendation])
    SELECT 
        'Databases using Delayed Durability.',
        'Operational Excellence',
        'Critical',
        'The following database(s) have Delayed Durability enabled: ' || group_concat(name, ', ') || '.'
    FROM cust_Databases
    WHERE delayed_durability_desc <> 'DISABLED'
    GROUP BY (SELECT 1)
    HAVING count(*) > 0;
    """, "Check Delayed Durability"),

    ("""
    INSERT INTO DiagAnalyzerFindings ([Title],[Category],[Severity],[Recommendation], [SummaryCategory])
    SELECT 
        'Databases with Parameterization Forced.',
        'Operational Excellence',
        'Critical',
        'The following database(s) have Parameterization Forced enabled: ' || group_concat(name, ', ') || '.',
        'QueryPerformance'
    FROM cust_Databases
    WHERE is_parameterization_forced = '1' or is_parameterization_forced = 'True'
    GROUP BY (SELECT 1)
    HAVING count(*) > 0;
    """, "Check Parameterization Forced"),

    ("""
    INSERT INTO DiagAnalyzerFindings ([Title],[Category],[Severity],[Recommendation], [SummaryCategory])
    SELECT 
        'Databases with Trustworthy setting enabled.',
        'Operational Excellence',
        'Critical',
        'The following database(s) have Trustworthy enabled: ' || group_concat(name, ', ') || '.',
        'Security'
    FROM cust_Databases
    WHERE (is_trustworthy_on = '1' or is_trustworthy_on = 'True') AND database_id > 4
    GROUP BY (SELECT 1)
    HAVING count(*) > 0;
    """, "Check Trustworthy setting on User DBs"),

    ("""
    INSERT INTO DiagAnalyzerFindings ([Title],[Category],[Severity],[Recommendation])
    SELECT 
        'Databases with Auto-Close enabled.',
        'Operational Excellence',
        'High',
        'The following database(s) have Auto-Close enabled: ' || group_concat(name, ', ') || '.'
    FROM cust_Databases
    WHERE (is_auto_close_on = '1' or is_auto_close_on = 'True')
    GROUP BY (SELECT 1)
    HAVING count(*) > 0;
    """, "Check Auto-Close databases"),

    ("""
    INSERT INTO DiagAnalyzerFindings ([Title],[Category],[Severity],[Recommendation])
    SELECT 
        'Databases with Auto-Shrink enabled.',
        'Operational Excellence',
        'High',
        'The following database(s) have Auto-Shrink enabled: ' || group_concat(name, ', ') || '.'
    FROM cust_Databases
    WHERE (is_auto_shrink_on = '1' or is_auto_shrink_on = 'True')
    GROUP BY (SELECT 1)
    HAVING count(*) > 0;
    """, "Check Auto-Shrink databases"),

    ("""
    INSERT INTO DiagAnalyzerFindings ([Title],[Category],[Severity],[Recommendation])
    SELECT 
        'Databases without CHECKSUM page verification.',
        'Operational Excellence',
        'Critical',
        'The following database(s) do not have page verification set to CHECKSUM: ' || group_concat(name, ', ') || '.'
    FROM cust_Databases
    WHERE page_verify_option_desc <> 'CHECKSUM' AND name NOT IN ('tempdb')
    GROUP BY (SELECT 1)
    HAVING count(*) > 0;
    """, "Check Page Verification Options"),

    # Server Configuration Rules
    ("""
    INSERT INTO DiagAnalyzerFindings ([Title],[Category],[Severity],[Recommendation])
    SELECT 
        'Max Degree of Parallelism (MaxDOP) is set to 0.',
        'Server Configuration',
        'High',
        'MaxDOP is set to 0, which allows queries to use all available CPUs on the server. Consider setting it to the number of cores in a NUMA node (max 8).'
    FROM cust_SPConfigure
    WHERE name = 'max degree of parallelism' AND value_in_use = '0';
    """, "Check MaxDOP Configuration"),

    ("""
    INSERT INTO DiagAnalyzerFindings ([Title],[Category],[Severity],[Recommendation])
    SELECT 
        'Cost Threshold for Parallelism is set to default (5).',
        'Server Configuration',
        'Medium',
        'Cost Threshold for Parallelism is set to 5. This is often too low for modern hardware, causing small queries to parallelize unnecessarily. Consider increasing it to 50.'
    FROM cust_SPConfigure
    WHERE name = 'cost threshold for parallelism' AND CAST(value_in_use AS INT) <= 5;
    """, "Check Cost Threshold for Parallelism"),

    # HEAP Tables with High Rows Count
    ("""
    INSERT INTO DiagAnalyzerFindings ([Title],[Category],[Severity],[Recommendation])
    SELECT 
        'Tables have been identified that are Heaps (No Clustered Index) with high row counts.',
        'Database Design',
        'High',
        'Table [' || i.DBName || '].[' || i.TableName || '] is a HEAP with ' || d.RowCnt || ' rows. Consider adding a clustered index to prevent Table Scans.'
    FROM cust_IndexDetail i
    JOIN cust_CompressionDetails d ON i.DBName = d.DBName AND i.TableName = d.TableName
    WHERE i.TableName NOT LIKE 'sys%' 
      AND i.TableName NOT LIKE 'ServiceBroker%' 
      AND i.IndexType = 'HEAP' 
      AND CAST(d.RowCnt AS BIGINT) > 10000;
    """, "Check HEAP Tables with > 10,000 Rows"),
]

for sql, desc in rules:
    print(f"Running Rule: {desc}...")
    try:
        cursor.execute(sql)
        conn.commit()
    except Exception as e:
        print(f"Error running rule: {e}")

# Count total findings
cursor.execute("SELECT COUNT(*) FROM DiagAnalyzerFindings")
total_findings = cursor.fetchone()[0]

# Export to CSV
cursor.execute("SELECT * FROM DiagAnalyzerFindings")
data = cursor.fetchall()
if data:
    headers = [col[0] for col in cursor.description]
    csv_path = os.path.join(output_dir, "DiagAnalyzerFindings.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        writer.writerows(data)
    print(f"\nSuccessfully populated DiagAnalyzerFindings table with {total_findings} health findings.")
    print(f"Exported to {csv_path}")

conn.close()
