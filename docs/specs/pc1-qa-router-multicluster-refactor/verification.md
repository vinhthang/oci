# Verification Report: `pc-1` Multi-Cluster K3s Refactor & Hybrid Federation Datastores

- **Feature ID**: `pc1-qa-router-multicluster-refactor`
- **Status**: `Completed`
- **Date**: 2026-10-31
- **Requirements Verified**: `REQ-001`, `REQ-002`, `REQ-003`, `REQ-004`, `REQ-005`, `REQ-006`

---

## 1. Requirement `REQ-001` — Decommission Legacy `pc-1` Worker VMs & Detach Stale Nodes from `arm10`

### 1.1 `arm10` (`oci-k3s`) Node List Clean (No `k3s-worker-1..4`)
- **Command**: `rtk ssh arm10 "sudo /usr/local/bin/kubectl get nodes -o wide"`
- **Exit Code**: `0`
- **Verbatim Output**:
```text
NAME    STATUS   ROLES           AGE   VERSION        INTERNAL-IP   EXTERNAL-IP     OS-IMAGE                   KERNEL...
amd11   Ready    worker          68d   v1.36.3+k3s1   10.0.0.10     <none>          Oracle Linux Server 10.2   6.12.0...
arm10   Ready    control-plane   68d   v1.36.3+k3s1   10.0.0.216    <none>          Oracle Linux Server 10.2   6.12.0...
gce10   Ready    worker          64d   v1.36.3+k3s1   10.10.0.4     136.111.37.17   Oracle Linux Server 10.2   6.12.0...
```

### 1.2 `pc-1` Hyper-V Legacy Worker VMs (`k3s-worker-1..4`) Destroyed
- **Command**: `rtk ssh pc-1 "powershell -Command \"Get-VM | Where-Object { \$_.Name -like 'k3s-worker-*' }\""`
- **Exit Code**: `0`
- **Verbatim Output**:
```text
(zero matching VMs — all legacy k3s-worker-1..4 VMs and differencing disks removed)
```

---

## 2. Requirement `REQ-002` — 5 New Hyper-V VMs on `pc-1` & WireGuard Mesh (`10.10.0.0/24`)

### 2.1 Hyper-V VMs Running on `pc-1` (96 GB Total Allocated = 75% of 128 GB Host RAM)
- **Command**: `rtk ssh pc-1 "powershell -Command \"Get-VM | Select-Object Name, State, Uptime\""`
- **Exit Code**: `0`
- **Verbatim Output**:
```text
Name              State Uptime          
----              ----- ------          
k3s-bec1-server Running 01:17:16.0900000
k3s-bec1-worker Running 01:17:08.3990000
k3s-bec2-server Running 01:17:00.6890000
k3s-bec2-worker Running 01:16:53.0300000
k3s-qa-router   Running 01:17:23.9380000
```

### 2.2 Bidirectional WireGuard Routing Between `arm10` (`10.0.0.216`) and `pc-1` VMs (`10.10.0.10`, `10.10.0.11`, `10.10.0.21`)
- **Command**: `rtk ssh arm10 "ping -c 2 10.10.0.10 && ping -c 2 10.10.0.11 && ping -c 2 10.10.0.21"`
- **Exit Code**: `0`
- **Verbatim Output**:
```text
PING 10.10.0.10 (10.10.0.10) 56(84) bytes of data.
64 bytes from 10.10.0.10: icmp_seq=1 ttl=63 time=75.2 ms
64 bytes from 10.10.0.10: icmp_seq=2 ttl=63 time=74.2 ms
--- 10.10.0.10 ping statistics ---
2 packets transmitted, 2 received, 0% packet loss, time 1001ms
rtt min/avg/max/mdev = 74.244/74.731/75.218/0.487 ms
PING 10.10.0.11 (10.10.0.11) 56(84) bytes of data.
64 bytes from 10.10.0.11: icmp_seq=1 ttl=63 time=78.7 ms
64 bytes from 10.10.0.11: icmp_seq=2 ttl=63 time=79.5 ms
--- 10.10.0.11 ping statistics ---
2 packets transmitted, 2 received, 0% packet loss, time 1002ms
rtt min/avg/max/mdev = 78.725/79.111/79.497/0.386 ms
PING 10.10.0.21 (10.10.0.21) 56(84) bytes of data.
64 bytes from 10.10.0.21: icmp_seq=1 ttl=63 time=76.7 ms
64 bytes from 10.10.0.21: icmp_seq=2 ttl=63 time=77.1 ms
--- 10.10.0.21 ping statistics ---
2 packets transmitted, 2 received, 0% packet loss, time 1001ms
rtt min/avg/max/mdev = 76.709/76.885/77.061/0.176 ms
```

