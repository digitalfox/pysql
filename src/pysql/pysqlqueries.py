# -*- coding: utf-8 -*-

"""SQL queries ordered by theme in dictionary
@author: Sébastien Renard (sebastien.renard@digitalfox.org)
@author: Sébastien Delcros (sebastien.delcros@gmail.com)
@license: GNU GPL V3
"""

# pylint: disable-msg=C0103
searchObjectSql = {
    "datafile"  :    ("""select 'Datafiles', file_name from dba_data_files
                where  (%s) /*%s*/ order by %s""", "file_name"),
    "directory" :    ("""select owner, directory_name from all_directories
                where  (%s) and owner like '%s' order by %s""", "directory_name"),
    "index"     :    ("""select owner, index_name from all_indexes
                where (%s) and owner like '%s' order by %s""", "index_name"),
    "function"  :    ("""select distinct owner, name from all_source
                where (%s) and owner like '%s' and type='FUNCTION' order by %s""", "name"),
    "package"   :    ("""select distinct owner, name from all_source
                where (%s) and owner like '%s' and type='PACKAGE' order by %s""", "name"),
    "procedure" :    ("""select distinct owner, name from all_source
                where (%s) and owner like '%s' and type='PROCEDURE' order by %s""", "name"),
    "role":          ("""select 'Roles', role from dba_roles
                where (%s) /*%s*/ order by %s""", "role"),
    "profile":       ("""select distinct 'Profiles', profile from dba_profiles
                where (%s) /*%s*/ order by %s""", "profile"),
    "sequence"  :    ("""select sequence_owner, sequence_name from all_sequences
                where (%s) and sequence_owner like '%s' order by %s""", "sequence_name"),
    "synonym"   :    ("""select owner, synonym_name from all_synonyms
                where (%s) and owner like '%s' order by %s""", "synonym_name"),
    "table"     :    ("""select owner, table_name from all_tables
                where (%s) and owner like '%s' order by %s""", "table_name"),
    "tablespace":    ("""select 'Tablespaces', tablespace_name from dba_tablespaces
                where (%s) /*%s*/ order by %s""", "tablespace_name"),
    "trigger"   :    ("""select owner, trigger_name from all_triggers
                where (%s) and owner like '%s' order by %s""", "trigger_name"),
    "user":          ("""select 'Users', username from all_users
                where (%s) /*%s*/ order by %s""", "username"),
    "view"      :    ("""select owner, view_name from all_views
                where (%s) and owner like '%s' order by %s""", "view_name")
    }

guessInfoSql = {
    "commentFromNameAndOwner"    :    """select comments from all_tab_comments
                        where table_name=:1
                        and owner=:2""",
    "typeFromNameAndOwner"    :    """select object_type from all_objects
                        where object_name=:1
                        and owner=:2""",
    "typeFromNameAndSYS"    :    """select object_type from dba_objects
                        where object_name=:1
                        and owner='SYS'""",
    "otherTypeFromName"    :    """select 'USER' from all_users
                        where username=:1
                       union
                       select 'TABLESPACE' from dba_tablespaces
                        where tablespace_name=:1
                       union
                       select 'DATA FILE' from dba_data_files
                        where file_name=:1""",
    "objectStatusFromName"    :    """select status from all_objects
                        where object_name=:1""",
    "objectStatusFromNameAndOwner"    :    """select status from all_objects
                        where object_name=:1
                        and owner=:2""",
    "dbfStatusFromName"    :    """select status from dba_data_files
                        where file_name=:1""",
    "tbsStatusFromName"    :    """select status from dba_tablespaces
                        where tablespace_name=:1""",
    "userStatusFromName"    :    """select account_status from dba_users
                        where username=:1"""
    }

directorySql = {
    "pathFromName"        :    """select directory_path
                        from all_directories
                        where directory_name=:1"""
    }

datafileSql = {
    "tablespaceFromName"    :    """select tablespace_name
                        from dba_data_files
                        where file_name=:1""",
    "allocatedBytesFromName"    :   """select bytes
                        from dba_data_files
                        where file_name=:1""",
    "freeBytesFromName"    :    """select nvl(sum(fr.bytes), 0)
                        from dba_data_files df, dba_free_space fr
                        where df.file_id=fr.file_id
                          and df.file_name=:1"""
    }

