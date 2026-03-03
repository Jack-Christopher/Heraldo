#!/bin/bash

###############################################################################
# Heraldo Production Deployment Script
#
# Automates deployment of Heraldo (PDF to Audiobook) in production.
# Handles: git pull, Docker rebuild, health checks, and rollback.
#
# Usage:
#   ./deploy.sh              # Normal deployment (exits if no changes)
#   ./deploy.sh --force      # Force deployment even if no changes detected
#   ./deploy.sh -f           # Short form of --force
#   ./deploy.sh --help       # Show help message
###############################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"
BACKUP_DIR="backups"
LOG_FILE="deploy.log"
MAX_WAIT_HEALTH=90
API_CONTAINER="heraldo-api"
FRONTEND_CONTAINER="heraldo-frontend"
DB_CONTAINER="heraldo-mongodb"
API_PORT="${API_PORT:-5001}"
FRONTEND_PORT="${FRONTEND_PORT:-3001}"

FORCE_DEPLOY=false

# Functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}✓${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}✗${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}ℹ${NC} $1" | tee -a "$LOG_FILE"
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

check_prerequisites() {
    log "Checking prerequisites..."

    if ! command_exists docker; then
        error "Docker is not installed"
        exit 1
    fi

    if ! docker compose version >/dev/null 2>&1; then
        error "Docker Compose plugin is not available. Install Docker Compose V2."
        exit 1
    fi

    if ! command_exists git; then
        error "Git is not installed"
        exit 1
    fi

    if [ ! -f "$COMPOSE_FILE" ]; then
        error "Docker Compose file not found: $COMPOSE_FILE"
        exit 1
    fi

    if [ ! -f "$ENV_FILE" ]; then
        warning ".env not found. Copy .env.example and configure."
    fi

    success "All prerequisites met"
}

check_env_vars() {
    log "Checking environment variables..."

    if [ -f "$ENV_FILE" ]; then
        set -a
        source "$ENV_FILE" 2>/dev/null || true
        set +a
    fi

    if [ -z "${JWT_SECRET:-}" ] || [ "$JWT_SECRET" = "change-me-in-production" ]; then
        error "JWT_SECRET must be set and different from default"
        exit 1
    fi

    success "Environment variables validated"
}

save_current_version() {
    log "Saving current version for rollback..."
    local current_commit
    current_commit=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    echo "$current_commit" > .last_deployed_commit
    success "Saved: $current_commit"
}

pull_latest_code() {
    log "Pulling latest code..."

    if ! git fetch origin 2>/dev/null; then
        warning "Could not fetch. Ensure remote is configured."
    fi

    local current_branch
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    local remote_commit local_commit
    remote_commit=$(git rev-parse "origin/$current_branch" 2>/dev/null || echo "")
    local_commit=$(git rev-parse HEAD)

    if [ -n "$remote_commit" ] && [ "$remote_commit" = "$local_commit" ]; then
        if [ "$FORCE_DEPLOY" = true ]; then
            warning "No new changes, but --force set. Continuing..."
            git pull origin "$current_branch" 2>/dev/null || true
            return 0
        else
            warning "No new changes. Use --force to deploy anyway."
            return 1
        fi
    fi

    if ! git pull origin "$current_branch" 2>/dev/null; then
        warning "Could not pull. Proceeding with current code."
    fi

    success "Code updated"
    return 0
}

backup_current_images() {
    log "Backing up current images..."
    mkdir -p "$BACKUP_DIR"
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    docker images --format "{{.Repository}}:{{.Tag}} {{.ID}}" | grep -E "heraldo" > "$BACKUP_DIR/images_${timestamp}.txt" 2>/dev/null || true
    success "Backup saved"
}

stop_containers() {
    log "Stopping containers..."
    if docker compose -f "$COMPOSE_FILE" ps -q 2>/dev/null | grep -q .; then
        docker compose -f "$COMPOSE_FILE" stop
        success "Containers stopped"
    else
        info "No running containers"
    fi
}

rebuild_containers() {
    log "Rebuilding and starting containers..."

    if ! docker compose -f "$COMPOSE_FILE" build --no-cache; then
        error "Build failed"
        exit 1
    fi

    if ! docker compose -f "$COMPOSE_FILE" up -d; then
        error "Failed to start containers"
        exit 1
    fi

    success "Containers started"
}

check_container_running() {
    docker ps --format '{{.Names}}' | grep -q "^${1}$"
}

