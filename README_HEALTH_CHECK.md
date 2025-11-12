# Archon Health Check Guide

This guide explains how to verify your Archon development environment is properly configured before starting work.

## Quick Start

### Option 1: Comprehensive Health Check (Recommended)

Runs a detailed Python script that checks all services, environment variables, database connectivity, and more.

```bash
make health-check
```

**Checks:**
- ✓ Main API (port 8181)
- ✓ MCP Server (port 8051)
- ✓ Agent Work Orders (port 8053)
- ✓ Frontend Dev Server (port 3737)
- ✓ Environment variables
- ✓ Docker services status
- ✓ Database connectivity

### Option 2: Quick Test (Bash/Shell)

Runs a faster shell script with basic checks.

```bash
make quick-test
```

**Checks:**
- Docker installation and services
- Python environment (uv, virtualenv)
- Node.js environment (npm, node_modules)
- Environment variables
- Basic API endpoint availability

## Running Health Checks

### Before Starting a Claude Session

```bash
# Run comprehensive check
make health-check

# Or run quick test
make quick-test
```

### Manual Execution

**Python health check:**
```bash
cd python
uv run python ../scripts/health-check.py
```

**Shell quick test:**
```bash
bash scripts/quick-test.sh
```

## What Each Check Does

### Services Check
Verifies all Archon services are reachable:
- Main API server (FastAPI backend)
- MCP server (Model Context Protocol)
- Agent Work Orders service
- Frontend development server

### Environment Check
Ensures required environment variables are set:
- `SUPABASE_URL` - Required
- `SUPABASE_SERVICE_KEY` - Required
- `ENCRYPTION_KEY` - Optional
- `UPSTASH_REDIS_REST_URL` - Optional

### Docker Check
Validates Docker Compose services:
- Docker and Docker Compose installed
- Services defined in docker-compose.yml
- Running services count

### Database Check
Tests Supabase connectivity:
- Connection to Supabase REST API
- Valid credentials
- Network reachability

## Understanding Results

### Status Indicators

- ✓ (Green) - Healthy, working correctly
- ⚠ (Yellow) - Warning, may need attention
- ✗ (Red) - Error, requires fix

### Example Output

```
🔍 Archon Health Check

Checking services...
Checking environment...
Checking Docker...
Checking database...

╭──────────────────────────────────────────────────────────╮
│                   Health Check Results                   │
├─────────────────────────┬─────────┬─────────────────────┤
│ Component               │ Status  │ Message             │
├─────────────────────────┼─────────┼─────────────────────┤
│ Main API                │    ✓    │ Healthy             │
│ MCP Server              │    ✓    │ Healthy             │
│ Agent Work Orders       │    ⚠    │ Not running         │
│ Frontend Dev Server     │    ✓    │ Healthy             │
│ Environment Variables   │    ✓    │ All required vars   │
│ Docker Services         │    ✓    │ All 3 services      │
│ Database                │    ✓    │ Connected           │
╰─────────────────────────┴─────────┴─────────────────────╯

Summary:
  ✓ Healthy: 6/7
  ⚠ Warnings: 1
```

## Common Issues and Fixes

### Services Not Running

**Problem:** `✗ Not running` for services

**Fix:**
```bash
# Start all Docker services
docker compose up -d

# Or start specific profile
docker compose --profile backend up -d
```

### Missing Environment Variables

**Problem:** `✗ Missing: SUPABASE_URL, SUPABASE_SERVICE_KEY`

**Fix:**
```bash
# Copy example env file
cp python/.env.example python/.env

# Edit and add your credentials
nano python/.env
```

### Docker Not Available

**Problem:** `✗ Docker not installed` or `✗ Docker Compose not available`

**Fix:**
- Install Docker Desktop: https://www.docker.com/products/docker-desktop
- Ensure Docker is running

### Database Connection Failed

**Problem:** `✗ Connection timeout` or `✗ HTTP 500`

**Fix:**
1. Verify Supabase credentials in `.env`
2. Check Supabase project is active
3. Verify network connectivity

### Frontend Not Running

**Problem:** `✗ Frontend Dev Server - Not running`

**Fix:**
```bash
cd archon-ui-main
npm install
npm run dev
```

## Integration with Workflows

### In Makefile

```bash
# Check before starting development
make health-check && make dev
```

### In CI/CD

```bash
# As a pre-deployment check
make quick-test || exit 1
```

### In Git Hooks

Add to `.git/hooks/pre-commit`:
```bash
#!/bin/bash
make quick-test || {
    echo "Health check failed. Fix issues before committing."
    exit 1
}
```

## Advanced Usage

### Custom Port Checking

Edit `scripts/health-check.py` to add custom endpoints:

```python
SERVICES = {
    "Main API": "http://localhost:8181/health",
    "Custom Service": "http://localhost:9000/status",
}
```

### Continuous Monitoring

Run health check in watch mode:

```bash
watch -n 5 'make quick-test'
```

### Logging Results

Save health check output:

```bash
make health-check > health-report.txt 2>&1
```

## Dependencies

### Python Health Check
Requires:
- `httpx` - HTTP client
- `rich` - Terminal formatting

Install separately:
```bash
pip install -r scripts/requirements-health.txt
```

### Shell Quick Test
Requires:
- `bash` - Shell
- `curl` - HTTP testing
- `docker` - Container runtime

## Troubleshooting

### Script Not Executable

```bash
chmod +x scripts/quick-test.sh
```

### Python Module Not Found

```bash
cd python
uv sync --group all
uv run python ../scripts/health-check.py
```

### Windows Path Issues

Use Git Bash or WSL to run shell scripts:
```bash
# In Git Bash
bash scripts/quick-test.sh
```

## Best Practices

1. **Run health check at session start** - Catch issues early
2. **Check before committing** - Ensure environment is stable
3. **Monitor during development** - Watch for service failures
4. **Document custom checks** - Add project-specific validations
5. **Share with team** - Standardize environment verification

## Next Steps

After successful health check:

1. Review service logs: `docker compose logs -f`
2. Start development: `make dev`
3. Access services:
   - Frontend: http://localhost:3737
   - API: http://localhost:8181
   - MCP: http://localhost:8051

## Support

If health checks consistently fail:

1. Check Archon documentation: `README.md`, `CLAUDE.md`
2. Review Docker logs: `docker compose logs`
3. Verify system requirements
4. File an issue with health check output
