import clsx from "clsx";
import { motion } from "framer-motion";
import {
  BarChart3, Cpu, Database, LayoutDashboard, List, LogOut, MoreHorizontal, Plus, ShieldCheck, Flag, Tags, User as UserIcon, Workflow,
  type LucideIcon,
} from "lucide-react";
import { useEffect, type ReactNode } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { Logo } from "./Brand";
import { ThemeToggle } from "./Layout";
import { NotificationBell } from "./NotificationBell";

type Item = [string, string, LucideIcon];
const LANDLORD: Item[] = [
  ["Tổng quan", "/chu-tro", LayoutDashboard],
  ["Phòng của tôi", "/chu-tro/phong", List],
  ["Đăng tin mới", "/chu-tro/dang-tin", Plus],
  ["Lượt xem & liên hệ", "/chu-tro/thong-ke", BarChart3],
  ["Hồ sơ chủ trọ", "/chu-tro/ho-so", UserIcon],
];
const ADMIN: Item[] = [
  ["Tổng quan", "/admin", LayoutDashboard],
  ["Nguồn thu thập", "/admin/nguon", Database],
  ["Pipeline dữ liệu", "/admin/pipeline", Workflow],
  ["Kiểm duyệt tin", "/admin/kiem-duyet", ShieldCheck],
  ["Báo cáo vi phạm", "/admin/bao-cao", Flag],
  ["Chi phí AI", "/admin/chi-phi-ai", Cpu],
  ["Danh mục", "/admin/danh-muc", Tags],
];
const MOBILE_LANDLORD: Item[] = [["Tổng quan", "/chu-tro", LayoutDashboard], ["Phòng", "/chu-tro/phong", List], ["Đăng tin", "/chu-tro/dang-tin", Plus], ["Thống kê", "/chu-tro/thong-ke", BarChart3], ["Hồ sơ", "/chu-tro/ho-so", UserIcon]];
const MOBILE_ADMIN: Item[] = [["Tổng quan", "/admin", LayoutDashboard], ["Nguồn", "/admin/nguon", Database], ["Kiểm duyệt", "/admin/kiem-duyet", ShieldCheck], ["Báo cáo", "/admin/bao-cao", Flag], ["Thêm", "/admin/chi-phi-ai", MoreHorizontal]];

export function DashboardLayout({ role, title, sub, right, children }: { role: "landlord" | "admin"; title: string; sub?: string; right?: ReactNode; children: ReactNode }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  const items = role === "admin" ? ADMIN : LANDLORD;
  const mobile = role === "admin" ? MOBILE_ADMIN : MOBILE_LANDLORD;
  const end = (to: string) => to === "/chu-tro" || to === "/admin";
  return (
    <div className="flex min-h-screen bg-canvas">
      <aside className="sticky top-0 hidden h-screen w-[264px] shrink-0 flex-col border-r border-line bg-surface px-4 py-6 lg:flex">
        <div className="px-2"><Logo to={role === "admin" ? "/admin" : "/chu-tro"} /></div>
        <span className="mx-2 mt-4 w-fit rounded-full bg-primary-50 px-2.5 py-1 text-[11px] font-semibold text-primary-700">{role === "admin" ? "Quản trị viên" : "Chủ trọ"}</span>
        <nav className="mt-6 flex-1 space-y-1">
          {items.map(([l, to, Icon]) => (
            <NavLink key={to} to={to} end={end(to)} className={({ isActive }) => clsx("flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition", isActive ? "bg-primary-50 text-primary-700" : "text-ink-2 hover:bg-muted hover:text-ink")}>
              <Icon className="h-5 w-5" /> {l}
            </NavLink>
          ))}
        </nav>
        <button onClick={() => (logout(), nav("/"))} className="flex items-center gap-3 rounded-md px-3 py-2.5 text-sm text-ink-2 hover:bg-muted"><LogOut className="h-5 w-5" /> Đăng xuất</button>
      </aside>
      <div className="min-w-0 flex-1">
        <header className="flex flex-wrap items-center justify-between gap-4 px-4 pb-2 pt-5 sm:px-8 sm:pt-8">
          <div>
            <h1 className="text-[24px] font-bold sm:text-h2">{title}</h1>
            {sub && <p className="text-sm text-ink-3">{sub}</p>}
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-3 sm:flex">{right}</div>
            <ThemeToggle />
            <NotificationBell />
            <span className={clsx("flex h-10 w-10 items-center justify-center rounded-full text-sm font-semibold", role === "admin" ? "bg-ink text-canvas" : "bg-accent text-white")}>{user?.initials ?? "?"}</span>
          </div>
          {right && <div className="flex w-full flex-wrap gap-3 sm:hidden">{right}</div>}
        </header>
        <motion.main initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} className="space-y-6 px-4 pb-28 pt-4 sm:px-8 lg:pb-10">
          {children}
        </motion.main>
      </div>
      <nav className="fixed inset-x-0 bottom-0 z-40 flex justify-around border-t border-line bg-surface px-2 pb-[max(env(safe-area-inset-bottom),12px)] pt-2 lg:hidden">
        {mobile.map(([l, to, Icon]) => (
          <NavLink key={to} to={to} end={end(to)} className={({ isActive }) => clsx("flex flex-col items-center gap-1 px-2 text-[11px] font-medium", isActive ? "text-primary" : "text-ink-3")}>
            <Icon className="h-[22px] w-[22px]" /> {l}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

export function Table({ head, children, widths }: { head: string[]; children: ReactNode; widths?: string[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-sm">
        <thead>
          <tr className="bg-muted text-left text-[13px] text-ink-2">
            {head.map((h, i) => (
              <th key={h + i} className={clsx("px-4 py-3 font-semibold first:rounded-l-md last:rounded-r-md", i > 0 && "text-left")} style={widths?.[i] ? { width: widths[i] } : undefined}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">{children}</tbody>
      </table>
    </div>
  );
}
