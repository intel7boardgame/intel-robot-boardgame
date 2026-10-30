<#
시연 PC(RTX 3050 6GB) 첫 점검을 한 번에 합니다 (작성: 김관영 C2). 자세한 순서는 docs/demo-pc-checklist.md.

  powershell -ExecutionPolicy Bypass -File scripts\demo_pc_check.ps1                       # 전부 (인터넷으로 모델 받기)
  powershell -ExecutionPolicy Bypass -File scripts\demo_pc_check.ps1 -ModelsFrom E:\ollama  # USB에서 모델 복사
  powershell -ExecutionPolicy Bypass -File scripts\demo_pc_check.ps1 -NoRobot              # LeRobot·torch 설치 생략
  powershell -ExecutionPolicy Bypass -File scripts\demo_pc_check.ps1 -WithBig              # exaone3.5:7.8b도 비교

결과: data\env_report_<PC이름>.md (환경 점검), data\bench_<PC이름>.md (중계 모델 비교)
#>
param([string]$ModelsFrom = "", [switch]$NoRobot, [switch]$WithBig, [int]$Runs = 10)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$V = Get-Content versions.json -Raw -Encoding UTF8 | ConvertFrom-Json
$Models = @()
foreach ($p in $V.ollama.models.PSObject.Properties) {
    if (-not $p.Value.optional -or $WithBig) { $Models += $p.Name }   # 모델 목록·digest는 versions.json 기준
}
$Host_ = [System.Net.Dns]::GetHostName()   # check_env.py(socket.gethostname)와 같은 이름

function Step($msg) { Write-Host "`n#### $msg" -ForegroundColor Magenta }
function Has($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function OllamaUp {
    try { Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 3 | Out-Null; return $true } catch { return $false }
}

Step "A. Ollama 설치·실행"
$env:Path = "$env:LOCALAPPDATA\Programs\Ollama;$env:Path"
if (-not (Has ollama)) {
    if (-not (Has winget)) { throw "winget이 없습니다. https://ollama.com/download 에서 직접 설치 후 다시 실행하세요" }
    winget install --id Ollama.Ollama -e --version $V.ollama.app --accept-source-agreements --accept-package-agreements
    $env:Path = "$env:LOCALAPPDATA\Programs\Ollama;$env:Path"
}
ollama --version
if (-not (OllamaUp)) {
    Write-Host "Ollama 서버를 켭니다"
    Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
    for ($i = 0; $i -lt 30 -and -not (OllamaUp); $i++) { Start-Sleep 1 }
    if (-not (OllamaUp)) { throw "Ollama 서버가 30초 안에 켜지지 않았습니다. 트레이에서 Ollama를 실행한 뒤 다시 실행하세요" }
}

Step "B. 개발 환경 (setup_env.ps1)"
$setup = Join-Path $PSScriptRoot "setup_env.ps1"
if ($NoRobot) { & $setup } else { & $setup -Robot }
# setup_env.ps1 마지막 점검은 시연 기준이 아니라서 실패해도 계속 진행합니다 (아래 C·D에서 다시 확인)
$Py = Join-Path $Root ".venv\Scripts\python.exe"

Step "C. 중계 모델 준비: $($Models -join ', ')"
if ($ModelsFrom) {
    & $Py scripts\ollama_models.py import $ModelsFrom
}
$have = (Invoke-RestMethod http://127.0.0.1:11434/api/tags).models.name
foreach ($m in $Models) {
    if ($have -contains $m) { Write-Host "$m 있음" } else { ollama pull $m; if ($LASTEXITCODE -ne 0) { throw "$m 다운로드 실패" } }
}

Step "D. 환경 점검 (시연 기준)"
$checkArgs = @("scripts\check_env.py", "--demo")
if (-not $NoRobot) { $checkArgs += "--robot" }
& $Py @checkArgs
$envOk = $LASTEXITCODE -eq 0

Step "E. 중계 모델 비교 ($($Runs)회씩)"
$bench = "data\bench_$Host_.md"
& $Py scripts\bench_llm.py --models @Models --runs $Runs --out $bench

Step "끝"
Write-Host "환경 점검: data\env_report_$Host_.md"
Write-Host "모델 비교: $bench"
Write-Host "두 파일을 팀 채널이나 docs/prep-notes.md에 붙여 주세요."
if (-not $envOk) { Write-Host "환경 점검에 ❌ 항목이 있습니다. data\env_report_$Host_.md를 확인하세요." -ForegroundColor Yellow; exit 1 }
Write-Host "모두 통과" -ForegroundColor Green
