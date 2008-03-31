@REM
@REM Sébastien Delcros (sebastien.delcros@gmail.com)

@REM Simple Win32 batch wrapper to launch pysql from source package
@REM This is intended only for developpers or users that don't want to "install" pysql
@REM but just use it from a simple directory

@REM Start it
@cd src\pysql
@del *.pyc
python pysqlmain.py %1 %2