dbLinkSql = {
    "hostFromOwnerAndName"    :    """select owner, host
                        from all_db_links
                        where db_link=:1""",
    "usernameFromOwnerAndName"    :    """select owner, username
                        from all_db_links
                        where db_link=:1"""
    }

indexSql = {
    "propertiesFromOwnerAndName" : """ select TABLE_OWNER, TABLE_NAME, INDEX_TYPE, UNIQUENESS,
                                              COMPRESSION, LEAF_BLOCKS, DISTINCT_KEYS,
                                              AVG_LEAF_BLOCKS_PER_KEY
                                              from  all_indexes
                                              where owner=:1
                                              and index_name=:2""",
    "indexedColumnsFromOwnerAndName" : """select COLUMN_NAME, COLUMN_POSITION
                                              from  ALL_IND_COLUMNS
                                              where index_owner=:1
                                              and index_name=:2
                                              order by COLUMN_POSITION""",
    "isPartitionedFromOwnerAndName" :  """select partitioned
                                              from all_indexes
                                              where owner=:1
                                              and index_name=:2""",
    "tablespaceFromOwnerAndName" :     """select tablespace_name
                                              from all_indexes
                                              where owner=:1
                                              and index_name=:2"""
    }

metadataSql = {
    "ddlFromTypeNameAndOwner"    : """select
                                         dbms_metadata.get_ddl(:1, :2, :3)
                                         from dual"""
     }

mviewSql = {
    "queryFromOwnerAndName" :    """select owner, query
                        from all_mviews
                        where owner=:1
                          and mview_name=:2"""
    }

packageSql = {
    "proceduresFromOwnerAndName"    :    """select procedure_name
                        from all_procedures
                        where owner=:1
                          and object_name=:2""",
    "sourceFromOwnerAndName" : """ select line, replace(replace(text, chr(10), ' '), chr(13), ' ')
                        from  all_source
                        where owner=:1
                          and name=:2
                        order by line"""
    }

sequenceSql = {
    "lastFromOwnerAndName"    :    """select sequence_owner, last_number
                        from all_sequences
                        where sequence_owner=:1
                          and sequence_name=:2""",
    "minFromOwnerAndName"    :    """select sequence_owner, min_value
                        from all_sequences
                        where sequence_owner=:1
                          and sequence_name=:2""",
    "maxFromOwnerAndName"    :    """select sequence_owner, max_value
                        from all_sequences
                        where sequence_owner=:1
                          and sequence_name=:2""",
    "stepFromOwnerAndName"    :    """select sequence_owner, increment_by
                        from all_sequences
                        where sequence_owner=:1
                          and sequence_name=:2"""
    }

synonymSql = {
    "targetFromOwnerAndName" :     """select table_owner, table_name
                        from all_synonyms
                        where owner=:1
                          and synonym_name=:2"""
    }

storedObjectSql = {
    "sourceFromOwnerAndNameAndType"   :    """select text from all_source
                                        where owner=:1
                                        and name=:2
                                        and type=:3
                                        order by line"""
    }

