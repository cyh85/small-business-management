#Requires -Version 5.1
<#
.SYNOPSIS
    横纵分析法 Skill 一键安装器
.DESCRIPTION
    下载 small-business-management 仓库,把 hv-analysis skill 复制到本机 AI 工具的 skills 目录。
    支持: Claude Code / Claude CLI / Cursor / OpenCode
    不需要预先安装 git(用 GitHub ZIP 下载)。
.EXAMPLE
    irm https://raw.githubusercontent.com/cyh85/small-business-management/main/install.ps1 | iex
#>

$ErrorActionPreference = 'Stop'

$RepoUrl    = 'https://github.com/cyh85/small-business-management'
$ZipUrl     = "$RepoUrl/archive/refs/heads/main.zip"
$SkillName  = 'hv-analysis'

# 各工具 skills 目录(按优先级)
$Targets = @(
    @{ Name = 'Claude';   Win = "$env:USERPROFILE\.claude\skills";            Unix = "$HOME/.claude/skills" }
    @{ Name = 'Cursor';   Win = "$env:USERPROFILE\.cursor\skills";           Unix = "$HOME/.cursor/skills" }
    @{ Name = 'OpenCode'; Win = "$env:USERPROFILE\.config\opencode\skills";  Unix = "$HOME/.config/opencode/skills" }
)

function Get-SkillBase {
    param($Target)
    if ($IsWindows -or ($env:OS -match 'Windows')) {
        return $Target.Win
    } else {
        return $Target.Unix
    }
}

Write-Host "`n[横纵分析法] 一键安装器" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# 1. 确定临时目录并下载 ZIP
$TempDir = Join-Path $env:TEMP "hv_install_$(Get-Random)"
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null
$ZipPath = Join-Path $TempDir "repo.zip"

Write-Host "[1/4] 下载仓库 ZIP ..." -ForegroundColor Yellow
try {
    Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipPath -UseBasicParsing -TimeoutSec 120
} catch {
    Write-Host "  下载失败: $_" -ForegroundColor Red
    Write-Host "  请检查网络(可能需要代理)或手动 clone 仓库。" -ForegroundColor Red
    exit 1
}

# 2. 解压
Write-Host "[2/4] 解压 ..." -ForegroundColor Yellow
$ExtractDir = Join-Path $TempDir "extracted"
Expand-Archive -Path $ZipPath -DestinationPath $ExtractDir -Force

# 找到 skills/hv-analysis(解压后顶层目录带 -main 后缀)
$SourceSkill = Get-ChildItem -Path $ExtractDir -Recurse -Directory -Filter $SkillName | Select-Object -First 1
if (-not $SourceSkill) {
    Write-Host "  未找到 skills/$SkillName,仓库结构可能已变更。" -ForegroundColor Red
    exit 1
}

# 3. 检测已安装的工具并复制
Write-Host "[3/4] 检测 AI 工具并安装 Skill ..." -ForegroundColor Yellow
$InstalledAny = $false
foreach ($t in $Targets) {
    $base = Get-SkillBase $t
    if (Test-Path $base) {
        $dest = Join-Path $base $SkillName
        Copy-Item -Path $SourceSkill.FullName -Destination $dest -Recurse -Force
        Write-Host "  [OK] 已安装到 $($t.Name): $dest" -ForegroundColor Green
        $InstalledAny = $true
    }
}

# 如果都没检测到,默认装到 Claude
if (-not $InstalledAny) {
    $base = Get-SkillBase $Targets[0]
    New-Item -ItemType Directory -Path $base -Force | Out-Null
    $dest = Join-Path $base $SkillName
    Copy-Item -Path $SourceSkill.FullName -Destination $dest -Recurse -Force
    Write-Host "  [默认] 未检测到已有工具,已安装到 Claude: $dest" -ForegroundColor Green
    Write-Host "  如果你用 Cursor / OpenCode,请手动把 $dest 复制到对应 skills 目录。" -ForegroundColor Gray
}

# 4. 清理
Write-Host "[4/4] 清理临时文件 ..." -ForegroundColor Yellow
Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "`n[完成] 横纵分析法 Skill 已安装!" -ForegroundColor Green
Write-Host "使用方法:在 Claude / Cursor / OpenCode 中直接说"用横纵分析法研究 XXX"" -ForegroundColor White
Write-Host "或查看课程配套 README:https://github.com/cyh85/small-business-management`n" -ForegroundColor Gray
