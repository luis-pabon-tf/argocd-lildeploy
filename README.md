# argocd-lildeploy

Minimal FastAPI app for evaluating Argo CD as a CI/CD solution. Manifests in `k8s/`
are the source of truth: Argo CD watches this repo and keeps the cluster in sync.

Code changes deploy automatically too: GitHub Actions builds each push to
`ghcr.io/luis-pabon-tf/argocd-lildeploy:0.1.<run>`, and Argo CD Image Updater
commits the new tag into `k8s/kustomization.yaml` (git write-back), which Argo CD
then syncs. Full loop: `git push` → CI image → tag bump commit → rollout.

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
# 1. Cluster (images are pulled from ghcr.io, built by GitHub Actions)
kind create cluster --name argocd-eval

# 2. Install Argo CD
kubectl create namespace argocd
kubectl apply -n argocd --server-side --force-conflicts \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=Ready pods --all -n argocd --timeout=300s

# 3. Register the app (Argo CD pulls k8s/ from GitHub)
kubectl apply -f argocd/application.yaml

# 3b. Image Updater (auto-deploys new images from ghcr.io)
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj-labs/argocd-image-updater/stable/config/install.yaml
kubectl -n argocd create secret generic git-creds \
  --from-literal=username=luis-pabon-tf --from-literal=password=<GitHub PAT with repo write>
kubectl apply -f argocd/imageupdater.yaml

# 4. Argo CD UI at https://localhost:8080 (user: admin)
kubectl port-forward svc/argocd-server -n argocd 8080:443
argocd admin initial-password -n argocd

# 5. Reach the app
kubectl port-forward svc/lildeploy -n lildeploy 8081:80
curl http://localhost:8081/health
```

## The GitOps loop

**Manifest changes:** edit anything under `k8s/` (e.g. bump `replicas`), commit, push.
Argo CD detects the change (polls every ~3 min; use the UI's Refresh for instant) and
applies it — no kubectl, no manual deploy. `prune` and `selfHeal` are enabled:
resources deleted from git are removed from the cluster, and manual drift is reverted.

**Code changes:** edit `app/`, commit, push. GitHub Actions builds and pushes
`ghcr.io/luis-pabon-tf/argocd-lildeploy:0.1.<run>`; Image Updater (checks every ~2 min)
commits the tag bump to `k8s/kustomization.yaml`; Argo CD rolls the deployment.
The workflow's `paths` filter excludes `k8s/`, so Image Updater's own commits never
trigger rebuilds.

## Not covered in this eval (next steps for real use)

- Write-back auth uses a personal access token; production would use a GitHub App
  or deploy key. Tag scheme `0.1.<run>` is eval-simple; real projects tag releases.
- Kustomize overlays for dev/prod, private images/repos, SSO/RBAC, notifications.