tableSql = {
    "indexedColFromOwnerAndName"    :    """select column_name, index_name, column_position
                                              from all_ind_columns
                                              where table_owner=:1
                                              and table_name=:2""",
    "primaryKeyFromOwnerAndName"    :    """select col.column_name
                                              from all_constraints cons, all_cons_columns col
                                              where cons.constraint_type='P'
                                              and cons.owner=:1
                                              and cons.table_name=:2
                                              and cons.owner=col.owner
                                              and cons.table_name=col.table_name
                                              and col.constraint_name=cons.constraint_name
                                              order by col.position""",
    "lastAnalyzedFromOwnerAndName"  :    """select last_analyzed
                                              from all_tables
                                              where owner=:1
                                              and table_name=:2""",
    "numRowsFromOwnerAndName"       :    """select num_rows
                                              from all_tables
                                              where owner=:1
                                              and table_name=:2""",
    "avgRowLengthFromOwnerAndName"  :    """select avg_row_len
                                              from all_tables
                                              where owner=:1
                                              and table_name=:2""",
    "usedBlocksFromOwnerAndName"    :    """select blocks
                                              from dba_segments
                                              where owner=:1
                                              and segment_type='TABLE'
                                              and segment_name=:2""",
    "neededBlocksFromOwnerAndName"  :    """select
                                              count(distinct dbms_rowid.rowid_block_number(rowid))
                                              from %s.%s""",
    "isPartitionedFromOwnerAndName" :    """select partitioned
                                              from all_tables
                                              where owner=:1
                                              and table_name=:2""",
    "tablespaceFromOwnerAndName" :      """select tablespace_name
                                              from all_tables
                                              where owner=:1
                                              and table_name=:2"""
    }

tablespaceSql = {
    "datafilesFromName"    :    """select file_name
                        from dba_data_files
                        where tablespace_name=:1"""
    }

tabularSql = {
    "commentFromOwnerAndName"    :    """select comments from all_tab_comments
                        where owner=:1
                          and table_name=:2""",
    "commentFromDBAAndName"    :    """select comments from dba_tab_comments
                        where owner=:1
                          and table_name=:2""",
    "createdFromOwnerAndName"    :    """select created from all_objects
                        where owner=:1
                          and object_name=:2""",
    "createdFromDBAAndName"    :    """select created from dba_objects
                        where owner=:1
                          and object_name=:2""",
    "lastDDLFromOwnerAndName"    :    """select last_ddl_time from all_objects
                        where owner=:1
                          and object_name=:2""",
    "lastDDLFromDBAAndName"    :    """select last_ddl_time from dba_objects
                        where owner=:1
                          and object_name=:2""",
    "columnsFromOwnerAndName"    :    """select a.column_name, a.data_type||'('||a.data_length||')', a.nullable, c.comments
                    from all_tab_columns a, all_col_comments c
                    where a.owner=:1
                      and a.owner=c.owner
                      and a.table_name=:2
                      and a.table_name=c.table_name
                      and a.column_name=c.column_name""",
    "columnsFromDBAAndName"    :    """select a.column_name, a.data_type||'('||a.data_length||')', a.nullable, c.comments
                    from dba_tab_columns a, dba_col_comments c
                    where a.owner=:1
                      and a.owner=c.owner
                      and a.table_name=:2
                      and a.table_name=c.table_name
                      and a.column_name=c.column_name""",
    "numberOfColumnsFromOwnerAndName" :   """select count(*)
                                            from all_tab_columns
                                            where owner=:1
                                            and table_name=:2"""
    }

triggerSql = {
    "typeFromOwnerAndName"    :    """select trigger_type
                        from all_triggers
                        where owner=:1
                          and trigger_name=:2""",
    "eventFromOwnerAndName"   :    """select triggering_event
                        from all_triggers
                        where owner=:1
                          and trigger_name=:2""",
    "bodyFromOwnerAndName"    :    """select trigger_body
                        from all_triggers
                        where owner=:1
                          and trigger_name=:2""",
    "statusFromOwnerAndName"  :    """select status
                        from all_triggers
                        where owner=:1
                          and trigger_name=:2""",
    "tableFromOwnerAndName"  :    """select table_owner, table_name
                        from all_triggers
                        where owner=:1
                          and trigger_name=:2"""
    }

userSql = {
    "tablespaceFromName" :    """select tablespace_name
                        from dba_segments
                        where owner=:1
                        group by tablespace_name
                        union
                        select default_tablespace
                        from dba_users
                        where username=:1""",
    "defaultTbsFromName" :    """select default_tablespace
                        from dba_users
                        where username=:1""",
    "tempTbsFromName"    :    """select temporary_tablespace
                        from dba_users
                        where username=:1""",
    "nbTablesFromNameAndTbs"  :    """select count(*)
                        from all_tables
                        where owner=:1
                          and tablespace_name like :2""",
    "nbIndexesFromNameAndTbs"  :    """select count(*)
                        from all_indexes
                        where owner=:1
                          and tablespace_name like :2"""
    }

