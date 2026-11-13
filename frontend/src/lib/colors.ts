/** Đọc token màu hiện hành (sáng/tối) cho thư viện biểu đồ, vì thuộc tính SVG không hiểu var(). */
export function col(name: string): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim();
  return v ? `rgb(${v.split(/\s+/).join(",")})` : "#EA580C";
}
