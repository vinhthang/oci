#!/bin/bash
set -e

echo "=== 1. Reclaiming Physical RAM by Disabling crashkernel ==="
grubby --update-kernel=ALL --remove-args="crashkernel" --args="crashkernel=no" || true
systemctl disable --now kdump.service 2>/dev/null || true

echo "=== 2. Creating 2.5 GB Swap File ==="
if [ ! -f /swapfile ]; then
    fallocate -l 2560M /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2560
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "=== 3. Installing Packages ==="
dnf install -y podman zsh bind-utils tar gzip
chsh -s /bin/zsh opc || true

echo "=== 4. Installing Caddy Web Server ==="
if [ ! -f /usr/local/bin/caddy ]; then
    curl -sL https://github.com/caddyserver/caddy/releases/download/v2.9.1/caddy_2.9.1_linux_amd64.tar.gz | tar -xz -C /usr/local/bin caddy
    chmod +x /usr/local/bin/caddy
fi

echo "=== 5. Configuring Host Firewall ==="
systemctl start firewalld || true
systemctl enable firewalld || true
firewall-cmd --permanent --add-port=80/tcp || true
firewall-cmd --permanent --add-port=443/tcp || true
firewall-cmd --permanent --add-port=8080/tcp || true
firewall-cmd --permanent --add-port=53/tcp || true
firewall-cmd --permanent --add-port=53/udp || true
firewall-cmd --permanent --add-port=853/tcp || true
firewall-cmd --permanent --add-port=3000/tcp || true
firewall-cmd --permanent --add-port=8443/tcp || true
firewall-cmd --reload || true

echo "=== 6. Deploying VietCalendar Service ==="
tee /etc/systemd/system/vietcalendar.service <<'SERVICE_EOF'
[Unit]
Description=VietCalendar Rust REST Service & MCP Server
After=network-online.target
Wants=network-online.target

[Service]
Type=exec
Restart=always
RestartSec=5s
ExecStartPre=-/usr/bin/podman stop -t 10 vietcalendar
ExecStartPre=-/usr/bin/podman rm -f vietcalendar
ExecStart=/usr/bin/podman run --name vietcalendar -p 8080:8080 -e PORT=8080 ghcr.io/vinhthang/vietcalendar:latest
ExecStop=/usr/bin/podman stop -t 10 vietcalendar

[Install]
WantedBy=multi-user.target
SERVICE_EOF

echo "=== 7. Deploying AdGuard Home Service ==="
mkdir -p /opt/adguardhome/work /opt/adguardhome/conf /caddy/certificates
tee /etc/systemd/system/adguardhome.service <<'SERVICE_EOF'
[Unit]
Description=AdGuard Home DNS Server & Ad Blocker
After=network-online.target
Wants=network-online.target

[Service]
Type=exec
Restart=always
RestartSec=5s
ExecStartPre=-/usr/bin/podman stop -t 10 adguardhome
ExecStartPre=-/usr/bin/podman rm -f adguardhome
ExecStart=/usr/bin/podman run --name adguardhome \
  -v /opt/adguardhome/work:/opt/adguardhome/work:Z \
  -v /opt/adguardhome/conf:/opt/adguardhome/conf:Z \
  -v /caddy/certificates:/opt/adguardhome/certs:ro,Z \
  -p 53:53/tcp -p 53:53/udp \
  -p 127.0.0.1:3000:80/tcp \
  -p 853:853/tcp \
  docker.io/adguard/adguardhome:latest
ExecStop=/usr/bin/podman stop -t 10 adguardhome

[Install]
WantedBy=multi-user.target
SERVICE_EOF

echo "=== 8. Deploying Navidrome Lossless Music Server ==="
mkdir -p /opt/navidrome/data /opt/navidrome/music
tee /etc/systemd/system/navidrome.service <<'SERVICE_EOF'
[Unit]
Description=Navidrome Lossless Music Server
After=network-online.target
Wants=network-online.target

[Service]
Type=exec
Restart=always
RestartSec=5s
ExecStartPre=-/usr/bin/podman stop -t 10 navidrome
ExecStartPre=-/usr/bin/podman rm -f navidrome
ExecStart=/usr/bin/podman run --name navidrome \
  -v /opt/navidrome/data:/data:Z \
  -v /opt/navidrome/music:/music:ro,Z \
  -e ND_SCANSCHEDULE=1h \
  -e ND_LOGLEVEL=info \
  -e ND_BASEURL=https://music.${duckdns_domain} \
  -p 127.0.0.1:4533:4533/tcp \
  docker.io/deluan/navidrome:latest
ExecStop=/usr/bin/podman stop -t 10 navidrome

[Install]
WantedBy=multi-user.target
SERVICE_EOF

echo "=== 9. Deploying FileBrowser Personal Cloud File Manager ==="
mkdir -p /opt/filebrowser/config /opt/filebrowser/srv/Storage /opt/filebrowser/srv/Music
touch /opt/filebrowser/config/filebrowser.db
tee /etc/systemd/system/filebrowser.service <<'SERVICE_EOF'
[Unit]
Description=FileBrowser Personal Cloud File Manager
After=network-online.target
Wants=network-online.target

