#!/bin/bash

################################################################################
# Vesla Server Installation Script
# Automates setup of a new Vesla deployment server
################################################################################

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Log file
LOG_FILE="/opt/vesla/install.log"
INSTALL_DIR="/opt/vesla"

# Configuration variables (set by user input, flags, or config file)
DOMAINS=""
DO_TOKEN=""
ACME_EMAIL=""
DASHBOARD_PASSWORD=""
INSTALL_TAILSCALE=false
INSTALL_PORTAINER=false
CONFIG_FILE=""
SKIP_PROMPTS=false

# Ripple progress indicator availability
HAS_RIPPLE=false

################################################################################
# Utility Functions
################################################################################

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log_section() {
    echo "" | tee -a "$LOG_FILE"
    echo "$(printf '%.0s=' {1..80})" | tee -a "$LOG_FILE"
    echo "$1" | tee -a "$LOG_FILE"
    echo "$(printf '%.0s=' {1..80})" | tee -a "$LOG_FILE"
}

log_step() {
    echo -e "${BLUE}→${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}✗${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${CYAN}ℹ${NC} $1" | tee -a "$LOG_FILE"
}

die() {
    log_error "$1"
    exit 1
}

show_usage() {
    cat << 'EOF'
Usage: sudo bash install-server.sh [OPTIONS]

Options:
  --config FILE              Load configuration from JSON or YAML file
  --domains DOMAINS          Comma-separated domain names
  --do-token TOKEN           DigitalOcean API token
  --email EMAIL              Email for Let's Encrypt notifications
  --password PASSWORD        Admin password for Traefik dashboard
  --tailscale                Install Tailscale VPN
  --portainer                Install Portainer Docker UI
  --help                     Show this help message

Example config file (JSON):
  {
    "domains": "example.com,www.example.com",
    "do_token": "dop_v1_...",
    "acme_email": "admin@example.com",
    "dashboard_password": "secure_password",
    "install_tailscale": false,
    "install_portainer": true
  }

Example config file (YAML):
  domains: "example.com,www.example.com"
  do_token: "dop_v1_..."
  acme_email: "admin@example.com"
  dashboard_password: "secure_password"
  install_tailscale: false
  install_portainer: true

Example usage:
  # Interactive prompts (default)
  sudo bash install-server.sh

  # Load from config file
  sudo bash install-server.sh --config /path/to/config.json

  # Command-line flags
  sudo bash install-server.sh --domains example.com --do-token dop_v1_... --email admin@example.com

EOF
}