wait_for_health() {
    local container_name=$1
    local max_wait=${2:-$MAX_WAIT_HEALTH}
    local elapsed=0

    log "Waiting for $container_name (max ${max_wait}s)..."

    while [ $elapsed -lt $max_wait ]; do
        local health
        health=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "none")
        if [ "$health" = "healthy" ]; then
            success "$container_name is healthy"
            return 0
        fi
        sleep 5
        elapsed=$((elapsed + 5))
        echo -n "."
    done
    echo ""
    warning "$container_name health check timeout"
    return 1
}

check_api_health() {
    log "Checking API..."
    local max_attempts=18
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -sf "http://localhost:${API_PORT}/api/limits" > /dev/null 2>&1; then
            success "API is responding"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 5
        echo -n "."
    done
    echo ""
    error "API did not respond"
    return 1
}

check_frontend() {
    log "Checking frontend..."
    local max_attempts=12
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -sf "http://localhost:${FRONTEND_PORT}/" > /dev/null 2>&1; then
            success "Frontend is accessible"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 5
        echo -n "."
    done
    echo ""
    error "Frontend not accessible"
    return 1
}

show_status() {
    log "Container status:"
    docker compose -f "$COMPOSE_FILE" ps
    echo ""
    log "Recent logs:"
    echo "--- API ---"
    docker logs --tail 15 "$API_CONTAINER" 2>&1 || true
    echo ""
    echo "--- Frontend ---"
    docker logs --tail 10 "$FRONTEND_CONTAINER" 2>&1 || true
}

cleanup_old_images() {
    log "Cleaning up unused images..."
    docker image prune -f > /dev/null 2>&1 || true
    info "Cleanup done"
}

rollback() {
    error "Deployment failed. Attempting rollback..."
    if [ -f .last_deployed_commit ]; then
        local last_commit
        last_commit=$(cat .last_deployed_commit)
        warning "Rolling back to: $last_commit"
        if git checkout "$last_commit" 2>/dev/null; then
            rebuild_containers
            success "Rollback completed"
        else
            error "Rollback failed. Manual intervention needed."
            exit 1
        fi
    else
        error "No previous version for rollback."
        exit 1
    fi
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--force)
                FORCE_DEPLOY=true
                shift
                ;;
            -h|--help)
                echo "Heraldo Deployment"
                echo ""
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  -f, --force    Force deploy even if no changes"
                echo "  -h, --help     Show help"
                echo ""
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
}

main() {
    parse_arguments "$@"

    echo "=========================================="
    echo "  Heraldo Deployment"
    [ "$FORCE_DEPLOY" = true ] && echo "  [FORCE MODE]"
    echo "=========================================="
    echo ""

    trap rollback ERR

    check_prerequisites
    check_env_vars
    save_current_version

    if ! pull_latest_code; then
        if [ "$FORCE_DEPLOY" = false ]; then
            info "Exiting. Use --force to deploy anyway."
            trap - ERR
            exit 0
        fi
    fi

    backup_current_images
    stop_containers
    rebuild_containers

    log "Waiting for containers..."
    sleep 20

    if ! check_container_running "$API_CONTAINER"; then
        error "API container not running"
        exit 1
    fi
    if ! check_container_running "$FRONTEND_CONTAINER"; then
        error "Frontend container not running"
        exit 1
    fi
    if ! check_container_running "$DB_CONTAINER"; then
        error "MongoDB container not running"
        exit 1
    fi
    success "All containers running"

    if ! wait_for_health "$DB_CONTAINER" 45; then
        warning "MongoDB health timeout (may still be starting)"
    fi

    log "Running MongoDB migrations..."
    if docker compose -f "$COMPOSE_FILE" exec -T "$API_CONTAINER" python migrate.py 2>/dev/null; then
        success "Migrations complete"
    else
        warning "Migrations failed or skipped (API may run them at startup)"
    fi

    if ! check_api_health; then
        error "API health check failed"
        exit 1
    fi

    if ! check_frontend; then
        error "Frontend check failed"
        exit 1
    fi

    cleanup_old_images
    show_status

    trap - ERR

    echo ""
    echo "=========================================="
    success "Deployment completed!"
    echo "=========================================="
    echo ""
    info "API:      http://localhost:${API_PORT}"
    info "Frontend: http://localhost:${FRONTEND_PORT}"
    info "Logs:     $LOG_FILE"
    echo ""
}

main "$@"
