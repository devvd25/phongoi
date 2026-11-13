import { useMutation, useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { ArrowRight, Bell, Database, LogOut, ShieldCheck, SlidersHorizontal, User as UserIcon, type LucideIcon } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCatalog } from "../components/FilterPanel";
import { StudentLayout } from "../components/Layout";
import { Badge, Button, Card, Chip, Field, Select, Toggle, useToast } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { User } from "../lib/types";

type NeedsSummary = { chips: string[] };
type MenuItem = [LucideIcon, string, string];
type PrivacyItem = [string, string, boolean, (value: boolean) => void];

export default function Account() {
  const { user, setUser, logout } = useAuth();
  const toast = useToast();
  const nav = useNavigate();
  const { data: cat } = useCatalog();
  const { data: needs } = useQuery<NeedsSummary | null>({ queryKey: ["needs"], queryFn: () => api("/me/needs"), enabled: user?.role === "student" });
  const [form, setForm] = useState({ full_name: user!.full_name, phone: user!.phone ?? "", school_id: user!.school_id ?? "", personalize: user!.personalize });
  const [survey, setSurvey] = useState(false);
  const save = useMutation({
    mutationFn: () => api<User>("/me/profile", { method: "PUT", body: { ...form, school_id: form.school_id ? Number(form.school_id) : null, phone: form.phone || null } }),
    onSuccess: (u: User) => (setUser(u), toast("Đã lưu thay đổi")),
  });
  const [pwOpen, setPwOpen] = useState(false);
  const [pw, setPw] = useState({ current: "", next: "", confirm: "" });
  const changePw = useMutation({
    mutationFn: () => api("/me/password", { method: "PUT", body: { current_password: pw.current, new_password: pw.next } }),
    onSuccess: () => (toast("Đã đổi mật khẩu"), setPw({ current: "", next: "", confirm: "" }), setPwOpen(false)),
    onError: (e: Error) => toast(e.message, "danger"),
  });
  const del = useMutation({ mutationFn: () => api("/me", { method: "DELETE" }), onSuccess: () => (logout(), nav("/")) });
  const exportData = async () => {
    const data = await api("/me/export");
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
    Object.assign(document.createElement("a"), { href: url, download: "du-lieu-phong-oi.json" }).click();
  };
  const menu: MenuItem[] = [[UserIcon, "Hồ sơ cá nhân", "#ho-so"], [SlidersHorizontal, "Hồ sơ nhu cầu", "#nhu-cau"], [Bell, "Thông báo", "/da-luu"], [ShieldCheck, "Bảo mật", "#bao-mat"], [Database, "Quyền riêng tư và dữ liệu", "#rieng-tu"]];

  return (
    <StudentLayout>
      <div className="container-page grid gap-8 py-10 lg:grid-cols-[280px_1fr]">
        <Card pad="p-3" className="h-fit space-y-1 lg:sticky lg:top-24">
          {menu.map(([Icon, l, h], i) => (
            <a key={l} href={h} onClick={(e) => h.startsWith("/") && (e.preventDefault(), nav(h))} className={clsx("flex items-center gap-3 rounded-md px-4 py-3 text-[15px]", i === 0 ? "bg-primary-50 font-semibold text-primary-700" : "hover:bg-muted")}>
              <Icon className="h-5 w-5" /> {l}
            </a>
          ))}
          <div className="my-1 h-px bg-line" />
          <button onClick={() => (logout(), nav("/"))} className="flex w-full items-center gap-3 rounded-md px-4 py-3 text-[15px] text-danger hover:bg-danger-50"><LogOut className="h-5 w-5" /> Đăng xuất</button>
        </Card>
        <div className="space-y-6">
          <h1 className="text-h1">Tài khoản của bạn</h1>
          <Card id="ho-so" className="space-y-5">
            <div className="flex flex-wrap items-center gap-5">
              <span className="flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-[#FB923C] to-[#C2410C] text-h2 text-white">{user!.initials}</span>
              <div className="flex-1 space-y-1.5">
                <div className="text-h3">{user!.full_name}</div>
                <div className="text-sm text-ink-3">{user!.email} · tham gia {new Date(user!.created_at).toLocaleDateString("vi-VN", { month: "2-digit", year: "numeric" })}</div>
                <div className="flex gap-2"><Badge tone="Success" dot>Đã xác minh email</Badge><Badge>{user!.role === "student" ? "Sinh viên" : user!.role === "landlord" ? "Chủ trọ" : "Quản trị"}</Badge></div>
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Họ và tên" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
              <Field label="Email" value={user!.email} disabled />
              <Field label="Số điện thoại (không bắt buộc)" value={form.phone} placeholder="Chưa thêm" onChange={(e) => setForm({ ...form, phone: e.target.value })} />
              <Select label="Trường đang học" value={form.school_id} onChange={(e) => setForm({ ...form, school_id: e.target.value })}>
                <option value="">Chưa chọn</option>
                {cat?.schools.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </Select>
            </div>
            <div className="flex justify-end"><Button loading={save.isPending} onClick={() => save.mutate()}>Lưu thay đổi</Button></div>
          </Card>
          {user!.role === "student" && (
            <Card id="nhu-cau" className="space-y-4">
              <div className="flex items-center justify-between"><h2 className="text-h4">Hồ sơ nhu cầu</h2><Button variant="ghost" to="/ho-so-nhu-cau" iconRight={<ArrowRight className="h-4 w-4" />}>Chỉnh sửa</Button></div>
              <div className="flex flex-wrap gap-2">{needs ? needs.chips.map((c: string) => <Chip key={c} state="ai">{c}</Chip>) : <span className="text-sm text-ink-3">Chưa có hồ sơ nhu cầu.</span>}</div>
            </Card>
          )}
          <Card id="bao-mat" pad="px-6 pt-6 pb-2">
            <h2 className="text-h4">Bảo mật</h2>
            <div className="mt-3 flex items-center justify-between border-t border-line py-4">
              <div><div className="text-sm font-semibold">Mật khẩu</div><div className="text-sm text-ink-3">Nên đổi định kỳ và không dùng lại ở trang khác</div></div>
              <Button variant="secondary" onClick={() => setPwOpen((o) => !o)}>{pwOpen ? "Đóng" : "Đổi mật khẩu"}</Button>
            </div>
            {pwOpen && (
              <form onSubmit={(e) => (e.preventDefault(), changePw.mutate())} className="grid gap-4 border-t border-line py-4 sm:grid-cols-3">
                <Field label="Mật khẩu hiện tại" type="password" required value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} autoComplete="current-password" />
                <Field label="Mật khẩu mới" type="password" required minLength={8} value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} autoComplete="new-password" />
                <Field label="Nhập lại mật khẩu mới" type="password" required minLength={8} value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} autoComplete="new-password"
                  error={pw.confirm && pw.confirm !== pw.next ? "Hai mật khẩu không khớp" : undefined} />
                <div className="flex flex-wrap items-center justify-between gap-3 sm:col-span-3">
                  <a href="/quen-mat-khau" onClick={(e) => (e.preventDefault(), nav("/quen-mat-khau"))} className="text-[13px] font-semibold text-primary-700">Quên mật khẩu hiện tại?</a>
                  <Button type="submit" loading={changePw.isPending} disabled={!pw.current || pw.next.length < 8 || pw.next !== pw.confirm}>Cập nhật mật khẩu</Button>
                </div>
              </form>
            )}
          </Card>
          <Card id="rieng-tu" pad="px-6 pt-6 pb-4">
            <h2 className="text-h4">Quyền riêng tư và dữ liệu</h2>
            {([
              ["Dùng lịch sử xem để cá nhân hóa gợi ý", "Giúp AI gợi ý sát nhu cầu hơn. Bạn có thể tắt bất cứ lúc nào.", form.personalize, (v: boolean) => setForm({ ...form, personalize: v })],
              ["Nhận email khảo sát phục vụ nghiên cứu", "Nhóm nghiên cứu có thể mời bạn đánh giá chất lượng gợi ý.", survey, setSurvey],
            ] satisfies PrivacyItem[]).map(([t, d, v, f]) => (
              <div key={t} className="mt-3 flex items-center gap-4 border-t border-line pt-4">
                <div className="flex-1"><div className="text-sm font-semibold">{t}</div><div className="text-sm text-ink-3">{d}</div></div>
                <Toggle checked={v} onChange={f} label={t} />
              </div>
            ))}
            <div className="mt-4 flex gap-3 border-t border-line pt-4">
              <Button variant="secondary" onClick={exportData}>Tải dữ liệu của tôi</Button>
              <Button variant="danger" loading={del.isPending} onClick={() => confirm("Xóa vĩnh viễn tài khoản và toàn bộ dữ liệu của bạn?") && del.mutate()}>Xóa tài khoản</Button>
            </div>
          </Card>
        </div>
      </div>
    </StudentLayout>
  );
}
