import { motion } from "framer-motion";
import { ArrowLeft, Check, KeyRound, Send, Sparkles } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Aurora, Logo } from "../components/Brand";
import { useCatalog } from "../components/FilterPanel";
import { ThemeToggle } from "../components/Layout";
import { Button, Checkbox, Chip, Field, IconBox, Select } from "../components/ui";
import { api } from "../lib/api";
import { homeFor, useAuth } from "../lib/auth";

const HEAD = {
  login: "Tìm phòng trọ Đà Nẵng, nhẹ đầu hơn bao giờ hết",
  register: "Tạo tài khoản, nhận gợi ý phòng hợp với bạn mỗi ngày",
  forgot: "Lấy lại quyền truy cập chỉ trong vài bước",
  reset: "Đặt mật khẩu mới, quay lại tìm phòng ngay",
};

function strength(pw: string) {
  let s = 0;
  if (pw.length >= 8) s++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) s++;
  if (/\d/.test(pw)) s++;
  if (/[^A-Za-z0-9]/.test(pw)) s++;
  return s;
}

export default function Auth({ mode }: { mode: "login" | "register" | "forgot" | "reset" }) {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const { login, register, session } = useAuth();
  const { data: cat } = useCatalog();
  const [role, setRole] = useState(params.get("vai-tro") === "chu-tro" ? "landlord" : "student");
  const [form, setForm] = useState({ full_name: "", email: "", password: "", school_id: "" });
  const [agree, setAgree] = useState(true);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState<false | { message: string; dev_reset_url?: string }>(false);
  const [confirmPw, setConfirmPw] = useState("");
  const resetToken = params.get("token") ?? "";
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));
  const st = strength(form.password);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr("");
    if (mode === "register" && !agree) return setErr("Bạn cần đồng ý với điều khoản sử dụng");
    if (mode === "reset" && form.password !== confirmPw) return setErr("Hai mật khẩu không khớp");
    setBusy(true);
    try {
      if (mode === "forgot") {
        setSent(await api("/auth/forgot", { body: { email: form.email } }));
        return;
      }
      if (mode === "reset") {
        const u = session(await api("/auth/reset", { body: { token: resetToken, password: form.password } }));
        nav(homeFor(u), { replace: true });
        return;
      }
      const u =
        mode === "login"
          ? await login(form.email, form.password)
          : await register({ full_name: form.full_name, email: form.email, password: form.password, role, school_id: form.school_id ? Number(form.school_id) : null });
      const next = params.get("next");
      nav(next || (mode === "register" && u.role === "student" ? "/ho-so-nhu-cau" : homeFor(u)), { replace: true });
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Không thể hoàn tất yêu cầu");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative isolate hidden flex-col justify-between overflow-hidden p-20 lg:flex">
        <Aurora intensity={1.1} />
        <div className="space-y-6">
          <Logo variant="full" size="h-[72px]" />
          <h1 className="max-w-lg text-display-l">{HEAD[mode]}</h1>
          <p className="max-w-md text-lg text-ink-2">Gom tin từ nhiều nguồn, AI đọc hiểu và cảnh báo lừa đảo. Bạn chỉ cần nói mình cần gì.</p>
        </div>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="w-fit -rotate-2 space-y-3 rounded-xl border border-white/60 bg-surface/80 p-5 shadow-lg backdrop-blur-xl">
          <div className="flex items-center gap-2 text-[13px] font-semibold text-violet"><Sparkles className="h-4 w-4" /> AI đã hiểu yêu cầu</div>
          <div className="flex gap-2">{["≤ 2,5 triệu", "Gần Bách khoa ĐN", "Có gác"].map((c) => <Chip key={c} state="ai">{c}</Chip>)}</div>
        </motion.div>
        <div className="flex gap-10">{[["4.860", "tin đăng tại Đà Nẵng"], ["6", "nguồn tổng hợp"], ["0đ", "phí cho sinh viên"]].map(([v, l]) => <div key={l}><div className="text-h3">{v}</div><div className="caption">{l}</div></div>)}</div>
      </div>

      <div className="flex flex-col bg-surface">
        <div className="flex items-center justify-between p-6 lg:justify-end"><Logo className="lg:hidden" /><ThemeToggle /></div>
        <motion.form onSubmit={submit} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mx-auto w-full max-w-[440px] flex-1 space-y-5 px-6 pb-12">
          {mode === "forgot" ? (
            <>
              <Link to="/dang-nhap" className="flex items-center gap-2 text-[13px] font-semibold text-primary-700"><ArrowLeft className="h-4 w-4" /> Quay lại đăng nhập</Link>
              <IconBox icon={Send} size={56} />
              <div><h1 className="text-h1">Quên mật khẩu?</h1><p className="mt-2 text-ink-2">Nhập email bạn đã đăng ký, chúng tôi sẽ gửi liên kết đặt lại mật khẩu.</p></div>
              <Field label="Email" type="email" required value={form.email} onChange={(e) => set("email", e.target.value)} autoComplete="email" />
              {err && <div role="alert" className="rounded-md bg-danger-50 px-4 py-3 text-sm text-danger">{err}</div>}
              <Button full size="l" type="submit" loading={busy}>Gửi liên kết đặt lại</Button>
              {sent && (
                <div className="flex gap-3 rounded-lg bg-success-50 p-4">
                  <Check className="h-5 w-5 shrink-0 text-success" />
                  <div className="min-w-0 space-y-1">
                    <div className="text-sm font-semibold text-success">Đã ghi nhận yêu cầu</div>
                    <div className="text-sm text-ink-2">{sent.message} Liên kết có hiệu lực trong 30 phút.</div>
                    {sent.dev_reset_url && (
                      <div className="text-sm text-ink-2">
                        Môi trường phát triển chưa cấu hình email:{" "}
                        <Link to={new URL(sent.dev_reset_url).pathname + new URL(sent.dev_reset_url).search} className="font-semibold text-primary-700 underline">mở liên kết đặt lại</Link>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          ) : mode === "reset" ? (
            <>
              <Link to="/dang-nhap" className="flex items-center gap-2 text-[13px] font-semibold text-primary-700"><ArrowLeft className="h-4 w-4" /> Quay lại đăng nhập</Link>
              <IconBox icon={KeyRound} size={56} />
              <div><h1 className="text-h1">Đặt mật khẩu mới</h1><p className="mt-2 text-ink-2">Tối thiểu 8 ký tự, nên có chữ hoa, chữ số và ký tự đặc biệt.</p></div>
              {!resetToken ? (
                <div role="alert" className="rounded-md bg-danger-50 px-4 py-3 text-sm text-danger">
                  Liên kết thiếu mã đặt lại. <Link to="/quen-mat-khau" className="font-semibold underline">Gửi lại yêu cầu</Link>
                </div>
              ) : (
                <>
                  <div className="space-y-2">
                    <Field label="Mật khẩu mới" type="password" required minLength={8} value={form.password} onChange={(e) => set("password", e.target.value)} autoComplete="new-password" />
                    {form.password && (
                      <div className="flex items-center gap-1.5">
                        {[0, 1, 2, 3].map((i) => <span key={i} className={`h-1 flex-1 rounded-full ${i < st ? (st >= 3 ? "bg-success" : "bg-warning") : "bg-muted"}`} />)}
                        <span className={`ml-2 text-xs ${st >= 3 ? "text-success" : "text-warning"}`}>{st >= 3 ? "Mạnh" : "Yếu"}</span>
                      </div>
                    )}
                  </div>
                  <Field label="Nhập lại mật khẩu mới" type="password" required minLength={8} value={confirmPw} onChange={(e) => setConfirmPw(e.target.value)} autoComplete="new-password" />
                  {err && <div role="alert" className="rounded-md bg-danger-50 px-4 py-3 text-sm text-danger">{err}</div>}
                  <Button full size="l" type="submit" loading={busy}>Lưu mật khẩu mới</Button>
                </>
              )}
            </>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-1 rounded-md bg-muted p-1">
                {[["student", "Tôi là sinh viên"], ["landlord", "Tôi là chủ trọ"]].map(([k, l]) => (
                  <button type="button" key={k} onClick={() => setRole(k)} className={`rounded-sm py-2.5 text-[13px] font-semibold ${role === k ? "bg-surface shadow-sm" : "text-ink-2"}`}>{l}</button>
                ))}
              </div>
              <div><h1 className="text-h1">{mode === "login" ? "Chào mừng trở lại" : "Tạo tài khoản miễn phí"}</h1><p className="mt-2 text-ink-2">{mode === "login" ? "Đăng nhập để lưu tin, nhận gợi ý và cảnh báo giá." : "Chỉ mất 30 giây. Không phí môi giới."}</p></div>
              {mode === "register" && <Field label="Họ và tên" required value={form.full_name} onChange={(e) => set("full_name", e.target.value)} autoComplete="name" />}
              <Field label="Email" type="email" required value={form.email} onChange={(e) => set("email", e.target.value)} autoComplete="email" />
              <div className="space-y-2">
                <Field label="Mật khẩu" type="password" required minLength={mode === "register" ? 8 : 1} value={form.password} onChange={(e) => set("password", e.target.value)} autoComplete={mode === "login" ? "current-password" : "new-password"} />
                {mode === "register" && form.password && (
                  <div className="flex items-center gap-1.5">
                    {[0, 1, 2, 3].map((i) => <span key={i} className={`h-1 flex-1 rounded-full ${i < st ? (st >= 3 ? "bg-success" : "bg-warning") : "bg-muted"}`} />)}
                    <span className={`ml-2 text-xs ${st >= 3 ? "text-success" : "text-warning"}`}>{st >= 3 ? "Mạnh" : "Yếu"}</span>
                  </div>
                )}
              </div>
              {mode === "register" && role === "student" && (
                <Select label="Trường đang học (không bắt buộc)" value={form.school_id} onChange={(e) => set("school_id", e.target.value)}>
                  <option value="">Chọn trường</option>
                  {cat?.schools.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </Select>
              )}
              {mode === "login" ? (
                <div className="flex justify-end"><Link to="/quen-mat-khau" className="text-[13px] font-semibold text-primary-700">Quên mật khẩu?</Link></div>
              ) : (
                <Checkbox checked={agree} onChange={setAgree}>Tôi đồng ý với Điều khoản sử dụng và Chính sách quyền riêng tư của Phòng Ơi</Checkbox>
              )}
              {err && <div role="alert" className="rounded-md bg-danger-50 px-4 py-3 text-sm text-danger">{err}</div>}
              <Button full size="l" type="submit" loading={busy}>{mode === "login" ? "Đăng nhập" : "Tạo tài khoản"}</Button>
              <p className="text-center text-sm text-ink-2">
                {mode === "login" ? "Chưa có tài khoản? " : "Đã có tài khoản? "}
                <Link to={mode === "login" ? "/dang-ky" : "/dang-nhap"} className="font-semibold text-primary-700">{mode === "login" ? "Đăng ký miễn phí" : "Đăng nhập"}</Link>
              </p>
            </>
          )}
        </motion.form>
      </div>
    </div>
  );
}
