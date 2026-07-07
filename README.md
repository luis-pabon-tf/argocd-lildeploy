# argocd-lildeploy

Minimal FastAPI app for evaluating Argo CD as a CI/CD solution. Manifests in `k8s/`
are the source of truth: Argo CD watches this repo and keeps the cluster in sync.

## Endpoints

- `GET /` — hello world
- `GET /health` — health check (also used as Kubernetes liveness/readiness probe)

## Run locally (no Kubernetes)

```sh
uv sync
uv run uvicorn app.main:app --port 8000
```

## Argo CD evaluation setup (local kind cluster)

Prereqs: Docker, kubectl, kind, argocd CLI (`winget install Kubernetes.kind argoproj.argocd`).

```sh
# 1. Cluster + image (no registry needed: image is sideloaded into kind)
kind create cluster --name argocd-eval
docker build -t lildeploy:0.1.0 .
kind load docker-image lildeploy:0.1.0 --name argocd-eval

# 2. Install Argo CD
kubectl create namespace argocd
kubectl apply -n argocd --server-side --force-conflicts \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=Ready pods --all -n argocd --timeout=300s

# 3. Register the app (Argo CD pulls k8s/ from GitHub)
kubectl apply -f argocd/application.yaml

# 4. Argo CD UI at https://localhost:8080 (user: admin)
kubectl port-forward svc/argocd-server -n argocd 8080:443
argocd admin initial-password -n argocd

# 5. Reach the app
kubectl port-forward svc/lildeploy -n lildeploy 8081:80
curl http://localhost:8081/health
```

## The GitOps loop

Edit anything under `k8s/` (e.g. bump `replicas`), commit, push. Argo CD detects the
change (polls every ~3 min; use the UI's Refresh for instant) and applies it — no
kubectl, no manual deploy. `prune` and `selfHeal` are enabled: resources deleted from
git are removed from the cluster, and manual cluster drift is reverted.

## Not covered in this eval (next steps for real use)

- Image CI: a pipeline would push images to a registry and bump the tag in `k8s/`
  (or use Argo CD Image Updater). Here the image is sideloaded with a static tag.
- Kustomize overlays for dev/prod, private-repo credentials, SSO/RBAC, notifications.
