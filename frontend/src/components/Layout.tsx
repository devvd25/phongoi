import clsx from "clsx";
import { Heart, House, LogOut, Moon, Search, Sparkles, Sun, User as UserIcon, SlidersHorizontal } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { useTheme } from "../lib/theme";
import { Logo } from "./Brand";
import { Button } from "./ui";
import { NotificationBell } from "./NotificationBell";

export function ThemeToggle({ className }: { className?: string }) {
  const { dark, toggle } = useTheme();
  return (
    <button onClick={toggle} aria-label={dark ? "Chuyển giao diện sáng" : "Chuyển giao diện tối"} className={clsx("focus-ring flex h-10 w-10 items-center justify-center rounded-md border border-line bg-surface text-ink-2 hover:text-ink", className)}>
      {dark ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}
    </button>
  );
}

function Avatar({ initials, className }: { initials: string; className?: string }) {
  return <span className={clsx("flex h-10 w-10 items-center justify-center rounded-full bg-primary-50 text-sm font-semibold text-primary-700", className)}>{initials}</span>;
}

function UserMenu() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const nav = useNavigate();
  useEffect(() => {
    const h = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);
  if (!user) return null;
  const items =
    user.role === "student"
      ? [["Tài khoản", "/tai-khoan"], ["Hồ sơ nhu cầu", "/ho-so-nhu-cau"], ["Tin đã lưu", "/da-luu"]]
      : user.role === "landlord"
        ? [["Trang chủ trọ", "/chu-tro"], ["Hồ sơ chủ trọ", "/chu-tro/ho-so"]]
        : [["Trang quản trị", "/admin"]];
  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen((o) => !o)} className="focus-ring rounded-full" aria-label="Mở menu tài khoản">
        <Avatar initials={user.initials} />
      </button>
      {open && (
        <div className="absolute right-0 top-12 z-50 w-56 rounded-lg border border-line bg-surface p-1.5 shadow-lg">
          <div className="px-3 py-2">
            <div className="text-sm font-semibold">{user.full_name}</div>
            <div className="caption truncate">{user.email}</div>
          </div>
          {items.map(([l, to]) => (
            <Link key={to} to={to} onClick={() => setOpen(false)} className="block rounded-md px-3 py-2 text-sm hover:bg-muted">
              {l}
            </Link>
          ))}
          <button onClick={() => (logout(), nav("/"))} className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-danger hover:bg-danger-50">
            <LogOut className="h-4 w-4" /> Đăng xuất
          </button>
        </div>
      )}
    </div>
  );
}

export function Navbar({ transparent }: { transparent?: boolean }) {
  const { user } = useAuth();
  const links = [
    ["Tìm phòng", "/tim-kiem"],
    ["Gợi ý cho bạn", "/goi-y"],
    ["Giá thị trường", "/gia-thi-truong"],
    ["Dành cho chủ trọ", user?.role === "landlord" ? "/chu-tro" : "/dang-ky?vai-tro=chu-tro"],
  ];
  return (
    <header className={clsx("sticky top-0 z-40 border-b border-line/70 backdrop-blur-xl", transparent ? "bg-surface/60" : "bg-surface/85")}>
      <div className="container-page flex h-[72px] items-center justify-between gap-6">
        <Logo />
        <nav className="hidden items-center gap-8 lg:flex">
          {links.map(([l, to]) => (
            <NavLink key={l} to={to} className={({ isActive }) => clsx("text-sm font-medium transition-colors", isActive ? "text-primary" : "text-ink-2 hover:text-ink")}>
              {l}
            </NavLink>
          ))}
        </nav>
        <div className="flex items-center gap-2 sm:gap-3">
          <ThemeToggle className="hidden sm:flex" />
          {user ? (
            <>
              <NotificationBell />
              <UserMenu />
            </>
          ) : (
            <>
              <Button variant="ghost" to="/dang-nhap" className="hidden sm:inline-flex">
                Đăng nhập
              </Button>
              <Button to="/dang-ky">Đăng ký miễn phí</Button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

export function Footer() {
  const cols: [string, [string, string][]][] = [
    ["Sinh viên", [["Tìm phòng với AI", "/tim-kiem"], ["Gợi ý cho bạn", "/goi-y"], ["Giá thị trường", "/gia-thi-truong"], ["Tin đã lưu", "/da-luu"]]],
    ["Chủ trọ", [["Đăng tin miễn phí", "/chu-tro/dang-tin"], ["Quản lý phòng", "/chu-tro/phong"], ["Hướng dẫn đăng tin", "/chu-tro"]]],
    ["Hỗ trợ", [["Báo cáo tin lừa đảo", "/tim-kiem"], ["Câu hỏi thường gặp", "/"], ["Điều khoản & quyền riêng tư", "/"]]],
  ];
  return (
    <footer className="border-t border-line bg-surface pb-24 lg:pb-0">
      <div className="container-page grid gap-10 py-12 md:grid-cols-[1.4fr_2fr]">
        <div className="space-y-4">
          <Logo variant="full" size="h-16" />
          <p className="max-w-sm text-sm leading-relaxed text-ink-2">Nền tảng tổng hợp và phân tích tin đăng phòng trọ bằng AI, giúp sinh viên Đà Nẵng tìm phòng phù hợp, an toàn và minh bạch giá.</p>
        </div>
        <div className="grid grid-cols-2 gap-8 sm:grid-cols-3">
          {cols.map(([h, ls]) => (
            <div key={h} className="space-y-3">
              <div className="text-sm font-semibold">{h}</div>
              {ls.map(([l, to]) => (
                <Link key={l} to={to} className="block text-sm text-ink-2 hover:text-primary">
                  {l}
                </Link>
              ))}
            </div>
          ))}
        </div>
      </div>
      <div className="container-page flex flex-wrap justify-between gap-2 border-t border-line py-5 text-xs text-ink-3">
        <span>© 2026 Phòng Ơi · Đề tài nghiên cứu khoa học sinh viên cấp trường</span>
        <span>Dữ liệu tổng hợp từ nguồn công khai · luôn dẫn về bài đăng gốc</span>
      </div>
    </footer>
  );
}

export function MobileTabBar() {
  const tabs: [string, string, typeof House][] = [
    ["Trang chủ", "/", House],
    ["Tìm kiếm", "/tim-kiem", Search],
    ["Gợi ý", "/goi-y", Sparkles],
    ["Đã lưu", "/da-luu", Heart],
    ["Tài khoản", "/tai-khoan", UserIcon],
  ];
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 flex justify-around border-t border-line bg-surface/95 px-2 pb-[max(env(safe-area-inset-bottom),12px)] pt-2 backdrop-blur-xl lg:hidden">
      {tabs.map(([l, to, Icon]) => (
        <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => clsx("flex flex-col items-center gap-1 px-2 text-[11px] font-medium", isActive ? "text-primary" : "text-ink-3")}>
          <Icon className="h-[22px] w-[22px]" />
          {l}
        </NavLink>
      ))}
    </nav>
  );
}

export function StudentLayout({ children, footer = true }: { children: ReactNode; footer?: boolean }) {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="flex-1 pb-24 lg:pb-0">{children}</main>
      {footer && <Footer />}
      <MobileTabBar />
    </div>
  );
}

export { Avatar, SlidersHorizontal };