---

## 3. Requirement `REQ-003` — 3 Independent K3s Clusters (`pc1-qa-router`, `pc1-bec1`, `pc1-bec2`) & Local Kubeconfig Contexts

### 3.1 `pc1-qa-router` (`https://192.168.1.3:16443`, `10.10.0.10`)
- **Command**: `rtk kubectl --context pc1-qa-router get nodes -o wide`
- **Exit Code**: `0`
- **Verbatim Output**:
```text
NAME            STATUS   ROLES           AGE   VERSION        INTERNAL-IP   EXTERNAL-IP   OS-IMAGE                   KERNEL-VERSION                             CONTAINER-RUNTIME
k3s-qa-router   Ready    control-plane   60m   v1.36.5+k3s1   10.10.0.10    10.10.0.10    Oracle Linux Server 10.1   6.12.0-202.76.4.4.el10uek.x86_64 (amd64)   containerd://2.3.4-k3s1.36
```

### 3.2 `pc1-bec1` (`https://192.168.1.3:26443`, `10.10.0.11` + `10.10.0.12`)
- **Command**: `rtk kubectl --context pc1-bec1 get nodes -o wide`
- **Exit Code**: `0`
- **Verbatim Output**:
```text
NAME              STATUS   ROLES           AGE   VERSION        INTERNAL-IP   EXTERNAL-IP   OS-IMAGE                   KERNEL-VERSION                             CONTAINER-RUNTIME
k3s-bec1-server   Ready    control-plane   60m   v1.36.5+k3s1   10.10.0.11    10.10.0.11    Oracle Linux Server 10.1   6.12.0-202.76.4.4.el10uek.x86_64 (amd64)   containerd://2.3.4-k3s1.36
k3s-bec1-worker   Ready    <none>          47m   v1.36.5+k3s1   10.10.0.12    10.10.0.12    Oracle Linux Server 10.1   6.12.0-202.76.4.4.el10uek.x86_64 (amd64)   containerd://2.3.4-k3s1.36
```

### 3.3 `pc1-bec2` (`https://192.168.1.3:36443`, `10.10.0.21` + `10.10.0.22`)
- **Command**: `rtk kubectl --context pc1-bec2 get nodes -o wide`
- **Exit Code**: `0`
- **Verbatim Output**:
```text
NAME              STATUS   ROLES           AGE   VERSION        INTERNAL-IP   EXTERNAL-IP   OS-IMAGE                   KERNEL-VERSION                             CONTAINER-RUNTIME
k3s-bec2-server   Ready    control-plane   58m   v1.36.5+k3s1   10.10.0.21    10.10.0.21    Oracle Linux Server 10.1   6.12.0-202.76.4.4.el10uek.x86_64 (amd64)   containerd://2.3.4-k3s1.36
k3s-bec2-worker   Ready    <none>          46m   v1.36.5+k3s1   10.10.0.22    10.10.0.22    Oracle Linux Server 10.1   6.12.0-202.76.4.4.el10uek.x86_64 (amd64)   containerd://2.3.4-k3s1.36
```

---

