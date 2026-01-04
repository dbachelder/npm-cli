# NPM CLI Tool Requirements & Context

## Overview

This document describes the operations, workflows, and technical details for managing Nginx Proxy Manager (NPM) in a Docker-based homelab environment. The goal is to provide comprehensive context for building a CLI tool that automates common NPM management tasks.

## Current Pain Points

### Manual Operations That Need Automation
1. **Database + File Synchronization**: NPM stores config in MySQL but generates nginx conf files. Changes must be made in both places for persistence.
2. **Complex SQL Queries**: Common operations require hand-crafting SQL with JSON fields, proper escaping, and multi-step workflows.
3. **Certificate Management**: SSL certificates involve certbot CLI, database entries, symlink creation, and nginx config updates.
4. **Config Validation**: No easy way to validate configs before applying (requires manual nginx reload and log checking).
5. **Bulk Operations**: No way to list/update multiple proxy hosts efficiently.
6. **Template Management**: Repetitive configs (like Authentik forward auth) require copy-paste from previous hosts.

### Current Workarounds
- Shell scripts with heredocs for SQL
- Manual tracking of proxy host IDs in CLAUDE.md
- Docker exec commands for nginx reload
- Manual file editing with sed/vi inside containers

## NPM Architecture

### Components
```
┌─────────────────────────────────────────────┐
│  NPM Web UI (Node.js)                       │
│  - Port 81 (admin interface)                │
│  - Manages database via ORM                 │
└─────────────────┬───────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────┐
│  MySQL Database (nginx DB)                  │
│  - Tables: proxy_host, certificate, etc.    │
│  - JSON fields for arrays (domain_names)    │
└─────────────────┬───────────────────────────┘
                  │
                  ↓ (on startup/UI change)
┌─────────────────────────────────────────────┐
│  Generated Nginx Configs                    │
│  - /data/nginx/proxy_host/*.conf            │
│  - Regenerated from DB on container restart │
└─────────────────┬───────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────┐
│  Nginx Process                              │
│  - Reloadable via: nginx -s reload          │
│  - Logs: /data/logs/proxy-host-*_*.log      │
└─────────────────────────────────────────────┘
```

### Key Insight: Dual Config Management
- **Immediate changes**: Edit `/data/nginx/proxy_host/*.conf` + `nginx -s reload`
  - Pros: Takes effect immediately
  - Cons: Lost on container restart or UI edit
- **Persistent changes**: Update database + edit conf file + reload
  - Pros: Survives restarts and UI edits
  - Cons: Requires SQL knowledge and multi-step process

## Database Schema

### Connection Details
- **Container**: `mysql` (Docker container name)
- **Database**: `nginx`
- **User**: `nginx`
- **Password**: `$NPM_DB_PASSWORD` (from .env)
- **Access**: `docker exec mysql mysql -u nginx -p"$NPM_DB_PASSWORD" nginx`

### proxy_host Table

**Key Columns:**
```sql
CREATE TABLE proxy_host (
    id INT PRIMARY KEY AUTO_INCREMENT,
    created_on DATETIME,
    modified_on DATETIME,
    owner_user_id INT DEFAULT 1,

    -- Domain configuration
    domain_names JSON,  -- e.g., '["example.com"]'
    forward_scheme VARCHAR(10),  -- 'http' or 'https'
    forward_host VARCHAR(255),  -- 'service-name' or IP
    forward_port INT,

    -- SSL configuration
    certificate_id INT,  -- FK to certificate table, NULL if no SSL
    ssl_forced TINYINT DEFAULT 0,  -- 1 = force HTTPS redirect
    http2_support TINYINT DEFAULT 1,
    hsts_enabled TINYINT DEFAULT 0,
    hsts_subdomains TINYINT DEFAULT 0,

    -- Advanced features
    allow_websocket_upgrade TINYINT DEFAULT 0,
    access_list_id INT DEFAULT 0,
    block_exploits TINYINT DEFAULT 1,
    caching_enabled TINYINT DEFAULT 0,

    -- Custom nginx config
    advanced_config TEXT,  -- Custom location blocks, headers, etc.

    -- Locations (for path-based routing)
    locations JSON,  -- Custom location blocks

    -- Status
    enabled TINYINT DEFAULT 1,

    -- Metadata
    meta JSON DEFAULT '{}'
);
```

