#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-ds-workspace-mcp:smoke}"
WORK_ROOT="$(mktemp -d)"
CONTAINER_ONE="ds-workspace-mcp-smoke-one-$$"
CONTAINER_TWO="ds-workspace-mcp-smoke-two-$$"

cleanup() {
  docker rm -f "${CONTAINER_ONE}" "${CONTAINER_TWO}" >/dev/null 2>&1 || true
  rm -rf "${WORK_ROOT}"
}
trap cleanup EXIT

mkdir -p "${WORK_ROOT}/data" "${WORK_ROOT}/reports"
chmod 0777 "${WORK_ROOT}/data" "${WORK_ROOT}/reports"

cat > "${WORK_ROOT}/data/smoke.csv" <<'CSV'
feature,target
1,1
2,2
3,3
4,4
5,5
6,6
7,7
8,8
9,9
10,10
11,11
12,12
CSV

docker build -t "${IMAGE_NAME}" .

docker run -d \
  --name "${CONTAINER_ONE}" \
  -e MCP_TRANSPORT=streamable-http \
  -e MCP_HOST=0.0.0.0 \
  -e MCP_PORT=8000 \
  -e MCP_DATA_ROOT=/app/data \
  -e MCP_REPORTS_ROOT=/app/reports \
  -v "${WORK_ROOT}/data:/app/data" \
  -v "${WORK_ROOT}/reports:/app/reports" \
  "${IMAGE_NAME}" >/dev/null

sleep 5

docker exec "${CONTAINER_ONE}" ds-workspace-mcp list-datasets | grep -F "smoke.csv"
docker exec "${CONTAINER_ONE}" ds-workspace-mcp save-modeling-report \
  smoke.csv \
  --target-column target \
  --output-name smoke-report.md
test -f "${WORK_ROOT}/reports/smoke-report.md"

docker rm -f "${CONTAINER_ONE}" >/dev/null

docker run -d \
  --name "${CONTAINER_TWO}" \
  -e MCP_TRANSPORT=streamable-http \
  -e MCP_HOST=0.0.0.0 \
  -e MCP_PORT=8000 \
  -e MCP_DATA_ROOT=/app/data \
  -e MCP_REPORTS_ROOT=/app/reports \
  -v "${WORK_ROOT}/data:/app/data" \
  -v "${WORK_ROOT}/reports:/app/reports" \
  "${IMAGE_NAME}" >/dev/null

sleep 3

docker exec "${CONTAINER_TWO}" ds-workspace-mcp list-modeling-reports | grep -F "smoke-report.md"
