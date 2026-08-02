#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
OUTPUT_DIR="${BMS_QUALITY_OUTPUT_DIR:-${REPO_ROOT}/task-work/BMS-COMPREHENSIVE-QUALITY}"
BROWSER_REPORT=""
PERFORMANCE_REPORT=""
SKIP_BUILD=0

usage() {
  cat <<'EOF'
Usage:
  bash scripts/testing/comprehensive-quality.sh [options]

Options:
  --output-dir PATH         Artifact directory.
  --browser-report PATH     Browser baseline JSON produced by the controller helper.
  --performance-report PATH
                            Runtime performance JSON produced by the controller helper.
  --skip-build              Reassemble existing evidence without deleting or rebuilding.
  -h, --help                Show this help.

The default run removes only site/_site and site/.quarto, runs the canonical
comprehensive build gate, runs the static inventory, and reports browser and
performance as NOT RUN unless their controller-produced reports are supplied.
Human UX review always remains NOT RUN in this automated entrypoint.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      [[ $# -ge 2 ]] || { printf 'ERROR: --output-dir requires a path.\n' >&2; exit 2; }
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --browser-report)
      [[ $# -ge 2 ]] || { printf 'ERROR: --browser-report requires a path.\n' >&2; exit 2; }
      BROWSER_REPORT="$2"
      shift 2
      ;;
    --performance-report)
      [[ $# -ge 2 ]] || { printf 'ERROR: --performance-report requires a path.\n' >&2; exit 2; }
      PERFORMANCE_REPORT="$2"
      shift 2
      ;;
    --skip-build)
      SKIP_BUILD=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'ERROR: Unrecognized argument: %s\n\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -x "${REPO_ROOT}/.venv/Scripts/python.exe" ]] &&
  "${REPO_ROOT}/.venv/Scripts/python.exe" -c 'import sys' >/dev/null 2>&1; then
  PYTHON_COMMAND=("${REPO_ROOT}/.venv/Scripts/python.exe")
elif command -v py >/dev/null 2>&1; then
  PYTHON_COMMAND=(py)
elif command -v python >/dev/null 2>&1; then
  PYTHON_COMMAND=(python)
else
  printf 'ERROR: Neither a working project Python, py, nor python was found.\n' >&2
  exit 127
fi

cd "${REPO_ROOT}"
mkdir -p "${OUTPUT_DIR}/build" "${OUTPUT_DIR}/logs" "${OUTPUT_DIR}/static"
BUILD_REPORT="${OUTPUT_DIR}/build/build.json"
STATIC_REPORT="${OUTPUT_DIR}/static/static-inventory.json"

if [[ ${SKIP_BUILD} -eq 0 ]]; then
  SITE_OUTPUT="${REPO_ROOT}/site/_site"
  QUARTO_WORK="${REPO_ROOT}/site/.quarto"
  [[ "${SITE_OUTPUT}" == "${REPO_ROOT}/site/_site" ]] || {
    printf 'ERROR: Refusing unexpected rendered-output path: %s\n' "${SITE_OUTPUT}" >&2
    exit 2
  }
  [[ "${QUARTO_WORK}" == "${REPO_ROOT}/site/.quarto" ]] || {
    printf 'ERROR: Refusing unexpected Quarto work path: %s\n' "${QUARTO_WORK}" >&2
    exit 2
  }
  rm -rf -- "${SITE_OUTPUT}" "${QUARTO_WORK}"
  BUILD_STARTED_NS="$("${PYTHON_COMMAND[@]}" -c 'import time; print(time.monotonic_ns())')"
  set +e
  bash scripts/testing/build/comprehensive.sh 2>&1 | tee "${OUTPUT_DIR}/logs/clean-build.log"
  BUILD_EXIT=${PIPESTATUS[0]}
  set -e
  BUILD_FINISHED_NS="$("${PYTHON_COMMAND[@]}" -c 'import time; print(time.monotonic_ns())')"
  BUILD_DURATION_MS="$("${PYTHON_COMMAND[@]}" -c 'import sys; print((int(sys.argv[2]) - int(sys.argv[1])) // 1000000)' "${BUILD_STARTED_NS}" "${BUILD_FINISHED_NS}")"
  if [[ -d "${SITE_OUTPUT}" ]]; then
    RENDERED_FILE_COUNT="$(find "${SITE_OUTPUT}" -type f | wc -l | tr -d '[:space:]')"
  else
    RENDERED_FILE_COUNT=0
  fi
  BUILD_STATUS=PASS
  [[ ${BUILD_EXIT} -eq 0 ]] || BUILD_STATUS=FAIL
  "${PYTHON_COMMAND[@]}" scripts/testing/quality/quality_reports.py record-build \
    --output "${BUILD_REPORT}" \
    --status "${BUILD_STATUS}" \
    --command "bash scripts/testing/build/comprehensive.sh" \
    --duration-ms "${BUILD_DURATION_MS}" \
    --rendered-file-count "${RENDERED_FILE_COUNT}"

  set +e
  "${PYTHON_COMMAND[@]}" scripts/testing/quality/static_inventory.py \
    --repo-root "${REPO_ROOT}" \
    --site-dir "${SITE_OUTPUT}" \
    --output "${STATIC_REPORT}" 2>&1 | tee "${OUTPUT_DIR}/logs/static-inventory.log"
  STATIC_EXIT=${PIPESTATUS[0]}
  set -e
  if [[ ${STATIC_EXIT} -ne 0 ]]; then
    "${PYTHON_COMMAND[@]}" scripts/testing/quality/quality_reports.py record-component \
      --output "${STATIC_REPORT}" \
      --status FAIL \
      --route-or-file scripts/testing/quality/static_inventory.py \
      --evidence "Static inventory exited with code ${STATIC_EXIT}; see logs/static-inventory.log." \
      --reproduction "Run the canonical comprehensive-quality entrypoint."
  fi
fi

if [[ -z "${BROWSER_REPORT}" && -f "${OUTPUT_DIR}/browser/browser-baseline.json" ]]; then
  BROWSER_REPORT="${OUTPUT_DIR}/browser/browser-baseline.json"
fi
if [[ -z "${PERFORMANCE_REPORT}" && -f "${OUTPUT_DIR}/performance/runtime-performance.json" ]]; then
  PERFORMANCE_REPORT="${OUTPUT_DIR}/performance/runtime-performance.json"
fi

ASSEMBLE_ARGUMENTS=(
  assemble
  --output-dir "${OUTPUT_DIR}"
  --contract scripts/testing/quality/comparison-contract.json
  --build "${BUILD_REPORT}"
  --static "${STATIC_REPORT}"
)
if [[ -n "${BROWSER_REPORT}" ]]; then
  ASSEMBLE_ARGUMENTS+=(--browser "${BROWSER_REPORT}")
fi
if [[ -n "${PERFORMANCE_REPORT}" ]]; then
  ASSEMBLE_ARGUMENTS+=(--performance "${PERFORMANCE_REPORT}")
fi

"${PYTHON_COMMAND[@]}" scripts/testing/quality/quality_reports.py "${ASSEMBLE_ARGUMENTS[@]}"