load_config_file() {
    local config_file="$1"
    
    if [[ ! -f "$config_file" ]]; then
        die "Config file not found: $config_file"
    fi
    
    log_step "Loading configuration from $config_file"
    
    # Detect file format
    if [[ "$config_file" == *.json ]]; then
        # Simple JSON parsing (requires jq if more complex)
        if command -v jq &> /dev/null; then
            DOMAINS=$(jq -r '.domains // empty' "$config_file")
            DO_TOKEN=$(jq -r '.do_token // empty' "$config_file")
            ACME_EMAIL=$(jq -r '.acme_email // empty' "$config_file")
            DASHBOARD_PASSWORD=$(jq -r '.dashboard_password // empty' "$config_file")
            INSTALL_TAILSCALE=$(jq -r '.install_tailscale // false' "$config_file")
            INSTALL_PORTAINER=$(jq -r '.install_portainer // false' "$config_file")
        else
            # Fallback: basic grep-based parsing
            DOMAINS=$(grep -o '"domains"[[:space:]]*:[[:space:]]*"[^"]*"' "$config_file" | cut -d'"' -f4)
            DO_TOKEN=$(grep -o '"do_token"[[:space:]]*:[[:space:]]*"[^"]*"' "$config_file" | cut -d'"' -f4)
            ACME_EMAIL=$(grep -o '"acme_email"[[:space:]]*:[[:space:]]*"[^"]*"' "$config_file" | cut -d'"' -f4)
            DASHBOARD_PASSWORD=$(grep -o '"dashboard_password"[[:space:]]*:[[:space:]]*"[^"]*"' "$config_file" | cut -d'"' -f4)
        fi
    elif [[ "$config_file" == *.yaml || "$config_file" == *.yml ]]; then
        # Simple YAML parsing
        DOMAINS=$(grep "^domains:" "$config_file" | cut -d'"' -f2)
        DO_TOKEN=$(grep "^do_token:" "$config_file" | cut -d'"' -f2)
        ACME_EMAIL=$(grep "^acme_email:" "$config_file" | cut -d'"' -f2)
        DASHBOARD_PASSWORD=$(grep "^dashboard_password:" "$config_file" | cut -d'"' -f2)
        INSTALL_TAILSCALE=$(grep "^install_tailscale:" "$config_file" | awk '{print $2}')
        INSTALL_PORTAINER=$(grep "^install_portainer:" "$config_file" | awk '{print $2}')
    else
        die "Unsupported config file format. Use .json or .yaml"
    fi
    
    if [[ -n "$DOMAINS" ]]; then
        SKIP_PROMPTS=true
        log_success "Configuration loaded from file"
    fi
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help)
                show_usage
                exit 0
                ;;
            --config)
                CONFIG_FILE="$2"
                load_config_file "$CONFIG_FILE"
                shift 2
                ;;
            --domains)
                DOMAINS="$2"
                SKIP_PROMPTS=true
                shift 2
                ;;
            --do-token)
                DO_TOKEN="$2"
                shift 2
                ;;
            --email)
                ACME_EMAIL="$2"
                shift 2
                ;;
            --password)
                DASHBOARD_PASSWORD="$2"
                shift 2
                ;;
            --tailscale)
                INSTALL_TAILSCALE=true
                shift
                ;;
            --portainer)
                INSTALL_PORTAINER=true
                shift
                ;;
            *)
                echo "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

setup_ripple() {
    # Check if ripple is available
    if command -v ripple &> /dev/null; then
        HAS_RIPPLE=true
        return 0
    fi
    
    # Try to install ripple
    log_step "Installing ripple progress indicator"
    if curl -sL https://gist.githubusercontent.com/ttscoff/efe9c1284745c4df956457a5707e7450/raw/3f091ac9329a71ca19faa96372a894a6dc935928/ripple.rb -o /usr/local/bin/ripple 2>&1; then
        chmod +x /usr/local/bin/ripple
        if command -v ripple &> /dev/null; then
            HAS_RIPPLE=true
            log_success "Ripple installed"
            return 0
        fi
    fi
    
    log_warning "Ripple installation failed, proceeding without progress indicator"
    HAS_RIPPLE=false
}

# Run command with ripple if available, otherwise run normally
run_with_progress() {
    local message="$1"
    shift
    
    if [[ "$HAS_RIPPLE" == true ]]; then
        ripple "$message" -- "$@" 2>&1 | tee -a "$LOG_FILE" > /dev/null
        return ${PIPESTATUS[0]}
    else
        "$@" > /dev/null 2>&1
    fi
}

################################################################################
# Prerequisite Checks
################################################################################

check_prerequisites() {
    log_section "CHECKING PREREQUISITES"
    
    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        die "This script must be run as root (use sudo)"
    fi
    log_success "Running as root"
    
    # Check OS
    if [[ ! -f /etc/os-release ]]; then
        die "Cannot determine OS"
    fi
    
    . /etc/os-release
    if [[ "$ID" != "ubuntu" ]] || [[ ! "$VERSION_ID" =~ ^24\.04 ]]; then
        log_warning "This script is optimized for Ubuntu 24.04 LTS. You have $PRETTY_NAME"
        log_warning "Installation may fail or behave unexpectedly"
    else
        log_success "Ubuntu 24.04 LTS detected"
    fi
    
    # Check required commands
    local required_commands=("curl" "git" "grep" "sed")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            die "Required command not found: $cmd"
        fi
    done
    log_success "Required commands available"
    
    # Check disk space (10GB minimum)
    local available_space=$(df / | awk 'NR==2 {print $4}')
    if [[ $available_space -lt 10485760 ]]; then  # 10GB in KB
        die "Insufficient disk space. Minimum 10GB required, $(( available_space / 1048576 ))GB available"
    fi
    log_success "Sufficient disk space available ($(( available_space / 1048576 ))GB)"
    
    # Check internet connectivity
    if ! curl -s --connect-timeout 5 https://www.google.com > /dev/null 2>&1; then
        die "No internet connectivity detected"
    fi
    log_success "Internet connectivity confirmed"
    
    # Setup ripple for progress indication
    setup_ripple
}

