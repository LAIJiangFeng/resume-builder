# author: jf
[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 8999
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $scriptDir "spring-ai-backend"
$pomFile = Join-Path $backendDir "pom.xml"
$envFile = Join-Path $backendDir ".env"
$envExampleFile = Join-Path $backendDir ".env.example"

function Get-JavaMajorVersion {
    param(
        [Parameter(Mandatory = $true)]
        [string]$JavaHome
    )

    $javaExe = Join-Path $JavaHome "bin\java.exe"
    $javacExe = Join-Path $JavaHome "bin\javac.exe"
    if (-not (Test-Path -LiteralPath $javaExe) -or -not (Test-Path -LiteralPath $javacExe)) {
        return $null
    }

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $versionOutput = @(& $javaExe -version 2>&1)
        $javaExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    if ($javaExitCode -ne 0) {
        return $null
    }

    $versionLine = $versionOutput | Select-Object -First 1

    if ([string]$versionLine -match 'version "(?:1\.)?(\d+)') {
        return [int]$Matches[1]
    }

    return $null
}

function Add-JavaHomeCandidate {
    param(
        [AllowEmptyString()]
        [string]$Path
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return
    }

    $normalizedPath = $Path.Trim().TrimEnd('\')
    if (-not $javaHomeCandidates.Contains($normalizedPath)) {
        [void]$javaHomeCandidates.Add($normalizedPath)
    }
}

Write-Host "[1/5] 检查 Spring 后端目录和配置..." -ForegroundColor Cyan
if (-not (Test-Path -LiteralPath $pomFile)) {
    Write-Host "[错误] 未找到 Spring 后端项目：$pomFile" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path -LiteralPath $envFile)) {
    if (-not (Test-Path -LiteralPath $envExampleFile)) {
        Write-Host "[错误] 未找到 .env 或 .env.example。" -ForegroundColor Red
        exit 1
    }

    Copy-Item -LiteralPath $envExampleFile -Destination $envFile
    Write-Host "[提示] 已根据 .env.example 创建 spring-ai-backend/.env。" -ForegroundColor Yellow
    Write-Host "[提示] 请先填写数据库、模型和邮箱配置，再重新运行本脚本。" -ForegroundColor Yellow
    exit 1
}

Write-Host "[2/5] 查找 JDK 21..." -ForegroundColor Cyan
$javaHomeCandidates = [System.Collections.Generic.List[string]]::new()
Add-JavaHomeCandidate -Path $env:JAVA_HOME

$currentJavaCommand = Get-Command java.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -ne $currentJavaCommand) {
    Add-JavaHomeCandidate -Path (Split-Path -Parent (Split-Path -Parent $currentJavaCommand.Source))
}

$javaSearchRoots = @(
    (Join-Path $env:USERPROFILE ".jdks"),
    "C:\Program Files\Java",
    "C:\Program Files\Eclipse Adoptium",
    "C:\Program Files\Microsoft",
    "D:\Software",
    "D:\Java"
)

foreach ($searchRoot in $javaSearchRoots) {
    if (-not (Test-Path -LiteralPath $searchRoot)) {
        continue
    }

    if (Test-Path -LiteralPath (Join-Path $searchRoot "bin\java.exe")) {
        Add-JavaHomeCandidate -Path $searchRoot
    }

    Get-ChildItem -LiteralPath $searchRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '(?i)(jdk|jbr|java|temurin|corretto|openjdk)' } |
        ForEach-Object { Add-JavaHomeCandidate -Path $_.FullName }
}

$javaHome = $null
$detectedJavaVersions = [System.Collections.Generic.List[string]]::new()
foreach ($candidate in $javaHomeCandidates) {
    $majorVersion = Get-JavaMajorVersion -JavaHome $candidate
    if ($null -eq $majorVersion) {
        continue
    }

    [void]$detectedJavaVersions.Add("$candidate (Java $majorVersion)")
    if ($majorVersion -eq 21) {
        $javaHome = $candidate
        break
    }
}