viewSql = {
    "queryFromOwnerAndName" :    """select owner, text
                        from all_views
                        where owner=:1
                          and view_name=:2""",
    "replaceQueryFromName"    :    """create or replace view %s as %s""",
    "replaceQueryFromFullName"    :    """create or replace view %s as %s"""
    }

# Thanks to TOra for many parts of these requests!
sessionStatSql = {
    "all"        :    """Select a.Sid "Id", a.Serial# "Serial", a.SchemaName "Schema",
                        a.OsUser "Osuser", substr(a.Machine, 0, decode(instr(a.Machine, '.'), 0, length(a.Machine), instr(a.Machine, '.')-1)) "Machine", a.Program "Program",
                        To_Char(a.Logon_Time, 'MON-DD HH24:MI') "Logged Since",
                        b.Block_Gets "Blk Gets", b.Consistent_Gets "Cons Gets",
                        b.Physical_Reads "Phy Rds", b.Block_Changes "Blk Chg",
                        b.Consistent_Changes "Cons Chg", c.Value * 10 "CPU(ms)",
                        a.Process "C PID", e.SPid "S PID", d.sql_text "SQL"
                        from v$session a, v$sess_io b, v$sesstat c, v$sql d, v$process e
                        where a.sid = b.sid ( + )
                        and a.sid = c.sid ( + )
                        and ( c.statistic# = 12 OR c.statistic# IS NULL )
                        and a.sql_address = d.address ( + )
                        and a.sql_hash_value = d.hash_value ( + )
                        and ( d.child_number = 0 OR d.child_number IS NULL )
                        and a.paddr = e.addr ( + )
                        %s
                        and a.TYPE!= 'BACKGROUND'
                        order by a.Sid""",
    "details"    :    """select b.Name,a.Value
                        from V$SesStat a, V$StatName b
                        where a.SID = :1 and a.statistic# = b.statistic#""",
    "ios"        :    """select sum(block_gets) "Block gets", sum(consistent_gets) "Consistent gets",
                               sum(physical_reads) "Physical reads", sum(block_changes) "Block changes",
                               sum(consistent_changes) "Consistent changes"
                          from v$sess_io
                        where sid in
                            (select b.sid
                                from v$session a,v$session b
                                where a.sid = :1 and a.audsid = b.audsid)""",
    "locks"        :    """select b.Object_Name "Object Name", b.Object_Type "Type",
                        decode(a.locked_mode,0,'None',1,'Null',2,'Row-S',
                                            3,'Row-X',4,'Share',5,'S/Row-X',
                                            6,'Exclusive',a.Locked_Mode) "Locked Mode"
                          from v$locked_object a,sys.all_objects b
                         where a.object_id = b.object_id
                           and a.session_id = :1""",
    "waitEvents"    :    """select cpu*10 "CPU(ms)", parallel*10 "Parallel execution",
                                filewrite*10 "DB File Write", writecomplete*10 "Write Complete",
                                fileread*10 "DB File Read", singleread*10 "DB Single File Read",
                                control*10 "Control File I/O", direct*10 "Direct I/O",
                                log*10 "Log file", net*10 "SQL*Net",
                        (total-parallel-filewrite-writecomplete-fileread-singleread-control-direct-log-net)
                        *10 "Other"
                        from (select
                            sum(decode(substr(event,1,2),'PX',time_waited,0))
                                -sum(decode(event,'PX Idle Wait',time_waited,0)) parallel,
                            sum(decode(event,'db file parallel write',time_waited,
                            'db file single write',time_waited,0)) filewrite,
                            sum(decode(event,'write complete waits',time_waited,NULL))
                            writecomplete, sum(decode(event,
                                'db file parallel read',time_waited,
                                'db file sequential read',time_waited,0)) fileread,
                            sum(decode(event,'db file scattered read',time_waited,0)) singleread,
                            sum(decode(substr(event,1,12),'control file',time_waited,0)) control,
                            sum(decode(substr(event,1,11),'direct path',time_waited,0)) direct,
                            sum(decode(substr(event,1,3),'log',time_waited,0)) log,
                            sum(decode(substr(event,1,7),'SQL*Net',time_waited,0))
                                -sum(decode(event,
                                    'SQL*Net message from client',time_waited,0)) net,
                            sum(decode(event,
                                'PX Idle Wait',0,'SQL*Net message from client',0,time_waited)) total
                                from v$session_event
                                where sid in (select b.sid
                                    from v$session a,v$session b
                                    where a.sid = :1 and a.audsid = b.audsid)),
                            (select value*10 cpu
                                from v$sesstat a where statistic# = 12
                                and a.sid in
                                (select b.sid from v$session a,v$session b
                                    where a.sid = :1 and a.audsid = b.audsid))""",
    "openCursors"    :        """select SQL_Text "SQL", Address||':'||Hash_Value " Address"
                        from v$open_cursor where sid = :1""",
    "currentStatement":     """Select  b.sql_text "SQL" from v$session a, v$sqltext b
                                where a.sql_address = b.address ( + )
                                and a.sql_hash_value = b.hash_value ( + )
                                and a.Sid=:1
                                order by b.piece""",
    "longops":               """select target "Target", message "Message", start_time "Start time", start_time + elapsed_seconds/(60*60*24) "End time",  round(100*sofar/totalwork,2) "Progress (%)"
                                from v$session_longops
                                where time_remaining!=0 and sid = :1 order by start_time"""
}