################################################################################
# Interactive Configuration
################################################################################

prompt_configuration() {
    # Skip prompts if configuration was provided via flags or file
    if [[ "$SKIP_PROMPTS" == true ]]; then
        log_section "CONFIGURATION (from flags/file)"
        echo ""
        
        # Validate all required fields are present
        [[ -z "$DOMAINS" ]] && die "Domains not provided (use --domains or config file)"
        [[ -z "$DO_TOKEN" ]] && die "DigitalOcean token not provided (use --do-token or config file)"
        [[ -z "$ACME_EMAIL" ]] && die "ACME email not provided (use --email or config file)"
        [[ -z "$DASHBOARD_PASSWORD" ]] && die "Dashboard password not provided (use --password or config file)"
        
        log_info "Domains: $DOMAINS"
        log_info "Email: $ACME_EMAIL"
        log_info "Tailscale: $([ "$INSTALL_TAILSCALE" == true ] && echo 'Yes' || echo 'No')"
        log_info "Portainer: $([ "$INSTALL_PORTAINER" == true ] && echo 'Yes' || echo 'No')"
        echo ""
        return
    fi
    
    log_section "CONFIGURATION"
    echo ""
    
    # Domain names
    while [[ -z "$DOMAINS" ]]; do
        echo -e "${CYAN}Enter domain names${NC} (comma-separated)"
        echo "  Example: vesla-app.site,vesla-app.com"
        read -p "  Domains: " DOMAINS
        
        if [[ -z "$DOMAINS" ]]; then
            log_error "Domain names cannot be empty"
        fi
    done
    log_info "Domains configured: $DOMAINS"
    echo ""
    
    # DigitalOcean API token
    while [[ -z "$DO_TOKEN" ]]; do
        echo -e "${CYAN}Enter DigitalOcean API token${NC}"
        echo "  Get it from: https://cloud.digitalocean.com/account/api/tokens"
        read -sp "  Token: " DO_TOKEN
        echo ""
        
        if [[ -z "$DO_TOKEN" ]]; then
            log_error "API token cannot be empty"
        fi
    done
    log_info "DigitalOcean API token configured"
    echo ""
    
    # Email for Let's Encrypt
    while [[ -z "$ACME_EMAIL" ]]; do
        echo -e "${CYAN}Enter email for Let's Encrypt${NC}"
        echo "  Used for certificate renewal notifications"
        read -p "  Email: " ACME_EMAIL
        
        if [[ -z "$ACME_EMAIL" ]]; then
            log_error "Email cannot be empty"
        fi
    done
    log_info "Email configured: $ACME_EMAIL"
    echo ""
    
    # Dashboard password
    while [[ -z "$DASHBOARD_PASSWORD" ]]; do
        echo -e "${CYAN}Create admin password for Traefik dashboard${NC}"
        read -sp "  Password: " DASHBOARD_PASSWORD
        echo ""
        
        if [[ -z "$DASHBOARD_PASSWORD" ]]; then
            log_error "Password cannot be empty"
        fi
    done
    log_info "Dashboard password configured"
    echo ""
    
    # Optional: Tailscale
    echo -e "${CYAN}Install Tailscale?${NC} (secure VPN for remote access)"
    read -p "  (y/n): " -r TAILSCALE_CHOICE
    if [[ $TAILSCALE_CHOICE =~ ^[Yy]$ ]]; then
        INSTALL_TAILSCALE=true
        log_info "Tailscale installation enabled"
    fi
    echo ""
    
    # Optional: Portainer
    echo -e "${CYAN}Install Portainer?${NC} (web UI for Docker management)"
    read -p "  (y/n): " -r PORTAINER_CHOICE
    if [[ $PORTAINER_CHOICE =~ ^[Yy]$ ]]; then
        INSTALL_PORTAINER=true
        log_info "Portainer installation enabled"
    fi
    echo ""
}

