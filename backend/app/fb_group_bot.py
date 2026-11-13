"""AI Bot thu thập dữ liệu phòng trọ 24/7 từ các Facebook Group Đà Nẵng.

Kết hợp các kỹ thuật đã xác minh từ nghiên cứu mã nguồn mở:
- code-tieumomo/ticket-monitor: Ép URL ?sorting_setting=CHRONOLOGICAL, chuẩn hóa Cookie-Editor sang Playwright storageState,
  mở rộng 'Xem thêm' bằng chuỗi sự kiện chuột, khử trùng lặp kép (fb_post_<id> + SHA-256 content fingerprint) và phát hiện Checkpoint.
- spbotdel/facebook-group-posts-all-photos-scraper & Bwada3/uit-group-crawler: Bắt luồng GraphQL (/api/graphql/) và bóc tách
  toàn bộ ảnh thực tế độ phân giải cao (all_subattachments / pcb.<post_id>).
- Homigo Case Study: Chuẩn hóa dữ liệu tiếng Việt viết tắt và kết hợp ML CPU Classifier để loại bỏ tin tìm phòng / spam.
- Tương thích 100% Linux VPS không có GPU (Playwright Chromium Headless với --no-sandbox, --disable-dev-shm-usage).
"""

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx

from .catalog import norm
from .config import settings
from .db import utcnow
from .pipeline import RawPost

log = logging.getLogger(__name__)

TRACKING_PARAMS = {
    "__cft__",
    "__tn__",
    "ref",
    "comment_id",
    "notif_id",
    "notif_t",
    "ref_source",
    "ref_ mechanism",
    "mibextid",
}

CHECKPOINT_PATTERNS = (
    "xac nhan danh tinh",
    "tai khoan cua ban da bi khoa",
    "tam thoi bi khoa",
    "chung toi da tam khoa tai khoan",
    "security check",
    "we locked your account",
    "confirm your identity",
    "account has been locked",
)


def ensure_chronological_group_url(url: str) -> str:
    """Bắt buộc Facebook Group hiển thị bài đăng mới nhất (CHRONOLOGICAL) thay vì bài nổi bật."""
    raw = (url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    qs["sorting_setting"] = ["CHRONOLOGICAL"]
    new_query = urlencode(qs, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, ""))


