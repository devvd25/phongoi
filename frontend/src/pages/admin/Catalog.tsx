import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Dialog } from "../../components/Dialog";
import { DashboardLayout, Table } from "../../components/Dashboard";
import { Badge, Button, Card, Chip, Field, Select, Spinner, TextArea, Toggle, useToast } from "../../components/ui";
import { api } from "../../lib/api";
import { num, tr } from "../../lib/format";

type Tab = "amenities" | "districts" | "schools" | "scam";
const words = (s: string) => s.split(/[,\n]/).map((w) => w.trim()).filter(Boolean);
const ADD_LABEL: Record<Tab, string> = { amenities: "Thêm tiện ích", districts: "", schools: "Thêm trường", scam: "Thêm từ khóa" };

function AddDialog({ tab, open, onClose, districts }: { tab: Tab; open: boolean; onClose: () => void; districts: string[] }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [f, setF] = useState<Record<string, string>>({});
  useEffect(() => {
    open && setF({ district: districts[0] ?? "" });
  }, [open, tab]);
  const set = (k: string) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  const m = useMutation({
    mutationFn: () => {
      if (tab === "amenities") return api("/admin/catalog/amenities", { body: { label: f.label, synonyms: words(f.synonyms ?? "") } });
      if (tab === "scam") return api("/admin/catalog/scam-keywords", { body: { keyword: f.keyword } });
      return api("/admin/catalog/schools", {
        body: { name: f.name, short_name: f.short_name, district: f.district, lat: Number(f.lat), lng: Number(f.lng), aliases: words(f.aliases ?? "") },
      });
    },
    onSuccess: () => (toast("Đã thêm vào danh mục"), qc.invalidateQueries({ queryKey: ["ad-cat"] }), qc.invalidateQueries({ queryKey: ["catalog"] }), onClose()),
    onError: (e: any) => toast(e.message, "danger"),
  });
  const title = ADD_LABEL[tab];
  return (
    <Dialog open={open} onClose={onClose} onSubmit={() => m.mutate()} busy={m.isPending} title={title} submitLabel="Thêm">
      {tab === "amenities" && (
        <>
          <Field label="Tên tiện ích" required minLength={2} value={f.label ?? ""} onChange={set("label")} placeholder="VD: Thang máy" />
          <TextArea label="Từ đồng nghĩa, cách nhau bởi dấu phẩy" value={f.synonyms ?? ""} onChange={set("synonyms")} placeholder="có thang máy, thang may, elevator" />
          <p className="caption">Bộ trích xuất và ô tìm kiếm AI sẽ nhận ra tiện ích qua các từ này ngay sau khi lưu. Tin cũ được cập nhật ở lần xử lý lại kế tiếp.</p>
        </>
      )}
      {tab === "scam" && (
        <>
          <Field label="Từ khóa" required minLength={3} value={f.keyword ?? ""} onChange={set("keyword")} placeholder="VD: đặt cọc qua zalo" />
          <p className="caption">Tin chứa từ khóa này bị cộng điểm rủi ro khi chấm lại. Không phân biệt dấu và chữ hoa.</p>
        </>
      )}
      {tab === "schools" && (
        <>
          <Field label="Tên trường" required minLength={3} value={f.name ?? ""} onChange={set("name")} placeholder="VD: Trường ĐH Kiến trúc Đà Nẵng" />
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Tên viết tắt" required minLength={2} value={f.short_name ?? ""} onChange={set("short_name")} placeholder="VD: ĐH Kiến trúc" />
            <Select label="Khu vực" value={f.district ?? ""} onChange={set("district")}>
              {districts.map((d) => <option key={d}>{d}</option>)}
            </Select>
            <Field label="Vĩ độ" required type="number" step="any" min={15.8} max={16.3} value={f.lat ?? ""} onChange={set("lat")} placeholder="16.0322" />
            <Field label="Kinh độ" required type="number" step="any" min={107.8} max={108.4} value={f.lng ?? ""} onChange={set("lng")} placeholder="108.2210" />
          </div>
          <Field label="Tên gọi khác, cách nhau bởi dấu phẩy" value={f.aliases ?? ""} onChange={set("aliases")} placeholder="kiến trúc, dau" />
          <p className="caption">Lấy tọa độ bằng cách bấm chuột phải vào cổng trường trên bản đồ. Tọa độ phải nằm trong Đà Nẵng.</p>
        </>
      )}
    </Dialog>
  );
}