if ([string]::IsNullOrWhiteSpace($javaHome)) {
    Write-Host "[错误] 未找到包含 java.exe 和 javac.exe 的 JDK 21。" -ForegroundColor Red
    if ($detectedJavaVersions.Count -gt 0) {
        Write-Host "[提示] 当前发现的 Java：" -ForegroundColor Yellow
        $detectedJavaVersions | ForEach-Object { Write-Host "  $_" }
    }
    Write-Host "[提示] 安装 JDK 21，或将 JAVA_HOME 指向 JDK 21 后重试。" -ForegroundColor Yellow
    exit 1
}

$env:JAVA_HOME = $javaHome
$env:Path = "$(Join-Path $javaHome 'bin');$env:Path"
Write-Host "[通过] 使用 JDK 21：$javaHome" -ForegroundColor Green

Write-Host "[3/5] 检查 Maven 运行环境..." -ForegroundColor Cyan
$mavenCommand = Get-Command mvn.cmd -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $mavenCommand) {
    $mavenCommand = Get-Command mvn -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
}
if ($null -eq $mavenCommand) {
    Write-Host "[错误] 未找到 Maven，请先安装 Maven 3.9+ 并加入 PATH。" -ForegroundColor Red
    exit 1
}

$mavenVersionOutput = @(& $mavenCommand.Source -version 2>&1)
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] Maven 无法正常运行。" -ForegroundColor Red
    $mavenVersionOutput | ForEach-Object { Write-Host $_ }
    exit 1
}

$mavenJavaVersion = $mavenVersionOutput | Where-Object { $_ -match '^Java version:' } | Select-Object -First 1
if ([string]$mavenJavaVersion -notmatch '^Java version: 21(?:\.|,)') {
    Write-Host "[错误] Maven 没有使用 JDK 21：$mavenJavaVersion" -ForegroundColor Red
    exit 1
}
Write-Host "[通过] Maven 已使用 JDK 21。" -ForegroundColor Green

Write-Host "[4/5] 检查端口 $Port..." -ForegroundColor Cyan
$listeners = @(
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Sort-Object OwningProcess -Unique
)

if ($listeners.Count -gt 0) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/actuator/health" -TimeoutSec 2
        if ($health.status -eq "UP") {
            Write-Host "[提示] Spring 后端已经在 http://127.0.0.1:$Port 运行，无需重复启动。" -ForegroundColor Green
            exit 0
        }
    }
    catch {
        # 健康检查失败时继续输出端口占用详情。
    }

    Write-Host "[错误] 端口 $Port 已被占用，脚本不会强制结束该进程。" -ForegroundColor Red
    foreach ($listener in $listeners) {
        $processId = $listener.OwningProcess
        $processName = (Get-Process -Id $processId -ErrorAction SilentlyContinue).ProcessName
        $processCommand = (Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue).CommandLine
        Write-Host "  PID=$processId 进程=$processName"
        if (-not [string]::IsNullOrWhiteSpace($processCommand)) {
            Write-Host "  命令=$processCommand"
        }
    }
    Write-Host "[提示] 请先关闭占用进程，再重新运行本脚本。" -ForegroundColor Yellow
    exit 1
}

Write-Host "[5/5] 启动 Spring AI 后端：http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host "健康检查：http://127.0.0.1:$Port/actuator/health"
Write-Host "按 Ctrl+C 可停止后端。"
$env:SERVER_PORT = [string]$Port

$exitCode = 1
Push-Location $backendDir
try {
    & $mavenCommand.Source spring-boot:run
    $exitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

if ($exitCode -ne 0) {
    Write-Host "[错误] Spring 后端已退出，退出码：$exitCode" -ForegroundColor Red
}
else {
    Write-Host "Spring 后端已停止。" -ForegroundColor Yellow
}
exit $exitCode
