import sys

with open('caddy/Caddyfile', 'r') as f:
    content = f.read()

header = """{
    servers {
        metrics
    }
}
"""

if "servers {" not in content:
    content = header + content

if ":2019 {" not in content:
    content += """
:2019 {
    metrics
}
"""

with open('caddy/Caddyfile', 'w') as f:
    f.write(content)
