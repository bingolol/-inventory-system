<#
.SYNOPSIS
    进销存系统数据包热备脚本 v1.0
.DESCRIPTION
    对 SQLite 数据库执行热备份（PRAGMA wal_checkpoint + 文件复制），
    同时备份 uploads/images、pdfs 目录，生成带时间戳的备份包。
.NOTES
    作者: AI助手 | 日期: 2026-04-28
#>

param(
    [string]$BackupRoot = "C:\Backup\inventory-system",
    [int]$RetentionDays = 30,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupDir = Join-Path $BackupRoot $Timestamp
$SystemRoot = "C:\Users\Administrator\Desktop\inventory-system"
$BackendDir = Join-Path $SystemRoot "backend"
$DbFile = Join-Path $BackendDir "inventory.db"
$WalFile = Join-Path $BackendDir "inventory.db-wal"
$ShmFile = Join-Path $BackendDir "inventory.db-shm"

# ── 辅助函数 ──

function Write-Log {
    param([string]$Msg, [string]$Level = "INFO")
    $Time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $Line = "$Time [$Level] $Msg"
    Write-Host $Line
    if (-not (Test-Path $BackupRoot)) {
        New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
    }
    Add-Content -Path (Join-Path $BackupRoot "backup.log") -Value $Line -Encoding UTF8
}

function Invoke-SqliteCheckpoint {
    <#
    .SYNOPSIS
        通过 Python + SQLAlchemy 执行 WAL checkpoint，确保数据库文件完整可复制
    #>
    $CheckpointScript = @'
import sys, os
sys.path.insert(0, r"C:\Users\Administrator\Desktop\inventory-system\backend")
os.chdir(r"C:\Users\Administrator\Desktop\inventory-system\backend")

from sqlalchemy import create_engine, text
engine = create_engine("sqlite:///inventory.db", connect_args={"check_same_thread": False})
with engine.connect() as conn:
    # TRUNCATE 模式：将 WAL 内容写回主库文件，然后清空 WAL
    result = conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
    row = result.fetchone()
    print(f"CHECKPOINT_OK: busy={row[0]}, log_frames={row[1]}, checkpointed_frames={row[2]}")
conn.close()
engine.dispose()
'@
    $ScriptPath = Join-Path $env:TEMP "_checkpoint_$Timestamp.py"
    $CheckpointScript | Set-Content -Path $ScriptPath -Encoding UTF8
    try {
        $Output = & python $ScriptPath 2>&1
        if ($Output -match "CHECKPOINT_OK") {
            Write-Log "SQLite WAL checkpoint 成功: $Output"
            return $true
        } else {
            Write-Log "SQLite WAL checkpoint 失败: $Output" "ERROR"
            return $false
        }
    }
    finally {
        Remove-Item -Force $ScriptPath -ErrorAction SilentlyContinue
    }
}

# ── 主流程 ──

Write-Log "========== 热备份开始 =========="
Write-Log "备份目标: $BackupDir"

if ($DryRun) {
    Write-Log "[DryRun] 模拟运行，不执行实际操作"
}

# 1. 检查源目录是否存在
if (-not (Test-Path $SystemRoot)) {
    Write-Log "进销存系统目录不存在: $SystemRoot" "ERROR"
    exit 1
}

if (-not (Test-Path $DbFile)) {
    Write-Log "数据库文件不存在: $DbFile" "ERROR"
    exit 1
}

# 2. 创建备份目录
if (-not $DryRun) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    Write-Log "创建备份目录: $BackupDir"
}

# 3. WAL Checkpoint —— 将内存中的脏页刷到主库文件
Write-Log "执行 SQLite WAL checkpoint..."
$CheckpointOk = $false
if (-not $DryRun) {
    $CheckpointOk = Invoke-SqliteCheckpoint
    if (-not $CheckpointOk) {
        Write-Log "WAL checkpoint 失败，将尝试直接复制（可能获取到不一致的快照）" "WARN"
    }
} else {
    Write-Log "[DryRun] 跳过 WAL checkpoint"
    $CheckpointOk = $true
}

# 4. 复制数据库文件
Write-Log "备份数据库文件..."
$DbSize = (Get-Item $DbFile).Length
Write-Log "数据库大小: $([math]::Round($DbSize / 1KB, 2)) KB"

if (-not $DryRun) {
    # 使用 Copy-Item /Begin 开启异步读取，减少锁定时间
    Copy-Item -Path $DbFile -Destination (Join-Path $BackupDir "inventory.db") -Force
    Write-Log "数据库文件复制完成"

    # 如果 WAL 文件存在且 checkpoint 不成功，也备份 WAL 文件
    if ((Test-Path $WalFile) -and -not $CheckpointOk) {
        Copy-Item -Path $WalFile -Destination (Join-Path $BackupDir "inventory.db-wal") -Force
        Write-Log "WAL 文件也已备份（checkpoint 未成功）"
    }
    if ((Test-Path $ShmFile) -and -not $CheckpointOk) {
        Copy-Item -Path $ShmFile -Destination (Join-Path $BackupDir "inventory.db-shm") -Force
        Write-Log "SHM 文件也已备份（checkpoint 未成功）"
    }
}