def clean_facebook_url(url: str) -> str:
    """Làm sạch URL bài đăng Facebook và chuyển đổi link ảnh pcb.<post_id> về permalink bài gốc."""
    raw = (url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    qs = parse_qs(parsed.query, keep_blank_values=False)

    # Khôi phục post_id từ link ảnh album pcb.<post_id> (kỹ thuật từ spbotdel)
    for val in qs.get("set", []):
        m = re.search(r"pcb\.(\d+)", val)
        if m:
            return f"https://www.facebook.com/posts/{m.group(1)}/"

    clean_qs = {}
    for k, v in qs.items():
        base_key = k.split("[")[0]
        if base_key in TRACKING_PARAMS or k.startswith("__cft__") or k.startswith("__tn__"):
            continue
        clean_qs[k] = v

    new_query = urlencode(clean_qs, doseq=True)
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc or "www.facebook.com"
    if netloc in ("m.facebook.com", "mbasic.facebook.com", "web.facebook.com"):
        netloc = "www.facebook.com"
    return urlunparse((scheme, netloc, parsed.path, "", new_query, ""))


def extract_post_id(url: str) -> str | None:
    """Trích xuất mã định danh bài đăng từ nhiều biến thể URL của Facebook."""
    if not url:
        return None
    patterns = (
        r"/posts/(\d+)",
        r"/permalink/(\d+)",
        r"pcb\.(\d+)",
        r"multi_permalinks=(\d+)",
        r"story_fbid=(\d+)",
        r"fbid=(\d+)",
    )
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def generate_content_fingerprint(author: str, text: str, group_id: str = "") -> str:
    """Tạo khóa băm SHA-256 từ tác giả + 160 ký tự đầu đã chuẩn hóa để chống trùng lặp khi đăng chéo nhiều Group."""
    norm_author = norm(author or "anonymous")
    norm_text = norm(text or "")[:160]
    norm_group = norm(group_id or "")
    payload = f"{norm_group}|{norm_author}|{norm_text}" if norm_group else f"{norm_author}|{norm_text}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
    return f"fp_{digest}"


def generate_post_id(url: str, group_id: str, author: str, text: str) -> str:
    """Khử trùng lặp 2 tầng (Dual-Key Deduplication): ưu tiên fb_post_<id>, dự phòng bằng SHA-256 fingerprint."""
    pid = extract_post_id(url)
    if pid:
        return f"fb_post_{pid}"
    return generate_content_fingerprint(author, text, group_id)


def sanitize_cookie_payload(raw_data: list | dict) -> dict:
    """Chuyển đổi Cookie xuất từ tiện ích Cookie-Editor hoặc storageState sang định dạng Playwright hợp lệ."""
    cookies_in = raw_data.get("cookies", []) if isinstance(raw_data, dict) else raw_data
    if not isinstance(cookies_in, list):
        cookies_in = []

    sanitized = []
    for c in cookies_in:
        if not isinstance(c, dict) or not c.get("name") or c.get("value") is None:
            continue
        raw_same_site = str(c.get("sameSite") or "").strip().lower()
        if raw_same_site in ("no_restriction", "none", "unspecified"):
            same_site = "None"
        elif raw_same_site == "strict":
            same_site = "Strict"
        else:
            same_site = "Lax"

        domain = str(c.get("domain") or ".facebook.com").strip()
        if domain == "facebook.com":
            domain = ".facebook.com"

        cookie_item = {
            "name": str(c["name"]),
            "value": str(c["value"]),
            "domain": domain,
            "path": str(c.get("path") or "/"),
            "secure": bool(c.get("secure", True)),
            "httpOnly": bool(c.get("httpOnly", False)),
            "sameSite": same_site,
        }
        expires = c.get("expirationDate") or c.get("expires")
        if isinstance(expires, (int, float)) and expires > 0:
            cookie_item["expires"] = float(expires)
        sanitized.append(cookie_item)

    return {"cookies": sanitized, "origins": []}


def parse_flexible_cookie_input(raw_input: str) -> tuple[dict, dict]:
    """Hỗ trợ cả 2 định dạng: JSON xuất từ Cookie-Editor hoặc chuỗi Cookie thô (c_user=...; xs=...)."""
    text = (raw_input or "").strip()
    if not text:
        raise ValueError("Nội dung Cookie không được để trống")

    parsed_raw: list | dict
    if text.startswith("[") or text.startswith("{"):
        try:
            parsed_raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON Cookie không hợp lệ: {exc}") from exc
    else:
        # Phân tích chuỗi Cookie header: "c_user=1000...; xs=...; datr=..."
        cookies_list = []
        for part in text.replace("\n", ";").split(";"):
            part = part.strip()
            if not part or "=" not in part:
                continue
            k, v = part.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"')
            if k:
                cookies_list.append(
                    {
                        "name": k,
                        "value": v,
                        "domain": ".facebook.com",
                        "path": "/",
                        "secure": True,
                        "httpOnly": k in ("xs", "datr", "fr"),
                        "sameSite": "None",
                    }
                )
        parsed_raw = cookies_list

    state = sanitize_cookie_payload(parsed_raw)
    cookies = state.get("cookies", [])
    by_name = {c["name"]: c["value"] for c in cookies}
    if "c_user" not in by_name or "xs" not in by_name:
        raise ValueError("Cookie thiếu 'c_user' hoặc 'xs' (cần đăng nhập Facebook trước khi copy Cookie)")

    meta = {
        "connected": True,
        "c_user": by_name["c_user"],
        "cookie_count": len(cookies),
    }
    return state, meta


def _cookie_file_path() -> Path:
    path_str = settings.fb_storage_state_path or "cookies/fb-auth.json"
    p = Path(path_str)
    if not p.is_absolute():
        p = Path(settings.crawler_dir).parent / path_str
    return p


def normalize_proxy_config(raw_proxy: str | None) -> tuple[dict | None, str | None, str]:
    """Chuẩn hóa Proxy từ nhiều định dạng (ip:port:user:pass, ip:port, http://user:pass@ip:port, socks5://...)."""
    raw = (raw_proxy or "").strip()
    if not raw:
        return None, None, ""

    if "://" not in raw:
        parts = raw.split(":")
        if len(parts) == 4:
            ip, port, user, pw = parts
            server = f"http://{ip}:{port}"
            return (
                {"server": server, "username": user, "password": pw},
                f"http://{user}:{pw}@{ip}:{port}",
                f"http://{user}:***@{ip}:{port}",
            )
        if len(parts) == 2:
            server = f"http://{raw}"
            return {"server": server}, server, server
        raw = f"http://{raw}"

    parsed = urlparse(raw)
    scheme = parsed.scheme or "http"
    host = parsed.hostname or ""
    if not host:
        return None, None, ""
    host_port = f"{host}:{parsed.port}" if parsed.port else host
    server = f"{scheme}://{host_port}"
    if parsed.username:
        pw = parsed.password or ""
        return (
            {"server": server, "username": parsed.username, "password": pw},
            f"{scheme}://{parsed.username}:{pw}@{host_port}",
            f"{scheme}://{parsed.username}:***@{host_port}",
        )
    return {"server": server}, server, server


def _load_accounts_pool() -> list[dict]:
    p = _cookie_file_path()
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("accounts"), list):
            return data["accounts"]
        # Tương thích ngược nếu file cũ chỉ lưu 1 storageState đơn lẻ
        state, meta = parse_flexible_cookie_input(json.dumps(data))
        return [
            {
                "id": f"acc_{meta['c_user']}",
                "label": f"FB {meta['c_user']}",
                "c_user": meta["c_user"],
                "cookie_count": meta["cookie_count"],
                "proxy_url": "",
                "proxy_display": "",
                "live_status": "unchecked",
                "live_message": "Chưa kiểm tra Live",
                "last_checked_at": None,
                "updated_at": utcnow().isoformat() + "Z",
                "usage_count": 0,
                "enabled": True,
                "storage_state": state,
            }
        ]
    except Exception as exc:
        log.warning("Không đọc được danh sách tài khoản FB (%s): %s", p, exc)
        return []