**Common Queries:**
```sql
-- List all proxy hosts
SELECT id, domain_names, forward_host, forward_port FROM proxy_host;

-- Get specific host details
SELECT * FROM proxy_host WHERE id = 14;

-- Update advanced config
UPDATE proxy_host
SET advanced_config = '...', modified_on = NOW()
WHERE id = 14;

-- Find next available ID
SELECT MAX(id) + 1 FROM proxy_host;
```

### certificate Table

**Key Columns:**
```sql
CREATE TABLE certificate (
    id INT PRIMARY KEY AUTO_INCREMENT,
    created_on DATETIME,
    modified_on DATETIME,
    owner_user_id INT DEFAULT 1,

    -- Certificate details
    provider VARCHAR(50),  -- 'letsencrypt', 'other'
    nice_name VARCHAR(255),  -- Display name
    domain_names JSON,  -- e.g., '["example.com", "*.example.com"]'
    expires_on DATETIME,  -- 90 days from issue for Let's Encrypt

    -- Metadata
    meta JSON DEFAULT '{}'
);
```

**NPM Certificate File Convention:**
- Database entry with ID (e.g., 25)
- Certbot creates: `/etc/letsencrypt/live/example-com/`
- NPM expects: `/etc/letsencrypt/live/npm-25/`
- Solution: Symlink `example-com` → `npm-25`

## Common Workflows

### 1. Adding a New Proxy Host

**Current Manual Process:**
1. Get next proxy host ID: `SELECT MAX(id) FROM proxy_host;`
2. Create database entry with INSERT
3. Create nginx config file: `/data/nginx/proxy_host/{id}.conf`
4. Reload nginx: `docker exec nginx-proxy-manager nginx -s reload`

**What CLI Should Do:**
```bash
npm-cli proxy create \
  --domain example.codesushi.com \
  --forward-to http://service-name:8080 \
  --ssl-cert-id 16 \
  --force-ssl \
  --websockets \
  --template authentik-forward-auth
```

### 2. Updating Advanced Config (Persistent)

**Current Manual Process:**
```bash
# 1. Create SQL file with new config
cat > /tmp/update_npm.sql << 'EOF'
UPDATE proxy_host SET advanced_config = '
location / {
    # Custom config here
}', modified_on = NOW() WHERE id = 14;
EOF

# 2. Execute SQL
source .env && docker exec -i mysql mysql -u nginx -p"$NPM_DB_PASSWORD" nginx < /tmp/update_npm.sql

# 3. Update nginx config file
docker exec nginx-proxy-manager sed -i 's/OLD/NEW/' /data/nginx/proxy_host/14.conf

# 4. Reload nginx
docker exec nginx-proxy-manager nginx -s reload
```

**What CLI Should Do:**
```bash
# Edit advanced config in $EDITOR
npm-cli proxy edit-advanced 14

# Or apply from file
npm-cli proxy set-advanced 14 --from-file /path/to/config.nginx

# Or append snippet
npm-cli proxy add-location 14 /api --from-template api-bypass-auth
```

### 3. SSL Certificate Management (HTTP-01 Challenge)

**Current Manual Process:**
```bash
# 1. Request certificate via certbot
docker exec nginx-proxy-manager certbot certonly \
  --webroot \
  --webroot-path=/data/letsencrypt-acme-challenge \
  --email user@codesushi.com \
  --agree-tos \
  --no-eff-email \
  --cert-name example-codesushi-com \
  -d example.codesushi.com

# 2. Get next certificate ID
source .env && docker exec mysql mysql -u nginx -p"$NPM_DB_PASSWORD" nginx \
  -e "SELECT MAX(id) FROM certificate;"

# 3. Insert certificate metadata
cat > /tmp/npm_cert.sql << 'EOF'
INSERT INTO certificate (
    id, created_on, modified_on, owner_user_id,
    provider, nice_name, domain_names, expires_on, meta
) VALUES (
    26, NOW(), NOW(), 1,
    'letsencrypt', 'example.codesushi.com',
    '["example.codesushi.com"]',
    DATE_ADD(NOW(), INTERVAL 90 DAY), '{}'
);
EOF
source .env && docker exec -i mysql mysql -u nginx -p"$NPM_DB_PASSWORD" nginx < /tmp/npm_cert.sql

# 4. Create NPM naming convention symlink
docker exec nginx-proxy-manager ln -sf \
  /etc/letsencrypt/live/example-codesushi-com \
  /etc/letsencrypt/live/npm-26

# 5. Update proxy_host to use certificate
source .env && docker exec mysql mysql -u nginx -p"$NPM_DB_PASSWORD" nginx \
  -e "UPDATE proxy_host SET certificate_id = 26, ssl_forced = 1 WHERE id = 14;"

# 6. Update nginx config with SSL directives
# (manual editing required)

# 7. Reload nginx
docker exec nginx-proxy-manager nginx -s reload
```

