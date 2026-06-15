import os
import sqlite3
import re
import sys

def table_exists(table_name, conn):
    """Check if a table exists in the SQLite database."""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        exists = cursor.fetchone() is not None
        return exists
    except Exception:
        return False

# Stored Procedure Reports start below:


def executivesummary_cpu(conn):
    """
    T-SQL Source: ExecutiveSummary_CPU
    Required Tables: CounterData, CounterDetails, a, cust_ExpensiveQueries
    """
    required_tables = ['CounterData', 'CounterDetails', 'a', 'cust_ExpensiveQueries']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'ExecutiveSummary_CPU': Required tables not present.")
        return None, None
        
    query = """
AS
		CREATE TEMP TABLE temp_WindowsCPU AS SELECT  @MachineName = udf_GetMachineName()
			@MaxDOP BIT = 0, 
			@CXPACKET BIT = 0, 
			@TF8048 BIT = 0,
			@ExpensiveQueriesExist BIT = 0
			(
				SELECT *
				FROM cust_ExpensiveQueries
				WHERE 
					CAST(AverageRunTimeSeconds AS REAL) >= 10 
					AND CAST(execution_count AS INTEGER) >= 16 
			)
			OBJECT_ID(''CounterDetails'') IS NOT NULL 
			SELECT
				dd.ObjectName,
				dd.CounterName,
    AVG(CounterValue), AS AverageCPU
    MAX(CounterValue), AS MaxCPU
    STDEV(CounterValue) AS CPUStDev
			 FROM
				CounterData d
				JOIN CounterDetails dd ON d.CounterID = dd.CounterID
				WHERE dd.ObjectName LIKE ''Processor%''
					AND dd.CounterName LIKE ''_ Processor Time''
					AND dd.InstanceName NOT LIKE ''_Total''AND
    @MachineName AS MachineName
			GROUP BY dd.ObjectName,
				dd.CounterName
			INSERT INTO @Output
			SELECT @Statement
			INSERT INTO @Output
			SELECT @Statement
			SELECT TOP 1 @AvgCPU = AverageCPU
			FROM #WindowsCPU 
			ORDER BY AverageCPU DESC
				INSERT INTO @Output
				SELECT @Statement
			INSERT INTO @Output
			SELECT ''From a CPU perspective, everything looks great on this server.  There are no expensive queries overwhelming the CPU, there is no CPU issues and your CPU configuration settings are properly set.'' 
	SELECT Msg FROM @Output
	ORDER BY ID ASC
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing ExecutiveSummary_CPU: {e}")
        return None, None


def executivesummary_concurrency(conn):
    """
    T-SQL Source: ExecutiveSummary_Concurrency
    Required Tables: 
    """
    required_tables = []
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'ExecutiveSummary_Concurrency': Required tables not present.")
        return None, None
        
    query = """
AS
	CREATE TABLE #BlockedProcessOverview
	(
		CounterName VARCHAR(200),
		CounterAvg VARCHAR(30),
		CounterMin VARCHAR(30),
		CounterMax VARCHAR(30)
	)
	INSERT INTO #BlockedProcessOverview
	EXECUTE GetBlockedProcessOverview
	SELECT
		@CounterAvgLockWaits = CounterAvg,
		@CounterMinLockWaits = CounterMin
	FROM #BlockedProcessOverview
	WHERE CounterName = ''Lock waits (ms)''
	SELECT
		@CounterAvgBlocked = CounterAvg, 
		@CounterMinBlocked = CounterMin
	FROM #BlockedProcessOverview
	WHERE CounterName = ''Processes blocked''
		INSERT INTO @Output
		SELECT ''The average time spent waiting for a lock request to be granted on this system is '' + CAST(@CounterAvgLockWaits AS VARCHAR(20)) + '' milliseconds.''
		INSERT INTO @Output
		SELECT ''The average number of processes being blocked on this system at any given time during the capture was '' + CAST(@CounterAvgBlocked AS VARCHAR(20)) + ''. Consider enabling RCSI.''
		SELECT Msg = ''No concurrency issues detected in the captured workload.''
		SELECT Msg FROM @Output
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing ExecutiveSummary_Concurrency: {e}")
        return None, None


def executivesummary_disk(conn):
    """
    T-SQL Source: ExecutiveSummary_Disk
    Required Tables: PTOClinicFindings
    """
    required_tables = ['PTOClinicFindings']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'ExecutiveSummary_Disk': Required tables not present.")
        return None, None
        
    query = """
AS
	(
		SELECT * 
		FROM PTOClinicFindings
		WHERE Title = ''Disk response times are too long.''
	)
			INSERT INTO @Output
			SELECT Msg = ''Disk response times were noticed.''
		INSERT INTO @Output
		SELECT Msg = ''No disk related issues were noticed in the captured workload.''
	SELECT Msg
	FROM @Output
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing ExecutiveSummary_Disk: {e}")
        return None, None


def executivesummary_memory(conn):
    """
    T-SQL Source: ExecutiveSummary_Memory
    Required Tables: CounterData, CounterDetails, a, cust_ExpensiveQueries
    """
    required_tables = ['CounterData', 'CounterDetails', 'a', 'cust_ExpensiveQueries']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'ExecutiveSummary_Memory': Required tables not present.")
        return None, None
        
    query = """
AS
			@ServerMemoryInGB REAL,
			@MaxServerMemoryInGB REAL,
			@OSMemoryInGB REAL,
			@PercentageForOS REAL,
			@AvgGBytes REAL,
			@SQL NVARCHAR(MAX)
		CREATE TABLE #PLEDips(DipCount INT)
		CREATE TABLE #MemoryConfig
		(
			ServerMemoryInGB REAL,
			MaxServerMemoryInGB REAL,
			OSMemoryInGB REAL,
			PercentageForOS REAL,
			AvgMBytes REAL,
			MinMBytes REAL,
			MaxMBytes REAL
		)
		INSERT INTO #MemoryConfig
		EXECUTE GetMemoryConfiguration
		CREATE TEMP TABLE temp_SQLProcessWorkingSet AS SELECT  
			@ServerMemoryInGB = ServerMemoryInGB,
			@MaxServerMemoryInGB = MaxServerMemoryInGB,
			@OSMemoryInGB = OSMemoryInGB,
			@PercentageForOS = PercentageForOS,
			@AvgGBytes = CAST(AvgMBytes/1024.0 AS REAL)
		FROM #MemoryConfig
		INSERT INTO #PLEDips
		EXECUTE Summary_GetPLEDips
			(
				SELECT *
				FROM cust_ExpensiveQueries
				WHERE 
				CAST(AverageLogicalReads AS INTEGER) > 10000000 OR
				(CAST(AverageLogicalReads AS INTEGER) > 250000 AND CAST(execution_count AS INTEGER) > 15)
			)
			OBJECT_ID(''CounterDetails'') IS NOT NULL 
			SELECT
				InstanceName,
    AVG(CounterValue), AS AVGDataBytes
    MAX(CounterValue), AS MaxDataBytes
				RowNo = ROW_NUMBER() OVER(ORDER BY AVG(CounterValue) DESC),
    100.0 * cast(AVG(CounterValue) as REAL) / SUM (cast(AVG(CounterValue) as REAL)) OVER() AS OverallPercentage
			 FROM
				CounterData d
				JOIN CounterDetails dd ON d.CounterID = dd.CounterID
			WHERE 
				dd.countername = ''Working Set'' AND
				ObjectName = ''Process'' AND
				InstanceName <> ''_Total''
			GROUP BY InstanceName
			(
				SELECT *
				FROM #SQLProcessWorkingSet
				WHERE 
					(
						RowNo = 1 AND
						InstanceName NOT LIKE ''%sqlservr%''
					) OR
					(
						OverallPercentage < 50 AND
						InstanceName LIKE ''%sqlservr%''
					)
			)
			(
				SELECT 
					CounterName,MIN(CounterValue), MAX(CounterValue), AVG(CounterValue)
				FROM CounterData d
				INNER JOIN CounterDetails c on c.CounterID=d.CounterID
				WHERE ObjectName = ''Memory'' 
				AND CounterName = ''Pages/sec''
				GROUP BY CounterName
				HAVING 
				MAX(CounterValue) >12000 AND
				AVG(CounterValue) > 150
			)
			INSERT INTO @MemoryOutput
			SELECT @SQL
			INSERT INTO @MemoryOutput
			SELECT ''There are a number of very expensive queries being executed on the system, resulting in a high number of pages in the buffer pool continually being removed to make room for additional pages to satisfy the queries being ran.  These queries should be tuned so that the large scans they are causing do not flood the buffer pool.  ''    
			INSERT INTO @MemoryOutput
			SELECT  ''The operating system is experiencing memory contention, resulting in paging that could result in system-wide outages.  ''
			INSERT INTO @MemoryOutput
			SELECT ''At least one process on this server competing with SQL Server for memory.  On a production-level SQL Server machine, no other application should be challenging SQL Server for memory.  '' 
			INSERT INTO @MemoryOutput
			SELECT ''From a memory perspective, everything looks great on this server.  There are no expensive queries overwhelming the buffer pool, there is no OS-level memory pressure, no processes are competing with SQL Server for process memory, and your memory configuration settings are properly set.  '' 
	SELECT Msg FROM @MemoryOutput
	ORDER BY ID ASC
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing ExecutiveSummary_Memory: {e}")
        return None, None


def getagperfdata(conn):
    """
    T-SQL Source: GetAGPerfData
    Required Tables: CounterDetails, Counterdata
    """
    required_tables = ['CounterDetails', 'Counterdata']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetAGPerfData': Required tables not present.")
        return None, None
        
    query = """
AS
		(
			SELECT
			ObjectName,
			CounterName,
			InstanceName ,
    MAX(CounterValue) AS CounterMax
		FROM Counterdata c
			JOIN CounterDetails d ON c.CounterID = d.CounterID
		WHERE ObjectName LIKE ''%Database Replica%''
		GROUP BY 
				ObjectName, 
				CounterName,
				InstanceName
		HAVING MAX(CounterValue) > 0
		)
			SELECT
				ObjectName,
				CounterName,
				InstanceName ,
				CounterAvg = FORMAT(AVG(CounterValue), ''N''),
				CounterMin = FORMAT(MIN(CounterValue), ''N''),
				CounterMax = FORMAT(MAX(CounterValue), ''N'')
			FROM Counterdata c
				JOIN CounterDetails d ON c.CounterID = d.CounterID
			WHERE ObjectName LIKE ''%Database Replica%''
			GROUP BY 
			ObjectName, 
			CounterName,
			InstanceName
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetAGPerfData: {e}")
        return None, None


def getagreplicas(conn):
    """
    T-SQL Source: GetAGReplicas
    Required Tables: cust_AGReplicaStates, cust_AGReplicas
    """
    required_tables = ['cust_AGReplicaStates', 'cust_AGReplicas']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetAGReplicas': Required tables not present.")
        return None, None
        
    query = """
AS
		(OBJECT_ID(''cust_AGReplicaStates'') IS NOT NULL)
		SELECT
			replica_server_name, owner_sid, endpoint_url, availability_mode, availability_mode_desc,
			failover_mode, failover_mode_desc, session_timeout, primary_role_allow_connections,
			primary_role_allow_connections_desc, secondary_role_allow_connections,
			secondary_role_allow_connections_desc, create_date, modify_date, backup_priority,
			read_only_routing_url,
			is_local, role, role_desc, operational_state, operational_state_desc, connected_state,
			connected_state_desc, recovery_health, recovery_health_desc, synchronization_health,
			synchronization_health_desc, last_connect_error_number, last_connect_error_description,
			last_connect_error_timestamp
		FROM cust_AGReplicas rep
			JOIN cust_AGReplicaStates rs ON rep.replica_id = rs.replica_id
				AND rs.group_id = rs.group_id
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetAGReplicas: {e}")
        return None, None


def getagstate(conn):
    """
    T-SQL Source: GetAGState
    Required Tables: cust_AGStates
    """
    required_tables = ['cust_AGStates']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetAGState': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM cust_AGStates
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetAGState: {e}")
        return None, None


def getags(conn):
    """
    T-SQL Source: GetAGs
    Required Tables: cust_AGs
    """
    required_tables = ['cust_AGs']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetAGs': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM cust_AGs
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetAGs: {e}")
        return None, None


def getaccessmethodperfdata(conn):
    """
    T-SQL Source: GetAccessMethodPerfData
    Required Tables: CounterDetails, Counterdata
    """
    required_tables = ['CounterDetails', 'Counterdata']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetAccessMethodPerfData': Required tables not present.")
        return None, None
        
    query = """
AS
	SELECT @MachineName = udf_GetMachineName()
		OBJECT_ID(''Counterdata'') IS NOT NULL AND
		OBJECT_ID(''CounterDetails'') IS NOT NULL 
		SELECT
			ObjectName,
			CounterName,
			MachineName,
			CounterAvg = FORMAT(AVG(CounterValue), ''N''),
			CounterMin = FORMAT(MIN(CounterValue), ''N''),
			CounterMax = FORMAT(MAX(CounterValue), ''N'')
		FROM Counterdata c
			JOIN CounterDetails d ON c.CounterID = d.CounterID
		WHERE ObjectName LIKE ''%Access Methods'' AND
    @MachineName AS MachineName
		GROUP BY ObjectName, CounterName, MachineName
		ORDER BY CounterName
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetAccessMethodPerfData: {e}")
        return None, None


def getallloginfo(conn):
    """
    T-SQL Source: GetAllLogInfo
    Required Tables: SQLskills_AllLogInfo
    """
    required_tables = ['SQLskills_AllLogInfo']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetAllLogInfo': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM SQLskills_AllLogInfo
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetAllLogInfo: {e}")
        return None, None


def getautotuningconfiguration(conn):
    """
    T-SQL Source: GetAutoTuningConfiguration
    Required Tables: cust_AutoTuningConfig
    """
    required_tables = ['cust_AutoTuningConfig']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetAutoTuningConfiguration': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM cust_AutoTuningConfig
		WHERE DBName NOT IN(''tempdb'',''master'',''msdb'',''model'')
		ORDER BY DBName, name
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetAutoTuningConfiguration: {e}")
        return None, None


def getazureserverinfo(conn):
    """
    T-SQL Source: GetAzureServerInfo
    Required Tables: cust_azureserverinfo
    """
    required_tables = ['cust_azureserverinfo']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetAzureServerInfo': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM cust_azureserverinfo
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetAzureServerInfo: {e}")
        return None, None


def getazureserverproperties(conn):
    """
    T-SQL Source: GetAzureServerProperties
    Required Tables: cust_azureserverproperties
    """
    required_tables = ['cust_azureserverproperties']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetAzureServerProperties': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM cust_azureserverproperties
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetAzureServerProperties: {e}")
        return None, None


def getbackuphistory(conn):
    """
    T-SQL Source: GetBackupHistory
    Required Tables: cust_Databases, cust_backupHistory
    """
    required_tables = ['cust_Databases', 'cust_backupHistory']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetBackupHistory': Required tables not present.")
        return None, None
        
    query = """
AS
		CREATE TEMP TABLE temp_DBBackupDetails AS SELECT 
			d.name, recovery_model_desc, log_reuse_wait_desc, bk.LastFullBackupDate, bk.LastDifferentialBackupDate, bk.LastLogBackupDate
		 FROM cust_Databases d
			LEFT JOIN
			(
			SELECT
				databasename name,
				max(case when TYPE = ''D'' then backupfinishdate else null end) as LastFullBackupDate,
				max(case when TYPE = ''I'' then backupfinishdate else null end) as LastDifferentialBackupDate,
				max(case when TYPE = ''L'' then backupfinishdate else null end) as LastLogBackupDate
			FROM cust_backupHistory
			WHERE backupfinishdate IS NOT NULL
			GROUP BY databasename
		) bk
			ON d.name = bk.name
		WHERE d.name <> ''tempdb''
		SELECT *
		FROM #DBBackupDetails
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetBackupHistory: {e}")
        return None, None


def getbackupinfo(conn):
    """
    T-SQL Source: GetBackupInfo
    Required Tables: SQLskills_BackupInfo
    """
    required_tables = ['SQLskills_BackupInfo']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetBackupInfo': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT TOP(1000) *
		FROM SQLskills_BackupInfo
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetBackupInfo: {e}")
        return None, None


def getbaseline(conn):
    """
    T-SQL Source: GetBaseline
    Required Tables: Baseline_Summary, CounterDetails, Counterdata, baseline_summary
    """
    required_tables = ['Baseline_Summary', 'CounterDetails', 'Counterdata', 'baseline_summary']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetBaseline': Required tables not present.")
        return None, None
        
    query = """
AS
	CREATE TEMP TABLE temp_CounterTemp AS SELECT  @MachineName = udf_GetMachineName()
		OBJECT_ID(''Counterdata'') IS NOT NULL AND
		OBJECT_ID(''CounterDetails'') IS NOT NULL 
		SELECT
			CounterName,
			InstanceName,
			ObjectName,
    AVG(CounterValue), AS CounterAvg
    MIN(CounterValue), AS CounterMin
    MAX(CounterValue) AS CounterMax
		INTO Baseline_CPU
		FROM Counterdata c
			JOIN CounterDetails d ON c.CounterID = d.CounterID
		WHERE  
			MachineName = @MachineName AND
			InstanceName = ''_Total'' AND
			ObjectName LIKE ''Processor%'' 
		GROUP BY CounterName, InstanceName, ObjectName
		SELECT
			CounterName,
			InstanceName,
			ObjectName,
    AVG(CounterValue), AS CounterAvg
    MIN(CounterValue), AS CounterMin
    MAX(CounterValue) AS CounterMax
		INTO Baseline_Disk
		FROM Counterdata c
			JOIN CounterDetails d ON c.CounterID = d.CounterID
		WHERE  
			MachineName = @MachineName AND
			ObjectName IN(''LogicalDisk'',''PhysicalDisk'')
		GROUP BY CounterName, InstanceName, ObjectName
		SELECT
			CounterName,
			InstanceName,
			ObjectName,
    AVG(CounterValue), AS CounterAvg
    MIN(CounterValue), AS CounterMin
    MAX(CounterValue) AS CounterMax
		INTO Baseline_Memory
		FROM Counterdata c
			JOIN CounterDetails d ON c.CounterID = d.CounterID
		WHERE  
			MachineName = @MachineName AND
			ObjectName = ''Memory'' 
		GROUP BY CounterName, InstanceName, ObjectName
		SELECT
			CounterName,
			InstanceName,
			ObjectName,
    AVG(CounterValue), AS CounterAvg
    MIN(CounterValue), AS CounterMin
    MAX(CounterValue) AS CounterMax
		 FROM Counterdata c
			JOIN CounterDetails d ON c.CounterID = d.CounterID
		WHERE 
			ObjectName = ''Process'' AND CounterName IN(
			''% Processor Time'',
			''% User Time'',
			''IO Data Bytes/sec'',
			''Working Set'',
			''IO Write Bytes/sec'',
			''IO Read Bytes/sec'',
			''Private Bytes'',
			''Page File Bytes''
			) AND InstanceName <> ''_Total''
			AND MachineName = @MachineName
		GROUP BY CounterName, InstanceName, ObjectName
		SELECT
			Description = CASE WHEN ObjectName LIKE ''%SQL%'' THEN ''SQL Server'' ELSE ''Server'' END,
			ObjectName,
			CounterName,
    MIN(InstanceName), AS InstanceName
    AVG(CounterValue), AS CounterAvg
    MIN(CounterValue), AS CounterMin
    MAX(CounterValue) AS CounterMax
		INTO Baseline_Summary
		FROM Counterdata c
			JOIN CounterDetails d ON c.CounterID = d.CounterID
		WHERE 
			MachineName = @MachineName AND
					(
			(
				ObjectName LIKE ''%Access Methods'' AND
					CounterName IN
				(
				''Full Scans/sec'',
				''Index Searches/sec'',
				''Range Scans/sec'',
				''Table Lock Escalations/sec'',
				''Forwarded Records/sec'',
				''Table Lock Escalations/sec'',
				''Page Splits/sec'',
				''Pages compressed/sec''
				)
			)
				OR
				(
			ObjectName LIKE ''%Buffer Manager'' AND
				CounterName IN
			(
			''Database pages'',
			''Lazy writes/sec'',
			''Page life expectancy'',
			''Free list stalls/sec'',
			''Page lookups/sec'',
			''Page reads/sec'',
			''Page writes/sec'',
			''Readahead pages/sec'',
			''Buffer cache hit ratio'',
			''Extension allocated pages'',
			''Extension page writes/sec''
			)
		)
				OR
				(
			ObjectName LIKE ''%General Statistics'' AND
				CounterName IN
			(
			''Active Temp Tables'',
			''Logins/sec'',
			''Processes blocked'',
			''Transactions'',
			''User Connections'',
			''Temp Tables Creation Rate''
			)
		)
				OR
				(
			ObjectName LIKE ''%Memory Manager'' AND
				CounterName IN
			(
				''Connection Memory (KB)'',
				''Database Cache Memory (KB)'',
				''Lock Memory (KB)'',
				''Memory Grants Outstanding'',
				''Memory Grants Pending'',
				''External benefit of memory'',
				''Free Memory (KB)'',
				''Granted Workspace Memory (KB)'',
				''Optimizer Memory (KB)'',
				''Reserved Server Memory (KB)'',
				''SQL Cache Memory (KB)'',
				''Stolen Server Memory (KB)'',
				''Target Server Memory (KB)'',
				''Total Server Memory (KB)''
			)
		)
				OR
				(
			ObjectName LIKE ''%SQL Statistics'' AND
				CounterName IN
			(
				''Batch Requests/sec'',
				''SQL Compilations/sec'',
				''SQL Re-Compilations/sec'',
				''Guided Plan Executions/sec''
			)
		)
				OR
				(
			ObjectName LIKE ''%Locks'' AND
				CounterName IN
			(
				''Lock Requests/sec'',
				''Lock Wait Time (ms)'',
				''Average Wait Time (ms)'',
				''Lock Waits/sec'',
				''Number of Deadlocks/sec''
			)
		)
				OR
				(
			ObjectName = ''Memory'' AND
				CounterName IN
			(
				''Available MBytes'',
				''Pages/sec'',
				''Memory \ Committed Bytes'',
				''% Committed Bytes In Use'',
				''Commit Limit''
			)
		)
				OR
				(
			ObjectName = ''Processor'' AND
				CounterName IN
			(
				''% Processor Time'',
				''% User Time''
			)
		)
				OR
				(
			ObjectName = ''Network Interface'' AND
				CounterName IN
			(
				''Current Bandwidth'',
				''Bytes Total/sec''
			)
		) 
		)
			GROUP BY ObjectName, CounterName
		UNION ALL
			SELECT
				Description,
				ObjectName,
				CounterName,
				InstanceName,
				CounterAvg ,
				CounterMin ,
				CounterMax
			FROM
				(
		SELECT
    ''Busiest Database'', AS Description
					ObjectName,
					CounterName,
					InstanceName,
    AVG(CounterValue), AS CounterAvg
    MIN(CounterValue), AS CounterMin
    MAX(CounterValue), AS CounterMax
					RowNo = Row_Number() OVER(PARTITION BY CounterName ORDER BY AVG(CounterValue) DESC)
				FROM Counterdata c
					JOIN CounterDetails d ON c.CounterID = d.CounterID
				WHERE 
					ObjectName LIKE ''%Databases'' AND
					CounterName = ''Active Transactions'' AND
					InstanceName <> ''_Total''
					AND MachineName = @MachineName
				GROUP BY ObjectName, CounterName, InstanceName
		) x
			WHERE RowNo = 1
		UNION ALL
			SELECT Description = ''Top 10 Processes'',
				ObjectName, CounterName, InstanceName, CounterAvg, CounterMin, CounterMax
			FROM
				(
		SELECT *,
    (CounterAvg/(SELECT SUM(CounterAvg) AS AverageOverallPercentage
					FROM #CounterTemp i
					WHERE o.CounterName = i.CounterName AND CounterAvg > 0)*1.00)*100.00,
					RowNo = Row_Number() OVER(PARTITION BY CounterName ORDER BY CounterAvg DESC)
				FROM #CounterTemp o
				WHERE CounterAvg > 0
		) x
			WHERE RowNo <= 10
		ORDER BY Description, ObjectName, CounterName
		INSERT INTO Baseline_Summary(Description, ObjectName, CounterName, InstanceName, CounterAvg, CounterMin, CounterMax)
		SELECT 
    ''SQL Server'', AS Description
    ''Custom Counter'', AS ObjectName
    others.CounterName + '' to '' + batch.CounterName + '' ratio'', AS CounterName
    NULL, AS InstanceName
			CASE WHEN batch.CounterAvg = 0 THEN 0 ELSE others.CounterAvg/batch.CounterAvg END,
			CASE WHEN batch.CounterMin = 0 THEN 0 ELSE others.CounterMin/batch.CounterMin END,
			CASE WHEN batch.CounterMax = 0 THEN 0 ELSE others.CounterMax/batch.CounterMax END
		FROM 
		(
			SELECT * 
			FROM baseline_summary
			WHERE CounterName = ''Batch Requests/sec''
		) batch, 
		(
			SELECT * 
			FROM baseline_summary
			WHERE CounterName IN
			( 
				''Page lookups/sec'',
				''Lock Requests/sec'',
				''SQL Compilations/sec'',
				''SQL Re-Compilations/sec''
			)
		) others 
		SELECT *, OrderNo = DENSE_RANK() OVER(PARTITION BY Description, ObjectName, CounterName ORDER BY CounterAvg)
		FROM Baseline_Summary
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetBaseline: {e}")
        return None, None


def getbatchresponsebaseline(conn):
    """
    T-SQL Source: GetBatchResponseBaseline
    Required Tables: CounterData, CounterDetails, cust_BatchResponseBaseline
    """
    required_tables = ['CounterData', 'CounterDetails', 'cust_BatchResponseBaseline']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetBatchResponseBaseline': Required tables not present.")
        return None, None
        
    query = """
