# ADR 0040: Migrate Apache Pulsar to Data Namespace & Broker Port 8088 Governance

## Context
- **Absence of Official ASF Operator & Up-to-Date Release**: Apache Pulsar does not maintain an officially supported, feature-complete Kubernetes operator in the ASF ecosystem. The cluster runs on the latest upstream Apache Pulsar version 4.0.12 deployed via official Pulsar Helm Chart 4.7.0.
- **Namespace Domain Isolation Drift**: Pulsar components (Zookeeper, BookKeeper, Broker, Autorecovery) were historically deployed into the `default` Kubernetes namespace, violating ADR-0018 cluster-wide namespace domain partitioning (`data`, `apps`, `observability`, `system`).
- **Port Allocation Governance Violation**: The Pulsar Broker administrative HTTP web service listens on generic port `8080`, violating ADR-0005 and ADR-0038 port allocation governance policies forbidding port 8080 across all workloads to avoid port collisions.
- **Zero Active Workload Impact**: Audit of cluster topics and message backlogs verified 0 active user topics, allowing a seamless migration with zero data loss or operational disruption.

## Decision
1. **Relocate Pulsar to `data` Namespace via Helm**:
   - Configure `pulsar.namespace: data` in `charts/vinhthang-fleet/values.yaml` so all Pulsar subchart components render and deploy into the dedicated `data` namespace alongside PostgreSQL, MongoDB, and Redis.
   - Keep node scheduling strictly pinned to the high-memory control plane node (`arm10`) with `nodeSelector: kubernetes.io/hostname: arm10`.
2. **Remap Broker HTTP Admin to Dedicated Port 8088**:
   - Configure `pulsar.broker.ports.http: 8088` in `charts/vinhthang-fleet/values.yaml`, fully eliminating port 8080 collisions across the fleet.
3. **Purge Legacy Resources & Reset Persistent Volume Claims**:
   - Cleanly delete legacy StatefulSets (`fleet-pulsar-bookie`, `fleet-pulsar-broker`, `fleet-pulsar-recovery`, `fleet-pulsar-zookeeper`), Services, PVCs, and ConfigMaps from the `default` namespace.
   - Patch `claimRef: null` on the 3 local persistent volumes on `arm10` (`fleet-pulsar-zookeeper-data-0`, `fleet-pulsar-bookie-journal-0`, `fleet-pulsar-bookie-ledgers-0`) to reset their status to `Available` so the new StatefulSets in the `data` namespace immediately bind to them.
4. **Deploy Cleanly via Master Umbrella Helm Chart**:
   - Commit declarative changes to GitOps and allow the in-cluster GitOps webhook controller to apply the chart into the `data` namespace.

## Consequences
- **Strict Compliance with ADR-0018**: Apache Pulsar now resides strictly within the `data` domain namespace alongside all fleet data infrastructure, adhering to RBAC boundaries and tenant partitioning.
- **Elimination of Port 8080 Collisions**: Broker administrative endpoints operate on port 8088, satisfying cluster port governance invariants.
- **Clean PV Rebinding on `arm10`**: Existing local storage persistent volumes on `arm10` are cleanly released and bound to the new `data` namespace claims without requiring manual filesystem re-initialization or node storage reconfiguration.
- **Zero Blast Radius**: Since no active topics or publishers were connected, service cutover incurs zero data loss and zero production downtime.