**What CLI Should Do:**
```bash
npm-cli cert create \
  --domain example.codesushi.com \
  --method http-01 \
  --email user@codesushi.com

npm-cli proxy set-ssl 14 --cert-id 26 --force-https
```

### 4. SSL Certificate Management (DNS-01 Challenge)

**Current Manual Process:**
```bash
# 1. Run external certbot container with Route53 plugin
docker compose -f certbot-dns-route53.yml run --rm certbot certonly \
  --dns-route53 \
  --email user@codesushi.com \
  --agree-tos \
  --no-eff-email \
  --cert-name example-codesushi-com \
  -d example.codesushi.com

# 2-7. Same as HTTP-01 (database entry, symlink, etc.)
```

**What CLI Should Do:**
```bash
npm-cli cert create \
  --domain example.codesushi.com \
  --method dns-01 \
  --dns-provider route53 \
  --email user@codesushi.com
```

### 5. Listing and Querying

**Current Manual Process:**
```bash
# List all proxy hosts
source .env && docker exec mysql mysql -u nginx -p"$NPM_DB_PASSWORD" nginx \
  -e "SELECT id, domain_names FROM proxy_host;"

# Get details for specific host
source .env && docker exec mysql mysql -u nginx -p"$NPM_DB_PASSWORD" nginx \
  -e "SELECT * FROM proxy_host WHERE id = 14\G"
```

**What CLI Should Do:**
```bash
# List all proxy hosts
npm-cli proxy list

# Get details
npm-cli proxy get 14

# Filter by domain
npm-cli proxy list --domain "*.codesushi.com"

# Show SSL info
npm-cli cert list
npm-cli cert get 26
```

### 6. Config Validation and Testing

**Current Manual Process:**
```bash
# Test nginx config syntax
docker exec nginx-proxy-manager nginx -t

# View recent logs
docker logs nginx-proxy-manager --tail 50

# Check specific proxy host logs
docker exec nginx-proxy-manager tail -f /data/logs/proxy-host-14_access.log
```

**What CLI Should Do:**
```bash
# Validate before applying
npm-cli proxy validate 14

# Test config syntax
npm-cli test

# Watch logs
npm-cli logs 14 --follow
```

## Configuration Templates

### Common Patterns That Should Be Templatable

#### 1. Authentik Forward Auth (Full Protection)
```nginx
location /outpost.goauthentik.io {
    internal;
    proxy_pass http://authentik-server:9000/outpost.goauthentik.io;
    proxy_set_header Host $host;
    proxy_set_header X-Original-URL $scheme://$http_host$request_uri;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Content-Length "";
    proxy_pass_request_body off;
}

location / {
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Authentik forward auth
    auth_request /outpost.goauthentik.io/auth/nginx;
    error_page 401 = @goauthentik_proxy_signin;

    # Pass auth info to upstream
    auth_request_set $auth_cookie $upstream_http_set_cookie;
    add_header Set-Cookie $auth_cookie;

    auth_request_set $authentik_username $upstream_http_x_authentik_username;
    auth_request_set $authentik_groups $upstream_http_x_authentik_groups;
    auth_request_set $authentik_email $upstream_http_x_authentik_email;
    proxy_set_header X-authentik-username $authentik_username;
    proxy_set_header X-authentik-groups $authentik_groups;
    proxy_set_header X-authentik-email $authentik_email;

    proxy_pass $forward_scheme://$server:$port;
}

location @goauthentik_proxy_signin {
    internal;
    add_header Set-Cookie $auth_cookie;
    return 302 https://auth.codesushi.com/outpost.goauthentik.io/start?rd=$scheme://$http_host$request_uri;
}
```

