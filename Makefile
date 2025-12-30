# CLISAPP Root Makefile
# Unified entry surface for developer commands
#
# Usage: make <target>
# Run `make help` to see all available targets.

.DEFAULT_GOAL := help

# ==============================================================================
# HELP
# ==============================================================================

.PHONY: help
help: ## Show this help message
	@echo "CLISAPP - Available Commands"
	@echo "============================"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Core Targets:"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST) | grep -v "^  [a-z]*-"
	@echo ""
	@echo "Service Management:"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+-[a-zA-Z_-]+:.*##/ {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Aliases (for continuity):"
	@echo "  dev-up          -> up (start all services)"
	@echo "  api             -> api-up (start API service)"
	@echo "  tiles           -> tiles-up (start tile server)"
	@echo ""

# ==============================================================================
# PREFLIGHT & VALIDATION
# ==============================================================================

.PHONY: preflight
preflight: ## Validate configuration and dependencies before running services
	@command -v python3 >/dev/null 2>&1 || { \
		echo "  FAIL python3"; \
		echo "       Action: Install Python 3 (https://python.org/downloads/)"; \
		exit 1; \
	}
	@python3 scripts/preflight.py

# ==============================================================================
# SERVICE MANAGEMENT
# ==============================================================================

.PHONY: api-up
api-up: ## Start the API service (port 8080)
	@echo "[api-up] Not implemented yet - will start API on :8080"

.PHONY: api-down
api-down: ## Stop the API service
	@echo "[api-down] Not implemented yet - will stop API"

.PHONY: tiles-up
tiles-up: ## Start the tile server (port 8000)
	@echo "[tiles-up] Not implemented yet - will start tile server on :8000"

.PHONY: tiles-down
tiles-down: ## Stop the tile server
	@echo "[tiles-down] Not implemented yet - will stop tile server"

.PHONY: up
up: ## Start all services (API + tile server)
	@echo "[up] Not implemented yet - will start all services"

.PHONY: down
down: ## Stop all services
	@echo "[down] Not implemented yet - will stop all services"

# ==============================================================================
# STATUS & LOGGING
# ==============================================================================

.PHONY: status
status: ## Show status of running services
	@echo "[status] Not implemented yet - will show service health"

.PHONY: logs
logs: ## View service logs
	@echo "[logs] Not implemented yet - will show logs"

# ==============================================================================
# PIPELINE
# ==============================================================================

.PHONY: pipeline
pipeline: ## Run data pipeline
	@echo "[pipeline] Not implemented yet - will run data pipeline"

# ==============================================================================
# VERIFICATION
# ==============================================================================

.PHONY: verify
verify: ## Run verification/health checks
	@echo "[verify] Not implemented yet - will run health checks"

# ==============================================================================
# ALIASES (for continuity with existing workflows)
# ==============================================================================

.PHONY: dev-up
dev-up: up ## Alias for 'up' - start all services

.PHONY: api
api: api-up ## Alias for 'api-up' - start API service

.PHONY: tiles
tiles: tiles-up ## Alias for 'tiles-up' - start tile server
