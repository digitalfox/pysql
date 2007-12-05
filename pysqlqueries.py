#!/usr/bin/python
# -*- coding: utf-8 -*-

# Sébastien Renard (sebastien.renard@digitalfox.org)
# Sébastien Delcros (sebastien.delcros@gmail.com)
# Code licensed under GNU GPL V2

"""SQL queries ordered by theme in dictionary"""

# pylint: disable-msg=C0103
searchObjectSqlRequest={
    "table"     :    ("""select owner, table_name
                from all_tables
                where %s and owner like '%s' order by %s""", "table_name")
    }

searchObjectSql={
    "datafile"  :    """select 'Datafiles', file_name
                from dba_data_files
                where file_name like :1 and :2=:2""",
    "directory" :    """select owner, directory_name
                from all_directories
                where directory_name like :1 and owner like :2""",
    "index"     :    """select owner, index_name
                from all_indexes
                where index_name like :1 and owner like :2 order by index_name""",
    "function"  :    """select distinct owner, name
                from all_source
                where name like :1 and owner like :2 and type='FUNCTION' order by name""",
    "package"   :    """select distinct owner, name
                from all_source
                where name like :1 and owner like :2 and type='PACKAGE' order by name""",
    "procedure" :    """select distinct owner, name
                from all_source
                where name like :1 and owner like :2 and type='PROCEDURE' order by name""",
    "sequence"  :    """select sequence_owner, sequence_name
                from all_sequences
                where sequence_name like :1 and sequence_owner like :2 order by sequence_name""",
    "synonym"   :    """select owner, synonym_name
                from all_synonyms
                where synonym_name like :1 and owner like :2 order by synonym_name""",
    "tablespace":    """select 'Tablespaces', tablespace_name
                from dba_tablespaces
                where tablespace_name like :1 and :2=:2""",
    "table"     :    """select owner, table_name
                from all_tables
                where table_name like :1 and owner like :2 order by table_name""",
    "trigger"   :    """select owner, trigger_name
                from all_triggers
                where trigger_name like :1 and owner like :2 order by trigger_name""",
    "view"      :    """select owner, view_name
                from all_views
                where view_name like :1 and owner like :2 order by view_name"""
    }

guessInfoSql={
    "commentFromNameAndOwner"    :    """select comments from all_tab_comments
                        where table_name=:1
                        and owner=:2 """,
    "typeFromNameAndOwner"    :    """select object_type from all_objects
                        where object_name=:1
                        and owner=:2 """,
    "typeFromNameAndSYS"    :    """select object_type from dba_objects
                        where object_name=:1
                        and owner='SYS' """,
    "otherTypeFromName"    :    """select 'USER' from all_users
                        where upper(username)=upper(:1)
                       union
                       select 'TABLESPACE' from dba_tablespaces
                        where upper(tablespace_name)=upper(:1)
                       union
                       select 'DATA FILE' from dba_data_files
                        where file_name=:1 """
    }

directorySql={
    "pathFromName"        :    """select directory_path
                        from all_directories
                        where directory_name=:1 """
    }

datafileSql={
    "tablespaceFromName"    :    """select tablespace_name
                        from dba_data_files
                        where file_name=:1 """,
    "allocatedBytesFromName"    :    """select bytes
                        from dba_data_files
                        where file_name=:1 """,
    "freeBytesFromName"    :    """select nvl(sum(fr.bytes), 0)
                        from dba_data_files df, dba_free_space fr
                        where df.file_id=fr.file_id
                          and df.file_name=:1 """
    }

dbLinkSql={
    "hostFromOwnerAndName"    :    """select owner, host
                        from all_db_links
                        where db_link=:1 """,
    "usernameFromOwnerAndName"    :    """select owner, username
                        from all_db_links
                        where db_link=:1 """
    }

