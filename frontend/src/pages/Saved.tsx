import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import { ExternalLink, Heart, MapPin } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Aurora } from "../components/Brand";
import { StudentLayout } from "../components/Layout";
import { RoomPhoto } from "../components/ListingCard";
import { NotiRow, useNotificationPrefs, useNotifications } from "../components/NotificationBell";
import { Badge, Button, Card, Checkbox, Chip, Spinner, Toggle, type Tone } from "../components/ui";
import { api } from "../lib/api";
import { fullVnd, km, riskLabel, tr } from "../lib/format";
import type { ListingCard as Listing } from "../lib/types";

type SavedItem = Listing & { contacted: boolean; status_badge: { tone: Tone; label: string } };
type CompareColumn = Pick<Listing, "id" | "price" | "area" | "distance_km" | "risk_level" | "match"> & { monthly_total: number };
type Comparison = { recommended_id: number | null; columns: CompareColumn[] };
type ComparisonRow = [string, (column: CompareColumn) => string];

export default function Saved() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"all" | "watch" | "contacted">("all");
  const [sel, setSel] = useState<number[]>([]);
  const { prefs, set: setPref } = useNotificationPrefs();
  const { list: notis, readAll, open } = useNotifications();
  const { data: items, isLoading } = useQuery<SavedItem[]>({ queryKey: ["saved"], queryFn: () => api(`/me/saved`) });
  const { data: cmp } = useQuery<Comparison>({ queryKey: ["compare", sel], queryFn: () => api(`/me/compare?ids=${sel.join(",")}`), enabled: sel.length >= 2 });
  const unsave = useMutation({ mutationFn: (id: number) => api(`/me/saved/${id}`, { method: "DELETE" }), onSuccess: () => qc.invalidateQueries({ queryKey: ["saved"] }) });

  const shown = (items ?? []).filter((i) => (tab === "contacted" ? i.contacted : tab === "watch" ? i.risk_level !== "high" : true));
  const toggleSel = (id: number) => setSel((s) => (s.includes(id) ? s.filter((x) => x !== id) : s.length >= 3 ? s : [...s, id]));

  return (
    <StudentLayout>
      <div className="relative isolate">
        <Aurora intensity={0.45} className="h-[360px]" />
        <div className="container-page grid gap-8 pb-16 pt-10 lg:grid-cols-[1fr_400px]">
          <div className="space-y-5">
            <div className="flex items-center justify-between"><h1 className="text-h1">Tin đã lưu</h1><Badge>{items?.length ?? 0} phòng</Badge></div>
            <div className="flex flex-wrap gap-2">
              <Chip state={tab === "all" ? "selected" : "default"} onClick={() => setTab("all")}>Tất cả · {items?.length ?? 0}</Chip>
              <Chip state={tab === "watch" ? "selected" : "default"} onClick={() => setTab("watch")}>Đang theo dõi giá</Chip>
              <Chip state={tab === "contacted" ? "selected" : "default"} onClick={() => setTab("contacted")}>Đã liên hệ</Chip>
            </div>
            {isLoading ? <Spinner /> : shown.length === 0 ? (
              <Card className="py-12 text-center">
                <Heart className="mx-auto h-10 w-10 text-primary" />
                <div className="mt-3 text-h4">Chưa có tin nào</div>
                <p className="mt-1 text-ink-2">Bấm vào biểu tượng trái tim trên thẻ phòng để lưu lại và theo dõi giá.</p>
                <Button className="mt-5" to="/tim-kiem">Tìm phòng ngay</Button>
              </Card>
            ) : (
              shown.map((i) => (
                <div key={i.id} className={clsx("card flex items-center gap-4 p-3 transition", sel.includes(i.id) && "ring-2 ring-primary")}>
                  <Checkbox checked={sel.includes(i.id)} onChange={() => toggleSel(i.id)} />
                  <Link to={`/phong/${i.id}`} className="shrink-0"><RoomPhoto src={i.image} alt={i.title} className="h-24 w-32 rounded-md" /></Link>
                  <div className="min-w-0 flex-1 space-y-1.5">
                    <Link to={`/phong/${i.id}`} className="line-clamp-1 text-sm font-semibold hover:text-primary">{i.title}</Link>
                    <div className="flex items-center gap-1.5 text-[13px] text-ink-3"><MapPin className="h-3.5 w-3.5" /> {i.short_address}</div>
                    <div className="flex flex-wrap items-center gap-2.5"><span className="text-h4 text-primary-700">{fullVnd(i.price)}</span><Badge tone={i.status_badge.tone as Tone} dot>{i.status_badge.label}</Badge></div>
                  </div>
                  <div className="flex gap-1 pr-2">
                    <Link to={`/phong/${i.id}`} aria-label="Mở tin" className="rounded-md p-2 text-ink-2 hover:bg-muted"><ExternalLink className="h-5 w-5" /></Link>
                    <button aria-label="Bỏ lưu" onClick={() => unsave.mutate(i.id)} className="rounded-md p-2 hover:bg-danger-50"><Heart className="h-5 w-5 fill-danger text-danger" /></button>
                  </div>
                </div>
              ))
            )}

            <Card className="shadow-md">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-h3">So sánh {sel.length >= 2 ? `${sel.length} phòng đã chọn` : "phòng"}</h2>
                {cmp?.recommended_id && <Badge tone="Violet">AI đề xuất: Phòng {String.fromCharCode(65 + cmp.columns.findIndex((c) => c.id === cmp.recommended_id))}</Badge>}
              </div>
              {sel.length < 2 ? (
                <p className="mt-3 text-sm text-ink-2">Chọn 2 – 3 phòng bằng ô đánh dấu để so sánh giá, khoảng cách, tổng chi phí và mức phù hợp.</p>
              ) : cmp ? (
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr><th />{cmp.columns.map((c, k) => <th key={c.id} className={clsx("px-3 py-2 text-center", c.id === cmp.recommended_id && "rounded-t-md bg-primary-50 text-primary-700")}>Phòng {String.fromCharCode(65 + k)}</th>)}</tr>
                    </thead>
                    <tbody>
                      {([
                        ["Giá thuê", (c: CompareColumn) => tr(c.price)],
                        ["Diện tích", (c: CompareColumn) => (c.area ? `${c.area} m²` : "—")],
                        ["Tới trường", (c: CompareColumn) => km(c.distance_km) || "—"],
                        ["Tổng chi phí/tháng", (c: CompareColumn) => `≈ ${tr(c.monthly_total)}`],
                        ["Mức rủi ro", (c: CompareColumn) => riskLabel[c.risk_level].replace("Rủi ro ", "").replace(/^./, (x) => x.toUpperCase())],
                        ["Phù hợp với bạn", (c: CompareColumn) => `${c.match}%`],
                      ] satisfies ComparisonRow[]).map(([l, f]) => (
                        <tr key={l} className="border-t border-line">
                          <td className="py-3 pr-3 text-ink-2">{l}</td>
                          {cmp.columns.map((c) => <td key={c.id} className={clsx("px-3 py-3 text-center font-semibold", c.id === cmp.recommended_id && "bg-primary-50 text-primary-700")}>{f(c)}</td>)}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : <Spinner />}
            </Card>
          </div>

          <aside className="space-y-4">
            <Card pad="p-5" className="shadow-md">
              <div className="flex items-center justify-between pb-2"><h2 className="text-h3">Thông báo</h2><button onClick={readAll} className="text-[13px] font-semibold text-primary-700">Đánh dấu đã đọc</button></div>
              {notis.data?.map((n) => <NotiRow key={n.id} n={n} onClick={() => open(n)} />)}
            </Card>
            <Card pad="p-5" className="space-y-4" id="cai-dat-thong-bao">
              <div className="text-sm font-semibold">Nhận thông báo khi</div>
              {([["price_drop", "Giá phòng đã lưu giảm"], ["match", "Có tin mới khớp hồ sơ"], ["report", "Tin đã lưu bị báo cáo"], ["weekly", "Email tóm tắt hằng tuần"]] as const).map(([k, l]) => (
                <div key={k} className="flex items-center justify-between text-sm"><span>{l}</span><Toggle checked={!!prefs?.[k]} onChange={(v) => setPref(k, v)} label={l} /></div>
              ))}
            </Card>
          </aside>
        </div>
      </div>
    </StudentLayout>
  );
}
