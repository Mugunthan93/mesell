# MeeSell v0.1 — Infrastructure Spec (GCP + K3s + Valkey)

> Single-node K3s cluster on GCP asia-south1  
> All services as pods · Valkey for cache/queue · PostgreSQL in-cluster  
> Gemini API on same cloud · GCS for file storage

---

## 1. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    GCP VM (e2-standard-2)                       │
│                    asia-south1-b (Mumbai)                       │
│                    2 vCPU · 8GB RAM · 80GB SSD                  │
│                                                                 │
│  ┌───────────────────── K3s Cluster ──────────────────────────┐ │
│  │                                                             │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │ │
│  │  │  nginx   │  │   api    │  │  worker   │  │ frontend  │  │ │
│  │  │ ingress  │─▶│ (FastAPI)│  │ (Celery)  │  │ (React)   │  │ │
│  │  │          │  │ 2 rep    │  │ 2 rep     │  │ 1 rep     │  │ │
│  │  │ :80/:443 │  │ :8000    │  │           │  │ :3000     │  │ │
│  │  └──────────┘  └────┬─────┘  └─────┬─────┘  └───────────┘  │ │
│  │                     │              │                        │ │
│  │              ┌──────▼──────────────▼──────┐                 │ │
│  │              │     Shared Services        │                 │ │
│  │              │                            │                 │ │
│  │  ┌───────────┴──┐    ┌───────────────┐    │                 │ │
│  │  │  PostgreSQL  │    │    Valkey      │    │                 │ │
│  │  │  16-alpine   │    │   8-alpine     │    │                 │ │
│  │  │  :5432       │    │   :6379        │    │                 │ │
│  │  │  PVC: 20Gi   │    │   PVC: 2Gi     │    │                 │ │
│  │  └──────────────┘    └───────────────┘    │                 │ │
│  │              └────────────────────────────┘                 │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
└──────────┬──────────────────┬──────────────────┬────────────────┘
           │                  │                  │
    ┌──────▼──────┐   ┌──────▼──────┐   ┌───────▼──────┐
    │  GCS Bucket │   │ Gemini API  │   │   MSG91      │
    │  meesell-   │   │ (same cloud │   │   (OTP SMS)  │
    │  prod       │   │  low latency│   │              │
    │  Images +   │   │  Flash 2.5) │   └──────────────┘
    │  Exports    │   └─────────────┘
    └─────────────┘
```

---

## 2. GCP Resources & Cost (Free Tier)

| Resource | Spec | Monthly Cost | Free Credits? |
|----------|------|-------------|---------------|
| Compute Engine VM | e2-standard-2 (2 vCPU, 8GB) | ~$49/mo (~₹4,100) | ✅ Covered by $300 trial |
| Boot Disk | 80GB SSD (pd-balanced) | ~$8/mo | ✅ Covered |
| GCS Bucket | Standard, asia-south1 | ~$0.02/GB/mo | ✅ 5GB always-free |
| Static IP | 1 external IP (in use) | Free (in use) | ✅ Free while attached |
| Gemini 2.5 Flash | API calls | Pay per token | ✅ $300 trial covers it |
| Egress | First 200GB/mo | Free tier | ✅ Sufficient for MVP |
| **Total estimated** | | **~$60/mo (~₹5,000)** | **Covered for ~5 months** |

**GPU for rembg:** Two options:
- **Option A:** Run rembg on CPU (slower, ~3-5s per image but free, no GPU needed)
- **Option B:** Use GCP T4 GPU spot VM only when processing (g2-standard-4, ~$0.35/hr spot, spin up on demand)
- **Recommendation:** Start with CPU (Option A). At 50+ images/day, add GPU.

---

## 3. K3s Pod Definitions

### 3.1 Namespace

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: meesell
```

### 3.2 PostgreSQL

