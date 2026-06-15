import os
import re
import sqlite3
import csv

sql_dir = "SQLAnalyzer_modern/SQLAnalyzer"
db_path = "data-analysis.db"
output_dir = "diagnostics"

os.makedirs(output_dir, exist_ok=True)

# List of target SQL files to scan
sql_files = [
    "01_SQLDiagAnalysis.sql",
    "02_SQLSkillsProcs.sql",
    "20_SQLDiagEvaluteRules.sql",
    "22_ExecutiveSummary.sql",
    "40_ExecutiveSummary.sql",
    "41_ExecutiveSummary_Memory.sql",
    "42_ExecutiveSummary_Disk.sql",
    "43_ExecutiveSummary_CPU.sql",
    "44_ExecutiveSummary_Concurrency.sql"
]

def tokenize_sql(sql):
    token_specification = [
        ('STRING',   r"'(?:''|[^'])*'"),            # String literal
        ('ID',       r'[a-zA-Z_#][a-zA-Z0-9_#]*'),    # Identifiers
        ('NUMBER',   r'\d+(?:\.\d*)?'),              # Integer or decimal number
        ('OP',       r'[=<>!]+'),                    # Comparison operators
        ('PAREN',    r'[\(\)]'),                     # Parentheses
        ('SEMI',     r';'),                          # Semicolon
        ('COMMA',    r','),                          # Comma
        ('DOT',      r'\.'),                         # Dot
        ('NEWLINE',  r'\n'),                         # Line endings
        ('SKIP',     r'[ \t\r]+'),                   # Skip spaces and tabs
        ('MISC',     r'.'),                          # Any other character
    ]
    tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)
    
    tokens = []
    for mo in re.finditer(tok_regex, sql):
        kind = mo.lastgroup
        value = mo.group()
        if kind == 'SKIP':
            continue
        tokens.append((kind, value))
    return tokens