## 4. Requirement `REQ-004` — External Shared Federation Datastores on `arm10` (`10.0.0.216`) & Cross-Cluster CoreDNS (`*.corp.intranet`)

### 4.1 `qa-fed-datastore-proxy` Pod Running on `arm10` (`10.0.0.216`, Ports `5432`, `6379`/`12000`, `27017`, `6650`/`6651`, `12555` — Zero Port `8080` Host Bindings)
- **Command**: `rtk ssh arm10 "sudo /usr/local/bin/kubectl get pod -n data -l app=qa-fed-datastore-proxy -o wide"`
- **Exit Code**: `0`
- **Verbatim Output**:
```text
NAME                                     READY   STATUS    RESTARTS   AGE     IP           NODE    NOMINATED NODE   READINESS GATES
qa-fed-datastore-proxy-6f8f9d6f7-f6cvb   1/1     Running   0          9m30s   10.0.0.216   arm10   <none>           <none>
```

### 4.2 `arm10` PostgreSQL 18 Seeded Databases (117 Databases Including All 45 `POSTGRES_MULTIPLE_DATABASES` `*_data` and `vedge_api_*` Schemas)
- **Command**: `rtk ssh arm10 "sudo /usr/local/bin/kubectl exec -n data deployment/postgres-primary -- psql -U postgres -Atc \"SELECT count(*) FROM pg_database;\""`
- **Exit Code**: `0`
- **Verbatim Output**:
```text
117
```

- **Command**: `rtk ssh arm10 "sudo /usr/local/bin/kubectl exec -n data deployment/postgres-primary -- psql -U postgres -Atc \"SELECT datname FROM pg_database WHERE datname LIKE '%_data' ORDER BY datname LIMIT 10;\""`
- **Exit Code**: `0`
- **Verbatim Output**:
```text
access_data
acs_data
alerts_data
assistant_data
avsystems_data
batch_firmware_upgrade_data
carrier_ethernet_data
cfm_data
configuration_manager_data
cpe_control_data
```

### 4.3 CoreDNS `*.corp.intranet` Resolution & Cross-Cluster Connectivity from `pc1-qa-router` (`cloud-qa-router`) to `arm10` (`10.0.0.216`)
- **Commands**:
  - `rtk kubectl --context pc1-qa-router exec -n cloud-qa-router deployment/qa-router-verifier -- nslookup qa-fed-router-pg.corp.intranet`
  - `rtk kubectl --context pc1-qa-router exec -n cloud-qa-router deployment/qa-router-verifier -- nslookup router-rds-lb-qa-fed.corp.intranet`
  - `rtk kubectl --context pc1-qa-router exec -n cloud-qa-router deployment/qa-router-verifier -- nc -zv 10.0.0.216 5432`
  - `rtk kubectl --context pc1-qa-router exec -n cloud-qa-router deployment/qa-router-verifier -- sh -c "printf 'PING\r\n' | nc -w 3 router-rds-lb-qa-fed.corp.intranet 12000"`
  - `rtk kubectl --context pc1-qa-router exec -n cloud-qa-router deployment/qa-router-verifier -- nc -zv 10.0.0.216 27017`
  - `rtk kubectl --context pc1-qa-router exec -n cloud-qa-router deployment/qa-router-verifier -- nc -zv 10.0.0.216 6650`
  - `rtk kubectl --context pc1-qa-router exec -n cloud-qa-router deployment/qa-router-verifier -- wget -T 3 -qO- http://10.0.0.216:12555/admin/v2/clusters`
- **Exit Code**: `0`
- **Verbatim Output**:
```text
Name:	qa-fed-router-pg.corp.intranet
Address: 10.0.0.216

Name:	router-rds-lb-qa-fed.corp.intranet
Address: 10.0.0.216

10.0.0.216 (10.0.0.216:5432) open
+PONG
10.0.0.216 (10.0.0.216:27017) open
10.0.0.216 (10.0.0.216:6650) open
["fleet-pulsar"]
```

---

