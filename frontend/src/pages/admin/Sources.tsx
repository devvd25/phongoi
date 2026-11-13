import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import { Globe, Play, Plus, RefreshCw, Save, ShieldCheck, Sparkles, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Dialog } from "../../components/Dialog";
import { DashboardLayout, Table } from "../../components/Dashboard";
import { Badge, Button, Card, Checkbox, Field, IconBox, Select, Spinner, TextArea, Toggle, useToast, type Tone } from "../../components/ui";
import { api } from "../../lib/api";
import { timeAgo } from "../../lib/format";
import { isFbGroupSource, SRC_STATUS } from "./Overview";

const KIND: Record<string, string> = { scrapy: "Scrapy · trang HTML tĩnh", playwright: "Playwright · trang động", internal: "Tin chính chủ trên hệ thống", sample: "Bộ tin mẫu cục bộ", manual: "Nhập thủ công" };
const RUN: Record<string, [string, Tone]> = { success: ["Thành công", "Success"], partial: ["Lỗi một phần", "Warning"], error: ["Lỗi", "Danger"], running: ["Đang chạy", "Info"] };
const SELECTORS: [SelectorKey, string, string][] = [
  ["item_selector", "Selector từng tin đăng", "VD: .listing-item"],
  ["link_selector", "Selector liên kết chi tiết", "a::attr(href)"],
  ["text_selector", "Selector nội dung tin", "::text"],
  ["image_selector", "Selector ảnh", "img::attr(src)"],
  ["next_selector", "Selector trang kế tiếp", "a[rel=next]::attr(href)"],
];
const crawlable = (kind: string) => kind === "scrapy" || kind === "playwright";

type CrawlerKind = "scrapy" | "playwright" | "manual" | "internal" | "sample";
type Cfg = {
  item_selector?: string;
  link_selector?: string;
  text_selector?: string;
  image_selector?: string;
  next_selector?: string;
  terms_checked?: boolean;
};
type SelectorKey = Exclude<keyof Cfg, "terms_checked">;
type SourceRun = { id: number; started_at: string; status: string; new: number; dup: number; errors: number; duration_s: number | null; message?: string };
type Source = {
  id: number;
  name: string;
  kind: CrawlerKind;
  source_group?: "website" | "fb_group";
  start_url: string;
  frequency_minutes: number;
  rate_limit: string;
  max_pages: number;
  config: Cfg;
  removable: boolean;
  enabled: boolean;
  status: string;
  last_run_at: string | null;
  runs: SourceRun[];
  profile_id?: string | null;
  connector_type?: string;
  integration_status?: "ready" | "legal_review" | "partner_required";
  health_score?: number;
  consecutive_failures?: number;
  terms_url?: string | null;
  robots_url?: string | null;
  approval_notes?: string | null;
  approved_at?: string | null;
};
type SourceProfile = Pick<Source, "name" | "kind" | "start_url" | "config" | "connector_type" | "integration_status"> & { id: string };
type SourceDraft = Pick<Source, "name" | "kind" | "start_url" | "frequency_minutes" | "max_pages" | "config" | "connector_type" | "integration_status"> & { profile_id?: string };
type SourceEdit = Pick<Source, "start_url" | "frequency_minutes" | "max_pages" | "enabled" | "config">;
type RunResponse = { result?: { status: string; new: number; dup: number; errors: number } };
type FbAccountItem = {
  id: string;
  label: string;
  c_user: string;
  cookie_count: number;
  proxy_url: string;
  proxy_display: string;
  live_status: "live" | "expired" | "checkpoint" | "error" | "unchecked";
  live_message: string;
  last_checked_at: string | null;
  updated_at: string | null;
  usage_count: number;
  enabled: boolean;
};
type FbCookieStatus = {
  connected: boolean;
  total_accounts: number;
  live_count: number;
  active_count: number;
  c_user: string | null;
  cookie_count: number;
  updated_at: string | null;
  path: string;
  accounts: FbAccountItem[];
};
const LIVE_BADGE: Record<FbAccountItem["live_status"], [string, Tone]> = {
  live: ["LIVE · Hoạt động", "Success"],
  expired: ["DIE · Hết hạn", "Danger"],
  checkpoint: ["CHECKPOINT · Khóa", "Warning"],
  error: ["Lỗi Proxy / Mạng", "Warning"],
  unchecked: ["Chưa Check Live", "Neutral"],
};

const messageOf = (error: Error) => error.message;