# Queries used in pysqlgraphics
datamodelSql = {
    "tablesFromOwner"          :    """SELECT table_name
                                       FROM all_tables tab
                                       WHERE owner='%s'
                                         AND (%s)
                                         AND table_name NOT LIKE '%%PLAN_TABLE'
                                         AND table_name NOT LIKE 'TOAD%%'
                                         AND temporary='N'
                                         AND NOT EXISTS (SELECT 1
                                                         FROM all_external_tables ext
                                                         WHERE ext.owner=tab.owner
                                                           AND ext.table_name=tab.table_name)""",
    "columnsFromOwnerAndTable" :    """SELECT column_name
                                            , data_type
                                            , (SELECT position
                                               FROM all_cons_columns col, all_constraints cst
                                               WHERE cst.owner=col.owner
                                                 AND tab.owner=col.owner
                                                 AND tab.table_name=col.table_name
                                                 AND tab.column_name=col.column_name
                                                 AND col.constraint_name=cst.constraint_name
                                                 AND cst.constraint_type='P') pk_position
                                       FROM all_tab_columns tab
                                       WHERE owner=:1
                                         AND table_name=:2
                                       ORDER BY pk_position, column_id""",
   "constraintsFromOwner"     :    """SELECT fk.constraint_name, fk.table_name, pk.table_name
                                       FROM all_constraints fk, all_constraints pk
                                       WHERE fk.owner='%s'
                                         AND pk.table_name in (%s)
                                         AND fk.table_name in (%s)
                                         AND fk.owner=pk.owner
                                         AND fk.r_constraint_name = pk.constraint_name
                                         AND fk.constraint_type = 'R'
                                         AND pk.constraint_type = 'P'"""
}

dependenciesSql = {
    "refByFromOwnerAndName"  :   """SELECT referenced_owner, referenced_name, referenced_type
                                       FROM all_dependencies
                                       WHERE owner=:1
                                         AND name=:2""",
    "refOnFromOwnerAndName"  :   """SELECT owner, name, 'None'
                                       FROM all_dependencies
                                       WHERE referenced_owner=:1
                                         AND referenced_name=:2 """
}

