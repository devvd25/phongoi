import { useMutation, useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowRight, BarChart3, Check, ChevronRight, Clock, ExternalLink, Flag, Globe, GraduationCap, House, ImageIcon, Info, MapPin, Maximize2, Share2,
  ShieldAlert, ShieldCheck, Sparkles, Users, X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useCatalog } from "../components/FilterPanel";
import { StudentLayout } from "../components/Layout";
import { ListingCard, RoomPhoto, SaveButton } from "../components/ListingCard";
import { MapView } from "../components/MapView";
import { Badge, Bar, Button, Card, Checkbox, IconBox, Spinner, TextArea, useToast } from "../components/ui";
import { api } from "../lib/api";
import { fullVnd, riskLabel, riskTone, shortVnd, timeAgo, tr } from "../lib/format";

function PriceRange({ price, a }: { price: number; a: any }) {
  const lo = Math.min(a.p25 * 0.75, price * 0.9);
  const hi = Math.max(a.p75 * 1.25, price * 1.1);
  const x = (v: number) => `${((v - lo) / (hi - lo)) * 100}%`;
  return (
    <div className="relative mt-8 h-16">
      <div className="absolute top-6 h-2 w-full rounded-full bg-muted" />
      <div className="absolute top-6 h-2 rounded-full bg-primary-100" style={{ left: x(a.p25), width: `calc(${x(a.p75)} - ${x(a.p25)})` }} />
      <div className="absolute top-3.5 h-6 w-0.5 bg-ink-2" style={{ left: x(a.median) }} />
      <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} className="absolute top-[18px] -ml-2.5 h-5 w-5 rounded-full border-[3px] border-surface bg-primary shadow-glow" style={{ left: x(price) }} />
      <span className="absolute -top-2 -translate-x-1/2 whitespace-nowrap text-[13px] font-semibold text-primary-700" style={{ left: x(price) }}>Phòng này · {tr(price)}</span>
      <span className="absolute top-11 text-xs text-ink-3">{tr(lo)}</span>
      <span className="absolute right-0 top-11 text-xs text-ink-3">{tr(hi)}</span>
      <span className="absolute top-11 ml-2 whitespace-nowrap text-xs text-ink-2" style={{ left: x(a.median) }}>Trung vị khu vực · {tr(a.median)}</span>
    </div>
  );
}

