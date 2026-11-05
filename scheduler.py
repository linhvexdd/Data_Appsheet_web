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


def _hm(text: str) -> tuple[int, int]:
    hh, mm = (int(x) for x in text.split(":"))
    return hh, mm


def occurrences(s: dict, d) -> list[datetime]:
    """Các giờ chạy của lịch trong ngày d, theo tần suất:
    - "ngay" (mặc định): 1 lần lúc `gio`, vào các thứ trong `thu`
    - "lap": từ `gio` đến `den_gio`, cứ `moi` phút 1 lần, vào các thứ trong `thu`
    - "thang": 1 lần lúc `gio`, vào các ngày trong `ngay_thang` (0 = ngày cuối tháng)
    """
    try:
        hh, mm = _hm(s["gio"])
    except (KeyError, ValueError):
        return []
    start = datetime(d.year, d.month, d.day, hh, mm, tzinfo=TZ)
    kind = s.get("tan_suat") or "ngay"
    if kind == "thang":
        days = set(s.get("ngay_thang") or [1])
        last_day = (d.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        ok = d.day in days or (0 in days and d == last_day)
        return [start] if ok else []
    if d.isoweekday() not in set(s.get("thu") or [1, 2, 3, 4, 5, 6, 7]):  # 1 = Thứ Hai ... 7 = Chủ nhật
        return []
    if kind != "lap":
        return [start]
    step = max(int(s.get("moi") or 60), 30)
    try:
        eh, em = _hm(s.get("den_gio") or "23:59")
    except ValueError:
        eh, em = 23, 59
    end = datetime(d.year, d.month, d.day, eh, em, tzinfo=TZ)
    out, t = [], start
    while t <= end:
        out.append(t)
        t += timedelta(minutes=step)
    return out


def due_occurrence(s: dict, now: datetime) -> datetime | None:
    """Lần chạy gần nhất (hôm nay hoặc hôm qua) đã đến giờ nhưng chưa quá MAX_LATE.
    Lịch lặp bị trễ nhiều lượt thì chỉ chạy lượt mới nhất, không chạy bù."""
    best = None
    for back in (1, 0):
        for occ in occurrences(s, (now - timedelta(days=back)).date()):
            if occ <= now and now - occ <= MAX_LATE:
                best = occ
    return best


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