AS
	CREATE TEMP TABLE temp_BatchResponses AS SELECT  @MachineName = udf_GetMachineName()
		SELECT * FROM cust_BatchResponseBaseline
			OBJECT_ID(''CounterDetails'') IS NOT NULL 
			SELECT
				CounterName, InstanceName,
    cast(AVG(cast(countervalue as REAL))as REAL), AS AverageValue
    MAX(CAST(countervalue as REAL)) AS MaxValue
			 FROM CounterData d
				JOIN CounterDetails dd ON d.CounterID = dd.CounterID
			WHERE ObjectName LIKE ''%Batch Resp Statistics''
				AND InstanceName IN(
			''Elapsed Time:Requests'',''Elapsed Time:Total(ms)''
			)
				AND MachineName = @MachineName
			GROUP BY CounterName, InstanceName
			SELECT
    btime.countername, AS BatchDuration
				AvgRunTimeMS = FORMAT(CAST((CASE WHEN bcount.MaxValue = 0 THEN 0 ELSE btime.MaxValue/bcount.MaxValue END) AS REAL), ''N'', ''en-us''),
				StatementCount = FORMAT(CAST(bcount.MaxValue AS INTEGER), ''N'', ''en-us''),
				TimePercent = CASE WHEN btime.MaxValue = 0 THEN 0 ELSE CAST((100.0 * btime.MaxValue / SUM (btime.MaxValue) OVER()) as REAL) END,
				CountPercent = CASE WHEN bcount.MaxValue = 0 THEN 0 ELSE CAST((100.0 * bcount.MaxValue / SUM (bcount.MaxValue) OVER()) as REAL) END
			FROM
				(
			SELECT *
				FROM #BatchResponses
				WHERE InstanceName = ''Elapsed Time:Requests''
			) bcount
				JOIN
				(
			SELECT *
				FROM #BatchResponses
				WHERE InstanceName = ''Elapsed Time:Total(ms)''
			) btime ON bcount.CounterName = btime.CounterName
			order by bcount.CounterName asc
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetBatchResponseBaseline: {e}")
        return None, None


def getblockedprocessoverview(conn):
    """
    T-SQL Source: GetBlockedProcessOverview
    Required Tables: CounterDetails, Counterdata
    """
    required_tables = ['CounterDetails', 'Counterdata']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetBlockedProcessOverview': Required tables not present.")
        return None, None
        
    query = """
AS
	SELECT @MachineName = udf_GetMachineName()
		OBJECT_ID(''Counterdata'') IS NOT NULL AND
		OBJECT_ID(''CounterDetails'') IS NOT NULL 
					SELECT
				CounterName,
    AVG(CounterValue), AS CounterAvg
    MIN(CounterValue), AS CounterMin
    MAX(CounterValue) AS CounterMax
			FROM Counterdata c
				JOIN CounterDetails d ON c.CounterID = d.CounterID
			WHERE 
    ''Processes blocked'' AS CounterName
				AND MachineName = @MachineName
			GROUP BY CounterName
		UNION ALL
			SELECT
    ''Lock waits (ms)'', AS CounterName
    AVG(CounterValue), AS CounterAvg
    MIN(CounterValue), AS CounterMin
    MAX(CounterValue) AS CounterMax
			FROM Counterdata c
				JOIN CounterDetails d ON c.CounterID = d.CounterID
			WHERE ObjectName LIKE ''%Wait Statistics'' AND
				InstanceName = ''Average wait time (ms)'' AND
    ''Lock waits'' AS CounterName
				AND MachineName = @MachineName
			GROUP BY CounterName
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetBlockedProcessOverview: {e}")
        return None, None


def getblocking(conn):
    """
    T-SQL Source: GetBlocking
    Required Tables: blocker, cust_NOTABLEACTIVEQUERIES, cust_NotableActiveQueries, cust_requests, tbl_NOTABLEACTIVEQUERIES, tbl_requests
    """
    required_tables = ['blocker', 'cust_NOTABLEACTIVEQUERIES', 'cust_NotableActiveQueries', 'cust_requests', 'tbl_NOTABLEACTIVEQUERIES', 'tbl_requests']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetBlocking': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''tbl_NOTABLEACTIVEQUERIES'') IS NOT NULL  AND
		@ServerType = ''OnPremisesSQL''
		WITH
			blocker
			AS
			(
				SELECT a.runtime, a.session_id, a.blocking_session_id, task_state, wait_type, resource_description, blockingresource = CAST('''' AS VARCHAR(4000)),
				stmt_text, blockingstmt = CAST('''' AS VARCHAR(4000)),
				0 as lvl
					FROM
						(
		SELECT
							rownos = ROW_NUMBER() OVER(PARTITION BY r.session_id ORDER BY r.session_id ASC),
							r.runtime,
							r.session_id, r.blocking_session_id, task_state, wait_type, resource_description, stmt_text
						FROM tbl_requests r
							JOIN tbl_NOTABLEACTIVEQUERIES n ON r.session_id = n.session_id AND r.runtime = n.runtime
						WHERE 
    0 AS blocking_session_id
							AND EXISTS(
			SELECT 1
							FROM tbl_requests ri
							WHERE ri.blocking_session_id = r.session_id
		)
	) a
					WHERE rownos = 1
				UNION ALL
					SELECT
						x.runtime, x.session_id, x.blocking_session_id, x.task_state, x.wait_type, x.resource_description, blockingresource = CAST( b.resource_description AS VARCHAR(4000)), x.stmt_text, blockingstmt = CAST(b.stmt_text AS VARCHAR(4000)),
						lvl + 1
					FROM blocker b
						JOIN
						(
		SELECT
							rownos = ROW_NUMBER() OVER(PARTITION BY r.session_id ORDER BY r.session_id ASC),
							r.runtime,
							r.session_id, r.blocking_session_id, task_state, wait_type, resource_description, stmt_text
						FROM tbl_requests r
							JOIN tbl_NOTABLEACTIVEQUERIES n ON r.session_id = n.session_id AND r.runtime = n.runtime
						WHERE 
		blocking_session_id != 0
	) x ON b.session_id = x.blocking_session_id AND b.runtime = x.runtime
			)
		SELECT *
		FROM blocker
		ORDER BY lvl, session_id
		option(maxrecursion
		3000)
		OBJECT_ID(''cust_NotableActiveQueries'') IS NOT NULL  AND
		@ServerType = ''OnPremisesSQL''
		WITH
			blocker
			AS
			(
				SELECT a.runtime, a.session_id, a.blocking_session_id, task_state, wait_type, resource_description, blockingresource = CAST('''' AS VARCHAR(4000)),
				stmt_text, blockingstmt = CAST('''' AS VARCHAR(4000)),
				0 as lvl
					FROM
						(
		SELECT
							rownos = ROW_NUMBER() OVER(PARTITION BY r.session_id ORDER BY r.session_id ASC),
							r.runtime,
							r.session_id, r.blocking_session_id, task_state, wait_type, resource_description, stmt_text
						FROM cust_requests r
							JOIN cust_NotableActiveQueries n ON r.session_id = n.session_id AND r.runtime = n.runtime
						WHERE 
    0 AS blocking_session_id
							AND EXISTS(
			SELECT 1
							FROM cust_requests ri
							WHERE ri.blocking_session_id = r.session_id
		)
	) a
					WHERE rownos = 1
				UNION ALL
					SELECT
						x.runtime, x.session_id, x.blocking_session_id, x.task_state, x.wait_type, x.resource_description, blockingresource = CAST( b.resource_description AS VARCHAR(4000)), x.stmt_text, blockingstmt = CAST(b.stmt_text AS VARCHAR(4000)),
						lvl + 1
					FROM blocker b
						JOIN
						(
		SELECT
							rownos = ROW_NUMBER() OVER(PARTITION BY r.session_id ORDER BY r.session_id ASC),
							r.runtime,
							r.session_id, r.blocking_session_id, task_state, wait_type, resource_description, stmt_text
						FROM cust_requests r
							JOIN cust_NOTABLEACTIVEQUERIES n ON r.session_id = n.session_id AND r.runtime = n.runtime
						WHERE 
		blocking_session_id != 0
	) x ON b.session_id = x.blocking_session_id AND b.runtime = x.runtime
			)
		SELECT *
		FROM blocker
		ORDER BY lvl, session_id
		option(maxrecursion
		3000)
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetBlocking: {e}")
        return None, None


def getblockingdata(conn):
    """
    T-SQL Source: GetBlockingData
    Required Tables: blocker, tbl_requests
    """
    required_tables = ['blocker', 'tbl_requests']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetBlockingData': Required tables not present.")
        return None, None
        
    query = """
