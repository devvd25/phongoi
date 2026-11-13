import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, ArrowRight, BarChart3, Check, Sparkles, Upload, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { DashboardLayout } from "../../components/Dashboard";
import { useCatalog } from "../../components/FilterPanel";
import { ListingCard, RoomPhoto } from "../../components/ListingCard";
import { Button, Card, Chip, Field, Select, Spinner, TextArea, useToast } from "../../components/ui";
import { api } from "../../lib/api";
import { shortVnd } from "../../lib/format";

const EMPTY = { title: "", description: "", price: "", area: "", district: "Liên Chiểu", street: "", address: "", room_type: "phong_tro", max_people: "2", deposit_months: "1", electricity_price: "", water_price: "", amenities: [] as string[], images: [] as string[] };

const str = (v: unknown) => (v == null ? "" : String(v));

export default function LandlordPost() {
  const [params] = useSearchParams();
  const editId = Number(params.get("id")) || null;
  const { data: cat } = useCatalog();
  const toast = useToast();
  const nav = useNavigate();
  const qc = useQueryClient();
  const [raw, setRaw] = useState("");
  const [f, setF] = useState(EMPTY);
  const [chips, setChips] = useState<string[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);
  const set = (p: Partial<typeof EMPTY>) => setF((s) => ({ ...s, ...p }));
  const room = useQuery<any>({ queryKey: ["ll-room", editId], queryFn: () => api(`/landlord/rooms/${editId}`), enabled: !!editId });
  useEffect(() => {
    const r = room.data;
    if (!r) return;
    setF({
      title: r.title, description: r.description ?? "", price: str(r.price), area: str(r.area), district: r.district, street: r.street ?? "", address: r.address ?? "",
      room_type: r.room_type, max_people: str(r.max_people), deposit_months: str(r.deposit_months), electricity_price: str(r.electricity_price),
      water_price: str(r.water_price), amenities: r.amenities ?? [], images: r.images ?? [],
    });
  }, [room.data]);
  useEffect(() => {
    // Mở từ gợi ý "Thêm ảnh": cuộn tới khu vực ảnh sau khi tải xong.
    if (room.data && params.get("muc") === "anh") document.getElementById("hinh-anh")?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [room.data]);

  const autofill = useMutation<any>({
    mutationFn: () => api("/landlord/autofill", { body: { text: raw } }),
    onSuccess: (r) => {
      const x = r.fields;
      set({
        title: x.title || f.title, description: raw, price: x.price ? String(x.price) : f.price, area: x.area ? String(x.area) : f.area,
        district: x.district ?? f.district, street: x.street ?? "", address: x.address ?? f.address, room_type: x.room_type,
        max_people: x.max_people ? String(x.max_people) : f.max_people, deposit_months: x.deposit_months != null ? String(x.deposit_months) : f.deposit_months,
        electricity_price: x.electricity_price ? String(x.electricity_price) : "", water_price: x.water_price ? String(x.water_price) : "",
        amenities: Array.from(new Set([...f.amenities, ...x.amenities])),
      });
      setChips(r.chips);
      toast(x.missing.length ? `AI đã điền, còn thiếu: ${x.missing.join(", ")}` : "AI đã điền đầy đủ thông tin", "info");
    },
  });
  const price = useMutation<any>({ mutationFn: () => api("/landlord/price-check", { body: { district: f.district, area: Number(f.area) || null, amenities: f.amenities, room_type: f.room_type, price: Number(f.price) || null } }) });
  useEffect(() => {
    const t = setTimeout(() => f.district && price.mutate(), 500);
    return () => clearTimeout(t);
  }, [f.district, f.area, f.price, f.amenities.length, f.room_type]);

  const upload = useMutation<any, Error, FileList>({
    mutationFn: (files) => {
      const fd = new FormData();
      Array.from(files).forEach((x) => fd.append("files", x));
      return api("/landlord/upload", { form: fd });
    },
    onSuccess: (r) => set({ images: [...f.images, ...r.urls].slice(0, 12) }),
    onError: (e) => toast(e.message, "danger"),
  });
  const submit = useMutation({
    mutationFn: () => {
      const body = { ...f, price: Number(f.price), area: Number(f.area) || null, max_people: Number(f.max_people) || null, deposit_months: Number(f.deposit_months), electricity_price: Number(f.electricity_price) || null, water_price: Number(f.water_price) || null, address: f.address || f.street || f.district, street: f.street || null };
      return editId ? api(`/landlord/rooms/${editId}`, { method: "PATCH", body }) : api("/landlord/rooms", { body });
    },
    onSuccess: () => (toast(editId ? "Đã lưu thay đổi tin đăng" : "Đã gửi tin, Phòng Ơi sẽ duyệt trong vòng 2 giờ"), qc.invalidateQueries(), nav("/chu-tro/phong")),
    onError: (e: any) => toast(e.message, "danger"),
  });

  const checks = [
    [f.description.split(/\s+/).filter(Boolean).length >= 30, "Mô tả rõ ràng, đủ chi tiết"],
    [!!f.electricity_price && !!f.water_price, "Đủ giá điện, nước"],
    [!!f.address || !!f.street, "Có địa chỉ cụ thể"],
    [f.images.length >= 5, `Ít nhất 5 ảnh (hiện có ${f.images.length})`],
  ] as const;
  const quality = Math.round((4 + checks.filter((c) => c[0]).length * 1.5) * 10) / 10;
  const preview: any = {
    id: 0, title: f.title || "Tiêu đề tin của bạn", price: Number(f.price) || 0, area: Number(f.area) || null, district: f.district, short_address: f.street ? `${f.street}, ${f.district}` : f.district,
    image: f.images[0] ?? "/rooms/room-1.jpg", images: f.images, source_count: 1, match: null, price_tag: price.data?.verdict === "ok" ? "Giá tốt" : null,
    meta: [f.area && `${f.area} m²`, f.amenities.includes("gac_lung") && "Gác lửng"].filter(Boolean).join(" · "), risk_level: "low", quality_score: quality, posted_at: new Date().toISOString(),
  };
  const ok = f.title.length >= 5 && Number(f.price) >= 300_000 && (f.address || f.street);
  const title = editId ? "Sửa tin đăng" : "Đăng tin mới";
  if (editId && room.isLoading) return <DashboardLayout role="landlord" title={title}><Spinner /></DashboardLayout>;
  if (editId && room.isError) return <DashboardLayout role="landlord" title={title}><Card>Không tìm thấy phòng này. <Button variant="ghost" to="/chu-tro/phong">Về danh sách phòng</Button></Card></DashboardLayout>;

  return (
    <DashboardLayout
      role="landlord"
      title={title}
      sub={editId ? `${room.data?.status_label} · thay đổi được cập nhật ngay trên trang sinh viên` : "Tin của bạn được duyệt trong vòng 2 giờ · miễn phí"}
      right={<Button loading={submit.isPending} disabled={!ok} onClick={() => submit.mutate()} iconRight={<ArrowRight className="h-4 w-4" />}>{editId ? "Lưu thay đổi" : "Gửi duyệt"}</Button>}
    >
      <div className="grid gap-6 xl:grid-cols-[1fr_340px]">
        <div className="space-y-5">
          <div className="space-y-3 rounded-xl border border-dashed border-violet bg-violet-50 p-6">
            <div className="flex items-center gap-2 text-h4 text-violet"><Sparkles className="h-5 w-5" /> Điền nhanh bằng AI</div>
            <p className="text-sm text-ink-2">Dán nội dung tin bạn từng đăng trên Facebook hoặc Zalo, AI sẽ tự tách giá, diện tích, tiện ích và địa chỉ.</p>
            <textarea value={raw} onChange={(e) => setRaw(e.target.value)} rows={4} placeholder="Cho thuê phòng kiệt 45 Ngô Sĩ Liên, 22m2 có gác, máy lạnh, wc riêng. Giá 2tr2, điện 3k5, nước 100k/người, cọc 1 tháng…" className="w-full rounded-md border border-line bg-surface p-3 text-sm focus:border-primary focus:outline-none" />
            <div className="flex flex-wrap items-center gap-2">
              <Button variant="secondary" loading={autofill.isPending} disabled={raw.trim().length < 10} onClick={() => autofill.mutate()} iconRight={<ArrowRight className="h-4 w-4" />}>Tự điền bằng AI</Button>
              {chips.length > 0 && <span className="text-[13px] font-semibold text-violet">Đã nhận diện:</span>}
              {chips.map((c) => <Chip key={c} state="ai">{c}</Chip>)}
            </div>
          </div>
          <Card className="space-y-4">
            <h2 className="text-h4">Thông tin cơ bản</h2>
            <Field label="Tiêu đề tin" value={f.title} onChange={(e) => set({ title: e.target.value })} placeholder="Phòng gác lửng full nội thất, cửa sổ thoáng" />
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Giá thuê / tháng (đồng)" inputMode="numeric" value={f.price} onChange={(e) => set({ price: e.target.value.replace(/\D/g, "") })} helper={f.price ? shortVnd(Number(f.price)) : undefined} />
              <Field label="Diện tích (m²)" inputMode="numeric" value={f.area} onChange={(e) => set({ area: e.target.value })} />
              <Select label="Loại phòng" value={f.room_type} onChange={(e) => set({ room_type: e.target.value })}>{cat?.room_types.map((r) => <option key={r.key} value={r.key}>{r.label}</option>)}</Select>
              <Field label="Số người tối đa" inputMode="numeric" value={f.max_people} onChange={(e) => set({ max_people: e.target.value })} />
              <Field label="Tiền cọc (tháng)" inputMode="numeric" value={f.deposit_months} onChange={(e) => set({ deposit_months: e.target.value })} />
              <Field label="Giá điện (đồng/kWh)" inputMode="numeric" value={f.electricity_price} onChange={(e) => set({ electricity_price: e.target.value })} />
              <Field label="Giá nước (đồng/người)" inputMode="numeric" value={f.water_price} onChange={(e) => set({ water_price: e.target.value })} />
            </div>
            <TextArea label="Mô tả" value={f.description} onChange={(e) => set({ description: e.target.value })} rows={4} />
          </Card>
          <Card className="space-y-4">
            <h2 className="text-h4">Địa chỉ</h2>
            <div className="grid gap-4 sm:grid-cols-[200px_1fr]">
              <Select label="Khu vực" value={f.district} onChange={(e) => set({ district: e.target.value })}>{cat?.districts.map((d) => <option key={d}>{d}</option>)}</Select>
              <Field label="Địa chỉ" value={f.address} onChange={(e) => set({ address: e.target.value })} placeholder="Kiệt 45 Ngô Sĩ Liên, Hòa Khánh Bắc" />
            </div>
            <p className="caption">Vị trí trên bản đồ giúp sinh viên thấy khoảng cách tới trường.</p>
          </Card>
          <Card className="space-y-4">
            <h2 className="text-h4">Tiện ích</h2>
            <div className="flex flex-wrap gap-2">
              {cat?.amenities.map((a) => <Chip key={a.key} state={f.amenities.includes(a.key) ? "selected" : "default"} onClick={() => set({ amenities: f.amenities.includes(a.key) ? f.amenities.filter((x) => x !== a.key) : [...f.amenities, a.key] })}>{a.label}</Chip>)}
            </div>
          </Card>
          <Card className="space-y-4" id="hinh-anh">
            <h2 className="text-h4">Hình ảnh · {f.images.length}/12</h2>
            <div className="flex flex-wrap gap-3">
              {f.images.map((src) => (
                <div key={src} className="relative">
                  <RoomPhoto src={src} alt="" className="h-24 w-32 rounded-md" />
                  <button aria-label="Xóa ảnh" onClick={() => set({ images: f.images.filter((x) => x !== src) })} className="absolute right-1 top-1 rounded-full bg-black/60 p-1 text-white"><X className="h-3 w-3" /></button>
                </div>
              ))}
              <button onClick={() => fileRef.current?.click()} className="flex h-24 w-36 flex-col items-center justify-center gap-1 rounded-md border-[1.5px] border-dashed border-primary bg-primary-50 text-[13px] font-semibold text-primary-700">
                <Upload className="h-5 w-5" /> {upload.isPending ? "Đang tải…" : "Thêm ảnh"}
              </button>
              <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp" multiple hidden onChange={(e) => e.target.files?.length && upload.mutate(e.target.files)} />
            </div>
            <p className="caption">Tối đa 12 ảnh, mỗi ảnh không quá 5 MB · nên có ảnh WC, bếp và lối đi</p>
          </Card>
        </div>
        <aside className="space-y-4 xl:sticky xl:top-6 xl:self-start">
          <div className="text-sm font-semibold text-ink-2">Xem trước trên trang sinh viên</div>
          <div className="pointer-events-none"><ListingCard l={preview} /></div>
          <Card pad="p-5" className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-semibold"><BarChart3 className="h-[18px] w-[18px] text-primary" /> Giá đề xuất từ AI</div>
            <div className="text-h2 text-primary-700">{price.data ? `${shortVnd(price.data.low).replace(" triệu", "")} – ${shortVnd(price.data.high)}` : "—"}</div>
            {price.data?.verdict && (
              <div className={`flex items-center gap-1.5 text-sm ${price.data.verdict === "ok" ? "text-success" : "text-warning"}`}>
                {price.data.verdict === "ok" ? <Check className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
                {price.data.verdict === "ok" ? "Giá bạn nhập nằm trong khoảng hợp lý" : price.data.verdict === "high" ? "Giá cao hơn mặt bằng, phòng có thể lâu cho thuê" : "Giá thấp bất thường, có thể bị đánh dấu rủi ro"}
              </div>
            )}
          </Card>
          <Card pad="p-5" className="space-y-3">
            <div className="flex items-center justify-between"><span className="text-sm font-semibold">Điểm chất lượng dự kiến</span><span className="text-h4 text-primary-700">{String(quality).replace(".", ",")}/10</span></div>
            {checks.map(([okk, l]) => (
              <div key={l} className={`flex items-center gap-2 text-sm ${okk ? "" : "text-warning"}`}>{okk ? <Check className="h-4 w-4 text-success" /> : <AlertCircle className="h-4 w-4" />} {l}</div>
            ))}
          </Card>
        </aside>
      </div>
    </DashboardLayout>
  );
}
