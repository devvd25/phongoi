export const shortVnd = (v?: number | null) => {
  if (v == null) return "—";
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1).replace(/\.0$/, "").replace(".", ",")} triệu`;
  return `${Math.round(v / 1000)} nghìn`;
};

export const tr = (v?: number | null) => (v == null ? "—" : `${(v / 1_000_000).toFixed(1).replace(".", ",")} tr`);

export const fullVnd = (v?: number | null) => (v == null ? "—" : `${Math.round(v).toLocaleString("vi-VN")}đ`);

export const num = (v?: number | null) => (v == null ? "—" : v.toLocaleString("vi-VN"));

export const km = (v?: number | null) => (v == null ? "" : `${v.toFixed(1).replace(".", ",")} km`);

export function timeAgo(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "vừa xong";
  if (diff < 3600) return `${Math.floor(diff / 60)} phút trước`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} giờ trước`;
  if (diff < 172800) return "Hôm qua";
  if (diff < 30 * 86400) return `${Math.floor(diff / 86400)} ngày trước`;
  return new Date(iso).toLocaleDateString("vi-VN");
}

export const riskLabel: Record<string, string> = { low: "Rủi ro thấp", medium: "Cần lưu ý", high: "Rủi ro cao" };
export const riskTone: Record<string, "Success" | "Warning" | "Danger"> = { low: "Success", medium: "Warning", high: "Danger" };
