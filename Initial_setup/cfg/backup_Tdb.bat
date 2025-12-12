@echo off
setlocal enabledelayedexpansion

:: =========================================
::  SQLite 数据库备份脚本 - 增强版
::  功能：自动备份、压缩、清理旧文件、写日志
:: =========================================

:: ========== 配置区 ==========
set "BACKUP_DIR=T:\Servo Gun\backup\db_backups"
set "DB_SOURCE=T:\Servo Gun\release\db.sqlite3"
set "LOG_FILE=%BACKUP_DIR%\backup.log"
set "RETENTION_DAYS=90"
:: ============================

:: 检查源数据库是否存在
if not exist "%DB_SOURCE%" (
    echo [%date% %time%] ERROR: 数据库文件不存在: %DB_SOURCE% >> "%LOG_FILE%"
    echo 数据库文件未找到，请检查路径！
    exit /b 1
)

:: 创建备份目录
powershell -NoProfile -Command "New-Item -ItemType Directory -Force '%BACKUP_DIR%'" >nul 2>&1

:: 使用 PowerShell 获取标准格式时间戳（避免系统格式问题）
for /f "delims=" %%a in ('powershell Get-Date -Format yyyyMMddHHmmss') do set "TIMESTAMP=%%a"
set "BACKUP_FILE=%BACKUP_DIR%\db_backup_%TIMESTAMP%.zip"

:: 开始备份
echo [%date% %time%] INFO: 开始备份数据库... >> "%LOG_FILE%"
echo 正在备份数据库...

:: 执行压缩（使用 PowerShell）
powershell -NoProfile -Command "try { Compress-Archive -Path '%DB_SOURCE%' -DestinationPath '%BACKUP_FILE%' -Force; exit 0 } catch { Write-Host $_; exit 1 }" 
if !errorlevel! neq 0 (
    echo [%date% %time%] ERROR: 备份失败！压缩出错 >> "%LOG_FILE%"
    echo 备份失败：无法压缩数据库文件。
    exit /b 1
)

:: 检查备份文件是否生成
if exist "%BACKUP_FILE%" (
    echo [%date% %time%] SUCCESS: 备份成功: %BACKUP_FILE% >> "%LOG_FILE%"
    echo 备份成功: %BACKUP_FILE%
) else (
    echo [%date% %time%] ERROR: 备份失败！文件未生成 >> "%LOG_FILE%"
    echo 备份失败：文件未生成。
    exit /b 1
)

:: 清理旧备份
echo [%date% %time%] INFO: 开始清理 %RETENTION_DAYS% 天前的备份... >> "%LOG_FILE%"
powershell -NoProfile -Command "Get-ChildItem '%BACKUP_DIR%' -Filter *.zip | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-%RETENTION_DAYS%) } | Remove-Item -Force" >nul 2>&1
echo [%date% %time%] INFO: 旧备份清理完成 >> "%LOG_FILE%"
echo 旧备份清理完成。

:: 可选：发送通知（如调用 webhook、邮件脚本等）
:: call send_notification.bat "Backup Success: %TIMESTAMP%"

exit /b 0