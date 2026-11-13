import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, Pencil, Plus, Search, Send, Star } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { DashboardLayout } from "../../components/Dashboard";
import { RoomPhoto } from "../../components/ListingCard";
import { Badge, Button, Chip, Spinner, useToast, type Tone } from "../../components/ui";
import { api } from "../../lib/api";
import { fullVnd } from "../../lib/format";

type Room = { id: number; title: string; image?: string; status: string; status_tone: Tone; status_label: string; price: number; views: number; contacts: number; quality_score: number };
type RoomsResponse = { items: Room[]; counts: Record<string, number> };
type RoomPatch = { id: number; body: { refresh?: boolean; status?: string } };

export default function LandlordRooms() {
  const qc = useQueryClient();
  const toast = useToast();
  const [tab, setTab] = useState("all");
  const [q, setQ] = useState("");
  const { data } = useQuery<RoomsResponse>({ queryKey: ["ll-rooms"], queryFn: () => api("/landlord/rooms") });
  const patch = useMutation({
    mutationFn: ({ id, body }: RoomPatch) => api(`/landlord/rooms/${id}`, { method: "PATCH", body }),
    onSuccess: () => (toast("Đã cập nhật phòng"), qc.invalidateQueries({ queryKey: ["ll-rooms"] })),
  });
  const items = (data?.items ?? []).filter((r) => (tab === "all" || r.status === tab) && r.title.toLowerCase().includes(q.toLowerCase()));
  const c = data?.counts ?? {};

  return (
    <DashboardLayout role="landlord" title="Phòng của tôi" sub={`${c.all ?? 0} phòng · khu trọ Kiệt 45 Ngô Sĩ Liên, Liên Chiểu`} right={<Button to="/chu-tro/dang-tin" icon={<Plus className="h-4 w-4" />}>Đăng tin mới</Button>}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          {[["all", `Tất cả · ${c.all ?? 0}`], ["active", `Còn trống · ${c.active ?? 0}`], ["rented", `Đã cho thuê · ${c.rented ?? 0}`], ["pending", `Chờ duyệt · ${c.pending ?? 0}`]].map(([k, l]) => (
            <Chip key={k} state={tab === k ? "selected" : "default"} onClick={() => setTab(k)}>{l}</Chip>
          ))}
        </div>
        <label className="flex h-10 w-full items-center gap-2 rounded-full border border-line bg-surface px-4 sm:w-64">
          <Search className="h-4 w-4 text-ink-3" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Tìm theo tên phòng" className="min-w-0 flex-1 bg-transparent text-sm focus:outline-none" />
        </label>
      </div>
      {!data ? <Spinner /> : (
        <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((r) => (
            <div key={r.id} className="card overflow-hidden">
              <RoomPhoto src={r.image} alt={r.title} className="h-[170px] w-full" />
              <div className="space-y-3 p-4">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold">{r.title}</span>
                  <div className="flex items-center gap-1">
                    <Badge tone={r.status_tone as Tone} dot>{r.status_label}</Badge>
                    <Link to={`/chu-tro/dang-tin?id=${r.id}`} aria-label={`Sửa ${r.title}`} className="rounded-md p-1.5 text-ink-2 hover:bg-muted hover:text-ink"><Pencil className="h-4 w-4" /></Link>
                  </div>
                </div>
                <div className="flex items-baseline gap-1"><span className="text-h4 text-primary-700">{fullVnd(r.price)}</span><span className="caption">/tháng</span></div>
                <div className="flex gap-4 text-xs text-ink-2">
                  <span className="flex items-center gap-1"><Eye className="h-3.5 w-3.5" /> {r.status === "active" ? r.views : "—"} lượt xem</span>
                  <span className="flex items-center gap-1"><Send className="h-3.5 w-3.5" /> {r.status === "active" ? r.contacts : "—"} liên hệ</span>
                  <span className="flex items-center gap-1"><Star className="h-3.5 w-3.5" /> {String(r.quality_score).replace(".", ",")}/10</span>
                </div>
                <div className="flex gap-2 border-t border-line pt-3">
                  <Button variant="secondary" className="flex-1" onClick={() => patch.mutate({ id: r.id, body: { refresh: true } })}>Làm mới tin</Button>
                  {r.status === "active" && <Button variant="ghost" className="flex-1" onClick={() => patch.mutate({ id: r.id, body: { status: "rented" } })}>Đánh dấu đã thuê</Button>}
                  {r.status === "rented" && <Button variant="ghost" className="flex-1" onClick={() => patch.mutate({ id: r.id, body: { status: "active" } })}>Mở nhận khách</Button>}
                  {r.status === "pending" && <Button variant="ghost" className="flex-1" disabled>Đang chờ duyệt</Button>}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </DashboardLayout>
  );
}
