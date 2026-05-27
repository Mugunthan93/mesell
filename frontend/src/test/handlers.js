/**
 * Default MSW request handlers — the "happy path" backend.
 * Override per-test with `server.use(...)`.
 */
import { HttpResponse, http } from "msw";

const BASE = "*/api/v1";

export const fixtures = {
  catalog: {
    id: "11111111-1111-1111-1111-111111111111",
    user_id: "00000000-0000-0000-0000-000000000001",
    name: "Diwali Kurtis",
    status: "draft",
    category: "Kurtis",
    subcategory: null,
    quality_score: null,
    created_at: "2026-05-27T07:00:00Z",
    updated_at: "2026-05-27T07:00:00Z",
  },
  user: {
    id: "00000000-0000-0000-0000-000000000001",
    phone: "+919876543210",
    name: null,
    plan: "free",
    catalogs_used: 0,
    catalogs_limit: 5,
  },
};

export const handlers = [
  // --- auth ---
  http.post(`${BASE}/auth/send-otp`, async () =>
    HttpResponse.json({ sent: true, dev_otp: "1234" }),
  ),
  http.post(`${BASE}/auth/verify-otp`, async () =>
    HttpResponse.json({ token: "fake-jwt-token", user: fixtures.user }),
  ),
  http.get(`${BASE}/auth/me`, async ({ request }) => {
    const auth = request.headers.get("authorization");
    if (!auth?.startsWith("Bearer ")) {
      return new HttpResponse(JSON.stringify({ detail: "unauth" }), { status: 401 });
    }
    return HttpResponse.json(fixtures.user);
  }),

  // --- catalogs ---
  http.get(`${BASE}/catalogs`, async () =>
    HttpResponse.json({ data: [fixtures.catalog], total: 1, page: 1, limit: 20 }),
  ),
  http.post(`${BASE}/catalogs`, async () => HttpResponse.json(fixtures.catalog, { status: 201 })),
  http.get(`${BASE}/catalogs/:id`, async () =>
    HttpResponse.json({ ...fixtures.catalog, skus: [] }),
  ),

  // --- pricing (public) ---
  http.post(`${BASE}/pricing/calculate`, async () =>
    HttpResponse.json({
      selling_price: "599.00",
      cost_price: "250.00",
      weight_grams: 480,
      category: "Kurtis",
      zone: "national",
      shipping_slab: { max_grams: 500 },
      shipping_cost: "65.00",
      shipping_gst: "11.70",
      payment_processing: "11.98",
      return_provision: "149.75",
      packaging: "12.00",
      ad_spend: "0.00",
      commission: "0.00",
      total_costs: "500.43",
      net_profit: "98.57",
      margin_percent: "16.46",
      return_rate_used: 0.25,
      alerts: [
        { code: "weight_slab_warning", severity: "warn", message: "Drop below 500g to save shipping." },
      ],
      authenticated: false,
    }),
  ),
];
