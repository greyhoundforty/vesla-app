# Vesla Project - Development Plan & Status

**Last Updated:** January 17, 2026  
**Project Phase:** Core infrastructure complete, entering configuration & extensibility phase

---

## Executive Summary

Vesla is a Piku-inspired deployment platform that enables developers to push code to a server where it's automatically built, containerized, and deployed with HTTPS via Let's Encrypt.

**Current Status:** Core deployment pipeline is fully functional and tested with Python, Node.js, and Go example applications across multiple domains.

---

## What Has Been Accomplished

### Phase 1: Core Infrastructure (COMPLETE)

#### CLI Tool (`cli/vesla`)
- Full deployment workflow: `vesla init`, `vesla push`, `vesla list`, `vesla status`, `vesla logs`, `vesla delete`
- Configuration management: `vesla config set/get`
- Improved error handling with `-v/--verbose` flag for diagnostics
- Network diagnostics: DNS resolution, TCP connectivity, TLS certificate inspection
- Features:
  - Creates tarballs with exclusion patterns (`.git`, `node_modules`, `.env`, etc.)
  - Bearer token authentication
  - 300-second deployment timeout (appropriate for Docker builds)
  - Tarball cleanup after deployment

#### Server API (`server/api.py`)
- Flask-based REST API listening on port 5001
- Endpoints:
  - `POST /api/deploy` - Accept code tarball + config, trigger build
  - `GET /api/apps` - List deployed apps
  - `GET /api/apps/<name>` - Get app status
  - `GET /api/apps/<name>/logs` - Stream app logs
  - `DELETE /api/apps/<name>` - Delete app
  - `GET /health` - Health check
- Docker integration for build and deployment
- Gunicorn production server

#### Build System (`server/builder.py`)
- Language detection from filesystem markers:
  - Python: `requirements.txt`, `pyproject.toml`
  - Node.js: `package.json`
  - Go: `go.mod`, `main.go`
  - Ruby, PHP, Java, Rust, .NET auto-detected
- Multi-stage builds for compiled languages (Go, Rust, Java, .NET)
- Non-root user (uid 1000) in all containers
- Layer caching optimization
- Supports custom Dockerfile override

#### Reverse Proxy & HTTPS (`traefik/`)
- Traefik 2.11 managing all routing and TLS
- Docker provider integration (auto-discovery)
- Multi-domain support with wildcard certificates
- File-based configuration for custom routes
- Dashboard accessible via Tailscale VPN

#### DNS Management (`server/dns_manager.py`)
- Digital Ocean API integration
- Automatic A record creation for deployed apps
- DNS-01 ACME challenge support for Let's Encrypt

#### Deployment Examples
Three complete, tested example applications:
1. **Python** (`example-apps/python/`) - Flask, port 5000
2. **Node.js** (`example-apps/node/`) - Express, port 3000
3. **Go** (`example-apps/go/`) - Standard library, port 8080

All verified working across multiple domains (`.site`, `.club`, `.com`, `.cloud`)

#### Documentation
- Main README with architecture diagram, quick start, CLI reference
- Example app READMEs with local testing instructions
- BUILDPACKS.md with language support details

---

## What Worked Well

1. **Docker networking approach** - Using container hostnames (`http://vesla-api:5001`) instead of hardcoded IPs resolved connectivity issues

2. **Multi-domain testing** - Verified deployments work across all configured domains, confirming Traefik wildcard routing is solid

3. **Health check endpoint** - Enabled CLI diagnostics with network-level testing (DNS, TCP, TLS)

4. **Language detection** - Automatic detection based on filesystem markers is reliable and extensible

5. **Docker isolation** - Container builds with proper non-root users and layer caching

---

## Known Issues & Limitations

### Issue 1: Traefik Dashboard Configuration
**Problem:** Dashboard configured with `Host(\`traefik.internal\`)` causes Let's Encrypt rejection (`.internal` not a valid TLD)

