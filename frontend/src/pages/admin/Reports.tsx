import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DashboardLayout, Table } from "../../components/Dashboard";
import { Badge, Bar, Card, Chip, Spinner, StatCard, type Tone } from "../../components/ui";
import { api } from "../../lib/api";
import { timeAgo } from "../../lib/format";
import { useState } from "react";
import { Link } from "react-router-dom";

type ReportItem = { id: number; code: string; listing_title: string; reason: string; reporter: string; status: string; created_at: string };
type ReportsResponse = { kpis: { total: number; new: number; processing: number; confirmed: number; confirmed_rate: number; avg_hours: number }; items: ReportItem[]; by_reason: { reason: string; share: number }[] };
type ReportPatch = { id: number; s: string };
const ST: Record<string, [string, Tone]> = { new: ["Mới", "Danger"], processing: ["Đang xử lý", "Warning"], resolved: ["Đã xử lý", "Success"], rejected: ["Bác bỏ", "Neutral"] };

export default function AdminReports() {
  const qc = useQueryClient();
  const [status, setStatus] = useState("");
  const { data } = useQuery<ReportsResponse>({ queryKey: ["ad-rep", status], queryFn: () => api(`/admin/reports${status ? `?status=${status}` : ""}`) });
  const patch = useMutation({ mutationFn: ({ id, s }: ReportPatch) => api(`/admin/reports/${id}`, { method: "PATCH", body: { status: s } }), onSuccess: () => qc.invalidateQueries({ queryKey: ["ad-rep"] }) });
  if (!data) return <DashboardLayout role="admin" title="Báo cáo vi phạm"><Spinner /></DashboardLayout>;
  const k = data.kpis;
  return (
    <DashboardLayout role="admin" title="Báo cáo vi phạm" sub={`${k.total} báo cáo từ sinh viên trong 30 ngày`}>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Báo cáo mới" value={k.new} delta="Cần xử lý trong 24 giờ" tone="danger" />
        <StatCard label="Đang xử lý" value={k.processing} delta="Đã liên hệ người đăng" tone="muted" />
        <StatCard label="Xác nhận lừa đảo" value={k.confirmed} delta={`${String(k.confirmed_rate).replace(".", ",")}% số báo cáo`} />
        <StatCard label="Thời gian xử lý trung bình" value={`${String(k.avg_hours).replace(".", ",")} giờ`} delta="Mục tiêu dưới 24 giờ" />
      </div>
      <div className="grid gap-6 xl:grid-cols-[1fr_320px]">
        <Card pad="p-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-h4">Danh sách báo cáo</h2>
            <div className="flex gap-2">{[["", "Tất cả"], ["new", "Mới"], ["processing", "Đang xử lý"], ["resolved", "Đã xử lý"]].map(([s, l]) => <Chip key={s} state={status === s ? "selected" : "default"} onClick={() => setStatus(s)}>{l}</Chip>)}</div>
          </div>
          <Table head={["Mã", "Tin bị báo cáo", "Lý do", "Người báo cáo", "Trạng thái", "Thời gian"]}>
            {data.items.map((r) => (
              <tr key={r.id}>
                <td className="px-4 py-3 font-semibold">{r.code}</td>
                <td className="max-w-[260px] truncate px-4"><Link to="/admin/kiem-duyet" className="hover:text-primary">{r.listing_title}</Link></td>
                <td className="px-4 text-ink-2">{r.reason}</td>
                <td className="px-4 text-xs text-ink-3">{r.reporter}</td>
                <td className="px-4">
                  <select value={r.status} onChange={(e) => patch.mutate({ id: r.id, s: e.target.value })} aria-label="Đổi trạng thái" className="rounded-full border-0 bg-transparent p-0 text-xs font-semibold focus:ring-0">
                    {Object.entries(ST).map(([k2, [l]]) => <option key={k2} value={k2}>{l}</option>)}
                  </select>
                  <Badge tone={ST[r.status][1]} dot className="ml-1 hidden">{ST[r.status][0]}</Badge>
                </td>
                <td className="px-4 text-xs text-ink-3">{timeAgo(r.created_at)}</td>
              </tr>
            ))}
          </Table>
        </Card>
        <Card className="h-fit space-y-4">
          <h2 className="text-h4">Lý do phổ biến</h2>
          {data.by_reason.map((b) => (
            <div key={b.reason} className="grid grid-cols-[110px_1fr_40px] items-center gap-2 text-sm">
              <span>{b.reason}</span><Bar value={b.share * 100 / data.by_reason[0].share} tone="danger" height={10} /><span className="text-right font-semibold">{Math.round(b.share * 100)}%</span>
            </div>
          ))}
          <p className="caption">Báo cáo “yêu cầu cọc trước” được dùng làm dữ liệu huấn luyện cho mô hình chấm rủi ro.</p>
        </Card>
      </div>
    </DashboardLayout>
  );
}