################################################################################
# System Setup
################################################################################

setup_system() {
    log_section "SYSTEM SETUP"
    
    # Update package manager
    log_step "Updating package manager"
    apt-get update > /dev/null 2>&1 || die "Failed to update package manager"
    apt-get upgrade -y > /dev/null 2>&1 || die "Failed to upgrade packages"
    log_success "Package manager updated"
    
    # Install Ruby (required for ripple)
    log_step "Checking Ruby installation"
    if ! command -v ruby &> /dev/null; then
        log_step "Installing Ruby"
        apt-get install -y ruby-full > /dev/null 2>&1 || log_warning "Ruby installation failed"
        if command -v ruby &> /dev/null; then
            log_success "Ruby installed ($(ruby --version | cut -d' ' -f2))"
        else
            log_warning "Ruby installation failed, ripple will not be available"
        fi
    else
        log_success "Ruby already installed ($(ruby --version | cut -d' ' -f2))"
    fi
    
    # Install Docker
    log_step "Checking Docker installation"
    if ! command -v docker &> /dev/null; then
        log_step "Installing Docker"
        curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
        run_with_progress "Installing Docker Engine" bash /tmp/get-docker.sh || die "Docker installation failed"
        log_success "Docker installed"
    else
        log_success "Docker already installed ($(docker --version))"
    fi
    
    # Install Docker Compose
    log_step "Checking Docker Compose installation"
    if ! docker compose version &> /dev/null 2>&1; then
        log_step "Installing Docker Compose"
        run_with_progress "Downloading Docker Compose" curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        log_success "Docker Compose installed"
    else
        log_success "Docker Compose already installed"
    fi
    
    # Create vesla user
    log_step "Setting up vesla user"
    if ! id vesla &> /dev/null; then
        # Try to create with UID 1000, if taken, let system assign UID
        if useradd -m -s /bin/bash -u 1000 vesla 2>/dev/null; then
            log_success "Created vesla user (UID 1000)"
        elif useradd -m -s /bin/bash vesla 2>/dev/null; then
            local vesla_uid=$(id -u vesla)
            log_success "Created vesla user (UID $vesla_uid)"
            log_warning "UID 1000 was already taken, assigned UID $vesla_uid"
        else
            die "Failed to create vesla user"
        fi
    else
        log_success "Vesla user already exists"
    fi
    
    # Add vesla to docker group
    usermod -aG docker vesla || die "Failed to add vesla to docker group"
    log_success "Added vesla to docker group"
    
    # Create install directory
    log_step "Creating installation directory"
    mkdir -p "$INSTALL_DIR"
    chown vesla:vesla "$INSTALL_DIR"
    chmod 755 "$INSTALL_DIR"
    log_success "Installation directory ready: $INSTALL_DIR"
}

################################################################################
# Repository Setup
################################################################################

