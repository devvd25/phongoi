import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle, Bell, CheckCircle2, Clock, Cpu, EyeOff, Lightbulb, Phone, ShieldAlert, Sparkles, TrendingDown, type LucideIcon,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { timeAgo } from "../lib/format";
import { IconBox, Spinner, useToast } from "./ui";

type Noti = { id: number; kind: string; text: string; link: string | null; read: boolean; created_at: string };
type BoxTone = "primary" | "success" | "warning" | "danger" | "violet" | "accent" | "muted";

export const NOTI_ICON: Record<string, [LucideIcon, BoxTone]> = {
  match: [Bell, "primary"],
  price_drop: [TrendingDown, "success"],
  report: [ShieldAlert, "danger"],
  daily: [Sparkles, "violet"],
  contact: [Phone, "accent"],
  pending: [Clock, "primary"],
  approved: [CheckCircle2, "success"],
  hidden: [EyeOff, "danger"],
  price_tip: [Lightbulb, "warning"],
  source_error: [AlertTriangle, "danger"],
  budget: [Cpu, "violet"],
};

export function NotiRow({ n, onClick }: { n: Noti; onClick?: () => void }) {
  const [Icon, tone] = NOTI_ICON[n.kind] ?? NOTI_ICON.match;
  return (
    <button type="button" onClick={onClick} className={clsx("flex w-full gap-3 rounded-md p-3 text-left transition hover:bg-muted", !n.read && "bg-primary-50/60")}>
      <IconBox icon={Icon} tone={tone} size={36} />
      <div className="min-w-0 flex-1">
        <div className={clsx("text-sm", !n.read && "font-semibold")}>{n.text}</div>
        <div className="caption">{timeAgo(n.created_at)}</div>
      </div>
      {!n.read && <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-primary" />}
    </button>
  );
}

/** Danh sách thông báo + đánh dấu đã đọc, dùng chung cho chuông và trang Tin đã lưu. */
export function useNotifications(enabled = true) {
  const qc = useQueryClient();
  const nav = useNavigate();
  const list = useQuery<Noti[]>({ queryKey: ["notis"], queryFn: () => api("/me/notifications"), enabled });
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["notis"] });
    qc.invalidateQueries({ queryKey: ["notis-unread"] });
  };
  const read = useMutation({ mutationFn: (id?: number) => api("/me/notifications/read", { body: id ? { id } : {} }), onSuccess: refresh });
  const open = (n: Noti) => {
    if (!n.read) read.mutate(n.id);
    if (n.link) nav(n.link);
  };
  return { list, readAll: () => read.mutate(undefined), open };
}

/** Cài đặt nhận thông báo, lưu lên máy chủ theo từng tài khoản. */
export function useNotificationPrefs() {
  const qc = useQueryClient();
  const toast = useToast();
  const q = useQuery<Record<string, boolean>>({ queryKey: ["noti-prefs"], queryFn: () => api("/me/notification-prefs") });
  const m = useMutation({
    mutationFn: (patch: Record<string, boolean>) => api<Record<string, boolean>>("/me/notification-prefs", { method: "PUT", body: patch }),
    onMutate: (patch) => {
      qc.setQueryData<Record<string, boolean>>(["noti-prefs"], (old) => ({ ...old, ...patch }));
    },
    onSuccess: (data) => (qc.setQueryData(["noti-prefs"], data), toast("Đã lưu cài đặt thông báo")),
    onError: () => (qc.invalidateQueries({ queryKey: ["noti-prefs"] }), toast("Không lưu được cài đặt, thử lại sau", "danger")),
  });
  return { prefs: q.data, set: (key: string, value: boolean) => m.mutate({ [key]: value }) };
}

export function NotificationBell({ className }: { className?: string }) {
  const { user } = useAuth();
  const [pos, setPos] = useState<{ top: number; left: number; width: number } | null>(null);
  const open = !!pos;
  const setOpen = (v: boolean) => (v ? place() : setPos(null));
  const btn = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  // Đặt bảng theo vị trí nút chuông nhưng luôn nằm gọn trong màn hình (header có thể xuống dòng trên điện thoại).
  const place = () => {
    const r = btn.current!.getBoundingClientRect();
    const width = Math.min(380, window.innerWidth - 32);
    setPos({ top: r.bottom + 8, left: Math.min(Math.max(16, r.right - width), window.innerWidth - width - 16), width });
  };
  const { data: unread } = useQuery<{ count: number }>({ queryKey: ["notis-unread"], queryFn: () => api("/me/notifications/unread"), refetchInterval: 60_000, enabled: !!user });
  const { list, readAll, open: openNoti } = useNotifications(open);
  const nav = useNavigate();

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      const t = e.target as Node;
      if (!btn.current?.contains(t) && !panel.current?.contains(t)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    const onResize = () => setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    window.addEventListener("resize", onResize);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", onResize);
    };
  }, [open]);

  if (!user) return null;
  const count = unread?.count ?? 0;
  const settings = user.role === "student" ? "/da-luu" : user.role === "landlord" ? "/chu-tro/ho-so" : null;

  return (
    <div className={clsx("relative", className)}>
      <button
        ref={btn}
        type="button"
        aria-label={count ? `Thông báo, ${count} chưa đọc` : "Thông báo"}
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="focus-ring relative flex h-10 w-10 items-center justify-center rounded-md border border-line bg-surface text-ink-2 hover:text-ink"
      >
        <Bell className="h-[18px] w-[18px]" />
        {count > 0 && (
          <span className="absolute -right-1.5 -top-1.5 flex h-5 min-w-[20px] items-center justify-center rounded-full bg-primary px-1 text-[11px] font-bold text-white">
            {count > 9 ? "9+" : count}
          </span>
        )}
      </button>
      {createPortal(
        <AnimatePresence>
          {pos && (
            <motion.div
              ref={panel}
              role="dialog"
              aria-label="Thông báo"
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.15 }}
              style={pos}
              className="fixed z-50 rounded-xl border border-line bg-surface p-3 shadow-lg"
            >
              <div className="flex items-center justify-between px-2 pb-2">
                <span className="text-h4">Thông báo</span>
                {count > 0 && <button onClick={readAll} className="text-[13px] font-semibold text-primary-700">Đánh dấu đã đọc</button>}
              </div>
              <div className="max-h-[420px] space-y-1 overflow-y-auto">
                {list.isLoading ? <Spinner /> : list.data?.length ? (
                  list.data.map((n) => <NotiRow key={n.id} n={n} onClick={() => (openNoti(n), setOpen(false))} />)
                ) : (
                  <p className="px-2 py-8 text-center text-sm text-ink-3">Chưa có thông báo nào</p>
                )}
              </div>
              {settings && (
                <button onClick={() => (nav(settings), setOpen(false))} className="mt-2 w-full rounded-md border-t border-line pt-3 text-center text-[13px] font-semibold text-primary-700">
                  Cài đặt nhận thông báo
                </button>
              )}
            </motion.div>
          )}
        </AnimatePresence>,
        document.body,
      )}
    </div>
  );
}
