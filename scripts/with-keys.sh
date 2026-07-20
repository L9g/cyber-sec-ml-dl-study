#!/usr/bin/env bash
# 把 API key 注入子进程环境后 exec —— 密钥值从不出现在命令行上。
#
# 用法：
#   scripts/with-keys.sh openrouter -- .venv/bin/python scripts/run_calendar_probe.py
#   scripts/with-keys.sh openrouter,mistral -- pytest src/tests
#
# 为什么这么做（见记忆 feedback-no-clobber-verify-postcondition 与
# feedback-no-inline-secrets-in-bash）：`KEY=$(cat f) cmd` 这种写法会把明文展开到命令行，
# 于是渗进 shell history、Claude Code transcript 和 settings.local.json 权限白名单
# （2026-07-14 就这样累积了 20 条明文）。本包装器的调用行不含秘密，可安全加进白名单。
set -euo pipefail

KEYDIR="${API_KEYS_DIR:-$HOME/.config/api-keys}"

declare -A VARS=(
  [openrouter]=OPENROUTER_API_KEY
  [openai]=OPENAI_API_KEY
  [deepseek]=DEEPSEEK_API_KEY
  [mistral]=MISTRAL_API_KEY
  [gemini]=GEMINI_API_KEY
  [groq]=GROQ_API_KEY
  [together]=TOGETHER_API_KEY
  [anthropic]=ANTHROPIC_API_KEY
  [cohere]=COHERE_API_KEY
)

die() { echo "[with-keys] $*" >&2; exit 2; }

[ $# -ge 1 ] || die "用法: $0 <provider>[,<provider>...] -- <命令...>"
providers="$1"; shift
[ "${1:-}" = "--" ] && shift
[ $# -ge 1 ] || die "缺少要执行的命令（-- 之后）"

IFS=',' read -ra list <<< "$providers"
for p in "${list[@]}"; do
  var="${VARS[$p]:-}"
  [ -n "$var" ] || die "未知 provider: $p（可选: ${!VARS[*]}）"
  f="$KEYDIR/$p"
  [ -e "$f" ] || die "缺 key 文件: $f — 用 scripts/set-key.sh $p 写入"
  [ -s "$f" ] || die "key 文件为空: $f — 用 scripts/set-key.sh $p --force 重写"
  perms=$(stat -c %a "$f")
  [ "$perms" = "600" ] || echo "[with-keys] 警告: $f 权限为 $perms，应为 600" >&2
  # $(cat) 会剥掉尾部换行；值只进环境变量，不进命令行。
  export "$var=$(cat "$f")"
done

exec "$@"