**Current Workaround:** Dashboard only accessible via Tailscale VPN, not HTTPS-enabled

**Impact:** Low (admin-only tool, secure via VPN)

**Future Fix:** Remove HTTPS requirement for internal services or use IP-based routing

### Issue 2: Let's Encrypt Provider Hard-Coded to DigitalOcean
**Problem:** DNS challenge provider is locked to DigitalOcean in Traefik config

**Impact:** Users with other DNS providers must manually modify Traefik configuration

**Scope:** This is one of the planned tasks (see Task 2 below)

### Issue 3: No Backup/Persistence Strategy
**Problem:** Deployed app tarballs and ACME certificates not backed up

**Impact:** Loss of data if server fails

**Scope:** This is one of the planned tasks (see Task 3 below)

---

## Pending Tasks (Next Phase)

### Task 1: Server Installation Script

**Objective:** Automate server setup for new Vesla deployments

**Specifications:**

Create `install-server.sh` that:

1. **Checks prerequisites:**
   - Ubuntu 24.04 LTS
   - curl, git available
   - At least 10GB free disk space
   - Internet connectivity to GitHub, Docker Hub, DigitalOcean, Let's Encrypt

2. **Interactive prompts for configuration:**
   ```
   Enter domain names (comma-separated, e.g., vesla-app.site,vesla-app.com): 
   Enter DigitalOcean API token: (hidden input)
   Enter admin email for Let's Encrypt: 
   Create admin password for Traefik dashboard: (hidden input)
   ```

3. **System setup:**
   - Install Docker & Docker Compose
   - Create vesla user (non-root)
   - Add vesla user to docker group
   - Create `/opt/vesla` directory structure
   - Configure SSH hardening (disable root login, key auth only)
   - Setup UFW firewall (allow 22, 80, 443)
   - Install Tailscale (optional)

4. **Application setup:**
   - Clone/download Vesla repository
   - Generate Traefik configuration with provided domains
   - Create `.env` files with provided tokens/passwords
   - Generate Let's Encrypt certificates (initial DNS challenge)
   - Start Docker containers in correct order:
     1. Create `vesla-network`
     2. Start Traefik
     3. Start Vesla API server
     4. Start Dashboard (optional)
     5. Start Portainer (optional)

5. **Verification:**
   - Test `/health` endpoint
   - Verify certificate generation
   - Create test DNS record
   - Output success report with:
     - API endpoint URL
     - Dashboard URL
     - Tailscale command for access
     - Next steps for deploying apps

**Implementation Notes:**
- Error handling with clear messages
- Idempotent where possible (can re-run safely)
- Logged output to `/opt/vesla/install.log`
- Rollback plan on critical failures

**Files to create:**
- `install-server.sh` (main installation script)
- `scripts/setup-traefik.sh` (Traefik-specific config generation)
- `scripts/setup-api-server.sh` (API server setup)
- `install-server-README.md` (detailed documentation)

---

### Task 2: Let's Encrypt Provider Extensibility

**Objective:** Support multiple DNS providers (not just DigitalOcean) for Traefik ACME challenges

**Current State:**
- Traefik config hardcoded with `digitalocean` provider
- DigitalOcean token in `.env` file
- `dns_manager.py` uses DigitalOcean API

**Required Changes:**

#### 2a. Traefik Configuration Template
**File:** `traefik/traefik.yml` (make it a template)

Currently:
```yaml
certificatesResolvers:
  digitalocean:
    acme:
      dnsChallenge:
        provider: digitalocean
```

Should become configurable via environment variables:
```yaml
certificatesResolvers:
  acme:  # Generic name instead of provider-specific
    acme:
      email: "${ACME_EMAIL}"
      storage: "/letsencrypt/acme.json"
      dnsChallenge:
        provider: "${DNS_PROVIDER}"  # cloudflare, route53, azure, etc.
        delayBeforeCheck: 0
      # Provider-specific auth tokens injected via environment
```