function SynonymDialog({ item, onClose }: { item: any | null; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [text, setText] = useState("");
  useEffect(() => {
    item && setText(item.synonyms.join(", "));
  }, [item]);
  const refresh = () => (qc.invalidateQueries({ queryKey: ["ad-cat"] }), qc.invalidateQueries({ queryKey: ["catalog"] }));
  const save = useMutation({
    mutationFn: () => api(`/admin/catalog/amenities/${item.key}`, { method: "PUT", body: { synonyms: words(text) } }),
    onSuccess: () => (toast("Đã cập nhật từ đồng nghĩa"), refresh(), onClose()),
    onError: (e: any) => toast(e.message, "danger"),
  });
  const del = useMutation({
    mutationFn: () => api(`/admin/catalog/amenities/${item.key}`, { method: "DELETE" }),
    onSuccess: () => (toast(`Đã xóa tiện ích ${item.label}`), refresh(), onClose()),
    onError: (e: any) => toast(e.message, "danger"),
  });
  return (
    <Dialog
      open={!!item}
      onClose={onClose}
      onSubmit={() => save.mutate()}
      busy={save.isPending}
      title={item ? `Từ đồng nghĩa · ${item.label}` : ""}
      sub={item?.custom ? "Tiện ích do quản trị viên thêm" : "Tiện ích gốc: chỉ thêm được từ mới, từ gốc luôn được giữ"}
      danger={item?.custom && (
        <Button type="button" variant="ghost" className="text-danger" icon={<Trash2 className="h-4 w-4" />} loading={del.isPending} onClick={() => confirm(`Xóa tiện ích ${item.label}?`) && del.mutate()}>Xóa tiện ích</Button>
      )}
    >
      <TextArea label="Từ đồng nghĩa, cách nhau bởi dấu phẩy" value={text} onChange={(e) => setText(e.target.value)} rows={4} />
    </Dialog>
  );
}

export default function AdminCatalog() {
  const qc = useQueryClient();
  const toast = useToast();
  const [tab, setTab] = useState<Tab>("amenities");
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<any | null>(null);
  const { data } = useQuery<any>({ queryKey: ["ad-cat"], queryFn: () => api("/admin/catalog") });
  const toggle = useMutation({ mutationFn: (b: any) => api("/admin/catalog/amenity", { method: "PUT", body: b }), onSuccess: () => qc.invalidateQueries({ queryKey: ["ad-cat"] }) });
  const delKw = useMutation({
    mutationFn: (k: string) => api(`/admin/catalog/scam-keywords/${encodeURIComponent(k)}`, { method: "DELETE" }),
    onSuccess: () => (toast("Đã xóa từ khóa"), qc.invalidateQueries({ queryKey: ["ad-cat"] })),
    onError: (e: any) => toast(e.message, "danger"),
  });
  const right = tab !== "districts" && <Button icon={<Plus className="h-4 w-4" />} onClick={() => setAdding(true)}>{ADD_LABEL[tab]}</Button>;
  if (!data) return <DashboardLayout role="admin" title="Danh mục dữ liệu"><Spinner /></DashboardLayout>;
  const districts: string[] = data.districts.map((d: any) => d.district);

  return (
    <DashboardLayout role="admin" title="Danh mục dữ liệu" sub="Dùng cho trích xuất LLM, bộ lọc tìm kiếm và Elasticsearch" right={right}>
      <AddDialog tab={tab} open={adding} onClose={() => setAdding(false)} districts={districts} />
      <SynonymDialog item={editing} onClose={() => setEditing(null)} />
      <div className="flex flex-wrap gap-2">
        {([["amenities", `Tiện ích · ${data.amenities.length}`], ["districts", `Khu vực · ${data.districts.length}`], ["schools", `Trường đại học · ${data.schools.length}`], ["scam", `Từ khóa lừa đảo · ${data.scam_keywords.length}`]] as [Tab, string][]).map(([k, l]) => (
          <Chip key={k} state={tab === k ? "selected" : "default"} onClick={() => setTab(k)}>{l}</Chip>
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <Card pad="p-6" className="min-w-0">
          {tab === "amenities" && (
            <Table head={["Tiện ích", "Từ đồng nghĩa (LLM và tìm kiếm)", "Số tin", "Hiện bộ lọc", ""]} widths={["", "", "", "", "56px"]}>
              {data.amenities.map((a: any) => (
                <tr key={a.key}>
                  <td className="px-4 py-3 font-semibold">{a.label}{a.custom && <Badge tone="Violet" className="ml-2">Mới</Badge>}</td>
                  <td className="px-4 text-ink-2">{a.synonyms.join(", ")}</td>
                  <td className="px-4">{num(a.count)}</td>
                  <td className="px-4"><Toggle checked={a.in_filter} onChange={(v) => toggle.mutate({ key: a.key, in_filter: v })} label={`Hiện ${a.label}`} /></td>
                  <td className="px-2"><button onClick={() => setEditing(a)} aria-label={`Sửa ${a.label}`} className="rounded-md p-2 text-ink-2 hover:bg-muted"><Pencil className="h-4 w-4" /></button></td>
                </tr>
              ))}
            </Table>
          )}
          {tab === "districts" && (
            <>
              <Table head={["Khu vực", "Số tin", "Giá trung vị", "Khoảng phổ biến"]}>
                {data.districts.map((d: any) => <tr key={d.district}><td className="px-4 py-3 font-semibold">{d.district}</td><td className="px-4">{num(d.count)}</td><td className="px-4">{tr(d.median)}</td><td className="px-4 text-ink-2">{tr(d.p25)} – {tr(d.p75)}</td></tr>)}
              </Table>
              <p className="caption mt-4">Danh sách quận, huyện của Đà Nẵng cố định theo địa giới hành chính, giá thống kê tự cập nhật từ tin đăng.</p>
            </>
          )}
          {tab === "schools" && (
            <Table head={["Trường", "Tên viết tắt", "Khu vực", "Vĩ độ", "Kinh độ"]}>
              {data.schools.map((s: any) => <tr key={s.id}><td className="px-4 py-3 font-semibold">{s.name}</td><td className="px-4 text-ink-2">{s.short_name}</td><td className="px-4">{s.district}</td><td className="px-4">{s.lat}</td><td className="px-4">{s.lng}</td></tr>)}
            </Table>
          )}
          {tab === "scam" && (
            <div className="flex flex-wrap gap-2">
              {data.scam_keywords.map((k: any) => <Chip key={k.keyword} state={k.custom ? "ai" : "default"} onRemove={k.custom ? () => delKw.mutate(k.keyword) : undefined}>{k.keyword}</Chip>)}
            </div>
          )}
        </Card>
        <div className="space-y-6">
          <Card pad="px-6 pt-6 pb-2">
            <h2 className="text-h4">Trường đại học · {data.schools.length}</h2>
            {data.schools.slice(0, 5).map((s: any) => <div key={s.id} className="border-t border-line py-3 first-of-type:mt-3"><div className="text-sm font-semibold">{s.name}</div><div className="caption">{s.lat} · {s.lng}</div></div>)}
          </Card>
          <Card className="space-y-3">
            <h2 className="text-h4">Từ khóa lừa đảo · {data.scam_keywords.length}</h2>
            <p className="caption">Dùng làm đặc trưng cho mô hình chấm rủi ro. Từ khóa tím do quản trị viên thêm và có thể xóa.</p>
            <div className="flex flex-wrap gap-2">{data.scam_keywords.slice(0, 6).map((k: any) => <Chip key={k.keyword} state={k.custom ? "ai" : "default"}>{k.keyword}</Chip>)}</div>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