diskusageSql = {
    "Tablespaces"  :            """SELECT DISTINCT tablespace_name
                                   FROM user_segments
                                   WHERE segment_type in ('TABLE', 'TABLE PARTITION',
                                                          'INDEX', 'INDEX PARTITION')""",
    "TablespacesFromOwner"  :   """SELECT DISTINCT tablespace_name
                                   FROM dba_segments
                                   WHERE owner=:1
                                     AND segment_type in ('TABLE', 'TABLE PARTITION',
                                                          'INDEX', 'INDEX PARTITION')""",
    "TablesFromTbs" :           """SELECT t.table_name, t.num_rows, t.avg_row_len, s.bytes
                                   FROM all_tables t, user_segments s
                                   WHERE t.tablespace_name=:1
                                     AND t.table_name=s.segment_name
                                     AND t.temporary='N'
                                     AND t.table_name NOT IN (select table_name from all_external_tables)
                                   UNION
                                   SELECT p.table_name||'/'||p.partition_name, p.num_rows, p.avg_row_len, s.bytes
                                   FROM all_tab_partitions p, user_segments s
                                   WHERE p.tablespace_name=:1
                                     AND p.partition_name=s.partition_name
                                     AND s.segment_type='TABLE PARTITION'""",
    "IndexesFromTbs" :          """SELECT i.index_name, i.num_rows, i.distinct_keys, s.bytes, i.table_name
                                     FROM all_indexes i, user_segments s
                                     WHERE i.tablespace_name=:1
                                       AND i.index_name=s.segment_name
                                       AND s.segment_type='INDEX'
                                     UNION
                                     SELECT p.index_name||'/'||p.partition_name, p.num_rows, p.distinct_keys, s.bytes, ''
                                     FROM all_ind_partitions p, user_segments s
                                     WHERE p.tablespace_name=:1
                                       AND p.partition_name=s.partition_name
                                       AND s.segment_type='INDEX PARTITION'""",
    "TablesFromOwnerAndTbs" :   """SELECT t.table_name, t.num_rows, t.avg_row_len, s.bytes
                                   FROM all_tables t, dba_segments s
                                   WHERE t.owner=:1
                                     AND t.tablespace_name=:2
                                     AND t.owner=s.owner
                                     AND t.table_name=s.segment_name
                                     AND t.temporary='N'
                                     AND t.table_name NOT IN (select table_name from all_external_tables)
                                   UNION
                                   SELECT p.table_name||'/'||p.partition_name, p.num_rows, p.avg_row_len, s.bytes
                                   FROM all_tab_partitions p, dba_segments s
                                   WHERE p.table_owner=:1
                                     AND p.tablespace_name=:2
                                     AND p.table_owner=s.owner
                                     AND p.partition_name=s.partition_name
                                     AND s.segment_type='TABLE PARTITION'""",
    "IndexesFromOwnerAndTbs" :   """SELECT i.index_name, i.num_rows, i.distinct_keys, s.bytes, i.table_name
                                     FROM all_indexes i, dba_segments s
                                     WHERE i.owner=:1
                                       AND i.tablespace_name=:2
                                       AND i.owner=s.owner
                                       AND i.index_name=s.segment_name
                                       AND s.segment_type='INDEX'
                                     UNION
                                     SELECT p.index_name||'/'||p.partition_name, p.num_rows, p.distinct_keys, s.bytes, ''
                                     FROM all_ind_partitions p, dba_segments s
                                     WHERE s.owner=:1
                                       AND p.index_owner=s.owner
                                       AND p.partition_name=s.partition_name
                                       AND s.segment_type='INDEX PARTITION'"""
}

# Audit functions queries
perfSql = {
    "db_id"             : """select to_char(dbid) from v$database""",
    "instance_num"      : """select to_char(instance_number) from v$instance""",
    "snapshots"         : """select snap_id id, begin_interval_time time from dba_hist_snapshot where begin_interval_time > (sysdate - :1) order by snap_id desc""",
    "addm_report_text"  : """select dbms_advisor.get_task_report(:1, :2, :3) from sys.dual""",
    "awr_report_html"   : """select * from table(dbms_workload_repository.awr_report_html(:1, :2, :3, :4))""",
    "awr_report_text"   : """select * from table(dbms_workload_repository.awr_report_text(:1, :2, :3, :4))""",
    "sqltune_text"      : """select dbms_sqltune.report_tuning_task(:1, :2, :3) from sys.dual"""
}