function SelectorFields({ cfg, onChange }: { cfg: Cfg; onChange: (c: Cfg) => void }) {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        {SELECTORS.map(([k, l, ph]) => (
          <Field key={k} label={l} placeholder={ph} value={cfg[k] ?? ""} onChange={(e) => onChange({ ...cfg, [k]: e.target.value })} />
        ))}
      </div>
      <Checkbox checked={!!cfg.terms_checked} onChange={(v) => onChange({ ...cfg, terms_checked: v })}>
        Tôi đã đọc điều khoản sử dụng và robots.txt của trang, trang cho phép thu thập phần dữ liệu này
      </Checkbox>
    </div>
  );
}

const emptyDraft = (): SourceDraft => ({ name: "", kind: "scrapy", start_url: "", frequency_minutes: 60, max_pages: 3, config: {}, connector_type: "html_static", integration_status: "legal_review" });

function AddSourceDialog({ open, onClose, onCreated, defaultFb }: { open: boolean; onClose: () => void; onCreated: (id: number) => void; defaultFb?: boolean }) {
  const toast = useToast();
  const { data: profiles = [] } = useQuery<SourceProfile[]>({ queryKey: ["source-profiles"], queryFn: () => api("/admin/source-profiles"), staleTime: Infinity });
  const [f, setF] = useState<SourceDraft>(emptyDraft);
  useEffect(() => {
    if (open) {
      if (defaultFb) {
        setF({
          name: "AI Bot · FB ",
          kind: "playwright",
          start_url: "https://www.facebook.com/groups/",
          frequency_minutes: 15,
          max_pages: 3,
          config: { item_selector: "[role='feed'] > div", terms_checked: true },
          connector_type: "html_playwright",
          integration_status: "ready",
        });
      } else {
        setF(emptyDraft());
      }
    }
  }, [open, defaultFb]);
  const m = useMutation<Source, Error>({
    mutationFn: () => api<Source>("/admin/sources", { body: f }),
    onSuccess: (s) => (toast(`Đã thêm nguồn ${s.name}, đang tạm dừng`), onCreated(s.id), onClose()),
    onError: (e) => toast(messageOf(e), "danger"),
  });
  return (
    <Dialog open={open} onClose={onClose} onSubmit={() => m.mutate()} busy={m.isPending} title={defaultFb ? "Thêm Group Facebook Đà Nẵng (AI 24/7)" : "Thêm nguồn thu thập"} sub="Nguồn mới luôn ở trạng thái tạm dừng cho tới khi bạn chạy thử và bật lịch" submitLabel="Thêm nguồn">
      <Select
        label="Mẫu cấu hình nguồn"
        value=""
        onChange={(e) => {
          const profile = profiles.find((item) => item.id === e.target.value);
          if (profile) setF({ ...emptyDraft(), name: profile.name, kind: profile.kind, start_url: profile.start_url, config: { ...profile.config, terms_checked: profile.connector_type === "first_party" }, profile_id: profile.id, connector_type: profile.connector_type, integration_status: profile.integration_status });
        }}
      >
        <option value="">Tự cấu hình</option>
        {profiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.name}</option>)}
      </Select>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Tên nguồn" required minLength={2} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="VD: AI Bot · FB Hội Phòng Trọ Liên Chiểu" />
        <Select label="Phương thức" value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value as SourceDraft["kind"] })}>
          <option value="scrapy">{KIND.scrapy}</option>
          <option value="playwright">{KIND.playwright}</option>
          <option value="manual">{KIND.manual}</option>
        </Select>
      </div>
      {f.kind !== "manual" && (
        <>
          <Field label="URL bắt đầu" type="url" required value={f.start_url} onChange={(e) => setF({ ...f, start_url: e.target.value })} placeholder="https://www.facebook.com/groups/…" />
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Tần suất (phút)" type="number" min={5} max={1440} value={f.frequency_minutes} onChange={(e) => setF({ ...f, frequency_minutes: Number(e.target.value) })} />
            <Field label="Số trang tối đa mỗi lượt" type="number" min={1} max={50} value={f.max_pages} onChange={(e) => setF({ ...f, max_pages: Number(e.target.value) })} />
          </div>
          <SelectorFields cfg={f.config} onChange={(config) => setF({ ...f, config })} />
        </>
      )}
      <p className="rounded-md bg-muted p-3 text-xs text-ink-2">Phòng Ơi luôn tuân thủ giới hạn tốc độ và tự động lọc bài đăng bằng ML CPU trước khi lưu.</p>
    </Dialog>
  );
}

