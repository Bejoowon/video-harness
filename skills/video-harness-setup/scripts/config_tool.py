#!/usr/bin/env python3
"""인터뷰 답을 harness.config.json에 기록한다: init / set / add-channel / show / validate.

어느 에이전트에서 실행하든 같은 결과가 나오도록, 설정 파일을 손으로 고치는 대신
이 도구로만 쓴다. 저장 전에 항상 `harness_lib.validate_config`로 검증하고,
검증에 걸리면 파일을 건드리지 않는다.

표준 라이브러리만 사용한다 (global-constraints.md).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_lib as h

FORMATS = ["9:16", "16:9"]
KINDS = ["narration-shorts", "footage-shorts", "longform-vlog"]
STYLE_STARTS = ["reference", "preset", "manual", "later"]
CONSISTENCY_LEVELS = ["fixed", "variation", "decide-later"]
# 채널에 아직 없어도 `set`으로 새로 넣을 수 있는 선택 항목 (validate_config가 허용하는 것들).
OPTIONAL_CHANNEL_FIELDS = {"concept", "opening", "references", "style_start", "consistency"}
# 그 밖의 자리에서 아직 없어도 `set`으로 새로 넣을 수 있는 선택 항목. 키는 부모 경로
# (점으로 구분한 튜플)다. `modules.voice.model_path`는 보통 `install_module.py run`이
# 로컬 목소리 복제 모델을 내려받은 뒤 자동으로 채우지만, 이미 받아 둔 모델을 재사용할
# 때는 내려받지 않고 이 값을 직접 기록해야 한다.
OPTIONAL_FIELDS_BY_PARENT: dict[tuple[str, ...], set[str]] = {
    ("modules", "voice"): {"model_path"},
}


def _fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def _dump(data) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _load(workspace: Path) -> tuple[dict | None, str | None]:
    config = h.load_config(workspace)
    if config is None:
        return None, f"{workspace}에 harness.config.json이 없습니다. 먼저 `init`으로 만드세요."
    return config, None


def _save_if_valid(workspace: Path, config: dict) -> int | None:
    """검증을 통과할 때만 저장한다. 실패하면 오류를 찍고 1을 돌려준다(파일은 그대로).

    검증과 저장 자체는 `harness_lib.save_validated`가 한다 — 설정을 쓰는 모든 곳이
    같은 관문을 지나가게 하기 위해서다(design §7). 여기서는 사용자에게 보여 줄
    메시지만 만든다.
    """
    errors = h.save_validated(workspace, config)
    if errors:
        print("설정이 올바르지 않아 저장하지 않았습니다:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    return None


def cmd_init(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace)
    if h.load_config(workspace) is not None:
        return _fail(f"{workspace}에 harness.config.json이 이미 있습니다. 값을 바꾸려면 `set`을 쓰세요.")

    config = h.default_config()
    config["created"] = date.today().isoformat()
    config["platform"] = h.platform_info()
    config["workspace"] = {"name": args.name, "path": "."}
    if args.agents:
        config["agents"] = [a.strip() for a in args.agents.split(",") if a.strip()]

    failed = _save_if_valid(workspace, config)
    if failed:
        return failed
    _dump(config)
    return 0


def parse_value(raw: str):
    """JSON으로 읽고, JSON이 아니면 문자열 그대로 쓴다."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _list_index(target: list, part: str, key: str) -> tuple[int | None, str | None]:
    """목록 안의 항목을 가리키는 번호(0부터)를 읽는다. `channels.0.format` 같은 경로용."""
    if not part.isdigit():
        return None, f"목록에는 0부터 세는 번호를 쓴다: {key}"
    index = int(part)
    if index >= len(target):
        return None, f"{index}번 항목이 없습니다(항목 수 {len(target)}): {key}"
    return index, None


def _unknown_key_error(container: dict, part: str, key: str, extra=()) -> str:
    """오타를 잡기 위한 오류. 그 자리에 쓸 수 있는 키를 함께 보여 준다."""
    allowed = sorted(set(container) | set(extra))
    return f"'{part}'은(는) 이 자리에 없는 키입니다: {key} (쓸 수 있는 키: {', '.join(allowed)})"


