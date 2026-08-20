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

echo "=== 9. Deploying Caddy Web Server Configuration ==="
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

echo "=== 10. Starting and Enabling All Services ==="
systemctl daemon-reload
systemctl enable --now vietcalendar adguardhome navidrome caddy

echo "=== Cloud Init Completed Successfully! ==="