#### 2. Authentik Forward Auth with API/Webhook Bypass
```nginx
# Same as above, but with additional location blocks:

location ~ ^/(api|webhook) {
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # No auth_request - bypass Authentik
    proxy_pass $forward_scheme://$server:$port;
}
```

#### 3. VPN/LAN-Only Access
```nginx
location / {
    allow 10.10.10.0/24;    # WireGuard VPN network
    allow 192.168.7.0/24;   # Local LAN
    allow 172.20.0.0/16;    # Docker network
    deny all;

    # ... rest of config
}
```

#### 4. WebSocket Support
```nginx
location / {
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";

    # ... rest of config
}
```

#### 5. SSL Configuration (Post-Certificate)
```nginx
listen 443 ssl;
http2 on;

# Let's Encrypt SSL
include conf.d/include/letsencrypt-acme-challenge.conf;
include conf.d/include/ssl-cache.conf;
include conf.d/include/ssl-ciphers.conf;
ssl_certificate /etc/letsencrypt/live/npm-{{CERT_ID}}/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/npm-{{CERT_ID}}/privkey.pem;

# HSTS
map $scheme $hsts_header {
    https   "max-age=63072000;includeSubDomains; preload";
}
add_header Strict-Transport-Security $hsts_header always;

# Force SSL
include conf.d/include/force-ssl.conf;
```

### Template Variables
CLI should support variable substitution:
- `{{DOMAIN}}` - The domain name
- `{{FORWARD_SCHEME}}` - http or https
- `{{FORWARD_HOST}}` - Backend service name/IP
- `{{FORWARD_PORT}}` - Backend port
- `{{CERT_ID}}` - Certificate ID
- `{{VPN_SUBNET}}` - VPN network CIDR
- `{{LAN_SUBNET}}` - LAN network CIDR
- `{{DOCKER_SUBNET}}` - Docker network CIDR

## CLI Tool Design Recommendations

### Architecture
```
┌─────────────────────────────────────────────┐
│  CLI Interface (Cobra/Click)                │
│  - Commands: proxy, cert, logs, test        │
└─────────────────┬───────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────┐
│  NPM Manager (Core Logic)                   │
│  - Database operations (SQLAlchemy/ORM)     │
│  - File operations (nginx config)           │
│  - Docker operations (exec, logs)           │
└─────────────────┬───────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────┐
│  Template Engine (Jinja2)                   │
│  - Load templates from ~/.npm-cli/templates │
│  - Variable substitution                    │
└─────────────────────────────────────────────┘
```

### Command Structure

```bash
# Proxy host management
npm-cli proxy list [--domain PATTERN] [--enabled-only]
npm-cli proxy get ID [--format json|yaml|table]
npm-cli proxy create --domain DOMAIN --forward-to URL [OPTIONS]
npm-cli proxy update ID [OPTIONS]
npm-cli proxy delete ID [--force]
npm-cli proxy enable ID
npm-cli proxy disable ID

# Advanced config
npm-cli proxy edit-advanced ID [--editor EDITOR]
npm-cli proxy set-advanced ID --from-file FILE
npm-cli proxy add-location ID PATH --template NAME [--vars KEY=VALUE]
npm-cli proxy show-config ID [--nginx|--database]

# Certificate management
npm-cli cert list [--expired] [--expiring-soon DAYS]
npm-cli cert get ID
npm-cli cert create --domain DOMAIN --method [http-01|dns-01] [OPTIONS]
npm-cli cert renew ID
npm-cli cert delete ID
npm-cli cert attach ID --to-proxy PROXY_ID [--force-https]

# Testing and validation
npm-cli test [--proxy-id ID]
npm-cli validate ID
npm-cli logs ID [--follow] [--tail N] [--access|--error]

# Templates
npm-cli template list
npm-cli template show NAME
npm-cli template create NAME --from-file FILE
npm-cli template delete NAME

# Utilities
npm-cli reload
npm-cli backup [--output FILE]
npm-cli restore --from FILE
npm-cli export ID --format [nginx|json]
npm-cli import --from FILE
```

### Configuration File

