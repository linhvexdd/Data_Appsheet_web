"""Bộ hẹn giờ: đọc schedules.json, đến giờ thì gọi workflow tải data ở repo đích.

Không lưu trạng thái riêng: mỗi lần gọi đặt tên lượt chạy là "Lịch <id> <ngày giờ>",
lần sau kiểm tra danh sách lượt chạy để không gọi trùng.
Chạy bằng thư viện chuẩn của Python, không cần cài thêm gì.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Ho_Chi_Minh")
API = "https://api.github.com"
# Cron của GitHub có thể trễ; lịch trễ quá khoảng này thì bỏ qua thay vì chạy bù
MAX_LATE = timedelta(hours=3)


def gh(method: str, path: str, token: str, body: dict | None = None):
    req = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def due_occurrence(s: dict, now: datetime) -> datetime | None:
    """Lần chạy gần nhất (hôm nay hoặc hôm qua) đã đến giờ nhưng chưa quá MAX_LATE."""
    try:
        hh, mm = (int(x) for x in s["gio"].split(":"))
    except (KeyError, ValueError):
        return None
    days = set(s.get("thu") or [1, 2, 3, 4, 5, 6, 7])  # 1 = Thứ Hai ... 7 = Chủ nhật
    for back in (0, 1):
        d = (now - timedelta(days=back)).date()
        occ = datetime(d.year, d.month, d.day, hh, mm, tzinfo=TZ)
        if d.isoweekday() in days and occ <= now and now - occ <= MAX_LATE:
            return occ
    return None


def main() -> int:
    token = os.environ["DISPATCH_TOKEN"]
    target = os.environ["TARGET_REPO"]
    workflow = os.environ.get("TARGET_WORKFLOW", "tai-data-appsheet.yml")
    ref = os.environ.get("TARGET_REF", "main")
    schedules = json.loads(Path(os.environ.get("SCHEDULES_FILE", "schedules.json")).read_text(encoding="utf-8"))
    now = datetime.now(TZ)

    due = []
    for s in schedules.get("lich", []):
        if not s.get("bat", True):
            continue
        occ = due_occurrence(s, now)
        if occ:
            due.append((s, f"Lịch {s['id']} {occ:%Y-%m-%d %H:%M}"))
    if not due:
        print(f"{now:%Y-%m-%d %H:%M} - không có lịch nào đến giờ.")
        return 0

    runs = gh("GET", f"/repos/{target}/actions/workflows/{workflow}/runs?per_page=100", token)
    done = {r.get("display_title", "") for r in runs.get("workflow_runs", [])}
    for s, title in due:
        if title in done:
            print(f"Đã chạy rồi: {title}")
            continue
        inputs = {
            "che_do": s.get("che_do", "all"),
            "tu_ngay": s.get("tu_ngay", ""),
            "den_ngay": s.get("den_ngay", ""),
            "cot": s.get("cot", ""),
            "gia_tri": s.get("gia_tri", ""),
            "nguon": title,
        }
        gh("POST", f"/repos/{target}/actions/workflows/{workflow}/dispatches", token, {"ref": ref, "inputs": inputs})
        print(f"Đã gọi: {title} ({s.get('ten', '')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
