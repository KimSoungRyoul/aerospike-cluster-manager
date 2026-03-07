#!/usr/bin/env bash
# Setup Kind cluster with operator + UI for Playwright K8s E2E tests.
# Prerequisites: kind, kubectl, helm, podman
set -euo pipefail

KIND_CLUSTER="${KIND_CLUSTER:-kind}"
RELEASE="${RELEASE:-acko}"
NAMESPACE="${NAMESPACE:-acko-system}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../../.." && pwd)"
CHART_DIR="${REPO_ROOT}/charts/aerospike-ce-kubernetes-operator"
OPERATOR_IMG="ghcr.io/kimsoungryoul/aerospike-ce-kubernetes-operator:e2e"
FRONTEND_IMG="aerospike-cluster-manager-frontend:e2e"
BACKEND_IMG="aerospike-cluster-manager-backend:e2e"

echo "=== K8s E2E Setup ==="
echo "Kind cluster: ${KIND_CLUSTER}"
echo "Helm release: ${RELEASE} in namespace ${NAMESPACE}"
echo ""

# 1. Check Kind cluster exists
if ! kind get clusters 2>/dev/null | grep -q "^${KIND_CLUSTER}$"; then
  echo "ERROR: Kind cluster '${KIND_CLUSTER}' not found."
  echo "Create it with: kind create cluster --config ${REPO_ROOT}/kind-config.yaml --name ${KIND_CLUSTER}"
  exit 1
fi
echo "[OK] Kind cluster '${KIND_CLUSTER}' exists"

# 2. Install cert-manager (if not present)
if ! kubectl get namespace cert-manager &>/dev/null; then
  echo "[...] Installing cert-manager..."
  kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.17.2/cert-manager.yaml
  echo "[...] Waiting for cert-manager webhook..."
  kubectl wait --for=condition=Available deployment/cert-manager -n cert-manager --timeout=120s
  kubectl wait --for=condition=Available deployment/cert-manager-webhook -n cert-manager --timeout=120s
  kubectl wait --for=condition=Available deployment/cert-manager-cainjector -n cert-manager --timeout=120s
  echo "[OK] cert-manager installed"
else
  echo "[OK] cert-manager already installed"
fi

# 3. Build operator image
echo "[...] Building operator image..."
cd "${REPO_ROOT}"
make docker-build IMG="${OPERATOR_IMG}"
kind load docker-image "${OPERATOR_IMG}" --name "${KIND_CLUSTER}"
echo "[OK] Operator image loaded into Kind"

# 4. Build UI images (frontend + backend)
echo "[...] Building UI frontend image..."
cd "${REPO_ROOT}/aerospike-cluster-manager"
podman build -t "${FRONTEND_IMG}" -f frontend/Dockerfile frontend/
kind load docker-image "${FRONTEND_IMG}" --name "${KIND_CLUSTER}"
echo "[OK] Frontend image loaded into Kind"

echo "[...] Building UI backend image..."
podman build -t "${BACKEND_IMG}" -f backend/Dockerfile backend/
kind load docker-image "${BACKEND_IMG}" --name "${KIND_CLUSTER}"
echo "[OK] Backend image loaded into Kind"

# 5. Helm install (operator + UI + default templates)
echo "[...] Helm installing ${RELEASE}..."
helm upgrade --install "${RELEASE}" "${CHART_DIR}" \
  --namespace "${NAMESPACE}" --create-namespace \
  --set image.repository=ghcr.io/kimsoungryoul/aerospike-ce-kubernetes-operator \
  --set image.tag=e2e \
  --set image.pullPolicy=Never \
  --set ui.enabled=true \
  --set ui.image.repository=aerospike-cluster-manager-frontend \
  --set ui.image.tag=e2e \
  --set ui.image.pullPolicy=Never \
  --set ui.backendImage.repository=aerospike-cluster-manager-backend \
  --set ui.backendImage.tag=e2e \
  --set ui.backendImage.pullPolicy=Never \
  --set ui.k8s.enabled=true \
  --set defaultTemplates.enabled=true \
  --wait --timeout=300s
echo "[OK] Helm release '${RELEASE}' installed"

# 6. Wait for UI pod readiness
echo "[...] Waiting for UI pod readiness..."
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/component=ui \
  -n "${NAMESPACE}" --timeout=120s
echo "[OK] UI pod is ready"

echo ""
echo "=== Setup complete ==="
echo ""
echo "Start port-forward in a separate terminal:"
echo "  kubectl port-forward svc/${RELEASE}-aerospike-ce-kubernetes-operator-ui 3100:3000 -n ${NAMESPACE}"
echo ""
echo "Then run tests:"
echo "  npm run test:e2e:k8s"