durptSql = {
    "nbTotalBlocks"        : """SELECT SUM(a.blocks) FROM DBA_SEGMENTS a WHERE a.tablespace_name LIKE :1 AND a.owner LIKE :2""",
    "tablesForTbsAndUser"  : """SELECT a.owner "Owner", a.tablespace_name "Tablespace", a.segment_name "Table", DECODE(COUNT(a.partition_name), 0, '', '*') "Part?", COUNT(c.column_name) "#Cols", d.num_rows "#Rows", a.blocks "Size(blk)", ROUND(a.blocks*b.block_size/1024/1024, 1) "Size(Mo)", ROUND((100*a.blocks)/:1, 1) "Size(%)" FROM DBA_SEGMENTS a, DBA_TABLESPACES b, DBA_TAB_COLUMNS C, DBA_TABLES d WHERE a.tablespace_name LIKE :2 AND a.owner LIKE :3 AND a.tablespace_name=b.tablespace_name AND a.segment_name=c.table_name AND a.segment_name=d.table_name AND a.segment_name NOT LIKE '%PLAN_TABLE' AND a.segment_type LIKE 'TABLE%' AND NOT EXISTS (SELECT NULL FROM DBA_TABLES WHERE owner=a.owner AND temporary='Y' AND table_name=a.segment_name) GROUP BY a.owner, a.tablespace_name, a.segment_name, a.blocks, b.block_size, d.num_rows ORDER BY a.blocks DESC""",
    "indexesForTbsAndUser" : """SELECT a.owner "Owner", a.tablespace_name "Tablespace", a.segment_name "Index", DECODE(COUNT(a.partition_name), 0, '', '*') "Part?", COUNT(c.blevel) "Level", c.distinct_keys "Keys", a.blocks "Size(blk)", ROUND(a.blocks*b.block_size/1024/1024, 1) "Size(Mo)", ROUND((100*a.blocks)/:1, 1) "Size(%)" FROM DBA_SEGMENTS a, DBA_TABLESPACES b, DBA_INDEXES c WHERE a.tablespace_name LIKE :2 AND a.owner LIKE :3 AND a.tablespace_name=b.tablespace_name AND a.segment_name=c.index_name AND a.segment_name NOT LIKE '%PLAN_TABLE' AND a.segment_type LIKE 'INDEX%' AND NOT EXISTS (SELECT NULL FROM DBA_TABLES WHERE owner=a.owner AND temporary='Y' AND table_name=a.segment_name) GROUP BY a.owner, a.tablespace_name, a.segment_name, a.blocks, b.block_size, c.blevel, c.distinct_keys ORDER BY a.blocks DESC"""
}

lockSql = {
    "objects" : """select  lo.oracle_username,
                            s.program,
                            lo.os_user_name,
                            decode(lo.locked_mode,
                                1, 'No Lock',
                                2, 'Row Share',
                                3, 'Row Exclusive',
                                4, 'Share',
                                5, 'Share Row Exclusive',
                                6, 'Exclusive',
                                'NONE') lock_mode,
                            o.object_name
                    from v$locked_object lo, dba_objects o, v$session s
                    where lo.object_id=o.object_id
                    and lo.session_id=s.sid""",
    "sessions" : """select s1.username || '-' || s1.program || ' ( SID=' || s1.sid || ' )',
                            s2.username || '-' || s2.program || ' ( SID=' || s2.sid || ' )'
                     from v$lock l1, v$session s1, v$lock l2, v$session s2
                     where s1.sid=l1.sid and s2.sid=l2.sid and l1.BLOCK=1
                     and l2.request > 0 and l1.id1 = l2.id1 and l2.id2 = l2.id2"""
}

gatherCompleteSql = {
    "table"     : """select table_name from user_tables""",
    "index"     : """select index_name from user_indexes""",
    "sequence"  : """select sequence_name from user_sequences""",
    "directory" : """select directory_name from all_directories""",
    "view"      : """select view_name from user_views""",
    "synonym"   : """select synonym_name from user_synonyms""",
    "trigger"   : """select trigger_name from user_triggers""",
    "user"      : """select username from all_users""",
}
