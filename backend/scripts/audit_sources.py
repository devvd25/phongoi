"""One-shot availability audit for every URL in the source registry.

This is deliberately a HEAD-only, no-redirect check. It confirms DNS/TLS/HTTP
reachability without downloading listings or bypassing a site's access rules.
"""

import asyncio
import json

import httpx

from app.source_profiles import profiles
from app.url_safety import validate_public_http_url


async def probe(client: httpx.AsyncClient, semaphore: asyncio.Semaphore, profile: dict) -> dict:
    url = profile["start_url"]
    if not url:
        return {"id": profile["id"], "status": "internal", "http_status": None}
    async with semaphore:
        try:
            safe_url = validate_public_http_url(url, resolve_dns=True)
            response = await client.head(safe_url, follow_redirects=False)
            return {
                "id": profile["id"],
                "status": "reachable" if response.status_code < 500 else "server_error",
                "http_status": response.status_code,
                "redirect": response.headers.get("location"),
            }
        except Exception as exc:
            return {"id": profile["id"], "status": "unreachable", "http_status": None, "error": type(exc).__name__}


async def main() -> None:
    semaphore = asyncio.Semaphore(8)
    headers = {"User-Agent": "PhongOiResearchBot/1.0 source-health-check"}
    async with httpx.AsyncClient(timeout=8, headers=headers) as client:
        rows = await asyncio.gather(*(probe(client, semaphore, profile) for profile in profiles()))
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
