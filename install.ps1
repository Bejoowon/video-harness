# 영상 하네스 스킬 설치 (Windows PowerShell)
#
#   irm https://raw.githubusercontent.com/Bejoowon/video-harness/main/install.ps1 | iex
#
# 설치 위치를 고르려면 실행 전에 환경 변수를 준다:
#   $env:VIDEO_HARNESS_TARGET = "claude"   # Claude Code에만 (~\.claude\skills)
#   $env:VIDEO_HARNESS_TARGET = "codex"    # Codex에만 (~\.codex\skills)
#   $env:VIDEO_HARNESS_TARGET = "both"     # 둘 다
#   (지정 안 함) 이 컴퓨터에 있는 쪽을 찾아서 설치. 둘 다 없으면 Claude Code 쪽에 설치
#
# 하는 일은 저장소의 `skills\` 아래에 있는 스킬 폴더들을 복사하는 것뿐이다.
# 다른 프로그램은 설치하지 않는다. 이미 설치돼 있으면 예전 것을 지우지 않고
# skills-backup 폴더로 스킬마다 따로 옮긴 뒤 새로 넣는다.
$ErrorActionPreference = "Stop"

$Repo = "Bejoowon/video-harness"
$Branch = "main"
$UserHome = [Environment]::GetFolderPath("UserProfile")

$target = "$env:VIDEO_HARNESS_TARGET".ToLower()
$wantClaude = $target -in @("claude", "both")
$wantCodex = $target -in @("codex", "both")
if ($target -and -not ($wantClaude -or $wantCodex)) {
    throw "VIDEO_HARNESS_TARGET 값을 알 수 없습니다: $target  (claude, codex, both 중에서 고르세요)"
}
if (-not ($wantClaude -or $wantCodex)) {
    if ((Test-Path (Join-Path $UserHome ".claude")) -or (Get-Command claude -ErrorAction SilentlyContinue)) { $wantClaude = $true }
    if ((Test-Path (Join-Path $UserHome ".codex")) -or (Get-Command codex -ErrorAction SilentlyContinue)) { $wantCodex = $true }
    if (-not ($wantClaude -or $wantCodex)) {
        Write-Host "Claude Code와 Codex를 찾지 못해서 Claude Code 위치(~\.claude\skills)에 설치합니다."
        $wantClaude = $true
    }
}

$tmp = Join-Path ([IO.Path]::GetTempPath()) ("video-harness-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tmp | Out-Null
try {
    # VIDEO_HARNESS_SOURCE: 이미 받아 둔 저장소 폴더에서 설치할 때 쓴다(오프라인·점검용).
    if ($env:VIDEO_HARNESS_SOURCE) {
        $srcRoot = Join-Path $env:VIDEO_HARNESS_SOURCE "skills"
    } else {
        Write-Host "스킬을 내려받는 중..."
        $zip = Join-Path $tmp "repo.zip"
        Invoke-WebRequest -UseBasicParsing -Uri "https://codeload.github.com/$Repo/zip/refs/heads/$Branch" -OutFile $zip
        Expand-Archive -Path $zip -DestinationPath $tmp
        $found = Get-ChildItem -Path $tmp -Directory | Where-Object { Test-Path (Join-Path $_.FullName "skills") } | Select-Object -First 1
        if (-not $found) { throw "받은 파일에서 스킬 폴더를 찾지 못했습니다." }
        $srcRoot = Join-Path $found.FullName "skills"
    }
    if (-not (Test-Path $srcRoot)) { throw "스킬 폴더를 찾지 못했습니다: $srcRoot" }

    # 설치할 스킬 = `skills\` 아래에서 SKILL.md를 가진 폴더 전부.
    $skills = @(Get-ChildItem -Path $srcRoot -Directory |
        Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } |
        Sort-Object Name)
    if ($skills.Count -eq 0) { throw "받은 파일에서 스킬 폴더를 찾지 못했습니다." }

    function Install-To([string]$Label, [string]$Root, $Skills) {
        $skillsDir = Join-Path $Root "skills"
        New-Item -ItemType Directory -Force -Path $skillsDir | Out-Null
        $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
        foreach ($skill in $Skills) {
            $dest = Join-Path $skillsDir $skill.Name
            if (Test-Path $dest) {
                $backupRoot = Join-Path $Root "skills-backup"
                New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
                $backup = Join-Path $backupRoot ($skill.Name + "-" + $stamp)
                Move-Item -Path $dest -Destination $backup
                Write-Host "[$Label] 예전 설치본을 옮겨 두었습니다: $backup"
            }
            Copy-Item -Recurse -Path $skill.FullName -Destination $dest
            Get-ChildItem -Path $dest -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
            Write-Host "[$Label] 설치했습니다: $dest"
        }
    }

    if ($wantClaude) { Install-To "Claude Code" (Join-Path $UserHome ".claude") $skills }
    if ($wantCodex) { Install-To "Codex" (Join-Path $UserHome ".codex") $skills }

    Write-Host ""
    Write-Host "설치한 스킬:"
    foreach ($skill in $skills) { Write-Host "  - $($skill.Name)" }
} finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "필요한 프로그램 점검 (없는 것은 직접 설치해야 합니다. 이 스크립트는 설치하지 않습니다):"
foreach ($tool in @("python", "node", "ffmpeg", "git")) {
    if (Get-Command $tool -ErrorAction SilentlyContinue) { Write-Host "  있음  $tool" } else { Write-Host "  없음  $tool" }
}

Write-Host ""
Write-Host "다음 순서:"
Write-Host "  1. 영상 작업에 쓸 빈 폴더를 하나 만든다."
Write-Host "  2. 그 폴더에서 Claude Code(또는 Codex)를 새로 연다. 이미 열려 있었다면 껐다 켠다."
Write-Host "  3. 하고 싶은 일에 맞게 이렇게 말한다:"
Write-Host "       영상 하네스 세팅을 시작해줘   — 작업 공간을 처음 세팅할 때"
Write-Host "       레퍼런스 찾아줘               — 참고할 영상·채널을 찾을 때"
