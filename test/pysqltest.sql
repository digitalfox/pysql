-- This is pysql test file. 
-- It is a quick and not so dirty way 
-- to detect pysql regression between two commit

-- It should be launched like this : cat pysqlTest.sql | pysql user/passwd@SID
-- Error sum up at the end should be empty except failed drop because objects does not exist

-- User must have the right to create object in his own schema
-- any object with a name begining by toto could be destroyed. You are warned.

-- Use echo mode to display statement (make debug easier)
set echo=yes

-- This is a test single line comment with double dash

/* This is a test single line comment with slash & star */

/* This is 
a multiline
comment
with slash
&
star
*/

-- Simple SQL statements
drop table toto_table;
create table toto_table(id integer);
insert into toto_table (id) values (1);
delete from toto_table where id=1;
insert into toto_table (id) values (1);
commit
insert into toto_table (id) values (2);
rollback
update toto_table set id=3 where id=1;
commit
select * from toto_table;
alter table toto_table add label varchar2(50);
comment on table toto_table is 'test table';
comment on column toto_table.id is 'test id';
truncate table toto_table;
drop table toto_table;
-- to be done : grant, revoke

-- multi line SQL statements
create 
table
toto_table(id integer);

insert
	into
		toto_table
			(id)
				values(1);
delete 
	from toto_table
	where id=1;
commit
drop 
table
toto_table
;

-- mix comment and SQL statements
create -- this is a create order !
table  -- this is a table
toto_table(id integer); -- this was a request
/* lala */
insert /* blabla */
	into
/**********************/
		toto_table /*
lala
*/
			(id)
				values(1)/* lala*/;
commit /* lala */
/* lala */ drop 
table 
toto_table
/**/;/**/

-- should add mix comment and hint tests

-- plsql
execute dbms_output.enable(10000)
execute dbms_output.put_line('coucou')

begin
	dbms_output.put_line('coucou');
	dbms_output.put_line('coucou');
end;
/

-- functions test

-- connect(self, arg)
-- disconnect(self, arg)

showCompletion

history
history 1

library
library dual select * from dual;
library
library dual
library dual remove

bg
select * from dual&
bg 
bg 1

-- commit(self, arg)
-- rollback(self, arg)

count dual

-- describe
-- tables (we consider that we are logged as system)
desc help
desc scott.emp
-- views
desc v$_session
-- synonym
desc v$instance
-- tablespace
desc temp
-- datafile
-- to be done

-- graphical stuff 
datamodel -u scott
-- test other options of datamodel
pkgtree xmldom

ddl scott.emp
ddl v$session
ddl v_$session

session
session 10
explain select * from dual;
-- fail because of privilege...
explain select * from all_source;

-- search object
index
table
table scott.%
table e
view
sequence
directory
segment
trigger
tablespace
datafile

/*
    def do_edit(self, arg):
    def do_execute(self, arg):
    def do_explain(self, arg):
    def do_kill(self, arg):
    def do_lock(self, arg):
     def do_last(self, arg):
    def do_next(self, arg):
    def do_get(self, arg):
    def do_set(self, arg):
            self.do_get("all")
    def do_write(self, arg):
    def do_shell(self, arg):
    def do_script(self, arg):
    def do_watch(self, arg):
    def do_csv(self, arg):
    def do_time(self, arg):
    def do_show(self, arg):
    def do_exit(self, arg):
*/
