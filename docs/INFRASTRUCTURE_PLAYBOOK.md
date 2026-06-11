# MeeSell Infrastructure Safety Playbook

Last updated: 2026-06-04
Status: Live runbook — followed by meesell-infra-builder agent
Owner: Founder + dedicated agent

Single source of truth for MeeSell infrastructure. Runbook-grade: every command is imperative, every action shows expected output, every failure has a branch, every state change has a rollback. Read Section 0 before doing anything.

---

## Section 0: Critical Rules (Cannot Be Violated)

These rules override convenience, speed, and personal judgment. If a rule conflicts with a step, STOP and escalate.

- [DANGER] NEVER run `gcloud ... delete` without explicit founder approval in the current session.
- [DANGER] NEVER expose secrets in logs, commits, shell history, `kubectl describe`, or env dumps.
- [DANGER] NEVER push directly to `prod` without going through `staging` and a passing acceptance run.
- [DANGER] NEVER skip the validation step between phases. If validation fails, STOP. No "fix forward."
- [DANGER] NEVER touch `meesell-vm`, `shotfox-platform`, `shotfox-mvp1-alpha-dev` — other projects, out of scope.
- [SAFE] ALWAYS run `gcloud compute instances list` before any compute action; confirm only `meesell-dev` is in scope.
- [SAFE] ALWAYS save a state snapshot before destructive operations (see 2.1 pattern).
- [SAFE] ALWAYS show a diff (`kubectl diff -f file.yaml`) before applying to live namespaces.
- [SAFE] ALWAYS use `--dry-run=client -o yaml` or `--dry-run=server` first, then apply.
- [SAFE] ALWAYS scope kubectl with `-n <namespace>`. Do not rely on default.

Project identifiers (memorize):

- GCP account: `vaishnaviramoorthy@gmail.com`
- GCP project: `project-1f5cbf72-2820-4cdb-949`
- Zone: `asia-south1-a`
- New VM: `meesell-dev`
- Machine type: `e2-standard-2` (2 vCPU, 8 GB RAM)
- Boot disk: 30 GB pd-balanced, Ubuntu 22.04 LTS minimal
- Orchestrator: K3s
- Namespaces: `dev` (Day 1), `staging` (Day 7), `prod` (Week 2)
- Stack: PostgreSQL 16, Valkey 8, Supabase Studio (trimmed), FastAPI, Angular (nginx), Traefik ingress, cert-manager + Let's Encrypt

---

## Section 1: Pre-flight Checks (Run Before ANY Infrastructure Work)

Run every check. If any fails, STOP and resolve.

```bash
gcloud auth list
```
Expected: `*       vaishnaviramoorthy@gmail.com`
Fix: `gcloud auth login vaishnaviramoorthy@gmail.com`

```bash
gcloud config get-value project
```
Expected: `project-1f5cbf72-2820-4cdb-949`
Fix: `gcloud config set project project-1f5cbf72-2820-4cdb-949`

```bash
gcloud config get-value compute/zone
```
Expected: `asia-south1-a`
Fix: `gcloud config set compute/zone asia-south1-a`

```bash
gcloud billing accounts list
```
Expected: at least one row with `OPEN: True`. If `False`, STOP.