```yaml
# k8s/postgres.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: meesell
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 20Gi
  storageClassName: local-path
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: meesell
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:16-alpine
          ports:
            - containerPort: 5432
          env:
            - name: POSTGRES_DB
              value: meesell
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: meesell-secrets
                  key: POSTGRES_USER
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: meesell-secrets
                  key: POSTGRES_PASSWORD
          volumeMounts:
            - name: postgres-data
              mountPath: /var/lib/postgresql/data
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              cpu: 500m
              memory: 1Gi
      volumes:
        - name: postgres-data
          persistentVolumeClaim:
            claimName: postgres-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: meesell
spec:
  selector:
    app: postgres
  ports:
    - port: 5432
      targetPort: 5432
  clusterIP: None  # Headless for stable DNS
```

### 3.3 Valkey

```yaml
# k8s/valkey.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: valkey-pvc
  namespace: meesell
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 2Gi
  storageClassName: local-path
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: valkey
  namespace: meesell
spec:
  replicas: 1
  selector:
    matchLabels:
      app: valkey
  template:
    metadata:
      labels:
        app: valkey
    spec:
      containers:
        - name: valkey
          image: valkey/valkey:8-alpine
          ports:
            - containerPort: 6379
          command: ["valkey-server"]
          args:
            - "--maxmemory"
            - "256mb"
            - "--maxmemory-policy"
            - "allkeys-lru"
            - "--appendonly"
            - "yes"
            - "--appendfsync"
            - "everysec"
          volumeMounts:
            - name: valkey-data
              mountPath: /data
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 250m
              memory: 512Mi
      volumes:
        - name: valkey-data
          persistentVolumeClaim:
            claimName: valkey-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: valkey
  namespace: meesell
spec:
  selector:
    app: valkey
  ports:
    - port: 6379
      targetPort: 6379
```

### 3.4 API (FastAPI)

```yaml
# k8s/api.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: meesell
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
        - name: api
          image: asia-south1-docker.pkg.dev/PROJECT_ID/meesell/api:latest
          ports:
            - containerPort: 8000
          envFrom:
            - secretRef:
                name: meesell-secrets
            - configMapRef:
                name: meesell-config
          command:
            - gunicorn
            - app.main:app
            - -w
            - "2"
            - -k
            - uvicorn.workers.UvicornWorker
            - -b
            - 0.0.0.0:8000
            - --timeout
            - "120"
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 15
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 15
            periodSeconds: 30
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              cpu: 750m
              memory: 1Gi
---
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: meesell
spec:
  selector:
    app: api
  ports:
    - port: 8000
      targetPort: 8000
```

### 3.5 Worker (Celery)

```yaml
# k8s/worker.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: worker
  namespace: meesell
spec:
  replicas: 2
  selector:
    matchLabels:
      app: worker
  template:
    metadata:
      labels:
        app: worker
    spec:
      containers:
        - name: worker
          image: asia-south1-docker.pkg.dev/PROJECT_ID/meesell/api:latest  # same image as API
          envFrom:
            - secretRef:
                name: meesell-secrets
            - configMapRef:
                name: meesell-config
          command:
            - celery
            - -A
            - app.workers.celery_app
            - worker
            - --loglevel=info
            - --concurrency=2
            - -Q
            - default,images,ai_generation
          resources:
            requests:
              cpu: 500m
              memory: 1Gi       # rembg needs memory
            limits:
              cpu: 1000m
              memory: 2Gi
```

### 3.6 Frontend (React)

```yaml
# k8s/frontend.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: meesell
spec:
  replicas: 1
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
        - name: frontend
          image: asia-south1-docker.pkg.dev/PROJECT_ID/meesell/frontend:latest
          ports:
            - containerPort: 3000
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              cpu: 100m
              memory: 128Mi
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: meesell
spec:
  selector:
    app: frontend
  ports:
    - port: 3000
      targetPort: 3000
```

### 3.7 Ingress (Traefik — K3s default)

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: meesell-ingress
  namespace: meesell
  annotations:
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - meesell.in
        - api.meesell.in
      secretName: meesell-tls
  rules:
    - host: meesell.in
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 3000
    - host: api.meesell.in
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api
                port:
                  number: 8000
```

### 3.8 ConfigMap & Secrets

```yaml
# k8s/config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: meesell-config
  namespace: meesell
