import clsx from "clsx";
import { Link } from "react-router-dom";

/** Ảnh logo theo giao diện: bản chữ navy cho nền sáng, bản chữ sáng cho nền tối. */
export function LogoImage({ variant = "default", className }: { variant?: "default" | "full" | "mark"; className?: string }) {
  const name = { default: "logo", full: "logo-full", mark: "logo-mark" }[variant];
  const alt = variant === "full" ? "Phòng Ơi – Tìm trọ cho sinh viên" : "Phòng Ơi";
  return (
    <>
      <img src={`/brand/${name}.png`} alt={alt} className={clsx("block w-auto dark:hidden", className)} draggable={false} />
      <img src={`/brand/${name}-dark.png`} alt={alt} className={clsx("hidden w-auto dark:block", className)} draggable={false} />
    </>
  );
}

export function Logo({ to = "/", className, variant = "default", size = "h-10" }: { to?: string; className?: string; variant?: "default" | "full" | "mark"; size?: string }) {
  return (
    <Link to={to} className={clsx("focus-ring inline-flex shrink-0 items-center rounded-md", className)} aria-label="Phòng Ơi – trang chủ">
      <LogoImage variant={variant} className={size} />
    </Link>
  );
}

/** Nền Aurora dịu: hai vùng màu đào nhạt và tím nhạt trôi chậm ở nửa phải, phần chữ bên trái giữ sạch. */
export function Aurora({ className, intensity = 1 }: { className?: string; intensity?: number }) {
  return (
    <div aria-hidden className={clsx("pointer-events-none absolute inset-0 -z-10 overflow-hidden", className)}>
      <div className="absolute -left-40 -top-72 h-[520px] w-[760px] rounded-full blur-[110px]" style={{ background: "rgb(var(--aurora-3))", opacity: 0.55 * intensity }} />
      <div className="absolute -top-56 right-[-120px] h-[560px] w-[720px] animate-drift rounded-full blur-[120px]" style={{ background: "rgb(var(--aurora-1))", opacity: 0.42 * intensity }} />
      <div className="absolute right-[-240px] top-56 h-[520px] w-[620px] animate-drift rounded-full blur-[120px] [animation-delay:-9s]" style={{ background: "rgb(var(--aurora-2))", opacity: 0.34 * intensity }} />
    </div>
  );
}