#### 2b. DNS Provider Abstraction Layer
**File:** `server/dns_providers.py` (new)

Create abstract base class:
```python
class DNSProvider(ABC):
    @abstractmethod
    def create_record(self, domain, subdomain, ip_address):
        pass
    
    @abstractmethod
    def delete_record(self, domain, subdomain):
        pass
    
    @abstractmethod
    def verify_api_token(self):
        pass

class DigitalOceanProvider(DNSProvider):
    # Current implementation moved here
    
class CloudflareProvider(DNSProvider):
    # New implementation
    
class Route53Provider(DNSProvider):
    # New implementation
    
class AzureProvider(DNSProvider):
    # New implementation
    
class GoogleCloudDNSProvider(DNSProvider):
    # New implementation

# Factory function
def get_dns_provider(provider_name):
    providers = {
        'digitalocean': DigitalOceanProvider,
        'cloudflare': CloudflareProvider,
        'route53': Route53Provider,
        'azure': AzureProvider,
        'google': GoogleCloudDNSProvider,
    }
    return providers[provider_name]()
```

#### 2c. Environment Variables
**File:** `.env` template

Support dynamic provider config:
```
DNS_PROVIDER=digitalocean  # or cloudflare, route53, azure, google

# DigitalOcean
DO_AUTH_TOKEN=xxx

# Cloudflare
CLOUDFLARE_API_TOKEN=xxx
CLOUDFLARE_ZONE_ID=xxx

# AWS Route53
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx

# Azure
AZURE_CLIENT_ID=xxx
AZURE_CLIENT_SECRET=xxx
AZURE_SUBSCRIPTION_ID=xxx

# Google Cloud DNS
GOOGLE_PROJECT_ID=xxx
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

#### 2d. API Server Updates
**File:** `server/api.py`

When deploying an app, use configurable provider:
```python
@app.route('/api/deploy', methods=['POST'])
def deploy():
    # ... existing code ...
    provider = get_dns_provider(os.getenv('DNS_PROVIDER'))
    provider.create_record(domain, app_name, server_ip)
```

#### 2e. Traefik Container Environment
**File:** `traefik/docker-compose.yml`

Pass provider-specific tokens to Traefik:
```yaml
services:
  traefik:
    environment:
      - DNS_PROVIDER=${DNS_PROVIDER}
      - DO_AUTH_TOKEN=${DO_AUTH_TOKEN}
      - CLOUDFLARE_API_TOKEN=${CLOUDFLARE_API_TOKEN}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      # ... etc
```

**Implementation Priority:**
1. DigitalOcean (already works - refactor into provider class)
2. Cloudflare (high demand)
3. Route53 (AWS ecosystem)
4. Azure (enterprise)
5. Google Cloud DNS (enterprise)

**Documentation:**
- `PROVIDERS.md` - Configuration guide for each provider
- Installation script updated to prompt for provider selection

---

### Task 3: Backup Mechanism (IBM Cloud Object Storage / S3)

**Objective:** Persist deployments and certificates to object storage for disaster recovery

**Scope:** Save deployment tarballs and Let's Encrypt certificates

**Components:**

#### 3a. Backup Scheduler (`server/backup.py` - new)
```python
class BackupManager:
    def __init__(self, provider_name, credentials):
        self.provider = get_backup_provider(provider_name)
        self.provider.authenticate(credentials)
    
    def backup_tarball(self, app_name, tarball_path):
        """Upload deployment tarball"""
        remote_path = f"deployments/{app_name}/{timestamp}.tar.gz"
        self.provider.upload(tarball_path, remote_path)
    
    def backup_certificates(self):
        """Backup Let's Encrypt certificates"""
        remote_path = f"certificates/{timestamp}/acme.json"
        self.provider.upload("/opt/vesla/traefik/letsencrypt/acme.json", remote_path)
    
    def restore_certificates(self, backup_date):
        """Restore certificates from backup"""
        self.provider.download(f"certificates/{backup_date}/acme.json", 
                               "/opt/vesla/traefik/letsencrypt/acme.json")
    
    def list_backups(self, app_name=None):
        """List available backups"""
        if app_name:
            return self.provider.list(f"deployments/{app_name}/")
        return self.provider.list("deployments/")

