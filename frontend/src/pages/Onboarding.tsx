import { useMutation, useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { motion } from "framer-motion";
import { ArrowRight, BarChart3, Check, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Aurora, Logo } from "../components/Brand";
import { useCatalog } from "../components/FilterPanel";
import { Button, Chip, Select, useToast } from "../components/ui";
import { api } from "../lib/api";
import { shortVnd } from "../lib/format";
import type { Filters } from "../lib/types";

const STEPS = ["Trường học", "Ngân sách", "Kiểu phòng", "Sinh hoạt"];
const TRANSPORT = [["di_bo", "Đi bộ"], ["xe_dap", "Xe đạp"], ["xe_may", "Xe máy"], ["xe_buyt", "Xe buýt"]] as const;

type NeedsProfile = Omit<Filters, "budget_min" | "budget_max" | "school_id" | "max_distance_km" | "max_people"> & {
  budget_min: number;
  budget_max: number;
  school_id: number;
  max_distance_km: number;
  max_people: number;
  transport: string;
  move_in: string;
};
type ParseResponse = { filters: Filters; chips: string[] };

const DEFAULT_PROFILE: NeedsProfile = {
  school_id: 1,
  max_distance_km: 2,
  budget_min: 1_500_000,
  budget_max: 2_500_000,
  room_types: ["phong_tro"],
  amenities: [],
  max_people: 2,
  transport: "xe_may",
  move_in: "tháng 9",
  districts: [],
  hide_high_risk: true,
  sort: "match",
};

export default function Onboarding() {
  const nav = useNavigate();
  const toast = useToast();
  const { data: cat } = useCatalog();
  const { data: cur } = useQuery<Partial<NeedsProfile>>({ queryKey: ["needs"], queryFn: () => api("/me/needs") });
  const { data: market } = useQuery<{ city_median: number }>({ queryKey: ["market"], queryFn: () => api("/market/overview") });
  const [step, setStep] = useState(0);
  const [nl, setNl] = useState("");
  const [p, setP] = useState<NeedsProfile>(DEFAULT_PROFILE);
  useEffect(() => {
    cur && setP((s) => ({ ...s, ...Object.fromEntries(Object.entries(cur).filter(([, v]) => v != null)) }));
  }, [cur]);
  const set = (x: Partial<NeedsProfile>) => setP((s) => ({ ...s, ...x }));
  const { data: count } = useQuery<{ total: number }>({
    queryKey: ["onb-count", p.budget_min, p.budget_max, p.school_id, p.max_distance_km],
    queryFn: () => api("/search", { body: { filters: { budget_min: p.budget_min, budget_max: p.budget_max, school_id: p.school_id, max_distance_km: p.max_distance_km, districts: [], amenities: [], room_types: [], hide_high_risk: true, sort: "match" }, page_size: 1 } }),
  });
  const save = useMutation({ mutationFn: () => api("/me/needs", { method: "PUT", body: p }), onSuccess: () => (toast("Đã lưu hồ sơ nhu cầu"), nav("/goi-y")) });
  const parse = useMutation<ParseResponse>({
    mutationFn: () => api("/search/parse", { body: { query: nl } }),
    onSuccess: (r) => {
      const f = r.filters;
      set({ ...(f.budget_max && { budget_max: f.budget_max }), ...(f.budget_min && { budget_min: f.budget_min }), ...(f.school_id && { school_id: f.school_id, max_distance_km: f.max_distance_km ?? p.max_distance_km }), ...(f.amenities.length && { amenities: f.amenities }), ...(f.room_types.length && { room_types: f.room_types }), ...(f.max_people && { max_people: f.max_people }) });
      toast(`AI đã điền: ${r.chips.join(", ")}`, "info");
    },
  });

  // Biểu đồ phân bố giá (mô phỏng từ trung vị các khu vực) cho thanh trượt ngân sách.
  const hist = useMemo(() => Array.from({ length: 20 }, (_, i) => Math.round(80 * Math.exp(-((i - 6.5) ** 2) / 18) + 4)), []);
  const MIN = 800_000, MAX = 4_000_000;
  const pct = (v: number) => ((v - MIN) / (MAX - MIN)) * 100;
  const toggle = (k: "room_types" | "amenities", v: string) => set({ [k]: p[k].includes(v) ? p[k].filter((x) => x !== v) : [...p[k], v] });

  return (
    <div className="relative isolate min-h-screen">
      <Aurora intensity={0.9} />
      <div className="container-page flex h-[72px] items-center justify-between"><Logo /><Button variant="ghost" to="/">Bỏ qua, xem phòng ngay</Button></div>
      <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} className="mx-auto mb-16 mt-4 max-w-[880px] space-y-7 rounded-2xl border border-line bg-surface/90 p-6 shadow-lg backdrop-blur-xl sm:p-10">
        <div className="flex flex-wrap items-center gap-2">
          {STEPS.map((s, i) => (
            <div key={s} className="flex items-center gap-2">
              <span className={clsx("flex h-7 w-7 items-center justify-center rounded-full text-[13px] font-semibold", i < step ? "bg-success text-white" : i === step ? "bg-primary text-white" : "bg-muted text-ink-3")}>{i < step ? <Check className="h-4 w-4" /> : i + 1}</span>
              <span className={clsx("text-[13px] font-semibold", i > step && "text-ink-3")}>{s}</span>
              {i < STEPS.length - 1 && <span className={clsx("mx-1 h-0.5 w-8 sm:w-12", i < step ? "bg-success" : "bg-line")} />}
            </div>
          ))}
        </div>

        {step === 0 && (
          <div className="space-y-6">
            <div><div className="text-[13px] font-semibold text-primary">Bước 1/4</div><h1 className="mt-1 text-h2">Bạn đang học ở trường nào?</h1><p className="text-ink-2">Khoảng cách tới trường là tiêu chí quan trọng khi AI xếp hạng phòng.</p></div>
            <Select label="Trường của bạn" value={p.school_id ?? ""} onChange={(e) => set({ school_id: Number(e.target.value) })}>{cat?.schools.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</Select>
            <div><div className="label-s mb-2 text-ink-2">Khoảng cách tối đa</div><div className="flex flex-wrap gap-2">{[1, 2, 5, 10].map((k) => <Chip key={k} state={p.max_distance_km === k ? "selected" : "default"} onClick={() => set({ max_distance_km: k })}>{k === 10 ? "Không quan trọng" : `≤ ${k} km`}</Chip>)}</div></div>
            <div>
              <div className="label-s mb-2 text-ink-2">Bạn đi học bằng</div>
              <div className="grid grid-cols-4 gap-1 rounded-md bg-muted p-1">
                {TRANSPORT.map(([k, l]) => <button key={k} onClick={() => set({ transport: k })} className={clsx("rounded-sm py-2 text-[13px] font-semibold", p.transport === k ? "bg-surface shadow-sm" : "text-ink-2")}>{l}</button>)}
              </div>
            </div>
          </div>
        )}
        {step === 1 && (
          <div className="space-y-6">
            <div><div className="text-[13px] font-semibold text-primary">Bước 2/4</div><h1 className="mt-1 text-h2">Ngân sách mỗi tháng của bạn?</h1><p className="text-ink-2">AI dùng thông tin này để xếp hạng phòng phù hợp nhất. Bạn có thể đổi bất cứ lúc nào.</p></div>
            <div className="flex items-center justify-between"><span className="text-sm font-semibold">Ngân sách mỗi tháng</span><span className="text-h4 text-primary-700">{shortVnd(p.budget_min)} – {shortVnd(p.budget_max)}</span></div>
            <div className="relative">
              <div className="flex h-20 items-end gap-1">
                {hist.map((h, i) => { const v = MIN + ((i + 0.5) / 20) * (MAX - MIN); const on = v >= p.budget_min && v <= p.budget_max; return <div key={i} className={clsx("flex-1 rounded-t-sm transition-colors", on ? "bg-primary/85" : "bg-line")} style={{ height: `${h}%` }} />; })}
              </div>
              <div className="relative mt-2 h-6">
                <div className="absolute top-2.5 h-1.5 w-full rounded-full bg-muted" />
                <div className="absolute top-2.5 h-1.5 rounded-full bg-primary" style={{ left: `${pct(p.budget_min)}%`, width: `${pct(p.budget_max) - pct(p.budget_min)}%` }} />
                {(["budget_min", "budget_max"] as const).map((k) => (
                  <input key={k} type="range" min={MIN} max={MAX} step={100_000} value={p[k]} aria-label={k === "budget_min" ? "Ngân sách tối thiểu" : "Ngân sách tối đa"}
                    onChange={(e) => { const v = Number(e.target.value); set(k === "budget_min" ? { budget_min: Math.min(v, p.budget_max - 200_000) } : { budget_max: Math.max(v, p.budget_min + 200_000) }); }}
                    className="pointer-events-none absolute inset-0 w-full appearance-none bg-transparent [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:h-6 [&::-webkit-slider-thumb]:w-6 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:border-[3px] [&::-webkit-slider-thumb]:border-primary [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:shadow-md [&::-moz-range-thumb]:pointer-events-auto [&::-moz-range-thumb]:h-5 [&::-moz-range-thumb]:w-5 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-[3px] [&::-moz-range-thumb]:border-primary [&::-moz-range-thumb]:bg-white" />
                ))}
              </div>
            </div>
            <div className="flex items-center gap-2 text-[13px] text-ink-3"><BarChart3 className="h-4 w-4" /> Có {count?.total ?? "…"} phòng trong khoảng giá này gần trường bạn · trung vị Đà Nẵng {shortVnd(market?.city_median)}</div>
          </div>
        )}
        {step === 2 && (
          <div className="space-y-6">
            <div><div className="text-[13px] font-semibold text-primary">Bước 3/4</div><h1 className="mt-1 text-h2">Bạn thích kiểu phòng nào?</h1></div>
            <div><div className="label-s mb-2 text-ink-2">Loại phòng</div><div className="flex flex-wrap gap-2">{cat?.room_types.map((r) => <Chip key={r.key} state={p.room_types.includes(r.key) ? "selected" : "default"} onClick={() => toggle("room_types", r.key)}>{r.label}</Chip>)}</div></div>
            <div><div className="label-s mb-2 text-ink-2">Tiện ích cần có</div><div className="flex flex-wrap gap-2">{cat?.amenities.filter((a) => a.key !== "gio_tu_do").map((a) => <Chip key={a.key} state={p.amenities.includes(a.key) ? "selected" : "default"} onClick={() => toggle("amenities", a.key)}>{a.label}</Chip>)}</div></div>
          </div>
        )}
        {step === 3 && (
          <div className="space-y-6">
            <div><div className="text-[13px] font-semibold text-primary">Bước 4/4</div><h1 className="mt-1 text-h2">Thói quen sinh hoạt</h1></div>
            <div><div className="label-s mb-2 text-ink-2">Số người ở</div><div className="flex gap-2">{[1, 2, 3, 4].map((n) => <Chip key={n} state={p.max_people === n ? "selected" : "default"} onClick={() => set({ max_people: n })}>{n} người</Chip>)}</div></div>
            <div><div className="label-s mb-2 text-ink-2">Giờ giấc</div><Chip state={p.amenities.includes("gio_tu_do") ? "selected" : "default"} onClick={() => toggle("amenities", "gio_tu_do")}>Cần giờ giấc tự do</Chip></div>
            <div><div className="label-s mb-2 text-ink-2">Dự kiến chuyển vào</div><div className="flex flex-wrap gap-2">{["tháng 8", "tháng 9", "càng sớm càng tốt"].map((m) => <Chip key={m} state={p.move_in === m ? "selected" : "default"} onClick={() => set({ move_in: m })}>{m}</Chip>)}</div></div>
          </div>
        )}

        <div className="space-y-2 rounded-lg border border-dashed border-violet/40 bg-violet-50 p-4">
          <div className="flex items-center gap-2 text-[13px] font-semibold text-violet"><Sparkles className="h-4 w-4" /> Hoặc mô tả bằng một câu, AI tự điền giúp bạn</div>
          <div className="flex gap-2">
            <input value={nl} onChange={(e) => setNl(e.target.value)} placeholder="“Mình học Bách khoa, đi xe máy, muốn phòng có gác dưới 2,5 triệu, cho nấu ăn”" className="min-w-0 flex-1 bg-transparent text-[15px] placeholder:text-ink-3 focus:outline-none" />
            <Button variant="secondary" loading={parse.isPending} disabled={!nl.trim()} onClick={() => parse.mutate()}>Tự điền</Button>
          </div>
        </div>
        <div className="flex justify-between">
          <Button variant="ghost" size="l" disabled={step === 0} onClick={() => setStep(step - 1)}>Quay lại</Button>
          {step < 3 ? <Button size="l" onClick={() => setStep(step + 1)} iconRight={<ArrowRight className="h-4 w-4" />}>Tiếp tục</Button> : <Button size="l" loading={save.isPending} onClick={() => save.mutate()} iconRight={<ArrowRight className="h-4 w-4" />}>Xem gợi ý cho tôi</Button>}
        </div>
      </motion.div>
    </div>
  );
}
