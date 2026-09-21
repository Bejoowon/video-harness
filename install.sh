#!/usr/bin/env bash
# 영상 하네스 스킬 설치 (macOS · Linux)
#
#   curl -fsSL https://raw.githubusercontent.com/Bejoowon/video-harness/main/install.sh | bash
#
# 옵션을 주려면:  ... | bash -s -- --codex
#   --claude   Claude Code에만 설치 (~/.claude/skills)
#   --codex    Codex에만 설치 (~/.codex/skills)
#   --both     둘 다 설치
#   (옵션 없음) 이 컴퓨터에 있는 쪽을 찾아서 설치. 둘 다 없으면 Claude Code 쪽에 설치
#
# 하는 일은 저장소의 `skills/` 아래에 있는 스킬 폴더들을 복사하는 것뿐이다.
# 다른 프로그램은 설치하지 않는다. 이미 설치돼 있으면 예전 것을 지우지 않고
# skills-backup 폴더로 스킬마다 따로 옮긴 뒤 새로 넣는다.
set -euo pipefail

REPO="Bejoowon/video-harness"
BRANCH="main"

say()  { printf '%s\n' "$*"; }
fail() { printf '설치 실패: %s\n' "$*" >&2; exit 1; }

want_claude=0
want_codex=0
for arg in "$@"; do
  case "$arg" in
    --claude) want_claude=1 ;;
    --codex)  want_codex=1 ;;
    --both)   want_claude=1; want_codex=1 ;;
    -h|--help) sed -n '2,14p' "$0" 2>/dev/null || true; exit 0 ;;
    *) fail "모르는 옵션입니다: $arg  (--claude, --codex, --both 중에서 고르세요)" ;;
  esac
done

if [ "$want_claude" -eq 0 ] && [ "$want_codex" -eq 0 ]; then
  if [ -d "$HOME/.claude" ] || command -v claude >/dev/null 2>&1; then want_claude=1; fi
  if [ -d "$HOME/.codex" ]  || command -v codex  >/dev/null 2>&1; then want_codex=1; fi
  if [ "$want_claude" -eq 0 ] && [ "$want_codex" -eq 0 ]; then
    say "Claude Code와 Codex를 찾지 못해서 Claude Code 위치(~/.claude/skills)에 설치합니다."
    want_claude=1
  fi
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# VIDEO_HARNESS_SOURCE: 이미 받아 둔 저장소 폴더에서 설치할 때 쓴다(오프라인·점검용).
if [ -n "${VIDEO_HARNESS_SOURCE:-}" ]; then
  src_root="$VIDEO_HARNESS_SOURCE/skills"
else
  command -v curl >/dev/null 2>&1 || fail "curl이 없습니다."
  command -v tar  >/dev/null 2>&1 || fail "tar가 없습니다."
  say "스킬을 내려받는 중..."
  curl -fsSL "https://codeload.github.com/$REPO/tar.gz/refs/heads/$BRANCH" | tar -xz -C "$tmp" \
    || fail "내려받지 못했습니다. 인터넷 연결을 확인하고 다시 실행하세요."
  src_root="$(find "$tmp" -maxdepth 2 -type d -name skills | head -n 1)"
fi
[ -n "${src_root:-}" ] && [ -d "$src_root" ] || fail "받은 파일에서 스킬 폴더를 찾지 못했습니다."

# 설치할 스킬 = `skills/` 아래에서 SKILL.md를 가진 폴더 전부. 스킬이 늘어나도
# 이 스크립트를 고치지 않아도 되게 한다.
skills=()
for dir in "$src_root"/*/; do
  [ -f "$dir/SKILL.md" ] || continue
  skills+=("$(basename "$dir")")
done
[ "${#skills[@]}" -gt 0 ] || fail "받은 파일에서 스킬 폴더를 찾지 못했습니다."

install_to() {
  label="$1"; root="$2"
  stamp="$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$root/skills"
  for skill in "${skills[@]}"; do
    dest="$root/skills/$skill"
    if [ -e "$dest" ]; then
      backup="$root/skills-backup/$skill-$stamp"
      mkdir -p "$root/skills-backup"
      mv "$dest" "$backup"
      say "[$label] 예전 설치본을 옮겨 두었습니다: $backup"
    fi
    cp -R "$src_root/$skill" "$dest"
    find "$dest" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
    say "[$label] 설치했습니다: $dest"
  done
}

[ "$want_claude" -eq 1 ] && install_to "Claude Code" "$HOME/.claude"
[ "$want_codex"  -eq 1 ] && install_to "Codex" "$HOME/.codex"

say ""
say "설치한 스킬:"
for skill in "${skills[@]}"; do say "  - $skill"; done

say ""
say "필요한 프로그램 점검 (없는 것은 직접 설치해야 합니다. 이 스크립트는 설치하지 않습니다):"
for tool in python3 node ffmpeg git; do
  if command -v "$tool" >/dev/null 2>&1; then say "  있음  $tool"; else say "  없음  $tool"; fi
done

say ""
say "다음 순서:"
say "  1. 영상 작업에 쓸 빈 폴더를 하나 만든다."
say "  2. 그 폴더에서 Claude Code(또는 Codex)를 새로 연다. 이미 열려 있었다면 껐다 켠다."
say "  3. 하고 싶은 일에 맞게 이렇게 말한다:"
say "       영상 하네스 세팅을 시작해줘   — 작업 공간을 처음 세팅할 때"
say "       레퍼런스 찾아줘               — 참고할 영상·채널을 찾을 때"
