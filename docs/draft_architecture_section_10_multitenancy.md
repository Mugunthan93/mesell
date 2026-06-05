> **STATUS: INTEGRATED** into docs/MVP_ARCHITECTURE.md (2026-06-04 evening). This file is archival only. See the canonical version in MVP_ARCHITECTURE.md.

# Section 10 — Multi-tenancy and Data Isolation

> Draft produced by `nexus:level-1a:multi-tenant-saas-sme`, saved to disk by coordinator (agent failed to write directly). Coordinator review pending.

## 10.1 Tenancy Model: Single-Seller-Per-Account (V1)

MeeSell V1 is **single-seller-per-account**. One user (phone + JWT) = one tenant = one Meesho seller. Each `user_id` in the `users` table is a complete, independent tenant.

**V1.5+:** Team accounts deferred. Future implementation will add a `teams` table, per-team rate limits, and replace `user_id` filtering with `team_id` filtering. For V1, zero team infrastructure exists.

---

## 10.2 Data Isolation: App-Level Filtering (No RLS for V1)

**V1 Decision: Application-level `user_id` scoping with PostgreSQL foreign keys. Row-Level Security (RLS) deferred to V1.5.**

### Why app-level for V1?

✓ **Simpler logic**: Every service method takes `user_id` as explicit parameter
✓ **Easier testing**: Swap `user_id` in test fixtures; no RLS policy debugging
✓ **Fewer footguns**: Intent is explicit in Python code, not hidden in DB policies

✗ **No DB-level guarantee**: Developers must remember to filter; RLS provides automatic protection

**V1.5 evaluation:** Consider RLS when team accounts ship and codebase stabilizes.

### Implementation: Foreign Keys + Mandatory Filtering

```sql
CREATE TABLE catalogs (
  id              UUID PRIMARY KEY,
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  ...
);

CREATE TABLE products (
  id              UUID PRIMARY KEY,
  user_id         UUID NOT NULL REFERENCES users(id),
  catalog_id      UUID NOT NULL REFERENCES catalogs(id),
  ...
);

CREATE INDEX idx_catalogs_user           ON catalogs(user_id);
CREATE INDEX idx_products_user           ON products(user_id);
CREATE INDEX idx_products_user_status    ON products(user_id, status);
```

**Rule:** Every query touching `catalogs`, `products`, `product_images`, `pricing_calcs`, `exports` **must** include `WHERE user_id = :user_id`. Linter enforces this in CI.

---

## 10.3 JWT Claims and Tenant Injection

JWT payload from `/api/v1/auth/otp/verify`:

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "exp": 1719000000,
  "plan": "free"
}
```

FastAPI middleware extracts `sub` → `user_id` and injects into every route handler:

```python
async def get_current_user(token: str = Depends(HTTPBearer())) -> CurrentUser:
    payload = jwt.decode(token.credentials, settings.JWT_SECRET, ["HS256"])
    return CurrentUser(user_id=UUID(payload["sub"]), plan=payload["plan"])

@router.get("/api/v1/products")
async def list_products(
    user: CurrentUser = Depends(get_current_user),
    service: ProductService = Depends(),
):
    return await service.list_products(user_id=user.user_id)
