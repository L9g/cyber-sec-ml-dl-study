#!/usr/bin/env bash
# 交互写入一把 API key，自带三重守卫。
#
# 用法（必须在真实终端里跑）：
#   scripts/set-key.sh openrouter
#   scripts/set-key.sh openrouter --force    # 覆盖已有的
#
# 三重守卫，对应 2026-07-19 那次把已有 key 清空的事故：
#   ① 无 tty 直接拒绝 —— Claude Code 的 `!` 前缀没有交互式 stdin，read 会静默读到空，
#      旧写法因此「先截断、再写入空串」，把已存的 key 毁掉。
#   ② 目标已有内容则拒绝，除非显式 --force。
#   ③ 只有真读到非空输入才落盘；写入走临时文件 + mv，避免中途失败留下截断的残骸。
# 结尾打印真实字节数，不打无条件的成功回显。
set -euo pipefail

KEYDIR="${API_KEYS_DIR:-$HOME/.config/api-keys}"

die() { echo "[set-key] $*" >&2; exit 2; }

[ $# -ge 1 ] || die "用法: $0 <provider> [--force]"
provider="$1"; shift
force=0
[ "${1:-}" = "--force" ] && force=1

# ① 必须有 tty，否则 read 拿不到输入
[ -t 0 ] || die "需要交互式终端。请在普通终端窗口里跑此脚本；经 Claude Code 的 ! 前缀执行时没有 tty。"

mkdir -p "$KEYDIR"; chmod 700 "$KEYDIR"
f="$KEYDIR/$provider"

# ② 已有内容则拒绝
if [ -s "$f" ] && [ "$force" -ne 1 ]; then
  die "$f 已有内容（$(wc -c < "$f") 字节），未改动。确要覆盖请加 --force"
fi

printf '粘贴 %s 的 key（不回显），回车结束: ' "$provider" >&2
read -rs value
echo >&2

# ③ 空输入不落盘 —— 绝不截断已有文件
[ -n "$value" ] || die "没读到输入，未写入（原文件未改动）"

tmp="$(mktemp "$KEYDIR/.tmp.XXXXXX")"
chmod 600 "$tmp"
printf %s "$value" > "$tmp"
mv "$tmp" "$f"
chmod 600 "$f"

echo "[set-key] 已写入 $f — $(wc -c < "$f") 字节，权限 $(stat -c %a "$f")"