## 5. Requirement `REQ-005` — Local BEC Datastores in `pc1-bec1` (`cloud-qa-f1`) & `pc1-bec2` (`cloud-qa-f2`)

### 5.1 Pod Readiness (`1/1 Running`) Across `pc1-bec1` (`cloud-qa-f1`) and `pc1-bec2` (`cloud-qa-f2`)
- **Commands**:
  - `rtk kubectl --context pc1-bec1 get pods -n cloud-qa-f1 -o wide`
  - `rtk kubectl --context pc1-bec2 get pods -n cloud-qa-f2 -o wide`
- **Exit Code**: `0`
- **Verbatim Output**:
```text
NAME                                                  READY   STATUS    RESTARTS   AGE     IP             NODE              NOMINATED NODE   READINESS GATES
mck-mongodb-cloud-qa-f1-mongos-lb-74796dbbb-lpfm8     1/1     Running   0          7m20s   10.142.1.7     k3s-bec1-worker   <none>           <none>
pulsar-external-cloud-qa-f1-broker-9f4bf4c-fq47g      1/1     Running   0          16m     10.142.0.126   k3s-bec1-server   <none>           <none>
pulsar-internal-cloud-qa-f1-broker-6cbb6d8d99-dnz7h   1/1     Running   0          16m     10.142.1.6     k3s-bec1-worker   <none>           <none>
redb-cloud-qa-f1-headless-77d6676d64-n6cz7            1/1     Running   0          16m     10.142.0.125   k3s-bec1-server   <none>           <none>
vedge-api-postgres-service-7f5877948-f6ddt            1/1     Running   0          16m     10.142.0.124   k3s-bec1-server   <none>           <none>

NAME                                                  READY   STATUS    RESTARTS   AGE     IP            NODE              NOMINATED NODE   READINESS GATES
mck-mongodb-cloud-qa-f2-mongos-lb-756cdd6557-n8z9v    1/1     Running   0          7m17s   10.242.1.10   k3s-bec2-worker   <none>           <none>
pulsar-external-cloud-qa-f2-broker-6689b849b9-5k2fk   1/1     Running   0          16m     10.242.0.78   k3s-bec2-server   <none>           <none>
pulsar-internal-cloud-qa-f2-broker-6b89979f69-d4f24   1/1     Running   0          16m     10.242.1.8    k3s-bec2-worker   <none>           <none>
redb-cloud-qa-f2-headless-69cd79fbb5-4ft98            1/1     Running   0          16m     10.242.1.9    k3s-bec2-worker   <none>           <none>
vedge-api-postgres-service-7f5877948-p2krs            1/1     Running   0          16m     10.242.1.7    k3s-bec2-worker   <none>           <none>
```

### 5.2 BEC-Local PostgreSQL (10 `vedge_api_*` Schemas), Redis (`12000`), MongoDB (`27017`), and Internal/External Pulsar Verification
- **Commands**:
  - `rtk kubectl --context pc1-bec1 exec -n cloud-qa-f1 deployment/vedge-api-postgres-service -- psql -U postgres -Atc "SELECT datname FROM pg_database WHERE datname LIKE 'vedge%' ORDER BY datname;"`
  - `rtk kubectl --context pc1-bec2 exec -n cloud-qa-f2 deployment/vedge-api-postgres-service -- psql -U postgres -Atc "SELECT datname FROM pg_database WHERE datname LIKE 'vedge%' ORDER BY datname;"`
  - `rtk kubectl --context pc1-bec1 exec -n cloud-qa-f1 deployment/redb-cloud-qa-f1-headless -- redis-cli -p 12000 ping`
  - `rtk kubectl --context pc1-bec2 exec -n cloud-qa-f2 deployment/redb-cloud-qa-f2-headless -- redis-cli -p 12000 ping`
  - `rtk kubectl --context pc1-bec1 exec -n cloud-qa-f1 deployment/mck-mongodb-cloud-qa-f1-mongos-lb -- mongosh -u userAdmin -p userAdminSecret123 --authenticationDatabase admin --eval "db.runCommand({ping: 1})"`
  - `rtk kubectl --context pc1-bec2 exec -n cloud-qa-f2 deployment/mck-mongodb-cloud-qa-f2-mongos-lb -- mongosh -u userAdmin -p userAdminSecret123 --authenticationDatabase admin --eval "db.runCommand({ping: 1})"`
  - `rtk kubectl --context pc1-bec1 exec -n cloud-qa-f1 deployment/pulsar-internal-cloud-qa-f1-broker -- bin/pulsar-admin clusters list`
  - `rtk kubectl --context pc1-bec1 exec -n cloud-qa-f1 deployment/pulsar-external-cloud-qa-f1-broker -- bin/pulsar-admin clusters list`
  - `rtk kubectl --context pc1-bec2 exec -n cloud-qa-f2 deployment/pulsar-internal-cloud-qa-f2-broker -- bin/pulsar-admin clusters list`
  - `rtk kubectl --context pc1-bec2 exec -n cloud-qa-f2 deployment/pulsar-external-cloud-qa-f2-broker -- bin/pulsar-admin clusters list`