AS
		@ServerType <> ''OnPremisesSQL''
		UPDATE tbl_requests 
		WHERE blocking_session_id = ''NULL''
		;WITH blocker
		AS
		(
		SELECT a.runtime, a.session_id, a.blocking_session_id, task_state, wait_type, resource_description, blockingresource = CAST('''' AS VARCHAR(4000)),
		stmt_text, blockingstmt = CAST('''' AS VARCHAR(4000)),
		0 as lvl
		FROM
		(
			SELECT
			rownos = ROW_NUMBER() OVER(PARTITION BY r.session_id ORDER BY r.session_id ASC),
			r.runtime,
			r.session_id, r.blocking_session_id, task_state, wait_type, resource_description, stmt_text
			FROM tbl_requests r
			WHERE 
    0 AS blocking_session_id
			AND EXISTS
			(
				SELECT *
				FROM tbl_requests ri
				WHERE ri.blocking_session_id = r.session_id
			)
		) a
		WHERE rownos = 1
		UNION ALL
		SELECT
		x.runtime, x.session_id, x.blocking_session_id, x.task_state, x.wait_type, x.resource_description, blockingresource = CAST( b.resource_description AS VARCHAR(4000)), x.stmt_text, blockingstmt = CAST(b.stmt_text AS VARCHAR(4000)),
		lvl + 1
		FROM blocker b
		JOIN
		(
			SELECT
			rownos = ROW_NUMBER() OVER(PARTITION BY r.session_id ORDER BY r.session_id ASC),
			r.runtime,
			r.session_id, r.blocking_session_id, task_state, wait_type, resource_description, stmt_text
			FROM tbl_requests r
			WHERE 
			blocking_session_id != 0
		) x ON b.session_id = x.blocking_session_id 
		)
		SELECT *
		FROM blocker
		ORDER BY lvl, session_id
		option(maxrecursion
		3000)
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetBlockingData: {e}")
        return None, None


def getblockingxedata(conn):
    """
    T-SQL Source: GetBlockingXEData
    Required Tables: tbl_BlockingXeOutput
    """
    required_tables = ['tbl_BlockingXeOutput']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetBlockingXEData': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''tbl_BlockingXeOutput'') IS NOT NULL 
		SELECT *
		FROM tbl_BlockingXeOutput
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetBlockingXEData: {e}")
        return None, None


def getbuffercachesummary(conn):
    """
    T-SQL Source: GetBufferCacheSummary
    Required Tables: SQLskills_BufferCacheSummary
    """
    required_tables = ['SQLskills_BufferCacheSummary']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetBufferCacheSummary': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM SQLskills_BufferCacheSummary
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetBufferCacheSummary: {e}")
        return None, None


def getbufferperfdata(conn):
    """
    T-SQL Source: GetBufferPerfData
    Required Tables: CounterDetails, Counterdata
    """
    required_tables = ['CounterDetails', 'Counterdata']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetBufferPerfData': Required tables not present.")
        return None, None
        
    query = """
AS
	SELECT @MachineName = udf_GetMachineName()
		OBJECT_ID(''Counterdata'') IS NOT NULL AND
		OBJECT_ID(''CounterDetails'') IS NOT NULL 
		SELECT
			ObjectName,
			CounterName,
			MachineName,
			CounterAvg = FORMAT(AVG(CounterValue), ''N''),
			CounterMin = FORMAT(MIN(CounterValue), ''N''),
			CounterMax = FORMAT(MAX(CounterValue), ''N'')
		FROM Counterdata c
			JOIN CounterDetails d ON c.CounterID = d.CounterID
		WHERE ObjectName LIKE ''%:Buffer Manager'' AND
			CounterName NOT IN
		(
		''Integral Controller Slope'',
		''Extension page evictions/sec'',
		''Extension page unreferenced time'',
		''Extension outstanding IO counter''
		)
			AND MachineName = @MachineName
		GROUP BY ObjectName, CounterName, MachineName
		ORDER BY CounterName
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetBufferPerfData: {e}")
        return None, None


def getconfigvaluestochange(conn):
    """
    T-SQL Source: GetConfigValuesToChange
    Required Tables: tbl_SPCONFIGURE
    """
    required_tables = ['tbl_SPCONFIGURE']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetConfigValuesToChange': Required tables not present.")
        return None, None
        
    query = """
AS
		CREATE TEMP TABLE temp_ConfigDefaults AS SELECT  *
		 FROM
			(
								SELECT ConfigValue =''cost threshold for parallelism ''	, DefaultValue =5
			UNION ALL
				SELECT ''max degree of parallelism ''	, 0
			UNION ALL
				SELECT ''optimize for ad hoc workloads ''	, 0 
	) x
		SELECT
    c.name, AS ConfigName
    run_value, AS CurrentRunValue
			DefaultValue
		FROM tbl_SPCONFIGURE c
			JOIN #ConfigDefaults d ON c.name = d.ConfigValue
		WHERE run_value = DefaultValue
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetConfigValuesToChange: {e}")
        return None, None


def getconnectivityrb(conn):
    """
    T-SQL Source: GetConnectivityRB
    Required Tables: tbl_connectivity_ring_buffer
    """
    required_tables = ['tbl_connectivity_ring_buffer']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetConnectivityRB': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''tbl_connectivity_ring_buffer'') IS NOT NULL 
		SELECT *
		FROM tbl_connectivity_ring_buffer
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetConnectivityRB: {e}")
        return None, None


def getcores_vs_maxdop(conn):
    """
    T-SQL Source: GetCores_vs_MaxDop
    Required Tables: SQLskills_Cores_vs_MaxDop
    """
    required_tables = ['SQLskills_Cores_vs_MaxDop']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetCores_vs_MaxDop': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM SQLskills_Cores_vs_MaxDop
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetCores_vs_MaxDop: {e}")
        return None, None


def getcursorusage(conn):
    """
    T-SQL Source: GetCursorUsage
    Required Tables: cust_Cursors
    """
    required_tables = ['cust_Cursors']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetCursorUsage': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''cust_Cursors'') IS NOT NULL
		SELECT
			runtime,
			count,
    open count, AS opencount
    oldest create, AS oldestcreate
    replace(replace(properties,''|'',''''),''(0)'','''') AS properties
		FROM cust_Cursors
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetCursorUsage: {e}")
        return None, None


def getdbconnectionstatistics(conn):
    """
    T-SQL Source: GetDBConnectionStatistics
    Required Tables: cust_dbconnectionstats
    """
    required_tables = ['cust_dbconnectionstats']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetDBConnectionStatistics': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT TOP 1000 *
		FROM cust_dbconnectionstats
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetDBConnectionStatistics: {e}")
        return None, None


def getdbdiskspace(conn):
    """
    T-SQL Source: GetDBDiskSpace
    Required Tables: cust_DBDiskSpace
    """
    required_tables = ['cust_DBDiskSpace']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetDBDiskSpace': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''cust_DBDiskSpace'') IS NOT NULL
		SELECT *
		FROM cust_DBDiskSpace
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetDBDiskSpace: {e}")
        return None, None


def getdbfileinfo(conn):
    """
    T-SQL Source: GetDBFileInfo
    Required Tables: cust_DBFileSizes
    """
    required_tables = ['cust_DBFileSizes']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetDBFileInfo': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM cust_DBFileSizes
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetDBFileInfo: {e}")
        return None, None


def getdbfirewallrules(conn):
    """
    T-SQL Source: GetDBFirewallRules
    Required Tables: cust_dbfirewallrules
    """
    required_tables = ['cust_dbfirewallrules']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetDBFirewallRules': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM cust_dbfirewallrules
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetDBFirewallRules: {e}")
        return None, None


def getdbinfo(conn):
    """
    T-SQL Source: GetDBInfo
    Required Tables: SQLskills_DBInfo
    """
    required_tables = ['SQLskills_DBInfo']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetDBInfo': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM SQLskills_DBInfo
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetDBInfo: {e}")
        return None, None


def getdbmirroring(conn):
    """
    T-SQL Source: GetDBMirroring
    Required Tables: cust_DatabaseMirroring
    """
    required_tables = ['cust_DatabaseMirroring']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetDBMirroring': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''cust_DatabaseMirroring'') IS NOT NULL 
		SELECT *
		FROM cust_DatabaseMirroring
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetDBMirroring: {e}")
        return None, None


def getdbresourcestats(conn):
    """
    T-SQL Source: GetDBResourceStats
    Required Tables: cust_DBResourceStats
    """
    required_tables = ['cust_DBResourceStats']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetDBResourceStats': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM cust_DBResourceStats
		WHERE DBName NOT IN(''tempdb'',''master'',''msdb'',''model'')
		ORDER BY DBName, end_time 
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetDBResourceStats: {e}")
        return None, None


def getdbscopedconfiguration(conn):
    """
    T-SQL Source: GetDBScopedConfiguration
    Required Tables: cust_dbscopedconfiguration
    """
    required_tables = ['cust_dbscopedconfiguration']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetDBScopedConfiguration': Required tables not present.")
        return None, None
        
    query = """
AS
			SELECT *
			FROM cust_dbscopedconfiguration
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetDBScopedConfiguration: {e}")
        return None, None


def getdbservicelevelagreement(conn):
    """
    T-SQL Source: GetDBServiceLevelAgreement
    Required Tables: cust_general_DBSLAs
    """
    required_tables = ['cust_general_DBSLAs']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetDBServiceLevelAgreement': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM cust_general_DBSLAs
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetDBServiceLevelAgreement: {e}")
        return None, None


def getdbwaitsforcapture(conn):
    """
    T-SQL Source: GetDBWaitsForCapture
    Required Tables: Waits, cust_DatabaseWaits
    """
    required_tables = ['Waits', 'cust_DatabaseWaits']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetDBWaitsForCapture': Required tables not present.")
        return None, None
        
    query = """
AS
		CREATE TEMP TABLE temp_WaitsForCapture AS SELECT 
			mx.wait_type,
    CAST(mx.waiting_tasks_count AS INTEGER)- CAST(mn.waiting_tasks_count AS INTEGER), AS waiting_tasks_count
    CAST(mx.wait_time_ms AS INTEGER)- CAST(mn.wait_time_ms AS INTEGER), AS wait_time_ms
    CAST(mx.signal_wait_time_ms AS INTEGER) - CAST(mn.signal_wait_time_ms AS INTEGER) AS signal_wait_time_ms
		 FROM
			(
			CREATE TEMP TABLE temp_TempWaiting AS SELECT  *
			from cust_DatabaseWaits
			where runtime = (select min(runtime)
			from cust_DatabaseWaits)
		) mn
			join
			(
			select *
			from cust_DatabaseWaits
			where runtime = (select max(runtime)
			from cust_DatabaseWaits)
		) mx on mn.wait_type = mx.wait_type
		;WITH
			Waits
			AS
			(
				SELECT
					wait_type,
					wait_time_ms / 1000.0 AS WaitS,
					(wait_time_ms - signal_wait_time_ms) / 1000.0 AS ResourceS,
					signal_wait_time_ms / 1000.0 AS SignalS,
					waiting_tasks_count AS WaitCount,
					100.0 * wait_time_ms / SUM (wait_time_ms) OVER() AS Percentage,
					ROW_NUMBER() OVER(ORDER BY wait_time_ms DESC) AS RowNum
				FROM #WaitsForCapture
				WHERE wait_type NOT IN (
				N''BROKER_EVENTHANDLER'',             N''BROKER_RECEIVE_WAITFOR'',
				N''BROKER_TASK_STOP'',                N''BROKER_TO_FLUSH'',
				N''BROKER_TRANSMITTER'',              N''CHECKPOINT_QUEUE'',
				N''CHKPT'',                           N''CLR_AUTO_EVENT'',
				N''CLR_MANUAL_EVENT'',                N''CLR_SEMAPHORE'',
				N''DBMIRROR_DBM_EVENT'',              N''DBMIRROR_EVENTS_QUEUE'',
				N''DBMIRROR_WORKER_QUEUE'',           N''DBMIRRORING_CMD'',
				N''DIRTY_PAGE_POLL'',                 N''DISPATCHER_QUEUE_SEMAPHORE'',
				N''EXECSYNC'',                        N''FSAGENT'',
				N''FT_IFTS_SCHEDULER_IDLE_WAIT'',     N''FT_IFTSHC_MUTEX'',
				N''HADR_CLUSAPI_CALL'',               N''HADR_FILESTREAM_IOMGR_IOCOMPLETION'',
				N''HADR_LOGCAPTURE_WAIT'',            N''HADR_NOTIFICATION_DEQUEUE'',
				N''HADR_TIMER_TASK'',                 N''HADR_WORK_QUEUE'',
				N''KSOURCE_WAKEUP'',                  N''LAZYWRITER_SLEEP'',
				N''LOGMGR_QUEUE'',                    N''ONDEMAND_TASK_QUEUE'',
				N''PWAIT_ALL_COMPONENTS_INITIALIZED'',
				N''QDS_PERSIST_TASK_MAIN_LOOP_SLEEP'',
				N''QDS_CLEANUP_STALE_QUERIES_TASK_MAIN_LOOP_SLEEP'',
				N''REQUEST_FOR_DEADLOCK_SEARCH'',     N''RESOURCE_QUEUE'',
				N''SERVER_IDLE_CHECK'',               N''SLEEP_BPOOL_FLUSH'',
				N''SLEEP_DBSTARTUP'',                 N''SLEEP_DCOMSTARTUP'',
				N''SLEEP_MASTERDBREADY'',             N''SLEEP_MASTERMDREADY'',
				N''SLEEP_MASTERUPGRADED'',            N''SLEEP_MSDBSTARTUP'',
				N''SLEEP_SYSTEMTASK'',                N''SLEEP_TASK'',
				N''SLEEP_TEMPDBSTARTUP'',             N''SNI_HTTP_ACCEPT'',
				N''SP_SERVER_DIAGNOSTICS_SLEEP'',     N''SQLTRACE_BUFFER_FLUSH'',
				N''SQLTRACE_INCREMENTAL_FLUSH_SLEEP'',
				N''SQLTRACE_WAIT_ENTRIES'',           N''WAIT_FOR_RESULTS'',
				N''WAITFOR'',                         N''WAITFOR_TASKSHUTDOWN'',
				N''WAIT_XTP_HOST_WAIT'',              N''WAIT_XTP_OFFLINE_CKPT_NEW_LOG'',
				N''WAIT_XTP_CKPT_CLOSE'',             N''XE_DISPATCHER_JOIN'',
				N''XE_DISPATCHER_WAIT'',              N''XE_TIMER_EVENT'', 
				''PREEMPTIVE_OS_WRITEFILE'', ''PREEMPTIVE_XE_DISPATCHER'', ''QDS_ASYNC_QUEUE'')
					AND waiting_tasks_count > 0
			)
		SELECT
			MAX (W1.wait_type) AS WaitType,
			CAST (MAX (W1.WaitS) AS REAL (16,2)) AS Wait_S,
			CAST (MAX (W1.ResourceS) AS REAL (16,2)) AS Resource_S,
			CAST (MAX (W1.SignalS) AS REAL (16,2)) AS Signal_S,
			MAX (W1.WaitCount) AS WaitCount,
			CAST (MAX (W1.Percentage) AS REAL (5,2)) AS Percentage,
			CAST ((MAX (W1.WaitS) / MAX (W1.WaitCount)) AS REAL (16,4)) AS AvgWait_S,
			CAST ((MAX (W1.ResourceS) / MAX (W1.WaitCount)) AS REAL (16,4)) AS AvgRes_S,
			CAST ((MAX (W1.SignalS) / MAX (W1.WaitCount)) AS REAL (16,4)) AS AvgSig_S
		 FROM Waits AS W1
			INNER JOIN Waits AS W2
			ON W2.RowNum <= W1.RowNum
		GROUP BY W1.RowNum
		HAVING SUM (W2.Percentage) - MAX (W1.Percentage) < 95;
		SELECT
			WaitType, WaitCount, Percentage, AvgWaitTimeSec = AvgWait_S
		FROM #TempWaiting
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetDBWaitsForCapture: {e}")
        return None, None


def getdatabaseinfo(conn):
    """
    T-SQL Source: GetDatabaseInfo
    Required Tables: cust_Databases, cust_databases
    """
    required_tables = ['cust_Databases', 'cust_databases']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetDatabaseInfo': Required tables not present.")
        return None, None
        
    query = """
AS
	SELECT Flag = ''The is_auto_close_on setting on database '' + name + '' is enabled.''
			FROM cust_Databases
			WHERE is_auto_close_on = ''1'' OR is_auto_close_on = ''True''
		UNION ALL
			SELECT ''The is_auto_shrink_on setting on database '' + name + '' is enabled.''
			FROM cust_Databases
			WHERE is_auto_shrink_on = ''1'' OR is_auto_shrink_on = ''True''
		UNION ALL
			SELECT ''The database '' + name + '' is in standby recovery mode.''
			FROM cust_Databases
			WHERE is_in_standby = ''1'' OR is_in_standby = ''True''
		UNION ALL
			SELECT ''The is_read_committed_snapshot_on setting on database '' + name + '' is enabled.''
			FROM cust_Databases
			WHERE is_read_committed_snapshot_on = ''1'' OR is_read_committed_snapshot_on = ''True''
		UNION ALL
			SELECT ''The is_auto_create_stats_on setting on database '' + name + '' is disabled.''
			FROM cust_Databases
			WHERE is_auto_create_stats_on = ''0'' OR is_auto_create_stats_on = ''False''
		UNION ALL
			SELECT ''The is_auto_create_stats_on setting on database '' + name + '' is disabled.''
			FROM cust_Databases
			WHERE (is_auto_update_stats_on = ''0'' AND is_auto_update_stats_async_on = ''False'')
		UNION ALL
			SELECT ''The is_recursive_triggers_on setting on database '' + name + '' is enabled.''
			FROM cust_Databases
			WHERE is_recursive_triggers_on = ''1'' OR is_recursive_triggers_on = ''True''
		UNION ALL
			SELECT ''The is_trustworthy_on setting on database '' + name + '' is enabled.''
			FROM cust_Databases
			WHERE (is_trustworthy_on = ''1'' OR is_trustworthy_on = ''True'') AND database_id >4
		UNION ALL
			SELECT ''The database '' + name + '' is enabled for database ownership chaining.''
			FROM cust_Databases
			WHERE (is_db_chaining_on = ''1'' OR is_db_chaining_on = ''True'') AND database_id > 4
		UNION ALL
			SELECT ''The is_parameterization_forced setting on database '' + name + '' is enabled.''
			FROM cust_Databases
			WHERE is_parameterization_forced = ''1'' OR is_parameterization_forced = ''True''
		UNION ALL
			SELECT ''The is_master_key_encrypted_by_server setting on database '' + name + '' is enabled.''
			FROM cust_Databases
			WHERE (is_master_key_encrypted_by_server = ''1'' OR is_master_key_encrypted_by_server = ''True'') AND database_id > 4
		UNION ALL
			SELECT ''The database '' + name + '' is acting as a replication publisher.''
			FROM cust_Databases
			WHERE is_published = ''1'' OR is_published = ''True''
		UNION ALL
			SELECT ''The database '' + name + '' is acting as a replication subscriber.''
			FROM cust_Databases
			WHERE is_subscribed = ''1'' OR is_subscribed = ''True''
		UNION ALL
			SELECT ''The database '' + name + '' is participating in merge replication.''
			FROM cust_Databases
			WHERE is_merge_published = ''1'' OR is_merge_published = ''True''
		UNION ALL
			SELECT ''The database '' + name + '' is enabled for replication distribution.''
			FROM cust_Databases
			WHERE is_distributor = ''1'' OR is_distributor = ''True''
		UNION ALL
			SELECT ''The is_sync_with_backup setting on database '' + name + '' is enabled.''
			FROM cust_Databases
			WHERE is_sync_with_backup = ''1'' OR is_sync_with_backup = ''True''
		UNION ALL
			SELECT ''The is_broker_enabled setting on database '' + name + '' is enabled.''
			FROM cust_Databases
			WHERE is_broker_enabled = ''1'' OR is_broker_enabled = ''True''
		UNION ALL
			SELECT ''The is_date_correlation_on setting on database '' + name + '' is enabled.''
			FROM cust_Databases
			WHERE is_date_correlation_on = ''1'' OR is_date_correlation_on = ''True''
		UNION ALL
			SELECT ''The is_cdc_enabled setting on database '' + name + '' is enabled.''
			FROM cust_Databases
			WHERE is_cdc_enabled = ''1'' OR is_cdc_enabled = ''True''
		UNION ALL
			SELECT ''The is_encrypted setting on database '' + name + '' is enabled.''
			FROM cust_Databases
			WHERE is_encrypted = ''1'' OR is_encrypted = ''True''
		UNION ALL
			SELECT ''Database '' + name + '' is a database snapshot of database '' + (SELECT name
				FROM cust_databases ii
				WHERE ii.database_id = dd.source_database_id) + ''.''
			FROM cust_databases dd
			WHERE (source_database_id IS NOT NULL AND source_database_id <> ''NULL'')
		UNION ALL
			SELECT ''The database '' + name + '' is not set to allow multiple user connections.''
			FROM cust_databases
			WHERE user_access_desc <> ''MULTI_USER''
		UNION ALL
			SELECT ''The database '' + name + '' is not currently online.''
			FROM cust_databases
			WHERE state_desc <> ''ONLINE''
		UNION ALL
			SELECT ''The database '' + name + '' has Snapshot Isolation enabled.''
			FROM cust_databases
			WHERE snapshot_isolation_state_desc = ''ON''
		UNION ALL
			SELECT ''The page verify option on database '' + name + '' is not set to Checksum.''
			FROM cust_databases
			WHERE page_verify_option_desc <> ''CHECKSUM''
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetDatabaseInfo: {e}")
        return None, None


def getdatabasemirroringdata(conn):
    """
    T-SQL Source: GetDatabaseMirroringData
    Required Tables: CounterDetails, Counterdata
    """
    required_tables = ['CounterDetails', 'Counterdata']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetDatabaseMirroringData': Required tables not present.")
        return None, None
        
    query = """
AS
			SELECT
			ObjectName,
			CounterName,
			InstanceName ,
    MAX(CounterValue) AS CounterMax
		FROM Counterdata c
			JOIN CounterDetails d ON c.CounterID = d.CounterID
		WHERE ObjectName LIKE ''%Mirror%''
		GROUP BY 
				ObjectName, 
				CounterName,
				InstanceName
		HAVING MAX(CounterValue) > 0
		)
			SELECT
				ObjectName,
				CounterName,
				InstanceName ,
				CounterAvg = FORMAT(AVG(CounterValue), ''N''),
				CounterMin = FORMAT(MIN(CounterValue), ''N''),
				CounterMax = FORMAT(MAX(CounterValue), ''N'')
			FROM Counterdata c
				JOIN CounterDetails d ON c.CounterID = d.CounterID
			WHERE ObjectName LIKE ''%Mirror%''
			GROUP BY 
			ObjectName, 
			CounterName,
			InstanceName
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetDatabaseMirroringData: {e}")
        return None, None


def getdatabaseperfdata(conn):
    """
    T-SQL Source: GetDatabasePerfData
    Required Tables: CounterDetails, Counterdata
    """
    required_tables = ['CounterDetails', 'Counterdata']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetDatabasePerfData': Required tables not present.")
        return None, None
        
    query = """
AS
	SELECT @MachineName = udf_GetMachineName()
		OBJECT_ID(''Counterdata'') IS NOT NULL AND
		OBJECT_ID(''CounterDetails'') IS NOT NULL 
		SELECT
			ObjectName,
			CounterName,
			InstanceName,
			CounterAvg = FORMAT(AVG(CounterValue), ''N''),
			CounterMin = FORMAT(MIN(CounterValue), ''N''),
			CounterMax = FORMAT(MAX(CounterValue), ''N'')
		FROM Counterdata c
			JOIN CounterDetails d ON c.CounterID = d.CounterID
		WHERE ObjectName LIKE ''%Databases'' AND InstanceName <> ''_Total''
			AND MachineName = @MachineName
		GROUP BY ObjectName, CounterName, InstanceName
		ORDER BY CounterName, InstanceName
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetDatabasePerfData: {e}")
        return None, None


def getdeadlocks(conn):
    """
    T-SQL Source: GetDeadlocks
    Required Tables: Execution, tbl_DeadlockReport
    """
    required_tables = ['Execution', 'tbl_DeadlockReport']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetDeadlocks': Required tables not present.")
        return None, None
        
    query = """
AS
	CREATE TABLE #Deadlock
	(
		DeadlockID INT IDENTITY PRIMARY KEY CLUSTERED,
		UTCTimeStamp DATETIME,
		LocalTimeStamp DATETIME,
		DeadlockGraph XML
	)
		INSERT INTO #Deadlock
			(UTCTimeStamp, LocalTimeStamp, DeadlockGraph)
		CREATE TEMP TABLE temp_Victims AS SELECT  UTCTimeStamp, timestamp, c1
		FROM tbl_DeadlockReport
		SELECT
    Victims.List.value(''@id'', ''varchar(50)'') AS ID
		 FROM
			#Deadlock CTE
			CROSS APPLY CTE.DeadlockGraph.nodes(''//deadlock/victim-list/victimProcess'') AS Victims (List)
		CREATE TEMP TABLE temp_DeadlockLocks AS SELECT 
			CTE.DeadlockID,
			UTCTimeStamp,
			LocalTimeStamp,
			MainLock.Process.value(''@id'', ''varchar(100)'') AS LockID,
			OwnerList.Owner.value(''@id'', ''varchar(200)'') AS LockProcessId,
			REPLACE(MainLock.Process.value(''local-name(.)'', ''varchar(100)''), ''lock'', '''') AS LockEvent,
			MainLock.Process.value(''@objectname'', ''sysname'') AS ObjectName,
			OwnerList.Owner.value(''@mode'', ''varchar(10)'') AS LockMode,
			MainLock.Process.value(''@dbid'', ''INTEGER'') AS Database_id,
			MainLock.Process.value(''@associatedObjectId'', ''INTEGER'') AS AssociatedObjectId,
			MainLock.Process.value(''@WaitType'', ''varchar(100)'') AS WaitType,
			WaiterList.Owner.value(''@id'', ''varchar(200)'') AS WaitProcessId,
			WaiterList.Owner.value(''@mode'', ''varchar(10)'') AS WaitMode
		 FROM
			#Deadlock CTE
			CROSS APPLY CTE.DeadlockGraph.nodes(''//deadlock/resource-list'') AS Lock (list)
			CROSS APPLY Lock.list.nodes(''*'') AS MainLock (Process)
			OUTER APPLY MainLock.Process.nodes(''owner-list/owner'') AS OwnerList (Owner)
			CROSS APPLY MainLock.Process.nodes(''waiter-list/waiter'') AS WaiterList (Owner)
		CREATE TEMP TABLE temp_Process AS SELECT 
			CTE.DeadlockID,
			UTCTimeStamp,
			LocalTimeStamp,
			Victim = CONVERT(BIT, CASE WHEN Deadlock.Process.value(''@id'', ''varchar(50)'') = ifnull(Deadlock.Process.value(''../../@victim'', ''varchar(50)''), v.ID) 
											THEN 1
    Deadlock.Process.value(''@lockMode'', ''varchar(10)''), AS LockMode
    Process.ID, AS ProcessID
    Deadlock.Process.value(''@kpid'', ''INTEGER''), AS KPID
    Deadlock.Process.value(''@spid'', ''INTEGER''), AS SPID
    Deadlock.Process.value(''@sbid'', ''INTEGER''), AS SBID
    Deadlock.Process.value(''@ecid'', ''INTEGER''), AS ECID
    Deadlock.Process.value(''@isolationlevel'', ''varchar(200)''), AS IsolationLevel
    Deadlock.Process.value(''@waitresource'', ''varchar(200)''), AS WaitResource
    Deadlock.Process.value(''@logused'', ''INTEGER''), AS LogUsed
    Deadlock.Process.value(''@clientapp'', ''varchar(100)''), AS ClientApp
    Deadlock.Process.value(''@hostname'', ''varchar(20)''), AS HostName
    Deadlock.Process.value(''@loginname'', ''varchar(20)''), AS LoginName
    Deadlock.Process.value(''@lasttranstarted'', ''datetime''), AS TransactionTime
    Deadlock.Process.value(''@lastbatchstarted'', ''datetime''), AS BatchStarted
    Deadlock.Process.value(''@lastbatchcompleted'', ''datetime''), AS BatchCompleted
    Input.Buffer.value(''.'', ''varchar(2000)''), AS InputBuffer
			es.ExecutionStack,
    NULLIF(ExecStack.Stack.value(''.'', ''varchar(max)''), ''''), AS QueryStatement
    SUM(1) OVER (PARTITION BY CTE.DeadlockID), AS ProcessQty
    Deadlock.Process.value(''@trancount'', ''INTEGER'') AS TranCount
		 FROM
			#Deadlock CTE
			CROSS APPLY CTE.DeadlockGraph.nodes(''//deadlock/process-list/process'') AS Deadlock (Process)
			CROSS APPLY (SELECT Deadlock.Process.value(''@id'', ''varchar(50)'') ) AS Process (ID)
			LEFT JOIN #Victims v ON Process.ID = v.ID
			CROSS APPLY Deadlock.Process.nodes(''inputbuf'') AS Input (Buffer)
			CROSS APPLY Deadlock.Process.nodes(''executionStack'') AS Execution (Frame)
			CROSS APPLY 
			(
				SELECT ExecutionStack = 
				(
					SELECT
    ROW_NUMBER() OVER (PARTITION BY CTE.DeadlockID, AS ProcNumber
							Deadlock.Process.value(''@id'', ''varchar(50)''),
							Execution.Stack.value(''@procname'', ''sysname''),
							Execution.Stack.value(''@code'', ''varchar(MAX)'') 
							ORDER BY (SELECT 1)),
    Execution.Stack.value(''@procname'', ''sysname''), AS ProcName
    Execution.Stack.value(''@line'', ''INTEGER''), AS Line
					SQLHandle = Execution.Stack.value(''@sqlhandle'', ''varchar(64)''),
    LTRIM(RTRIM(Execution.Stack.value(''.'', ''varchar(MAX)''))) AS Code
				FROM Execution.Frame.nodes(''frame'') AS Execution (Stack)
				ORDER BY ProcNumber
				FOR XML PATH(''frame''), ROOT(''executionStack''), TYPE 
				)
			) es
			CROSS APPLY Execution.Frame.nodes(''frame'') AS ExecStack (Stack)
		SELECT DISTINCT
			p.DeadlockID,
			p.UTCTimeStamp,
			p.LocalTimeStamp,
			p.Victim,
			p.ProcessQty,
    DENSE_RANK() AS ProcessNbr
							OVER (PARTITION BY p.DeadlockId 
									ORDER BY p.ProcessID),
			p.LockMode,
    NULLIF(l.ObjectName, ''''), AS LockedObject
			l.database_id,
			l.AssociatedObjectId,
    p.ProcessID, AS LockProcess
			p.KPID,
			p.SPID,
			p.SBID,
			p.ECID,
			p.TranCount,
			l.LockEvent,
    l.LockMode, AS LockedMode
			l.WaitProcessID,
			l.WaitMode,
			p.WaitResource,
			l.WaitType,
			p.IsolationLevel,
			p.LogUsed,
			p.ClientApp,
			p.HostName,
			p.LoginName,
			p.TransactionTime,
			p.BatchStarted,
			p.BatchCompleted,
			p.QueryStatement,
			p.InputBuffer
		FROM
			#Process p
			LEFT JOIN #DeadlockLocks l ON 
				p.DeadlockID = l.DeadlockID AND
				p.ProcessID = l.LockProcessID
		ORDER BY 
			p.DeadlockId,
			p.Victim DESC,
			p.ProcessId;
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetDeadlocks: {e}")
        return None, None


def getdeprecatedfeatueres(conn):
    """
    T-SQL Source: GetDeprecatedFeatueres
    Required Tables: cust_DeprecatedFeatures
    """
    required_tables = ['cust_DeprecatedFeatures']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetDeprecatedFeatueres': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''cust_DeprecatedFeatures'') IS NOT NULL
		SELECT
    instance_name, AS Feature
    CAST(cntr_value AS INTEGER) AS UsageCount
		FROM cust_DeprecatedFeatures
		WHERE
			CAST(cntr_value AS INTEGER) > 0
		ORDER BY CAST(cntr_value AS INTEGER) DESC
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetDeprecatedFeatueres: {e}")
        return None, None


def getdiskinfo(conn):
    """
    T-SQL Source: GetDiskInfo
    Required Tables: cust_MSInfo
    """
    required_tables = ['cust_MSInfo']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetDiskInfo': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT DriveInfo = InfoDesc, *
		FROM cust_MSInfo
		WHERE Cate
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetDiskInfo: {e}")
        return None, None


def getdisklatency(conn):
    """
    T-SQL Source: GetDiskLatency
    Required Tables: CounterData, CounterDetails
    """
    required_tables = ['CounterData', 'CounterDetails']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetDiskLatency': Required tables not present.")
        return None, None
        
    query = """
AS
	SELECT @MachineName = udf_GetMachineName()
		OBJECT_ID(''CounterDetails'') IS NOT NULL 
		SELECT
			CounterName, InstanceName,
    cast(AVG(cast(countervalue as REAL))as REAL), AS AverageLatency
    MAX(CAST(countervalue as REAL)) AS MaxLatency
		FROM CounterData d
			JOIN CounterDetails dd ON d.CounterID = dd.CounterID
		WHERE dd.countername IN(''Avg. Disk sec/Read'', ''Avg. Disk sec/Write'')
			AND ObjectName = ''LogicalDisk''
			AND InstanceName <> ''_Total''
			AND MachineName = @MachineName
		GROUP BY CounterName, InstanceName
		ORDER BY AverageLatency DESC
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetDiskLatency: {e}")
        return None, None


def getdisklatencyinfo(conn):
    """
    T-SQL Source: GetDiskLatencyInfo
    Required Tables: SQLskills_DiskLatencyInfo
    """
    required_tables = ['SQLskills_DiskLatencyInfo']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetDiskLatencyInfo': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM SQLskills_DiskLatencyInfo
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetDiskLatencyInfo: {e}")
        return None, None


def getdiskoverview(conn):
    """
    T-SQL Source: GetDiskOverview
    Required Tables: CounterDetails, Counterdata, cust_DBFileSizes
    """
    required_tables = ['CounterDetails', 'Counterdata', 'cust_DBFileSizes']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetDiskOverview': Required tables not present.")
        return None, None
        
    query = """
AS
	CREATE TEMP TABLE temp_DiskPerf AS SELECT  @MachineName = udf_GetMachineName()
		OBJECT_ID(''Counterdata'') IS NOT NULL AND
		OBJECT_ID(''CounterDetails '') IS NOT NULL 
		CREATE TABLE #DBDrives
		(
			BaseDrive VARCHAR(MAX),
			FileList VARCHAR(MAX)
		)
			INSERT INTO #DBDrives
			SELECT BaseDrive, FileList = REVERSE(SUBSTRING(LTRIM(REVERSE(FileList)), 2, LEN(FileList)-1))
			FROM
				(
			SELECT BaseDrive = LEFT(FilePath, 2),
    ( AS FileList
				SELECT LogicalName + '', ''
					FROM cust_DBFileSizes i
					WHERE LEFT(i.FilePath, 2) = LEFT(o.FilePath, 2)
					FOR XML PATH('''')
			)
				FROM cust_DBFileSizes o
				GROUP BY LEFT(FilePath, 2)
		) x
			INSERT INTO #DBDrives
			SELECT BaseDrive = '''', FileList = ''''
			FROM (SELECT t = 1)x
		SELECT
			CounterName = CASE WHEN CounterName LIKE ''% Bytes%'' THEN REPLACE(CounterName, ''Bytes'', ''KBytes'') ELSE CounterName END,
     AS Description
		CASE
			WHEN CounterName = ''Avg. Disk Bytes/Transfer'' THEN ''Average IO Size''
			WHEN CounterName = ''Avg. Disk Bytes/Read'' THEN ''Average Read IO Size''
			WHEN CounterName = ''Avg. Disk Bytes/Write'' THEN ''Average Write IO Size''
			WHEN CounterName = ''Disk Writes/sec'' THEN ''Write IOs per second''
			WHEN CounterName = ''Disk Reads/sec'' THEN ''Read IOs per second''
			WHEN CounterName = ''Disk Transfers/sec'' THEN ''Total IOs per second''
			WHEN CounterName = ''% Disk Read Time'' THEN ''% Work spent servicing read requests''
			WHEN CounterName = ''% Disk Write Time'' THEN ''% Work spent servicing write requests''
			WHEN CounterName = ''% Disk Time'' THEN ''% Work spent servicing all requests''
			WHEN CounterName = ''Split IO/Sec'' THEN ''Measures NTFS non-contiguous file segments IO requests''
			WHEN CounterName = ''Avg. Disk sec/Read'' THEN ''Disk Read latency''
			WHEN CounterName = ''Avg. Disk sec/Transfer'' THEN ''Total Disk latency''
			WHEN CounterName = ''Avg. Disk sec/Write'' THEN ''Disk Write latency''
			WHEN CounterName = ''Current Disk Queue Length'' THEN ''IOs Currently Waiting''
			WHEN CounterName = ''Avg. Disk Queue Length'' THEN ''Average IOs Waiting''
			WHEN CounterName = ''Avg. Disk Write Queue Length'' THEN ''Average Write IOs Waiting''
			WHEN CounterName = ''Avg. Disk Read Queue Length'' THEN ''Average Read IOs Waiting''
			WHEN CounterName = ''Disk Bytes/sec'' THEN ''Disk Transfer Rate''
			WHEN CounterName = ''Disk Read Bytes/sec'' THEN ''Disk Read Transfer Rate''
			WHEN CounterName = ''Disk Write Bytes/sec'' THEN ''Disk Write Transfer Rate''
			WHEN CounterName = ''% Free Space'' THEN ''Amount of free space on disk''
			WHEN CounterName = ''% Idle Time'' THEN ''% of time disk is not servicing requests''
			InstanceName,
			CounterAvg = CASE WHEN CounterName LIKE ''% Bytes%'' THEN AVG(CounterValue)/1024.0 ELSE AVG(CounterValue) END,
			CounterMin = CASE WHEN CounterName LIKE ''% Bytes%'' THEN MIN(CounterValue)/1024.0 ELSE MIN(CounterValue) END,
			CounterMax = CASE WHEN CounterName LIKE ''% Bytes%'' THEN MAX(CounterValue)/1024.0 ELSE MAX(CounterValue) END
		 FROM Counterdata c
			JOIN CounterDetails d ON c.CounterID = d.CounterID
		WHERE ObjectName = ''LogicalDisk'' AND
			InstanceName <> ''_Total''
			AND MachineName = @MachineName
		GROUP BY CounterName, InstanceName
		ORDER BY InstanceName, CounterName
		SELECT p.*, SQLFileList = d.FileList
		FROM #DiskPerf p
			LEFT JOIN #DBDrives d on p.InstanceName = d.BaseDrive
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetDiskOverview: {e}")
        return None, None


def getenabledtraceflags(conn):
    """
    T-SQL Source: GetEnabledTraceFlags
    Required Tables: cust_TraceFlags
    """
    required_tables = ['cust_TraceFlags']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetEnabledTraceFlags': Required tables not present.")
        return None, None
        
    query = """
AS
SELECT *
	FROM cust_TraceFlags
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetEnabledTraceFlags: {e}")
        return None, None


def geterrorlog(conn):
    """
    T-SQL Source: GetErrorLog
    Required Tables: 
    """
    required_tables = []
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetErrorLog': Required tables not present.")
        return None, None
        
    query = """

    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetErrorLog: {e}")
        return None, None


def geterrorlogerrors(conn):
    """
    T-SQL Source: GetErrorLogErrors
    Required Tables: cust_ErrorLogAnalysis, sys
    """
    required_tables = ['cust_ErrorLogAnalysis', 'sys']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetErrorLogErrors': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT
			ErrorNumber,
			First_Logged_Date,
			Last_Logged_Date,
			Error_Count,
			ErrorMessage = Logged_Message + CASE WHEN ErrorNumber IS NULL THEN '''' ELSE '' '' +
				(
				SELECT text
			FROM sys.messages m
			WHERE language_id = 1033 AND
				m.message_id = x.ErrorNumber AND
				x.ErrorNumber IS NOT NULL
				) END
		FROM
			(
				SELECT
				Logged_Message,
				First_Logged_Date,
				Last_Logged_Date,
				Error_Count,
				ErrorNumber = 
					CASE 
					WHEN Logged_Message LIKE ''% Error: %, Severity: %, State: %.'' 
						THEN SUBSTRING(Logged_Message, CHARINDEX(''Error: '' , Logged_Message) + 7, (CHARINDEX('','' , Logged_Message)-CHARINDEX(''Error: '' , Logged_Message)-7))
			FROM cust_ErrorLogAnalysis
			WHERE 
				(
					Logged_Message LIKE ''%error%'' OR
				Logged_Message LIKE ''%fail%'' OR
				Logged_Message LIKE ''%paged%'' OR
				Logged_Message LIKE ''%timeout%'' OR
				Logged_Message LIKE ''%insufficient%'' OR
				Logged_Message LIKE ''%invalid%'' OR
				Logged_Message LIKE ''%unable%'' OR
				Logged_Message LIKE ''%overflow%'' OR
				Logged_Message LIKE ''%corrupt%''
				) AND
				(
					Logged_Message NOT LIKE ''%0 errors%'' AND
				Logged_Message NOT LIKE ''%without errors%''AND
				Logged_Message NOT LIKE ''%clientoption2%'' AND
				Logged_Message NOT LIKE ''%Login failed for%'' AND
				Logged_Message NOT LIKE ''%Backup Database backed up. Database: %Error%%'' AND
				Logged_Message NOT LIKE ''%Starting up database ''''%Error%''''%'' AND
				Logged_Message NOT LIKE ''%This is an informational message only%No user action is required.%'' AND
				Logged_Message NOT LIKE ''%Server Logging SQL Server messages in file%'' AND
				Logged_Message NOT LIKE ''%Logging SQL Server messages in file %'' AND
				Logged_Message NOT LIKE ''%The error log has been reinitialized%'' AND
				Logged_Message NOT LIKE ''%See the previous log for older entries%''  AND
				Logged_Message NOT LIKE ''%Attempting to cycle error log%'' AND
				Logged_Message NOT LIKE ''spid% Error: %, Severity: %, State: __'' AND
				Logged_Message NOT LIKE ''spid% Error: %, Severity: %, State: _'' AND
				Logged_Message NOT LIKE ''Backup Error: %, Severity: %, State: _''AND
				Logged_Message NOT LIKE ''Lo
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetErrorLogErrors: {e}")
        return None, None


def getexpensivequeries(conn):
    """
    T-SQL Source: GetExpensiveQueries
    Required Tables: cust_expensivequeries, tbl_query_store_plan, tbl_query_store_query, tbl_query_store_query_text, tbl_query_store_runtime_stats
    """
    required_tables = ['cust_expensivequeries', 'tbl_query_store_plan', 'tbl_query_store_query', 'tbl_query_store_query_text', 'tbl_query_store_runtime_stats']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetExpensiveQueries': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''tbl_query_store_runtime_stats'') IS NOT NULL AND
		OBJECT_ID(''tbl_query_store_plan'') IS NOT NULL AND
		OBJECT_ID(''tbl_query_store_query'') IS NOT NULL AND
		OBJECT_ID(''tbl_query_store_query_text'') IS NOT NULL 
		SELECT DISTINCT TOP(1000)
			q.dbname,
			first_execution_time, q.last_execution_time,
    CAST(avg_duration AS FLOAT)/1000000.00, AS avg_durationSec
    CAST(min_duration AS FLOAT)/1000000.00, AS min_durationSec
    CAST(max_duration AS FLOAT)/1000000.00, AS max_durationSec
    cast(avg_logical_io_reads AS FLOAT), min_logical_io_reads, max_logical_io_reads, AS avg_logical_io_reads
			min_dop, max_dop,
			min_rowcount, max_rowcount,
			query_parameterization_type_desc,
			execution_type_desc,
			count_executions,
			query_hash,
			query_plan_hash,
			query_sql_text
		from
			tbl_query_store_runtime_stats q
			join tbl_query_store_plan p on q.dbid = p.dbid and q.plan_id = p.plan_id
			join tbl_query_store_query qq on p.dbid = qq.dbid and p.query_id = qq.query_id
			join tbl_query_store_query_text qt on qt.dbid = qq.dbid and qt.query_text_id = qq.query_text_id
		order by cast(avg_logical_io_reads as float) desc
		SELECT *
		FROM cust_expensivequeries
		ORDER BY AverageRunTimeSeconds desc
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetExpensiveQueries: {e}")
        return None, None


def getfailedvarules(conn):
    """
    T-SQL Source: GetFailedVARules
    Required Tables: 
    """
    required_tables = []
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetFailedVARules': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT DatabaseName, Platform, Cate
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetFailedVARules: {e}")
        return None, None


def getfilelatencyinfo(conn):
    """
    T-SQL Source: GetFileLatencyInfo
    Required Tables: SQLskills_FileLatencyInfo
    """
    required_tables = ['SQLskills_FileLatencyInfo']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetFileLatencyInfo': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM SQLskills_FileLatencyInfo
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetFileLatencyInfo: {e}")
        return None, None


def getfindimplicitconversions(conn):
    """
    T-SQL Source: GetFindImplicitConversions
    Required Tables: SQLskills_FindImplicitConversions
    """
    required_tables = ['SQLskills_FindImplicitConversions']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetFindImplicitConversions': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM SQLskills_FindImplicitConversions
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetFindImplicitConversions: {e}")
        return None, None


def getgeneralstatsperfdata(conn):
    """
    T-SQL Source: GetGeneralStatsPerfData
    Required Tables: CounterDetails, Counterdata
    """
    required_tables = ['CounterDetails', 'Counterdata']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetGeneralStatsPerfData': Required tables not present.")
        return None, None
        
    query = """
AS
	SELECT @MachineName = udf_GetMachineName()
		OBJECT_ID(''Counterdata'') IS NOT NULL AND
		OBJECT_ID(''CounterDetails'') IS NOT NULL 
		SELECT
			ObjectName,
			CounterName,
			MachineName,
			CounterAvg = FORMAT(AVG(CounterValue), ''N''),
			CounterMin = FORMAT(MIN(CounterValue), ''N''),
			CounterMax = FORMAT(MAX(CounterValue), ''N'')
		FROM Counterdata c
			JOIN CounterDetails d ON c.CounterID = d.CounterID
		WHERE ObjectName LIKE ''%General Statistics'' AND
			CounterName IN
		(
		''Active Temp Tables'',
		''Logical Connections'',
		''Logins/sec'',
		''Lo
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetGeneralStatsPerfData: {e}")
        return None, None


def getgeoreplication(conn):
    """
    T-SQL Source: GetGeoReplication
    Required Tables: cust_AzureGeoRepl
    """
    required_tables = ['cust_AzureGeoRepl']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetGeoReplication': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM cust_AzureGeoRepl
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetGeoReplication: {e}")
        return None, None


def getiosubsystem(conn):
    """
    T-SQL Source: GetIOSubsystem
    Required Tables: tbl_IO_SUBSYSTEM
    """
    required_tables = ['tbl_IO_SUBSYSTEM']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetIOSubsystem': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''tbl_IO_SUBSYSTEM'') IS NOT NULL 
		SELECT
			timestamp, component_state,
			ioLatchTimeouts, intervalLongIos, totalLongIos, longestPendingRequests_duration,
			longestPendingRequests_filePath
		FROM tbl_IO_SUBSYSTEM
		WHERE longestPendingRequests_duration > 0
		ORDER BY longestPendingRequests_duration DESC
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetIOSubsystem: {e}")
        return None, None


def getindexcounts(conn):
    """
    T-SQL Source: GetIndexCounts
    Required Tables: SQLskills_IndexCounts
    """
    required_tables = ['SQLskills_IndexCounts']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetIndexCounts': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM SQLskills_IndexCounts
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetIndexCounts: {e}")
        return None, None


def getindexdetail(conn):
    """
    T-SQL Source: GetIndexDetail
    Required Tables: cust_IndexDetail, cust_IndexOperations, cust_UnusedIndexes
    """
    required_tables = ['cust_IndexDetail', 'cust_IndexOperations', 'cust_UnusedIndexes']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetIndexDetail': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''cust_IndexOperations'') IS NOT NULL AND
		OBJECT_ID(''cust_UnusedIndexes'') IS NOT NULL 
		SELECT DISTINCT
			d.DBName, d.TableName, d.IndexName, d.IndexColumns, d.IncludedColumns, d.IndexType, d.IsUnique,
			d.IsPrimaryKey, d.FillFact, d.IgnoreDupKey, d.IsUniqueConstraint, d.IsDisabled, d.IsHypothetical,
			d.AllowRowLocks, d.AllowPageLocks
		FROM cust_IndexDetail d
			LEFT JOIN cust_IndexOperations o ON d.DBName = o.DBName AND d.TableName = o.TableName and d.IndexName = o.IndexName
			LEFT JOIN cust_UnusedIndexes u ON d.DBName = u.DatabaseName AND d.TableName = u.TableName and d.IndexName = u.IndexName
		ORDER BY d.DBName, d.TableName
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetIndexDetail: {e}")
        return None, None


def getindexdetails(conn):
    """
    T-SQL Source: GetIndexDetails
    Required Tables: SQLskills_IndexDetails
    """
    required_tables = ['SQLskills_IndexDetails']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetIndexDetails': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM SQLskills_IndexDetails
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetIndexDetails: {e}")
        return None, None


def getindexusageforobject(conn):
    """
    T-SQL Source: GetIndexUsageForObject
    Required Tables: SQLskills_IndexUsageForObject
    """
    required_tables = ['SQLskills_IndexUsageForObject']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetIndexUsageForObject': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM SQLskills_IndexUsageForObject
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetIndexUsageForObject: {e}")
        return None, None


def getlastbackupinfo(conn):
    """
    T-SQL Source: GetLastBackupInfo
    Required Tables: SQLskills_LastBackupInfo
    """
    required_tables = ['SQLskills_LastBackupInfo']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetLastBackupInfo': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM SQLskills_LastBackupInfo
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetLastBackupInfo: {e}")
        return None, None


def getlastcheckdbdate(conn):
    """
    T-SQL Source: GetLastCheckDBDate
    Required Tables: SQLskills_LastCheckDBDate
    """
    required_tables = ['SQLskills_LastCheckDBDate']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetLastCheckDBDate': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM SQLskills_LastCheckDBDate
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetLastCheckDBDate: {e}")
        return None, None


def getlatchwaits(conn):
    """
    T-SQL Source: GetLatchWaits
    Required Tables: Latches, cust_latchwaits
    """
    required_tables = ['Latches', 'cust_latchwaits']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetLatchWaits': Required tables not present.")
        return None, None
        
    query = """
AS
		WITH
			Latches
			AS
			(
				SELECT
					latch_class,
					cast(wait_time_ms as INTEGER)  / 1000.0 AS WaitS,
					cast(waiting_requests_count as INTEGER) AS WaitCount,
					100.0 * cast(wait_time_ms as INTEGER) / SUM (cast(wait_time_ms as INTEGER)) OVER() AS Percentage,
					ROW_NUMBER() OVER(ORDER BY cast(wait_time_ms as INTEGER) DESC) AS RowNum
				FROM cust_latchwaits
				WHERE latch_class NOT IN (
	N''BUFFER'')
					AND cast(wait_time_ms as INTEGER)> 0
			)
		SELECT
			W1.latch_class AS LatchClass,
			CAST (W1.WaitS AS REAL(14, 2)) AS Wait_S,
			W1.WaitCount AS WaitCount,
			CAST (W1.Percentage AS REAL(14, 2)) AS Percentage,
			CAST ((W1.WaitS / W1.WaitCount) AS REAL (14, 4)) AS AvgWait_S
		FROM Latches AS W1
			INNER JOIN Latches AS W2 ON W2.RowNum <= W1.RowNum
		WHERE W1.WaitCount > 0
		GROUP BY W1.RowNum, W1.latch_class, W1.WaitS, W1.WaitCount, W1.Percentage
		HAVING SUM (W2.Percentage) - W1.Percentage < 95;
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetLatchWaits: {e}")
        return None, None


def getlockinfo(conn):
    """
    T-SQL Source: GetLockInfo
    Required Tables: CounterDetails, Counterdata
    """
    required_tables = ['CounterDetails', 'Counterdata']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetLockInfo': Required tables not present.")
        return None, None
        
    query = """
AS
	SELECT @MachineName = udf_GetMachineName()
		OBJECT_ID(''Counterdata'') IS NOT NULL AND
		OBJECT_ID(''CounterDetails'') IS NOT NULL 
		SELECT
			ObjectName,
			CounterName,
    AVG(CounterValue), AS CounterAvg
    MIN(CounterValue), AS CounterMin
    MAX(CounterValue) AS CounterMax
		FROM Counterdata c
			JOIN CounterDetails d ON c.CounterID = d.CounterID
		WHERE ObjectName LIKE ''%Locks%''
			AND MachineName = @MachineName
		GROUP BY ObjectName, CounterName
		ORDER BY CounterName
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetLockInfo: {e}")
        return None, None


def getlocking(conn):
    """
    T-SQL Source: GetLocking
    Required Tables: cust_Locking
    """
    required_tables = ['cust_Locking']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetLocking': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM cust_Locking
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetLocking: {e}")
        return None, None


def getloginfo(conn):
    """
    T-SQL Source: GetLogInfo
    Required Tables: cust_LogInfo
    """
    required_tables = ['cust_LogInfo']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetLogInfo': Required tables not present.")
        return None, None
        
    query = """
AS
		CREATE TEMP TABLE temp_TempLogInfo AS SELECT  DBName, VLFCount = SUM(CAST(VLFCount AS INTEGER))
		 FROM cust_LogInfo
		GROUP BY DBName
		HAVING SUM(CAST(VLFCount AS INTEGER))  > @VLFThreshold
		SELECT *
		FROM #TempLogInfo
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetLogInfo: {e}")
        return None, None


def getlogreuse(conn):
    """
    T-SQL Source: GetLogReuse
    Required Tables: cust_Databases
    """
    required_tables = ['cust_Databases']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetLogReuse': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT name, log_reuse_wait_desc
		FROM cust_Databases
		WHERE log_reuse_wait_desc <> ''NOTHING''
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetLogReuse: {e}")
        return None, None


def getmaintenanceplans(conn):
    """
    T-SQL Source: GetMaintenancePlans
    Required Tables: SQLskills_MaintenancePlans
    """
    required_tables = ['SQLskills_MaintenancePlans']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetMaintenancePlans': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM SQLskills_MaintenancePlans
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetMaintenancePlans: {e}")
        return None, None


def getmanagedinstanceresourcestats(conn):
    """
    T-SQL Source: GetManagedInstanceResourceStats
    Required Tables: cust_serverresourcestats
    """
    required_tables = ['cust_serverresourcestats']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetManagedInstanceResourceStats': Required tables not present.")
        return None, None
        
    query = """
AS
	SELECT 
		start_time
		,end_time
		,cpu = cast(avg_cpu_percent as REAL)
		,cast(reserved_storage_mb as REAL)/1024.0 as ReservedStorageGB
		,cast(storage_space_used_mb as REAL)/1024.0 as StorageUsedGB
		,io_requests
		,io_bytes_read
		,io_bytes_written
	FROM cust_serverresourcestats
	WHERE DATEADD(DAY, -3, GETDATE()) < start_time
	ORDER BY start_time asc
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetManagedInstanceResourceStats: {e}")
        return None, None


def getmemmanagerperfdata(conn):
    """
    T-SQL Source: GetMemManagerPerfData
    Required Tables: CounterDetails, Counterdata
    """
    required_tables = ['CounterDetails', 'Counterdata']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetMemManagerPerfData': Required tables not present.")
        return None, None
        
    query = """
AS
	CREATE TEMP TABLE temp_MemoryManager AS SELECT  @MachineName = udf_GetMachineName()
		OBJECT_ID(''Counterdata'') IS NOT NULL AND
		OBJECT_ID(''CounterDetails'') IS NOT NULL 
		SELECT
			ObjectName,
			CounterName,
			MachineName,
    AVG(CounterValue), AS CounterAvg
    MIN(CounterValue), AS CounterMin
    MAX(CounterValue) AS CounterMax
		 FROM Counterdata c
			JOIN CounterDetails d ON c.CounterID = d.CounterID
		WHERE ObjectName LIKE ''%Memory Manager''
			AND MachineName = @MachineName
		GROUP BY ObjectName, CounterName, MachineName
		SELECT *
		FROM #MemoryManager
		ORDER BY CounterName
			SELECT @Pending = CAST(CounterAvg AS REAL)
			FROM #MemoryManager
			WHERE CounterName = ''Memory Grants Pending''
				INSERT INTO PTOClinicFindings
					(Title,Cate
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetMemManagerPerfData: {e}")
        return None, None


def getmembershippermissions(conn):
    """
    T-SQL Source: GetMembershipPermissions
    Required Tables: cust_MembershipPermissions
    """
    required_tables = ['cust_MembershipPermissions']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetMembershipPermissions': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM cust_MembershipPermissions
		WHERE GranteeName IN(''sysadmin'', ''SecurityAdmin'', ''db_owner'') and
			GrantorName NOT IN(''dbo'', ''sa'')
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetMembershipPermissions: {e}")
        return None, None


def getmemoryclerksummary(conn):
    """
    T-SQL Source: GetMemoryClerkSummary
    Required Tables: SQLskills_MemoryClerkSummary
    """
    required_tables = ['SQLskills_MemoryClerkSummary']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetMemoryClerkSummary': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM SQLskills_MemoryClerkSummary
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetMemoryClerkSummary: {e}")
        return None, None


def getmemoryconfiguration(conn):
    """
    T-SQL Source: GetMemoryConfiguration
    Required Tables: CounterData, CounterDetails, cust_JobObjects, cust_MSInfo, cust_OSInfo, cust_SPConfigure, tbl_SPCONFIGURE, tbl_ServerProperties
    """
    required_tables = ['CounterData', 'CounterDetails', 'cust_JobObjects', 'cust_MSInfo', 'cust_OSInfo', 'cust_SPConfigure', 'tbl_SPCONFIGURE', 'tbl_ServerProperties']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetMemoryConfiguration': Required tables not present.")
        return None, None
        
    query = """
AS
	CREATE TEMP TABLE temp_TempMemConfig AS SELECT  @MachineName = udf_GetMachineName()
	CREATE TABLE #SPConfigure
	(
		name varchar(50),
		run_value varchar(250)
	)
		INSERT INTO #SPConfigure
		SELECT *
		FROM tbl_SPCONFIGURE
		WHERE replace(run_value, ''-'', '''') <> '''' AND isnumeric(run_value)=1
		INSERT INTO #SPConfigure
		SELECT *
		FROM cust_SPConfigure
		WHERE replace(value_in_use, ''-'', '''') <> '''' AND isnumeric(value_in_use)=1
	SELECT
		ServerMemoryInMB = CAST(0 AS REAL),
		MaxServerMemoryInMB = MaxServerMemory,
		OSMemory = CAST(0 AS REAL),
		PercentageForOS = CAST(0 AS REAL),
    CAST(0 AS REAL), MinMBytes= CAST(0 AS REAL), MaxMBytes= CAST(0 AS REAL) AS AvgMBytes
	 FROM
	(
		SELECT
			MaxServerMemory = MAX(CAST(run_value AS INTEGER))
		FROM #SPConfigure
		WHERE name in(''max server memory (MB)'')
	) mem
		UPDATE t
			FROM cust_OSInfo)
		FROM #TempMemConfig t
		SELECT
			@ServerMemoryMB = 
		CASE 
			WHEN Metric = ''GB'' THEN CAST(Val AS NUMERIC)*1024.00
			WHEN Metric = ''TB'' THEN CAST(Val AS NUMERIC)*1024.00*1024.00
		FROM
			(
		SELECT
    udf_CleanUpString(CAST(LTRIM(RTRIM(LEFT(Mem, CHARINDEX('' '', Mem)))) AS VARCHAR(20))), AS Val
    SUBSTRING(Mem, CHARINDEX('' '', Mem)+1, 2) AS Metric
			FROM
				(
			SELECT Mem = REPLACE((LTRIM(RTRIM(REPLACE(InfoDesc, ''Total Physical Memory'', '''')))),'','',''.'')
				FROM cust_MSInfo
				WHERE InfoDesc LIKE ''%Total Physical Memory%''
				)x
			) y
			SELECT @ServerMemoryMB = CAST(PropertyValue AS INTEGER)/1024.0
			FROM tbl_ServerProperties
			WHERE PropertyName = ''physical_memory_kb''
	UPDATE t
		ServerMemoryInMB = ifnull(@ServerMemoryMB, ServerMemoryInMB)
	FROM #TempMemConfig t
	UPDATE t
	PercentageForOS = CASE WHEN MaxServerMemoryInMB > ServerMemoryInMB THEN 0 ELSE ((ServerMemoryInMB - MaxServerMemoryInMB) / ServerMemoryInMB) * 100 END,
	OSMemory = CASE WHEN MaxServerMemoryInMB > ServerMemoryInMB THEN 0 ELSE (ServerMemoryInMB - MaxServerMemoryInMB) END
	FROM #TempMemConfig t
	OBJECT_ID(''CounterDetails'') IS NOT NULL AND
	OBJECT_ID(''tbl_SCRIPT_ENVIRONMENT_DETAILS'') IS NOT NULL
		UPDATE t
    x.MinMBytes, AS MinMBytes
    x.MaxMBytes AS MaxMBytes
		FROM #TempMemConfig t
		CROSS JOIN 
		(
			SELECT
    avg(FirstValueA), MinMBytes = MIN(FirstValueA), MaxMBytes = max(FirstValueA) AS AvgMBytes
				FROM CounterData
				WHERE CounterID =(
			SELECT CounterID
				FROM CounterDetails
				WHERE countername = ''Available MBytes'' AND
    REPLACE(@MachineName, ''\\'', '''') AS MachineName
			)
		)x
			SELECT
				ServerMemoryInGB = ServerMemoryInMB/1024.0,
				MaxServerMemoryInGB = MaxServerMemoryInMB/1024.0, 
				x.*
			FROM #TempMemConfig
			CROSS JOIN
			(
				SELECT 
					memory_limit_gb = CAST(memory_limit_mb AS INTEGER)/1024.0, 
					process_memory_limit_gb = CAST(process_memory_limit_mb AS INTEGER)/1024.0, 
    CAST(non_sos_mem_gap_mb AS INTEGER)/1024.0, AS non_sos_mem_gap_gb
    CAST(low_mem_signal_threshold_mb AS INTEGER)/1024.0, AS low_mem_signal_threshold_gb
					peak_job_memory_used_gb = CAST(peak_job_memory_used_mb AS INTEGER)/1024.0, 
					peak_process_memory_used_gb = CAST(peak_process_memory_used_mb AS INTEGER)/1024.0
				FROM cust_JobObjects
			) x
			SELECT
				ServerMemoryInGB = ServerMemoryInMB/1024.0,
				MaxServerMemoryInGB = MaxServerMemoryInMB/1024.0
			FROM #TempMemConfig
		SELECT
			ServerMemoryInGB = ServerMemoryInMB/1024.0,
			MaxServerMemoryInGB = MaxServerMemoryInMB/1024.0,
			OSMemoryInGB = OSMemory/1024.0,
			PercentageForOS,
			AvgMBytes,
			MinMBytes,
			MaxMBytes
		FROM #TempMemConfig
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetMemoryConfiguration: {e}")
        return None, None


def getmemoryconsumers(conn):
    """
    T-SQL Source: GetMemoryConsumers
    Required Tables: cust_MemoryClerks
    """
    required_tables = ['cust_MemoryClerks']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetMemoryConsumers': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT
    CAST((100.0 * (CAST(Pages_KB AS INTEGER)) / SUM (CAST(Pages_KB AS INTEGER)) OVER()) AS REAL), AS MemPercentage
			Rnk = ROW_NUMBER() OVER(ORDER BY CAST(Pages_KB AS INTEGER) DESC), 
    CAST(Pages_KB AS INTEGER)/128.00/1024, AS SizeInGB
			*
		FROM cust_MemoryClerks
		WHERE type <> ''USERSTORE_TOKENPERM''
			AND pages_kb > 250
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetMemoryConsumers: {e}")
        return None, None


def getmemorygrants(conn):
    """
    T-SQL Source: GetMemoryGrants
    Required Tables: 
    """
    required_tables = []
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetMemoryGrants': Required tables not present.")
        return None, None
        
    query = """

    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetMemoryGrants: {e}")
        return None, None


def getmemoryperfdata(conn):
    """
    T-SQL Source: GetMemoryPerfData
    Required Tables: CounterDetails, Counterdata
    """
    required_tables = ['CounterDetails', 'Counterdata']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetMemoryPerfData': Required tables not present.")
        return None, None
        
    query = """
AS
	SELECT @MachineName = udf_GetMachineName()
		OBJECT_ID(''Counterdata'') IS NOT NULL AND
		OBJECT_ID(''CounterDetails'') IS NOT NULL 
		SELECT
			ObjectName,
			CounterName,
			MachineName,
			CounterAvg = FORMAT(AVG(CounterValue), ''N''),
			CounterMin = FORMAT(MIN(CounterValue), ''N''),
			CounterMax = FORMAT(MAX(CounterValue), ''N'')
		FROM Counterdata c
			JOIN CounterDetails d ON c.CounterID = d.CounterID
		WHERE ObjectName = ''Memory'' AND
			CounterName IN
		(
		''Available MBytes'',
		''Commit Limit'',
		''Page Faults/sec'',
		''Page Reads/sec'',
		''Page Writes/sec'',
		''Pages Input/sec'',
		''Pages Output/sec'',
		''Pages/sec'',
		''Free System Page Table Entries'',
		''% Committed Bytes In Use''
		)
			AND MachineName = @MachineName
		GROUP BY ObjectName, CounterName, MachineName
		ORDER BY CounterName
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetMemoryPerfData: {e}")
        return None, None


def getmemoryresources(conn):
    """
    T-SQL Source: GetMemoryResources
    Required Tables: tbl_Resource
    """
    required_tables = ['tbl_Resource']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetMemoryResources': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''tbl_Resource'') IS NOT NULL 
		SELECT
			timestamp, state, LastNotification, available_physical_memory/(1024*1024) as AvailableMemory_MB,
			working_set/(1024*1024) as WorkingSet_MB ,
			available_virtual_memory/(1024*1024) as available_virtual_memory_MB,
			Target_committed_kb/1024 as TargetMemory_MB,
			current_committed_kb/1024 as TotalMemoryMB,
			Pages_free_kb/1024 as PagesFree_MB,
			Pages_allocated_kb/1024 as PagesAllocated_MB,
			Pages_in_use_kb/1024 as Pages_in_use_MB,
			locked_pages_allocated_kb/1024 as locked_pages_allocated_MB,
			large_pages_allocated_kb /1024  as large_pages_allocated_MB,
			outOfMemoryExceptions, isAnyPoolOutOfMemory, processOutOfMemoryPeriod,
			percent_workingset_committed,
			page_faults
		sys_physical_memory_high , sys_physical_memory_low ,
			process_phyiscal_memory_low , process_virtual_memory_low
		FROM tbl_Resource
		ORDER BY TIMESTAMP ASC
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetMemoryResources: {e}")
        return None, None


def getmissingindexes(conn):
    """
    T-SQL Source: GetMissingIndexes
    Required Tables: SQLskills_MissingIndexes
    """
    required_tables = ['SQLskills_MissingIndexes']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetMissingIndexes': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM SQLskills_MissingIndexes
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetMissingIndexes: {e}")
        return None, None


def getmostexpensivequeries(conn):
    """
    T-SQL Source: GetMostExpensiveQueries
    Required Tables: SQLskills_MostExpensiveQueries
    """
    required_tables = ['SQLskills_MostExpensiveQueries']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetMostExpensiveQueries': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM SQLskills_MostExpensiveQueries
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetMostExpensiveQueries: {e}")
        return None, None


def getnetworkdata(conn):
    """
    T-SQL Source: GetNetworkData
    Required Tables: CounterDetails, Counterdata
    """
    required_tables = ['CounterDetails', 'Counterdata']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetNetworkData': Required tables not present.")
        return None, None
        
    query = """
AS
	CREATE TEMP TABLE temp_Temp AS SELECT  @MachineName = udf_GetMachineName()
		OBJECT_ID(''Counterdata'') IS NOT NULL AND
		OBJECT_ID(''CounterDetails'') IS NOT NULL 
		SELECT
			ObjectName,
			CounterName,
    AVG(CounterValue), AS CounterAvg
    MIN(CounterValue), AS CounterMin
    MAX(CounterValue) AS CounterMax
		 FROM Counterdata c
			JOIN CounterDetails d ON c.CounterID = d.CounterID
		WHERE 
			ObjectName LIKE ''Network Interface%'' AND
			CounterName NOT LIKE ''Packets%'' AND
			CounterName NOT LIKE ''Output%''
			AND MachineName = @MachineName
		GROUP BY ObjectName, CounterName
		ORDER BY CounterName
		SELECT
			CounterName, CounterAvg, AvgPercentOfCapacity = (CounterAvg/MaxNetworkBandwidth)*100,
			MaxPercentOfCapacity = (CounterMax/MaxNetworkBandwidth)*100, MaxNetworkBandwidth
		FROM #Temp t
		CROSS APPLY
		(
			SELECT MaxNetworkBandwidth = CounterMax
			FROM #Temp
			WHERE CounterName = ''Current Bandwidth''
		)x
		WHERE CounterName LIKE ''Bytes%''
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetNetworkData: {e}")
        return None, None


def getnondefaultsettings(conn):
    """
    T-SQL Source: GetNonDefaultSettings
    Required Tables: triggers
    """
    required_tables = ['triggers']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetNonDefaultSettings': Required tables not present.")
        return None, None
        
    query = """
AS
		CREATE TEMP TABLE temp_ConfigDefaults AS SELECT  *
		 FROM
			(
																																																																																																																																																																																						SELECT ConfigValue = ''access check cache bucket count'' 	, DefaultValue = 0
			UNION ALL
				SELECT ''access check cache quota'' 	, 0
			UNION ALL
				SELECT ''ad hoc distributed queries'' 	, 0
			UNION ALL
				SELECT ''affinity I/O mask'' 	, 0
			UNION ALL
				SELECT ''affinity64 I/O mask'' 	, 0
			UNION ALL
				SELECT ''affinity mask'' 	, 0
			UNION ALL
				SELECT ''affinity64 mask''	, 0
			UNION ALL
				SELECT ''automatic soft-NUMA disabled''	, 0
			UNION ALL
				SELECT ''backup checksum default''	, 0
			UNION ALL
				SELECT ''backup compression default''	, 0
			UNION ALL
				SELECT ''blocked process threshold ''	, 0
			UNION ALL
				SELECT ''c2 audit mode ''	, 0
			UNION ALL
				SELECT ''clr enabled''	, 0
			UNION ALL
				SELECT ''common criteria compliance enabled ''	, 0
			UNION ALL
				SELECT ''contained database authentication''	, 0
			UNION ALL
				SELECT ''cost threshold for parallelism ''	, 5
			UNION ALL
				SELECT ''cross db ownership chaining''	, 0
			UNION ALL
				SELECT ''cursor threshold '', -1
			UNION ALL
				SELECT ''default full-text language ''	, 1033
			UNION ALL
				SELECT ''default language''	, 0
			UNION ALL
				SELECT ''default trace enabled ''	, 1
			UNION ALL
				SELECT ''disallow results from triggers ''	, 0
			UNION ALL
				SELECT ''EKM provider enabled''	, 0
			UNION ALL
				SELECT ''external scripts enabled ''	, 0
			UNION ALL
				SELECT ''filestream access level''	, 0
			UNION ALL
				SELECT ''fill factor (%)''	, 0
			UNION ALL
				SELECT ''index create memory (KB)''	, 0
			UNION ALL
				SELECT ''in-doubt xact resolution ''	, 0
			UNION ALL
				SELECT ''lightweight pooling ''	, 0
			UNION ALL
				SELECT ''locks''	, 0
			UNION ALL
				SELECT ''max degree of parallelism ''	, 0
			UNION ALL
				SELECT ''max full-text crawl range ''	, 4
			UNION ALL
				SELECT ''max text repl size''	, 65536
			UNION ALL
				SELECT ''max worker threads ''	, 0
			UNION ALL
				SELECT ''media retention ''	, 0
			UNION ALL
				SELECT ''min memory per query (KB)''	, 1024
			UNION ALL
				SELECT ''nested triggers''	, 1
			UNION ALL
				SELECT ''network packet size (B)''	, 4096
			UNION ALL
				SELECT ''Ole Automation Procedures ''	, 0
			UNION ALL
				SELECT ''open objects''	, 0
			UNION ALL
				SELECT ''PH_timeout ''	, 60
			UNION ALL
				SELECT ''PolyBase Hadoop and Azure blob storage ''	, 0
			UNION ALL
				SELECT ''precompute rank ''	, 0
			UNION ALL
				SELECT ''priority boost ''	, 0
			UNION ALL
				SELECT ''query 
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetNonDefaultSettings: {e}")
        return None, None


def getnotableactivequeries(conn):
    """
    T-SQL Source: GetNotableActiveQueries
    Required Tables: cust_NotableActiveQueries, cust_Requests
    """
    required_tables = ['cust_NotableActiveQueries', 'cust_Requests']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetNotableActiveQueries': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT 
    CAST(plan_total_logical_reads as INTEGER)/cast(plan_total_exec_count as INTEGER),* AS AvgLogicalReads
		FROM cust_Requests r
		JOIN cust_NotableActiveQueries q ON r.runtime = q.runtime AND r.session_id = q.session_id
		WHERE plan_total_exec_count <> ''NULL''
		ORDER BY AvgLogicalReads DESC
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetNotableActiveQueries: {e}")
        return None, None


def getobjectpermissions(conn):
    """
    T-SQL Source: GetObjectPermissions
    Required Tables: cust_ObjectPermissions
    """
    required_tables = ['cust_ObjectPermissions']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetObjectPermissions': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM cust_ObjectPermissions
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetObjectPermissions: {e}")
        return None, None


def getoptimizerinfo(conn):
    """
    T-SQL Source: GetOptimizerInfo
    Required Tables: cust_OptimizerInfo
    """
    required_tables = ['cust_OptimizerInfo']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetOptimizerInfo': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM cust_OptimizerInfo
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetOptimizerInfo: {e}")
        return None, None


def getple(conn):
    """
    T-SQL Source: GetPLE
    Required Tables: cust_AzurePLE
    """
    required_tables = ['cust_AzurePLE']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetPLE': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM cust_AzurePLE
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetPLE: {e}")
        return None, None


def getptoclinicfindings(conn):
    """
    T-SQL Source: GetPTOClinicFindings
    Required Tables: tbl_FileStats
    """
    required_tables = ['tbl_FileStats']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetPTOClinicFindings': Required tables not present.")
        return None, None
        
    query = """
(
	@PrintRules BIT = 0
)
AS
    SELECT @executiondatetime= MIN(runtime) FROM tbl_FileStats
     INSERT INTO PTOClinicFindings (Title,Cate
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetPTOClinicFindings: {e}")
        return None, None


def getpendingios(conn):
    """
    T-SQL Source: GetPendingIOs
    Required Tables: cust_PendingIOs
    """
    required_tables = ['cust_PendingIOs']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetPendingIOs': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''cust_PendingIOs'') IS NOT NULL 
		CREATE TEMP TABLE temp_pendingIOs AS SELECT  io_handle_path, io_offset, io_user_data_address, io_completion_request_address
		 FROM cust_PendingIOs
		GROUP BY io_handle_path, io_offset, io_user_data_address, io_completion_request_address
		HAVING(COUNT(*) > 1)
		SELECT o.*
		FROM #pendingIOs p
		JOIN cust_PendingIOs o ON
		p.io_handle_path = o.io_handle_path AND
		p.io_offset = o.io_offset AND
		p.io_user_data_address = o.io_user_data_address AND
		p.io_completion_request_address = o.io_completion_request_address
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetPendingIOs: {e}")
        return None, None


def getperprocessorusage(conn):
    """
    T-SQL Source: GetPerProcessorUsage
    Required Tables: CounterData, CounterDetails
    """
    required_tables = ['CounterData', 'CounterDetails']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetPerProcessorUsage': Required tables not present.")
        return None, None
        
    query = """
AS
	SELECT @MachineName = udf_GetMachineName()
		OBJECT_ID(''CounterDetails'') IS NOT NULL 
		SELECT
			CounterName, InstanceName,
    cast(AVG(cast(countervalue as REAL))as REAL), AS AverageCPU
    MAX(CAST(countervalue as REAL)), AS MaxCPU
    STDEV(CAST(countervalue as REAL)) AS CPUStDev
		FROM CounterData d
			JOIN CounterDetails dd ON d.CounterID = dd.CounterID
		WHERE 
			dd.ObjectName IN(''Processor Information'') AND
			CounterName LIKE ''% Processor Time'' AND
    @MachineName AS MachineName
		GROUP BY CounterName, InstanceName
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetPerProcessorUsage: {e}")
        return None, None


def getpercentaggrowthfiles(conn):
    """
    T-SQL Source: GetPercentagGrowthFiles
    Required Tables: cust_DBFileSizes
    """
    required_tables = ['cust_DBFileSizes']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetPercentagGrowthFiles': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM cust_DBFileSizes
		WHERE Growth LIKE ''%%%'' AND
			DBName NOT IN(''master'',''model'',''msdb'')
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetPercentagGrowthFiles: {e}")
        return None, None


def getpossibleparamsniffing(conn):
    """
    T-SQL Source: GetPossibleParamSniffing
    Required Tables: tbl_query_store_plan, tbl_query_store_query, tbl_query_store_query_text, tbl_query_store_runtime_stats
    """
    required_tables = ['tbl_query_store_plan', 'tbl_query_store_query', 'tbl_query_store_query_text', 'tbl_query_store_runtime_stats']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetPossibleParamSniffing': Required tables not present.")
        return None, None
        
    query = """
AS
	OBJECT_ID(''tbl_query_store_runtime_stats'') IS NOT NULL AND
		OBJECT_ID(''tbl_query_store_plan'') IS NOT NULL AND
		OBJECT_ID(''tbl_query_store_query'') IS NOT NULL AND
		OBJECT_ID(''tbl_query_store_query_text'') IS NOT NULL 
	CREATE TEMP TABLE temp_Sniffing AS SELECT  * 
	 FROM (
		SELECT DISTINCT TOP(1000)
			q.dbname,
			first_execution_time, q.last_execution_time,
    CAST(avg_duration AS FLOAT)/1000000.00, AS avg_durationSec
    CAST(min_duration AS FLOAT)/1000000.00, AS min_durationSec
    CAST(max_duration AS FLOAT)/1000000.00, AS max_durationSec
    CAST(avg_logical_io_reads AS FLOAT), min_logical_io_reads, max_logical_io_reads, AS avg_logical_io_reads
			min_dop, max_dop,
			min_rowcount, max_rowcount,
			query_parameterization_type_desc,
			execution_type_desc,
			count_executions,
			query_hash,
			query_plan_hash,
			query_sql_text
		FROM
			tbl_query_store_runtime_stats q
			join tbl_query_store_plan p on q.dbid = p.dbid and q.plan_id = p.plan_id
			join tbl_query_store_query qq on p.dbid = qq.dbid and p.query_id = qq.query_id
			join tbl_query_store_query_text qt on qt.dbid = qq.dbid and qt.query_text_id = qq.query_text_id
		WHERE 
			query_sql_text like ''%@%'' AND
			CAST(max_logical_io_reads AS FLOAT) > 100000 AND
			((CAST(max_logical_io_reads AS FLOAT) - CAST(min_logical_io_reads AS FLOAT) )/CAST(max_logical_io_reads AS FLOAT)) *100.00 > 50
		) a
		ORDER BY 
			avg_logical_io_reads  DESC
		SELECT *
		FROM #Sniffing
		ORDER BY 
			avg_logical_io_reads  DESC
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetPossibleParamSniffing: {e}")
        return None, None


def getpowersettings(conn):
    """
    T-SQL Source: GetPowerSettings
    Required Tables: tbl_PowerPlan
    """
    required_tables = ['tbl_PowerPlan']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetPowerSettings': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''tbl_PowerPlan'') IS NOT NULL 
		SELECT ActivePlanName
		FROM tbl_PowerPlan
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetPowerSettings: {e}")
        return None, None


def getprocessinfo(conn):
    """
    T-SQL Source: GetProcessInfo
    Required Tables: CounterData, CounterDetails
    """
    required_tables = ['CounterData', 'CounterDetails']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetProcessInfo': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''CounterDetails'') IS NOT NULL 
		CREATE TEMP TABLE temp_CounterInfo AS SELECT 
			InstanceName,
    AVG(CounterValue), AS AVGDataBytes
    MAX(CounterValue) AS MaxDataBytes
		 FROM
			CounterData d
			JOIN CounterDetails dd ON d.CounterID = dd.CounterID
		WHERE 
			dd.countername = ''IO Data Bytes/sec'' AND
			ObjectName = ''Process'' AND
			InstanceName <> ''_Total''
		GROUP BY InstanceName
		DELETE FROM #CounterInfo
		WHERE AVGDataBytes = 0
		SELECT TOP(5)
			*, DataBytesPercentage = (AVGDataBytes/(SELECT SUM(AVGDataBytes)
			FROM #CounterInfo)*1.00)*100.00
		FROM #CounterInfo
		ORDER BY AVGDataBytes DESC
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetProcessInfo: {e}")
        return None, None


def getprocessperfdata(conn):
    """
    T-SQL Source: GetProcessPerfData
    Required Tables: CounterDetails, Counterdata
    """
    required_tables = ['CounterDetails', 'Counterdata']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetProcessPerfData': Required tables not present.")
        return None, None
        
    query = """
AS
	CREATE TEMP TABLE temp_CounterTemp AS SELECT  @MachineName = udf_GetMachineName()
		OBJECT_ID(''Counterdata'') IS NOT NULL AND
		OBJECT_ID(''CounterDetails'') IS NOT NULL 
		SELECT
			CounterName,
			InstanceName,
			MachineName,
    AVG(CounterValue), AS CounterAvg
    MIN(CounterValue), AS CounterMin
    MAX(CounterValue) AS CounterMax
		 FROM Counterdata c
			JOIN CounterDetails d ON c.CounterID = d.CounterID
		WHERE ObjectName = ''Process'' AND CounterName NOT IN(
		''Creating Process ID'',
		''Elapsed Time'',
		''Handle Count'',
		''ID Process'',
		''Priority Base''
		) AND InstanceName <> ''_Total''
			AND MachineName = @MachineName
		GROUP BY CounterName, InstanceName, MachineName
		ORDER BY CounterName
		SELECT *
		FROM
			(
			SELECT *,
    (CounterAvg/(SELECT SUM(CounterAvg) AS AverageOverallPercentage
				FROM #CounterTemp i
				WHERE o.CounterName = i.CounterName AND CounterAvg > 0)*1.00)*100.00,
				Grouping = DENSE_RANK() OVER(ORDER BY CounterName),
				RowNo = ROW_NUMBER() OVER(PARTITION BY CounterName ORDER BY CounterAvg DESC)
			FROM #CounterTemp o
			WHERE CounterAvg > 0
		) x
		WHERE RowNo <=5
		ORDER BY CounterName, CounterAvg DESC
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetProcessPerfData: {e}")
        return None, None


def getprocessorperfdata(conn):
    """
    T-SQL Source: GetProcessorPerfData
    Required Tables: CounterDetails, Counterdata
    """
    required_tables = ['CounterDetails', 'Counterdata']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetProcessorPerfData': Required tables not present.")
        return None, None
        
    query = """
AS
	SELECT @MachineName = udf_GetMachineName()
		OBJECT_ID(''Counterdata'') IS NOT NULL AND
		OBJECT_ID(''CounterDetails'') IS NOT NULL 
		SELECT
			ObjectName,
			CounterName,
			MachineName,
			CounterAvg = FORMAT(AVG(CounterValue), ''N''),
			CounterMin = FORMAT(MIN(CounterValue), ''N''),
			CounterMax = FORMAT(MAX(CounterValue), ''N'')
		FROM Counterdata c
			JOIN CounterDetails d ON c.CounterID = d.CounterID
		WHERE ObjectName = ''Processor''
			AND MachineName = @MachineName
		GROUP BY ObjectName, CounterName, MachineName
		ORDER BY CounterName
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetProcessorPerfData: {e}")
        return None, None


def getprocs(conn):
    """
    T-SQL Source: GetProcs
    Required Tables: sys
    """
    required_tables = ['sys']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetProcs': Required tables not present.")
        return None, None
        
    query = """
AS
	SELECT ProcName = ''EXECUTE '' + name 
	FROM sys.procedures
	WHERE name like ''Get%'' and name <> ''GetProcs'' and name <> ''GetTopNQueryHash'' 
	ORDER BY CASE WHEN name = ''GetPTOClinicFindings'' THEN ''zzzzzzzzzzzzzzzzz'' ELSE name END ASC
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetProcs: {e}")
        return None, None


def getqueryprocessingstatus(conn):
    """
    T-SQL Source: GetQueryProcessingStatus
    Required Tables: tbl_QUERY_PROCESSING
    """
    required_tables = ['tbl_QUERY_PROCESSING']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetQueryProcessingStatus': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''tbl_QUERY_PROCESSING'') IS NOT NULL 
		SELECT *
		FROM tbl_QUERY_PROCESSING
		WHERE component_state != ''CLEAN''
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetQueryProcessingStatus: {e}")
        return None, None


def getquerystoreoptions(conn):
    """
    T-SQL Source: GetQueryStoreOptions
    Required Tables: cust_QueryStoreOptions
    """
    required_tables = ['cust_QueryStoreOptions']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetQueryStoreOptions': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM cust_QueryStoreOptions
		WHERE DBName NOT IN(''master'',''msdb'',''tempdb'',''model'')
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetQueryStoreOptions: {e}")
        return None, None


def getquerystorequeries(conn):
    """
    T-SQL Source: GetQueryStoreQueries
    Required Tables: tbl_query_store_plan, tbl_query_store_query, tbl_query_store_query_text, tbl_query_store_runtime_stats
    """
    required_tables = ['tbl_query_store_plan', 'tbl_query_store_query', 'tbl_query_store_query_text', 'tbl_query_store_runtime_stats']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetQueryStoreQueries': Required tables not present.")
        return None, None
        
    query = """
AS
	OBJECT_ID(''tbl_query_store_runtime_stats'') IS NOT NULL AND
		OBJECT_ID(''tbl_query_store_plan'') IS NOT NULL AND
		OBJECT_ID(''tbl_query_store_query'') IS NOT NULL AND
		OBJECT_ID(''tbl_query_store_query_text'') IS NOT NULL 
		SELECT DISTINCT TOP(1000)
			q.dbname,
			first_execution_time, q.last_execution_time,
    CAST(avg_duration AS FLOAT)/1000000.00, AS avg_durationSec
    CAST(min_duration AS FLOAT)/1000000.00, AS min_durationSec
    CAST(max_duration AS FLOAT)/1000000.00, AS max_durationSec
    cast(avg_logical_io_reads AS FLOAT), min_logical_io_reads, max_logical_io_reads, AS avg_logical_io_reads
			min_dop, max_dop,
			min_rowcount, max_rowcount,
			query_parameterization_type_desc,
			execution_type_desc,
			count_executions,
			query_hash,
			query_plan_hash,
			query_sql_text
		from
			tbl_query_store_runtime_stats q
			join tbl_query_store_plan p on q.dbid = p.dbid and q.plan_id = p.plan_id
			join tbl_query_store_query qq on p.dbid = qq.dbid and p.query_id = qq.query_id
			join tbl_query_store_query_text qt on qt.dbid = qq.dbid and qt.query_text_id = qq.query_text_id
		order by cast(avg_logical_io_reads as float) desc
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetQueryStoreQueries: {e}")
        return None, None


def getquerywaits(conn):
    """
    T-SQL Source: GetQueryWaits
    Required Tables: 
    """
    required_tables = []
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetQueryWaits': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''tbl_query_store_runtime_stats'') IS NOT NULL AND
		OBJECT_ID(''tbl_query_store_plan'') IS NOT NULL AND
		OBJECT_ID(''tbl_query_store_query'') IS NOT NULL AND
		OBJECT_ID(''tbl_query_store_query_text'') IS NOT NULL AND
		OBJECT_ID(''tbl_query_store_wait_stats'') IS NOT NULL AND
		OBJECT_ID(''tbl_query_store_runtime_stats_interval'') IS NOT NULL
		SELECT TOP(5000)
			i.runtime_stats_interval_id, 
			ws.wait_cate
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetQueryWaits: {e}")
        return None, None


def getring_buffer_connectivity(conn):
    """
    T-SQL Source: GetRING_BUFFER_CONNECTIVITY
    Required Tables: SQLskills_RING_BUFFER_CONNECTIVITY
    """
    required_tables = ['SQLskills_RING_BUFFER_CONNECTIVITY']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetRING_BUFFER_CONNECTIVITY': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM SQLskills_RING_BUFFER_CONNECTIVITY
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetRING_BUFFER_CONNECTIVITY: {e}")
        return None, None


def getring_buffer_exception(conn):
    """
    T-SQL Source: GetRING_BUFFER_EXCEPTION
    Required Tables: SQLskills_RING_BUFFER_EXCEPTION
    """
    required_tables = ['SQLskills_RING_BUFFER_EXCEPTION']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetRING_BUFFER_EXCEPTION': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM SQLskills_RING_BUFFER_EXCEPTION
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetRING_BUFFER_EXCEPTION: {e}")
        return None, None


def getring_buffer_memory_broker(conn):
    """
    T-SQL Source: GetRING_BUFFER_MEMORY_BROKER
    Required Tables: SQLskills_RING_BUFFER_MEMORY_BROKER
    """
    required_tables = ['SQLskills_RING_BUFFER_MEMORY_BROKER']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetRING_BUFFER_MEMORY_BROKER': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM SQLskills_RING_BUFFER_MEMORY_BROKER
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetRING_BUFFER_MEMORY_BROKER: {e}")
        return None, None


def getring_buffer_oom(conn):
    """
    T-SQL Source: GetRING_BUFFER_OOM
    Required Tables: SQLskills_RING_BUFFER_OOM
    """
    required_tables = ['SQLskills_RING_BUFFER_OOM']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetRING_BUFFER_OOM': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM SQLskills_RING_BUFFER_OOM
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetRING_BUFFER_OOM: {e}")
        return None, None


def getring_buffer_resource_monitor(conn):
    """
    T-SQL Source: GetRING_BUFFER_RESOURCE_MONITOR
    Required Tables: SQLskills_RING_BUFFER_RESOURCE_MONITOR
    """
    required_tables = ['SQLskills_RING_BUFFER_RESOURCE_MONITOR']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetRING_BUFFER_RESOURCE_MONITOR': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM SQLskills_RING_BUFFER_RESOURCE_MONITOR
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetRING_BUFFER_RESOURCE_MONITOR: {e}")
        return None, None


def getring_buffer_scheduler_monitor(conn):
    """
    T-SQL Source: GetRING_BUFFER_SCHEDULER_MONITOR
    Required Tables: SQLskills_RING_BUFFER_SCHEDULER_MONITOR
    """
    required_tables = ['SQLskills_RING_BUFFER_SCHEDULER_MONITOR']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetRING_BUFFER_SCHEDULER_MONITOR': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM SQLskills_RING_BUFFER_SCHEDULER_MONITOR
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetRING_BUFFER_SCHEDULER_MONITOR: {e}")
        return None, None


def getreadwritestalls(conn):
    """
    T-SQL Source: GetReadWriteStalls
    Required Tables: cust_DBFileSizes
    """
    required_tables = ['cust_DBFileSizes']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetReadWriteStalls': Required tables not present.")
        return None, None
        
    query = """
AS
		CREATE TEMP TABLE temp_ReadWriteStalls AS SELECT  DBName, LogicalName, FilePath,
			AverageReadStallMS, AverageWriteStallMS, Growth
		 FROM cust_DBFileSizes
		WHERE 
		dbname not in(''master'',''msdb'',''model'') AND
			(
			cast(AverageReadStallMS AS INTEGER) >= @DurationT or
			cast(AverageWriteStallMS AS INTEGER) >= @DurationT
		)
		SELECT *
		FROM #ReadWriteStalls
			SELECT
				@Read = SUM(CASE WHEN AverageReadStallMS > @DurationT THEN 1 ELSE 0 END),
				@Write = SUM(CASE WHEN AverageWriteStallMS > @DurationT THEN 1 ELSE 0 END)
			FROM #ReadWriteStalls
			INSERT INTO PTOClinicFindings (Title,Cate
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetReadWriteStalls: {e}")
        return None, None


def getresourcestats(conn):
    """
    T-SQL Source: GetResourceStats
    Required Tables: cust_ResoureStats
    """
    required_tables = ['cust_ResoureStats']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetResourceStats': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM cust_ResoureStats
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetResourceStats: {e}")
        return None, None


def getringbufferexceptionmonitor(conn):
    """
    T-SQL Source: GetRingBufferExceptionMonitor
    Required Tables: 
    """
    required_tables = []
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetRingBufferExceptionMonitor': Required tables not present.")
        return None, None
        
    query = """

    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetRingBufferExceptionMonitor: {e}")
        return None, None


def getringbufferresourcemonitor(conn):
    """
    T-SQL Source: GetRingBufferResourceMonitor
    Required Tables: 
    """
    required_tables = []
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetRingBufferResourceMonitor': Required tables not present.")
        return None, None
        
    query = """

    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetRingBufferResourceMonitor: {e}")
        return None, None


def getringbufferschedulermonitor(conn):
    """
    T-SQL Source: GetRingBufferSchedulerMonitor
    Required Tables: 
    """
    required_tables = []
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetRingBufferSchedulerMonitor': Required tables not present.")
        return None, None
        
    query = """

    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetRingBufferSchedulerMonitor: {e}")
        return None, None


def getsqlagentjobs(conn):
    """
    T-SQL Source: GetSQLAgentJobs
    Required Tables: SQLskills_SQLAgentJobs
    """
    required_tables = ['SQLskills_SQLAgentJobs']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetSQLAgentJobs': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM SQLskills_SQLAgentJobs
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetSQLAgentJobs: {e}")
        return None, None


def getsqldbbufferpool(conn):
    """
    T-SQL Source: GetSQLDBBufferPool
    Required Tables: cust_azurebufferpool
    """
    required_tables = ['cust_azurebufferpool']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetSQLDBBufferPool': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM cust_azurebufferpool
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetSQLDBBufferPool: {e}")
        return None, None


def getsqldbelasticpoolinfo(conn):
    """
    T-SQL Source: GetSQLDBElasticPoolInfo
    Required Tables: cust_azureelasticpools
    """
    required_tables = ['cust_azureelasticpools']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetSQLDBElasticPoolInfo': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT TOP 1000 *
		FROM cust_azureelasticpools
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetSQLDBElasticPoolInfo: {e}")
        return None, None


def getsqldbeventlog(conn):
    """
    T-SQL Source: GetSQLDBEventLog
    Required Tables: cust_AzureEventLog
    """
    required_tables = ['cust_AzureEventLog']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetSQLDBEventLog': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM cust_AzureEventLog
		WHERE event_type <> ''connection_successful''
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetSQLDBEventLog: {e}")
        return None, None


def getsqldbfirewallrules(conn):
    """
    T-SQL Source: GetSQLDBFirewallRules
    Required Tables: cust_azurefilewallrules
    """
    required_tables = ['cust_azurefilewallrules']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetSQLDBFirewallRules': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM cust_azurefilewallrules
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetSQLDBFirewallRules: {e}")
        return None, None


def getsqlstatsperfdata(conn):
    """
    T-SQL Source: GetSQLStatsPerfData
    Required Tables: CounterDetails, Counterdata
    """
    required_tables = ['CounterDetails', 'Counterdata']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetSQLStatsPerfData': Required tables not present.")
        return None, None
        
    query = """
AS
	SELECT @MachineName = udf_GetMachineName()
		OBJECT_ID(''Counterdata'') IS NOT NULL AND
		OBJECT_ID(''CounterDetails'') IS NOT NULL 
		SELECT
			ObjectName,
			CounterName,
			MachineName,
			CounterAvg = FORMAT(AVG(CounterValue), ''N''),
			CounterMin = FORMAT(MIN(CounterValue), ''N''),
			CounterMax = FORMAT(MAX(CounterValue), ''N'')
		FROM Counterdata c
			JOIN CounterDetails d ON c.CounterID = d.CounterID
		WHERE ObjectName LIKE ''%SQL Statistics''
			AND MachineName = @MachineName
		GROUP BY ObjectName, CounterName, MachineName
		HAVING MAX(CounterValue) > 0
		ORDER BY CounterName
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetSQLStatsPerfData: {e}")
        return None, None


def getschedulermonitor(conn):
    """
    T-SQL Source: GetSchedulerMonitor
    Required Tables: tbl_scheduler_monitor
    """
    required_tables = ['tbl_scheduler_monitor']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetSchedulerMonitor': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''tbl_scheduler_monitor'') IS NOT NULL 
		SELECT *
		FROM tbl_scheduler_monitor
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetSchedulerMonitor: {e}")
        return None, None


def getsecurityevents(conn):
    """
    T-SQL Source: GetSecurityEvents
    Required Tables: tbl_security_ring_buffer
    """
    required_tables = ['tbl_security_ring_buffer']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetSecurityEvents': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''tbl_security_ring_buffer'') IS NOT NULL 
		SELECT *
		FROM tbl_security_ring_buffer
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetSecurityEvents: {e}")
        return None, None


def getsensitivedatacolumns(conn):
    """
    T-SQL Source: GetSensitiveDataColumns
    Required Tables: cust_SensitivityRecommendations
    """
    required_tables = ['cust_SensitivityRecommendations']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetSensitiveDataColumns': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM cust_SensitivityRecommendations
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetSensitiveDataColumns: {e}")
        return None, None


def getspinlocks(conn):
    """
    T-SQL Source: GetSpinlocks
    Required Tables: cust_Spinlocks
    """
    required_tables = ['cust_Spinlocks']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetSpinlocks': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT TOP(10)
			*, SpinPercent = ((CAST(spins AS INTEGER)  + 1)/(TotalSpins*1.000))*100.00
		FROM cust_Spinlocks
	CROSS JOIN 
	(
	SELECT SUM(CAST(spins AS INTEGER)) AS TotalSpins
			FROM cust_Spinlocks
	)x
		ORDER BY SpinPercent DESC
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetSpinlocks: {e}")
        return None, None


def getstartupparameters(conn):
    """
    T-SQL Source: GetStartupParameters
    Required Tables: cust_AllDocumentedTraceFlags, tbl_StartupParameters
    """
    required_tables = ['cust_AllDocumentedTraceFlags', 'tbl_StartupParameters']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetStartupParameters': Required tables not present.")
        return None, None
        
    query = """
AS
		CREATE TEMP TABLE temp_StartupParams AS SELECT  ArgsName, ArgsValue = REPLACE(ArgsValue, ''-'',''!'')
		 FROM tbl_StartupParameters
		WHERE ArgsName LIKE ''SQL%''
			SELECT p.ArgsValue, TraceFlagDesc = c.Description
			FROM #StartupParams p
				LEFT JOIN cust_AllDocumentedTraceFlags c ON SUBSTRING(p.ArgsValue,3,LEN(p.ArgsValue)) = CAST(c.TraceFlag AS VARCHAR(10))
					AND p.ArgsValue LIKE ''!T%''
			SELECT *
			FROM #StartupParams
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetStartupParameters: {e}")
        return None, None


def getstats(conn):
    """
    T-SQL Source: GetStats
    Required Tables: cust_GetStats
    """
    required_tables = ['cust_GetStats']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetStats': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT
			TableName,
			DBName,
    CAST(((RowsSampled*1.0/RowCnt)*100.00) AS REAL), AS SampleRatePercent
			StatName,
			Updated,
			RowCnt,
			RowsSampled,
			UnfilteredRows
		FROM
			cust_GetStats
		WHERE 
			(
				(
					RowCnt > 10000 AND
					(RowsSampled*1.0/RowCnt) < .30 AND
					StatName NOT LIKE ''_WA_Sys_%''
				) OR 
				RowsSampled IS NULL
			) AND
			DBName NOT IN(''tempdb'',''master'',''msdb'',''model'')
		ORDER BY RowCnt DESC, (RowsSampled*1.0/RowCnt) asc
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetStats: {e}")
        return None, None


def getsuspectpages(conn):
    """
    T-SQL Source: GetSuspectPages
    Required Tables: cust_SuspectPages
    """
    required_tables = ['cust_SuspectPages']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetSuspectPages': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''cust_SuspectPages'') IS NOT NULL
		SELECT *
		FROM cust_SuspectPages
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetSuspectPages: {e}")
        return None, None


def getsystemcomponentstatus(conn):
    """
    T-SQL Source: GetSystemComponentStatus
    Required Tables: tbl_SYSTEM
    """
    required_tables = ['tbl_SYSTEM']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetSystemComponentStatus': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''tbl_SYSTEM'') IS NOT NULL 
		SELECT *
		FROM tbl_SYSTEM
		WHERE 
			component_state <> ''CLEAN'' OR
			spinlockBackoffs > 0 OR
			sickSpinlockTypeAfterAv <> ''none'' OR
			latchWarnings > 0 OR
			isAccessViolationOccurred > 0 OR
			writeAccessViolationCount > 0 OR
			totalDumpRequests > 0 OR
			intervalDumpRequests > 0 OR
			nonYieldingTasksReported  > 0 OR
			systemCpuUtilization > 90 OR
			sqlCpuUtilization  > 90 OR
			BadPagesDetected > 0 OR
			BadPagesFixed > 0 OR
			LastBadPageAddress <> ''0x0''
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetSystemComponentStatus: {e}")
        return None, None


def getsystemcomponentsummary(conn):
    """
    T-SQL Source: GetSystemComponentSummary
    Required Tables: tbl_Summary
    """
    required_tables = ['tbl_Summary']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetSystemComponentSummary': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''tbl_Summary'') IS NOT NULL 
		SELECT *
		FROM tbl_Summary
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetSystemComponentSummary: {e}")
        return None, None


def getsystemconfiguration(conn):
    """
    T-SQL Source: GetSystemConfiguration
    Required Tables: cust_SPConfigure, tbl_SPCONFIGURE, tbl_Sys_Configurations
    """
    required_tables = ['cust_SPConfigure', 'tbl_SPCONFIGURE', 'tbl_Sys_Configurations']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetSystemConfiguration': Required tables not present.")
        return None, None
        
    query = """
AS
	CREATE TABLE #SPConfigure
	(
		name varchar(50),
		run_value varchar(250)
	)
		INSERT INTO #SPConfigure
		SELECT *
		FROM tbl_SPCONFIGURE
		WHERE replace(run_value, ''-'', '''') <> '''' AND isnumeric(run_value)=1
		INSERT INTO #SPConfigure
		SELECT name, value_in_use
		FROM cust_SPConfigure
		INSERT INTO #SPConfigure
		SELECT name, value_in_use
		FROM tbl_Sys_Configurations
	SELECT *
	FROM #SPConfigure
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetSystemConfiguration: {e}")
        return None, None


def getsystemhealthwaitstats(conn):
    """
    T-SQL Source: GetSystemHealthWaitStats
    Required Tables: tbl_OS_WAIT_STATS_byDuration
    """
    required_tables = ['tbl_OS_WAIT_STATS_byDuration']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetSystemHealthWaitStats': Required tables not present.")
        return None, None
        
    query = """
AS
		CREATE TEMP TABLE temp_Waits AS SELECT  DISTINCT *, WaitDate = CAST(timestamp AS DATE)
		 FROM tbl_OS_WAIT_STATS_byDuration
		WHERE wait_type NOT LIKE ''%PREEMPTIVE%'' AND
			wait_cate
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetSystemHealthWaitStats: {e}")
        return None, None


def getsysteminformation(conn):
    """
    T-SQL Source: GetSystemInformation
    Required Tables: cust_MSInfo, cust_OSInfo, cust_RTDSC, tbl_SCRIPT_ENVIRONMENT_DETAILS, tbl_XPMSVER
    """
    required_tables = ['cust_MSInfo', 'cust_OSInfo', 'cust_RTDSC', 'tbl_SCRIPT_ENVIRONMENT_DETAILS', 'tbl_XPMSVER']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetSystemInformation': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT @MajorVersion = CAST(LEFT(Value, CHARINDEX(''.'',Value)-1) AS INTEGER)
		FROM tbl_SCRIPT_ENVIRONMENT_DETAILS
		WHERE Name = ''SQL Version (SP)''
	CREATE TABLE #TempOSInfo
	(
		ValueName varchar(200),
		Value nvarchar(300),
		Ranker INT
	)
		INSERT INTO #TempOSInfo
			(ValueName, Value)
		SELECT ''SchedulerCount'', scheduler_count
		FROM cust_OSInfo
			INSERT INTO #TempOSInfo
				(ValueName, Value)
			SELECT ''MemoryGB'', MemoryGB = cast(physical_memory_in_bytes as INTEGER)/1024.0/1024.0/1024.0
			FROM cust_OSInfo
		INSERT INTO #TempOSInfo
			(ValueName, Value)
		SELECT ''cpu_count'', cpu_count
		FROM cust_OSInfo
		INSERT INTO #TempOSInfo
			(ValueName, Value)
		SELECT ''hyperthread_ratio'', hyperthread_ratio
		FROM cust_OSInfo
			INSERT INTO #TempOSInfo
				(ValueName, Value)
			SELECT ''bpool_committed'', bpool_committed
			FROM cust_OSInfo
			INSERT INTO #TempOSInfo
				(ValueName, Value)
			SELECT ''bpool_commit_target'', bpool_commit_target
			FROM cust_OSInfo
			INSERT INTO #TempOSInfo
				(ValueName, Value)
			SELECT ''bpool_visible'', bpool_visible
			FROM cust_OSInfo
		INSERT INTO #TempOSInfo
			(ValueName, Value)
		SELECT ''max_workers_count'', max_workers_count
		FROM cust_OSInfo
		INSERT INTO #TempOSInfo
			(ValueName, Value)
		SELECT ''scheduler_count'', scheduler_count
		FROM cust_OSInfo
		INSERT INTO #TempOSInfo
			(ValueName, Value)
		SELECT ''scheduler_total_count'', scheduler_total_count
		FROM cust_OSInfo
		INSERT INTO #TempOSInfo
			(ValueName, Value)
		SELECT ''sqlserver_start_time'', sqlserver_start_time
		FROM cust_OSInfo
		SELECT
			@ServerMemoryMB = CASE 
				WHEN Metric = ''GB'' THEN Val*1024.00
				WHEN Metric = ''TB'' THEN Val*1024.00*1024.00
		FROM
			(
			SELECT
    udf_CleanUpString(CAST(LTRIM(RTRIM(LEFT(Mem, CHARINDEX('' '', Mem)))) AS VARCHAR(20))), AS Val
    SUBSTRING(Mem, CHARINDEX('' '', Mem)+1, 2) AS Metric
			FROM
				(
				SELECT Mem = REPLACE((LTRIM(RTRIM(REPLACE(InfoDesc, ''Total Physical Memory'', '''')))),'','',''.'')
				FROM cust_MSInfo
				WHERE InfoDesc LIKE ''%Total Physical Memory%''
			)x
		) y
		INSERT INTO #TempOSInfo
			(ValueName, Value)
		SELECT ''System Memory'', CAST(@ServerMemoryMB/1024.0 AS VARCHAR(20)) + '' GB''
		INSERT INTO #TempOSInfo
			(ValueName, Value, Ranker)
		SELECT Name, Value, 1
		FROM tbl_SCRIPT_ENVIRONMENT_DETAILS
		WHERE Name IN(''SQL Server Name'',''Machine Name'',''SQL Version (SP)'',''Edition'')
		INSERT INTO #TempOSInfo
			(ValueName, Value, Ranker)
		SELECT Name, COALESCE(CAST(Character_Value as varchar(1000)), cast(Internal_Value as varchar(1000))), 2
		FROM tbl_XPMSVER
		WHERE Name IN(
		''Platform'',
		''FileVersion'',
		''OriginalFilename'',
		''PrivateBuild'',
		''SpecialBuild'',
		''WindowsVersion'',
		''ProcessorCount'',
		''ProcessorActiveMask'',
		''ProcessorType'')
		INSERT INTO #TempOSInfo
			(ValueName, Value, Ranker)
		SELECT
    LTRIM((LEFT(LineDesc,charindex('':'',LineDesc)-1))), AS LineSetting
    LTRIM((SUBSTRING(LineDesc,(charindex('':'',LineDesc)+1), LEN(LineDesc)))), AS LineValue
			3
		FROM cust_RTDSC
		WHERE Cate
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetSystemInformation: {e}")
        return None, None


def getsystemsettings(conn):
    """
    T-SQL Source: GetSystemSettings
    Required Tables: tbl_SPCONFIGURE
    """
    required_tables = ['tbl_SPCONFIGURE']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetSystemSettings': Required tables not present.")
        return None, None
        
    query = """
 AS
 		SELECT * 
 		FROM tbl_SPCONFIGURE
 		WHERE ISNUMERIC(run_value) = 1
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetSystemSettings: {e}")
        return None, None


def gettablesizes(conn):
    """
    T-SQL Source: GetTableSizes
    Required Tables: cust_CompressionDetails
    """
    required_tables = ['cust_CompressionDetails']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetTableSizes': Required tables not present.")
        return None, None
        
    query = """
AS
		DELETE FROM cust_CompressionDetails WHERE RowCnt = ''NULL''
		SELECT DBName, TableName, TableRowCount = MAX(CAST(RowCnt AS INTEGER))
		FROM cust_CompressionDetails
		WHERE CAST(RowCnt AS INTEGER) > 100
		GROUP BY DBName, TableName
		ORDER BY TableRowCount DESC
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetTableSizes: {e}")
        return None, None


def gettableusage(conn):
    """
    T-SQL Source: GetTableUsage
    Required Tables: 
    """
    required_tables = []
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetTableUsage': Required tables not present.")
        return None, None
        
    query = """

    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetTableUsage: {e}")
        return None, None


def gettablesmissingindexes(conn):
    """
    T-SQL Source: GetTablesMissingIndexes
    Required Tables: cust_CompressionDetails, cust_IndexDetail
    """
    required_tables = ['cust_CompressionDetails', 'cust_IndexDetail']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetTablesMissingIndexes': Required tables not present.")
        return None, None
        
    query = """
AS
		CREATE TEMP TABLE temp_TablesMissingIndexes AS SELECT  *
		 FROM
			(
							SELECT DBName, TableName, IndexStatus = ''No clustered index''
				FROM cust_IndexDetail
				WHERE 
    ''HEAP'' AS IndexType
			UNION ALL
				SELECT DBName, TableName, IndexStatus = ''No non-clustered indexes''
				FROM cust_IndexDetail o
				WHERE IndexType NOT IN(''NONCLUSTERED'') AND
					IndexType NOT LIKE ''%COLUMNSTORE%''
					AND NOT EXISTS
			(
				SELECT *
					FROM cust_IndexDetail i
					WHERE IndexType = ''NONCLUSTERED'' AND
						i.DBName = o.DBName AND
						i.TableName = o.TableName
			)
		) x
			SELECT DISTINCT tmi.*, RowCnt = CAST(c.RowCnt AS INTEGER), c.DataCompressionDescription
			FROM #TablesMissingIndexes tmi
				JOIN cust_CompressionDetails c
				ON tmi.DBName = c.DBName AND
					tmi.TableName = c.TableName
			ORDER BY CAST(c.RowCnt AS INTEGER) DESC
			SELECT DISTINCT tmi.*
			FROM #TablesMissingIndexes tmi
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetTablesMissingIndexes: {e}")
        return None, None


def gettempdbschedulerinfo(conn):
    """
    T-SQL Source: GetTempDBSchedulerInfo
    Required Tables: cust_DBFileSizes, cust_OSInfo
    """
    required_tables = ['cust_DBFileSizes', 'cust_OSInfo']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetTempDBSchedulerInfo': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''cust_OSInfo'') IS NOT NULL
		CREATE TEMP TABLE temp_TempDBInfo AS SELECT 
    COUNT(*), AS TempDBFileCount
    COUNT(DISTINCT InitialSizeInMB), AS DistinctTempDBFileSizes
    (SELECT MAX(scheduler_count) AS SchedulerCount
			FROM cust_OSInfo)
		 FROM cust_DBFileSizes
		WHERE DBName = ''tempdb'' AND (LogicalName not like ''%log%'' or FilePath not like ''%.ldf'')
		SELECT @FileCount = TempDBFileCount, @SchedulerCount = SchedulerCount
		FROM #TempDBInfo
		WHERE ((TempDBFileCount*1.00)/ SchedulerCount) < .15
				INSERT INTO PTOClinicFindings
					(Title,Cate
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetTempDBSchedulerInfo: {e}")
        return None, None


def gettempdbsizedifferences(conn):
    """
    T-SQL Source: GetTempDBSizeDifferences
    Required Tables: cust_DBFileSizes
    """
    required_tables = ['cust_DBFileSizes']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetTempDBSizeDifferences': Required tables not present.")
        return None, None
        
    query = """
AS
	CREATE TEMP TABLE temp_tempfiles AS SELECT  InitialSizeInMB, Growth, SizeInMB, FileCount = COUNT(*), RowNo = ROW_NUMBER() OVER(ORDER BY NEWID())
	 FROM cust_DBFileSizes
	WHERE DBName = ''tempdb'' and LogicalName <> ''templog''
	GROUP BY InitialSizeInMB, Growth, SizeInMB
	HAVING COUNT(*) > 1
		SELECT InitialSizeInMB, Growth, SizeInMB
		FROM #tempfiles
		INSERT INTO PTOClinicFindings
			(Title,Cate
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetTempDBSizeDifferences: {e}")
        return None, None


def gettopcpuqueries(conn):
    """
    T-SQL Source: GetTopCPUQueries
    Required Tables: 
    """
    required_tables = []
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetTopCPUQueries': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''GetTopNQueryHash'') IS NOT NULL
		EXECUTE (''EXECUTE GetTopNQueryHash ''''CPU'''''')
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetTopCPUQueries: {e}")
        return None, None


def gettopmemgrantstatements(conn):
    """
    T-SQL Source: GetTopMemGrantStatements
    Required Tables: tbl_Query_Execution_Memory
    """
    required_tables = ['tbl_Query_Execution_Memory']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetTopMemGrantStatements': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM tbl_Query_Execution_Memory
		WHERE text NOT LIKE ''% sp_mem_stats_grants %''
		ORDER BY CAST(logical_reads AS INTEGER) DESC
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetTopMemGrantStatements: {e}")
        return None, None


def gettopplanstats(conn):
    """
    T-SQL Source: GetTopPlanStats
    Required Tables: 
    """
    required_tables = []
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetTopPlanStats': Required tables not present.")
        return None, None
        
    query = """
AS
		EXECUTE (@SQL)
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetTopPlanStats: {e}")
        return None, None


def gettoprequestsbywaittype(conn):
    """
    T-SQL Source: GetTopRequestsByWaitType
    Required Tables: 
    """
    required_tables = []
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetTopRequestsByWaitType': Required tables not present.")
        return None, None
        
    query = """

    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetTopRequestsByWaitType: {e}")
        return None, None


def gettracebatchdata(conn):
    """
    T-SQL Source: GetTraceBatchData
    Required Tables: ReadTrace
    """
    required_tables = ['ReadTrace']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetTraceBatchData': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''ReadTrace.tblConnections'') IS NOT NULL 
		SELECT TOP(2500)
			t.StartTime,
			t.EndTime,
			t.Duration,
			t.Reads,
			t.Writes,
			t.CPU,
			ApplicationName,
			LoginName,
			HostName,
			NTDomainName,
			NTUserName,
    REPLACE(t.textdata, '''''''','''''''''''') AS TextData
		FROM
			ReadTrace.tblBatches t
			JOIN ReadTrace.tblConnections c ON t.ConnSeq = c.ConnSeq
		WHERE 
			t.textdata not like ''%sp_trace%'' AND
			t.textdata not like ''%PRINT ''''
			t.textdata not like ''%tbl_RUNTIMES%''
			AND t.Duration > 0
		ORDER BY t.Reads DESC
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetTraceBatchData: {e}")
        return None, None


def gettriggerexecutionmetrics(conn):
    """
    T-SQL Source: GetTriggerExecutionMetrics
    Required Tables: cust_CompressionDetails, cust_Triggers
    """
    required_tables = ['cust_CompressionDetails', 'cust_Triggers']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetTriggerExecutionMetrics': Required tables not present.")
        return None, None
        
    query = """
AS
		CREATE TEMP TABLE temp_TriggerData AS SELECT  DISTINCT
    t.name, AS TriggerName
    t.parent_table, AS TableName
    CAST(NULL AS INTEGER), AS RowCnt
			TriggerExecutionCount = CASE WHEN t.execution_count IS NULL OR t.execution_count = ''NULL'' THEN 0 ELSE t.execution_count END,
			total_logical_reads,
			total_logical_writes,
			total_elapsed_time,
			min_elapsed_time,
			max_elapsed_time,
			min_logical_reads,
			max_logical_reads,
			DBName,
    type_desc AS TriggerType
		 FROM cust_Triggers t
		OBJECT_ID(''tempdb..#TriggerData'') IS NOT NULL
		UPDATE t
    CAST(d.RowCnt AS INTEGER) AS RowCnt
		FROM #TriggerData t
			JOIN cust_CompressionDetails d
			ON t.DBName = d.DBName AND
				t.TableName = d.TableName
		SELECT *
		FROM #TriggerData
		ORDER BY CAST(TriggerExecutionCount AS INT) DESC
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetTriggerExecutionMetrics: {e}")
        return None, None


def getudfexecutiondata(conn):
    """
    T-SQL Source: GetUDFExecutionData
    Required Tables: cust_UDFExecution
    """
    required_tables = ['cust_UDFExecution']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetUDFExecutionData': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM cust_UDFExecution
		ORDER BY CAST(execution_count AS INTEGER) DESC
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetUDFExecutionData: {e}")
        return None, None


def getunusedindexes(conn):
    """
    T-SQL Source: GetUnusedIndexes
    Required Tables: cust_UnusedIndexes
    """
    required_tables = ['cust_UnusedIndexes']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetUnusedIndexes': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT
			DatabaseName, TableName, IndexName, TableRows, UserSeeks, UserScans,
			UserLookups, UserUpdates, *,
			LastRestart = CAST(CASE WHEN LastRestart = ''NULL'' THEN NULL ELSE LastRestart END AS DATE) ,
			LastUserSeek = CAST(CASE WHEN LastUserSeek = ''NULL'' THEN NULL ELSE LastUserSeek END AS DATE),
			LastUserScan = CAST(CASE WHEN LastUserScan = ''NULL'' THEN NULL ELSE LastUserScan END AS DATE),
			LastUserLookup = CAST(CASE WHEN LastUserLookup = ''NULL'' THEN NULL ELSE LastUserLookup END AS DATE),
			LastUserUpdate = CAST(CASE WHEN LastUserUpdate = ''NULL'' THEN NULL ELSE LastUserUpdate END AS DATE)
		FROM cust_UnusedIndexes
		WHERE CAST(UserSeeks AS INTEGER) = 0 AND
			CAST(UserScans AS INTEGER) = 0 AND CAST(UserLookups AS INTEGER) = 0
			AND DatabaseName NOT IN(''tempdb'', ''msdb'', ''master'', ''model'')
			AND cast(replace(TableRows, ''NULL'', '''') AS INTEGER)> 100000
		ORDER BY CAST(TableRows AS INTEGER) DESC
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetUnusedIndexes: {e}")
        return None, None


def getusefulindexes(conn):
    """
    T-SQL Source: GetUsefulIndexes
    Required Tables: cust_MissingIndexes
    """
    required_tables = ['cust_MissingIndexes']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetUsefulIndexes': Required tables not present.")
        return None, None
        
    query = """
AS
		CREATE TEMP TABLE temp_UsefulIndexes AS SELECT 
			DatabaseName, Benefit = cast(UserImpact as real), Cost = cast(UserCost as real),
			Seeks, Compiles,
			LastUserSeek, FullObjectName, TableName, EqualityColumns, InequalityColumns, IncludedColumns,
			x.*
		 FROM cust_MissingIndexes
		CROSS APPLY fn_SortIncludedColumns(TableName, EqualityColumns, IncludedColumns, '','')x
		WHERE FullObjectName NOT LIKE ''%msdb%'' AND
			Seeks > 3000 AND
			cast(UserImpact as real) > 60 AND
			cast(UserCost as real) < 30
			SELECT *, RowFlag = CASE WHEN 
			Benefit > 60 AND Cost < 30 THEN ''G'' ELSE ''N'' END
			FROM #UsefulIndexes
			WHERE Seeks > 1000
		)
			SELECT *, RowFlag = CASE WHEN 
			Benefit > 60 AND Cost < 30 THEN ''G'' ELSE ''N'' END
			FROM #UsefulIndexes
			WHERE Seeks > 1000
			ORDER BY CAST(Seeks AS INTEGER) DESC
			INSERT INTO PTOClinicFindings (Title,Cate
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetUsefulIndexes: {e}")
        return None, None


def getwaitstatsperfdata(conn):
    """
    T-SQL Source: GetWaitStatsPerfData
    Required Tables: CounterDetails, Counterdata
    """
    required_tables = ['CounterDetails', 'Counterdata']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetWaitStatsPerfData': Required tables not present.")
        return None, None
        
    query = """
AS
	SELECT @MachineName = udf_GetMachineName()
		OBJECT_ID(''Counterdata'') IS NOT NULL AND
		OBJECT_ID(''CounterDetails'') IS NOT NULL 
		SELECT
			ObjectName,
			InstanceName,
			CounterName,
			MachineName,
			CounterAvg = FORMAT(AVG(CounterValue), ''N''),
			CounterMin = FORMAT(MIN(CounterValue), ''N''),
			CounterMax = FORMAT(MAX(CounterValue), ''N'')
		FROM Counterdata c
			JOIN CounterDetails d ON c.CounterID = d.CounterID
		WHERE ObjectName LIKE ''%Wait Statistics'' AND
			InstanceName = ''Average wait time (ms)'' AND
			CounterName NOT IN(
		''Transaction ownership waits'',''Thread-safe memory objects waits'',''Wait for the worker'',''Workspace synchronization waits''
		)
			AND MachineName = @MachineName
		GROUP BY ObjectName, InstanceName, CounterName, MachineName
		HAVING MAX(CounterValue) > 5
		ORDER BY CounterName
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetWaitStatsPerfData: {e}")
        return None, None


def getwaits(conn):
    """
    T-SQL Source: GetWaits
    Required Tables: cust_Waiting
    """
    required_tables = ['cust_Waiting']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetWaits': Required tables not present.")
        return None, None
        
    query = """
AS
		CREATE TEMP TABLE temp_TempWaiting AS SELECT 
			WaitType,
    CAST(WaitCount AS INTEGER), AS WaitCount
			Percentage, AvgWaitTimeSec = AvgWait_S
		 FROM cust_Waiting
		SELECT *
		FROM #TempWaiting
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetWaits: {e}")
        return None, None


def getwaitsforcapture(conn):
    """
    T-SQL Source: GetWaitsForCapture
    Required Tables: Waits, tbl_OS_WAIT_STATS
    """
    required_tables = ['Waits', 'tbl_OS_WAIT_STATS']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetWaitsForCapture': Required tables not present.")
        return None, None
        
    query = """
AS
		CREATE TEMP TABLE temp_WaitsForCapture AS SELECT 
			mx.wait_type,
    CAST(mx.waiting_tasks_count AS INTEGER)- CAST(mn.waiting_tasks_count AS INTEGER), AS waiting_tasks_count
    CAST(mx.wait_time_ms AS INTEGER)- CAST(mn.wait_time_ms AS INTEGER), AS wait_time_ms
    CAST(mx.signal_wait_time_ms AS INTEGER) - CAST(mn.signal_wait_time_ms AS INTEGER) AS signal_wait_time_ms
		 FROM
			(
			CREATE TEMP TABLE temp_TempWaiting AS SELECT  *
			from tbl_OS_WAIT_STATS
			where runtime = (select min(runtime)
			from tbl_OS_WAIT_STATS)
		) mn
			join
			(
			select *
			from tbl_OS_WAIT_STATS
			where runtime = (select max(runtime)
			from tbl_OS_WAIT_STATS)
		) mx on mn.wait_type = mx.wait_type
		;WITH
			Waits
			AS
			(
				SELECT
					wait_type,
					wait_time_ms / 1000.0 AS WaitS,
					(wait_time_ms - signal_wait_time_ms) / 1000.0 AS ResourceS,
					signal_wait_time_ms / 1000.0 AS SignalS,
					waiting_tasks_count AS WaitCount,
					100.0 * wait_time_ms / SUM (wait_time_ms) OVER() AS Percentage,
					ROW_NUMBER() OVER(ORDER BY wait_time_ms DESC) AS RowNum
				FROM #WaitsForCapture
				WHERE wait_type NOT IN (
				N''BROKER_EVENTHANDLER'',             N''BROKER_RECEIVE_WAITFOR'',
				N''BROKER_TASK_STOP'',                N''BROKER_TO_FLUSH'',
				N''BROKER_TRANSMITTER'',              N''CHECKPOINT_QUEUE'',
				N''CHKPT'',                           N''CLR_AUTO_EVENT'',
				N''CLR_MANUAL_EVENT'',                N''CLR_SEMAPHORE'',
				N''DBMIRROR_DBM_EVENT'',              N''DBMIRROR_EVENTS_QUEUE'',
				N''DBMIRROR_WORKER_QUEUE'',           N''DBMIRRORING_CMD'',
				N''DIRTY_PAGE_POLL'',                 N''DISPATCHER_QUEUE_SEMAPHORE'',
				N''EXECSYNC'',                        N''FSAGENT'',
				N''FT_IFTS_SCHEDULER_IDLE_WAIT'',     N''FT_IFTSHC_MUTEX'',
				N''HADR_CLUSAPI_CALL'',               N''HADR_FILESTREAM_IOMGR_IOCOMPLETION'',
				N''HADR_LOGCAPTURE_WAIT'',            N''HADR_NOTIFICATION_DEQUEUE'',
				N''HADR_TIMER_TASK'',                 N''HADR_WORK_QUEUE'',
				N''KSOURCE_WAKEUP'',                  N''LAZYWRITER_SLEEP'',
				N''LOGMGR_QUEUE'',                    N''ONDEMAND_TASK_QUEUE'',
				N''PWAIT_ALL_COMPONENTS_INITIALIZED'',
				N''QDS_PERSIST_TASK_MAIN_LOOP_SLEEP'',
				N''QDS_CLEANUP_STALE_QUERIES_TASK_MAIN_LOOP_SLEEP'',
				N''REQUEST_FOR_DEADLOCK_SEARCH'',     N''RESOURCE_QUEUE'',
				N''SERVER_IDLE_CHECK'',               N''SLEEP_BPOOL_FLUSH'',
				N''SLEEP_DBSTARTUP'',                 N''SLEEP_DCOMSTARTUP'',
				N''SLEEP_MASTERDBREADY'',             N''SLEEP_MASTERMDREADY'',
				N''SLEEP_MASTERUPGRADED'',            N''SLEEP_MSDBSTARTUP'',
				N''SLEEP_SYSTEMTASK'',                N''SLEEP_TASK'',
				N''SLEEP_TEMPDBSTARTUP'',             N''SNI_HTTP_ACCEPT'',
				N''SP_SERVER_DIAGNOSTICS_SLEEP'',     N''SQLTRACE_BUFFER_FLUSH'',
				N''SQLTRACE_INCREMENTAL_FLUSH_SLEEP'',
				N''SQLTRACE_WAIT_ENTRIES'',           N''WAIT_FOR_RESULTS'',
				N''WAITFOR'',                         N''WAITFOR_TASKSHUTDOWN'',
				N''WAIT_XTP_HOST_WAIT'',              N''WAIT_XTP_OFFLINE_CKPT_NEW_LOG'',
				N''WAIT_XTP_CKPT_CLOSE'',             N''XE_DISPATCHER_JOIN'',
				N''XE_DISPATCHER_WAIT'',              N''XE_TIMER_EVENT'', 
				''PREEMPTIVE_OS_WRITEFILE'', ''PREEMPTIVE_XE_DISPATCHER'', ''QDS_ASYNC_QUEUE'',''SOS_WORK_DISPATCHER'',
				''DIRTY_PAGE_POLL'',
				''QDS_PERSIST_TASK_MAIN_LOOP_SLEEP'',
				''SP_SERVER_DIAGNOSTICS_SLEEP'',
				''QDS_ASYNC_QUEUE'', ''CXCONSUMER'', 
				''XE_LIVE_TARGET_TVF'',
				''PREEMPTIVE_XE_DISPATCHER''
)
					AND waiting_tasks_count > 0
			)
		SELECT
			MAX (W1.wait_type) AS WaitType,
			CAST (MAX (W1.WaitS) AS REAL (16,2)) AS Wait_S,
			CAST (MAX (W1.ResourceS) AS REAL (16,2)) AS Resource_S,
			CAST (MAX (W1.SignalS) AS REAL (16,2)) AS Signal_S,
			MAX (W1.WaitCount) AS WaitCount,
			CAST (MAX (W1.Percentage) AS REAL (5,2)) AS Percentage,
			CAST ((MAX (W1.WaitS) / MAX (W1.WaitCount)) AS REAL (16,4)) AS AvgWait_S,
			CAST ((MAX (W1.ResourceS) / MAX (W1.WaitCount)) AS REAL (16,4)) AS AvgRes_S,
			CAST ((MAX (W1.SignalS) / MAX (W1.WaitCount)) AS REAL (16,4)) AS AvgSig_S
		 FROM Waits AS W1
			INNER JOIN Waits AS W2
			ON W2.RowNum <= W1.RowNum
		GROUP BY W1.RowNum
		HAVING SUM (W2.Percentage) - MAX (W1.Percentage) < 95;
		SELECT
			WaitType, WaitCount, Percentage, AvgWaitTimeSec = AvgWait_S
		FROM #TempWaiting
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetWaitsForCapture: {e}")
        return None, None


def getxeerrors(conn):
    """
    T-SQL Source: GetXEErrors
    Required Tables: tbl_errors
    """
    required_tables = ['tbl_errors']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'GetXEErrors': Required tables not present.")
        return None, None
        
    query = """
AS
		OBJECT_ID(''tbl_errors'') IS NOT NULL 
		SELECT
			error_number,
			ErrorMessage = MIN(message),
    COUNT(*) AS RwCnt
		FROM tbl_errors
		WHERE 
			message NOT LIKE ''Changed database context to%'' AND
			message > '''' AND
			message NOT LIKE ''
			message NOT LIKE ''Changed language setting%'' AND
			error_number NOT IN(''17806'') AND
			message NOT LIKE(''%occurred while establishing a connection; the connection has been closed%'')
		GROUP BY error_number
		ORDER BY RwCnt DESC
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing GetXEErrors: {e}")
        return None, None


def getsysconfigurations(conn):
    """
    T-SQL Source: Getsysconfigurations
    Required Tables: SQLskills_sysconfigurations
    """
    required_tables = ['SQLskills_sysconfigurations']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'Getsysconfigurations': Required tables not present.")
        return None, None
        
    query = """
AS
		SELECT *
		FROM SQLskills_sysconfigurations
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing Getsysconfigurations: {e}")
        return None, None


def summary_expensivequeries(conn):
    """
    T-SQL Source: Summary_ExpensiveQueries
    Required Tables: cust_ExpensiveQueries
    """
    required_tables = ['cust_ExpensiveQueries']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'Summary_ExpensiveQueries': Required tables not present.")
        return None, None
        
    query = """
AS
		select @ExpensiveQueryCount = COUNT_BIG(*), @MaxLogicalReads = MAX(CAST(AverageLogicalReads AS INTEGER)) from cust_ExpensiveQueries
		WHERE CAST(AverageLogicalReads AS INTEGER)> 1000000
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing Summary_ExpensiveQueries: {e}")
        return None, None


def summary_getpledips(conn):
    """
    T-SQL Source: Summary_GetPLEDips
    Required Tables: CounterDetails, Counterdata
    """
    required_tables = ['CounterDetails', 'Counterdata']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'Summary_GetPLEDips': Required tables not present.")
        return None, None
        
    query = """
AS
	SELECT @MachineName = udf_GetMachineName()
		OBJECT_ID(''CounterDetails'') IS NOT NULL 
		SELECT
    COUNT(*) AS DipCount
		FROM (
			SELECT
				RecordIndex, CounterDateTime, Countervalue,
				DiffVal = countervalue - LEAD(countervalue, 1) OVER(ORDER BY recordindex),
    ((countervalue - LEAD(countervalue, 1) AS VariancePercent
				OVER(ORDER BY recordindex))/(CASE WHEN CounterValue = 0 THEN 1 ELSE CounterValue END)*1.00)*100
			FROM Counterdata c
				JOIN CounterDetails d ON c.CounterID = d.CounterID
			WHERE ObjectName LIKE ''%:Buffer Manager'' AND
				CounterName = ''Page life expectancy'' AND
    @MachineName AS MachineName
		)x
		WHERE VariancePercent > 40
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing Summary_GetPLEDips: {e}")
        return None, None


def summary_servertype(conn):
    """
    T-SQL Source: Summary_ServerType
    Required Tables: tbl_ServerProperties
    """
    required_tables = ['tbl_ServerProperties']
    if not all(table_exists(t, conn) for t in required_tables):
        print("Skipping 'Summary_ServerType': Required tables not present.")
        return None, None
        
    query = """
AS
		(
			SELECT *
			FROM tbl_ServerProperties 
			WHERE PropertyName = ''EngineEdition'' AND
    ''5'' AS PropertyValue
		)
			(
				SELECT *
				FROM tbl_ServerProperties 
				WHERE PropertyName = ''DatabaseEdition'' AND
    ''Hyperscale'' AS PropertyValue
			)
		(
			SELECT *
			FROM tbl_ServerProperties 
			WHERE PropertyName = ''EngineEdition'' AND
    ''8'' AS PropertyValue
		)
	SELECT ServerType = @ServerType 
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        headers = [col[0] for col in cursor.description]
        return headers, data
    except Exception as e:
        print(f"Error executing Summary_ServerType: {e}")
        return None, None
