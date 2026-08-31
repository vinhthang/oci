import yaml

with open("charts/vinhthang-fleet/values.yaml", "r") as f:
    values = yaml.safe_load(f)

# The safe_load will only keep the LAST key if there are duplicates! 
# So it lost remoteWrite!