Baseline inventory (evidence we did not touch other projects' VMs):
```bash
gcloud compute instances list > /tmp/meesell-baseline-$(date +%Y%m%d-%H%M).txt
cat /tmp/meesell-baseline-*.txt
```
Expected baseline (DO NOT TOUCH): `meesell-vm`, `shotfox-platform`, `shotfox-mvp1-alpha-dev`.

Credit check:
```bash
gcloud beta billing budgets list --billing-account=$(gcloud billing accounts list --format="value(ACCOUNT_ID)" | head -1)
```
Record current amount and thresholds. If no budget exists, create per Section 13 before provisioning.

Founder IP for firewall scoping:
```bash
FOUNDER_IP=$(curl -s ifconfig.me); echo "Founder IP: $FOUNDER_IP"
```
Verify IPv4 shape. If empty: `FOUNDER_IP=$(curl -s https://api.ipify.org)`.

Safety gate: all six checks pass. Do not proceed otherwise.

---

## Section 2: VM Provisioning — Day 1

### 2.1 Snapshot project state (rollback insurance)

```bash
gcloud compute instances list      > /tmp/meesell-pre-day1-state.txt
gcloud compute firewall-rules list > /tmp/meesell-pre-day1-firewall.txt
gcloud compute disks list          > /tmp/meesell-pre-day1-disks.txt
ls -la /tmp/meesell-pre-day1-*.txt
```
Expected: three non-empty files. Keep for Day 1.

### 2.2 Provision `meesell-dev`

[DANGER] State-changing. Read entire step before pasting.

```bash
gcloud compute instances create meesell-dev \
  --project=project-1f5cbf72-2820-4cdb-949 \
  --zone=asia-south1-a \
  --machine-type=e2-standard-2 \
  --network-interface=network-tier=PREMIUM,subnet=default \
  --maintenance-policy=MIGRATE \
  --provisioning-model=STANDARD \
  --service-account=default \
  --scopes=https://www.googleapis.com/auth/cloud-platform \
  --tags=k3s-server,http-server,https-server \
  --create-disk=auto-delete=yes,boot=yes,device-name=meesell-dev,image=projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts,mode=rw,size=30,type=pd-balanced \
  --no-shielded-secure-boot --shielded-vtpm --shielded-integrity-monitoring \
  --labels=env=dev,project=meesell,owner=founder \
  --reservation-affinity=any
```
Expected last lines: `meesell-dev  asia-south1-a  e2-standard-2  ... RUNNING`.

Validation:
```bash
gcloud compute instances describe meesell-dev --zone=asia-south1-a \
  --format="value(status,networkInterfaces[0].accessConfigs[0].natIP)"
VM_IP=$(gcloud compute instances describe meesell-dev --zone=asia-south1-a --format="value(networkInterfaces[0].accessConfigs[0].natIP)")
echo "meesell-dev IP: $VM_IP"
```
Expected: `RUNNING<TAB><IP>`.

If validation fails:
- Quota: `gcloud compute project-info describe --format="value(quotas)" | tr ';' '\n' | grep -i cpus`
- Image: `gcloud compute images list --filter="family=ubuntu-2204-lts" --project=ubuntu-os-cloud`
- IAM: confirm caller has `roles/compute.instanceAdmin.v1`.
- Read the error verbatim. Do not retry blindly.

Rollback (founder approval required):
```bash
gcloud compute instances delete meesell-dev --zone=asia-south1-a --quiet
gcloud compute instances list | grep meesell-dev || echo "ROLLBACK OK"
```

### 2.3 Firewall rules

[DANGER] Default firewall already allows SSH. We add HTTP, HTTPS, and a scoped K3s API rule.

```bash
gcloud compute firewall-rules create meesell-dev-http \
  --network=default --action=ALLOW --rules=tcp:80 \
  --source-ranges=0.0.0.0/0 --target-tags=http-server

gcloud compute firewall-rules create meesell-dev-https \
  --network=default --action=ALLOW --rules=tcp:443 \
  --source-ranges=0.0.0.0/0 --target-tags=https-server

FOUNDER_IP=$(curl -s ifconfig.me)
gcloud compute firewall-rules create meesell-dev-k3s-api \
  --network=default --action=ALLOW --rules=tcp:6443 \
  --source-ranges=${FOUNDER_IP}/32 --target-tags=k3s-server
```
Expected: three `Created` lines.

Validation:
```bash
gcloud compute firewall-rules list --filter="name~meesell-dev" \
  --format="table(name,sourceRanges,allowed)"
```
Expected: three rows. `meesell-dev-k3s-api` sourceRanges MUST equal `${FOUNDER_IP}/32`, never `0.0.0.0/0`.

If a rule already exists or shows `0.0.0.0/0` on K3s API: delete and recreate.
```bash
gcloud compute firewall-rules delete meesell-dev-k3s-api --quiet
```

Rollback all:
```bash
gcloud compute firewall-rules delete meesell-dev-http meesell-dev-https meesell-dev-k3s-api --quiet
```

Safety gate: VM RUNNING, IP captured, three firewall rules present and correctly scoped.

---

## Section 3: K3s Installation — Day 1

### 3.1 SSH to `meesell-dev`

```bash
gcloud compute ssh meesell-dev --zone=asia-south1-a --tunnel-through-iap
```
If SSH fails: enable IAP `gcloud services enable iap.googleapis.com`; or drop `--tunnel-through-iap` if firewall permits direct SSH from your IP.

### 3.2 Install K3s (on VM)

```bash
curl -sfL https://get.k3s.io | sh -s - server \
  --disable=traefik \
  --tls-san=$(curl -s ifconfig.me) \
  --write-kubeconfig-mode=644 \
  --node-name=meesell-dev-master
```
Bundled Traefik is disabled because we install our own in Section 8.

Validation:
```bash
sudo systemctl status k3s --no-pager | head -15
sudo kubectl get nodes
sudo kubectl get pods --all-namespaces
```
Expected: `Active: active (running)`; `meesell-dev-master   Ready   control-plane,master`; kube-system pods Running/Completed.

If install fails:
- Disk: `df -h /var` (need > 5 GB free)
- Logs: `sudo journalctl -u k3s -n 100 --no-pager`
- Ports: `sudo ss -tlnp | grep -E "6443|10250"`
- Conflicting runtime: `sudo systemctl status containerd docker 2>&1 | head -20`

Rollback:
```bash
sudo /usr/local/bin/k3s-uninstall.sh
sudo systemctl status k3s 2>&1 | grep "could not be found" && echo "ROLLBACK OK"
```

### 3.3 Configure local kubectl (founder's laptop)

```bash
mkdir -p ~/.kube
gcloud compute scp meesell-dev:/etc/rancher/k3s/k3s.yaml ~/.kube/meesell-dev.yaml \
  --zone=asia-south1-a --tunnel-through-iap
VM_IP=$(gcloud compute instances describe meesell-dev --zone=asia-south1-a --format="value(networkInterfaces[0].accessConfigs[0].natIP)")
sed -i.bak "s/127.0.0.1/${VM_IP}/g" ~/.kube/meesell-dev.yaml
chmod 600 ~/.kube/meesell-dev.yaml
export KUBECONFIG=~/.kube/meesell-dev.yaml
kubectl get nodes
echo 'export KUBECONFIG=~/.kube/meesell-dev.yaml' >> ~/.zshrc
```
Expected: `meesell-dev-master   Ready` from laptop.

If it fails:
- TLS SAN mismatch: rerun K3s install with correct `--tls-san=${VM_IP}`.
- Firewall: update if founder IP changed:
  ```bash
  NEW_IP=$(curl -s ifconfig.me)
  gcloud compute firewall-rules update meesell-dev-k3s-api --source-ranges=${NEW_IP}/32
  ```

Safety gate: laptop `kubectl get nodes` returns Ready.

---

## Section 4: Namespace Setup — Day 1

```bash
kubectl create namespace dev     --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace staging --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace dev     env=dev     --overwrite
kubectl label namespace staging env=staging --overwrite
kubectl get namespaces -L env
```
Expected rows include `dev` (env=dev), `staging` (env=staging).

Note: `prod` is NOT created until Week 2.

Rollback: `kubectl delete namespace staging dev`.

---

## Section 5: PostgreSQL Deployment — Day 1

### 5.1 Credentials

```bash
mkdir -p ~/.meesell-secrets && chmod 700 ~/.meesell-secrets
PG_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')
echo -n "$PG_PASSWORD" > ~/.meesell-secrets/dev-postgres-password
chmod 600 ~/.meesell-secrets/dev-postgres-password
kubectl -n dev create secret generic postgres-credentials \
  --from-literal=username=meesell \
  --from-literal=password="$PG_PASSWORD" \
  --from-literal=database=meesell \
  --dry-run=client -o yaml | kubectl apply -f -
unset PG_PASSWORD
```
Validation:
```bash
ls -la ~/.meesell-secrets/dev-postgres-password
kubectl -n dev get secret postgres-credentials -o jsonpath='{.metadata.name}'
```
Expected: file mode `-rw-------`, secret name `postgres-credentials`.

[DANGER] Never `kubectl get secret -o yaml` and share the output. Never `echo $PG_PASSWORD`.

### 5.2 Manifest `~/meesell-infra/dev/postgres.yaml`

```yaml
apiVersion: v1
kind: Service
metadata: { name: postgres, namespace: dev }
spec:
  clusterIP: None
  selector: { app: postgres }
  ports: [ { port: 5432, name: postgres } ]
---
apiVersion: apps/v1
kind: StatefulSet
metadata: { name: postgres, namespace: dev }
spec:
  serviceName: postgres
  replicas: 1
  selector: { matchLabels: { app: postgres } }
  template:
    metadata: { labels: { app: postgres } }
    spec:
      containers:
        - name: postgres
          image: postgres:16
          ports: [ { containerPort: 5432 } ]
          env:
            - { name: POSTGRES_USER,     valueFrom: { secretKeyRef: { name: postgres-credentials, key: username } } }
            - { name: POSTGRES_PASSWORD, valueFrom: { secretKeyRef: { name: postgres-credentials, key: password } } }
            - { name: POSTGRES_DB,       valueFrom: { secretKeyRef: { name: postgres-credentials, key: database } } }
            - { name: PGDATA, value: /var/lib/postgresql/data/pgdata }
          resources:
            requests: { cpu: "200m", memory: "500Mi" }
            limits:   { cpu: "1000m", memory: "1Gi" }
          readinessProbe:
            exec: { command: ["pg_isready","-U","meesell","-d","meesell"] }
            initialDelaySeconds: 10
            periodSeconds: 5
          livenessProbe:
            exec: { command: ["pg_isready","-U","meesell","-d","meesell"] }
            initialDelaySeconds: 30
            periodSeconds: 15
          volumeMounts:
            - { name: data, mountPath: /var/lib/postgresql/data }
  volumeClaimTemplates:
    - metadata: { name: data }
      spec:
        accessModes: ["ReadWriteOnce"]
        resources: { requests: { storage: 20Gi } }
```

Apply:
```bash
kubectl -n dev diff -f ~/meesell-infra/dev/postgres.yaml || true
kubectl -n dev apply -f ~/meesell-infra/dev/postgres.yaml --dry-run=server
kubectl -n dev apply -f ~/meesell-infra/dev/postgres.yaml
kubectl -n dev rollout status statefulset/postgres --timeout=180s
kubectl -n dev exec postgres-0 -- pg_isready -U meesell -d meesell
kubectl -n dev exec postgres-0 -- psql -U meesell -d meesell -c "SELECT 1;"
```
Expected: `postgres-0  1/1 Running`; `accepting connections`; `SELECT 1` returns `1`.

Fail branches:
- Pod `Pending`: `kubectl -n dev describe pod postgres-0`; PVC unbound? `kubectl get storageclass` (K3s default = `local-path`).
- `CrashLoopBackOff`: `kubectl -n dev logs postgres-0 --tail=100`. Usually PGDATA non-empty from prior attempt; wiping PVC requires founder approval.

Rollback:
```bash
kubectl -n dev delete -f ~/meesell-infra/dev/postgres.yaml
kubectl -n dev delete pvc data-postgres-0   # ONLY with founder approval (data loss)
```

### 5.3 Backup

```bash
mkdir -p ~/meesell-backups
TS=$(date +%Y%m%d-%H%M)
kubectl -n dev exec postgres-0 -- pg_dump -U meesell meesell \
  > ~/meesell-backups/meesell-dev-${TS}.sql
ls -lh ~/meesell-backups/meesell-dev-${TS}.sql
```
Expected: non-empty `.sql` file.

Restore (founder approval; destroys current data):
```bash
kubectl -n dev exec -i postgres-0 -- psql -U meesell -d meesell < ~/meesell-backups/<file>.sql
```

---

## Section 6: Valkey Deployment — Day 1

### 6.1 Credentials

```bash
VK_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')
echo -n "$VK_PASSWORD" > ~/.meesell-secrets/dev-valkey-password
chmod 600 ~/.meesell-secrets/dev-valkey-password
kubectl -n dev create secret generic valkey-credentials \
  --from-literal=password="$VK_PASSWORD" \
  --dry-run=client -o yaml | kubectl apply -f -
unset VK_PASSWORD
```

### 6.2 Manifest `~/meesell-infra/dev/valkey.yaml`

```yaml
apiVersion: v1
kind: Service
metadata: { name: valkey, namespace: dev }
spec:
  clusterIP: None
  selector: { app: valkey }
  ports: [ { port: 6379, name: valkey } ]
---
apiVersion: apps/v1
kind: StatefulSet
metadata: { name: valkey, namespace: dev }
spec:
  serviceName: valkey
  replicas: 1
  selector: { matchLabels: { app: valkey } }
  template:
    metadata: { labels: { app: valkey } }
    spec:
      containers:
        - name: valkey
          image: valkey/valkey:8
          args: ["--requirepass","$(VALKEY_PASSWORD)","--appendonly","yes"]
          env:
            - { name: VALKEY_PASSWORD, valueFrom: { secretKeyRef: { name: valkey-credentials, key: password } } }
          ports: [ { containerPort: 6379 } ]
          resources:
            requests: { cpu: "100m", memory: "200Mi" }
            limits:   { cpu: "500m", memory: "512Mi" }
          readinessProbe:
            exec: { command: ["sh","-c","valkey-cli -a \"$VALKEY_PASSWORD\" ping | grep PONG"] }
            initialDelaySeconds: 5
            periodSeconds: 5
          volumeMounts:
            - { name: data, mountPath: /data }
  volumeClaimTemplates:
    - metadata: { name: data }
      spec:
        accessModes: ["ReadWriteOnce"]
        resources: { requests: { storage: 5Gi } }
```

Apply and validate:
```bash
kubectl -n dev apply -f ~/meesell-infra/dev/valkey.yaml --dry-run=server
kubectl -n dev apply -f ~/meesell-infra/dev/valkey.yaml
kubectl -n dev rollout status statefulset/valkey --timeout=120s
kubectl -n dev exec valkey-0 -- sh -c 'valkey-cli -a "$VALKEY_PASSWORD" ping'
```
Expected: `PONG`.

If `NOAUTH Authentication required.`: env var not injected. `kubectl -n dev describe pod valkey-0` and verify secret reference.

Rollback: `kubectl -n dev delete -f ~/meesell-infra/dev/valkey.yaml`.

Backup:
```bash
kubectl -n dev exec valkey-0 -- sh -c 'valkey-cli -a "$VALKEY_PASSWORD" BGSAVE'
TS=$(date +%Y%m%d-%H%M)
kubectl -n dev cp valkey-0:/data/appendonly.aof ~/meesell-backups/valkey-dev-${TS}.aof
```

---

## Section 7: Supabase Studio Deployment — Day 1

Studio UI only. Auth/Storage out of scope for Day 1.

`~/meesell-infra/dev/supabase-studio.yaml`:
```yaml
apiVersion: v1
kind: Service
metadata: { name: supabase-studio, namespace: dev }
spec:
  selector: { app: supabase-studio }
  ports: [ { port: 3000, targetPort: 3000, name: http } ]
---
apiVersion: apps/v1
kind: Deployment
metadata: { name: supabase-studio, namespace: dev }
spec:
  replicas: 1
  selector: { matchLabels: { app: supabase-studio } }
  template:
    metadata: { labels: { app: supabase-studio } }
    spec:
      containers:
        - name: studio
          image: supabase/studio:latest
          ports: [ { containerPort: 3000 } ]
          env:
            - { name: STUDIO_PG_META_URL, value: "http://postgres.dev.svc.cluster.local:8080" }
            - { name: POSTGRES_PASSWORD, valueFrom: { secretKeyRef: { name: postgres-credentials, key: password } } }
            - { name: DEFAULT_ORGANIZATION_NAME, value: "MeeSell" }
            - { name: DEFAULT_PROJECT_NAME, value: "meesell-dev" }
            - { name: SUPABASE_URL, value: "http://localhost:3000" }
            - { name: SUPABASE_PUBLIC_URL, value: "http://localhost:3000" }
          resources:
            requests: { cpu: "100m", memory: "256Mi" }
            limits:   { cpu: "500m", memory: "512Mi" }
          readinessProbe:
            httpGet: { path: /, port: 3000 }
            initialDelaySeconds: 15
            periodSeconds: 10
```

Apply and validate:
```bash
kubectl -n dev apply -f ~/meesell-infra/dev/supabase-studio.yaml --dry-run=server
kubectl -n dev apply -f ~/meesell-infra/dev/supabase-studio.yaml
kubectl -n dev rollout status deployment/supabase-studio --timeout=180s
kubectl -n dev port-forward svc/supabase-studio 3000:3000 &
PF_PID=$!; sleep 3
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000
kill $PF_PID
```
Expected: HTTP `200` or `307`.

If `ImagePullBackOff`: large image; `kubectl -n dev describe pod -l app=supabase-studio` and wait.

Rollback: `kubectl -n dev delete -f ~/meesell-infra/dev/supabase-studio.yaml`.

---

## Section 8: cert-manager + Traefik — Day 2

[DANGER] Depends on a domain. If domain not yet purchased, defer Sections 8–9 to Day 7; skip to Section 10.

### 8.1 Traefik via Helm

```bash
helm repo add traefik https://traefik.github.io/charts && helm repo update
kubectl create namespace traefik --dry-run=client -o yaml | kubectl apply -f -
helm upgrade --install traefik traefik/traefik \
  --namespace traefik \
  --set service.type=LoadBalancer \
  --set ports.web.port=80 --set ports.websecure.port=443 \
  --set additionalArguments="{--api.dashboard=false}"
kubectl -n traefik get pods
kubectl -n traefik get svc traefik
```
Expected: pod Running, service has external IP (on K3s single-node, the node IP).

### 8.2 cert-manager

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.5/cert-manager.yaml
kubectl -n cert-manager rollout status deployment/cert-manager           --timeout=120s
kubectl -n cert-manager rollout status deployment/cert-manager-webhook   --timeout=120s
kubectl -n cert-manager rollout status deployment/cert-manager-cainjector --timeout=120s
```

### 8.3 Let's Encrypt ClusterIssuer

`~/meesell-infra/cluster/letsencrypt.yaml`:
```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata: { name: letsencrypt-prod }
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: vaishnaviramoorthy@gmail.com
    privateKeySecretRef: { name: letsencrypt-prod-key }
    solvers:
      - http01: { ingress: { class: traefik } }
```

```bash
kubectl apply -f ~/meesell-infra/cluster/letsencrypt.yaml
kubectl get clusterissuer letsencrypt-prod
```
Expected: `READY True`.

Rollback:
```bash
kubectl delete -f ~/meesell-infra/cluster/letsencrypt.yaml
helm -n traefik uninstall traefik
kubectl delete -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.5/cert-manager.yaml
```

---

## Section 9: Ingress Configuration — Day 2 or Day 7

`<DOMAIN>` must be replaced with the founder's purchased domain.

`~/meesell-infra/dev/ingress-studio.yaml`:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: studio
  namespace: dev
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
spec:
  ingressClassName: traefik
  rules:
    - host: studio.<DOMAIN>
      http:
        paths:
          - path: /
            pathType: Prefix
            backend: { service: { name: supabase-studio, port: { number: 3000 } } }
  tls:
    - hosts: [ studio.<DOMAIN> ]
      secretName: studio-tls
```

Apply only after DNS A record points `studio.<DOMAIN>` to the VM IP:
```bash
dig +short studio.<DOMAIN>          # Expected: VM external IP
kubectl apply -f ~/meesell-infra/dev/ingress-studio.yaml
kubectl -n dev describe ingress studio
kubectl -n dev get certificate studio-tls
```
Expected: certificate `READY True` within ~2 minutes.

If cert stuck `False`:
- `kubectl -n dev describe certificate studio-tls`
- `kubectl -n dev get challenges`
- Most common: DNS not propagated. Wait, retry `dig`.

Rollback: `kubectl delete -f ~/meesell-infra/dev/ingress-studio.yaml`.

---

## Section 10: Secret Management Discipline

Rules:
- All secrets live in Kubernetes Secrets; never inline in committed YAML.
- All local secret files live in `~/.meesell-secrets/` (dir 700, files 600).
- `.gitignore` MUST contain `*.env`, `.meesell-secrets/`, `*.sql` (backups may contain user data).
- NEVER paste secret contents into chat, logs, or tickets.
- NEVER `kubectl get secret -o yaml` and share output.
- Pod logs MUST NOT echo secrets; use structured logging with redaction.

Audit:
```bash
kubectl -n dev get secrets -o name
ls -la ~/.meesell-secrets/
git -C ~/meesell-infra status --ignored | head
```
Confirm: only expected secret names, files `-rw-------`, no untracked secret files.

Rotation (postgres example):
```bash
NEW_PW=$(openssl rand -base64 32 | tr -d '\n')
kubectl -n dev create secret generic postgres-credentials \
  --from-literal=username=meesell --from-literal=password="$NEW_PW" --from-literal=database=meesell \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n dev exec postgres-0 -- psql -U meesell -d postgres -c "ALTER USER meesell WITH PASSWORD '$NEW_PW';"
kubectl -n dev rollout restart statefulset/postgres
echo -n "$NEW_PW" > ~/.meesell-secrets/dev-postgres-password
chmod 600 ~/.meesell-secrets/dev-postgres-password
unset NEW_PW
```
Validation: `kubectl -n dev exec postgres-0 -- pg_isready` returns `accepting connections`.

---

## Section 11: Daily Operations Checklist

Morning (every working day):
```bash
kubectl get pods -A | grep -vE "Running|Completed" || echo "All pods healthy"
kubectl top nodes
kubectl top pods -A --sort-by=memory | head -10
gcloud compute instances describe meesell-dev --zone=asia-south1-a --format="value(status)"
ls -lt ~/meesell-backups/ | head -5
gcloud beta billing budgets list --billing-account=$(gcloud billing accounts list --format="value(ACCOUNT_ID)" | head -1)
```
Expected: "All pods healthy" or only Completed pods; node CPU/mem < 80%; VM RUNNING; backup in last 24h.

If any check fails, jump to Section 12.

---

## Section 12: Incident Response Runbooks

### 12.1 Pod won't start
```bash
kubectl -n <ns> describe pod <pod>
kubectl -n <ns> logs <pod> --tail=100
kubectl -n <ns> logs <pod> --previous --tail=100 2>/dev/null
kubectl -n <ns> get events --sort-by=.lastTimestamp | tail -20
```
Common causes: PVC not bound (`kubectl get pvc -n <ns>`, check storage class); `ImagePullBackOff` (wrong image tag); `OOMKilled` (raise memory limit, but identify the leak first).

### 12.2 VM out of disk
```bash
gcloud compute ssh meesell-dev --zone=asia-south1-a --tunnel-through-iap --command="df -h /"
kubectl top nodes
sudo crictl rmi --prune
sudo journalctl --vacuum-time=3d
```
If still > 85%, resize disk (founder approval):
```bash
gcloud compute disks resize meesell-dev --zone=asia-south1-a --size=50GB
```
Then on VM: `sudo growpart /dev/sda 1 && sudo resize2fs /dev/sda1`.

### 12.3 K3s API unreachable from laptop
```bash
gcloud compute instances describe meesell-dev --zone=asia-south1-a --format="value(status)"
gcloud compute firewall-rules describe meesell-dev-k3s-api
curl -k https://$(gcloud compute instances describe meesell-dev --zone=asia-south1-a --format="value(networkInterfaces[0].accessConfigs[0].natIP)"):6443/healthz
```
If VM stopped: `gcloud compute instances start meesell-dev --zone=asia-south1-a`.
If founder IP changed:
```bash
NEW_IP=$(curl -s ifconfig.me)
gcloud compute firewall-rules update meesell-dev-k3s-api --source-ranges=${NEW_IP}/32
```
If K3s service down: SSH and `sudo systemctl restart k3s`.

### 12.4 Database connection refused
```bash
kubectl -n <ns> get pods -l app=postgres
kubectl -n <ns> get endpoints postgres
kubectl -n <ns> exec postgres-0 -- pg_isready -U meesell -d meesell
kubectl -n <ns> run pgtest --rm -it --image=postgres:16 --restart=Never -- \
  psql "postgres://meesell:$(cat ~/.meesell-secrets/dev-postgres-password)@postgres.<ns>.svc.cluster.local:5432/meesell" -c "SELECT 1;"
```
If endpoints empty, StatefulSet/service selector is wrong.

---

## Section 13: Cost Monitoring Discipline

Weekly:
```bash
gcloud billing accounts list
gcloud beta billing budgets list --billing-account=$(gcloud billing accounts list --format="value(ACCOUNT_ID)" | head -1)
gcloud compute instances list --format="table(name,zone,machineType.basename(),status)"
gcloud compute disks list --format="table(name,sizeGb,type,zone)"
```

Thresholds:
- 50% consumed: notify founder, no action.
- 75% consumed: pause non-essential workloads, review with founder.
- 90% consumed: STOP. Snapshot, then shut down on founder's call:
  ```bash
  gcloud compute disks snapshot meesell-dev --zone=asia-south1-a --snapshot-names=meesell-dev-final-$(date +%Y%m%d)
  gcloud compute instances stop meesell-dev --zone=asia-south1-a   # founder approval
  ```

Budget creation (one-time if missing):
```bash
gcloud beta billing budgets create \
  --billing-account=$(gcloud billing accounts list --format="value(ACCOUNT_ID)" | head -1) \
  --display-name="meesell-dev-budget" \
  --budget-amount=300USD \
  --threshold-rule=percent=0.5 \
  --threshold-rule=percent=0.75 \
  --threshold-rule=percent=0.9
```

---

## Section 14: Day 1 Acceptance — All Must Pass

Tick only if expected output matches.

- [ ] `gcloud compute instances list | grep meesell-dev` shows `RUNNING`.
- [ ] `gcloud compute firewall-rules list --filter="name~meesell-dev"` shows three rules; K3s API scoped to founder IP/32.
- [ ] `kubectl get nodes` shows `meesell-dev-master   Ready`.
- [ ] `kubectl get namespaces` shows `dev` and `staging` with `env` label.
- [ ] `kubectl -n dev get pods` shows `postgres-0`, `valkey-0`, `supabase-studio-*` all `1/1 Running`.
- [ ] `kubectl -n dev exec postgres-0 -- pg_isready` returns `accepting connections`.
- [ ] `kubectl -n dev exec valkey-0 -- sh -c 'valkey-cli -a "$VALKEY_PASSWORD" ping'` returns `PONG`.
- [ ] Port-forward to `supabase-studio` returns HTTP `200`/`307`.
- [ ] Local `kubectl get nodes` works from founder's laptop.
- [ ] Manual backup files exist in `~/meesell-backups/` (postgres + valkey).
- [ ] `~/.meesell-secrets/` is `700`, files are `600`.
- [ ] `kubectl -n dev get secrets` lists `postgres-credentials` and `valkey-credentials`.
- [ ] `kubectl -n dev get events | grep -i error` returns nothing recent.
- [ ] GCP billing budget exists with 50/75/90% thresholds.
- [ ] No changes against `meesell-vm`, `shotfox-platform`, `shotfox-mvp1-alpha-dev` (compare to `/tmp/meesell-pre-day1-state.txt`).

If any item fails, STOP. Do not proceed to Day 2.

---

## Section 15: Day 1 → Day 2 Hand-off

Connection strings (in-cluster):
- PostgreSQL: `postgres://meesell:<password>@postgres.dev.svc.cluster.local:5432/meesell`
- Valkey: `redis://:<password>@valkey.dev.svc.cluster.local:6379/0`

Password retrieval (laptop, K3s context):
```bash
kubectl -n dev get secret postgres-credentials -o jsonpath='{.data.password}' | base64 -d
kubectl -n dev get secret valkey-credentials   -o jsonpath='{.data.password}' | base64 -d
```
Use only when wiring app deployments; never echo to logs.

Namespace conventions:
- `dev` — Day 1 work and ongoing engineering.
- `staging` — created Day 1, populated Day 7 with mirror of `dev` via Kustomize overlays.
- `prod` — created Week 2 after staging passes acceptance for one full week.

Secret pattern for a new pod:
```yaml
env:
  - name: DATABASE_URL
    value: "postgres://meesell:$(POSTGRES_PASSWORD)@postgres.dev.svc.cluster.local:5432/meesell"
  - name: POSTGRES_PASSWORD
    valueFrom: { secretKeyRef: { name: postgres-credentials, key: password } }
```

Safe deployment template:
1. Write manifest under `~/meesell-infra/dev/<name>.yaml`.
2. `kubectl -n dev diff -f <file>` — review.
3. **[MANDATORY GATE]** `kubectl -n dev apply -f <file> --dry-run=server` — server-side
   validate. **Founder ruling 2026-06-11: `kubectl apply --dry-run=server` is a MANDATORY
   pre-apply checklist item at EVERY deploy (dev, staging, future prod). It is never
   optional and never skipped.** A clean server-side dry-run is a hard precondition for
   step 4. If the cluster is unreachable at authoring time, the dry-run is deferred to
   deploy time (per F3) but MUST run — and pass — before any real `apply`.
4. `kubectl -n dev apply -f <file>` — apply (only after step 3 passes clean).
5. `kubectl -n dev rollout status deployment/<name>` — wait.
6. Readiness probe and resource limits required. No deployment lands without both.
7. Commit manifest to infra repo (NOT secrets).

Not yet wired (do not assume):
- TLS/ingress on real domain (Sections 8–9 + domain purchase).
- Supabase Auth/Storage — Studio only.
- Off-VM backup storage (currently laptop-local).
- Observability stack (Prometheus/Grafana/Loki) — Week 2.
- `prod` namespace.

Hand-off complete when Section 14 is fully ticked and this section has been read by the receiving agent.