**~/.npm-cli/config.yaml**
```yaml
npm:
  docker:
    npm_container: nginx-proxy-manager
    mysql_container: mysql
    certbot_dns_container: certbot-dns-route53

  database:
    host: localhost  # Connect via docker exec
    database: nginx
    user: nginx
    password_env: NPM_DB_PASSWORD  # Read from environment

  paths:
    nginx_config: /data/nginx/proxy_host
    letsencrypt: /etc/letsencrypt/live
    logs: /data/logs

  defaults:
    auth:
      provider: authentik
      server: authentik-server:9000
      domain: auth.codesushi.com

    networks:
      vpn: 10.10.10.0/24
      lan: 192.168.7.0/24
      docker: 172.20.0.0/16

    ssl:
      email: user@codesushi.com
      force_https: true
      hsts: true

templates:
  directory: ~/.npm-cli/templates

logging:
  level: INFO
  file: ~/.npm-cli/npm-cli.log
```

### Key Features to Implement

#### 1. Database + File Sync
- Always keep database and nginx config files in sync
- Provide option for quick (non-persistent) vs persistent changes
- Warn when files don't match database

#### 2. Template System
- Ship with built-in templates for common patterns
- Allow user-defined templates
- Support variable substitution
- Validate templates before applying

#### 3. SSL Workflow Automation
- Single command to request cert + create DB entry + create symlink + attach to proxy
- Support both HTTP-01 and DNS-01 challenges
- Automatic renewal tracking (warn about expiring certs)

#### 4. Validation and Safety
- Validate nginx config syntax before applying
- Dry-run mode for all destructive operations
- Backup/restore functionality
- Rollback on failure

#### 5. Developer Experience
- Colorized output (rich/click)
- Progress bars for long operations
- Interactive mode for complex configs
- JSON/YAML output for scripting

#### 6. Integration with Existing Tools
- Read .env file for secrets
- Work with docker-compose environment
- Export configs for version control
- Import from existing NPM installations

## Environment and Context

### Docker Setup
- NPM container name: `nginx-proxy-manager`
- MySQL container name: `mysql`
- Network: `infra-net` (external Docker network)
- All services share this network

### Current Environment Variables
```bash
NPM_DB_PASSWORD  # MySQL password for nginx user
```

### File System Paths (Inside NPM Container)
```
/data/
├── nginx/
│   ├── proxy_host/
│   │   ├── 1.conf
│   │   ├── 2.conf
│   │   └── ...
│   └── custom/
│       ├── http.conf
│       └── server_proxy.conf
├── logs/
│   ├── proxy-host-1_access.log
│   ├── proxy-host-1_error.log
│   └── ...
└── letsencrypt-acme-challenge/
    └── ...

/etc/letsencrypt/
├── live/
│   ├── npm-16/  (symlink or actual)
│   ├── npm-25/  (symlink)
│   ├── n8n-codesushi-com/  (actual cert files)
│   └── ...
└── ...
```

### MySQL Access Pattern
```bash
# From host
source .env
docker exec mysql mysql -u nginx -p"$NPM_DB_PASSWORD" nginx -e "QUERY"

# From NPM container
mysql -h mysql -u nginx -p"$NPM_DB_PASSWORD" nginx -e "QUERY"
```

## Integration with Homelab Workflow

### Adding New Services (Current Process)
Reference: CLAUDE.md "Adding New Services"

1. **DNS Setup**: Add to `~/scripts/dyndns.sh` and run
2. **Docker Compose**: Create service compose file
3. **NPM Proxy**: Manual database + config creation (THIS IS THE PAIN POINT)
4. **Documentation**: Update CLAUDE.md tables
5. **Verification**: Test access and auth

**What CLI Could Streamline:**
```bash
# Single command to create proxy host with common settings
npm-cli proxy create-from-service \
  --domain newservice.codesushi.com \
  --docker-service newservice \
  --port 8080 \
  --template authentik-vpn-only \
  --add-to-homepage

# This would:
# 1. Create proxy host in database
# 2. Generate nginx config
# 3. Request SSL certificate (optional)
# 4. Add to homepage/config/services.yaml (optional)
# 5. Test and reload nginx
```

## Example Proxy Host Configurations

### Current Production Examples