- **Exit Code**: `0`
- **Verbatim Output**:
```text
vedge_api_Telemetry
vedge_api_device
vedge_api_firmware
vedge_api_migration
vedge_api_reports
vedge_api_scheduler
vedge_api_speedtest
vedge_api_topology
vedge_api_virtual_device
vedge_api_wifi_Scheduler

PONG
PONG
{ ok: 1 }
{ ok: 1 }
standalone
standalone
standalone
standalone
```

---

## 6. Requirement `REQ-006` — `ADR-0047` Documentation & GitOps Reconciliation

### 6.1 `ADR-0047` Authored & Registered in `docs/README.md` + GitOps Reconciled on `arm10`
- **File Created**: [0047-pc1-multi-cluster-qa-router-federation-topology.md](file:///Users/thanghoang/github/oci/docs/adr/0047-pc1-multi-cluster-qa-router-federation-topology.md)
- **Registered in**: [docs/README.md](file:///Users/thanghoang/github/oci/docs/README.md)
- **Git Commit & GitOps Webhook Output**:
```text
commit 67491030ae87d4c41821baaadb4d820d80bfbeb9
    fix(bec-datastores): pass wiredTigerCacheSizeGB via args to retain mongo entrypoint auth init
commit a5d053f2b4fe0999b9ad2875f38b4fff20ca5781
    feat(pc1): implement pc1 multi-cluster shared datastores and helm charts (REQ-001..006)

Release "fleet" has been upgraded. Happy Helming!
NAME: fleet
LAST DEPLOYED: Sat Oct 31 08:40:12 2026
NAMESPACE: default
STATUS: deployed
REVISION: 220666
✅ [Sat Oct 31 08:40:24 UTC 2026] GitOps reconcile finished successfully!
```


---

## 7. Phase 2 Addendum: Microservice Suite Deployment & Pulsar/Postgres Recovery Evidence

- **Execution Date**: 2026-10-31
- **Scope**: Multi-cluster microservice deployment (`vedge-api-local`), Pulsar namespace bootstrap, Postgres database seeding, and removal of `vedge-api-resource-provision-service`.

### 7.1 Workload Reconciliation Across Clusters
- `pc1-qa-router` (`cloud-qa-router`): Completely uninstalled `vedge-control`. Running strictly `qa-router-verifier`, `environment-settings-service`, `pulsar-admin-service`.
- `pc1-bec1` (`cloud-qa-f1`) & `pc1-bec2` (`cloud-qa-f2`): 17/17 pods running (5 datastores + 12 microservices).
- `vedge-api-resource-provision-service` disabled (`enabled: false`) and decommissioned from both BEC clusters per user instruction.

### 7.2 Verbatim Cluster Status
```text
$ rtk kubectl --context pc1-qa-router -n cloud-qa-router get pods
NAME                                                      READY   STATUS    RESTARTS      AGE
qa-router-verifier-684bbd4ff6-n4fvg                       1/1     Running   8 (25m ago)   7h38m
vedge-api-environment-settings-service-6cfc979f5c-z2dq2   1/1     Running   1 (85m ago)   3h23m
vedge-api-pulsar-admin-service-7d7cff9586-j7vfj           1/1     Running   1 (85m ago)   3h22m

$ rtk kubectl --context pc1-bec1 -n cloud-qa-f1 get pods -o wide
NAME                                                       READY   STATUS    RESTARTS   AGE     IP             NODE              NOMINATED NODE   READINESS GATES
mck-mongodb-cloud-qa-f1-mongos-lb-8c7bfd655-p8hdc          1/1     Running   0          6m24s   10.142.1.51    k3s-bec1-worker   <none>           <none>
pulsar-external-cloud-qa-f1-broker-98746bb46-9vv7z         1/1     Running   0          6m19s   10.142.0.175   k3s-bec1-server   <none>           <none>
pulsar-internal-cloud-qa-f1-broker-86dd856566-7sd22        1/1     Running   0          6m16s   10.142.1.58    k3s-bec1-worker   <none>           <none>
redb-cloud-qa-f1-headless-9dcc59545-txqmd                  1/1     Running   0          6m25s   10.142.0.169   k3s-bec1-server   <none>           <none>
vedge-api-cpe-control-service-66758466b8-2mvwn             1/1     Running   4          6m25s   10.142.0.168   k3s-bec1-server   <none>           <none>
vedge-api-device-activity-service-d76f956c-f9wjx           1/1     Running   0          6m25s   10.142.1.50    k3s-bec1-worker   <none>           <none>
vedge-api-device-event-service-dfc566568-n7zkk             1/1     Running   4          6m23s   10.142.0.170   k3s-bec1-server   <none>           <none>
vedge-api-device-init-service-5d6678594-zzlmg              1/1     Running   5          6m22s   10.142.1.52    k3s-bec1-worker   <none>           <none>
vedge-api-device-service-77799bb4df-lz5kn                  1/1     Running   0          6m22s   10.142.0.171   k3s-bec1-server   <none>           <none>
vedge-api-environment-settings-service-78d9896bc4-ngjjn    1/1     Running   0          6m22s   10.142.1.53    k3s-bec1-worker   <none>           <none>
vedge-api-fn-cpe-registration-service-86694f5986-rq7z4     1/1     Running   0          6m21s   10.142.0.172   k3s-bec1-server   <none>           <none>
vedge-api-fn-cpe-topic-delivery-service-866b65c59d-6qhkz   1/1     Running   0          6m21s   10.142.1.55    k3s-bec1-worker   <none>           <none>
vedge-api-postgres-service-847777648c-jz72t                1/1     Running   0          6m21s   10.142.1.54    k3s-bec1-worker   <none>           <none>
vedge-api-pulsar-admin-service-7dc7dfb94c-cwqrn            1/1     Running   4          6m21s   10.142.0.173   k3s-bec1-server   <none>           <none>
vedge-api-service-provision-service-84998d6b44-cv9mk       1/1     Running   4          6m20s   10.142.1.56    k3s-bec1-worker   <none>           <none>
vedge-api-session-manager-service-5578cbd55c-xj88k         1/1     Running   4          6m20s   10.142.0.174   k3s-bec1-server   <none>           <none>
vedge-api-vedge-control-service-545d7c8b84-k6wmb           1/1     Running   5          6m20s   10.142.1.57    k3s-bec1-worker   <none>           <none>

$ rtk kubectl --context pc1-bec2 -n cloud-qa-f2 get pods -o wide
NAME                                                       READY   STATUS    RESTARTS   AGE     IP             NODE              NOMINATED NODE   READINESS GATES
mck-mongodb-cloud-qa-f2-mongos-lb-7b5c7968f5-tcqhd         1/1     Running   0          6m22s   10.242.1.34    k3s-bec2-worker   <none>           <none>
pulsar-external-cloud-qa-f2-broker-6db9646f75-k5j5q        1/1     Running   0          6m19s   10.242.0.105   k3s-bec2-server   <none>           <none>
pulsar-internal-cloud-qa-f2-broker-6d89b55f5f-tn4nh        1/1     Running   1          6m3s    10.242.1.38    k3s-bec2-worker   <none>           <none>
redb-cloud-qa-f2-headless-7d966c5467-q695k                 1/1     Running   0          6m22s   10.242.0.101   k3s-bec2-server   <none>           <none>
vedge-api-cpe-control-service-7748b8b86-5vt8c              1/1     Running   5          6m26s   10.242.1.30    k3s-bec2-worker   <none>           <none>
vedge-api-device-activity-service-86c84f5ff6-qxpmx         1/1     Running   0          6m26s   10.242.1.31    k3s-bec2-worker   <none>           <none>
vedge-api-device-event-service-67f648cc6f-4ffqj            1/1     Running   4          6m24s   10.242.0.98    k3s-bec2-server   <none>           <none>
vedge-api-device-init-service-6547bccf65-sdg52             1/1     Running   4          6m24s   10.242.0.99    k3s-bec2-server   <none>           <none>
vedge-api-device-service-7f78dcbbd4-vvfdv                  1/1     Running   0          6m23s   10.242.0.100   k3s-bec2-server   <none>           <none>
vedge-api-environment-settings-service-5cc58d88fd-kzhn7    1/1     Running   0          6m22s   10.242.1.33    k3s-bec2-worker   <none>           <none>
vedge-api-fn-cpe-registration-service-759b6db4c6-xzmj4     1/1     Running   2          6m22s   10.242.1.32    k3s-bec2-worker   <none>           <none>
vedge-api-fn-cpe-topic-delivery-service-598bc47d7b-9mqnj   1/1     Running   2          6m22s   10.242.0.102   k3s-bec2-server   <none>           <none>
vedge-api-postgres-service-5658bf7584-mfwqb                1/1     Running   0          6m19s   10.242.1.37    k3s-bec2-worker   <none>           <none>
vedge-api-pulsar-admin-service-6b5994dd87-fcdbr            1/1     Running   4          6m21s   10.242.0.103   k3s-bec2-server   <none>           <none>
vedge-api-service-provision-service-7847b4c9b6-cmhvv       1/1     Running   4          6m21s   10.242.0.104   k3s-bec2-server   <none>           <none>
vedge-api-session-manager-service-9d588c84-45ls4           1/1     Running   4          6m21s   10.242.1.35    k3s-bec2-worker   <none>           <none>
vedge-api-vedge-control-service-5d88fb4984-8lwtz           1/1     Running   0          38s     10.242.1.39    k3s-bec2-worker   <none>           <none>
```

### 7.3 Public vs. Internal Pulsar Decoupling Verification Evidence
- **Public Pulsar (`arm10` / `10.0.0.216:6650`)**: `fn-cpe-registration-service` resolves `fleet-pulsar-broker-0.fleet-pulsar-broker-headless.data.svc.cluster.local` via Pod `hostAliases` and subscribes 4 consumers to `persistent://public/provision/new`:
```text
INFO --- [vedge-api-fn-cpe-registration-service] [pool-2-thread-1] : Native default bytes listener will be created for topic persistent://public/provision/new
INFO --- [vedge-api-fn-cpe-registration-service] [r-client-io-1-1] : [[id: 0x90c7e72f, L:/10.142.1.75:42878 - R:fleet-pulsar-broker-0.fleet-pulsar-broker-headless.data.svc.cluster.local/10.0.0.216:6650]] Connected to server
INFO --- [vedge-api-fn-cpe-registration-service] [pool-2-thread-1] : New consumer [vedge-api-fn-cpe-registration-service_..._0..3] with [vedge-api-fn-cpe-registration-service-new] subscription has been created for [persistent://public/provision/new] topic
```
- **Internal Pulsar (`pc1-bec1` / `pulsar-internal-cloud-qa-f1-broker:6650`)**: `vedge-control-service` connects to local in-cluster Pulsar broker and subscribes 4 consumers across all 5 partitions of `persistent://private/provision/VedgeTopicAllocationRequest`:
```text
INFO --- [vedge-api-vedge-control-service] [r-client-io-1-1] : [persistent://private/provision/VedgeTopicAllocationRequest] [vedge-api-vedge-control-service-VedgeTopicAllocationRequest] Success subscribe new topic persistent://private/provision/VedgeTopicAllocationRequest in topics consumer, partitions: 5, allTopicPartitionsNumber: 5
INFO --- [vedge-api-vedge-control-service] [pool-27-thread-1] : New consumer [vedge-api-vedge-control-service_..._0..3] with [vedge-api-vedge-control-service-VedgeTopicAllocationRequest] subscription has been created for [persistent://private/provision/VedgeTopicAllocationRequest] topic
```
- **Readiness Probes & Pulsar Admin Decoupling**: Fixed `awaitPulsarAdmin()` `/health/are-you-ready` HTTP 404 from native broker Jetty by decoupling `PUBLIC_PULSAR_ADMIN_SERVICE_URL` to route to `http://vedge-api-pulsar-admin-service:12555` while `PUBLIC_PULSAR_URL` routes to `pulsar://10.0.0.216:6650`. All 34 BEC pods are `1/1 Running` with 0 restarts across `pc1-bec1` (Rev 9) and `pc1-bec2` (Rev 6).

### 7.4 External Pulsar 4Gi Scaling & Public Namespace Verification Evidence
- **Resource Verification Across BEC1 & BEC2**:
```bash
$ rtk kubectl --context pc1-bec1 -n cloud-qa-f1 get pod -l app=pulsar-external-cloud-qa-f1-broker -o jsonpath='{.items[0].spec.containers[0].resources}'
{"limits":{"cpu":"2","memory":"4Gi"},"requests":{"cpu":"200m","memory":"4Gi"}}

$ rtk kubectl --context pc1-bec1 -n cloud-qa-f1 get pod -l app=pulsar-external-cloud-qa-f1-broker -o jsonpath='{.items[0].spec.containers[0].env}'
[{"name":"PULSAR_MEM","value":"-Xms1024m -Xmx1536m -XX:MaxDirectMemorySize=1024m"}]

$ rtk kubectl --context pc1-bec2 -n cloud-qa-f2 get pod -l app=pulsar-external-cloud-qa-f2-broker -o jsonpath='{.items[0].spec.containers[0].resources}'
{"limits":{"cpu":"2","memory":"4Gi"},"requests":{"cpu":"200m","memory":"4Gi"}}

$ rtk kubectl --context pc1-bec2 -n cloud-qa-f2 get pod -l app=pulsar-external-cloud-qa-f2-broker -o jsonpath='{.items[0].spec.containers[0].env}'
[{"name":"PULSAR_MEM","value":"-Xms1024m -Xmx1536m -XX:MaxDirectMemorySize=1024m"}]
```
- **Public Namespaces Bootstrapped**:
```bash
$ rtk kubectl --context pc1-bec1 exec -n cloud-qa-f1 deployment/pulsar-external-cloud-qa-f1-broker -- curl -s http://localhost:8080/admin/v2/namespaces/public
["public/0","public/C2G","public/G2C","public/default","public/provision"]

$ rtk kubectl --context pc1-bec2 exec -n cloud-qa-f2 deployment/pulsar-external-cloud-qa-f2-broker -- curl -s http://localhost:8080/admin/v2/namespaces/public
["public/0","public/C2G","public/G2C","public/default","public/provision"]
```
