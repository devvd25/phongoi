import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Check, Copy, Database, Globe, Play, Search, ShieldCheck, SlidersHorizontal, Sparkles, type LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";
import { DashboardLayout, Table } from "../../components/Dashboard";
import { Badge, Bar, Button, Card, IconBox, Spinner, StatCard, Toggle, useToast, type Tone } from "../../components/ui";
import { api } from "../../lib/api";
import { fullVnd, num, timeAgo } from "../../lib/format";

export type PipelineRun = {
  started_at: string;
  duration_s: number;
  status: string;
  stages: { key: string; label: string; tool: string; count: number }[];
};

type OverviewSource = {
  id: number;
  name: string;
  kind: string;
  source_group?: "website" | "fb_group";
  profile_id?: string | null;
  start_url?: string;
  connector_type: string;
  status: string;
  last_run_at: string | null;
  last_new: number;
  error_rate: number;
  enabled: boolean;
};

type AdminOverviewResponse = {
  dataset?: { mode: string; label?: string };
  kpis: { collected_24h: number; valid_24h: number; valid_rate: number; merged_24h: number; merged_rate: number; ai_cost_today: number; ai_cost_per_listing: number };
  services: { elasticsearch: boolean; llm_model: string; queue: string };
  pipeline: PipelineRun | null;
  sources: OverviewSource[];
  llm_usage: { task: string; model: string; calls: number }[];
  eval: { f1: number; json_valid: number; search_latency_s: number };
  budget: { used: number; monthly: number };
};

const STAGE_ICON: Record<string, LucideIcon> = { collect: Database, clean: SlidersHorizontal, extract: Sparkles, dedupe: Copy, risk: ShieldCheck, index: Search };
export const SRC_STATUS: Record<string, [string, Tone]> = { ok: ["Hoạt động", "Success"], running: ["Đang chạy", "Info"], error: ["Bị chặn / lỗi", "Danger"], paused: ["Tạm dừng", "Neutral"] };

export function isFbGroupSource(s: { source_group?: string; profile_id?: string | null; start_url?: string; name: string }): boolean {
  if (s.source_group) return s.source_group === "fb_group";
  const pid = (s.profile_id ?? "").toLowerCase();
  const url = (s.start_url ?? "").toLowerCase();
  const name = s.name.toLowerCase();
  return pid.startsWith("fb-group-") || pid === "facebook-groups" || url.includes("facebook.com/groups") || name.includes("fb ") || name.includes("facebook");
}

export function PipelineFlow({ p }: { p: PipelineRun }) {
  return (
    <div className="flex flex-col items-stretch gap-2 xl:flex-row xl:items-center">
      {p.stages.map((s, i) => {
        const Icon = STAGE_ICON[s.key] ?? Database;
        const llm = s.key === "extract";
        return (
          <div key={s.key} className="flex flex-1 items-center gap-2">
            <div className={`flex-1 space-y-1.5 rounded-lg border p-4 ${llm ? "border-violet bg-violet-50" : "border-line bg-canvas"}`}>
              <IconBox icon={Icon} tone={llm ? "violet" : "primary"} size={36} className={llm ? "bg-surface" : ""} />
              <div className="text-sm font-semibold">{s.label}</div>
              <div className="caption">{s.tool}</div>
              <div className={`text-h3 ${s.key === "index" ? "text-success" : ""}`}>{num(s.count)}</div>
            </div>
            {i < p.stages.length - 1 && <ArrowRight className="hidden h-[18px] w-[18px] shrink-0 text-ink-3 xl:block" />}
          </div>
        );
      })}
    </div>
  );
}

