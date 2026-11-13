import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "../../components/ui";
import { AuthProvider } from "../../lib/auth";
import { api } from "../../lib/api";
import AdminOverview from "./Overview";

vi.mock("../../lib/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("../../lib/api")>();
  return { ...original, api: vi.fn() };
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("AdminOverview", () => {
  it("labels seeded dashboard figures as demo data", async () => {
    vi.mocked(api).mockResolvedValue({
      dataset: { mode: "demo", label: "Dữ liệu minh họa" },
      kpis: { collected_24h: 10, valid_24h: 9, valid_rate: 90, merged_24h: 1, merged_rate: 10, ai_cost_today: 0, ai_cost_per_listing: 0 },
      services: { elasticsearch: false, llm_model: "rules", queue: "sync" },
      pipeline: null,
      sources: [],
      llm_usage: [],
      eval: { f1: 0.9, json_valid: 100, search_latency_s: 0.1 },
      budget: { used: 0, monthly: 1_000_000 },
    });

    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter>
          <AuthProvider>
            <ToastProvider>
              <AdminOverview />
            </ToastProvider>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect((await screen.findAllByText("Dữ liệu minh họa")).length).toBeGreaterThan(0);
  });

  it("runs enabled real sources after sample fixtures have been removed", async () => {
    vi.mocked(api).mockImplementation(async (path) => {
      if (path === "/admin/sources/run-enabled") return { queued_count: 1, skipped_count: 0 };
      return {
        dataset: { mode: "live", label: "Dữ liệu vận hành" },
        kpis: { collected_24h: 0, valid_24h: 0, valid_rate: 0, merged_24h: 0, merged_rate: 0, ai_cost_today: 0, ai_cost_per_listing: 0 },
        services: { elasticsearch: false, llm_model: "rules", queue: "sync" },
        pipeline: null,
        sources: [{ id: 7, name: "Nguồn phòng trọ Đà Nẵng", kind: "scrapy", connector_type: "html_static", status: "ok", last_run_at: null, last_new: 0, error_rate: 0, enabled: true }],
        llm_usage: [],
        eval: { f1: 0.9, json_valid: 100, search_latency_s: 0.1 },
        budget: { used: 0, monthly: 1_000_000 },
      };
    });

    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter>
          <AuthProvider>
            <ToastProvider>
              <AdminOverview />
            </ToastProvider>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    const buttons = await screen.findAllByRole("button", { name: "Chạy thu thập ngay" });
    expect(buttons.length).toBeGreaterThan(0);
    buttons.forEach((button) => expect(button).toBeEnabled());
    fireEvent.click(buttons[0]);

    await waitFor(() => expect(api).toHaveBeenCalledWith("/admin/sources/run-enabled", { body: {} }));
  });
});