export default function AdminSources() {
  const qc = useQueryClient();
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = searchParams.get("tab") === "fb_group" ? "fb_group" : "website";
  const [activeGroup, setActiveGroup] = useState<"website" | "fb_group">(initialTab);
  const { data } = useQuery<Source[]>({ queryKey: ["ad-src"], queryFn: () => api("/admin/sources") });
  const [selId, setSelId] = useState<number | null>(null);
  const [adding, setAdding] = useState(false);
  const [cookieOpen, setCookieOpen] = useState(false);
  const [cookieLabel, setCookieLabel] = useState("");
  const [cookieProxy, setCookieProxy] = useState("");
  const [cookieInput, setCookieInput] = useState("");
  const [approving, setApproving] = useState(false);
  const [approval, setApproval] = useState({ terms_url: "", robots_url: "", notes: "" });
  const [query, setQuery] = useState("");
  const { data: fbCookie } = useQuery<FbCookieStatus>({ queryKey: ["fb-cookie"], queryFn: () => api("/admin/fb-cookie") });

  useEffect(() => {
    const t = searchParams.get("tab");
    if (t === "fb_group" || t === "website") {
      setActiveGroup(t);
    }
  }, [searchParams]);

  const fbSources = (data ?? []).filter(isFbGroupSource);
  const webSources = (data ?? []).filter((s) => !isFbGroupSource(s));
  const groupList = activeGroup === "fb_group" ? fbSources : webSources;

  const sel = groupList.find((s) => s.id === selId) ?? groupList[0] ?? data?.[0];
  const [f, setF] = useState<SourceEdit | null>(null);
  useEffect(() => {
    sel && setF({ start_url: sel.start_url, frequency_minutes: sel.frequency_minutes, max_pages: sel.max_pages, enabled: sel.enabled, config: sel.config ?? {} });
  }, [sel?.id]);

  const refresh = () => qc.invalidateQueries({ queryKey: ["ad-src"] });
  const save = useMutation({
    mutationFn: () => {
      if (!sel || !f) throw new Error("Chưa chọn nguồn");
      return api<Source>(`/admin/sources/${sel.id}`, { method: "PATCH", body: crawlable(sel.kind) ? f : { ...f, config: undefined } });
    },
    onSuccess: () => (toast("Đã lưu cấu hình"), refresh()),
    onError: (e: Error) => toast(messageOf(e), "danger"),
  });
  const run = useMutation<RunResponse, Error>({
    mutationFn: () => {
      if (!sel) throw new Error("Chưa chọn nguồn");
      return api<RunResponse>(`/admin/sources/${sel.id}/run`, { body: {} });
    },
    onSuccess: (r) => (toast(r.result ? `Lượt chạy ${r.result.status}: ${r.result.new} mới, ${r.result.dup} trùng, ${r.result.errors} lỗi` : "Đã đưa vào hàng đợi"), refresh()),
    onError: (e: Error) => toast(messageOf(e), "danger"),
  });
  const runBatch = useMutation<{ queued_count: number; skipped_count: number }, Error, "web" | "fb">({
    mutationFn: (scope) => api("/admin/sources/run-enabled", { body: { scope } }),
    onSuccess: (res, scope) => {
      const name = scope === "fb" ? "Group Facebook AI 24/7" : "Website cho thuê";
      if (res.queued_count > 0) {
        toast(`Đã chạy thu thập ${res.queued_count} nguồn ${name}`, "success");
      } else {
        toast(`Chưa có nguồn ${name} nào đang bật và đủ điều kiện`, "danger");
      }
      refresh();
    },
    onError: (e: Error) => toast(messageOf(e), "danger"),
  });
  const del = useMutation({
    mutationFn: () => {
      if (!sel) throw new Error("Chưa chọn nguồn");
      return api(`/admin/sources/${sel.id}`, { method: "DELETE" });
    },
    onSuccess: () => (toast(`Đã xóa nguồn ${sel?.name ?? ""}`), setSelId(null), refresh()),
    onError: (e: Error) => toast(messageOf(e), "danger"),
  });
  const approve = useMutation<Source, Error>({
    mutationFn: () => {
      if (!sel) throw new Error("Chưa chọn nguồn");
      return api<Source>(`/admin/sources/${sel.id}/approve`, { method: "POST", body: approval });
    },
    onSuccess: () => (toast("Đã ghi nhận phê duyệt; nguồn vẫn đang tạm dừng"), setApproving(false), refresh()),
    onError: (e: Error) => toast(messageOf(e), "danger"),
  });
  const sync = useMutation<{ created: number; total: number }, Error>({
    mutationFn: () => api("/admin/sources/sync-registry", { method: "POST" }),
    onSuccess: (r) => (toast(r.created ? `Đã thêm ${r.created} nguồn mới` : `Registry đã đủ ${r.total} nguồn`), refresh()),
    onError: (e: Error) => toast(messageOf(e), "danger"),
  });
  const saveCookie = useMutation<FbCookieStatus, Error>({
    mutationFn: () =>
      api("/admin/fb-cookie", {
        method: "POST",
        body: { cookie_input: cookieInput, label: cookieLabel, proxy_url: cookieProxy, check_live: true },
      }),
    onSuccess: (res) => {
      toast(`Đã thêm & kiểm tra tài khoản FB (Tổng: ${res.total_accounts} nick · ${res.live_count} LIVE)`, "success");
      setCookieLabel("");
      setCookieProxy("");
      setCookieInput("");
      qc.invalidateQueries({ queryKey: ["fb-cookie"] });
    },
    onError: (e) => toast(messageOf(e), "danger"),
  });
  const checkLive = useMutation<FbCookieStatus, Error, string | undefined>({
    mutationFn: (account_id) => api("/admin/fb-cookie/check", { method: "POST", body: { account_id: account_id ?? null } }),
    onSuccess: (res) => {
      toast(`Kết quả Check Live: ${res.live_count}/${res.total_accounts} tài khoản LIVE`, res.live_count > 0 ? "success" : "danger");
      qc.invalidateQueries({ queryKey: ["fb-cookie"] });
    },
    onError: (e) => toast(messageOf(e), "danger"),
  });
  const deleteAccount = useMutation<FbCookieStatus, Error, string>({
    mutationFn: (accountId) => api(`/admin/fb-cookie/${accountId}`, { method: "DELETE" }),
    onSuccess: () => {
      toast("Đã xóa tài khoản khỏi dàn Cookie FB", "success");
      qc.invalidateQueries({ queryKey: ["fb-cookie"] });
    },
    onError: (e) => toast(messageOf(e), "danger"),
  });
  const clearCookie = useMutation<FbCookieStatus, Error>({
    mutationFn: () => api("/admin/fb-cookie", { method: "DELETE" }),
    onSuccess: () => {
      toast("Đã xóa toàn bộ Cookie Facebook", "success");
      qc.invalidateQueries({ queryKey: ["fb-cookie"] });
    },
    onError: (e) => toast(messageOf(e), "danger"),
  });

  const switchTab = (tab: "website" | "fb_group") => {
    setActiveGroup(tab);
    setSearchParams({ tab });
    const targetList = tab === "fb_group" ? fbSources : webSources;
    if (targetList.length > 0) setSelId(targetList[0].id);
  };

  const addBtn = (
    <div className="flex flex-wrap gap-2">
      <Button variant="secondary" icon={<Sparkles className="h-4 w-4 text-violet" aria-hidden="true" />} onClick={() => setCookieOpen(true)}>
        {fbCookie?.total_accounts
          ? `Dàn Cookie FB (${fbCookie.live_count}/${fbCookie.total_accounts} LIVE)`
          : "Quản lý Cookie + Proxy FB"}
      </Button>
      <Button variant="secondary" icon={<RefreshCw className="h-4 w-4" aria-hidden="true" />} loading={sync.isPending} onClick={() => sync.mutate()}>Đồng bộ registry</Button>
      <Button icon={<Plus className="h-4 w-4" aria-hidden="true" />} onClick={() => setAdding(true)}>
        {activeGroup === "fb_group" ? "Thêm Group FB" : "Thêm Website"}
      </Button>
    </div>
  );

  if (!data) return <DashboardLayout role="admin" title="Nguồn thu thập"><Spinner /></DashboardLayout>;
  if (!sel || !f) return <DashboardLayout role="admin" title="Nguồn thu thập"><p className="text-sm text-ink-3">Chưa có nguồn thu thập.</p></DashboardLayout>;

  const isSelectedFb = isFbGroupSource(sel);

  return (
    <DashboardLayout
      role="admin"
      title="Nguồn thu thập"
      sub={`${webSources.length} Website cho thuê · ${fbSources.length} Group FB AI Crawl 24/7 · ${data.filter((s) => s.enabled).length} đang bật`}
      right={addBtn}
    >
      <AddSourceDialog open={adding} onClose={() => setAdding(false)} onCreated={(id) => (refresh(), setSelId(id))} defaultFb={activeGroup === "fb_group"} />
      <Dialog
        open={cookieOpen}
        onClose={() => setCookieOpen(false)}
        onSubmit={() => saveCookie.mutate()}
        busy={saveCookie.isPending}
        title="Quản lý Dàn Tài khoản Cookie + Proxy Facebook (AI Bot 24/7)"
        sub="Gắn nhiều tài khoản Facebook kèm Proxy riêng cho từng nick. Hệ thống tự động kiểm tra Cookie LIVE/DIE và xoay vòng tài khoản ít dùng nhất khi quét 38 Group Đà Nẵng."
        submitLabel="Thêm Tài Khoản & Check Live"
      >
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-xs font-semibold text-ink-2">
              Danh sách tài khoản đã gắn ({fbCookie?.total_accounts ?? 0} tài khoản · {fbCookie?.live_count ?? 0} LIVE)
            </div>
            {!!fbCookie?.total_accounts && (
              <div className="flex items-center gap-2">
                <Button variant="secondary" loading={checkLive.isPending} onClick={() => checkLive.mutate(undefined)}>
                  Check Live tất cả
                </Button>
                <Button variant="ghost" className="text-danger" loading={clearCookie.isPending} onClick={() => confirm("Xóa toàn bộ tài khoản Cookie FB?") && clearCookie.mutate()}>
                  Xóa hết
                </Button>
              </div>
            )}
          </div>

          {!fbCookie?.accounts?.length ? (
            <div className="rounded-lg border border-warning/40 bg-warning-50 p-3 text-xs text-warning">
              <b>Chưa có tài khoản nào trong dàn Cookie:</b> Hãy thêm ít nhất 1 tài khoản Facebook (kèm Proxy nếu có) ở bên dưới để Bot quét trực tiếp 38 Group Đà Nẵng.
            </div>
          ) : (
            <div className="max-h-56 space-y-2 overflow-y-auto pr-1">
              {fbCookie.accounts.map((acc) => {
                const [statusLabel, statusTone] = LIVE_BADGE[acc.live_status] ?? LIVE_BADGE.unchecked;
                return (
                  <div key={acc.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line bg-canvas p-3 text-xs">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-bold text-ink">{acc.label}</span>
                        <code className="rounded bg-muted px-1.5 py-0.5 text-[11px]">UID: {acc.c_user}</code>
                        <Badge tone={statusTone} dot>{statusLabel}</Badge>
                      </div>
                      <div className="text-ink-2">
                        <b>Proxy:</b> <code>{acc.proxy_display}</code> · <b>Đã quét:</b> {acc.usage_count} lượt
                      </div>
                      <div className="text-[11px] text-ink-3">{acc.live_message}</div>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Button variant="secondary" loading={checkLive.isPending} onClick={() => checkLive.mutate(acc.id)}>
                        Check Live
                      </Button>
                      <Button variant="ghost" className="text-danger" loading={deleteAccount.isPending} onClick={() => deleteAccount.mutate(acc.id)}>
                        Xóa
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="h-px bg-line my-2" />
        <div className="text-xs font-semibold text-ink">Thêm / Cập nhật Tài khoản Cookie + Proxy mới:</div>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field
            label="Tên gợi nhớ tài khoản"
            value={cookieLabel}
            onChange={(e) => setCookieLabel(e.target.value)}
            placeholder="VD: Clone Đà Nẵng 01"
          />
          <Field
            label="Proxy riêng cho nick này (Tùy chọn)"
            value={cookieProxy}
            onChange={(e) => setCookieProxy(e.target.value)}
            placeholder="ip:port:user:pass hoặc http://user:pass@ip:port"
          />
        </div>
        <TextArea
          label="Nội dung Cookie Facebook (JSON Cookie-Editor hoặc chuỗi c_user=...; xs=...)"
          required
          minLength={10}
          value={cookieInput}
          onChange={(e) => setCookieInput(e.target.value)}
          placeholder={'Dán JSON từ Cookie-Editor hoặc chuỗi c_user=1000...; xs=45%3A...; datr=...'}
        />
      </Dialog>
      <Dialog open={approving} onClose={() => setApproving(false)} onSubmit={() => approve.mutate()} busy={approve.isPending} title="Phê duyệt nguồn thu thập" sub="Lưu bằng chứng đã kiểm tra quyền sử dụng dữ liệu. Phê duyệt không tự động bật nguồn." submitLabel="Xác nhận phê duyệt">
        <Field label="URL điều khoản sử dụng" name="terms_url" type="url" required autoComplete="off" value={approval.terms_url} onChange={(e) => setApproval({ ...approval, terms_url: e.target.value })} placeholder="https://example.com/terms…" />
        <Field label="URL robots.txt" name="robots_url" type="url" required autoComplete="off" value={approval.robots_url} onChange={(e) => setApproval({ ...approval, robots_url: e.target.value })} placeholder="https://example.com/robots.txt…" />
        <TextArea label="Ghi chú kiểm tra" name="approval_notes" required minLength={10} maxLength={2000} autoComplete="off" value={approval.notes} onChange={(e) => setApproval({ ...approval, notes: e.target.value })} placeholder="Phạm vi được phép, giới hạn tốc độ, ngày kiểm tra…" />
      </Dialog>

      {/* Thanh chuyển đổi tách biệt 2 bên: 1 bên Website cho thuê | 1 bên Group FB AI Crawl 24/7 */}
      <div className="grid gap-4 md:grid-cols-2">
        <div
          role="button"
          tabIndex={0}
          onClick={() => switchTab("website")}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && switchTab("website")}
          className={clsx(
            "flex cursor-pointer items-center justify-between gap-4 rounded-xl border p-4 transition",
            activeGroup === "website" ? "border-primary bg-primary-50 ring-2 ring-primary/30" : "border-line bg-surface hover:border-line-strong"
          )}
        >
          <div className="flex items-center gap-3">
            <IconBox icon={Globe} tone={activeGroup === "website" ? "primary" : "muted"} size={42} className="bg-surface" />
            <div>
              <div className="flex items-center gap-2">
                <span className="text-base font-bold">1. Nguồn Website Cho Thuê</span>
                <Badge tone="Info">{webSources.filter((s) => s.enabled).length}/{webSources.length} bật</Badge>
              </div>
              <p className="caption">Các trang BĐS, cổng thông tin phòng trọ & nhà trọ Đà Nẵng</p>
            </div>
          </div>
          <Button
            variant="secondary"
            icon={<Play className="h-3.5 w-3.5" />}
            loading={runBatch.isPending}
            onClick={(e) => {
              e.stopPropagation();
              runBatch.mutate("web");
            }}
          >
            Chạy Website
          </Button>
        </div>

        <div
          role="button"
          tabIndex={0}
          onClick={() => switchTab("fb_group")}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && switchTab("fb_group")}
          className={clsx(
            "flex cursor-pointer items-center justify-between gap-4 rounded-xl border p-4 transition",
            activeGroup === "fb_group" ? "border-violet bg-violet-50 ring-2 ring-violet/30" : "border-line bg-surface hover:border-line-strong"
          )}
        >
          <div className="flex items-center gap-3">
            <IconBox icon={Sparkles} tone="violet" size={42} className="bg-surface" />
            <div>
              <div className="flex items-center gap-2">
                <span className="text-base font-bold">2. Nguồn Group FB · AI Crawl 24/7</span>
                <Badge tone="Success" dot>{fbSources.filter((s) => s.enabled).length}/{fbSources.length} trực tuyến</Badge>
              </div>
              <p className="caption">Bot Playwright quét bài mới 24/7 + ML CPU lọc tin tìm phòng/spam</p>
            </div>
          </div>
          <Button
            icon={<Sparkles className="h-3.5 w-3.5" />}
            loading={runBatch.isPending}
            onClick={(e) => {
              e.stopPropagation();
              runBatch.mutate("fb");
            }}
          >
            Chạy Bot FB 24/7
          </Button>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[360px_1fr]">
        <div className="space-y-3">
          <Field
            label={activeGroup === "fb_group" ? "Tìm Group Facebook Đà Nẵng" : "Tìm trang Website cho thuê"}
            type="search"
            placeholder={activeGroup === "fb_group" ? "Tìm tên Group FB…" : "Tìm tên Website BĐS…"}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <div className="max-h-[70vh] space-y-3 overflow-y-auto pr-1">
            {groupList
              .filter((source) => source.name.toLocaleLowerCase("vi").includes(query.trim().toLocaleLowerCase("vi")))
              .map((s) => {
                const [l, t] = SRC_STATUS[s.status] ?? SRC_STATUS.ok;
                const on = s.id === sel.id;
                const fb = isFbGroupSource(s);
                return (
                  <button
                    key={s.id}
                    onClick={() => setSelId(s.id)}
                    className={clsx(
                      "flex w-full items-center gap-3 rounded-lg border p-4 text-left transition",
                      on
                        ? fb
                          ? "border-violet bg-violet-50 ring-1 ring-violet"
                          : "border-primary bg-primary-50 ring-1 ring-primary"
                        : "border-line bg-surface hover:border-line-strong"
                    )}
                  >
                    <IconBox icon={fb ? Sparkles : Globe} tone={on ? (fb ? "violet" : "primary") : "muted"} size={36} className={on ? "bg-surface" : ""} />
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-semibold">{s.name}</div>
                      <div className="caption truncate">
                        {fb ? `AI Bot 24/7 · mỗi ${s.frequency_minutes} phút` : `${KIND[s.kind]} · ${s.integration_status === "ready" ? "sẵn sàng" : s.integration_status === "partner_required" ? "cần đối tác" : "chờ pháp lý"}`}
                      </div>
                    </div>
                    <Badge tone={t} dot>{l}</Badge>
                  </button>
                );
              })}
          </div>
        </div>

        <div className="min-w-0 space-y-6">
          <Card className={clsx("space-y-5", isSelectedFb && "border-violet/40")}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-h3">{sel.name}</h2>
                  <Badge tone={isSelectedFb ? "Info" : "Neutral"}>{isSelectedFb ? "AI Bot · Group FB 24/7" : "Website BĐS"}</Badge>
                </div>
                <p className="text-sm text-ink-3">
                  {KIND[sel.kind]} · sức khỏe {sel.health_score ?? 0}/100{sel.last_run_at && ` · thu thập lần cuối ${timeAgo(sel.last_run_at)}`}
                </p>
              </div>
              <Badge tone={(SRC_STATUS[sel.status] ?? SRC_STATUS.ok)[1]} dot>{(SRC_STATUS[sel.status] ?? SRC_STATUS.ok)[0]}</Badge>
            </div>

            {isSelectedFb && (
              <div className="rounded-lg border border-violet/30 bg-violet-50/70 p-4 text-xs text-ink-2 space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="font-semibold text-sm text-ink">Cơ chế vận hành AI Bot Facebook Group Đà Nẵng 24/7:</div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={fbCookie?.live_count ? "Success" : fbCookie?.total_accounts ? "Info" : "Warning"} dot>
                      {fbCookie?.total_accounts
                        ? `${fbCookie.live_count}/${fbCookie.total_accounts} Cookie LIVE · Xoay vòng tự động`
                        : "Chưa gắn Cookie FB · Đang chạy dữ liệu dự phòng"}
                    </Badge>
                    {!!fbCookie?.total_accounts && (
                      <Button variant="secondary" loading={checkLive.isPending} onClick={() => checkLive.mutate(undefined)}>
                        Check Live
                      </Button>
                    )}
                    <Button variant="secondary" onClick={() => setCookieOpen(true)}>
                      Quản lý Cookie + Proxy ({fbCookie?.total_accounts ?? 0})
                    </Button>
                  </div>
                </div>
                <div>• <b>Xoay vòng Đa Tài khoản & Proxy riêng:</b> Tự động chọn nick <code>LIVE</code> ít dùng nhất kèm Proxy riêng của nick đó cho mỗi lượt quét Group; tự động ngắt nick nếu gặp Checkpoint.</div>
                <div>• <b>Ép luồng thời gian thực:</b> Tự động gắn <code>?sorting_setting=CHRONOLOGICAL</code> & bóc tách ảnh gốc từ gói tin GraphQL (<code>all_subattachments</code> / <code>pcb.&lt;post_id&gt;</code>) + DOM.</div>
                <div>• <b>Bộ lọc AI Hybrid (0% GPU):</b> Mô hình <code>ML CPU (LinearSVC · F1 0.922)</code> tự động loại bỏ bài đăng <i>"Cần tìm phòng"</i> và <i>"Spam dịch vụ"</i> trong <code>&lt; 2ms</code>.</div>
              </div>
            )}

            <Field label={isSelectedFb ? "URL Group Facebook Đà Nẵng" : "URL bắt đầu"} value={f.start_url ?? ""} onChange={(e) => setF({ ...f, start_url: e.target.value })} disabled={!crawlable(sel.kind)} />
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Tần suất quét (phút)" inputMode="numeric" value={f.frequency_minutes ?? ""} onChange={(e) => setF({ ...f, frequency_minutes: Number(e.target.value) })} />
              <Field label={isSelectedFb ? "Số lượt cuộn / trang mỗi phiên" : "Số trang tối đa mỗi lượt"} inputMode="numeric" value={f.max_pages ?? ""} onChange={(e) => setF({ ...f, max_pages: Number(e.target.value) })} />
              <Field label="Giới hạn tốc độ" value={sel.rate_limit} disabled />
              <Field label="Phương thức" value={isSelectedFb ? "Playwright Headless + GraphQL Interceptor" : KIND[sel.kind]} disabled />
            </div>
            {crawlable(sel.kind) && <SelectorFields cfg={f.config ?? {}} onChange={(config) => setF({ ...f, config })} />}
            {([["Tuân thủ giới hạn tốc độ & chống trùng lặp SHA-256", true, true], [isSelectedFb ? "Bật giám sát Group FB 24/7 theo lịch" : "Bật thu thập theo lịch", f.enabled, false]] as [string, boolean, boolean][]).map(([l, v, locked]) => (
              <div key={l} className="flex items-center justify-between"><span className="text-sm">{l}{locked && <span className="caption"> · luôn bật</span>}</span><Toggle checked={!!v} onChange={(x) => !locked && setF({ ...f, enabled: x })} label={l} /></div>
            ))}
            {!f.enabled && crawlable(sel.kind) && <p className="rounded-md bg-warning-50 p-3 text-xs text-warning">Nguồn đang tạm dừng. Trước khi chạy hoặc bật, hãy khai báo selector và xác nhận điều khoản sử dụng.</p>}
            {sel.integration_status === "partner_required" && <p className="rounded-md bg-warning-50 p-3 text-xs text-warning">Nguồn này chỉ được tích hợp qua hợp đồng, feed hoặc API chính thức; crawler trực tiếp chưa được phép bật.</p>}
            {sel.approved_at && <p className="rounded-md bg-success-50 p-3 text-xs text-success">Đã phê duyệt vận hành lúc {new Intl.DateTimeFormat("vi-VN", { dateStyle: "short", timeStyle: "short" }).format(new Date(sel.approved_at))}.</p>}
            <div className="flex flex-wrap justify-between gap-3">
              <div>
                {sel.removable && (
                  <Button variant="ghost" className="text-danger" icon={<Trash2 className="h-4 w-4" />} loading={del.isPending} onClick={() => confirm(`Xóa nguồn ${sel.name} và lịch sử chạy của nguồn?`) && del.mutate()}>Xóa nguồn</Button>
                )}
              </div>
              <div className="flex gap-3">
                {crawlable(sel.kind) && sel.integration_status === "legal_review" && <Button variant="secondary" icon={<ShieldCheck className="h-4 w-4" aria-hidden="true" />} onClick={() => {
                  let robots = "";
                  try { robots = `${new URL(sel.start_url).origin}/robots.txt`; } catch { /* URL will be validated by the API. */ }
                  setApproval({ terms_url: sel.terms_url ?? "", robots_url: sel.robots_url ?? robots, notes: sel.approval_notes ?? "" });
                  setApproving(true);
                }}>Phê duyệt pháp lý</Button>}
                <Button variant="secondary" icon={<Play className="h-4 w-4" />} loading={run.isPending} onClick={() => run.mutate()}>{isSelectedFb ? "Chạy Bot FB ngay" : "Chạy thử"}</Button>
                <Button icon={<Save className="h-4 w-4" />} loading={save.isPending} onClick={() => save.mutate()}>Lưu cấu hình</Button>
              </div>
            </div>
          </Card>
          <Card pad="p-6">
            <h2 className="mb-4 text-h4">Lịch sử chạy gần đây</h2>
            {sel.runs.length === 0 ? <p className="text-sm text-ink-3">Nguồn chưa chạy lần nào.</p> : (
              <Table head={["Thời gian", "Trạng thái", "Tin mới", "Trùng", "Lỗi", "Thời lượng"]}>
                {sel.runs.map((r) => (
                  <tr key={r.id} title={r.message}>
                    <td className="px-4 py-3">{new Date(r.started_at).toLocaleString("vi-VN", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" })}</td>
                    <td className="px-4"><Badge tone={RUN[r.status][1]} dot>{RUN[r.status][0]}</Badge></td>
                    <td className="px-4">{r.new}</td><td className="px-4">{r.dup}</td>
                    <td className={`px-4 ${r.errors ? "text-warning" : "text-ink-3"}`}>{r.errors}</td>
                    <td className="px-4 text-ink-2">{r.duration_s != null ? `${r.duration_s} giây` : "—"}</td>
                  </tr>
                ))}
              </Table>
            )}
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