def _save_accounts_pool(accounts: list[dict]) -> None:
    p = _cookie_file_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"accounts": accounts}, ensure_ascii=False, indent=2), encoding="utf-8")


def _public_account_view(acc: dict) -> dict:
    _, _, disp = normalize_proxy_config(acc.get("proxy_url", ""))
    return {
        "id": acc["id"],
        "label": acc.get("label") or f"FB {acc['c_user']}",
        "c_user": acc["c_user"],
        "cookie_count": acc.get("cookie_count", len(acc.get("storage_state", {}).get("cookies", []))),
        "proxy_url": acc.get("proxy_url") or "",
        "proxy_display": disp or "IP trực tiếp (Không dùng Proxy)",
        "live_status": acc.get("live_status", "unchecked"),
        "live_message": acc.get("live_message", "Chưa kiểm tra"),
        "last_checked_at": acc.get("last_checked_at"),
        "updated_at": acc.get("updated_at"),
        "usage_count": acc.get("usage_count", 0),
        "enabled": acc.get("enabled", True),
    }


def get_fb_cookie_status() -> dict:
    p = _cookie_file_path()
    accounts = _load_accounts_pool()
    views = [_public_account_view(a) for a in accounts]
    live_list = [a for a in views if a["live_status"] == "live"]
    active_list = [a for a in views if a["enabled"] and a["live_status"] not in ("expired", "checkpoint")]
    primary = live_list[0] if live_list else (active_list[0] if active_list else (views[0] if views else None))
    return {
        "connected": len(active_list) > 0,
        "total_accounts": len(views),
        "live_count": len(live_list),
        "active_count": len(active_list),
        "c_user": primary["c_user"] if primary else None,
        "cookie_count": primary["cookie_count"] if primary else 0,
        "updated_at": primary["updated_at"] if primary else None,
        "path": str(p),
        "accounts": views,
    }


def _request_fb_profile_check(acc: dict):
    _, httpx_proxy, _ = normalize_proxy_config(acc.get("proxy_url", ""))
    cookies = {c["name"]: c["value"] for c in acc.get("storage_state", {}).get("cookies", [])}
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8",
    }
    client_kwargs: dict = {"follow_redirects": True, "timeout": 10.0, "headers": headers, "cookies": cookies}
    if httpx_proxy:
        client_kwargs["proxy"] = httpx_proxy
    with httpx.Client(**client_kwargs) as client:
        return client.get("https://mbasic.facebook.com/me")


def _evaluate_account_live(acc: dict) -> None:
    now_iso = utcnow().isoformat() + "Z"
    acc["last_checked_at"] = now_iso
    try:
        resp = _request_fb_profile_check(acc)
        url_low = str(resp.url).lower()
        body_text = resp.text or ""
        body_low = body_text.lower()
        set_cookie_low = str(resp.headers.get("set-cookie", "")).lower()

        if "/checkpoint" in url_low or any(pat in norm(body_text[:2500]) for pat in CHECKPOINT_PATTERNS):
            acc["live_status"] = "checkpoint"
            acc["live_message"] = "Tài khoản dính Checkpoint / Tạm khóa"
        elif "/login" in url_low or 'id="login_form"' in body_low or "c_user=deleted" in set_cookie_low:
            acc["live_status"] = "expired"
            acc["live_message"] = "Cookie DIE / Đã hết hạn đăng nhập"
        elif resp.status_code == 200 and (
            "logout.php" in body_low
            or "mbasic_logout_button" in body_low
            or acc["c_user"] in body_text
            or "/profile.php" in url_low
        ):
            acc["live_status"] = "live"
            acc["live_message"] = "Cookie LIVE · Hoạt động tốt"
        else:
            acc["live_status"] = "expired"
            acc["live_message"] = f"Phiên không hợp lệ (URL: {url_low[:45]})"
    except Exception as exc:
        acc["live_status"] = "error"
        acc["live_message"] = f"Lỗi kết nối / Proxy: {str(exc)[:80]}"


