with open("charts/vinhthang-fleet/values.yaml", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.strip() == "nodeSelector:n    kubernetes.io/hostname: arm10":
        new_lines.append("  nodeSelector:\n")
        new_lines.append("    kubernetes.io/hostname: arm10\n")
    else:
        new_lines.append(line)

with open("charts/vinhthang-fleet/values.yaml", "w") as f:
    f.writelines(new_lines)
