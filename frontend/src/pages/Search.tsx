import { useQueries, useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { motion } from "framer-motion";
import { Check, ChevronRight, List, Map as MapIcon, RefreshCw, Search as SearchIcon, SlidersHorizontal, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { AISearchBar } from "../components/AISearchBar";
import { Aurora } from "../components/Brand";
import { FilterPanel, useCatalog } from "../components/FilterPanel";
import { StudentLayout } from "../components/Layout";
import { ListingCard, ListingCardSkeleton } from "../components/ListingCard";
import { MapView } from "../components/MapView";
import { Badge, Button, Chip, IconBox, Select, Skeleton, Toggle } from "../components/ui";
import { api } from "../lib/api";
import { shortVnd } from "../lib/format";
import type { Filters, SearchResult } from "../lib/types";

const DEFAULT: Filters = { districts: [], amenities: [], room_types: [], hide_high_risk: true, sort: "match" };

function AIProgress() {
  const steps = [
    ["Hiểu nhu cầu", 0.2],
    ["Lọc tin đăng", 0.6],
    ["Xếp hạng theo mức phù hợp", 1.0],
  ] as const;
  return (
    <div className="flex flex-wrap items-center gap-4 rounded-lg bg-violet-50 px-4 py-3">
      <span className="flex items-center gap-2 text-sm font-semibold text-violet">
        <Sparkles className="h-[18px] w-[18px] animate-pulse" /> AI đang phân tích câu hỏi của bạn…
      </span>
      {steps.map(([l, d]) => (
        <motion.span key={l} initial={{ opacity: 0.4 }} animate={{ opacity: 1 }} transition={{ delay: d }} className="flex items-center gap-1.5 text-[13px] font-semibold">
          <Check className="h-4 w-4 text-success" /> {l}
        </motion.span>
      ))}
    </div>
  );
}

function Empty({ filters, onApply }: { filters: Filters; onApply: (f: Filters) => void }) {
  const relax = useMemo(() => {
    const out: { label: string; f: Filters }[] = [];
    if (filters.budget_max) out.push({ label: `Tăng ngân sách lên ${shortVnd(Math.round(filters.budget_max * 1.3 / 100000) * 100000)}`, f: { ...filters, budget_max: Math.round(filters.budget_max * 1.3) } });
    if (filters.districts.length) out.push({ label: "Mở rộng ra các khu vực lân cận", f: { ...filters, districts: [] } });
    if (filters.max_distance_km) out.push({ label: `Nới khoảng cách tới ${filters.max_distance_km * 2} km`, f: { ...filters, max_distance_km: filters.max_distance_km * 2 } });
    if (filters.amenities.length) out.push({ label: "Bỏ bớt yêu cầu tiện ích", f: { ...filters, amenities: filters.amenities.slice(0, -1) } });
    return out.slice(0, 3);
  }, [filters]);
  const counts = useQueries({
    queries: relax.map((r) => ({ queryKey: ["count", r.f], queryFn: () => api<SearchResult>("/search", { body: { filters: r.f, page_size: 4 } }) })),
  });
  return (
    <div className="flex flex-col items-center py-12 text-center">
      <div className="flex h-28 w-28 items-center justify-center rounded-full bg-gradient-to-br from-primary-100 to-violet-50 shadow-glow">
        <SearchIcon className="h-12 w-12 text-primary" />
      </div>
      <h2 className="mt-6 text-h2">Chưa có phòng khớp hoàn toàn</h2>
      <p className="mt-2 max-w-xl text-lg text-ink-2">Thử nới một vài tiêu chí, AI đã tính sẵn số phòng phù hợp cho từng lựa chọn:</p>
      <div className="mt-6 grid w-full max-w-4xl gap-4 sm:grid-cols-3">
        {relax.map((r, i) => (
          <button key={r.label} onClick={() => onApply(r.f)} className="card flex items-center gap-3 p-4 text-left shadow-md transition hover:-translate-y-0.5 hover:shadow-lg">
            <IconBox icon={Sparkles} tone="violet" />
            <div className="flex-1">
              <div className="text-sm font-semibold">{r.label}</div>
              <div className="text-[13px] text-success">{counts[i]?.data ? `${counts[i].data!.total} phòng phù hợp` : "Đang đếm…"}</div>
            </div>
            <ChevronRight className="h-4 w-4 text-ink-3" />
          </button>
        ))}
      </div>
    </div>
  );
}

export default function Search() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const q = params.get("q") ?? "";
  const [filters, setFilters] = useState<Filters | null>(null);
  const [page, setPage] = useState(1);
  const [panel, setPanel] = useState(false);
  const [hover, setHover] = useState<number | null>(null);
  const [mobileMap, setMobileMap] = useState(false);
  const { data: cat } = useCatalog();
  useEffect(() => {
    (setFilters(null), setPage(1));
  }, [q]);

  const body = filters ? { filters, page } : { query: q || undefined, page };
  const { data, isFetching, isError, refetch } = useQuery<SearchResult>({ queryKey: ["search", body], queryFn: () => api("/search", { body }), placeholderData: (p) => p });
  const f: Filters = filters ?? data?.filters ?? DEFAULT;
  const apply = (nf: Filters) => (setFilters(nf), setPage(1), setPanel(false));
  const loading = isFetching && (!data || filters === null);

  const removeChip = (chip: string) => {
    const nf = { ...f };
    if (chip.startsWith("Giá") || chip.includes("–")) (nf.budget_max = null), (nf.budget_min = null);
    else if (chip.startsWith("Cách")) (nf.school_id = null), (nf.max_distance_km = null);
    else if (cat?.districts.includes(chip)) nf.districts = f.districts.filter((d) => d !== chip);
    else {
      const a = cat?.amenities.find((x) => x.label === chip);
      const r = cat?.room_types.find((x) => x.label === chip);
      if (a) nf.amenities = f.amenities.filter((x) => x !== a.key);
      else if (r) nf.room_types = f.room_types.filter((x) => x !== r.key);
      else if (chip.startsWith("Từ")) nf.area_min = null;
      else if (chip.endsWith("người")) nf.max_people = null;
      else nf.keywords = null;
    }
    apply(nf);
  };

  const pills: [string, boolean][] = [
    [f.budget_min || f.budget_max ? `Giá: ${f.budget_min ? shortVnd(f.budget_min) : "0"} – ${f.budget_max ? shortVnd(f.budget_max) : "∞"}` : "Giá", !!(f.budget_min || f.budget_max)],
    [f.districts.length ? `Khu vực: ${f.districts.join(", ")}` : "Khu vực", f.districts.length > 0],
    [f.area_min ? `Từ ${Math.round(f.area_min)} m²` : "Diện tích", !!f.area_min],
    [f.amenities.length ? `Tiện ích · ${f.amenities.length}` : "Tiện ích", f.amenities.length > 0],
    [f.room_types.length ? `Loại · ${f.room_types.length}` : "Loại phòng", f.room_types.length > 0],
  ];

  return (
    <StudentLayout footer={false}>
      <div className="relative isolate">
        <Aurora intensity={0.55} className="h-[420px]" />
        <div className="container-page space-y-4 pb-4 pt-6">
          <AISearchBar key={q} initial={q} busy={loading} onSubmit={(v) => nav(`/tim-kiem?q=${encodeURIComponent(v)}`)} />
          {loading ? (
            <AIProgress />
          ) : (
            data &&
            data.chips.length > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                <span className="flex items-center gap-1.5 text-sm font-semibold text-violet">
                  <Sparkles className="h-4 w-4" /> AI đã hiểu:
                </span>
                {data.chips.map((c) => (
                  <Chip key={c} state="ai" onRemove={() => removeChip(c)}>{c}</Chip>
                ))}
                <Button variant="ghost" onClick={() => setPanel(true)}>Chỉnh tiêu chí</Button>
              </div>
            )
          )}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap gap-2">
              <button onClick={() => setPanel(true)} className="focus-ring inline-flex h-9 items-center gap-2 rounded-full border border-line bg-surface px-4 text-[13px] font-semibold">
                <SlidersHorizontal className="h-4 w-4" /> Bộ lọc
              </button>
              {pills.map(([l, a]) => (
                <button key={l} onClick={() => setPanel(true)} className={clsx("focus-ring hidden h-9 items-center rounded-full border px-4 text-[13px] font-semibold md:inline-flex", a ? "border-primary bg-primary-50 text-primary-700" : "border-line bg-surface")}>
                  {l}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-[13px] font-semibold">
                <Toggle checked={f.hide_high_risk} onChange={(v) => apply({ ...f, hide_high_risk: v })} label="Ẩn tin rủi ro cao" /> Ẩn tin rủi ro cao
              </label>
              <Select label="" aria-label="Sắp xếp" value={f.sort} onChange={(e) => apply({ ...f, sort: e.target.value as Filters["sort"] })} className="[&>select]:mt-0 [&>select]:h-9 [&>span]:hidden">
                <option value="match">Sắp xếp: Phù hợp nhất</option>
                <option value="price_asc">Giá thấp đến cao</option>
                <option value="price_desc">Giá cao đến thấp</option>
                <option value="newest">Mới đăng</option>
                <option value="distance">Gần trường nhất</option>
              </Select>
            </div>
          </div>
        </div>
      </div>

      <div className="container-page pb-10">
        {isError ? (
          <div className="flex flex-col items-center py-20 text-center">
            <IconBox icon={RefreshCw} tone="warning" size={72} />
            <h2 className="mt-5 text-h2">Không tải được kết quả</h2>
            <p className="mt-2 max-w-md text-ink-2">Kết nối mạng không ổn định hoặc máy chủ đang bận. Tin bạn đã lưu vẫn xem được.</p>
            <div className="mt-6 flex gap-3">
              <Button onClick={() => refetch()}>Thử lại</Button>
              <Button variant="ghost" to="/da-luu">Xem tin đã lưu</Button>
            </div>
          </div>
        ) : !loading && data && data.total === 0 ? (
          <Empty filters={f} onApply={apply} />
        ) : (
          <div className="grid gap-6 lg:grid-cols-[664px_1fr]">
            <div className={clsx("space-y-4", mobileMap && "hidden lg:block")}>
              <div>
                <h1 className="text-h3">{loading ? <Skeleton className="h-7 w-48" /> : `${data?.total ?? 0} phòng phù hợp`}</h1>
                {data && !loading && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {data.hidden_risky > 0 && <Badge tone="Danger" dot>Đã ẩn {data.hidden_risky} tin rủi ro cao</Badge>}
                    {data.merged_duplicates > 0 && <Badge tone="Info" dot>Gộp {data.merged_duplicates} tin trùng lặp</Badge>}
                    <Badge>Từ {data.source_count} nguồn</Badge>
                  </div>
                )}
              </div>
              <div className="grid gap-6 sm:grid-cols-2">
                {loading || !data
                  ? Array.from({ length: 4 }, (_, i) => <ListingCardSkeleton key={i} />)
                  : data.items.map((l, i) => <ListingCard key={l.id} l={l} i={i} onHover={setHover} active={hover === l.id} />)}
              </div>
              {data && data.pages > 1 && (
                <div className="flex justify-center gap-2 pt-2">
                  {Array.from({ length: data.pages }, (_, i) => i + 1)
                    .filter((p) => p <= 3 || p === data.pages || Math.abs(p - page) <= 1)
                    .map((p, idx, arr) => (
                      <span key={p} className="flex gap-2">
                        {idx > 0 && p - arr[idx - 1] > 1 && <span className="flex h-10 w-6 items-center justify-center text-ink-3">…</span>}
                        <button
                          onClick={() => (setFilters(f), setPage(p), window.scrollTo({ top: 0, behavior: "smooth" }))}
                          className={clsx("h-10 w-10 rounded-md text-sm font-semibold", p === page ? "bg-primary text-on-primary" : "border border-line bg-surface")}
                        >
                          {p}
                        </button>
                      </span>
                    ))}
                </div>
              )}
            </div>
            <div className={clsx("lg:block", mobileMap ? "block" : "hidden")}>
              <div className="sticky top-24 h-[calc(100vh-160px)] min-h-[480px] overflow-hidden rounded-xl border border-line">
                {data ? (
                  <MapView
                    className="h-full w-full"
                    pins={data.pins}
                    activeId={hover}
                    onPinClick={(id) => nav(`/phong/${id}`)}
                    school={data.school}
                    radiusKm={f.school_id ? f.max_distance_km : null}
                  />
                ) : (
                  <div className="skeleton h-full w-full" />
                )}
              </div>
            </div>
          </div>
        )}
      </div>
      <button
        onClick={() => setMobileMap((m) => !m)}
        className="fixed bottom-24 left-1/2 z-30 flex -translate-x-1/2 items-center gap-2 rounded-full bg-ink px-5 py-3 text-sm font-semibold text-canvas shadow-lg lg:hidden"
      >
        {mobileMap ? <List className="h-4 w-4" /> : <MapIcon className="h-4 w-4" />} {mobileMap ? "Danh sách" : "Bản đồ"}
      </button>
      <FilterPanel open={panel} value={f} total={data?.total} onClose={() => setPanel(false)} onApply={apply} />
    </StudentLayout>
  );
}