[Service]
Type=exec
Restart=always
RestartSec=5s
ExecStartPre=-/usr/bin/podman stop -t 10 filebrowser
ExecStartPre=-/usr/bin/podman rm -f filebrowser
ExecStart=/usr/bin/podman run --name filebrowser \
  -v /opt/filebrowser/srv:/srv:Z \
  -v /opt/navidrome/music:/srv/Music:Z \
  -v /opt/filebrowser/config/filebrowser.db:/database/filebrowser.db:Z \
  -p 127.0.0.1:8082:8080/tcp \
  docker.io/filebrowser/filebrowser:latest \
  --address 0.0.0.0 --port 8080
ExecStop=/usr/bin/podman stop -t 10 filebrowser

[Install]
WantedBy=multi-user.target
SERVICE_EOF

echo "=== 10. Deploying Hugo Blog with PaperMod Theme ==="
dnf install -y git
HUGO_VER=$(curl -s https://api.github.com/repos/gohugoio/hugo/releases/latest | grep 'tag_name' | cut -d '"' -f 4 | tr -d 'v')
[ -z "$HUGO_VER" ] && HUGO_VER="0.144.2"
curl -sL "https://github.com/gohugoio/hugo/releases/download/v${HUGO_VER}/hugo_extended_${HUGO_VER}_linux-amd64.tar.gz" -o /tmp/hugo.tar.gz
tar -xzf /tmp/hugo.tar.gz -C /usr/local/bin hugo
chmod +x /usr/local/bin/hugo
rm -f /tmp/hugo.tar.gz

mkdir -p /opt/hugo-blog/content/posts /opt/hugo-blog/themes /opt/hugo-blog/public
if [ ! -d /opt/hugo-blog/themes/PaperMod ]; then
    git clone --depth=1 https://github.com/adityatelange/hugo-PaperMod.git /opt/hugo-blog/themes/PaperMod
fi

tee /opt/hugo-blog/hugo.toml <<'HUGO_EOF'
baseURL = 'https://blog.${duckdns_domain}/'
languageCode = 'en-us'
title = "Thang's Tech Notes"
theme = 'PaperMod'

[pagination]
  pagerSize = 5

[params]
  env = 'production'
  title = "Thang's Tech Notes"
  description = "A tech blog co-crafted with prompt engineering and AI pair-programming on Oracle Cloud."
  author = "Thang Hoang & Antigravity"
  defaultTheme = "auto"
  ShowReadingTime = true
  ShowShareButtons = true
  ShowPostNavLinks = true
  ShowBreadCrumbs = true
  ShowCodeCopyButtons = true
  ShowWordCount = true
  ShowRssButtonInSectionTermList = true
  UseHugoToc = true
  disableSpecial1stPost = false
  disableScrollToTop = false
  comments = false
  hidemeta = false
  hideSummary = false
  showtoc = true
  tocopen = false

  [params.homeInfoParams]
    Title = "👋 Hi, I’m Thang Hoang - software developer"
    Content = "Welcome to my personal tech blog! This entire blog is — and will mostly be — written by my AI assistant **Antigravity** guided by my prompts. I love prompt engineering and exploring what autonomous AI pair-programming can build on Always Free cloud infrastructure.<br><br>🗓️ *Launched: August 21, 2026, 00:36 (GMT+7) • Hosted on `amd10` in Tokyo.*"

  [[params.socialIcons]]
    name = "github"
    url = "https://github.com/vinhthang"

[menu]
  [[menu.main]]
    identifier = "posts"
    name = "Posts"
    url = "/posts/"
    weight = 10

[outputs]
  home = ["HTML", "RSS", "JSON"]
HUGO_EOF

tee /etc/systemd/system/hugo-watcher.service <<'SERVICE_EOF'
[Unit]
Description=Hugo Blog Live Auto-Rebuilder
After=network.target

[Service]
Type=simple
User=opc
ExecStart=/usr/local/bin/hugo --minify --watch -s /opt/hugo-blog -d /opt/hugo-blog/public
Restart=always
RestartSec=3s

[Install]
WantedBy=multi-user.target
SERVICE_EOF

echo "=== 11. Deploying Caddy Web Server Configuration ==="
mkdir -p /etc/caddy
tee /etc/caddy/Caddyfile <<CADDY_EOF
${duckdns_domain} {
    reverse_proxy 127.0.0.1:8080
}

adguard.${duckdns_domain} {
    reverse_proxy 127.0.0.1:3000
}

music.${duckdns_domain} {
    reverse_proxy 127.0.0.1:4533
}

files.${duckdns_domain} {
    reverse_proxy 127.0.0.1:4180
}

blog.${duckdns_domain} {
    root * /opt/hugo-blog/public
    file_server
    encode gzip zstd
}
CADDY_EOF

tee /etc/systemd/system/caddy.service <<'SERVICE_EOF'
[Unit]
Description=Caddy Web Server with Automatic HTTPS
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
ExecStart=/usr/local/bin/caddy run --environ --config /etc/caddy/Caddyfile
ExecReload=/usr/local/bin/caddy reload --config /etc/caddy/Caddyfile
TimeoutStopSec=5s
LimitNOFILE=1048576
AmbientCapabilities=CAP_NET_BIND_SERVICE
Restart=always
RestartSec=3s

[Install]
WantedBy=multi-user.target
SERVICE_EOF

echo "=== 12. Starting and Enabling All Services ==="
systemctl daemon-reload
systemctl enable --now vietcalendar adguardhome navidrome filebrowser hugo-watcher caddy

echo "=== Cloud Init Completed Successfully! ==="
