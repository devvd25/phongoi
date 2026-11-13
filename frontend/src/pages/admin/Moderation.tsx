import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import { ExternalLink } from "lucide-react";
import { useState } from "react";
import { DashboardLayout } from "../../components/Dashboard";
import { RoomPhoto } from "../../components/ListingCard";
import { Badge, Bar, Button, Card, Chip, Spinner, useToast } from "../../components/ui";
import { api } from "../../lib/api";
import { timeAgo } from "../../lib/format";

const TABS = [["queue", "Chờ xử lý"], ["ai", "AI cảnh báo"], ["reports", "Sinh viên báo cáo"], ["pending", "Tin mới chờ duyệt"], ["done", "Đã ẩn"]] as const;

export default function AdminModeration() {
  const qc = useQueryClient();
  const toast = useToast();
  const [tab, setTab] = useState<string>("queue");
  const [selId, setSelId] = useState<number | null>(null);
  const { data } = useQuery<any>({ queryKey: ["ad-mod", tab], queryFn: () => api(`/admin/moderation?tab=${tab}`) });
  const cur = selId ?? data?.items[0]?.id;
  const { data: d } = useQuery<any>({ queryKey: ["ad-mod-d", cur], queryFn: () => api(`/admin/moderation/${cur}`), enabled: !!cur });
  const act = useMutation({
    mutationFn: (action: string) => api(`/admin/moderation/${cur}`, { body: { action } }),
    onSuccess: (_, a) => (toast(a === "hide" ? "Đã ẩn tin và đóng các báo cáo" : a === "approve" ? "Đã duyệt tin" : a === "block" ? "Đã khóa người đăng" : "Đã bỏ qua cảnh báo"), setSelId(null), qc.invalidateQueries({ queryKey: ["ad-mod"] })),
  });

  return (
    <DashboardLayout role="admin" title="Kiểm duyệt và báo cáo" sub={`${data?.counts.queue ?? "…"} tin đang chờ xử lý · ưu tiên theo điểm rủi ro`}>
      <div className="flex flex-wrap gap-2">
        {TABS.map(([k, l]) => <Chip key={k} state={tab === k ? "selected" : "default"} onClick={() => (setTab(k), setSelId(null))}>{l}{data?.counts[k] != null ? ` · ${data.counts[k]}` : ""}</Chip>)}
      </div>
      <div className="grid gap-6 xl:grid-cols-[1fr_400px]">
        <Card pad="p-3" className="min-w-0">
          {!data ? <Spinner /> : data.items.length === 0 ? <p className="p-8 text-center text-ink-2">Không có tin nào trong mục này.</p> : (
            <div className="divide-y divide-line">
              {data.items.map((l: any) => (
                <button key={l.id} onClick={() => setSelId(l.id)} className={clsx("flex w-full items-center gap-3 rounded-md px-3 py-3 text-left", l.id === cur && "bg-primary-50")}>
                  <RoomPhoto src={l.image} alt="" className="h-13 h-[52px] w-[52px] shrink-0 rounded-md" />
                  <div className="min-w-0 flex-1"><div className="truncate text-sm font-semibold">{l.title}</div><div className="caption truncate">{l.source} · {l.main_reason}</div></div>
                  <Badge tone={l.risk_score >= 65 ? "Danger" : l.risk_score >= 35 ? "Warning" : "Neutral"} dot>{l.risk_score}</Badge>
                  <span className="hidden w-16 text-center text-sm sm:block">{l.report_count} báo cáo</span>
                  <span className="hidden w-24 text-right text-xs text-ink-3 md:block">{timeAgo(l.posted_at)}</span>
                </button>
              ))}
            </div>
          )}
        </Card>
        {d && (
          <Card pad="p-5" className="h-fit space-y-4 shadow-lg xl:sticky xl:top-6">
            <RoomPhoto src={d.image} alt="" className="h-[180px] w-full rounded-lg" />
            <div>
              <h2 className="text-h4">{d.title}</h2>
              {d.sources.map((s: any) => s.url ? <a key={s.name} href={s.url} target="_blank" rel="noopener noreferrer" className="mt-1 flex items-center gap-1.5 text-sm text-primary-700">{s.name} <ExternalLink className="h-3.5 w-3.5" /></a> : <div key={s.name} className="caption">{s.name}</div>)}
            </div>
            <div className="space-y-2 rounded-lg bg-danger-50 p-4">
              <div className="flex items-center justify-between"><span className="text-sm font-semibold text-danger">Điểm rủi ro AI</span><span className="text-h3 text-danger">{d.risk.score}/100</span></div>
              <Bar value={d.risk.score} tone="danger" />
            </div>
            <div className="label-s text-ink-2">Lý do AI đánh dấu</div>
            {d.risk.reasons.length ? d.risk.reasons.map((r: string) => <div key={r} className="flex items-center gap-2.5 text-sm"><span className="h-2 w-2 shrink-0 rounded-full bg-danger" /> {r}</div>) : <p className="text-sm text-ink-3">Không có dấu hiệu bất thường.</p>}
            {d.reports.length > 0 && <div className="label-s text-ink-2">Báo cáo từ sinh viên · {d.reports.length}</div>}
            {d.reports.slice(0, 3).map((r: any) => (
              <div key={r.id} className="space-y-1 rounded-md bg-muted p-3"><div className="text-sm">“{r.text || r.reason}”</div><div className="caption">{r.label} · {timeAgo(r.created_at)}</div></div>
            ))}
            {d.status === "pending" ? (
              <Button full size="l" loading={act.isPending} onClick={() => act.mutate("approve")}>Duyệt và hiển thị tin</Button>
            ) : d.status !== "hidden" && (
              <div className="space-y-2">
                <Button full size="l" loading={act.isPending} onClick={() => act.mutate("hide")}>Xác nhận lừa đảo và ẩn tin</Button>
                <div className="flex gap-2"><Button variant="secondary" className="flex-1" onClick={() => act.mutate("dismiss")}>Bỏ qua cảnh báo</Button><Button variant="ghost" className="flex-1" onClick={() => act.mutate("block")}>Khóa người đăng</Button></div>
              </div>
            )}
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
}
