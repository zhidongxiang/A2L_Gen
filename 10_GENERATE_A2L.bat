@echo off
set PWD_PATH=%cd%

set A2LTEMP_FILE=E:\Work\Git_Repository\XCP\_A2L\Template.a2l
set PATH_ABS_FILE=..\Integration_Project\Obj
set VARI_LIST_FILE=.\Variable_Configuration.xls

set DEBUG_INFO_FILE=.\debug_info.txt

python Generate_A2l.py %PATH_ABS_FILE% %A2LTEMP_FILE% %VARI_LIST_FILE%

REM if %errorlevel% == 1 (
REM     echo on
REM     echo Generate a2l file failed!!!
REM )else (
REM     echo on
REM     echo Generate a2l file successfully!!!
REM )

pause
EXIT /b 0