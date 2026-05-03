#!/usr/bin/env bash
#
# 多服务统一管理脚本
# 放在 /opt/services/manage.sh，所有服务通过此脚本管理
#
# 用法:
#   ./manage.sh list              列出所有服务及端口
#   ./manage.sh status            查看所有服务状态
#   ./manage.sh status <服务名>   查看指定服务状态
#   ./manage.sh start <服务名>    启动
#   ./manage.sh stop <服务名>     停止
#   ./manage.sh restart <服务名>  重启
#   ./manage.sh logs <服务名>     查看实时日志（Ctrl+C 退出）
#   ./manage.sh logs <服务名> 50  查看最近 50 行日志
#   ./manage.sh add <服务名> <端口> <目录>  注册新服务
#

set -euo pipefail

# ============================================================
# 服务注册表 —— 新增服务时在这里加一行
# 格式：服务名=端口=目录=描述
# ============================================================
SERVICES=(
    "procurement=10001=procurement=采购管理系统"
    # 添加更多服务示例（取消注释并修改）:
    # "wiki=10002=wiki=知识库"
    # "monitor=10003=monitor=监控面板"
)

# ============================================================
# 以下为脚本逻辑，一般不需要修改
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

parse_service() {
    local entry="$1"
    S_NAME="${entry%%=*}"
    local rest="${entry#*=}"
    S_PORT="${rest%%=*}"
    rest="${rest#*=}"
    S_DIR="${rest%%=*}"
    S_DESC="${rest#*=}"
}

find_service() {
    local target="$1"
    for entry in "${SERVICES[@]}"; do
        parse_service "$entry"
        if [ "$S_NAME" = "$target" ]; then
            return 0
        fi
    done
    return 1
}

cmd_list() {
    echo -e "${BOLD}已注册服务${NC}"
    echo ""
    printf "  %-4s %-18s %-8s %-30s %-10s\n" "序号" "服务名" "端口" "目录" "描述"
    printf "  %-4s %-18s %-8s %-30s %-10s\n" "----" "------" "----" "----" "----"
    local i=1
    for entry in "${SERVICES[@]}"; do
        parse_service "$entry"
        printf "  %-4s %-18s %-8s %-30s %-10s\n" "$i" "$S_NAME" "$S_PORT" "/opt/services/$S_DIR" "$S_DESC"
        i=$((i + 1))
    done
    echo ""
}

cmd_status() {
    local target="${1:-}"
    if [ -n "$target" ]; then
        if ! find_service "$target"; then
            echo -e "${RED}未找到服务: $target${NC}"
            exit 1
        fi
        show_one_status "$S_NAME"
        return
    fi

    echo -e "${BOLD}服务状态总览${NC}"
    echo ""
    for entry in "${SERVICES[@]}"; do
        parse_service "$entry"
        show_one_status "$S_NAME"
    done
}

show_one_status() {
    local name="$1"
    local active pid since
    active=$(systemctl show "$name" --property=ActiveState --value 2>/dev/null || echo "not-found")
    if [ "$active" = "active" ]; then
        pid=$(systemctl show "$name" --property=MainPID --value 2>/dev/null || echo "?")
        since=$(systemctl show "$name" --property=ActiveEnterTimestamp --value 2>/dev/null || echo "?")
        echo -e "  ${GREEN}● $name${NC}  运行中  PID=$pid  启动于 $since"
    elif [ "$active" = "inactive" ]; then
        echo -e "  ${RED}● $name${NC}  已停止"
    elif [ "$active" = "failed" ]; then
        echo -e "  ${RED}● $name${NC}  异常退出"
    else
        echo -e "  ${YELLOW}● $name${NC}  未注册 ($active)"
    fi
}

cmd_start() {
    local target="$1"
    require_service "$target"
    echo "启动 $S_DESC ($S_NAME)..."
    sudo systemctl start "$S_NAME"
    sleep 1
    show_one_status "$S_NAME"
}