def parse_and_strip_control_flow(sql):
    is_globally_commented = sql.strip().startswith('--')
    uncommented_lines = []
    for line in sql.split('\n'):
        if is_globally_commented and line.strip().startswith('--'):
            uncommented_lines.append(line.replace('--', '', 1))
        else:
            uncommented_lines.append(line)
    sql = '\n'.join(uncommented_lines)
    
    sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
    sql = re.sub(r'(?s)/\*.*?\*/', '', sql)
    
    # Remove dbo schema prefix
    sql = re.sub(r'(?i)\[?dbo\]?\.', '', sql)
    
    # Strip brackets
    sql = sql.replace('[', '').replace(']', '')
    
    # Translate SELECT INTO temp table
    def replace_select_into(match):
        cols = match.group(1)
        temp_table = match.group(2).replace('#', 'temp_')
        return f"CREATE TEMP TABLE {temp_table} AS SELECT {cols} FROM"
    
    sql = re.sub(r'(?i)\bSELECT\b(.*?)\bINTO\s+(\#\w+)\s+\bFROM\b', replace_select_into, sql, flags=re.DOTALL)
    sql = sql.replace('#', 'temp_')
    
    # Pre-tokenization T-SQL function normalizations
    sql = re.sub(r'(?i)\bisnull\b', 'ifnull', sql)
    sql = re.sub(r'(?i)\boption\s*\(maxrecursion\s+\d+\)', '', sql)
    sql = re.sub(r'(?i)CONVERT\s*\(\s*VARCHAR\(\d+\)\s*,\s*([^,]+)\s*,\s*101\s*\)', r'\1', sql)
    
    tokens = tokenize_sql(sql)
    
    output_tokens = []
    i = 0
    n = len(tokens)
    
    begin_stack = []
    case_depth = 0
    
    while i < n:
        kind, val = tokens[i]
        val_upper = val.upper()
        
        if kind == 'ID' and val_upper == 'CASE':
            case_depth += 1
            output_tokens.append(val)
            i += 1
        elif kind == 'ID' and val_upper == 'END':
            if case_depth > 0:
                case_depth -= 1
                output_tokens.append(val)
            else:
                if begin_stack:
                    begin_stack.pop()
            i += 1
        elif kind == 'ID' and val_upper == 'BEGIN':
            if len(output_tokens) > 0 and output_tokens[-1].upper() == 'AS':
                 output_tokens.pop()
            else:
                 begin_stack.append('BEGIN')
            i += 1
        elif kind == 'ID' and val_upper == 'IF':
            j = i + 1
            has_begin = False
            paren_depth = 0
            while j < n:
                jk, jv = tokens[j]
                jv_upper = jv.upper()
                if jv == '(':
                    paren_depth += 1
                elif jv == ')':
                    paren_depth -= 1
                elif jv_upper == 'BEGIN' and paren_depth == 0:
                    has_begin = True
                    break
                elif jv_upper in ['SELECT', 'CREATE', 'DROP', 'UPDATE', 'INSERT', 'DELETE', 'SET', 'DECLARE'] and paren_depth == 0:
                    break
                j += 1
                
            if has_begin:
                begin_stack.append('IF_BEGIN')
                i = j + 1
            else:
                i = j
        elif kind == 'ID' and val_upper in ['DECLARE', 'SET', 'PRINT']:
            while i < n and tokens[i][0] != 'NEWLINE' and tokens[i][1] != ';':
                i += 1
            if i < n:
                i += 1
        elif kind == 'ID' and val_upper in ['CREATE', 'ALTER'] and i+1 < n and tokens[i+1][1].upper() == 'PROCEDURE':
            while i < n and tokens[i][1].upper() != 'AS':
                i += 1
            if i < n:
                i += 1
        else:
            if kind != 'NEWLINE':
                 output_tokens.append(val)
            else:
                 output_tokens.append('\n')
            i += 1
            
    result = []
    prev_kind = None
    paren_depth = 0
    
    for idx, val in enumerate(output_tokens):
        if val == '(':
            paren_depth += 1
        elif val == ')':
            paren_depth -= 1
            
        if val == '\n':
            result.append(val)
            prev_kind = 'NEWLINE'
            continue
            
        val_upper = val.upper()
        if val_upper in ['SELECT', 'CREATE', 'DROP', 'INSERT', 'UPDATE', 'DELETE'] and paren_depth == 0:
            is_as_select = False
            if val_upper == 'SELECT':
                 last_tok = None
                 for tok in reversed(output_tokens[:idx]):
                     if tok != '\n':
                         last_tok = tok.upper()
                         break
                 if last_tok == 'AS':
                     is_as_select = True
            if not is_as_select:
                last_non_space = None
                for r in reversed(result):
                    if r.strip():
                        last_non_space = r
                        break
                if last_non_space and last_non_space != ';':
                    result.append(';')
                    result.append('\n')
                    prev_kind = 'SEMI'
                    
        if prev_kind and prev_kind not in ['NEWLINE', 'SEMI'] and val not in [',', '.', ';', '(', ')']:
            result.append(' ')
        result.append(val)
        prev_kind = 'ID' if val.isalnum() else 'OP'
        
    cleaned_sql = ''.join(result)
    
    return cleaned_sql

def translate_select_list(select_sql):
    match = re.search(r'(?i)\bSELECT\s+', select_sql)
    if not match:
        return select_sql
        
    depth = 0
    from_idx = -1
    select_len = len(select_sql)
    
    i = 0
    while i < select_len:
        char = select_sql[i]
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
        elif char.upper() == 'F' and depth == 0:
            if i + 4 <= select_len and select_sql[i:i+4].upper() == "FROM":
                if (i == 0 or select_sql[i-1].isspace()) and (i+4 == select_len or select_sql[i+4].isspace() or select_sql[i+4] == '('):
                    from_idx = i
                    break
        i += 1
        
    if from_idx == -1:
        return select_sql
        
    select_clause = select_sql[:from_idx]
    from_clause = select_sql[from_idx:]
    
    select_match = re.search(r'(?i)\bSELECT\s+', select_clause)
    select_prefix = select_clause[:select_match.end()]
    select_list_text = select_clause[select_match.end():]
    
    cols = []
    current_col = []
    depth = 0
    for char in select_list_text:
        if char == '(':
            depth += 1
            current_col.append(char)
        elif char == ')':
            depth -= 1
            current_col.append(char)
        elif char == ',' and depth == 0:
            cols.append(''.join(current_col).strip())
            current_col = []
        else:
            current_col.append(char)
    if current_col:
        cols.append(''.join(current_col).strip())
        
    translated_cols = []
    for col in cols:
        if '=' in col:
            parts = col.split('=', 1)
            alias = parts[0].strip()
            expr = parts[1].strip()
            alias_clean = alias.replace('[', '').replace(']', '')
            if re.match(r'^\w+$', alias_clean):
                translated_cols.append(f"{expr} AS {alias}")
                continue
        translated_cols.append(col)
        
    new_select_clause = select_prefix + ', '.join(translated_cols)
    return new_select_clause + " " + from_clause