class S3BackupProvider:
    # Supports both AWS S3 and IBM Cloud Object Storage (S3-compatible)
    
class AzureBlobProvider:
    # Alternative: Azure Blob Storage
    
class GCSBackupProvider:
    # Alternative: Google Cloud Storage
```

#### 3b. Integration Points

**During deployment (in `server/api.py`):**
```python
@app.route('/api/deploy', methods=['POST'])
def deploy():
    # ... build and deploy container ...
    
    # After successful deployment
    backup_manager.backup_tarball(app_name, tarball_path)
    return success_response()
```

**Scheduled certificate backup (cron or APScheduler):**
```python
# In api.py initialization
scheduler = APScheduler()
scheduler.add_job(
    backup_manager.backup_certificates,
    'cron',
    hour=2,  # Daily at 2 AM UTC
    id='backup_certs'
)
scheduler.start()
```

#### 3c. IBM Cloud Object Storage Configuration

**Environment variables:**
```
BACKUP_PROVIDER=ibm_cloud_s3  # or aws_s3, azure_blob, google_cloud

# IBM Cloud Object Storage
IBM_COS_INSTANCE_CRN=crn:v1:...
IBM_COS_API_KEY=xxx
IBM_COS_ENDPOINT=https://s3.us-south.cloud-object-storage.appdomain.cloud
IBM_COS_BUCKET_NAME=vesla-backups

# Alternative: AWS S3
AWS_S3_BUCKET=vesla-backups
AWS_S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
```

**Bucket structure:**
```
vesla-backups/
├── deployments/
│   ├── myapp/
│   │   ├── 2026-01-17T10-30-00Z.tar.gz
│   │   └── 2026-01-16T15-45-00Z.tar.gz
│   └── otherapp/
│       └── 2026-01-17T08-00-00Z.tar.gz
├── certificates/
│   ├── 2026-01-17T10-30-00Z/acme.json
│   └── 2026-01-16T15-45-00Z/acme.json
└── system-backups/
    └── metadata.json
```

#### 3d. CLI Integration

Add backup commands:
```bash
vesla backup list                    # List all backups
vesla backup list myapp              # List backups for specific app
vesla backup restore myapp <date>    # Restore app tarball
vesla backup certificates list       # List certificate backups
vesla backup certificates restore <date>  # Restore certificate
```

#### 3e. API Endpoints

```
GET  /api/backups              # List backups
GET  /api/backups/<app>        # Backups for app
POST /api/backups/restore      # Restore from backup
GET  /api/backups/certificates # Certificate backups
POST /api/backups/certificates/restore # Restore certs
```

#### 3f. Configuration Files

**File:** `server/requirements.txt` (additions)
```
ibm-cos-sdk==2.13.5      # IBM Cloud Object Storage SDK
boto3==1.26.137          # AWS S3 SDK
azure-storage-blob==12.18.3  # Azure Blob Storage
google-cloud-storage==2.10.0  # Google Cloud Storage
apscheduler==3.10.4      # For scheduling backups
```

**File:** `BACKUP-SETUP.md` (new)
- IBM Cloud Object Storage setup instructions
- IAM role configuration
- Encryption and access control best practices
- Disaster recovery procedures

---

## Architecture Diagrams

### Current (Working) Flow
```
Developer → CLI
    ↓ (HTTPS, tarball)
Vesla API Server
    ├→ Builder (Docker)
    ├→ Traefik Registrar
    └→ DNS Manager (Digital Ocean)
         ↓ (A record)
    Domain DNS
    
    Result: Container running, HTTPS enabled
