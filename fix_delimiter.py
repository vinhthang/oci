import sys
with open("charts/vinhthang-fleet/templates/grafana.yaml", "r") as f:
    content = f.read()

content = content.replace("              severity: critical\nkind: Deployment", "              severity: critical\n---\napiVersion: apps/v1\nkind: Deployment")

with open("charts/vinhthang-fleet/templates/grafana.yaml", "w") as f:
    f.write(content)