# 5. 备份上传图片目录
$ImagesDir = Join-Path $BackendDir "uploads\images"
if (Test-Path $ImagesDir) {
    $ImageCount = (Get-ChildItem $ImagesDir -File -ErrorAction SilentlyContinue).Count
    Write-Log "备份上传图片 ($ImageCount 个文件)..."
    if (-not $DryRun) {
        $DestImagesDir = Join-Path $BackupDir "uploads\images"
        Copy-Item -Path $ImagesDir -Destination $DestImagesDir -Recurse -Force
        Write-Log "图片目录备份完成"
    }
} else {
    Write-Log "上传图片目录不存在，跳过" "WARN"
}

# 6. 备份 PDF 目录
$PdfsDir = Join-Path $BackendDir "pdfs"
if (Test-Path $PdfsDir) {
    $PdfCount = (Get-ChildItem $PdfsDir -File -ErrorAction SilentlyContinue).Count
    Write-Log "备份 PDF 文件 ($PdfCount 个文件)..."
    if (-not $DryRun) {
        $DestPdfsDir = Join-Path $BackupDir "pdfs"
        Copy-Item -Path $PdfsDir -Destination $DestPdfsDir -Recurse -Force
        Write-Log "PDF 目录备份完成"
    }
} else {
    Write-Log "PDF 目录不存在，跳过" "WARN"
}

# 7. 生成备份元信息
$MetaFile = Join-Path $BackupDir "backup_meta.json"
$Meta = @{
    timestamp       = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    version         = "1.0.0"
    source_dir      = $SystemRoot
    db_size_bytes   = $DbSize
    checkpoint_ok   = $CheckpointOk
    image_count     = if (Test-Path $ImagesDir) { $ImageCount } else { 0 }
    pdf_count       = if (Test-Path $PdfsDir) { $PdfCount } else { 0 }
    hostname        = $env:COMPUTERNAME
    script_version  = "1.0"
}

if (-not $DryRun) {
    $Meta | ConvertTo-Json -Depth 3 | Set-Content -Path $MetaFile -Encoding UTF8
    Write-Log "备份元信息已写入: $MetaFile"
}

# 8. 验证备份完整性
if (-not $DryRun) {
    Write-Log "验证备份完整性..."
    $BackupDb = Join-Path $BackupDir "inventory.db"
    if (Test-Path $BackupDb) {
        $BackupSize = (Get-Item $BackupDb).Length
        if ($BackupSize -gt 0 -and $BackupSize -eq $DbSize) {
            Write-Log "数据库备份验证通过 (大小匹配: $BackupSize bytes)"
        } else {
            Write-Log "数据库备份大小不匹配! 源: $DbSize, 备份: $BackupSize" "ERROR"
        }

        # 用 SQLite PRAGMA integrity_check 验证
        $VerifyScript = @"
import sqlite3
conn = sqlite3.connect(r'$BackupDb')
result = conn.execute('PRAGMA integrity_check').fetchone()[0]
print(f'INTEGRITY: {result}')
conn.close()
"@
        $VerifyPath = Join-Path $env:TEMP "_verify_$Timestamp.py"
        $VerifyScript | Set-Content -Path $VerifyPath -Encoding UTF8
        try {
            $VerifyOutput = & python $VerifyPath 2>&1
            if ($VerifyOutput -match "INTEGRITY: ok") {
                Write-Log "SQLite integrity_check 通过"
            } else {
                Write-Log "SQLite integrity_check 失败: $VerifyOutput" "ERROR"
            }
        }
        finally {
            Remove-Item -Force $VerifyPath -ErrorAction SilentlyContinue
        }
    } else {
        Write-Log "备份目录中未找到数据库文件!" "ERROR"
    }
}

# 9. 压缩备份目录（可选，减少磁盘占用）
if (-not $DryRun) {
    $ZipFile = "$BackupDir.zip"
    Write-Log "压缩备份到: $ZipFile"
    Compress-Archive -Path $BackupDir -DestinationPath $ZipFile -Force
    $ZipSize = (Get-Item $ZipFile).Length
    Write-Log "压缩完成，大小: $([math]::Round($ZipSize / 1MB, 2)) MB"

    # 压缩成功后删除原始目录，只保留 zip
    Remove-Item -Path $BackupDir -Recurse -Force
    Write-Log "已清理原始备份目录，保留 zip 文件"
}

# 10. 清理过期备份
Write-Log "清理超过 $RetentionDays 天的旧备份..."
$Cutoff = (Get-Date).AddDays(-$RetentionDays)
Get-ChildItem -Path $BackupRoot -Filter "*.zip" | Where-Object {
    $_.LastWriteTime -lt $Cutoff
} | ForEach-Object {
    Write-Log "删除旧备份: $($_.Name)"
    if (-not $DryRun) {
        Remove-Item -Path $_.FullName -Force
    }
}

Write-Log "========== 热备份完成 =========="
