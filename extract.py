import sys

with open("/tmp/fleet.yaml", "r") as f:
    docs = f.read().split("---")

new_docs = []
for doc in docs:
    if "namespace: observability" in doc or "namespace: \"observability\"" in doc or ("Role" in doc and "observability" in doc):
        new_docs.append(doc)

with open("/tmp/observability.yaml", "w") as f:
    f.write("---".join(new_docs))