setup_repository() {
    log_section "REPOSITORY SETUP"
    
    log_step "Cloning Vesla repository"
    
    # Check if directory already exists
    if [[ -d "$INSTALL_DIR/.git" ]]; then
        log_info "Repository already exists, pulling latest changes"
        cd "$INSTALL_DIR"
        sudo -u vesla git pull origin main || log_warning "Failed to pull latest changes"
    else
        log_step "Downloading Vesla repository"
        cd /tmp
        sudo -u vesla git clone https://github.com/greyhoundforty/vesla-app.git vesla-app-tmp
        cp -r /tmp/vesla-app-tmp/* "$INSTALL_DIR/"
        cp -r /tmp/vesla-app-tmp/.git* "$INSTALL_DIR/"
        chown -R vesla:vesla "$INSTALL_DIR"
        rm -rf /tmp/vesla-app-tmp
        log_success "Repository downloaded"
    fi
    
    log_success "Repository ready at $INSTALL_DIR"
}

################################################################################
# Docker Network Setup
################################################################################

setup_docker_network() {
    log_section "DOCKER NETWORK"
    
    log_step "Creating vesla-network"
    
    if docker network inspect vesla-network &> /dev/null; then
        log_info "Network already exists"
    else
        docker network create \
            --driver bridge \
            --subnet=172.18.0.0/16 \
            vesla-network || die "Failed to create Docker network"
        log_success "Docker network created"
    fi
}

################################################################################
# Configuration Files
################################################################################

generate_traefik_config() {
    log_section "TRAEFIK CONFIGURATION"
    
    log_step "Generating Traefik configuration"
    
    # Convert comma-separated domains to YAML array
    local domains_array=()
    IFS=',' read -ra domains_array <<< "$DOMAINS"
    
    # Generate domain configuration
    local domains_config=""
    for domain in "${domains_array[@]}"; do
        domain=$(echo "$domain" | xargs)  # Trim whitespace
        domains_config+="          - main: \"$domain\"
            sans:
              - \"*.$domain\"
"
    done
    
    # Generate bcrypt hash for dashboard password
    log_step "Generating password hash"
    local password_hash=$(docker run --rm httpd:2.4-alpine htpasswd -nbB admin "$DASHBOARD_PASSWORD" | cut -d: -f2)
    
    # Create .env file
    cat > "$INSTALL_DIR/traefik/.env" << EOF
# Traefik Configuration
DO_AUTH_TOKEN=$DO_TOKEN
ACME_EMAIL=$ACME_EMAIL
TRAEFIK_DASHBOARD_PASSWORD_HASH=$password_hash
EOF
    
    chown vesla:vesla "$INSTALL_DIR/traefik/.env"
    chmod 600 "$INSTALL_DIR/traefik/.env"
    
    log_success "Traefik configuration generated"
}

generate_api_server_config() {
    log_section "API SERVER CONFIGURATION"
    
    log_step "Generating API server configuration"
    
    # Generate random API token
    local api_token=$(openssl rand -hex 32)
    
    # Create .env file
    cat > "$INSTALL_DIR/server/.env" << EOF
# Vesla Server Configuration
FLASK_ENV=production
API_TOKEN=$api_token
DO_AUTH_TOKEN=$DO_TOKEN
ACME_EMAIL=$ACME_EMAIL
EOF
    
    chown vesla:vesla "$INSTALL_DIR/server/.env"
    chmod 600 "$INSTALL_DIR/server/.env"
    
    log_success "API server configuration generated"
    log_info "API Token: $api_token (save this securely!)"
}

################################################################################
# Container Startup
################################################################################

start_containers() {
    log_section "STARTING CONTAINERS"
    
    # Start Traefik
    log_step "Starting Traefik"
    cd "$INSTALL_DIR/traefik"
    docker compose up -d > /dev/null 2>&1 || die "Failed to start Traefik"
    sleep 5
    log_success "Traefik started"
    
    # Start Vesla API Server
    log_step "Starting Vesla API server"
    cd "$INSTALL_DIR/server"
    docker compose up -d > /dev/null 2>&1 || die "Failed to start API server"
    sleep 5
    log_success "API server started"
    
    # Start Dashboard
    log_step "Starting Vesla dashboard"
    cd "$INSTALL_DIR/dashboard"
    docker compose up -d > /dev/null 2>&1 || die "Failed to start dashboard"
    sleep 3
    log_success "Dashboard started"
    
    # Optional: Start Portainer
    if [[ "$INSTALL_PORTAINER" == true ]]; then
        log_step "Starting Portainer"
        cd "$INSTALL_DIR/portainer"
        docker compose up -d > /dev/null 2>&1 || die "Failed to start Portainer"
        sleep 3
        log_success "Portainer started"
    fi
    
    # Optional: Setup Tailscale
    if [[ "$INSTALL_TAILSCALE" == true ]]; then
        setup_tailscale
    fi
}

setup_tailscale() {
    log_step "Installing Tailscale"
    
    if ! command -v tailscale &> /dev/null; then
        curl -fsSL https://tailscale.com/install.sh | sh > /dev/null 2>&1 || log_warning "Tailscale installation failed"
        systemctl enable tailscaled > /dev/null 2>&1
        systemctl start tailscaled > /dev/null 2>&1
    fi
    
    log_success "Tailscale installed (run 'tailscale up' to authenticate)"
}

################################################################################
# Verification
################################################################################

verify_installation() {
    log_section "VERIFICATION"
    
    # Check Traefik
    log_step "Checking Traefik"
    if docker ps | grep -q "traefik"; then
        log_success "Traefik is running"
    else
        log_error "Traefik is not running"
        return 1
    fi
    
    # Check API Server
    log_step "Checking API server"
    if docker ps | grep -q "vesla-api"; then
        log_success "API server is running"
    else
        log_error "API server is not running"
        return 1
    fi
    
    # Check health endpoint
    log_step "Testing API health endpoint"
    sleep 2
    if curl -s http://127.0.0.1:5001/health | grep -q "healthy"; then
        log_success "API health check passed"
    else
        log_warning "API health check failed (may not be ready yet)"
    fi
    
    # Check Docker network
    log_step "Verifying Docker network"
    if docker network inspect vesla-network &> /dev/null; then
        log_success "Docker network is configured"
    else
        log_error "Docker network verification failed"
        return 1
    fi
    
    log_success "Installation verification complete"
    return 0
}

################################################################################
# Success Report
################################################################################

print_success_report() {
    log_section "INSTALLATION COMPLETE"
    
    echo ""
    echo -e "${GREEN}Vesla server installation finished successfully!${NC}"
    echo ""
    
    # Get server IP
    local server_ip=$(hostname -I | awk '{print $1}')
    
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}IMPORTANT INFORMATION${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    echo "Installation Directory:"
    echo "  $INSTALL_DIR"
    echo ""
    
    echo "Configured Domains:"
    echo "  $DOMAINS"
    echo ""
    
    echo "API Endpoint:"
    echo "  https://api.$(echo $DOMAINS | cut -d',' -f1 | xargs)"
    echo ""
    
    echo "Dashboard:"
    echo "  http://127.0.0.1:8080 (local via SSH tunnel)"
    echo ""
    
    if [[ "$INSTALL_PORTAINER" == true ]]; then
        echo "Portainer:"
        echo "  http://127.0.0.1:9000 (local via SSH tunnel)"
        echo ""
    fi
    
    if [[ "$INSTALL_TAILSCALE" == true ]]; then
        echo "Tailscale Setup:"
        echo "  1. SSH into the server: ssh $(whoami)@$server_ip"
        echo "  2. Run: tailscale up"
        echo "  3. Follow the authentication link"
        echo ""
    fi
    
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo "NEXT STEPS:"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "1. Configure the Vesla CLI on your local machine:"
    echo "   vesla config set server_url https://api.$(echo $DOMAINS | cut -d',' -f1 | xargs)"
    echo "   vesla config set api_token (check the .env file)"
    echo ""
    echo "2. Deploy a test application:"
    echo "   cd example-apps/python"
    echo "   vesla push"
    echo ""
    echo "3. View logs:"
    echo "   Installation log: $LOG_FILE"
    echo "   Docker logs: docker compose logs -f"
    echo ""
    echo "4. Important:"
    echo "   - Back up your .env files (contain API tokens and passwords)"
    echo "   - Save the generated API token securely"
    echo "   - Configure DNS records pointing to: $server_ip"
    echo ""
}

################################################################################
# Cleanup on Error
################################################################################

cleanup_on_error() {
    log_error "Installation failed. Check $LOG_FILE for details."
    echo ""
    echo "To retry:"
    echo "  sudo bash $0"
    echo ""
    echo "To see what went wrong:"
    echo "  tail -50 $LOG_FILE"
}

trap cleanup_on_error EXIT

################################################################################
# Main Execution
################################################################################

main() {
    # Parse command-line arguments first
    parse_arguments "$@"
    
    # Initialize log file
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE"
    
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║     Vesla Server Installation Script                       ║"
    echo "║     Piku-inspired deployment platform                     ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
    
    log "Installation started"
    log "User: $(whoami), Host: $(hostname), OS: $(uname -a)"
    
    check_prerequisites
    prompt_configuration
    setup_system
    setup_repository
    setup_docker_network
    generate_traefik_config
    generate_api_server_config
    start_containers
    
    if verify_installation; then
        trap - EXIT
        print_success_report
        log "Installation completed successfully"
        exit 0
    else
        die "Installation verification failed"
    fi
}

# Run main function
main "$@"
