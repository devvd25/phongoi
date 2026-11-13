import sys
import re
import asyncio
from datetime import datetime
import httpx
from parsel import Selector

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from app.db import SessionLocal
from app.models import CrawlSource

async def test_all():
    db = SessionLocal()
    sources = db.query(CrawlSource).order_by(CrawlSource.id).all()
    print(f"Tổng cộng {len(sources)} nguồn thu thập trong hệ thống\n")
    print(f"{'ID':<4} | {'Tên nguồn':<36} | {'Loại':<15} | {'Mã HTTP':<9} | {'Đánh giá hoạt động'}")
    print("-" * 115)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    results = []

    async with httpx.AsyncClient(timeout=12, headers=headers, follow_redirects=True, verify=False) as client:
        for s in sources:
            item_info = {
                "id": s.id,
                "name": s.name,
                "kind": s.kind,
                "conn": s.connector_type,
                "url": s.start_url,
                "status": "unknown",
                "http_code": None,
                "note": ""
            }

            if not s.start_url:
                item_info["status"] = "OK_INTERNAL"
                item_info["note"] = "Nội bộ (Nhập web form/CSV)"
                results.append(item_info)
                print(f"{s.id:<4} | {s.name:<36} | {s.connector_type:<15} | {'N/A':<9} | Sẵn sàng (Nguồn nội bộ trực tiếp)")
                continue

            if s.connector_type == "rest_api" and "helprent" in s.start_url:
                try:
                    resp = await client.get(s.start_url)
                    data = resp.json()
                    total = data.get("total", 0)
                    item_info["status"] = "OK"
                    item_info["http_code"] = resp.status_code
                    item_info["note"] = f"API hoạt động tốt ({total} tin có sẵn)"
                    print(f"{s.id:<4} | {s.name:<36} | {s.connector_type:<15} | {resp.status_code:<9} | API hoạt động tốt ({total} tin)")
                except Exception as e:
                    item_info["status"] = "ERROR"
                    item_info["note"] = str(e)
                    print(f"{s.id:<4} | {s.name:<36} | {s.connector_type:<15} | {'ERROR':<9} | Lỗi API: {e}")
                results.append(item_info)
                continue

            if s.connector_type == "community_api":
                item_info["status"] = "PARTNER_API"
                item_info["note"] = "Cần Token API nhóm Facebook / Bot Telegram"
                print(f"{s.id:<4} | {s.name:<36} | {s.connector_type:<15} | {'API Tok':<9} | Cần Token API nhóm / Telegram Bot")
                results.append(item_info)
                continue

            try:
                resp = await client.get(s.start_url)
                item_info["http_code"] = resp.status_code
                
                if resp.status_code == 200:
                    html = resp.text
                    sel_parser = Selector(text=html)
                    cfg = s.config or {}
                    sel = cfg.get("item_selector", "")
                    elements = []
                    if sel and not sel.startswith("__"):
                        elements = sel_parser.css(sel).getall()
                    
                    if len(elements) > 0:
                        item_info["status"] = "OK"
                        item_info["note"] = f"Khớp {len(elements)} phần tử tin đăng theo selector"
                        print(f"{s.id:<4} | {s.name:<36} | {s.connector_type:<15} | 200 OK   | Hoạt động tốt (Khớp {len(elements)} tin)")
                    else:
                        item_info["status"] = "OK_NEED_SELECTOR"
                        item_info["note"] = "Web truy cập được 200 OK nhưng selector mặc định chưa khớp HTML động"
                        print(f"{s.id:<4} | {s.name:<36} | {s.connector_type:<15} | 200 OK   | Kết nối thành công (Cần tinh chỉnh selector)")
                elif resp.status_code == 403:
                    item_info["status"] = "BLOCKED_WAF"
                    item_info["note"] = "Bị chặn bởi Cloudflare / WAF Anti-bot của sàn"
                    print(f"{s.id:<4} | {s.name:<36} | {s.connector_type:<15} | 403 Block | Bị chặn bởi Cloudflare/WAF của sàn")
                elif resp.status_code in (301, 302, 308):
                    item_info["status"] = "REDIRECT"
                    item_info["note"] = f"Chuyển hướng -> {resp.headers.get('Location')}"
                    print(f"{s.id:<4} | {s.name:<36} | {s.connector_type:<15} | {resp.status_code} Redir | Chuyển hướng URL")
                else:
                    item_info["status"] = f"HTTP_{resp.status_code}"
                    item_info["note"] = f"HTTP {resp.status_code}"
                    print(f"{s.id:<4} | {s.name:<36} | {s.connector_type:<15} | {resp.status_code:<9} | Mã phản hồi khác")
            except Exception as e:
                item_info["status"] = "TIMEOUT_OR_ERR"
                item_info["note"] = f"{type(e).__name__}: {str(e)[:40]}"
                print(f"{s.id:<4} | {s.name:<36} | {s.connector_type:<15} | ERROR     | {type(e).__name__}")
            
            results.append(item_info)

    db.close()
    return results

if __name__ == "__main__":
    asyncio.run(test_all())