failures = []
successes = []
procedures_found = []

# Scan files and extract procedures
for filename in sql_files:
    filepath = os.path.join(sql_dir, filename)
    if not os.path.exists(filepath):
         print(f"Skipping scan of missing file: {filepath}")
         continue
         
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        file_content = f.read()
        
    # Match procedure names
    # Match Get*, ExecutiveSummary*, Summary*, Reporting*
    matches = re.findall(r'(?:--\s*)?CREATE\s+PROCEDURE\s+(?:\[?dbo\]?\.?)?\[?((?:Get|ExecutiveSummary_|Summary_|Reporting)\w+)\]?', file_content, re.IGNORECASE)
    for proc in set(matches):
        procedures_found.append((proc, file_content, filename))

print(f"Total target procedures found across SQL files: {len(procedures_found)}")

# Process found procedures
for proc, file_content, source_file in procedures_found:
    pattern_str = r'(?:--\s*)?CREATE\s+PROCEDURE\s+(?:\[?dbo\]?\.?)?\[?' + re.escape(proc) + r'\]?.*?(?=GO|--\s*GO|CREATE\s+PROCEDURE|--\s*CREATE\s+PROCEDURE|\Z)'
    pattern = re.compile(pattern_str, re.DOTALL | re.IGNORECASE)
    
    match = pattern.search(file_content)
    if not match:
        continue
        
    proc_body = match.group(0)
    cleaned_body = parse_and_strip_control_flow(proc_body)
    
    # Split queries by semicolon
    queries = cleaned_body.split(';')
    
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    
    success = False
    error_msg = ""
    created_tables = []
    
    try:
        cursor = conn.cursor()
        for q in queries:
            q_stripped = q.strip(' \t\n\r;(')
            if not q_stripped:
                continue
            
            translated_q = translate_select_list(q_stripped)
            
            # Cleanup trailing unmatched parens
            open_p = translated_q.count('(')
            close_p = translated_q.count(')')
            if close_p > open_p and translated_q.endswith(')'):
                translated_q = translated_q[:-1]
                
            if translated_q.upper().startswith("SELECT"):
                cursor.execute(translated_q)
                data = cursor.fetchall()
                headers = [col[0] for col in cursor.description]
                csv_path = os.path.join(output_dir, f"{proc}.csv")
                with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(headers)
                    writer.writerows(data)
                successes.append((proc, csv_path, len(data), source_file))
                success = True
            else:
                if "CREATE TEMP TABLE" in translated_q.upper() or "CREATE TABLE" in translated_q.upper():
                    match_tbl = re.search(r'(?i)CREATE\s+(?:TEMP\s+)?TABLE\s+(\w+)', translated_q)
                    if match_tbl:
                        created_tables.append(match_tbl.group(1))
                cursor.execute(translated_q)
                conn.commit()
                
        if not success:
            error_msg = "No SELECT query returned data or was executed successfully."
            
    except Exception as e:
        error_msg = str(e)
    finally:
        try:
            cursor = conn.cursor()
            for tbl in created_tables:
                cursor.execute(f"DROP TABLE IF EXISTS {tbl}")
            conn.commit()
        except:
            pass
        conn.close()
        
    if not success:
        failures.append((proc, error_msg, cleaned_body, source_file))

print(f"\n=== Translation Summary ===")
print(f"Successfully translated and ran: {len(successes)} procedures.")
print(f"Failed to run: {len(failures)} procedures.")

# Log failures with source file context
with open("translation_failures.log", "w", encoding="utf-8") as f:
    for proc, err, body, src in failures:
        f.write("=" * 80 + "\n")
        f.write(f"PROCEDURE: {proc} (Source: {src})\n")
        f.write(f"ERROR: {err}\n")
        f.write("-" * 80 + "\n")
        f.write(body)
        f.write("\n\n")
        
print("\nFailures have been logged to 'translation_failures.log'.")
