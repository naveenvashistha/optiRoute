#!/usr/bin/env bash
# Run on optiroute-vm: sudo bash deploy.sh <commit-sha> [release-directory]
set -euo pipefail
umask 077

APP_DIR=/opt/optiroute
REGISTRY=asia-south1-docker.pkg.dev
RUNTIME_ACCOUNT=optiroute-runtime@optiroute-512819.iam.gserviceaccount.com
METADATA=http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default

if [[ $# -lt 1 || $# -gt 2 || ! "$1" =~ ^[0-9a-f]{40}$ ]]; then
  echo 'Usage: sudo bash deploy.sh <40-character lowercase Git commit SHA> [absolute release-directory]' >&2
  exit 1
fi
if [[ $(id -u) != 0 ]]; then
  echo 'Run this script with sudo.' >&2
  exit 1
fi
for command in docker curl jq flock mktemp install; do
  if ! command -v "$command" >/dev/null; then
    echo "Required command is missing: $command" >&2
    exit 1
  fi
done
RELEASE_DIR=${2:-$APP_DIR}
if [[ "$RELEASE_DIR" != /* ]]; then
  echo 'The release directory must be an absolute path.' >&2
  exit 1
fi
for file in .env backend/.env; do
  if [[ ! -f "$APP_DIR/$file" ]]; then
    echo "Required deployment file is missing: $APP_DIR/$file" >&2
    exit 1
  fi
done
for file in compose.yaml compose.production.yaml deploy/deploy.sh \
  deploy/nginx-trusted-proxy.conf deploy/nginx-forwarded-scheme.map; do
  if [[ ! -f "$RELEASE_DIR/$file" ]]; then
    echo "Required release file is missing: $RELEASE_DIR/$file" >&2
    exit 1
  fi
done

cd "$APP_DIR"
# Prevent two deployments (including manual runs) from updating the app together.
exec 9> .deploy.lock
flock -n 9 || { echo 'Another deployment is already running.' >&2; exit 1; }

docker_config_dir=''
next_env=''
cleanup() {
  # These paths are created by mktemp below, never supplied by a caller.
  if [[ -n "$next_env" ]]; then rm -f -- "$next_env"; fi
  if [[ -n "$docker_config_dir" ]]; then rm -rf -- "$docker_config_dir"; fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Shell variables take precedence over .env during validation and image pulls.
# Keep the existing release selection on disk until all images are downloaded.
export IMAGE_TAG="$1"
compose_base=(docker compose --project-name optiroute --project-directory "$APP_DIR"
  --env-file "$APP_DIR/.env")
release_compose=("${compose_base[@]}" -f "$RELEASE_DIR/compose.yaml"
  -f "$RELEASE_DIR/compose.production.yaml")
compose=("${compose_base[@]}" -f "$APP_DIR/compose.yaml"
  -f "$APP_DIR/compose.production.yaml")

echo "Validating deployment configuration for $IMAGE_TAG..."
"${release_compose[@]}" config --quiet

runtime=$(curl --fail --silent --show-error --noproxy '*' \
  --connect-timeout 5 --max-time 10 -H 'Metadata-Flavor: Google' "$METADATA/email")
if [[ "$runtime" != "$RUNTIME_ACCOUNT" ]]; then
  echo 'The VM does not have the expected runtime service account attached.' >&2
  exit 1
fi

# Use fresh VM credentials without changing /root/.docker/config.json or keeping
# the access token after this run. Never enable shell tracing for this script.
docker_config_dir=$(mktemp -d)
export DOCKER_CONFIG="$docker_config_dir"
echo 'Authenticating to Artifact Registry with the VM runtime account...'
curl --fail --silent --show-error --noproxy '*' \
  --connect-timeout 5 --max-time 10 -H 'Metadata-Flavor: Google' "$METADATA/token" \
  | jq -er '.access_token | select(type == "string" and length > 0)' \
  | docker login --username oauth2accesstoken --password-stdin "$REGISTRY"

echo 'Downloading images before changing running containers...'
"${release_compose[@]}" pull --policy always backend frontend
"${release_compose[@]}" pull --policy missing redis

# CI uploads into its own home first. Install only the versioned deployment
# files after successful pulls, under the same lock as the container update.
if [[ "$RELEASE_DIR" != "$APP_DIR" ]]; then
  echo 'Installing release configuration...'
  install -o root -g root -m 644 "$RELEASE_DIR/compose.yaml" \
    "$RELEASE_DIR/compose.production.yaml" "$APP_DIR/"
  install -o root -g root -m 644 "$RELEASE_DIR/deploy/nginx-trusted-proxy.conf" \
    "$RELEASE_DIR/deploy/nginx-forwarded-scheme.map" "$APP_DIR/deploy/"
  install -o root -g root -m 700 "$RELEASE_DIR/deploy/deploy.sh" "$APP_DIR/deploy/deploy.sh"
fi

# Preserve other settings/comments in the root .env and replace only IMAGE_TAG.
# A temporary file in the same directory allows an atomic replacement.
next_env=$(mktemp "$APP_DIR/.env.next.XXXXXX")
awk -v tag="$IMAGE_TAG" '
  /^[[:space:]]*(export[[:space:]]+)?IMAGE_TAG[[:space:]]*=/ {
    if (!written) print "IMAGE_TAG=" tag
    written=1
    next
  }
  { print }
  END { if (!written) print "IMAGE_TAG=" tag }
' .env > "$next_env"
cp -- .env .env.previous
chmod 600 .env.previous
mv -- "$next_env" .env
next_env=''

echo 'Applying release and waiting for healthy containers...'
if ! "${compose[@]}" up -d --no-build --pull never --wait --wait-timeout 300; then
  echo 'Container startup failed. Inspect Docker Compose status on the VM.' >&2
  echo 'The previous environment selection is saved in .env.previous; rollback is manual.' >&2
  exit 1
fi

echo 'Checking readiness through frontend Nginx...'
curl --fail --silent --show-error --connect-timeout 5 --max-time 10 \
  --retry 5 --retry-delay 2 --retry-all-errors \
  http://127.0.0.1:8080/api/ready \
  | jq -e '.status == "ready"' >/dev/null

echo "Release $IMAGE_TAG is healthy."