def _descend(target, part: str, key: str):
    """경로의 다음 칸으로 들어간다. 없는 키와 더 내려갈 수 없는 값은 거절한다."""
    if isinstance(target, list):
        index, error = _list_index(target, part, key)
        if error:
            return None, error
        child = target[index]
    else:
        if part not in target:
            return None, _unknown_key_error(target, part, key)
        child = target[part]
    if not isinstance(child, (dict, list)):
        return None, f"'{part}'은(는) 하위 키를 가질 수 없는 값입니다: {key}"
    return child, None


def _assign(target, part: str, value, key: str, extra=()) -> str | None:
    if isinstance(target, list):
        index, error = _list_index(target, part, key)
        if error:
            return error
        target[index] = value
        return None
    if not isinstance(target, dict):
        return f"'{part}'에는 값을 둘 수 없습니다: {key}"
    if part not in target and part not in extra:
        return _unknown_key_error(target, part, key, extra)
    target[part] = value
    return None


def cmd_set(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace)
    config, error = _load(workspace)
    if error:
        return _fail(error)

    parts = args.key.split(".")
    if not args.key or "" in parts:
        return _fail(f"키 형식이 올바르지 않습니다: '{args.key}'")
    if parts[0] not in config:
        return _fail(f"알 수 없는 최상위 키입니다: '{parts[0]}' (허용: {', '.join(sorted(config))})")

    # 채널의 선택 항목은 아직 없어도 새로 넣을 수 있다 (channels.<번호>.<항목>).
    if parts[0] == "channels" and len(parts) == 3:
        extra = OPTIONAL_CHANNEL_FIELDS
    else:
        extra = OPTIONAL_FIELDS_BY_PARENT.get(tuple(parts[:-1]), set())

    target = config
    for part in parts[:-1]:
        child, error = _descend(target, part, args.key)
        if error:
            return _fail(error)
        target = child
    value = parse_value(args.value)
    old_value = target.get(parts[-1]) if isinstance(target, dict) else None
    error = _assign(target, parts[-1], value, args.key, extra)
    if error:
        return _fail(error)

    reset_note = _reset_handoff_verification(config, args.key, old_value, value)

    failed = _save_if_valid(workspace, config)
    if failed:
        return failed
    # stdout은 언제나 JSON 객체 하나다 — 안내 문장도 그 안에 담는다.
    result = {args.key: value}
    if reset_note:
        result["note"] = reset_note
    _dump(result)
    return 0


def _reset_handoff_verification(config: dict, key: str, old_value, new_value) -> str | None:
    """편집기를 바꾸면 이전 편집기로 받은 확인을 지운다.

    `status.handoff_verified_by_user`는 "이 편집기에서 실제로 열어 봤다"는 사람의
    확인이다. 편집기가 바뀌면 그 확인은 다른 앱에 대한 것이므로 더 이상 유효하지
    않다. 남겨 두면 doctor가 확인된 것처럼 읽는다.
    """
    if key != "modules.handoff.editor" or old_value == new_value:
        return None
    status = config.setdefault("status", {})
    if not status.get("handoff_verified_by_user"):
        return None
    status["handoff_verified_by_user"] = False
    return (
        f"편집기를 '{old_value}'에서 '{new_value}'로 바꿨으므로 이전 편집기에서 받은 확인"
        "(status.handoff_verified_by_user)을 지웠습니다. 새 편집기에서 다시 확인받으세요."
    )


def parse_reference(raw: str) -> dict:
    """`<url 또는 경로>::<마음에 드는 점>`을 레퍼런스 항목으로 바꾼다."""
    location, _, likes = raw.partition("::")
    return {"url": location.strip(), "likes": likes.strip(), "status": "pending"}


def _unique_id(base: str, taken: set) -> str:
    if base not in taken:
        return base
    suffix = 2
    while f"{base}-{suffix}" in taken:
        suffix += 1
    return f"{base}-{suffix}"


