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
	@command -v python3 >/dev/null 2>&1 || { \
		echo "  FAIL python3"; \
		echo "       Action: Install Python 3 (https://python.org/downloads/)"; \
		exit 1; \
	}
	@python3 scripts/api_service.py up

.PHONY: api-down
api-down: ## Stop the API service
	@command -v python3 >/dev/null 2>&1 || { \
		echo "  FAIL python3"; \
		echo "       Action: Install Python 3 (https://python.org/downloads/)"; \
		exit 1; \
	}
	@python3 scripts/api_service.py down

.PHONY: tiles-up
tiles-up: ## Start the tile server (port 8000)
	@command -v python3 >/dev/null 2>&1 || { \
		echo "  FAIL python3"; \
		echo "       Action: Install Python 3 (https://python.org/downloads/)"; \
		exit 1; \
	}
	@python3 scripts/tiles_service.py up

.PHONY: tiles-down
tiles-down: ## Stop the tile server
	@command -v python3 >/dev/null 2>&1 || { \
		echo "  FAIL python3"; \
		echo "       Action: Install Python 3 (https://python.org/downloads/)"; \
		exit 1; \
	}
	@python3 scripts/tiles_service.py down

.PHONY: up
up: ## Start all services (API + tile server)
	@set -e; \
	$(MAKE) api-up; \
	if ! $(MAKE) tiles-up; then \
		echo ""; \
		echo "  ✗ tiles-up failed; stopping API service..."; \
		$(MAKE) api-down >/dev/null 2>&1 || true; \
		exit 1; \
	fi
	@echo ""
	@echo "  ✓ All services started"
	@echo ""
	@echo "  Platform Connectivity Note:"
	@echo "  - iOS Simulator:      Use http://localhost:8080 and http://localhost:8000"
	@echo "  - Android Emulator:   Use http://10.0.2.2:8080 and http://10.0.2.2:8000"
	@echo ""

.PHONY: down
down: ## Stop all services
	@rc=0; \
	$(MAKE) api-down || rc=$$?; \
	$(MAKE) tiles-down || rc=$$?; \
	if [ $$rc -ne 0 ]; then exit $$rc; fi
	@echo ""
	@echo "  ✓ All services stopped"
	@echo ""

# ==============================================================================
# STATUS & LOGGING
# ==============================================================================

.PHONY: status
status: ## Show status of running services
	@command -v python3 >/dev/null 2>&1 || { \
		echo "  FAIL python3"; \
		echo "       Action: Install Python 3 (https://python.org/downloads/)"; \
		exit 1; \
	}
	@python3 scripts/status.py

.PHONY: logs
logs: ## View service logs
	@command -v python3 >/dev/null 2>&1 || { \
		echo "  FAIL python3"; \
		echo "       Action: Install Python 3 (https://python.org/downloads/)"; \
		exit 1; \
	}
	@python3 scripts/logs.py

# ==============================================================================
# PIPELINE
# ==============================================================================

.PHONY: pipeline
pipeline: ## Run all layer pipelines (PM2.5, precipitation, temperature, humidity, UV)
	@command -v python3 >/dev/null 2>&1 || { \
		echo "  FAIL python3"; \
		echo "       Action: Install Python 3 (https://python.org/downloads/)"; \
		exit 1; \
	}
	@python3 scripts/pipeline.py

.PHONY: pipeline-all
pipeline-all: pipeline ## Alias for 'pipeline' - run all layer pipelines

.PHONY: pipeline-download
pipeline-download: ## Run download stage for specific layer (requires LAYER=...)
	@command -v python3 >/dev/null 2>&1 || { \
		echo "  FAIL python3"; \
		echo "       Action: Install Python 3 (https://python.org/downloads/)"; \
		exit 1; \
	}
	@if [ -z "$(LAYER)" ]; then \
		echo "Error: LAYER parameter is required"; \
		echo "Usage: make pipeline-download LAYER=<layer>"; \
		echo "Supported layers: pm25, precipitation, uv, temperature, humidity"; \
		exit 1; \
	fi
	@python3 scripts/pipeline_stage.py download --layer $(LAYER)

.PHONY: pipeline-process
pipeline-process: ## Run process stage for specific layer (requires LAYER=...)
	@command -v python3 >/dev/null 2>&1 || { \
		echo "  FAIL python3"; \
		echo "       Action: Install Python 3 (https://python.org/downloads/)"; \
		exit 1; \
	}
	@if [ -z "$(LAYER)" ]; then \
		echo "Error: LAYER parameter is required"; \
		echo "Usage: make pipeline-process LAYER=<layer>"; \
		echo "Supported layers: pm25, precipitation, uv, temperature, humidity"; \
		exit 1; \
	fi
	@python3 scripts/pipeline_stage.py process --layer $(LAYER)