data:
  APP_ENV: "production"
  DATABASE_URL: "postgresql+asyncpg://meesell:$(POSTGRES_PASSWORD)@postgres:5432/meesell"
  VALKEY_URL: "redis://valkey:6379/0"          # Valkey uses redis:// protocol
  CELERY_BROKER_URL: "redis://valkey:6379/1"   # Valkey as Celery broker
  CELERY_RESULT_BACKEND: "redis://valkey:6379/2"
  GCS_BUCKET: "meesell-prod"
  GCS_PROJECT_ID: "your-project-id"
  GEMINI_MODEL: "gemini-2.5-flash"
  CORS_ORIGINS: "https://meesell.in"
---
# k8s/secrets.yaml (apply via kubectl, not committed to git)
apiVersion: v1
kind: Secret
metadata:
  name: meesell-secrets
  namespace: meesell
type: Opaque
stringData:
  POSTGRES_USER: "meesell"
  POSTGRES_PASSWORD: "change-this-strong-password"
  JWT_SECRET: "change-this-jwt-secret"
  GEMINI_API_KEY: "AIza..."
  MSG91_AUTH_KEY: "..."
  MSG91_TEMPLATE_ID: "..."
  RAZORPAY_KEY_ID: "rzp_live_..."
  RAZORPAY_KEY_SECRET: "..."
  GCS_SERVICE_ACCOUNT_KEY: |
    {
      "type": "service_account",
      ...
    }
```

---

## 4. Resource Budget (8GB RAM total)

```
┌─────────────────────────────────────────────┐
│            8GB RAM Distribution              │
├─────────────────────┬────────┬──────────────┤
│ Component           │ Req    │ Limit        │
├─────────────────────┼────────┼──────────────┤
│ PostgreSQL          │ 512Mi  │ 1Gi          │
│ Valkey              │ 256Mi  │ 512Mi        │
│ API (×2 replicas)   │ 1Gi    │ 2Gi          │
│ Worker (×2 replicas)│ 2Gi    │ 4Gi          │
│ Frontend (×1)       │ 64Mi   │ 128Mi        │
│ K3s system          │ ~300Mi │ ~500Mi       │
│ OS overhead         │ ~200Mi │ ~300Mi       │
├─────────────────────┼────────┼──────────────┤
│ Total Requested     │ 4.3Gi  │              │
│ Total Limits        │        │ 8.4Gi        │
│ Headroom            │ 3.7Gi  │ Burst OK     │
└─────────────────────┴────────┴──────────────┘
```

Worker pods get the most memory because rembg loads the U2-Net model (~170MB) into memory for background removal. With 2 workers × 2 concurrency = 4 parallel image processing tasks max.

---

## 5. Storage Architecture

### GCS (Google Cloud Storage) — Images & Exports

```
gs://meesell-prod/
├── originals/
│   └── {user_id}/
│       └── {image_id}.jpg          # Raw uploaded photos
├── processed/
│   └── {user_id}/
│       └── {image_id}.jpg          # BG removed, 1024×1024, white BG
├── exports/
│   └── {user_id}/
│       ├── {catalog_id}.csv        # Meesho bulk upload CSV
│       └── {catalog_id}_images.zip # Processed images ZIP
└── temp/
    └── ...                         # Cleanup daily via lifecycle policy
```

### GCS Client (Python)

```python
# app/services/storage.py

from google.cloud import storage

class GCSStorage:
    def __init__(self):
        self.client = storage.Client()
        self.bucket = self.client.bucket(settings.GCS_BUCKET)
    
    async def upload(self, file_bytes: bytes, path: str, content_type: str) -> str:
        blob = self.bucket.blob(path)
        blob.upload_from_string(file_bytes, content_type=content_type)
        blob.make_public()  # or use signed URLs for private
        return blob.public_url
    
    async def get_signed_url(self, path: str, expiry_minutes: int = 60) -> str:
        blob = self.bucket.blob(path)
        return blob.generate_signed_url(
            expiration=timedelta(minutes=expiry_minutes),
            method="GET"
        )
    
    async def delete(self, path: str):
        blob = self.bucket.blob(path)
        blob.delete()
```

### Persistent Volumes (K3s local-path)

```
/var/lib/rancher/k3s/storage/
├── postgres-pvc/       # 20Gi — PostgreSQL data
└── valkey-pvc/         # 2Gi  — Valkey AOF persistence
```

**Backup strategy (MVP):** Daily cron job `pg_dump` to GCS bucket `gs://meesell-backups/`.

