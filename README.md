# argocd-lildeploy

![build](https://github.com/luis-pabon-tf/argocd-lildeploy/actions/workflows/build-image.yml/badge.svg)

Minimal FastAPI app for evaluating Argo CD as a GitOps/CD solution. Deploys are fully automated from `git push` as you can see below.

## What's in this repo

- `app/` — the FastAPI app (two toy endpoints + health check)
- `Dockerfile` — how the app becomes a container image
- `.github/workflows/build-image.yml` — CI: builds and pushes the image to ghcr.io
  when app code changes on `main`
- `k8s/` — the Kubernetes manifests Argo CD keeps the cluster synced to
- `argocd/` — the Argo CD `Application` and `ImageUpdater` definitions, applied
  once during setup

## Update/Deployment Loop
`git push` → CI image → tag bump commit → rollout.

* Edit `app/` in a branch, then merge a PR into `main`.
* GitHub Actions builds and pushes `ghcr.io/luis-pabon-tf/argocd-lildeploy:0.1.<run>`.
* Image Updater commits the tag bump to `k8s/kustomization.yaml`.
* Argo CD rolls the deployment.

End-to-end is typically ~3–5 minutes:
* Image Updater polls every ~2 min.
* Argo CD polls every ~3 min and the UI also has a force-refresh option.

Only pushes to `main` build images, and the workflow's `paths` filter excludes `k8s/`, so Image Updater's own commits never trigger rebuilds.

The manifests in `k8s/` are the source of truth — Argo CD keeps the cluster matching
them.

Image Updater's role is to keep those manifests current: when a new image tag appears in ghcr.io, it updates `newTag` inside `kustomization.yaml`.

Manifest edits deploy the same way: change anything under `k8s/` (e.g. bump `replicas`), push, and Argo CD applies it. `prune` and `selfHeal` are enabled: resources deleted from git are removed from the cluster, and manual kubectl changes are reverted.

## Argo CD evaluation setup (local kind cluster)

Prereqs:
* [Docker](https://docs.docker.com/get-docker/)
* [kubectl](https://kubernetes.io/docs/tasks/tools/)
* [kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)
* [argocd CLI](https://argo-cd.readthedocs.io/en/stable/cli_installation/)

Install via your platform's package manager (winget, brew, apt/snap, choco) or the linked docs.

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

# 3b. Image Updater (watches ghcr.io, commits tag bumps to git)
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj-labs/argocd-image-updater/stable/config/install.yaml
# fine-grained PAT: Repository access = this repo only; Permissions: Contents = Read and write
kubectl -n argocd create secret generic git-creds \
  --from-literal=username=<GitHub username> --from-literal=password=<GitHub PAT>
kubectl apply -f argocd/imageupdater.yaml

# 4. Argo CD UI at https://localhost:8080 (user: admin)
# port-forward blocks the terminal and must stay running while you use the UI
kubectl port-forward svc/argocd-server -n argocd 8080:443
argocd admin initial-password -n argocd

# 5. Reach the app (same deal: keep the port-forward running, use a second terminal)
kubectl port-forward svc/lildeploy -n lildeploy 8081:80
curl http://localhost:8081/health

# 6. Teardown when done — removes the whole cluster, Argo CD and all
kind delete cluster --name argocd-eval
```

Reproducing from a fork? After the first CI run, make the ghcr package public (GitHub → your profile → Packages → package settings → Change visibility) so the cluster can pull it anonymously, and update the image/repo URLs in `k8s/` and `argocd/` to your fork.

## If something looks stuck

- **Code change not deploying?**
  Give it ~3–5 min. Then check, in order:
    - The Actions run succeeded
    - A `build: automatic update` commit from Image Updater landed on `main`
    - The app's sync status in the Argo CD UI
- **Can't reach the app or the UI?**
  The relevant `kubectl port-forward` probably
  isn't running — it's a foreground process, not a persistent setting.

## In case you'd like to run this locally (no Kubernetes)

```sh
uv sync
uv run uvicorn app.main:app --port 8000
```

## Endpoints

- `GET /` — hello message
- `GET /bye` — goodbye message (added post-setup to demo the code-change loop)
- `GET /health` — health check (also used as Kubernetes liveness/readiness probe)

## Potential next steps

- Write-back auth uses a personal access token; production would use a GitHub App or deploy key.
- The `0.1.<run>` tag scheme just increments a CI build counter, while in production we'd probably go with semantic versioning.
- Kustomize overlays for dev/prod, private images/repos, SSO/RBAC, notifications.