.PHONY: pipeline-tiles
pipeline-tiles: ## Run tiles generation stage for specific layer (requires LAYER=...)
	@command -v python3 >/dev/null 2>&1 || { \
		echo "  FAIL python3"; \
		echo "       Action: Install Python 3 (https://python.org/downloads/)"; \
		exit 1; \
	}
	@if [ -z "$(LAYER)" ]; then \
		echo "Error: LAYER parameter is required"; \
		echo "Usage: make pipeline-tiles LAYER=<layer>"; \
		echo "Supported layers: pm25, precipitation, uv, temperature, humidity"; \
		exit 1; \
	fi
	@python3 scripts/pipeline_stage.py tiles --layer $(LAYER)

.PHONY: pipeline-pm25
pipeline-pm25: ## Run PM2.5 layer pipeline
	@command -v python3 >/dev/null 2>&1 || { \
		echo "  FAIL python3"; \
		echo "       Action: Install Python 3 (https://python.org/downloads/)"; \
		exit 1; \
	}
	@python3 scripts/run_pipeline_layer.py pm25

.PHONY: pipeline-precip
pipeline-precip: ## Run precipitation layer pipeline
	@command -v python3 >/dev/null 2>&1 || { \
		echo "  FAIL python3"; \
		echo "       Action: Install Python 3 (https://python.org/downloads/)"; \
		exit 1; \
	}
	@python3 scripts/run_pipeline_layer.py precip

.PHONY: pipeline-temp
pipeline-temp: ## Run temperature layer pipeline
	@command -v python3 >/dev/null 2>&1 || { \
		echo "  FAIL python3"; \
		echo "       Action: Install Python 3 (https://python.org/downloads/)"; \
		exit 1; \
	}
	@python3 scripts/run_pipeline_layer.py temp

.PHONY: pipeline-humidity
pipeline-humidity: ## Run humidity layer pipeline
	@command -v python3 >/dev/null 2>&1 || { \
		echo "  FAIL python3"; \
		echo "       Action: Install Python 3 (https://python.org/downloads/)"; \
		exit 1; \
	}
	@python3 scripts/run_pipeline_layer.py humidity

.PHONY: pipeline-uv
pipeline-uv: ## Run UV layer pipeline
	@command -v python3 >/dev/null 2>&1 || { \
		echo "  FAIL python3"; \
		echo "       Action: Install Python 3 (https://python.org/downloads/)"; \
		exit 1; \
	}
	@python3 scripts/run_pipeline_layer.py uv

# ==============================================================================
# VERIFICATION
# ==============================================================================

.PHONY: verify
verify: ## Run aggregated verification (backend + pipeline + mobile instructions)
	@command -v python3 >/dev/null 2>&1 || { \
		echo "  FAIL python3"; \
		echo "       Action: Install Python 3 (https://python.org/downloads/)"; \
		exit 1; \
	}
	@python3 scripts/verify.py

.PHONY: verify-backend
verify-backend: ## Run backend verification (API + tile server health + sample tiles)
	@command -v python3 >/dev/null 2>&1 || { \
		echo "  FAIL python3"; \
		echo "       Action: Install Python 3 (https://python.org/downloads/)"; \
		exit 1; \
	}
	@python3 scripts/verify_backend.py

.PHONY: verify-pipeline
verify-pipeline: ## Run pipeline verification (end-to-end smoke test with fixtures)
	@command -v python3 >/dev/null 2>&1 || { \
		echo "  FAIL python3"; \
		echo "       Action: Install Python 3 (https://python.org/downloads/)"; \
		exit 1; \
	}
	@python3 scripts/verify_pipeline.py

.PHONY: verify-mobile
verify-mobile: ## Run mobile verification checklist (iOS/Android manual regression)
	@command -v python3 >/dev/null 2>&1 || { \
		echo "  FAIL python3"; \
		echo "       Action: Install Python 3 (https://python.org/downloads/)"; \
		exit 1; \
	}
	@python3 scripts/verify_mobile.py

.PHONY: check-boundaries
check-boundaries: ## Check architectural boundaries (app/ vs data_pipeline/ separation)
	@command -v python3 >/dev/null 2>&1 || { \
		echo "  FAIL python3"; \
		echo "       Action: Install Python 3 (https://python.org/downloads/)"; \
		exit 1; \
	}
	@python3 scripts/check_boundaries.py

# ==============================================================================
# ALIASES (for continuity with existing workflows)
# ==============================================================================

.PHONY: dev-up
dev-up: up ## Alias for 'up' - start all services

.PHONY: api
api: api-up ## Alias for 'api-up' - start API service

.PHONY: tiles
tiles: tiles-up ## Alias for 'tiles-up' - start tile server