```yaml
# k8s/backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: pg-backup
  namespace: meesell
spec:
  schedule: "0 2 * * *"     # 2 AM IST daily
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: postgres:16-alpine
              command:
                - /bin/sh
                - -c
                - |
                  pg_dump -h postgres -U $POSTGRES_USER $POSTGRES_DB | \
                  gzip > /tmp/meesell_$(date +%Y%m%d).sql.gz && \
                  gsutil cp /tmp/meesell_*.sql.gz gs://meesell-backups/
              envFrom:
                - secretRef:
                    name: meesell-secrets
          restartPolicy: OnFailure
```

---

## 6. Valkey Configuration

```python
# Valkey is 100% Redis-protocol compatible
# All redis-py / celery[redis] libraries work unchanged
# Just point connection URL to valkey service

# app/config.py
VALKEY_URL = "redis://valkey:6379/0"        # DB 0: sessions, OTP, rate limits
CELERY_BROKER = "redis://valkey:6379/1"     # DB 1: Celery task broker
CELERY_BACKEND = "redis://valkey:6379/2"    # DB 2: Celery result backend

# Usage is identical to Redis:
import redis.asyncio as redis

valkey = redis.from_url(settings.VALKEY_URL)

# OTP storage
await valkey.setex(f"otp:{phone}", 300, json.dumps({"code": otp, "attempts": 0}))

# Rate limiting
await valkey.incr(f"ratelimit:{user_id}:generate:{window}")
await valkey.expire(f"ratelimit:{user_id}:generate:{window}", 60)

# Session cache
await valkey.setex(f"session:{token}", 86400, json.dumps(user_data))
```

Celery config:

```python
# app/workers/celery_app.py

from celery import Celery

celery_app = Celery(
    "meesell",
    broker=settings.CELERY_BROKER,         # redis://valkey:6379/1
    backend=settings.CELERY_BACKEND,       # redis://valkey:6379/2
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    task_routes={
        "app.workers.image_tasks.*": {"queue": "images"},
        "app.workers.generation_tasks.*": {"queue": "ai_generation"},
    },
    worker_prefetch_multiplier=1,     # Fair scheduling for long AI tasks
    task_acks_late=True,              # Re-queue if worker crashes
)
```

---

## 7. CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
# (or GitLab CI — since you use GitLab)

stages:
  - build
  - push
  - deploy

build:
  script:
    # API image (also used by worker)
    - docker build -t asia-south1-docker.pkg.dev/$PROJECT_ID/meesell/api:$CI_COMMIT_SHORT_SHA ./backend
    # Frontend image
    - docker build -t asia-south1-docker.pkg.dev/$PROJECT_ID/meesell/frontend:$CI_COMMIT_SHORT_SHA ./frontend

push:
  script:
    - docker push asia-south1-docker.pkg.dev/$PROJECT_ID/meesell/api:$CI_COMMIT_SHORT_SHA
    - docker push asia-south1-docker.pkg.dev/$PROJECT_ID/meesell/frontend:$CI_COMMIT_SHORT_SHA

deploy:
  script:
    # SSH into GCP VM and update K3s deployments
    - ssh meesell-vm "kubectl -n meesell set image deployment/api api=asia-south1-docker.pkg.dev/$PROJECT_ID/meesell/api:$CI_COMMIT_SHORT_SHA"
    - ssh meesell-vm "kubectl -n meesell set image deployment/worker worker=asia-south1-docker.pkg.dev/$PROJECT_ID/meesell/api:$CI_COMMIT_SHORT_SHA"
    - ssh meesell-vm "kubectl -n meesell set image deployment/frontend frontend=asia-south1-docker.pkg.dev/$PROJECT_ID/meesell/frontend:$CI_COMMIT_SHORT_SHA"
    - ssh meesell-vm "kubectl -n meesell rollout status deployment/api --timeout=120s"
```

---

## 8. VM Setup Script

```bash
#!/bin/bash
# setup-meesell.sh — Run on fresh GCP VM (Ubuntu 24.04)

