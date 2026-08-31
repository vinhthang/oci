# 24. Deploy Apache Pulsar Helm Chart on Oracle10 Node

Date: 2026-08-29

## Status

Deprecated (Superseded by ADR-0029)

## Context

The previous lightweight Apache Pulsar standalone deployment on the master node (`arm10`) was decommissioned to reclaim memory resources (see ADR-0019). The system still requires a durable, high-throughput event bus to support future stream processing, data ingestion, and microservice decoupled communication.

We have an external worker node, `oracle10`, which has substantial computing capacity (4 OCPU, 30GB RAM). To leverage these resources, we need to deploy the full Apache Pulsar cluster.

## Decision

We will deploy the official Apache Pulsar Helm chart (`apache/pulsar` version 4.7.0) to the cluster, explicitly pinned to the `oracle10` node.
- **Node Affinity**: All Pulsar components (Zookeeper, Bookkeeper, Broker, Autorecovery) are configured with a `nodeSelector` targeting `kubernetes.io/hostname: oracle10`.
- **Helm Integration**: The Pulsar chart is added as a dependency to the main umbrella chart (`vinhthang-fleet`).
- **Storage Configuration**: To bypass the disabled local-path provisioner on `arm10` while maintaining data safety on `oracle10`, we manually pre-provision `PersistentVolume`s for Zookeeper (`data`, `dataLog`) and Bookkeeper (`journal`, `ledgers`) using the `local-storage` provisioner. These PVs map directly to host directories on `oracle10` (`/home/thang/pulsar/*`), bypassing any root `sudo` limitations.
- **Observability Stack**: The default `victoria-metrics-k8s-stack` bundled with the Pulsar chart is disabled to avoid CRD collision and excessive resource overhead.

## Consequences

### Positive
- **High Resource Availability**: Pulsar components run on the 30GB RAM `oracle10` node, safely decoupled from the critical control plane (`arm10`) and edge gateway (`amd10`/`amd11`).
- **Distributed Architecture Ready**: Using the official distributed Helm chart prepares the infrastructure for multi-node scaling if more nodes are added to the cluster.
- **Zero Sudo Requirements**: Host storage binds via standard `/home/thang` directories, ensuring clean permission compliance with Kubernetes security contexts.

### Negative
- **Single Node Bottleneck**: Currently scaled to `replicaCount: 1` per component. While fully functional, high availability and node fault tolerance are lacking until additional worker nodes are provisioned.
- **Dependency on External Node**: Since `oracle10` is an external workstation, if the node becomes temporarily unavailable, the event bus will go down, halting message processing in dependent microservices.
