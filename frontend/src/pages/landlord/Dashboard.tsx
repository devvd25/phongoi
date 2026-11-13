import { col } from "../../lib/colors";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Clock, ImageIcon, Pencil, Plus, Sparkles, TrendingUp } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, XAxis } from "recharts";
import { DashboardLayout, Table } from "../../components/Dashboard";
import { RoomPhoto } from "../../components/ListingCard";
import { Badge, Button, Card, Chip, IconBox, Spinner, StatCard, useToast, type Tone } from "../../components/ui";
import { api } from "../../lib/api";
import { fullVnd } from "../../lib/format";

const SUG_ICON: Record<string, [any, any]> = { price: [TrendingUp, "warning"], photos: [ImageIcon, "primary"], stale: [Clock, "accent"] };

export default function LandlordDashboard() {
  const qc = useQueryClient();
  const toast = useToast();
  const [filter, setFilter] = useState("all");
  const nav = useNavigate();
  const { data } = useQuery<any>({ queryKey: ["ll-dash"], queryFn: () => api("/landlord/dashboard") });
  const act = useMutation({
    mutationFn: (s: any) => api(`/landlord/rooms/${s.listing_id}`, { method: "PATCH", body: s.kind === "price" ? { price: s.suggested_price } : { refresh: true } }),
    onSuccess: () => (toast("Đã cập nhật tin đăng"), qc.invalidateQueries({ queryKey: ["ll-dash"] })),
  });
  if (!data) return <DashboardLayout role="landlord" title="Tổng quan"><Spinner /></DashboardLayout>;
  const k = data.kpis;
  const max = Math.max(...data.views_7d.map((d: any) => d.views));
  const rooms = data.rooms.filter((r: any) => filter === "all" || (filter === "rented" ? r.status === "rented" && r.status_tone === "Warning" : r.status === filter));
  const today = new Date().toLocaleDateString("vi-VN", { weekday: "long", day: "2-digit", month: "2-digit", year: "numeric" });

  return (
    <DashboardLayout
      role="landlord"
      title={`Chào ${data.user.full_name.split(" ").slice(-2).join(" ")}`}
      sub={`${today} · ${k.total} phòng tại Liên Chiểu`}
      right={<>{data.user.phone_verified && <Badge tone="Success" dot>Chủ trọ đã xác minh</Badge>}<Button to="/chu-tro/dang-tin" icon={<Plus className="h-4 w-4" />}>Đăng tin mới</Button></>}
    >
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Phòng đang cho thuê" value={`${k.rented}/${k.total}`} delta={`Tỷ lệ lấp đầy ${k.occupancy}%`} />
        <StatCard label="Phòng còn trống" value={k.available} delta="Đang hiển thị với sinh viên" tone="muted" />
        <StatCard label="Lượt xem tuần này" value={k.views_week.toLocaleString("vi-VN")} delta={`${k.views_change >= 0 ? "+" : ""}${k.views_change}% so với tuần trước`} tone={k.views_change >= 0 ? "success" : "warning"} />
        <StatCard label="Lượt bấm liên hệ" value={k.contacts_week} delta={`Tỷ lệ chuyển đổi ${String(k.conversion).replace(".", ",")}%`} />
      </div>
      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <Card>
          <div className="flex items-center justify-between"><h2 className="text-h4">Lượt xem 7 ngày qua</h2><Chip state="selected">Tất cả phòng</Chip></div>
          <div className="mt-4 h-[240px]">
            <ResponsiveContainer>
              <BarChart data={data.views_7d} margin={{ top: 24, left: 0, right: 0 }}>
                <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fontSize: 13, fill: col("text-2") }} />
                <Bar dataKey="views" radius={[8, 8, 0, 0]} animationDuration={700}>
                  {data.views_7d.map((d: any, i: number) => <Cell key={i} fill={d.views === max ? col("primary") : col("primary-100")} />)}
                  <LabelList dataKey="views" position="top" style={{ fontSize: 12, fill: col("text-3") }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card className="space-y-4">
          <div className="flex items-center gap-2 text-h4 text-violet"><Sparkles className="h-5 w-5" /> Gợi ý từ AI</div>
          {data.suggestions.length === 0 && <p className="text-sm text-ink-2">Mọi phòng đều đang ổn. Tuyệt vời!</p>}
          {data.suggestions.map((s: any, i: number) => {
            const [Icon, tone] = SUG_ICON[s.kind];
            return (
              <div key={i} className="flex gap-3">
                <IconBox icon={Icon} tone={tone} size={36} />
                <div className="flex-1">
                  <div className="text-[13px] font-semibold">{s.title}</div>
                  <div className="text-xs text-ink-2">{s.text}</div>
                  <button onClick={() => (s.kind === "photos" ? nav(`/chu-tro/dang-tin?id=${s.listing_id}&muc=anh`) : act.mutate(s))} className="mt-1 text-[13px] font-semibold text-primary-700">{s.action}</button>
                </div>
              </div>
            );
          })}
        </Card>
      </div>
      <Card pad="p-0">
        <div className="flex flex-wrap items-center justify-between gap-3 p-6 pb-4">
          <h2 className="text-h3">Phòng của bạn</h2>
          <div className="flex flex-wrap gap-2">
            {[["all", `Tất cả · ${data.rooms.length}`], ["active", "Còn trống"], ["rented", "Sắp trống"], ["pending", "Chờ duyệt"]].map(([k2, l]) => (
              <Chip key={k2} state={filter === k2 ? "selected" : "default"} onClick={() => setFilter(k2)}>{l}</Chip>
            ))}
          </div>
        </div>
        <div className="px-6 pb-4">
          <Table head={["Phòng", "Giá thuê", "Trạng thái", "Lượt xem", "Liên hệ", "Chất lượng", ""]}>
            {rooms.map((r: any) => (
              <tr key={r.id}>
                <td className="px-4 py-3"><div className="flex items-center gap-3"><RoomPhoto src={r.image} alt="" className="h-12 w-12 rounded-md" /><div><div className="font-semibold">{r.title}</div><div className="caption">{r.street ? `Kiệt 45 ${r.street}` : r.district}</div></div></div></td>
                <td className="px-4 font-semibold">{fullVnd(r.price)}</td>
                <td className="px-4"><Badge tone={r.status_tone as Tone} dot>{r.status_label}</Badge></td>
                <td className="px-4">{r.status === "active" ? r.views : "—"}</td>
                <td className="px-4">{r.status === "active" ? r.contacts : "—"}</td>
                <td className={`px-4 font-semibold ${r.quality_score >= 8 ? "text-success" : "text-warning"}`}>{String(r.quality_score).replace(".", ",")}/10</td>
                <td className="px-4"><Link to={`/chu-tro/dang-tin?id=${r.id}`} aria-label={`Sửa ${r.title}`} className="inline-flex rounded-md p-2 text-ink-3 hover:bg-muted hover:text-ink"><Pencil className="h-4 w-4" /></Link></td>
              </tr>
            ))}
          </Table>
        </div>
      </Card>
    </DashboardLayout>
  );
}
