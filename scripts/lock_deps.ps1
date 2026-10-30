<#
잠금 파일(*.lock) 다시 만들기 (작성: 김관영 C2). requirements*.txt나 versions.json의 torch를 바꾼 뒤에만 실행합니다.

  powershell -ExecutionPolicy Bypass -File scripts\lock_deps.ps1

requirements-robot.lock  공통 + CUDA torch + lerobot. Windows (시연 PC·A). 먼저 만듦
requirements.lock        공통. Windows·macOS·Linux 모두 (--universal). 로봇 lock과 겹치는 버전을 맞춤
만든 뒤 setup_env.ps1 -Recreate -Robot으로 새 환경에서 테스트가 통과하는지 보고 PR에 함께 올립니다 (docs/versions.md).
#>
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$V = Get-Content versions.json -Raw -Encoding UTF8 | ConvertFrom-Json
$Py = ($V.python.version -split "\.")[0..1] -join "."   # 3.12
$Header = "--no-header"

Write-Host "== requirements-robot.lock (Python $Py, Windows, CUDA $($V.torch.cuda))"
$tmp = Join-Path $Root "requirements-robot.in.tmp"   # -r 경로가 저장소 기준으로 풀리게 저장소 안에 만듦
$cuda = "cu" + ($V.torch.cuda -replace "\.", "")      # 12.8 → cu128
$torchPins = $V.torch.packages | ForEach-Object { "$_+$cuda" }
(@("-r requirements.txt") + $torchPins + @("-r requirements-robot.txt")) | Set-Content $tmp -Encoding ascii
uv pip compile $tmp --python-version $Py --python-platform windows $Header `
    --extra-index-url $V.torch.index_url --index-strategy unsafe-best-match -o requirements-robot.lock
$code = $LASTEXITCODE
Remove-Item $tmp
if ($code -ne 0) { throw "로봇 lock 실패" }

# 공통 lock은 로봇 lock을 제약으로 걸어, 겹치는 패키지가 두 환경에서 같은 버전이 되게 합니다 (예: packaging)
Write-Host "== requirements.lock (Python $Py, 모든 OS, 로봇 lock과 버전 맞춤)"
uv pip compile requirements.txt -c requirements-robot.lock --python-version $Py --universal $Header -o requirements.lock
if ($LASTEXITCODE -ne 0) { throw "공통 lock 실패" }
Write-Host "완료. git diff로 바뀐 버전을 확인하세요." -ForegroundColor Green