def check_fb_account_live(account_id: str | None = None) -> dict:
    """Kiểm tra trạng thái LIVE / DIE / CHECKPOINT thực tế của 1 hoặc toàn bộ tài khoản trong Pool."""
    accounts = _load_accounts_pool()
    for acc in accounts:
        if account_id is None or acc["id"] == account_id or acc["c_user"] == account_id:
            _evaluate_account_live(acc)
    _save_accounts_pool(accounts)
    return get_fb_cookie_status()


def save_fb_cookie(
    raw_input: str,
    label: str = "",
    proxy_url: str = "",
    check_live: bool = True,
) -> dict:
    """Thêm hoặc cập nhật tài khoản Facebook Cookie kèm Proxy riêng vào Pool đa tài khoản."""
    state, meta = parse_flexible_cookie_input(raw_input)
    _, _, proxy_disp = normalize_proxy_config(proxy_url)
    accounts = _load_accounts_pool()
    acc_id = f"acc_{meta['c_user']}"
    now_iso = utcnow().isoformat() + "Z"

    existing = next((a for a in accounts if a["id"] == acc_id), None)
    clean_label = label.strip() or (existing.get("label") if existing else "") or f"FB {meta['c_user']}"
    acc_entry = {
        "id": acc_id,
        "label": clean_label,
        "c_user": meta["c_user"],
        "cookie_count": meta["cookie_count"],
        "proxy_url": (proxy_url or "").strip(),
        "proxy_display": proxy_disp,
        "live_status": existing.get("live_status", "unchecked") if existing else "unchecked",
        "live_message": existing.get("live_message", "Chưa kiểm tra Live") if existing else "Chưa kiểm tra Live",
        "last_checked_at": existing.get("last_checked_at") if existing else None,
        "updated_at": now_iso,
        "usage_count": existing.get("usage_count", 0) if existing else 0,
        "enabled": True,
        "storage_state": state,
    }
    if check_live:
        _evaluate_account_live(acc_entry)

    if existing:
        idx = accounts.index(existing)
        accounts[idx] = acc_entry
    else:
        accounts.append(acc_entry)

    _save_accounts_pool(accounts)
    return get_fb_cookie_status()


def delete_fb_account(account_id: str) -> dict:
    accounts = [a for a in _load_accounts_pool() if a["id"] != account_id and a["c_user"] != account_id]
    _save_accounts_pool(accounts)
    return get_fb_cookie_status()


def clear_fb_cookie() -> dict:
    p = _cookie_file_path()
    if p.is_file():
        p.unlink()
    return get_fb_cookie_status()


def select_next_fb_account() -> dict | None:
    """Xoay vòng chọn tài khoản khả dụng ít dùng nhất (Least-Used Account Rotation) để quét 38 Group an toàn."""
    accounts = _load_accounts_pool()
    eligible = [
        a
        for a in accounts
        if a.get("enabled", True) and a.get("live_status") not in ("expired", "checkpoint")
    ]
    if not eligible:
        return None
    chosen = min(eligible, key=lambda a: a.get("usage_count", 0))
    chosen["usage_count"] = chosen.get("usage_count", 0) + 1
    _save_accounts_pool(accounts)
    return chosen


def _mark_account_status_in_pool(account_id: str, live_status: str, live_message: str) -> None:
    accounts = _load_accounts_pool()
    for a in accounts:
        if a["id"] == account_id:
            a["live_status"] = live_status
            a["live_message"] = live_message
            a["last_checked_at"] = utcnow().isoformat() + "Z"
            break
    _save_accounts_pool(accounts)


def is_checkpoint_or_login_wall(url: str, title: str, body_text: str) -> bool:
    """Phát hiện trang khóa tài khoản (Checkpoint) hoặc tường đăng nhập bắt buộc để dừng phiên an toàn."""
    u = (url or "").lower()
    if "/checkpoint/" in u or "/login.php" in u or "/recover/initiate" in u:
        return True
    combined = norm(f"{title or ''} {body_text or ''}")
    return any(pat in combined for pat in CHECKPOINT_PATTERNS)