#### Proxy Host ID 7: n8n.codesushi.com
- **Domain**: n8n.codesushi.com
- **Forward to**: http://n8n:5678
- **SSL**: Certificate ID 16
- **Features**:
  - Authentik forward auth on main paths
  - Bypass auth for `/webhook*` and `/api/*` paths
  - WebSocket support via custom headers

#### Proxy Host ID 13: ai.codesushi.com
- **Domain**: ai.codesushi.com
- **Forward to**: http://open-webui:8080
- **SSL**: Certificate ID (TBD from docs)
- **Features**:
  - Authentik forward auth on main paths
  - Bypass auth for `/api/*` paths (API key auth instead)

#### Proxy Host ID 14: vpn.codesushi.com
- **Domain**: vpn.codesushi.com
- **Forward to**: http://wg-easy:51821
- **SSL**: Certificate ID (TBD)
- **Features**:
  - Network ACL (VPN/LAN only)
  - Authentik forward auth
  - No public internet access

#### Proxy Host ID 15: hl.codesushi.com
- **Domain**: hl.codesushi.com
- **Forward to**: http://homepage:3000
- **SSL**: Certificate ID 25 (DNS-01 challenge)
- **Features**:
  - Network ACL (VPN/LAN only)
  - No Authentik (relies on network restriction)
  - DNS-01 cert (no public HTTP access)

#### Proxy Host ID 16: sludge.codesushi.com
- **Domain**: sludge.codesushi.com
- **Forward to**: http://192.168.7.200:8000 (host service, not Docker)
- **SSL**: Certificate ID 26 (HTTP-01 challenge via certbot CLI)
- **Features**:
  - Network ACL (VPN/LAN only)
  - Authentik forward auth
  - HTTP-01 cert with automated certbot workflow

### Important Note: Host Services vs Docker Services
When forwarding to a service running on the host (not in Docker):
- Use host IP: `192.168.7.200` (NOT `127.0.0.1` or `localhost`)
- Reason: `127.0.0.1` inside the NPM container refers to the container itself, not the host
- Example: sludge.codesushi.com → http://192.168.7.200:8000

## Testing and Validation

### What to Test After Changes
1. **Nginx syntax**: `nginx -t`
2. **HTTP access**: `curl -I http://domain.com`
3. **HTTPS access**: `curl -I https://domain.com`
4. **Auth redirect**: Should redirect to auth.codesushi.com
5. **Logs**: Check for errors in proxy-host-*_error.log

### CLI Should Support
```bash
# Run all tests
npm-cli test 14

# Would check:
# - Nginx config syntax
# - Database/file consistency
# - SSL certificate validity
# - HTTP/HTTPS response codes
# - Auth redirect behavior
# - Log for recent errors
```

## Future Enhancements

### Nice-to-Have Features
1. **Monitoring Integration**: Export metrics for Prometheus/Grafana
2. **Backup/Restore**: Full config backup and restore from CLI
3. **Diff Tool**: Compare database vs file configs
4. **Migration Tool**: Import from other reverse proxies (Traefik, Caddy)
5. **Health Checks**: Automated testing of all proxy hosts
6. **Certificate Renewal Automation**: Track expiry and auto-renew
7. **Config as Code**: Define entire NPM setup in YAML/JSON
8. **Ansible/Terraform Integration**: Export configs for IaC tools

### Infrastructure as Code Vision
```yaml
# npm-config.yaml
proxy_hosts:
  - domain: example.codesushi.com
    forward_to: http://service:8080
    ssl:
      method: http-01
      force_https: true
    auth:
      provider: authentik
      bypass_paths: ['/api/*', '/webhook*']
    network:
      allow: [vpn, lan, docker]
    websockets: true

# Apply with:
npm-cli apply -f npm-config.yaml
```

## Conclusion

This CLI tool should transform NPM management from:
- ❌ Manual SQL queries + file editing + docker exec commands
- ❌ Multi-step processes prone to human error
- ❌ Copy-paste config snippets
- ❌ Tribal knowledge in CLAUDE.md

To:
- ✅ Single-command operations
- ✅ Automated workflows with validation
- ✅ Reusable templates
- ✅ Version-controlled configuration

The tool should be designed for both:
1. **Interactive use**: Quick commands for ad-hoc changes
2. **Automation**: Scripting and IaC integration