def cmd_add_channel(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace)
    config, error = _load(workspace)
    if error:
        return _fail(error)

    channels = config.setdefault("channels", [])
    if any(c.get("name") == args.name for c in channels):
        return _fail(f"같은 이름의 채널이 이미 있습니다: {args.name}")

    channel = {
        "id": _unique_id(h.slugify_channel(args.name), {c.get("id") for c in channels}),
        "name": args.name,
        "format": args.format,
        "kind": args.kind,
        "target_seconds": args.target_seconds,
        "language": args.language,
    }
    optional = (
        ("concept", args.concept),
        ("opening", args.opening),
        ("style_start", args.style_start),
        ("consistency", args.consistency),
    )
    for key, value in optional:
        if value:
            channel[key] = value
    if args.reference:
        channel["references"] = [parse_reference(r) for r in args.reference]

    channels.append(channel)
    failed = _save_if_valid(workspace, config)
    if failed:
        return failed
    _dump(channel)
    return 0


def cmd_remove_channel(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace)
    config, error = _load(workspace)
    if error:
        return _fail(error)

    channels = config.get("channels", [])
    target = next((c for c in channels if c.get("id") == args.channel_id), None)
    if target is None:
        known = ", ".join(c.get("id", "?") for c in channels) or "없음"
        return _fail(f"채널을 찾을 수 없습니다: {args.channel_id} (등록된 id: {known})")

    config["channels"] = [c for c in channels if c is not target]
    failed = _save_if_valid(workspace, config)
    if failed:
        return failed

    name = target.get("name", args.channel_id)
    print(
        f"채널 '{name}'({args.channel_id})을(를) 설정에서 뺐습니다. "
        f"디스크의 '{name}/' 폴더와 그 안의 파일은 하나도 지우지 않았습니다. "
        "필요 없으면 직접 지우세요."
    )
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    config, error = _load(Path(args.workspace))
    if error:
        return _fail(error)
    _dump(config)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    config, error = _load(Path(args.workspace))
    if error:
        return _fail(error)
    errors = h.validate_config(config)
    if errors:
        for item in errors:
            print(f"  - {item}", file=sys.stderr)
        return 1
    print("설정이 올바릅니다.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="harness.config.json 기록 도구")
    sub = parser.add_subparsers(dest="command", required=True)

    init_parser = sub.add_parser("init", help="기본 설정 파일을 만든다")
    init_parser.add_argument("workspace", type=Path)
    init_parser.add_argument("--name", required=True, help="작업 공간 이름")
    init_parser.add_argument("--agents", help="쉼표로 구분한 에이전트 목록 (claude,codex)")

    set_parser = sub.add_parser("set", help="점으로 구분한 키에 값을 기록한다")
    set_parser.add_argument("workspace", type=Path)
    set_parser.add_argument("key", help="예: modules.render.engine")
    set_parser.add_argument("value", help="JSON 값. JSON이 아니면 문자열로 본다")

    channel_parser = sub.add_parser("add-channel", help="채널을 추가한다")
    channel_parser.add_argument("workspace", type=Path)
    channel_parser.add_argument("--name", required=True, help="채널 이름 (폴더 이름이 된다)")
    channel_parser.add_argument("--format", required=True, choices=FORMATS)
    channel_parser.add_argument("--kind", required=True, choices=KINDS)
    channel_parser.add_argument("--target-seconds", required=True, type=int)
    channel_parser.add_argument("--language", default="ko")
    channel_parser.add_argument("--concept", help="한 줄 콘셉트")
    channel_parser.add_argument("--opening", help="고정 오프닝")
    channel_parser.add_argument("--style-start", choices=STYLE_STARTS)
    channel_parser.add_argument("--consistency", choices=CONSISTENCY_LEVELS)
    channel_parser.add_argument(
        "--reference",
        action="append",
        metavar="URL::마음에 드는 점",
        help="여러 번 줄 수 있다",
    )

    remove_parser = sub.add_parser("remove-channel", help="채널을 설정에서 뺀다 (폴더는 그대로 둔다)")
    remove_parser.add_argument("workspace", type=Path)
    remove_parser.add_argument("channel_id", help="뺄 채널의 id")

    show_parser = sub.add_parser("show", help="설정을 보여준다")
    show_parser.add_argument("workspace", type=Path)

    validate_parser = sub.add_parser("validate", help="설정을 검증한다")
    validate_parser.add_argument("workspace", type=Path)

    return parser


_COMMANDS = {
    "init": cmd_init,
    "set": cmd_set,
    "add-channel": cmd_add_channel,
    "remove-channel": cmd_remove_channel,
    "show": cmd_show,
    "validate": cmd_validate,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return _COMMANDS[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
