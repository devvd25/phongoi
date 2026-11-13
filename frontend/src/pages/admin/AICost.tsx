import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Bar as RBar, BarChart, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import { DashboardLayout, Table } from "../../components/Dashboard";
import { Bar, Button, Card, Field, Spinner, StatCard, Toggle, useToast } from "../../components/ui";
import { api } from "../../lib/api";
import { col } from "../../lib/colors";
import { fullVnd, num } from "../../lib/format";

const TASK: Record<string, string> = { extract: "Trích xuất tin đăng", query: "Hiểu truy vấn tìm kiếm", summary: "Tóm tắt tin cho sinh viên" };

type Budget = { monthly: number; alert_pct: number; auto_downgrade: boolean; used: number };
type BudgetForm = Omit<Budget, "monthly" | "alert_pct"> & { monthly: number | string; alert_pct: number | string };
type AICostResponse = {
  month: string;
  kpis: { cost: number; budget_pct: number; tokens: number; tokens_change: number; cost_per_listing: number; cache_rate: number };
  budget: Budget;
  daily: { label: string; extract: number; query: number; summary: number }[];
  by_task: { task: string; model: string; calls: number; tokens: number; cost: number }[];
};

export default function AdminAICost() {
  const qc = useQueryClient();
  const toast = useToast();
  const { data } = useQuery<AICostResponse>({ queryKey: ["ad-ai"], queryFn: () => api("/admin/ai-cost") });
  const [b, setB] = useState<BudgetForm | null>(null);
  useEffect(() => {
    data && setB(data.budget);
  }, [data]);
  const save = useMutation({
    mutationFn: () => {
      if (!b) throw new Error("Chưa tải được cấu hình ngân sách");
      return api("/admin/ai-budget", { method: "PUT", body: { monthly: Number(b.monthly), alert_pct: Number(b.alert_pct), auto_downgrade: b.auto_downgrade } });
    },
    onSuccess: () => (toast("Đã lưu ngân sách"), qc.invalidateQueries({ queryKey: ["ad-ai"] })),
  });
  if (!data || !b) return <DashboardLayout role="admin" title="Chi phí AI"><Spinner /></DashboardLayout>;
  const k = data.kpis;
  return (
    <DashboardLayout role="admin" title="Chi phí AI" sub={`Tháng ${data.month} · cập nhật mỗi giờ`}>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Chi phí tháng này" value={fullVnd(k.cost)} delta={`${k.budget_pct}% ngân sách`} tone={k.budget_pct >= Number(b.alert_pct) ? "warning" : "muted"} />
        <StatCard label="Token đã dùng" value={`${(k.tokens / 1e6).toFixed(1).replace(".", ",")} triệu`} delta={`${k.tokens_change >= 0 ? "+" : ""}${k.tokens_change}% so với tháng trước`} tone="warning" />
        <StatCard label="Chi phí trung bình mỗi tin" value={`${k.cost_per_listing}đ`} delta="Sau khi tối ưu prompt v3" />
        <StatCard label="Tỷ lệ dùng cache" value={`${k.cache_rate}%`} delta="Giảm lượt gọi lặp lại" />
      </div>
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-h4">Chi phí theo ngày và tác vụ</h2>
          <div className="flex gap-4 text-xs text-ink-2">{[["violet", "Trích xuất tin"], ["primary", "Hiểu truy vấn"], ["accent", "Tóm tắt tin"]].map(([c, l]) => <span key={l} className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: col(c) }} /> {l}</span>)}</div>
        </div>
        <div className="mt-4 h-[240px]">
          <ResponsiveContainer>
            <BarChart data={data.daily} margin={{ left: 0, right: 0 }}>
              <XAxis dataKey="label" interval={6} axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: col("text-3") }} />
              <Tooltip formatter={(v: number, n: string) => [fullVnd(v), TASK[n]]} contentStyle={{ borderRadius: 12, border: `1px solid ${col("border")}`, background: col("bg-surface") }} />
              <RBar dataKey="extract" stackId="a" fill={col("violet")} />
              <RBar dataKey="query" stackId="a" fill={col("primary")} />
              <RBar dataKey="summary" stackId="a" fill={col("accent")} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <Card pad="p-6">
          <h2 className="mb-4 text-h4">Theo tác vụ và mô hình</h2>
          <Table head={["Tác vụ", "Mô hình", "Lượt gọi", "Token", "Chi phí"]}>
            {data.by_task.map((r) => (
              <tr key={r.task + r.model}><td className="px-4 py-3 font-semibold">{TASK[r.task]}</td><td className="px-4 text-ink-2">{r.model}</td><td className="px-4">{num(r.calls)}</td><td className="px-4">{(r.tokens / 1e6).toFixed(1).replace(".", ",")} triệu</td><td className="px-4 font-semibold">{fullVnd(r.cost)}</td></tr>
            ))}
          </Table>
        </Card>
        <Card className="space-y-4">
          <h2 className="text-h4">Cảnh báo ngân sách</h2>
          <Field label="Ngân sách mỗi tháng (đồng)" inputMode="numeric" value={b.monthly} onChange={(e) => setB({ ...b, monthly: e.target.value.replace(/\D/g, "") })} />
          <Field label="Gửi cảnh báo khi đạt (%)" inputMode="numeric" value={b.alert_pct} onChange={(e) => setB({ ...b, alert_pct: e.target.value.replace(/\D/g, "") })} />
          <div className="flex items-center gap-3"><span className="flex-1 text-sm">Tự chuyển sang mô hình rẻ hơn khi vượt ngân sách</span><Toggle checked={b.auto_downgrade} onChange={(v) => setB({ ...b, auto_downgrade: v })} label="Tự chuyển mô hình" /></div>
          <div className="space-y-2">
            <div className="flex justify-between text-sm font-semibold"><span>Đã dùng</span><span className="text-primary-700">{(data.budget.used / 1e6).toFixed(2).replace(".", ",")} / {(data.budget.monthly / 1e6).toFixed(0)} triệu</span></div>
            <Bar value={(data.budget.used / data.budget.monthly) * 100} tone="accent" height={10} />
          </div>
          <Button full loading={save.isPending} onClick={() => save.mutate()}>Lưu ngân sách</Button>
        </Card>
      </div>
    </DashboardLayout>
  );
}
