import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "../../components/ui";
import { AuthProvider } from "../../lib/auth";
import { api } from "../../lib/api";
import AdminSources from "./Sources";

vi.mock("../../lib/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("../../lib/api")>();
  return { ...original, api: vi.fn() };
});

const source = {
  id: 1,
  name: "Bộ tin mẫu",
  kind: "sample",
  start_url: "",
  frequency_minutes: 60,
  rate_limit: "1 yêu cầu / 2 giây",
  max_pages: 3,
  config: {},
  removable: false,
  enabled: true,
  status: "ok",
  last_run_at: null,
  runs: [],
};

describe("AdminSources", () => {
  beforeEach(() => {
    vi.mocked(api).mockImplementation(async (path) => {
      if (path === "/admin/sources") return [
        source,
        { ...source, id: 2, name: "HelpRent Da Nang API", kind: "manual", connector_type: "rest_api", integration_status: "ready" },
        { ...source, id: 3, name: "Nguồn chờ pháp lý", kind: "scrapy", enabled: false, connector_type: "html_static", integration_status: "legal_review", config: { item_selector: ".item", terms_checked: false } },
      ];
      if (path === "/admin/source-profiles") {
        return [{ id: "chotot-da-nang", name: "Chợ Tốt Đà Nẵng", kind: "scrapy", start_url: "https://example.com", config: { item_selector: ".item", terms_checked: false } }];
      }
      return [];
    });
  });

  it("offers versioned crawler profiles when adding a source", async () => {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter>
          <AuthProvider>
            <ToastProvider>
              <AdminSources />
            </ToastProvider>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    fireEvent.click((await screen.findAllByRole("button", { name: "Thêm nguồn" }))[0]);

    expect(await screen.findByRole("option", { name: "Chợ Tốt Đà Nẵng" })).toBeInTheDocument();
  });

  it("filters a large source registry by name", async () => {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter><AuthProvider><ToastProvider><AdminSources /></ToastProvider></AuthProvider></MemoryRouter>
      </QueryClientProvider>,
    );

    fireEvent.change(await screen.findByRole("searchbox", { name: "Tìm nguồn" }), { target: { value: "HelpRent" } });
    expect(screen.getByRole("button", { name: /HelpRent Da Nang API/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Bộ tin mẫu/ })).not.toBeInTheDocument();
  });

  it("offers a legal approval workflow for external crawlers", async () => {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter><AuthProvider><ToastProvider><AdminSources /></ToastProvider></AuthProvider></MemoryRouter>
      </QueryClientProvider>,
    );

    fireEvent.click(await screen.findByRole("button", { name: /Nguồn chờ pháp lý/ }));
    expect(screen.getByRole("button", { name: "Phê duyệt pháp lý" })).toBeInTheDocument();
  });
});