```

---

## 10.4 Service-Layer Enforcement

Every service method querying tenant data takes `user_id` as explicit parameter:

```python
class ProductService:
    async def get_product(self, user_id: UUID, product_id: UUID) -> Product:
        stmt = select(Product).where(
            (Product.id == product_id) & (Product.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        product = result.scalars().first()
        if not product:
            raise HTTPException(status_code=404)
        return product
```

**CI Linter:** Reject any service method that queries owned tables without `user_id` in signature.

**Tests:** Every fixture creates unique `user_id`; isolation tests verify User A cannot read User B's products:

```python
@pytest.mark.asyncio
async def test_product_isolation():
    user_a_id = UUID("00000000-0000-0000-0000-000000000001")
    user_b_id = UUID("00000000-0000-0000-0000-000000000002")

    product = await service.create_product(user_a_id, ...)

    with pytest.raises(HTTPException):
        await service.get_product(user_b_id, product.id)
```

---

## 10.5 Cross-Tenant Risk Assessment

| Data | Risk | Mitigation |
|---|---|---|
| Products & Catalogs | LOW | `user_id` WHERE clause on every query |
| Seller Profile | LOW | `user_id` PRIMARY KEY (one per user) |
| GCS Images | LOW | Signed URLs scoped to single product (§10.8) |
| AI Suggestions | LOW | Stored in `products.ai_suggestions_jsonb`, scoped by `user_id` |
| Pricing & Exports | LOW | Both owned by `user_id` foreign key |

**Non-existent in V1 (no risk):**
- Shared analytics (V1.5)
- Cross-seller recommendations
- Admin panel (SQL read-only replica only in V1)

---

## 10.6 Admin Access: V1 = SQL, V1.5 = Admin Panel

**V1:** Read-only PostgreSQL replica on GCP VM. All admin SQL queries logged to `audit_events` table (§11).

**V1.5:** Separate `admin_users` table + JWT claim `is_admin: true`. Routes: `/api/v1/admin/sellers/:user_id/...`. Full audit trail.

---

## 10.7 Rate Limiting Per Tenant (Valkey)

All limits are per-user to prevent one seller starving others:

| Action | Limit | Window | Key |
|---|---|---|---|
| OTP send | 3 | 1 hour | `ratelimit:otp:send:{phone}:3600` |
| Autofill | 50 | 1 hour | `ratelimit:autofill:{user_id}:3600` |
| Smart picker | 100 | 1 hour | `ratelimit:picker:{user_id}:3600` |
| Create product | 20 | 1 hour | `ratelimit:create_product:{user_id}:3600` |

Sliding-window in Valkey: `INCR key; EXPIRE key 3600 if count==1`.

---

## 10.8 GCS Bucket Layout: Signed URLs Scoped per Product

```
gs://meesell-images/{user_id}/{product_id}/{image_idx}.jpg
```

Signed URLs are scoped to **one image**, not the entire product folder:

```python
def get_signed_url(user_id: UUID, product_id: UUID, image_idx: int) -> str:
    bucket = storage_client.bucket("meesell-images")
    blob = bucket.blob(f"{user_id}/{product_id}/{image_idx}.jpg")
    return blob.generate_signed_url(version="v4", expiration=timedelta(hours=1))
```

Leaked URL = access to one image only, not catalog-wide.

---

## 10.9 Plan-Based Limits (V1 = 100 products, V1.5 = Tiered)

V1: All sellers are "free" plan with soft cap of **100 active products**.

```python
async def check_product_limit(user_id: UUID, db: AsyncSession):
    active = await db.execute(
        select(func.count(Product.id)).where(
            (Product.user_id == user_id) & (Product.status != "deleted")
        )
    )
    if active.scalar() >= 100:
        raise HTTPException(status_code=429, detail="Product limit reached")
```

**V1.5 divergence:**
- "pro": 500 products, 200 autofill/hour
- "free": 100 products, 50 autofill/hour

---

## 10.10 Multi-Tenancy Test Checklist

1. ✓ Unique `user_id` per test (UUID per fixture)
2. ✓ Seed seller_profile + user
3. ✓ Create tenant-scoped entities (products, catalogs)
4. ✓ Assert isolation: User A data invisible to User B
5. ✓ Verify: same `product_id` returns 404 for different user

**Indexes for efficiency:**

```sql
CREATE INDEX idx_catalogs_user            ON catalogs(user_id);
CREATE INDEX idx_products_user            ON products(user_id);
CREATE INDEX idx_products_user_status     ON products(user_id, status);
CREATE INDEX idx_catalogs_user_created    ON catalogs(user_id, created_at DESC);
```
