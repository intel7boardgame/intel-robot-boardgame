<#
공통 개발 환경 설치 (작성: 김관영 C2). 버전은 versions.json과 잠금 파일(*.lock)을 따릅니다.

  powershell -ExecutionPolicy Bypass -File scripts\setup_env.ps1           # 공통 (게임·비전·LLM·화면)
  powershell -ExecutionPolicy Bypass -File scripts\setup_env.ps1 -Robot    # + 로봇(LeRobot, CUDA torch) - A·시연 PC
  powershell -ExecutionPolicy Bypass -File scripts\setup_env.ps1 -Recreate # .venv를 새로 만듦

1) uv 확인·설치  2) Python .venv (versions.json)  3) requirements.lock  4) (-Robot) requirements-robot.lock → opencv 복구 → FFmpeg
패키지는 uv pip sync로 lock과 똑같이 맞춥니다. lock에 없는 패키지를 따로 깔았다면 지워지니, 필요하면 requirements.txt에 넣고 lock을 다시 만듭니다.
5) 테스트·환경 점검. 기존 .venv의 Python이 다르면 .venv-old-<버전>-<시각>으로 옮기고 새로 만듭니다 (지우지 않음).
#>
param([switch]$Robot, [switch]$Recreate)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:UV_LINK_MODE = "copy"   # 캐시와 저장소가 다른 드라이브면 하드링크가 안 되므로 경고 없이 복사
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$V = Get-Content versions.json -Raw -Encoding UTF8 | ConvertFrom-Json
$PyVersion = $V.python.version                         # 예: 3.12.14
$PyMinor = ($PyVersion -split "\.")[0..1] -join "."     # 예: 3.12

function Step($msg) { Write-Host "`n== $msg" -ForegroundColor Cyan }
function Has($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function Check($what) { if ($LASTEXITCODE -ne 0) { throw "$what 실패 (exit $LASTEXITCODE)" } }
function TorchcodecOk {
    # Windows PowerShell 5.1은 Stop 상태에서 네이티브 명령의 stderr를 오류로 바꾸므로 잠시 Continue로
    $old = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    & $Py -c "import torchcodec" 2>$null | Out-Null
    $ok = $LASTEXITCODE -eq 0
    $ErrorActionPreference = $old
    return $ok
}
function RefreshPath {
    $env:Path = "$env:USERPROFILE\.local\bin;" + [Environment]::GetEnvironmentVariable("Path", "User") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "Machine")
}

Step "1/5 uv 확인 (최소 $($V.uv.min))"
if (-not (Has uv)) {
    Write-Host "uv가 없어 설치합니다"
    if (Has winget) {
        winget install --id astral-sh.uv -e --accept-source-agreements --accept-package-agreements
    } else {
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    }
    RefreshPath
    if (-not (Has uv)) { throw "uv를 설치했지만 찾을 수 없습니다. 새 PowerShell 창에서 다시 실행하세요" }
}
uv --version

Step "2/5 Python $PyVersion 가상환경 (.venv)"
$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path $Py) {
    $ver = & $Py -c "import sys; print('%d.%d.%d' % sys.version_info[:3])"
    if ($ver -ne $PyVersion -or $Recreate) {
        $bak = ".venv-old-$ver-" + (Get-Date -Format "MMdd_HHmm")
        Write-Host "기존 .venv(Python $ver)를 $bak 로 옮깁니다. 문제없으면 나중에 지워도 됩니다"
        Rename-Item .venv $bak
    } else {
        Write-Host "기존 .venv(Python $ver)를 그대로 씁니다"
    }
}
if (-not (Test-Path $Py)) { uv venv --python $PyVersion .venv; Check "venv 생성" }

if ($Robot) {
    Step "3/5 공통 + 로봇 패키지 ($($V.lock_files.robot): CUDA $($V.torch.cuda) torch, lerobot $($V.lerobot.version))"
    # sync: lock에 없는 패키지는 지워서 모든 PC를 똑같이 맞춤
    uv pip sync --python $Py $V.lock_files.robot --extra-index-url $V.torch.index_url --index-strategy unsafe-best-match
    Check "로봇 패키지 설치"
    Step "4/5 opencv 화면 출력 복구 · FFmpeg (torchcodec)"
    # lerobot이 깐 opencv-python-headless가 cv2를 덮어써 imshow가 안 되므로 GUI 빌드를 마지막에 다시 깝니다
    uv pip install --python $Py --reinstall --no-deps $V.opencv_gui; Check "opencv 복구"
    # torchcodec(LeRobot 영상 읽기)은 FFmpeg shared DLL(4~8)이 PATH에 있어야 함. conda를 안 쓰니 winget으로 설치
    if (TorchcodecOk) {
        Write-Host "torchcodec OK (FFmpeg 찾음)"
    } else {
        Write-Host "torchcodec이 FFmpeg를 못 찾아 FFmpeg $($V.ffmpeg.version) shared를 설치합니다"
        if (Has winget) {
            winget install --id $V.ffmpeg.winget_id -e --accept-source-agreements --accept-package-agreements
        }
        RefreshPath
        if (TorchcodecOk) {
            Write-Host "torchcodec OK (FFmpeg 설치됨). VS Code·터미널은 새로 열어야 PATH가 적용됩니다"
        } else {
            Write-Warning "torchcodec을 아직 못 씁니다. winget install --id $($V.ffmpeg.winget_id) 후 새 터미널에서 다시 실행하세요 (ACT 학습 전까지만 해결하면 됨)"
        }
    }
} else {
    Step "3/5 공통 패키지 ($($V.lock_files.common))"
    uv pip sync --python $Py $V.lock_files.common; Check "공통 패키지 설치"  # lock에 없는 패키지는 지움
    Step "4/5 로봇 패키지 건너뜀 (로봇 담당·시연 PC는 -Robot을 붙여 실행)"
}

Step "5/5 확인: 테스트 · mock 한 판 · 환경 점검"
& $Py -m pytest tests -q; Check "pytest"
$winner = ("6`n" * 10) | & $Py src\main.py --mock | Select-Object -Last 1
Write-Host "mock 한 판: $winner"
$checkArgs = @("scripts\check_env.py")
if ($Robot) { $checkArgs += "--robot" }
& $Py @checkArgs
$ok = $LASTEXITCODE -eq 0

Write-Host ""
if ($ok) {
    Write-Host "설치 완료. 이후에는 .venv\Scripts\activate 로 가상환경을 켜고 작업합니다." -ForegroundColor Green
} else {
    Write-Host "설치는 끝났지만 점검 표에 ❌ 항목이 있습니다. 위 표를 확인하세요." -ForegroundColor Yellow
    exit 1
}