export default function AdminOverview() {
  const qc = useQueryClient();
  const toast = useToast();
  const { data } = useQuery<AdminOverviewResponse>({ queryKey: ["ad-ov"], queryFn: () => api("/admin/overview") });
  const runnableCount = data?.sources.filter((s) => s.enabled && (s.kind === "scrapy" || s.kind === "playwright" || s.connector_type === "rest_api")).length ?? 0;

  const run = useMutation<{ queued_count: number; skipped_count: number }, Error, "all" | "web" | "fb">({
    mutationFn: (scope = "all") => api("/admin/sources/run-enabled", { body: { scope } }),
    onSuccess: (result, scope) => {
      const label = scope === "fb" ? "AI Bot Group FB" : scope === "web" ? "nguồn Website" : "nguồn";
      if (result.queued_count > 0) {
        const skipped = result.skipped_count ? `; bỏ qua ${result.skipped_count} nguồn chưa đủ điều kiện` : "";
        toast(`Đã bắt đầu thu thập từ ${result.queued_count} ${label}${skipped}`, "success");
      } else {
        toast(`Chưa có ${label} đủ điều kiện đang bật.`, "danger");
      }
      qc.invalidateQueries();
    },
    onError: (error: Error) => toast(error.message, "danger"),
  });

  const toggle = useMutation({
    mutationFn: ({ id, enabled }: { id: number; enabled: boolean }) => api(`/admin/sources/${id}`, { method: "PATCH", body: { enabled } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ad-ov"] }),
  });

  if (!data) return <DashboardLayout role="admin" title="Tổng quan hệ thống"><Spinner /></DashboardLayout>;
  const k = data.kpis;
  const p = data.pipeline;

  const fbSources = data.sources.filter(isFbGroupSource);
  const webSources = data.sources.filter((s) => !isFbGroupSource(s));
  const enabledFbCount = fbSources.filter((s) => s.enabled && (s.kind === "scrapy" || s.kind === "playwright")).length;
  const enabledWebCount = webSources.filter((s) => s.enabled && (s.kind === "scrapy" || s.kind === "playwright" || s.connector_type === "rest_api")).length;

  return (
    <DashboardLayout
      role="admin"
      title="Tổng quan hệ thống"
      sub={`Dữ liệu tin đăng phòng trọ Đà Nẵng · ${data.services.elasticsearch ? "Elasticsearch" : "tìm kiếm SQL"} · ${data.services.llm_model}`}
      right={<>{data.dataset?.mode === "demo" && <Badge tone="Warning">Dữ liệu minh họa</Badge>}<Badge tone="Success" dot>Tất cả dịch vụ hoạt động</Badge><span title={runnableCount ? `Chạy tất cả ${runnableCount} nguồn đang bật` : "Hãy bật ít nhất một nguồn thu thập"}><Button variant="secondary" loading={run.isPending} disabled={!runnableCount} onClick={() => run.mutate("all")}>Chạy tất cả nguồn</Button></span></>}
    >
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Tin thu thập 24 giờ" value={num(k.collected_24h)} delta="Từ Website & Group FB đang bật" />
        <StatCard label="Tin hợp lệ sau xử lý" value={num(k.valid_24h)} delta={`${String(k.valid_rate).replace(".", ",")}% tổng tin thu thập`} tone="muted" />
        <StatCard label="Tin trùng đã gộp" value={num(k.merged_24h)} delta={`Tỷ lệ gộp ${String(k.merged_rate).replace(".", ",")}%`} tone="muted" />
        <StatCard label="Chi phí AI hôm nay" value={fullVnd(k.ai_cost_today)} delta={`≈ ${k.ai_cost_per_listing}đ mỗi tin (0% GPU)`} tone="muted" />
      </div>
      {p && (
        <Card className="space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-h4">Luồng xử lý dữ liệu · lượt chạy {new Date(p.started_at).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}</h2>
            <Badge tone={p.status === "success" ? "Success" : "Warning"}>Hoàn tất trong {Math.floor(p.duration_s / 60)} phút {p.duration_s % 60} giây</Badge>
          </div>
          <PipelineFlow p={p} />
        </Card>
      )}

      {/* Tách riêng 2 bên: 1 bên Website cho thuê, 1 bên Group Facebook AI Crawl 24/7 */}
      <div className="grid gap-6 xl:grid-cols-2">
        <Card pad="p-6" className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2.5">
              <IconBox icon={Globe} tone="primary" size={36} />
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-h4">Nguồn Website Cho Thuê</h2>
                  <Badge tone="Info">{enabledWebCount}/{webSources.length} đang bật</Badge>
                </div>
                <p className="caption">Cổng thông tin BĐS & nhà trọ Đà Nẵng (Scrapy / REST API)</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="secondary" icon={<Play className="h-3.5 w-3.5" />} loading={run.isPending} disabled={!enabledWebCount} onClick={() => run.mutate("web")}>
                Chạy Website
              </Button>
              <Button variant="ghost" to="/admin/nguon?tab=website">Quản lý</Button>
            </div>
          </div>
          <div className="max-h-[420px] overflow-y-auto">
            <Table head={["Website", "Trạng thái", "Chạy cuối", "Tin mới", "Lỗi", "Bật"]}>
              {webSources.map((s) => {
                const [l, t] = SRC_STATUS[s.status] ?? SRC_STATUS.ok;
                return (
                  <tr key={s.id}>
                    <td className="px-4 py-3 font-semibold">{s.name}</td>
                    <td className="px-4"><Badge tone={t} dot>{l}</Badge></td>
                    <td className="px-4 text-ink-2">{s.last_run_at ? timeAgo(s.last_run_at) : "—"}</td>
                    <td className="px-4">{s.last_new}</td>
                    <td className={`px-4 ${s.error_rate >= 50 ? "text-danger" : "text-ink-2"}`}>{String(s.error_rate).replace(".", ",")}%</td>
                    <td className="px-4"><Toggle checked={s.enabled} onChange={(v) => toggle.mutate({ id: s.id, enabled: v })} label={`Bật ${s.name}`} /></td>
                  </tr>
                );
              })}
            </Table>
          </div>
        </Card>

        <Card pad="p-6" className="space-y-4 border-violet/40">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2.5">
              <IconBox icon={Sparkles} tone="violet" size={36} />
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-h4">Nguồn Group FB · AI Crawl 24/7</h2>
                  <Badge tone="Success" dot>{enabledFbCount}/{fbSources.length} trực tuyến</Badge>
                </div>
                <p className="caption">Playwright CHRONOLOGICAL + ML CPU lọc tin tìm phòng & spam</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button icon={<Sparkles className="h-3.5 w-3.5" />} loading={run.isPending} disabled={!enabledFbCount} onClick={() => run.mutate("fb")}>
                Chạy AI Bot FB
              </Button>
              <Button variant="ghost" to="/admin/nguon?tab=fb_group">Cấu hình Bot</Button>
            </div>
          </div>
          <div className="max-h-[420px] overflow-y-auto">
            <Table head={["Group Facebook Đà Nẵng", "Trạng thái", "Chạy cuối", "Tin mới", "Lỗi", "24/7"]}>
              {fbSources.map((s) => {
                const [l, t] = SRC_STATUS[s.status] ?? SRC_STATUS.ok;
                return (
                  <tr key={s.id}>
                    <td className="px-4 py-3 font-semibold">{s.name}</td>
                    <td className="px-4"><Badge tone={t} dot>{l}</Badge></td>
                    <td className="px-4 text-ink-2">{s.last_run_at ? timeAgo(s.last_run_at) : "—"}</td>
                    <td className="px-4 font-semibold text-success">{s.last_new}</td>
                    <td className={`px-4 ${s.error_rate >= 50 ? "text-danger" : "text-ink-2"}`}>{String(s.error_rate).replace(".", ",")}%</td>
                    <td className="px-4"><Toggle checked={s.enabled} onChange={(v) => toggle.mutate({ id: s.id, enabled: v })} label={`Bật ${s.name}`} /></td>
                  </tr>
                );
              })}
            </Table>
          </div>
        </Card>
      </div>

      <Card className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-h4"><Sparkles className="h-5 w-5 text-violet" /> Hiệu năng AI Hybrid & Sử dụng mô hình</div>
          <Badge tone="Neutral">{data.services.llm_model}</Badge>
        </div>
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="space-y-2">
            {data.llm_usage.length === 0 ? (
              <p className="text-sm text-ink-2">Đang vận hành bằng mô hình ML CPU cục bộ (LinearSVC + RandomForest) · chi phí 0đ/tin.</p>
            ) : (
              data.llm_usage.map((u, i) => (
                <div key={u.task + u.model} className="space-y-1.5">
                  <div className="flex justify-between text-sm"><span className="text-ink-2">{u.model} · {u.task === "extract" ? "trích xuất tin" : u.task === "query" ? "hiểu truy vấn" : "tóm tắt"}</span><span className="font-semibold">{num(u.calls)}</span></div>
                  <Bar value={(u.calls / Math.max(...data.llm_usage.map((x) => x.calls))) * 100} tone={i === 0 ? "violet" : "primary"} />
                </div>
              ))
            )}
          </div>
          <div className="space-y-2">
            {[["Độ chính xác trích xuất (F1)", String(data.eval.f1).replace(".", ","), "text-success"], ["Đầu ra đúng định dạng JSON", `${String(data.eval.json_valid).replace(".", ",")}%`, "text-success"], ["Thời gian phản hồi tìm kiếm", `${String(data.eval.search_latency_s).replace(".", ",")} giây`, ""]].map(([l, v, c]) => (
              <div key={l} className="flex justify-between text-sm"><span className="text-ink-2">{l}</span><span className={`font-semibold ${c}`}>{v}</span></div>
            ))}
          </div>
          <div className="space-y-2">
            <Link to="/admin/chi-phi-ai" className="block space-y-2 rounded-md bg-muted p-3">
              <div className="flex justify-between text-[13px] font-semibold"><span>Ngân sách AI tháng này</span><span className="text-primary-700">{(data.budget.used / 1e6).toFixed(2).replace(".", ",")} / {data.budget.monthly / 1e6} triệu</span></div>
              <Bar value={(data.budget.used / data.budget.monthly) * 100} tone="accent" />
            </Link>
            <div className="flex items-center gap-2 text-xs text-ink-3"><Check className="h-4 w-4 text-success" /> Hàng đợi: {data.services.queue === "redis" ? "Celery + Redis" : "chạy đồng bộ (chế độ demo)"}</div>
          </div>
        </div>
      </Card>
    </DashboardLayout>
  );
}
