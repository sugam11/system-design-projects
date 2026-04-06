#!/bin/bash

# =============================================
# Oracle ARM Instance Setup Script
# YouTube Channel: Design AND Build System Design with AI
# =============================================

set -e  # Exit on any error

echo "========================================"
echo "  Oracle ARM Instance Setup"
echo "========================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
info() { echo -e "${YELLOW}[→]${NC} $1"; }
warn() { echo -e "${RED}[!]${NC} $1"; }

# -----------------------------------------------
# 1. GitHub SSH Setup
# -----------------------------------------------
info "Setting up GitHub SSH connection..."

# Generate SSH key if it doesn't exist
if [ ! -f ~/.ssh/github_ed25519 ]; then
  ssh-keygen -t ed25519 -C "oracle-arm-instance" -f ~/.ssh/github_ed25519 -N ""
  log "SSH key generated"
else
  log "SSH key already exists, skipping generation"
fi

# Add GitHub to known hosts
ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null
log "GitHub added to known hosts"

# Configure SSH to use this key for GitHub
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

# Print public key for user to add to GitHub
echo ""
warn "Add this public key to GitHub before continuing:"
warn "Go to: GitHub → Settings → SSH Keys → New SSH Key"
echo ""
echo "========================================"
cat ~/.ssh/github_ed25519.pub
echo "========================================"
echo ""
read -p "Press ENTER after you've added the key to GitHub..."

# Test GitHub connection
info "Testing GitHub connection..."
if ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
  log "GitHub connected successfully!"
else
  warn "GitHub connection test failed. Check that you added the key correctly."
  warn "You can test manually with: ssh -T git@github.com"
fi

# -----------------------------------------------
# 2. Clone your repo
# -----------------------------------------------
info "Cloning setup repo from GitHub..."
read -p "Enter your GitHub repo URL (e.g. git@github.com:username/repo.git): " REPO_URL

if [ -n "$REPO_URL" ]; then
  git clone "$REPO_URL" ~/repo
  log "Repo cloned to ~/repo"
else
  warn "No repo URL provided, skipping clone"
fi

# -----------------------------------------------
# 3. System Update
# -----------------------------------------------
info "Updating system packages..."
sudo apt update && sudo apt upgrade -y
log "System updated"

# -----------------------------------------------
# 4. Install essentials
# -----------------------------------------------
info "Installing essential packages..."
sudo apt install -y \
  curl \
  git \
  wget \
  unzip \
  net-tools \
  netfilter-persistent \
  iptables-persistent
log "Essentials installed"

# -----------------------------------------------
# 5. Install Docker
# -----------------------------------------------
info "Installing Docker..."
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu
log "Docker installed"

# -----------------------------------------------
# 6. Install Docker Compose Plugin
# -----------------------------------------------
info "Installing Docker Compose..."
sudo apt install -y docker-compose-plugin
log "Docker Compose installed: $(docker compose version)"

# -----------------------------------------------
# 7. Install Nginx
# -----------------------------------------------
info "Installing Nginx..."
sudo apt install -y nginx
sudo systemctl enable nginx
sudo systemctl start nginx
log "Nginx installed and started"

# -----------------------------------------------
# 8. Install Certbot (SSL)
# -----------------------------------------------
info "Installing Certbot..."
sudo apt install -y certbot python3-certbot-nginx
log "Certbot installed"

# -----------------------------------------------
# 9. Install Node.js LTS
# -----------------------------------------------
info "Installing Node.js LTS..."
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs
log "Node.js installed: $(node --version)"
log "npm installed: $(npm --version)"

# -----------------------------------------------
# 10. Open firewall ports (iptables)
# -----------------------------------------------
info "Configuring firewall rules..."
sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 22 -j ACCEPT
sudo netfilter-persistent save
log "Firewall rules saved"

# -----------------------------------------------
# 11. Create project directory structure
# -----------------------------------------------
info "Creating project directories..."
mkdir -p ~/apps/url-shortener
mkdir -p ~/nginx/conf.d
mkdir -p ~/scripts
log "Directories created"

# -----------------------------------------------
# 12. Verify everything
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
echo "  1. Run: newgrp docker  (for Docker permissions)"
echo "  2. Point your domain DNS to this server's IP in Cloudflare"
echo "  3. Run: sudo certbot --nginx -d yourdomain.com"
echo "  4. cd ~/apps/url-shortener && start building!"
echo ""
