#!/bin/bash

# =============================================
# Oracle ARM Instance Setup Script
# YouTube Channel: Design AND Build System Design with AI
# Idempotent — safe to re-run, resumes from last failed step
# =============================================

set -e

echo "========================================"
echo "  Oracle ARM Instance Setup"
echo "========================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
info() { echo -e "${YELLOW}[→]${NC} $1"; }
warn() { echo -e "${RED}[!]${NC} $1"; }
skip() { echo -e "${BLUE}[~]${NC} $1 (already done, skipping)"; }

# -----------------------------------------------
# State tracking
# -----------------------------------------------
STATE_FILE="$HOME/.setup_state"

mark_done() {
  echo "$1" >> "$STATE_FILE"
}

is_done() {
  grep -qx "$1" "$STATE_FILE" 2>/dev/null
}

# Show progress on start
if [ -f "$STATE_FILE" ]; then
  echo ""
  echo "Resuming setup. Completed steps so far:"
  cat "$STATE_FILE" | sed 's/^/  ✓ /'
  echo ""
fi

# -----------------------------------------------
# Step 1: GitHub SSH Setup
# -----------------------------------------------
if is_done "github_ssh"; then
  skip "GitHub SSH setup"
else
  info "Setting up GitHub SSH connection..."

  if [ ! -f ~/.ssh/github_ed25519 ]; then
    ssh-keygen -t ed25519 -C "oracle-arm-instance" -f ~/.ssh/github_ed25519 -N ""
    log "SSH key generated"
  else
    log "SSH key already exists"
  fi

  ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null
  log "GitHub added to known hosts"

  if ! grep -q "Host github.com" ~/.ssh/config 2>/dev/null; then
    cat >> ~/.ssh/config <<EOF

Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/github_ed25519
EOF
    chmod 600 ~/.ssh/config
    log "SSH config updated"
  fi

  echo ""
  warn "Add this public key to GitHub before continuing:"
  warn "Go to: GitHub → Settings → SSH Keys → New SSH Key"
  echo ""
  echo "========================================"
  cat ~/.ssh/github_ed25519.pub
  echo "========================================"
  echo ""
  read -p "Press ENTER after you've added the key to GitHub..."

  info "Testing GitHub connection..."
  if ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
    log "GitHub connected successfully!"
    mark_done "github_ssh"
  else
    warn "GitHub connection test failed. Fix this and re-run the script."
    exit 1
  fi
fi

# -----------------------------------------------
# Step 2: Clone repo
# -----------------------------------------------
if is_done "repo_cloned"; then
  skip "Repo clone"
else
  info "Cloning setup repo from GitHub..."
  read -p "Enter your GitHub repo URL (e.g. git@github.com:username/repo.git): " REPO_URL

  if [ -n "$REPO_URL" ]; then
    if [ -d ~/repo ]; then
      warn "~/repo already exists, pulling latest instead..."
      git -C ~/repo pull
    else
      git clone "$REPO_URL" ~/repo
    fi
    log "Repo ready at ~/repo"
    mark_done "repo_cloned"
  else
    warn "No repo URL provided, skipping"
    mark_done "repo_cloned"
  fi
fi

# -----------------------------------------------
# Step 3: System update
# -----------------------------------------------
if is_done "system_updated"; then
  skip "System update"
else
  info "Updating system packages..."
  sudo apt update && sudo apt upgrade -y
  log "System updated"
  mark_done "system_updated"
fi

# -----------------------------------------------
# Step 4: Essential packages
# -----------------------------------------------
if is_done "essentials_installed"; then
  skip "Essential packages"
else
  info "Installing essential packages..."
  sudo apt install -y \
    curl git wget unzip net-tools \
    netfilter-persistent iptables-persistent
  log "Essentials installed"
  mark_done "essentials_installed"
fi

# -----------------------------------------------
# Step 5: Docker
# -----------------------------------------------
if is_done "docker_installed"; then
  skip "Docker"
else
  info "Installing Docker..."
  if command -v docker &>/dev/null; then
    log "Docker already installed: $(docker --version), skipping"
  else
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker ubuntu
    log "Docker installed"
  fi
  mark_done "docker_installed"
fi

# -----------------------------------------------
# Step 6: Docker Compose
# -----------------------------------------------
if is_done "docker_compose_installed"; then
  skip "Docker Compose"
else
  info "Installing Docker Compose..."
  sudo apt install -y docker-compose-plugin
  log "Docker Compose installed: $(docker compose version)"
  mark_done "docker_compose_installed"
fi

# -----------------------------------------------
# Step 7: Nginx
# -----------------------------------------------
if is_done "nginx_installed"; then
  skip "Nginx"
else
  info "Installing Nginx..."
  sudo apt install -y nginx
  sudo systemctl enable nginx
  sudo systemctl start nginx
  log "Nginx installed and started"
  mark_done "nginx_installed"
fi

# -----------------------------------------------
# Step 8: Certbot
# -----------------------------------------------
if is_done "certbot_installed"; then
  skip "Certbot"
else
  info "Installing Certbot..."
  sudo apt install -y certbot python3-certbot-nginx
  log "Certbot installed"
  mark_done "certbot_installed"
fi

# -----------------------------------------------
# Step 9: Node.js
# -----------------------------------------------
if is_done "nodejs_installed"; then
  skip "Node.js"
else
  info "Installing Node.js LTS..."
  curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
  sudo apt install -y nodejs
  log "Node.js installed: $(node --version)"
  mark_done "nodejs_installed"
fi

# -----------------------------------------------
# Step 10: Firewall
# -----------------------------------------------
if is_done "firewall_configured"; then
  skip "Firewall rules"
else
  info "Configuring firewall rules..."
  sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
  sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
  sudo iptables -I INPUT -p tcp --dport 22 -j ACCEPT
  sudo netfilter-persistent save
  log "Firewall rules saved"
  mark_done "firewall_configured"
fi

# -----------------------------------------------
# Step 11: Directory structure
# -----------------------------------------------
if is_done "directories_created"; then
  skip "Project directories"
else
  info "Creating project directories..."
  mkdir -p ~/apps/url-shortener
  mkdir -p ~/nginx/conf.d
  mkdir -p ~/scripts
  log "Directories created"
  mark_done "directories_created"
fi

# -----------------------------------------------
# Verification
# -----------------------------------------------
echo ""
echo "========================================"
echo "  Verification"
echo "========================================"
log "Docker:         $(docker --version)"
log "Docker Compose: $(docker compose version)"
log "Nginx:          $(nginx -v 2>&1)"
log "Node.js:        $(node --version)"
log "npm:            $(npm --version)"
log "Certbot:        $(certbot --version)"
log "Git:            $(git --version)"

echo ""
echo "========================================"
echo "  Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Run: newgrp docker"
echo "  2. Point your domain DNS to this server's IP in Cloudflare"
echo "  3. Run: sudo certbot --nginx -d yourdomain.com"
echo "  4. cd ~/apps/url-shortener && start building!"
echo ""
echo "To reset and start over: rm ~/.setup_state"
echo ""