```

### With Backup System (Task 3)
```
Developer → CLI
    ↓ (HTTPS, tarball)
Vesla API Server
    ├→ Builder (Docker)
    ├→ Traefik Registrar
    ├→ DNS Manager
    └→ Backup Manager ←→ IBM Cloud Object Storage
         ↓ (tarball saved)
    
    Scheduled: Cert Backup ←→ IBM Cloud Object Storage
    
    Recovery Path: Object Storage → Restore API → Running
```

### With Provider Abstraction (Task 2)
```
Configuration (DNS_PROVIDER env var)
         ↓
Provider Factory
    ├→ DigitalOcean
    ├→ Cloudflare
    ├→ Route53
    ├→ Azure
    └→ Google Cloud
         ↓
Traefik receives provider credentials
         ↓
DNS Challenge (provider-specific)
         ↓
Let's Encrypt
         ↓
TLS Certificate
```

---

## Testing Checklist (for each task)

### Task 1: Server Install Script
- [ ] Fresh Ubuntu 24.04 VM
- [ ] Run script with different domain combinations
- [ ] Test with/without Tailscale
- [ ] Verify Docker containers start in correct order
- [ ] Confirm health check passes
- [ ] Deploy test app successfully
- [ ] Test on minimal system (2GB RAM, limited disk)
- [ ] Verify error handling and rollback

### Task 2: Provider Extensibility
- [ ] Refactor DigitalOcean to provider class
- [ ] Implement Cloudflare provider
- [ ] Test certificate generation with each provider
- [ ] Test DNS A record creation with each provider
- [ ] Test certificate renewal (wait 60+ days or mock)
- [ ] Switch providers mid-deployment
- [ ] Verify environment variables properly passed to Traefik

### Task 3: Backup Mechanism
- [ ] Upload deployment tarballs to IBM COS
- [ ] Schedule certificate backups
- [ ] Verify backup file structure
- [ ] Test restore of tarball → re-deploy app
- [ ] Test restore of certificates
- [ ] List and filter backups
- [ ] Test with AWS S3 (alternative provider)
- [ ] Encryption at rest verified
- [ ] Retention policy enforcement

---

## Recommended Implementation Order

1. **Task 1** (Server Install Script) - Foundation for others to test on
2. **Task 2** (Provider Extensibility) - Most requested feature
3. **Task 3** (Backup Mechanism) - Can be worked on independently

Each task can be developed in parallel once Task 1 is complete (provides test environments).

---

## Resources & References

### Traefik Multi-Provider Support
- Traefik Docs: https://doc.traefik.io/traefik/https/acme/
- Supported providers: https://doc.traefik.io/traefik/https/acme/#providers

### DNS Providers
- Cloudflare API: https://api.cloudflare.com/
- AWS Route53: https://docs.aws.amazon.com/route53/
- Azure DNS: https://learn.microsoft.com/en-us/azure/dns/
- Google Cloud DNS: https://cloud.google.com/dns/docs

### Object Storage SDKs
- IBM COS: https://github.com/IBM/ibm-cos-sdk-python
- AWS S3: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html
- Azure Blob: https://github.com/Azure/azure-sdk-for-python
- Google Cloud Storage: https://cloud.google.com/python/docs/reference/storage/latest

---

## Notes for Next Agent

1. **All prior work is functional and tested** - Don't rebuild, extend
2. **Example apps are verified working** - Use as deployment test cases
3. **CLI diagnostics work well** - Use `vesla push -v` for troubleshooting
4. **Docker networking uses hostnames** - Don't revert to IP addresses
5. **Traefik dashboard issue is known limitation** - Document but don't block progress
6. **Provider extensibility is higher priority than backup** - Reflects user requests
7. **Test each provider before merging** - Real DNS/ACME interactions required

---

**Next Session Trigger:** When ready to implement Task 1, load this document and begin with server install script requirements.
