import { col } from "../../lib/colors";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Bar, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { DashboardLayout, Table } from "../../components/Dashboard";
import { Bar as Progress, Card, Chip, Spinner, StatCard } from "../../components/ui";
import { api } from "../../lib/api";

type StatsResponse = {
  kpis: { impressions: number; impressions_change: number; views: number; ctr: number; contacts: number; contact_rate: number; saves: number; saves_change: number };
  daily: { label: string; views: number; contacts: number }[];
  funnel: { label: string; value: number }[];
  keywords: { keyword: string; share: number }[];
  per_room: { id: number; name: string; views: number; contacts: number; rate: number }[];
};

export default function LandlordStats() {
  const [days, setDays] = useState(30);
  const { data } = useQuery<StatsResponse>({ queryKey: ["ll-stats", days], queryFn: () => api(`/landlord/stats?days=${days}`) });
  return (
    <DashboardLayout role="landlord" title="Lượt xem và liên hệ" sub={`${days} ngày gần nhất · cập nhật mỗi giờ`} right={<><Chip state={days === 30 ? "selected" : "default"} onClick={() => setDays(30)}>30 ngày</Chip><Chip state={days === 7 ? "selected" : "default"} onClick={() => setDays(7)}>7 ngày</Chip></>}>
      {!data ? <Spinner /> : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Lượt hiển thị trong kết quả" value={data.kpis.impressions.toLocaleString("vi-VN")} delta={`${data.kpis.impressions_change >= 0 ? "+" : ""}${data.kpis.impressions_change}% so với kỳ trước`} />
            <StatCard label="Lượt xem chi tiết" value={data.kpis.views.toLocaleString("vi-VN")} delta={`Tỷ lệ bấm xem ${String(data.kpis.ctr).replace(".", ",")}%`} tone="muted" />
            <StatCard label="Lượt xem bài gốc, liên hệ" value={data.kpis.contacts} delta={`${String(data.kpis.contact_rate).replace(".", ",")}% lượt xem chi tiết`} />
            <StatCard label="Lượt lưu tin" value={data.kpis.saves} delta={`${data.kpis.saves_change >= 0 ? "+" : ""}${data.kpis.saves_change} so với kỳ trước`} />
          </div>
          <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
            <Card>
              <div className="flex items-center justify-between">
                <h2 className="text-h4">Lượt xem và liên hệ theo ngày</h2>
                <div className="flex gap-4 text-xs text-ink-2"><span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-primary-100" /> Lượt xem</span><span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-accent" /> Liên hệ</span></div>
              </div>
              <div className="mt-4 h-[260px]">
                <ResponsiveContainer>
                  <ComposedChart data={data.daily} margin={{ left: -20, right: 0, top: 10 }}>
                    <XAxis dataKey="label" interval={days === 30 ? 6 : 0} axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: col("text-3") }} />
                    <YAxis yAxisId="v" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: col("text-3") }} />
                    <YAxis yAxisId="c" orientation="right" hide />
                    <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid rgb(var(--border))", background: col("bg-surface") }} />
                    <Bar yAxisId="v" dataKey="views" name="Lượt xem" fill={col("primary-100")} radius={[4, 4, 0, 0]} />
                    <Line yAxisId="c" dataKey="contacts" name="Liên hệ" stroke={col("accent")} strokeWidth={2.5} dot={false} type="monotone" />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card className="space-y-4">
              <h2 className="text-h4">Phễu chuyển đổi</h2>
              {data.funnel.map((s, i) => (
                <div key={s.label} className="flex flex-col items-center gap-1.5">
                  <div className={`flex h-11 items-center justify-center rounded-md text-sm font-semibold ${i === 0 ? "bg-primary-100 text-primary-700" : i === 1 ? "bg-primary text-white" : "bg-accent text-white"}`} style={{ width: `${100 - i * 28}%` }}>{s.value.toLocaleString("vi-VN")}</div>
                  <span className="caption">{s.label}</span>
                </div>
              ))}
              <p className="text-sm text-success">Tỷ lệ liên hệ của bạn là {String(data.kpis.contact_rate).replace(".", ",")}% lượt xem chi tiết.</p>
            </Card>
          </div>
          <div className="grid gap-6 xl:grid-cols-2">
            <Card className="space-y-4">
              <h2 className="text-h4">Sinh viên tìm gì nhiều nhất</h2>
              {data.keywords.map((kw) => (
                <div key={kw.keyword} className="grid grid-cols-[140px_1fr_44px] items-center gap-3 text-sm">
                  <span>“{kw.keyword}”</span>
                  <Progress value={kw.share * 100 / Math.max(...data.keywords.map((x) => x.share))} tone="violet" height={10} />
                  <span className="text-right font-semibold">{Math.round(kw.share * 100)}%</span>
                </div>
              ))}
            </Card>
            <Card pad="p-6">
              <h2 className="mb-4 text-h4">Hiệu quả từng phòng</h2>
              <Table head={["Phòng", "Xem", "Liên hệ", "Tỷ lệ"]}>
                {data.per_room.map((r) => (
                  <tr key={r.id}><td className="px-4 py-3 font-semibold">{r.name}</td><td className="px-4">{r.views}</td><td className="px-4">{r.contacts}</td><td className={`px-4 font-semibold ${r.rate >= 6 ? "text-success" : "text-warning"}`}>{String(r.rate).replace(".", ",")}%</td></tr>
                ))}
              </Table>
            </Card>
          </div>
        </>
      )}
    </DashboardLayout>
  );
}
