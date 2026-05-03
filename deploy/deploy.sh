#!/bin/bash
set -euo pipefail

IMAGE="${DOCKERHUB_USERNAME}/datagrapho-fe:${IMAGE_TAG}"
CONTAINER_NAME="datagrapho-fe"
HOST_PORT="${HOST_PORT}"
CONTAINER_PORT="${CONTAINER_PORT}"
NETWORK="${NETWORK_NAME}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
die() { log "ERROR: $*" >&2; exit 1; }

[[ -z "${DOCKERHUB_USERNAME}" ]] && die "DOCKERHUB_USERNAME is not set"
[[ -z "${IMAGE_TAG}" ]]          && die "IMAGE_TAG is not set"
[[ -z "${HOST_PORT}" ]]          && die "HOST_PORT is not set"
[[ -z "${CONTAINER_PORT}" ]]     && die "CONTAINER_PORT is not set"
[[ -z "${NETWORK_NAME}" ]]       && die "NETWORK_NAME is not set"

log "Pulling image: $IMAGE"
docker pull "$IMAGE" || die "Failed to pull image"

if docker ps -q --filter "name=^${CONTAINER_NAME}$" | grep -q .; then
  log "Stopping existing container: $CONTAINER_NAME"
  docker stop --time 30 "$CONTAINER_NAME"
fi

if docker ps -aq --filter "name=^${CONTAINER_NAME}$" | grep -q .; then
  log "Removing existing container: $CONTAINER_NAME"
  docker rm "$CONTAINER_NAME"
fi

log "Starting new container from $IMAGE"
docker run -d \
  --name "$CONTAINER_NAME" \
  --network "$NETWORK" \
  --restart unless-stopped \
  -p "${HOST_PORT}:${CONTAINER_PORT}" \
  "$IMAGE" || die "Failed to start container"

log "Waiting for container to become healthy..."
RETRIES=10
DELAY=3
for i in $(seq 1 "$RETRIES"); do
  STATUS=$(docker inspect --format '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || true)
  if [[ "$STATUS" == "running" ]]; then
    log "Container is running (attempt $i/$RETRIES)"
    break
  fi
  if [[ "$i" -eq "$RETRIES" ]]; then
    docker logs "$CONTAINER_NAME" >&2
    die "Container did not reach running state after $((RETRIES * DELAY))s"
  fi
  log "Status: ${STATUS:-unknown} — retrying in ${DELAY}s..."
  sleep "$DELAY"
done

log "Pruning dangling images..."
docker image prune -f

log "Deploy complete. [Running: $IMAGE]"