function ReportDialog({ id, title, price, image, onClose }: { id: number; title: string; price: number; image?: string | null; onClose: () => void }) {
  const { data: cat } = useCatalog();
  const [reason, setReason] = useState("deposit");
  const [text, setText] = useState("");
  const [hide, setHide] = useState(true);
  const toast = useToast();
  const m = useMutation({
    mutationFn: () => api(`/listings/${id}/report`, { body: { reason, description: text } }),
    onSuccess: () => (toast("Đã gửi báo cáo. Cảm ơn bạn đã giúp cộng đồng!"), onClose()),
    onError: () => toast("Không gửi được báo cáo. Thử lại sau.", "danger"),
  });
  return (
    <motion.div className="fixed inset-0 z-[70] flex items-end justify-center bg-slate-950/50 backdrop-blur-[3px] sm:items-center" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose}>
      <motion.div role="dialog" aria-label="Báo cáo tin đăng" onClick={(e) => e.stopPropagation()} initial={{ y: 30, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className="max-h-[90vh] w-full space-y-4 overflow-y-auto rounded-t-xl bg-surface p-7 shadow-lg sm:max-w-[560px] sm:rounded-2xl">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-h3">Báo cáo tin đăng</h3>
            <p className="text-sm text-ink-3">Giúp cộng đồng sinh viên tránh tin xấu</p>
          </div>
          <button onClick={onClose} aria-label="Đóng" className="rounded-full bg-muted p-2"><X className="h-4 w-4" /></button>
        </div>
        <div className="flex items-center gap-3 rounded-lg bg-muted p-3">
          <RoomPhoto src={image} alt="" className="h-14 w-14 rounded-md" />
          <div className="min-w-0">
            <div className="truncate text-[13px] font-semibold">{title}</div>
            <div className="caption">{fullVnd(price)}/tháng</div>
          </div>
        </div>
        <div className="text-sm font-semibold">Vấn đề bạn gặp là gì?</div>
        <div className="space-y-2">
          {cat?.report_reasons.map((r) => (
            <label key={r.key} className={clsx("flex cursor-pointer items-center gap-3 rounded-md border px-4 py-3 text-sm", reason === r.key ? "border-primary bg-primary-50 font-semibold text-primary-700" : "border-line")}>
              <input type="radio" name="reason" className="sr-only" checked={reason === r.key} onChange={() => setReason(r.key)} />
              <span className={clsx("flex h-5 w-5 items-center justify-center rounded-full border-2", reason === r.key ? "border-primary" : "border-line-strong")}>
                {reason === r.key && <span className="h-2.5 w-2.5 rounded-full bg-primary" />}
              </span>
              {r.key === "deposit" ? "Nghi lừa đảo, yêu cầu chuyển cọc trước" : r.key === "wrong_info" ? "Thông tin sai: giá, ảnh hoặc địa chỉ" : r.key === "rented" ? "Phòng đã cho thuê nhưng tin vẫn đăng" : r.key === "duplicate" ? "Tin trùng lặp hoặc spam" : "Lý do khác"}
            </label>
          ))}
        </div>
        <TextArea label="Mô tả thêm (không bắt buộc)" value={text} onChange={(e) => setText(e.target.value)} placeholder="Ví dụ: chủ trọ yêu cầu chuyển cọc trước khi xem phòng" maxLength={1000} />
        <Checkbox checked={hide} onChange={setHide}>Ẩn tin này khỏi kết quả của tôi</Checkbox>
        <div className="flex items-center gap-2 text-xs text-ink-3">
          <Info className="h-4 w-4" /> Báo cáo được gửi ẩn danh. Đội kiểm duyệt phản hồi trong vòng 24 giờ.
        </div>
        <div className="flex justify-end gap-3">
          <Button variant="ghost" onClick={onClose}>Hủy</Button>
          <Button loading={m.isPending} onClick={() => m.mutate()}>Gửi báo cáo</Button>
        </div>
      </motion.div>
    </motion.div>
  );
}

export default function Listing() {
  const { id } = useParams();
  const { data: d, isLoading, isError } = useQuery<any>({ queryKey: ["listing", id], queryFn: () => api(`/listings/${id}`) });
  const { data: cat } = useCatalog();
  const [report, setReport] = useState(false);
  const [gallery, setGallery] = useState<number | null>(null);
  const toast = useToast();
  useEffect(() => {
    if (id) api(`/listings/${id}/event`, { body: { kind: "view" } }).catch(() => {});
  }, [id]);

  if (isLoading) return <StudentLayout><Spinner /></StudentLayout>;
  if (isError || !d)
    return (
      <StudentLayout>
        <div className="container-page py-24 text-center">
          <h1 className="text-h2">Không tìm thấy tin đăng</h1>
          <Button className="mt-6" to="/tim-kiem">Quay lại tìm phòng</Button>
        </div>
      </StudentLayout>
    );

  const imgs: (string | null)[] = Array.isArray(d.images) && d.images.length ? d.images : [null];
  const sourcesList: any[] = Array.isArray(d.sources) ? d.sources : [];
  const amenitiesList: string[] = Array.isArray(d.amenities) ? d.amenities : [];
  const aiSummaryList: string[] = Array.isArray(d.ai_summary)
    ? d.ai_summary
    : typeof d.ai_summary === "string" && d.ai_summary.trim()
      ? d.ai_summary
          .replace(/^\[|\]$/g, "")
          .split(/\s*·\s*|',\s*'|",\s*"/)
          .map((s: string) => s.replace(/^['"\[\]]+|['"\[\]]+$/g, "").trim())
          .filter(Boolean)
      : [];
  const reasonsList: string[] = Array.isArray(d.reasons) ? d.reasons : [];
  const nearbyList: any[] = Array.isArray(d.nearby) ? d.nearby : [];
  const similarList: any[] = Array.isArray(d.similar) ? d.similar : [];
  const original = sourcesList.find((s: any) => s.url)?.url;
  const contact = () => api(`/listings/${d.id}/event`, { body: { kind: "contact" } }).catch(() => {});
  const facts = [
    [Maximize2, "Diện tích", d.area ? `${d.area} m²` : "—"],
    [Users, "Số người", d.max_people ? `Tối đa ${d.max_people}` : "—"],
    [House, "Loại phòng", amenitiesList.includes("gac_lung") ? "Có gác lửng" : d.room_type_label],
    [Clock, "Giờ giấc", amenitiesList.includes("gio_tu_do") ? "Tự do" : "Theo quy định"],
  ];
  const qBits = [
    ["Đầy đủ thông tin", Math.min(10, (d.quality_score ?? 7) + 0.4)],
    ["Chất lượng ảnh", Math.min(10, 4 + (Array.isArray(d.images) ? d.images.length : 0))],
    ["Độ tin cậy nguồn", d.risk_level === "low" ? 9 : d.risk_level === "medium" ? 6 : 3],
  ] as const;

  return (
    <StudentLayout>
      <div className="container-page space-y-6 pb-28 pt-6 lg:pb-16">
        <nav className="flex items-center gap-2 text-[13px] text-ink-3" aria-label="Breadcrumb">
          <Link to="/tim-kiem" className="hover:text-primary">Tìm phòng</Link>
          <ChevronRight className="h-3.5 w-3.5" />
          <Link to={`/tim-kiem?q=${encodeURIComponent(d.district)}`} className="hover:text-primary">{d.district}</Link>
          <ChevronRight className="h-3.5 w-3.5" />
          <span className="truncate text-ink">{d.title}</span>
        </nav>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="space-y-3">
            <h1 className="text-[28px] font-bold leading-tight sm:text-h1">{d.title}</h1>
            <div className="flex flex-wrap items-center gap-3">
              <span className="flex items-center gap-1.5 text-ink-2"><MapPin className="h-[18px] w-[18px]" /> {d.address}</span>
              {d.source_count > 1 && <Badge tone="Info">Gộp từ {d.source_count} nguồn</Badge>}
              <Badge tone={riskTone[d.risk_level]} dot>{riskLabel[d.risk_level]}</Badge>
              <Badge>Đăng {timeAgo(d.posted_at)}</Badge>
            </div>
          </div>
          <div className="flex gap-3">
            <Button variant="ghost" icon={<Share2 className="h-4 w-4" />} onClick={() => (navigator.clipboard?.writeText(location.href), toast("Đã sao chép liên kết tin đăng", "info"))}>Chia sẻ</Button>
            <SaveButton id={d.id} initial={d.saved} className="h-10 w-10 border border-line" />
          </div>
        </div>

        {/* Gallery */}
        <div className="grid gap-4 md:grid-cols-[2fr_1fr_1fr] md:grid-rows-2">
          {[0, 1, 2, 3, 4].map((k) => (
            <button key={k} onClick={() => setGallery(k % imgs.length)} className={clsx("group relative overflow-hidden rounded-lg", k === 0 ? "aspect-[3/2] md:row-span-2 md:aspect-auto md:h-[420px]" : "hidden h-[202px] md:block")}>
              <RoomPhoto src={imgs[k % imgs.length]} fallbacks={imgs} alt={`${d.title} – ảnh ${k + 1}`} className="h-full w-full transition-transform duration-500 group-hover:scale-[1.03]" />
              {k === 4 && (
                <span className="absolute bottom-4 right-4 flex items-center gap-2 rounded-full bg-white/95 px-4 py-2 text-[13px] font-semibold text-slate-900 shadow-md">
                  <ImageIcon className="h-4 w-4" /> Xem {imgs.filter(Boolean).length} ảnh
                </span>
              )}
            </button>
          ))}
        </div>

        <div className="grid gap-8 lg:grid-cols-[1fr_400px]">
          <div className="space-y-6">
            <Card pad="p-5" className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              {facts.map(([Icon, l, v]: any) => (
                <div key={l} className="flex items-center gap-3">
                  <IconBox icon={Icon} />
                  <div>
                    <div className="caption">{l}</div>
                    <div className="text-sm font-semibold">{v}</div>
                  </div>
                </div>
              ))}
            </Card>

            <div className="space-y-3 rounded-xl border border-violet/25 bg-violet-50 p-6">
              <div className="flex items-center gap-2 text-h4 text-violet"><Sparkles className="h-5 w-5" /> Tóm tắt bởi AI</div>
              {aiSummaryList.length > 0 ? (
                aiSummaryList.map((s: string, idx: number) => (
                  <div key={`${idx}-${s}`} className="flex items-center gap-3"><span className="h-1.5 w-1.5 rounded-full bg-violet" /> {s}</div>
                ))
              ) : (
                <div className="flex items-center gap-3 text-sm text-ink-2"><span className="h-1.5 w-1.5 rounded-full bg-violet" /> Đã chuẩn hóa thông tin giá thuê, khu vực và tiện ích từ tin gốc</div>
              )}
              <p className="text-xs text-ink-3">Trích xuất tự động từ {d.source_count} tin đăng gốc. Thông tin có thể chưa chính xác, hãy xác nhận lại với chủ trọ.</p>
            </div>

            <Card>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-h3">Giá này có hợp lý không?</h2>
                <Badge tone={d.price_analysis.diff_pct <= 0 ? "Success" : d.price_analysis.diff_pct > 15 ? "Warning" : "Info"} dot>
                  {d.price_analysis.diff_pct <= 0 ? `Thấp hơn ${Math.abs(d.price_analysis.diff_pct)}% so với khu vực` : `Cao hơn ${d.price_analysis.diff_pct}% so với khu vực`}
                </Badge>
              </div>
              <PriceRange price={d.price} a={d.price_analysis} />
              <div className="mt-4 flex items-center gap-2 rounded-md bg-muted px-4 py-3 text-sm text-ink-2">
                <BarChart3 className="h-[18px] w-[18px] shrink-0 text-primary" />
                Mô hình {d.price_analysis.estimate.method === "model" ? "học máy" : "thống kê"} dự đoán giá hợp lý: {shortVnd(d.price_analysis.estimate.mid)} (±{shortVnd(d.price_analysis.estimate.mid - d.price_analysis.estimate.low)}). Vùng tô màu là mức giá của 50% phòng tương tự trong khu vực.
              </div>
            </Card>

            <Card>
              <h2 className="text-h3">Chi phí ước tính mỗi tháng</h2>
              <div className="mt-4 divide-y divide-line">
                {d.monthly_cost.items.map((i: any) => (
                  <div key={i.label} className="flex justify-between py-2.5"><span className="text-ink-2">{i.label}</span><span className="font-semibold">{fullVnd(i.amount)}</span></div>
                ))}
              </div>
              <div className="mt-2 flex items-center justify-between border-t border-line pt-3">
                <span className="text-h4">Tổng dự kiến</span>
                <span className="text-h3 text-primary-700">≈ {fullVnd(d.monthly_cost.total)}</span>
              </div>
            </Card>

            <Card>
              <h2 className="text-h3">Tiện ích</h2>
              <div className="mt-4 flex flex-wrap gap-2">
                {cat?.amenities.map((a) => {
                  const ok = amenitiesList.includes(a.key);
                  return (
                    <span key={a.key} className={clsx("inline-flex items-center gap-1.5 rounded-full border border-line px-3 py-2 text-sm", ok ? "bg-surface" : "bg-muted text-ink-3")}>
                      {ok ? <Check className="h-4 w-4 text-success" /> : <X className="h-4 w-4" />} {a.label}
                    </span>
                  );
                })}
              </div>
            </Card>

            <Card>
              <h2 className="text-h3">Vị trí và khoảng cách</h2>
              <div className="mt-4 grid gap-6 md:grid-cols-[340px_1fr]">
                <div className="h-[232px] overflow-hidden rounded-lg">
                  {d.lat && <MapView className="h-full w-full" pins={[{ id: d.id, lat: d.lat, lng: d.lng, price: d.price }]} activeId={d.id} school={d.school} />}
                </div>
                <div className="divide-y divide-line">
                  {nearbyList.map((n: any) => (
                    <div key={n.name} className="flex items-center gap-3 py-3">
                      <IconBox icon={n.kind === "school" ? GraduationCap : MapPin} tone="muted" size={36} />
                      <div><div className="text-sm font-semibold">{n.name}</div><div className="text-[13px] text-ink-3">{n.text}</div></div>
                    </div>
                  ))}
                </div>
              </div>
            </Card>

            <Card>
              <h2 className="text-h3">Bài đăng gốc</h2>
              <p className="mt-1 text-sm text-ink-2">Tin này được gộp từ {d.source_count} bài đăng. Phòng Ơi không lưu số điện thoại, bạn liên hệ chủ trọ tại bài gốc.</p>
              <div className="mt-4 space-y-3">
                {sourcesList.map((s: any, i: number) => (
                  <a key={i} href={s.url || undefined} target="_blank" rel="noopener noreferrer" onClick={contact} className="flex items-center gap-3 rounded-md border border-line px-4 py-3 transition hover:border-primary">
                    <IconBox icon={Globe} size={36} />
                    <div className="flex-1"><div className="text-sm font-semibold">{s.name}</div><div className="caption">Đăng {timeAgo(s.posted_at)}</div></div>
                    {s.url && <ExternalLink className="h-[18px] w-[18px] text-primary" />}
                  </a>
                ))}
              </div>
            </Card>
          </div>

          {/* Sidebar */}
          <aside className="space-y-4 lg:sticky lg:top-24 lg:self-start">
            <Card className="space-y-4 shadow-lg">
              <div className="flex items-baseline gap-1.5"><span className="text-h1 text-primary-700">{fullVnd(d.price)}</span><span className="text-ink-3">/tháng</span></div>
              <div className="text-sm text-ink-2">Cọc {d.deposit_months ?? 1} tháng · Hợp đồng từ 6 tháng</div>
              <div className="space-y-2.5 rounded-lg bg-violet-50 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-violet">{d.personalized ? "Vì sao hợp với bạn" : "Điểm nổi bật"}</span>
                  <Badge tone="Violet">Phù hợp {d.match}%</Badge>
                </div>
                {reasonsList.map((r: string) => <div key={r} className="flex items-center gap-2 text-sm"><Check className="h-4 w-4 text-success" /> {r}</div>)}
              </div>
              <Button full size="l" href={original} onClick={contact} iconRight={<ArrowRight className="h-4 w-4" />}>Xem bài đăng gốc</Button>
              <Button full size="l" variant="secondary" to="/da-luu">Lưu vào danh sách so sánh</Button>
              <p className="text-xs text-ink-3">Phòng Ơi không thu phí và không làm trung gian. Hãy xem phòng trực tiếp trước khi đặt cọc.</p>
            </Card>
            <Card pad="p-5" className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-sm font-semibold">
                  {d.risk?.level === "low" ? <ShieldCheck className="h-5 w-5 text-success" /> : <ShieldAlert className="h-5 w-5 text-danger" />} Kiểm tra an toàn
                </span>
                <Badge tone={riskTone[d.risk?.level || "low"]}>{riskLabel[d.risk?.level || "low"]} · {d.risk?.score ?? 0}/100</Badge>
              </div>
              {(Array.isArray(d.risk?.reasons) ? d.risk.reasons : []).map((r: string) => <div key={r} className="flex items-center gap-2 text-sm text-danger"><span className="h-2 w-2 rounded-full bg-danger" /> {r}</div>)}
              {(Array.isArray(d.risk?.checks) ? d.risk.checks : []).map((r: string) => <div key={r} className="flex items-center gap-2 text-sm text-ink-2"><Check className="h-4 w-4 text-success" /> {r}</div>)}
              <button onClick={() => setReport(true)} className="flex items-center gap-2 py-1 text-[13px] font-semibold text-danger"><Flag className="h-4 w-4" /> Báo cáo tin này</button>
            </Card>
            <Card pad="p-5" className="space-y-3">
              <div className="flex items-center justify-between"><span className="text-sm font-semibold">Chất lượng tin đăng</span><span className="text-h4 text-primary-700">{(d.quality_score ?? 7).toString().replace(".", ",")}/10</span></div>
              {qBits.map(([l, v]) => (
                <div key={l} className="space-y-1.5">
                  <div className="flex justify-between text-sm"><span className="text-ink-2">{l}</span><span className="font-semibold">{Math.round(v)}/10</span></div>
                  <Bar value={v * 10} height={6} />
                </div>
              ))}
            </Card>
          </aside>
        </div>

        {similarList.length > 0 && (
          <section className="space-y-5 pt-6">
            <div className="flex items-center justify-between"><h2 className="text-h2">Phòng tương tự gần đây</h2><Button variant="ghost" to={`/tim-kiem?q=${encodeURIComponent(d.district)}`} iconRight={<ArrowRight className="h-4 w-4" />}>Xem thêm</Button></div>
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">{similarList.map((l: any, i: number) => <ListingCard key={l.id} l={l} i={i} />)}</div>
          </section>
        )}
      </div>

      {/* Thanh dưới trên mobile */}
      <div className="fixed inset-x-0 bottom-[68px] z-30 flex items-center gap-3 border-t border-line bg-surface px-4 py-3 shadow-lg lg:hidden">
        <div className="flex-1"><div className="text-h4 text-primary-700">{fullVnd(d.price)}</div><div className="caption">/tháng · cọc {d.deposit_months ?? 1} tháng</div></div>
        <Button href={original} onClick={contact} iconRight={<ArrowRight className="h-4 w-4" />}>Xem bài gốc</Button>
      </div>

      <AnimatePresence>{report && <ReportDialog id={d.id} title={d.title} price={d.price} image={d.image} onClose={() => setReport(false)} />}</AnimatePresence>
      <AnimatePresence>
        {gallery !== null && (
          <motion.div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/90 p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setGallery(null)}>
            <RoomPhoto src={imgs[gallery]} alt="" className="max-h-[85vh] w-auto max-w-full rounded-lg" />
            <span className="absolute bottom-6 rounded-full bg-black/60 px-3 py-1 text-sm text-white">{gallery + 1}/{imgs.length}</span>
            <button className="absolute right-6 top-6 rounded-full bg-white/10 p-2 text-white" aria-label="Đóng"><X className="h-5 w-5" /></button>
            <button className="absolute right-6 top-1/2 rounded-full bg-white/10 p-3 text-white" aria-label="Ảnh tiếp" onClick={(e) => (e.stopPropagation(), setGallery((gallery + 1) % imgs.length))}><ChevronRight className="h-6 w-6" /></button>
          </motion.div>
        )}
      </AnimatePresence>
    </StudentLayout>
  );
}
