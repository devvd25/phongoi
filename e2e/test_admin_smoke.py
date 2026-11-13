"""Browser smoke tests for the highest-risk admin setup flow.

Start the API on :8000 and Vite on :5173 before running:
    python e2e/test_admin_smoke.py
"""

import os
import re
import unittest

from playwright.sync_api import Page, expect, sync_playwright


BASE_URL = os.getenv("E2E_BASE_URL", "http://127.0.0.1:5173")


def login_admin(page: Page) -> None:
    page.goto(f"{BASE_URL}/dang-nhap")
    page.get_by_label("Email").fill("admin@phongoi.vn")
    page.get_by_label("Mật khẩu").fill("Admin@2026")
    page.get_by_role("button", name="Đăng nhập").click()
    expect(page).to_have_url(re.compile(r"/admin/?$"))


class AdminSmokeTest(unittest.TestCase):
    def test_admin_can_identify_demo_data_and_start_from_a_crawler_profile(self):
        console_errors: list[str] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)

            login_admin(page)
            expect(page.get_by_role("heading", name="Tổng quan hệ thống")).to_be_visible()

            page.goto(f"{BASE_URL}/admin/nguon")
            page.get_by_label("Tìm nguồn").fill("HelpRent")
            expect(page.get_by_role("button", name=re.compile("HelpRent Da Nang API"))).to_be_visible()
            page.get_by_label("Tìm nguồn").fill("")
            page.get_by_role("button", name=re.compile("Phongtro123 Đà Nẵng")).click()
            expect(page.get_by_role("button", name="Phê duyệt pháp lý")).to_be_visible()
            page.get_by_role("button", name="Thêm nguồn").first.click()
            expect(page.get_by_role("option", name="Phongtro123 Đà Nẵng")).to_be_attached()
            browser.close()

        self.assertEqual(console_errors, [])


if __name__ == "__main__":
    unittest.main()