# 1. Install K3s
curl -sfL https://get.k3s.io | sh -s - \
  --disable=servicelb \
  --write-kubeconfig-mode=644

# 2. Wait for K3s
until kubectl get nodes | grep -q "Ready"; do sleep 5; done

# 3. Install cert-manager (for Let's Encrypt TLS)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.0/cert-manager.yaml

# 4. Create namespace
kubectl create namespace meesell

# 5. Apply secrets (from local file, NOT in git)
kubectl apply -f k8s/secrets.yaml

# 6. Apply all manifests
kubectl apply -f k8s/config.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/valkey.yaml
kubectl apply -f k8s/api.yaml
kubectl apply -f k8s/worker.yaml
kubectl apply -f k8s/frontend.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/backup-cronjob.yaml

# 7. Verify
kubectl -n meesell get pods
kubectl -n meesell get svc
kubectl -n meesell get ingress

echo "MeeSell deployed. Configure DNS: meesell.in → $(curl -s ifconfig.me)"
```

---

## 9. Monitoring (Lightweight)

```yaml
# k8s/monitoring.yaml
# Minimal monitoring stack for MVP — no Prometheus/Grafana overhead

# Option 1: GCP Cloud Monitoring (free for GCE VMs)
# - CPU, memory, disk metrics auto-collected
# - Set alerts for CPU > 80%, memory > 85%, disk > 90%

# Option 2: Simple health check cron
apiVersion: batch/v1
kind: CronJob
metadata:
  name: health-check
  namespace: meesell
spec:
  schedule: "*/5 * * * *"    # Every 5 minutes
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: healthcheck
              image: curlimages/curl:latest
              command:
                - /bin/sh
                - -c
                - |
                  API=$(curl -s -o /dev/null -w "%{http_code}" http://api:8000/health)
                  if [ "$API" != "200" ]; then
                    curl -X POST "https://api.msg91.com/..." # SMS alert
                  fi
          restartPolicy: OnFailure
```

Application-level monitoring:

```python
# app/main.py — health endpoint

@app.get("/health")
async def health():
    checks = {}
    
    # PostgreSQL
    try:
        await db.execute("SELECT 1")
        checks["postgres"] = "ok"
    except:
        checks["postgres"] = "error"
    
    # Valkey
    try:
        await valkey.ping()
        checks["valkey"] = "ok"
    except:
        checks["valkey"] = "error"
    
    # GCS
    try:
        storage.client.get_bucket(settings.GCS_BUCKET)
        checks["gcs"] = "ok"
    except:
        checks["gcs"] = "error"
    
    status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks}
```

---

## 10. Scaling Triggers

| Metric | Current (MVP) | Action |
|--------|--------------|--------|
| Users < 500 | Single VM, current spec | No change |
| API latency > 500ms | 2 replicas | Increase to 3 replicas |
| Worker queue depth > 50 | 2 replicas | Increase to 4 replicas |
| Image processing > 5s avg | CPU-based rembg | Add GPU spot instance |
| Database connections > 80 | Pod PostgreSQL | Migrate to Cloud SQL |
| Total users > 2000 | Single node K3s | Add second node or move to GKE |
| Storage > 50GB | GCS Standard | Enable lifecycle policy (archive old exports after 30 days) |

---

## 11. Pod Topology Summary

```
kubectl -n meesell get pods

NAME                        READY   CPU     MEM     ROLE
postgres-xxx                1/1     250m    512Mi   Database
valkey-xxx                  1/1     100m    256Mi   Cache + Queue broker
api-xxx-1                   1/1     250m    512Mi   FastAPI (replica 1)
api-xxx-2                   1/1     250m    512Mi   FastAPI (replica 2)
worker-xxx-1                1/1     500m    1Gi     Celery (replica 1)
worker-xxx-2                1/1     500m    1Gi     Celery (replica 2)
frontend-xxx                1/1     50m     64Mi    React SPA
                            ─────   ─────   ─────
                            TOTAL   1.9 CPU  3.9Gi   (of 2 CPU / 8Gi available)
```

---

*End of Infrastructure Spec — MeeSell v0.1 (GCP + K3s + Valkey)*