cmd_stop() {
    local target="$1"
    require_service "$target"
    echo "停止 $S_DESC ($S_NAME)..."
    sudo systemctl stop "$S_NAME"
    sleep 1
    show_one_status "$S_NAME"
}

cmd_restart() {
    local target="$1"
    require_service "$target"
    echo "重启 $S_DESC ($S_NAME)..."
    sudo systemctl restart "$S_NAME"
    sleep 1
    show_one_status "$S_NAME"
}

cmd_logs() {
    local target="$1"
    local lines="${2:-0}"
    require_service "$target"
    if [ "$lines" -gt 0 ]; then
        sudo journalctl -u "$S_NAME" -n "$lines" --no-pager
    else
        sudo journalctl -u "$S_NAME" -f
    fi
}

cmd_add() {
    local name="$1"
    local port="$2"
    local dir="$3"
    local desc="${4:-$name}"

    # 检查是否已存在
    if find_service "$name"; then
        echo -e "${RED}服务 $name 已存在${NC}"
        exit 1
    fi

    # 检查端口是否冲突
    for entry in "${SERVICES[@]}"; do
        parse_service "$entry"
        if [ "$S_PORT" = "$port" ]; then
            echo -e "${RED}端口 $port 已被 $S_NAME 占用${NC}"
            exit 1
        fi
    done

    # 追加到注册表
    local script_path="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
    local new_entry="    \"$name=$port=$dir=$desc\""
    # 找到最后一行 SERVICES 的内容，在其后追加
    sed -i.bak "/^)/i\\$new_entry" "$script_path" && rm -f "${script_path}.bak"

    echo -e "${GREEN}服务 $name 已注册${NC}"
    echo "  端口: $port"
    echo "  目录: /opt/services/$dir"
    echo "  描述: $desc"
    echo ""
    echo "接下来你需要："
    echo "  1. 创建 systemd 服务文件: sudo vim /etc/systemd/system/$name.service"
    echo "  2. 创建 nginx 配置:       sudo vim /etc/nginx/sites-available/$name.conf"
    echo "  3. 启动服务:              ./manage.sh start $name"
}

require_service() {
    if ! find_service "$1"; then
        echo -e "${RED}未找到服务: $1${NC}"
        echo "已注册的服务:"
        for entry in "${SERVICES[@]}"; do
            parse_service "$entry"
            echo "  $S_NAME"
        done
        exit 1
    fi
}

# ============================================================
# 入口
# ============================================================

case "${1:-help}" in
    list)
        cmd_list
        ;;
    status)
        cmd_status "${2:-}"
        ;;
    start)
        [ -z "${2:-}" ] && { echo "用法: $0 start <服务名>"; exit 1; }
        cmd_start "$2"
        ;;
    stop)
        [ -z "${2:-}" ] && { echo "用法: $0 stop <服务名>"; exit 1; }
        cmd_stop "$2"
        ;;
    restart)
        [ -z "${2:-}" ] && { echo "用法: $0 restart <服务名>"; exit 1; }
        cmd_restart "$2"
        ;;
    logs)
        [ -z "${2:-}" ] && { echo "用法: $0 logs <服务名> [行数]"; exit 1; }
        cmd_logs "$2" "${3:-0}"
        ;;
    add)
        [ -z "${4:-}" ] && { echo "用法: $0 add <服务名> <端口> <目录> <描述>"; exit 1; }
        cmd_add "$2" "$3" "$4" "${5:-$2}"
        ;;
    help|*)
        echo "多服务管理工具"
        echo ""
        echo "用法: $0 <命令> [参数]"
        echo ""
        echo "命令:"
        echo "  list                    列出所有服务及端口"
        echo "  status [服务名]         查看状态（不带服务名则显示全部）"
        echo "  start <服务名>          启动"
        echo "  stop <服务名>           停止"
        echo "  restart <服务名>        重启"
        echo "  logs <服务名> [行数]    查看日志（默认实时跟踪）"
        echo "  add <名> <端口> <目录> <描述>  注册新服务"
        ;;
esac