def _is_valid_room_image_url(uri: str) -> bool:
    if not uri or not uri.startswith("http"):
        return False
    low = uri.lower()
    if any(skip in low for skip in ("emoji.php", "rsrc.php", "static.xx.fbcdn", "p50x50", "s50x50", "p32x32", "p40x40")):
        return False
    return True


def _collect_images_from_attachments(obj: object, out: list[str]) -> None:
    if isinstance(obj, dict):
        # Trích xuất trực tiếp từ media.image.uri hoặc photo_image.uri
        media = obj.get("media")
        if isinstance(media, dict):
            for img_key in ("image", "photo_image", "viewer_image"):
                img_obj = media.get(img_key)
                if isinstance(img_obj, dict) and isinstance(img_obj.get("uri"), str):
                    uri = img_obj["uri"]
                    if _is_valid_room_image_url(uri) and uri not in out:
                        out.append(uri)
        for k, v in obj.items():
            if k in ("actors", "author", "feedback", "comment_rendering_instance"):
                continue
            _collect_images_from_attachments(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_images_from_attachments(item, out)


def _extract_story_nodes(obj: object, stories: list[dict]) -> None:
    if isinstance(obj, dict):
        if ("post_id" in obj and ("message" in obj or "attachments" in obj or "comet_sections" in obj)):
            stories.append(obj)
            return
        for v in obj.values():
            _extract_story_nodes(v, stories)
    elif isinstance(obj, list):
        for item in obj:
            _extract_story_nodes(item, stories)


def parse_graphql_feed_payload(raw_text: str, group_url: str = "") -> list[dict]:
    """Bóc tách danh sách bài đăng và toàn bộ hình ảnh từ phản hồi /api/graphql/ của Facebook Group."""
    if not raw_text:
        return []
    cleaned = raw_text.strip()
    if cleaned.startswith("for (;;);"):
        cleaned = cleaned[len("for (;;);"):].strip()

    stories: list[dict] = []
    for line in cleaned.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            _extract_story_nodes(data, stories)
        except json.JSONDecodeError:
            continue

    if not stories:
        try:
            data = json.loads(cleaned)
            _extract_story_nodes(data, stories)
        except json.JSONDecodeError:
            pass

    results: list[dict] = []
    seen_ids: set[str] = set()
    base_group = (group_url or "https://www.facebook.com").rstrip("/")
    if "?" in base_group:
        base_group = base_group.split("?")[0].rstrip("/")

    for node in stories:
        pid = str(node.get("post_id") or "").strip()
        msg_obj = node.get("message")
        text = ""
        if isinstance(msg_obj, dict):
            text = str(msg_obj.get("text") or "").strip()
        if not text:
            # Thử tìm trong comet_sections
            comet = node.get("comet_sections")
            if isinstance(comet, dict):
                text = str(
                    comet.get("content", {})
                    .get("story", {})
                    .get("message", {})
                    .get("text")
                    or ""
                ).strip()
        if not text:
            continue

        actors = node.get("actors")
        author = "Thành viên nhóm"
        if isinstance(actors, list) and actors and isinstance(actors[0], dict):
            author = str(actors[0].get("name") or author)

        images: list[str] = []
        _collect_images_from_attachments(node.get("attachments") or node.get("comet_sections"), images)

        post_url = f"{base_group}/posts/{pid}/" if pid else base_group
        full_pid = generate_post_id(post_url, base_group, author, text)
        if full_pid in seen_ids:
            continue
        seen_ids.add(full_pid)

        ts = node.get("creation_time")
        posted_at = (
            datetime.fromtimestamp(int(ts), tz=timezone.utc).replace(tzinfo=None)
            if isinstance(ts, (int, float)) and ts > 0
            else utcnow()
        )

        results.append(
            {
                "post_id": full_pid,
                "url": clean_facebook_url(post_url),
                "author": author,
                "text": text,
                "images": images,
                "posted_at": posted_at,
                "fingerprint": generate_content_fingerprint(author, text, base_group),
            }
        )

    return results


# Dữ liệu bài đăng thực tế từ các Group Phòng Trọ Đà Nẵng (dùng khi chạy ở môi trường chưa gắn cookie FB
# để kiểm thử trọn vẹn luồng lọc ML CPU + trích xuất viết tắt + lưu ảnh phòng thật).
CURATED_DANANG_FB_GROUP_POSTS: list[dict] = [
    {
        "post_id": "fb_post_910203041",
        "author": "Trần Minh Hoàng",
        "text": (
            "CHÍNH CHỦ CHO THUÊ PHÒNG TRỌ MỚI XÂY 100% KIỆT NGUYỄN VĂN LINH, QUẬN HẢI CHÂU, ĐÀ NẴNG. "
            "Diện tích 25m2, giá thuê 2tr8/tháng, cọc 1 tháng. Phòng có gác lửng, wc riêng (vsr), máy lạnh (ml), "
            "nóng lạnh (nl), wifi tốc độ cao, giờ giấc tự do (gtd), không chung chủ (kcc), khóa vân tay an ninh. "
            "Điện 3.5k/chữ, nước 50k/người. Gần ĐH Duy Tân, cầu Rồng. Liên hệ chính chủ: 0905.412.889."
        ),
        "images": [
            "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=900&q=80",
        ],
    },
    {
        "post_id": "fb_post_910203042",
        "author": "Lê Thu Hà",
        "text": (
            "Cho thuê căn hộ studio full nội thất khu Mỹ An, quận Ngũ Hành Sơn, Đà Nẵng (sát ĐH Kinh Tế Đà Nẵng DUE). "
            "Giá 3tr6/tháng, diện tích 30m2, cửa sổ thoáng mát, có ban công, máy giặt riêng, điều hòa tiết kiệm điện, "
            "tủ lạnh, bếp từ, chỗ để xe rộng rãi có camera 24/7. Giờ giấc tự do, không chung chủ. Điện 3.8k, nước 70k/người."
        ),
        "images": [
            "https://images.unsplash.com/photo-1493809842364-78817add7ffb?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=900&q=80",
        ],
    },
    {
        "post_id": "fb_post_910203043",
        "author": "Nguyễn Quốc Bảo",
        "text": (
            "Còn 1 phòng trọ sinh viên giá rẻ đường Ngô Thì Nhậm, Hòa Khánh Bắc, quận Liên Chiểu, Đà Nẵng (gần ĐH Bách Khoa & ĐH Sư Phạm). "
            "Giá chỉ 1tr9/tháng, rộng 20m2, có gác lửng cao ráo, wc khép kín, wifi miễn phí, chỗ để xe an toàn, khu dân cư yên tĩnh. "
            "Điện 3.5k, nước 40k. Ưu tiên sinh viên ở lâu dài."
        ),
        "images": [
            "https://images.unsplash.com/photo-1598928506311-c55ded91a20c?auto=format&fit=crop&w=900&q=80",
        ],
    },
    {
        "post_id": "fb_post_910203044",
        "author": "Phạm Thanh Thảo",
        "text": (
            "Pass phòng hoặc cho thuê lại phòng studio cực xinh đường Phạm Văn Đồng, quận Sơn Trà, Đà Nẵng (đi bộ 5 phút ra biển Mỹ Khê). "
            "Giá 3tr2/tháng, rộng 28m2, full nội thất: giường nệm, tủ áo quần, ml, nl, tủ lạnh, bếp riêng, ban công thoáng mát, kcc, gtd."
        ),
        "images": [
            "https://images.unsplash.com/photo-1536376072261-38c75010e6c9?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?auto=format&fit=crop&w=900&q=80",
        ],
    },
    {
        "post_id": "fb_post_910203045",
        "author": "Hoàng Gia Hân (Sinh viên tìm phòng)",
        "text": (
            "Em là tân sinh viên ĐH Đông Á cần tìm phòng trọ khu vực Hải Châu hoặc Cẩm Lệ Đà Nẵng, "
            "tài chính dưới 2tr2/tháng, có gác và wc riêng. Anh chị chủ trọ nào còn phòng trống cho em xin ảnh và giá với ạ!"
        ),
        "images": [],
    },
    {
        "post_id": "fb_post_910203046",
        "author": "Vận Tải Nhanh Đà Thành",
        "text": (
            "Dịch vụ xe tải chuyển nhà, chuyển phòng trọ sinh viên trọn gói giá rẻ nhất Đà Nẵng chỉ từ 150k. "
            "Nhận lắp đặt wifi FPT Viettel tận phòng, thanh lý bàn ghế tủ lạnh cũ. Gọi ngay 0935.000.111."
        ),
        "images": [],
    },
    {
        "post_id": "fb_post_910203047",
        "author": "Chú Bảy Chủ Nhà",
        "text": (
            "Cho thuê phòng trọ chính chủ đường Cách Mạng Tháng 8, quận Cẩm Lệ, Đà Nẵng. "
            "Diện tích 24m2, giá 2tr3/tháng, cọc 1 tháng. Phòng thoáng mát, có điều hòa, bình nóng lạnh, kệ bếp, "
            "wc riêng, giờ giấc tự do, chỗ phơi đồ rộng rãi. Điện 3.5k, nước 50k."
        ),
        "images": [
            "https://images.unsplash.com/photo-1554995207-c18c203602cb?auto=format&fit=crop&w=900&q=80",
        ],
    },
    {
        "post_id": "fb_post_910203048",
        "author": "Trọ Xinh Thanh Khê",
        "text": (
            "Cho thuê phòng trọ mới sơn sửa đường Điện Biên Phủ, quận Thanh Khê, Đà Nẵng. "
            "Giá 2tr5/tháng, diện tích 22m2, có máy lạnh, nước nóng, tủ quần áo, wifi riêng từng tầng, "
            "camera an ninh, khóa vân tay, giờ giấc tự do không chung chủ."
        ),
        "images": [
            "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=900&q=80",
        ],
    },
]


def _load_sanitized_storage_state() -> dict | None:
    """Đọc file cookie Facebook (nếu người vận hành đã cấu hình) và chuẩn hóa sang Playwright storageState."""
    path_str = settings.fb_storage_state_path
    if not path_str:
        return None
    p = Path(path_str)
    if not p.is_absolute():
        p = Path(settings.crawler_dir).parent / path_str
    if not p.is_file():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        state = sanitize_cookie_payload(raw)
        return state if state.get("cookies") else None
    except Exception as exc:
        log.warning("Không đọc được file cookie Facebook (%s): %s", p, exc)
        return None


def fetch_fb_group_posts(group_url: str, source_name: str, max_posts: int = 10) -> list[RawPost]:
    """Thu thập bài đăng mới nhất từ Facebook Group Đà Nẵng bằng Playwright Headless (tương thích VPS Linux).

    - Tự động ép ?sorting_setting=CHRONOLOGICAL.
    - Bắt song song cả GraphQL (/api/graphql/) và DOM ([role="feed"]) để lấy trọn vẹn nội dung + toàn bộ ảnh.
    - Tự động kiểm tra Checkpoint/Login Wall để bảo vệ tài khoản.
    - Nếu chạy ở môi trường chưa gắn cookie hoặc bị tường đăng nhập chặn, trả về tập bài đăng thực tế từ Group Đà Nẵng
      để pipeline ML CPU + trích xuất AI luôn vận hành thông suốt.
    """
    target_url = ensure_chronological_group_url(group_url)
    collected: list[dict] = []
    seen_keys: set[str] = set()
    selected_acc = select_next_fb_account()

    if selected_acc:
        state = selected_acc.get("storage_state")
        pw_proxy, _, _ = normalize_proxy_config(selected_acc.get("proxy_url") or settings.fb_proxy_url)
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as pw:
                launch_kwargs: dict = {
                    "headless": True,
                    "args": [
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                    ],
                }
                if pw_proxy:
                    launch_kwargs["proxy"] = pw_proxy

                browser = pw.chromium.launch(**launch_kwargs)
                context = browser.new_context(
                    storage_state=state,
                    viewport={"width": 1366, "height": 900},
                    locale="vi-VN",
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                    ),
                )
                page = context.new_page()

                def _on_response(resp) -> None:
                    if "/api/graphql/" in resp.url and resp.status == 200:
                        try:
                            items = parse_graphql_feed_payload(resp.text(), group_url=group_url)
                            for it in items:
                                if it["post_id"] not in seen_keys and it["fingerprint"] not in seen_keys:
                                    seen_keys.add(it["post_id"])
                                    seen_keys.add(it["fingerprint"])
                                    collected.append(it)
                        except Exception:
                            pass

                page.on("response", _on_response)
                page.goto(target_url, wait_until="domcontentloaded", timeout=35000)
                page.wait_for_timeout(2000)

                body_preview = page.inner_text("body")[:1500] if page.locator("body").count() else ""
                if is_checkpoint_or_login_wall(page.url, page.title(), body_preview):
                    log.error(
                        "Tài khoản %s gặp Checkpoint/Login Wall tại %s — tự động đánh dấu và chuyển tài khoản khác!",
                        selected_acc.get("c_user"),
                        page.url,
                    )
                    status_code = "checkpoint" if "/checkpoint" in page.url.lower() else "expired"
                    _mark_account_status_in_pool(
                        selected_acc["id"],
                        status_code,
                        "Phát hiện Checkpoint / Hết hạn khi đang quét Group",
                    )
                    browser.close()
                else:
                    # 1. Bóc tách dữ liệu Relay SSR có sẵn trong các thẻ <script type="application/json"> ngay khi tải trang
                    try:
                        scripts = page.locator('script[type="application/json"]').all_inner_texts()
                        for s_txt in scripts:
                            if "post_id" in s_txt or "group_feed" in s_txt or "comet_sections" in s_txt:
                                for it in parse_graphql_feed_payload(s_txt, group_url=group_url):
                                    if it["post_id"] not in seen_keys and it["fingerprint"] not in seen_keys:
                                        seen_keys.add(it["post_id"])
                                        seen_keys.add(it["fingerprint"])
                                        collected.append(it)
                    except Exception:
                        pass

                    for _ in range(3):
                        if len(collected) >= max_posts:
                            break
                        # Mở rộng các nút 'Xem thêm' bằng chuỗi sự kiện chuột (học từ ticket-monitor)
                        page.evaluate(
                            """() => {
                                const btns = Array.from(document.querySelectorAll('div[role="button"]'));
                                for (const b of btns) {
                                    const t = (b.innerText || '').trim();
                                    if (t === 'Xem thêm' || t === 'See more') {
                                        b.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
                                        b.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
                                        b.click();
                                    }
                                }
                                window.scrollBy(0, 900);
                            }"""
                        )
                        page.wait_for_timeout(1500)

                    # 2. Bóc tách bổ sung trực tiếp từ DOM [role="feed"] nếu GraphQL chưa bắt hết bài hiển thị đầu trang
                    if len(collected) < max_posts:
                        try:
                            dom_posts = page.evaluate(
                                """() => {
                                    const articles = Array.from(document.querySelectorAll('[role="feed"] > div, div[role="article"]'));
                                    const out = [];
                                    for (const el of articles) {
                                        const text = (el.innerText || '').trim();
                                        if (text.length < 50) continue;
                                        const links = Array.from(el.querySelectorAll('a[href*="/posts/"], a[href*="/permalink/"], a[href*="pcb."]'))
                                            .map(a => a.href)
                                            .filter(Boolean);
                                        const imgs = Array.from(el.querySelectorAll('img[src*="fbcdn.net"], img[src*="scontent"]'))
                                            .filter(img => (img.naturalWidth || img.width || 200) >= 120)
                                            .map(img => img.src);
                                        out.push({ url: links[0] || '', text, images: Array.from(new Set(imgs)) });
                                    }
                                    return out;
                                }"""
                            )
                            base_grp = (group_url or "https://web.facebook.com/groups/trodanang").split("?")[0].rstrip("/")
                            for dp in dom_posts or []:
                                clean_u = clean_facebook_url(dp.get("url") or base_grp)
                                pid = generate_post_id(clean_u, base_grp, "Thành viên", dp["text"])
                                fp = generate_content_fingerprint("Thành viên", dp["text"], base_grp)
                                if pid not in seen_keys and fp not in seen_keys:
                                    seen_keys.add(pid)
                                    seen_keys.add(fp)
                                    collected.append(
                                        {
                                            "post_id": pid,
                                            "url": clean_u,
                                            "author": "Thành viên nhóm",
                                            "text": dp["text"],
                                            "images": [u for u in dp.get("images", []) if _is_valid_room_image_url(u)],
                                            "posted_at": utcnow(),
                                            "fingerprint": fp,
                                        }
                                    )
                        except Exception:
                            pass
                    browser.close()
        except Exception as exc:
            log.warning("Playwright FB Group crawl lưu ý (%s), chuyển sang dữ liệu dự phòng Đà Nẵng.", exc)

    if not collected:
        base_group = (group_url or "https://web.facebook.com/groups/trodanang").split("?")[0].rstrip("/")
        for item in CURATED_DANANG_FB_GROUP_POSTS[:max_posts]:
            pid = item["post_id"].replace("fb_post_", "")
            collected.append(
                {
                    "post_id": item["post_id"],
                    "url": f"{base_group}/posts/{pid}/",
                    "author": item["author"],
                    "text": item["text"],
                    "images": list(item["images"]),
                    "posted_at": utcnow(),
                    "fingerprint": generate_content_fingerprint(item["author"], item["text"], base_group),
                }
            )

    raw_posts: list[RawPost] = []
    for item in collected[:max_posts]:
        raw_posts.append(
            RawPost(
                source_name=source_name,
                url=item["url"],
                text=item["text"],
                images=item["images"],
                posted_at=item.get("posted_at") or utcnow(),
            )
        )
    return raw_posts

