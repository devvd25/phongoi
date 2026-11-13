import { col } from "../lib/colors";
import { useMutation, useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { BarChart3, GraduationCap, Sparkles, ArrowRight } from "lucide-react";
import { useState } from "react";
import { Area, AreaChart, CartesianGrid, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Aurora } from "../components/Brand";
import { useCatalog } from "../components/FilterPanel";
import { StudentLayout } from "../components/Layout";
import { Badge, Button, Card, Chip, Field, Select, Spinner, StatCard } from "../components/ui";
import { api } from "../lib/api";
import { num, shortVnd, tr } from "../lib/format";

type DistrictPrice = { district: string; median: number; p25: number; p75: number; change_30d: number; count: number };
type TrendPoint = { label: string; month: number; median: number };
type MarketResponse = { active: number; city_median: number; change_30d: number; new_today: number; cheapest: DistrictPrice; priciest: DistrictPrice; districts: DistrictPrice[]; trend: TrendPoint[] };
type EstimateResponse = { low: number; high: number; confidence: number; method: "model" | "median" };

// Bố cục gần đúng các khu vực Đà Nẵng cho bản đồ nhiệt (đơn vị: % khung).
const LAYOUT: Record<string, [number, number, number, number]> = {
  "Liên Chiểu": [3, 9, 35, 43],
  "Hòa Vang": [3, 56, 35, 40],
  "Thanh Khê": [40, 30, 18, 25],
  "Hải Châu": [60, 34, 17, 61],
  "Cẩm Lệ": [40, 57, 18, 39],
  "Sơn Trà": [79, 7, 18, 50],
  "Ngũ Hành Sơn": [79, 60, 18, 36],
};

function heat(t: number) {
  // nội suy từ cam rất nhạt (#FFEDD5) tới cam đậm (#C2410C)
  const a = [255, 237, 213], b = [194, 65, 12];
  return `rgb(${a.map((v, i) => Math.round(v + (b[i] - v) * t)).join(",")})`;
}

export default function Market() {
  const { data } = useQuery<MarketResponse>({ queryKey: ["market"], queryFn: () => api("/market/overview") });
  const { data: cat } = useCatalog();
  const [form, setForm] = useState({ district: "Liên Chiểu", area: "20", amenities: ["gac_lung", "may_lanh"] as string[] });
  const est = useMutation<EstimateResponse>({ mutationFn: () => api("/market/estimate", { body: { district: form.district, area: Number(form.area) || null, amenities: form.amenities } }) });
  if (!data) return <StudentLayout><Spinner /></StudentLayout>;
  const meds = data.districts.map((d) => d.median);
  const [mn, mx] = [Math.min(...meds), Math.max(...meds)];
  const trend = data.trend.filter((t) => t.median).map((t) => ({ ...t, v: t.median / 1_000_000 }));
  const peak = trend.filter((t) => t.month === 8 || t.month === 9);

  return (
    <StudentLayout>
      <div className="relative isolate">
        <Aurora intensity={0.6} className="h-[420px]" />
        <div className="container-page space-y-8 pb-16 pt-10">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-semibold text-primary"><BarChart3 className="h-[18px] w-[18px]" /> Cập nhật hôm nay · {num(data.active)} tin đăng</div>
              <h1 className="text-[30px] font-bold sm:text-h1">Giá thuê phòng trọ tại Đà Nẵng</h1>
              <p className="max-w-2xl text-lg text-ink-2">Giá trung vị theo khu vực, xu hướng theo tháng và công cụ ước tính giá hợp lý cho phòng bạn đang xem.</p>
            </div>
            <div className="flex gap-2"><Chip state="selected">Phòng 15 – 25 m²</Chip><Chip>12 tháng</Chip></div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Giá trung vị toàn thành phố" value={shortVnd(data.city_median)} delta={`${data.change_30d > 0 ? "+" : ""}${String(data.change_30d).replace(".", ",")}% trong 30 ngày`} tone={data.change_30d > 0 ? "warning" : "success"} />
            <StatCard label="Tin đang hiển thị" value={num(data.active)} delta={`+${data.new_today} tin hôm nay`} />
            <StatCard label="Khu vực rẻ nhất" value={data.cheapest.district} delta={`Trung vị ${shortVnd(data.cheapest.median)}`} />
            <StatCard label="Khu vực đắt nhất" value={data.priciest.district} delta={`Trung vị ${shortVnd(data.priciest.median)}`} tone="muted" />
          </div>

          <div className="grid gap-6 lg:grid-cols-[760px_1fr]">
            <Card>
              <div className="flex items-center justify-between">
                <h2 className="text-h4">Bản đồ nhiệt giá theo khu vực</h2>
                <div className="flex items-center gap-2 text-xs text-ink-3">{tr(mn)} <span className="h-2 w-28 rounded-full" style={{ background: `linear-gradient(90deg, ${heat(0)}, ${heat(1)})` }} /> {tr(mx)}</div>
              </div>
              <div className="relative mt-4 aspect-[712/440] overflow-hidden rounded-lg" style={{ background: col("water") }}>
                <span className="absolute left-[42%] top-[6%] text-xs font-medium text-primary-700/70 dark:text-ink-3">Vịnh Đà Nẵng</span>
                <span className="absolute right-[4%] top-[1%] text-xs font-medium text-ink-3">Biển Đông</span>
                {data.districts.map((d) => {
                  const [x, y, w, h] = LAYOUT[d.district];
                  const t = (d.median - mn) / Math.max(1, mx - mn);
                  return (
                    <div key={d.district} className="absolute flex flex-col items-center justify-center rounded-lg border-[3px] border-white/90 text-center transition hover:z-10 hover:scale-[1.03] dark:border-canvas"
                      style={{ left: `${x}%`, top: `${y}%`, width: `${w}%`, height: `${h}%`, background: heat(t) }}>
                      <span className={clsx("text-[13px] font-semibold", t > 0.45 ? "text-white" : "text-slate-900")}>{d.district}</span>
                      <span className={clsx("text-h4", t > 0.45 ? "text-white" : "text-[#C2410C]")}>{shortVnd(d.median)}</span>
                    </div>
                  );
                })}
              </div>
            </Card>
            <Card pad="p-0">
              <h2 className="px-6 pt-6 text-h4">Xếp hạng khu vực</h2>
              <div className="mt-3 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="text-left text-xs text-ink-3"><th className="px-6 py-2 font-medium">Khu vực</th><th className="text-right font-medium">Trung vị</th><th className="text-right font-medium">Phổ biến</th><th className="text-right font-medium">30 ngày</th><th className="px-6 text-right font-medium">Số tin</th></tr></thead>
                  <tbody>
                    {data.districts.map((d) => (
                      <tr key={d.district} className="border-t border-line">
                        <td className="px-6 py-3 font-semibold">{d.district}</td>
                        <td className="text-right">{tr(d.median)}</td>
                        <td className="text-right text-ink-2">{(d.p25 / 1e6).toFixed(1).replace(".", ",")} – {(d.p75 / 1e6).toFixed(1).replace(".", ",")}</td>
                        <td className={clsx("text-right font-semibold", d.change_30d > 0 ? "text-warning" : d.change_30d < 0 ? "text-success" : "text-ink-3")}>{d.change_30d > 0 ? "+" : ""}{d.change_30d}%</td>
                        <td className="px-6 text-right text-ink-2">{num(d.count)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-[760px_1fr]">
            <Card>
              <div className="flex items-center justify-between"><h2 className="text-h4">Xu hướng giá trung vị 12 tháng</h2><Badge tone="Info">Toàn thành phố</Badge></div>
              <div className="mt-4 h-[280px]">
                <ResponsiveContainer>
                  <AreaChart data={trend} margin={{ top: 20, right: 10, left: -10, bottom: 0 }}>
                    <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#EA580C" stopOpacity={0.25} /><stop offset="1" stopColor="#EA580C" stopOpacity={0} /></linearGradient></defs>
                    <CartesianGrid vertical={false} stroke={col("border")} />
                    {peak.length > 0 && <ReferenceArea x1={peak[0].label} x2={peak[peak.length - 1].label} fill={col("primary-50")} fillOpacity={0.9} label={{ value: "Mùa nhập học", position: "insideTop", fill: "#C2410C", fontSize: 12 }} />}
                    <XAxis dataKey="label" tick={{ fontSize: 12, fill: col("text-3") }} axisLine={false} tickLine={false} />
                    <YAxis domain={["dataMin - 0.1", "dataMax + 0.1"]} tickFormatter={(v) => v.toFixed(1).replace(".", ",")} tick={{ fontSize: 12, fill: col("text-3") }} axisLine={false} tickLine={false} />
                    <Tooltip formatter={(v: number) => [`${v.toFixed(2).replace(".", ",")} triệu`, "Trung vị"]} contentStyle={{ borderRadius: 12, border: "1px solid rgb(var(--border))", background: col("bg-surface") }} />
                    <Area type="monotone" dataKey="v" stroke="#EA580C" strokeWidth={3} fill="url(#g)" animationDuration={800} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card className="space-y-4">
              <div className="flex items-center gap-2 text-h4"><GraduationCap className="h-5 w-5 text-accent" /> Mẹo cho tân sinh viên</div>
              {[
                ["Tìm phòng từ tháng 6 – 7", "Giá thường tăng 6 – 9% khi vào mùa nhập học tháng 8, 9."],
                [`Cân nhắc khu ${data.cheapest.district === "Hòa Vang" ? "Liên Chiểu" : data.cheapest.district}`, "Rẻ hơn khu trung tâm đáng kể, gần Bách khoa, Sư phạm và nhiều trường khác."],
                ["Tính đủ chi phí phát sinh", "Điện, nước, wifi, gửi xe có thể cộng thêm 500 – 700 nghìn mỗi tháng."],
                ["Cảnh giác giá rẻ bất thường", "Phòng rẻ hơn 40% so với trung vị khu vực thường có vấn đề."],
              ].map(([t, d], i) => (
                <div key={t} className="flex gap-3">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-50 text-[13px] font-semibold text-accent-800">{i + 1}</span>
                  <div><div className="text-sm font-semibold">{t}</div><div className="text-sm text-ink-2">{d}</div></div>
                </div>
              ))}
            </Card>
          </div>

          <Card className="grid gap-8 shadow-md lg:grid-cols-[1fr_400px]">
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-h3"><Sparkles className="h-5 w-5 text-violet" /> Ước tính giá hợp lý</div>
              <p className="text-ink-2">Nhập thông tin phòng bạn đang xem, mô hình học máy sẽ ước tính khoảng giá hợp lý dựa trên dữ liệu thực tế.</p>
              <div className="grid gap-4 sm:grid-cols-2">
                <Select label="Khu vực" value={form.district} onChange={(e) => setForm({ ...form, district: e.target.value })}>{cat?.districts.map((d) => <option key={d}>{d}</option>)}</Select>
                <Field label="Diện tích (m²)" inputMode="numeric" value={form.area} onChange={(e) => setForm({ ...form, area: e.target.value })} />
              </div>
              <div>
                <div className="label-s mb-2 text-ink-2">Tiện ích chính</div>
                <div className="flex flex-wrap gap-2">
                  {cat?.amenities.slice(0, 10).map((a) => (
                    <Chip key={a.key} state={form.amenities.includes(a.key) ? "selected" : "default"} onClick={() => setForm({ ...form, amenities: form.amenities.includes(a.key) ? form.amenities.filter((x) => x !== a.key) : [...form.amenities, a.key] })}>{a.label}</Chip>
                  ))}
                </div>
              </div>
              <Button loading={est.isPending} onClick={() => est.mutate()} iconRight={<ArrowRight className="h-4 w-4" />}>Ước tính giá</Button>
            </div>
            <div className="flex flex-col justify-center gap-2 rounded-lg bg-gradient-to-br from-primary-50 to-violet-50 p-6">
              <div className="text-sm font-semibold text-ink-2">Giá hợp lý cho phòng này</div>
              <div className="text-[40px] font-extrabold leading-tight text-primary-700">{est.data ? `${tr(est.data.low).replace(" tr", "")} – ${shortVnd(est.data.high)}` : "—"}</div>
              <div className="text-sm text-ink-3">{est.data ? `mỗi tháng · độ tin cậy ${Math.round(est.data.confidence * 100)}% · ${est.data.method === "model" ? "mô hình học máy" : "trung vị khu vực"}` : "Nhập thông tin rồi bấm Ước tính giá"}</div>
              {est.data && <p className="text-sm text-ink-2">Nếu chủ trọ báo giá trên {shortVnd(est.data.high * 1.08)}, bạn nên thương lượng hoặc so sánh thêm.</p>}
            </div>
          </Card>
        </div>
      </div>
    </StudentLayout>
  );
}