indexSql={
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
                                              order by COLUMN_POSITION"""
    }

metadataSql={
    "ddlFromTypeNameAndOwner"    : """select
                                         dbms_metadata.get_ddl(:1, :2, :3)
                                         from dual"""
     }

mviewSql={
    "queryFromOwnerAndName" :    """select owner, query
                        from all_mviews
                        where owner=:1
                          and mview_name=:2 """
    }

sequenceSql={
    "lastFromOwnerAndName"    :    """select sequence_owner, last_number
                        from all_sequences
                        where sequence_owner=:1
                          and sequence_name=:2 """,
    "minFromOwnerAndName"    :    """select sequence_owner, min_value
                        from all_sequences
                        where sequence_owner=:1
                          and sequence_name=:2 """,
    "maxFromOwnerAndName"    :    """select sequence_owner, max_value
                        from all_sequences
                        where sequence_owner=:1
                          and sequence_name=:2 """,
    "stepFromOwnerAndName"    :    """select sequence_owner, increment_by
                        from all_sequences
                        where sequence_owner=:1
                          and sequence_name=:2 """
    }

synonymSql={
    "targetFromOwnerAndName" :     """select table_owner, table_name
                        from all_synonyms
                        where owner=:1
                          and synonym_name=:2 """
    }

storedObjectSql={
    "sourceFromOwnerAndNameAndType"   :    """select text from all_source
                                        where owner=:1
                                        and name=:2
                                        and type=:3
                                        order by line"""
    }

tableSql={
    "indexedColFromOwnerAndName"    :    """select column_name, index_name, column_position
                                              from all_ind_columns
                                              where table_owner=:1
                                              and table_name=:2 """,
    "primaryKeyFromOwnerAndName"    :    """select col.column_name 
                                              from all_constraints cons, all_cons_columns col
                                              where cons.constraint_type='P' 
                                              and cons.owner=:1
                                              and cons.table_name=:2
                                              and cons.owner=col.owner
                                              and cons.table_name=col.table_name 
                                              and col.constraint_name=cons.constraint_name
                                              order by col.position"""
    }

tablespaceSql={
    "datafilesFromName"    :    """select file_name
                        from dba_data_files
                        where tablespace_name=:1 """
    }

tabularSql={
    "commentFromOwnerAndName"    :    """select comments from all_tab_comments
                        where owner=:1
                          and table_name=:2 """,
    "commentFromDBAAndName"    :    """select comments from dba_tab_comments
                        where owner=:1
                          and table_name=:2 """,
    "columnsFromOwnerAndName"    :    """select a.column_name, a.data_type, a.nullable, c.comments
                    from all_tab_columns a, all_col_comments c
                    where a.owner=:1
                      and a.owner=c.owner
                      and a.table_name=:2
                      and a.table_name=c.table_name
                      and a.column_name=c.column_name""",
    "columnsFromDBAAndName"    :    """select a.column_name, a.data_type, a.nullable, c.comments
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

triggerSql={
    "typeFromOwnerAndName"    :    """select trigger_type
                        from all_triggers
                        where owner=:1
                          and trigger_name=:2 """,
    "eventFromOwnerAndName"   :    """select triggering_event
                        from all_triggers
                        where owner=:1
                          and trigger_name=:2 """,
    "bodyFromOwnerAndName"    :    """select trigger_body
                        from all_triggers
                        where owner=:1
                          and trigger_name=:2 """,
    "statusFromOwnerAndName"  :    """select status
                        from all_triggers
                        where owner=:1
                          and trigger_name=:2 """,
    "tableFromOwnerAndName"  :    """select table_owner, table_name
                        from all_triggers
                        where owner=:1
                          and trigger_name=:2 """
    }

userSql={
    "defaultTbsFromName"    :    """select default_tablespace
                        from dba_users
                        where username=:1 """,
    "tempTbsFromName"    :    """select temporary_tablespace
                        from dba_users
                        where username=:1 """
    }

viewSql={
    "queryFromOwnerAndName" :    """select owner, text
                        from all_views
                        where owner=:1
                          and view_name=:2 """,
    "replaceQueryFromName"    :    """create or replace view %s as %s """,
    "replaceQueryFromFullName"    :    """create or replace view %s as %s """
    }

# Thanks to TOra for many parts of these requests !
sessionStatSql={
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
                        from v$open_cursor where sid = :1 """,
    "currentStatement":     """Select  b.sql_text "SQL" from v$session a, v$sql b
                                where a.sql_address = b.address ( + )
                                and a.sql_hash_value = b.hash_value ( + )
                                and ( b.child_number = 0 OR b.child_number IS NULL )
                                and a.Sid=:1"""
}

# Queries used in pysqlgraphics
datamodelSql={
    "tablesFromOwner"          :    """SELECT table_name
                                       FROM all_tables tab
                                       WHERE owner=:1
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
                                       WHERE fk.owner=:1
                                         AND fk.owner=pk.owner
                                         AND fk.r_constraint_name = pk.constraint_name
                                         AND fk.constraint_type = 'R'
                                         AND pk.constraint_type = 'P'"""
}

dependenciesSql={
    "refByFromOwnerAndName"  :   """SELECT referenced_owner, referenced_name, referenced_type
                                       FROM all_dependencies
                                       WHERE owner=:1
                                         AND name=:2""",
    "refOnFromOwnerAndName"  :   """SELECT owner, name, 'None'
                                       FROM all_dependencies
                                       WHERE referenced_owner=:1
                                         AND referenced_name=:2 """
}

diskusageSql={
    "TablespacesFromOwner"  :   """SELECT DISTINCT tablespace_name
                                   FROM dba_segments
                                   WHERE owner=:1
                                     AND segment_type in ('TABLE', 'TABLE PARTITION',
                                                          'INDEX', 'INDEX PARTITION')""",
    "TablesFromOwnerAndTbs" :   """SELECT t.table_name, t.num_rows, t.avg_row_len, s.bytes
                                   FROM all_tables t, dba_segments s
                                   WHERE t.owner=:1
                                     AND t.tablespace_name=:2
                                     AND t.owner=s.owner
                                     AND t.table_name=s.segment_name
                                     AND t.temporary='N'
                                     AND t.table_name NOT IN (select table_name from all_external_tables)
                                   UNION
                                   SELECT p.partition_name, p.num_rows, p.avg_row_len, s.bytes
                                   FROM all_tab_partitions p, dba_segments s
                                   WHERE p.table_owner=:1
                                     AND p.tablespace_name=:2
                                     AND p.table_owner=s.owner
                                     AND p.partition_name=s.partition_name
                                     AND s.segment_type='TABLE PARTITION'
                                     """,
    "IndexesFromOwnerAndTbs" :   """SELECT i.index_name, i.num_rows, i.distinct_keys, s.bytes, i.table_name
                                     FROM all_indexes i, dba_segments s
                                     WHERE i.owner=:1
                                       AND i.tablespace_name=:2
                                       AND i.owner=s.owner
                                       AND i.index_name=s.segment_name
                                       AND s.segment_type='INDEX'
                                     UNION
                                     SELECT p.partition_name, p.num_rows, p.distinct_keys, s.bytes, ''
                                     FROM all_ind_partitions p, dba_segments s
                                     WHERE s.owner=:1
                                       AND p.index_owner=s.owner
                                       AND p.partition_name=s.partition_name
                                       AND s.segment_type='INDEX PARTITION'"""
}
