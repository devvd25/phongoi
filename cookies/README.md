# Hướng dẫn gắn Cookie cho AI Bot Facebook Group Đà Nẵng 24/7

Đặt file `fb-auth.json` xuất từ tiện ích **Cookie-Editor** vào thư mục này (`phongoi-web/cookies/fb-auth.json`).
Hệ thống `fb_group_bot.py` sẽ tự động chuẩn hóa `sameSite` (`None` / `Lax` / `Strict`) và nạp vào Playwright Headless.

