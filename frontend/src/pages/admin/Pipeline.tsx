import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { DashboardLayout, Table } from "../../components/Dashboard";
import { Badge, Bar, Button, Card, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { num } from "../../lib/format";
import { PipelineFlow, type PipelineRun } from "./Overview";

type PipelineResponse = {
  latest: PipelineRun | null;
  field_accuracy: { field: string; f1: number }[];
  prompt_versions: { name: string; f1: number; cost: number; json_valid: number; current: boolean }[];
  runs: (PipelineRun & { id: number; collected: number; valid: number })[];
  issues: { id: number; snippet: string; reason: string; payload: Record<string, unknown> }[];
};

export default function AdminPipeline() {
  const { data } = useQuery<PipelineResponse>({ queryKey: ["ad-pipe"], queryFn: () => api("/admin/pipeline") });
  const [json, setJson] = useState<number | null>(null);
  if (!data) return <DashboardLayout role="admin" title="Pipeline dữ liệu"><Spinner /></DashboardLayout>;
  const avg = data.field_accuracy.reduce((sum, item) => sum + item.f1, 0) / Math.max(1, data.field_accuracy.length);

  return (
    <DashboardLayout role="admin" title="Pipeline dữ liệu" sub="Thu thập · làm sạch · trích xuất LLM · gộp trùng · chấm rủi ro · đánh chỉ mục">
      {data.latest && <Card><PipelineFlow p={data.latest} /></Card>}
      <div className="grid gap-6 xl:grid-cols-[1fr_460px]">
        <Card className="space-y-4">
          <div className="flex items-center justify-between"><h2 className="text-h4">Độ chính xác trích xuất theo trường (F1)</h2><Badge tone="Success">Trung bình {avg.toFixed(2).replace(".", ",")}</Badge></div>
          {data.field_accuracy.map((x) => (
            <div key={x.field} className="grid grid-cols-[150px_1fr_44px] items-center gap-4 text-sm">
              <span>{x.field}</span>
              <Bar value={x.f1 * 100} tone={x.f1 >= 0.9 ? "success" : x.f1 >= 0.85 ? "primary" : "warning"} height={10} />
              <span className="text-right font-semibold">{x.f1.toFixed(2).replace(".", ",")}</span>
            </div>
          ))}
          <p className="caption">Đánh giá trên 500 tin gán nhãn thủ công.</p>
        </Card>
        <Card pad="p-6">
          <h2 className="mb-4 text-h4">So sánh phiên bản prompt</h2>
          <Table head={["Phiên bản", "F1", "Chi phí/tin", "JSON hợp lệ"]}>
            {data.prompt_versions.map((v) => (
              <tr key={v.name}>
                <td className="px-4 py-3"><span className="font-semibold">{v.name}</span> {v.current && <Badge tone="Violet">Đang dùng</Badge>}</td>
                <td className="px-4">{v.f1.toFixed(2).replace(".", ",")}</td><td className="px-4">{v.cost}đ</td><td className="px-4">{String(v.json_valid).replace(".", ",")}%</td>
              </tr>
            ))}
          </Table>
        </Card>
      </div>
      <Card pad="p-6">
        <h2 className="mb-4 text-h4">Các lượt chạy</h2>
        <Table head={["Lượt", "Bắt đầu", "Thời lượng", "Thu thập", "Hợp lệ", "Trạng thái"]}>
          {data.runs.map((r) => (
            <tr key={r.id}>
              <td className="px-4 py-3 font-semibold">#{r.id}</td>
              <td className="px-4">{new Date(r.started_at).toLocaleString("vi-VN", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" })}</td>
              <td className="px-4 text-ink-2">{r.duration_s != null ? `${Math.floor(r.duration_s / 60)} phút ${r.duration_s % 60} giây` : "—"}</td>
              <td className="px-4">{num(r.collected)}</td><td className="px-4">{num(r.valid)}</td>
              <td className="px-4"><Badge tone={r.status === "success" ? "Success" : r.status === "error" ? "Danger" : "Warning"} dot>{r.status === "success" ? "Hoàn tất" : r.status === "error" ? "Lỗi" : "Lỗi một phần"}</Badge></td>
            </tr>
          ))}
        </Table>
      </Card>
      <Card className="space-y-3">
        <h2 className="text-h4">Tin không trích xuất được · cần xem lại</h2>
        {data.issues.map((i) => (
          <div key={i.id} className="space-y-2 rounded-md bg-muted px-4 py-3">
            <div className="flex flex-wrap items-center gap-4">
              <span className="min-w-0 flex-1 text-sm text-ink-2">“{i.snippet}”</span>
              <Badge tone="Warning">{i.reason}</Badge>
              <Button variant="ghost" onClick={() => setJson(json === i.id ? null : i.id)}>{json === i.id ? "Ẩn JSON" : "Xem JSON"}</Button>
            </div>
            {json === i.id && <pre className="overflow-x-auto rounded-md bg-surface p-3 text-xs">{JSON.stringify(i.payload, null, 2)}</pre>}
          </div>
        ))}
      </Card>
    </DashboardLayout>
  );
}
