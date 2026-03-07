#!/usr/bin/env bash
# Teardown K8s E2E test resources (does NOT delete the Kind cluster itself).
set -euo pipefail

RELEASE="${RELEASE:-acko}"
NAMESPACE="${NAMESPACE:-acko-system}"

echo "=== K8s E2E Teardown ==="

# 1. Delete test AerospikeCluster resources
echo "[...] Deleting test AerospikeCluster resources..."
kubectl delete aerospikeclusters --all -n "${NAMESPACE}" --ignore-not-found --timeout=60s 2>/dev/null || true
echo "[OK] AerospikeCluster resources cleaned up"

# 2. Uninstall Helm release
echo "[...] Uninstalling Helm release '${RELEASE}'..."
helm uninstall "${RELEASE}" -n "${NAMESPACE}" --ignore-not-found 2>/dev/null || true
echo "[OK] Helm release uninstalled"

echo ""
echo "=== Teardown complete ==="
echo "Kind cluster is still running. To delete it: kind delete cluster --name kind"
