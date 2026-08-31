import sys

with open("charts/vinhthang-fleet/templates/grafana.yaml", "r") as f:
    content = f.read()

# I will find the alerting ConfigMap and properly append the rules.yaml to its data block
