import yaml
with open('charts/vinhthang-fleet/values.yaml', 'r') as f:
    values = yaml.safe_load(f)

for comp in ['proxy', 'pulsar_metadata', 'toolset']:
    if comp not in values['pulsar']:
        values['pulsar'][comp] = {}
    values['pulsar'][comp]['podMonitor'] = {'enabled': False}

with open('charts/vinhthang-fleet/values.yaml', 'w') as f:
    yaml.dump(values, f, default_flow_style=False)
