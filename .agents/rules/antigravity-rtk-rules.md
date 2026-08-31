# RTK - Rust Token Killer (Project Rule)

Always prefix shell commands with `rtk` to minimize token consumption.

- **Maven**: `rtk mvn test`, `rtk mvn clean package`
- **Kubernetes**: `rtk kubectl get pods`, `rtk kubectl logs`
- **Cloud & OCI**: `oci <cmd> | rtk json`, `rtk err oci <cmd>`
- **Docker / Podman**: `rtk docker ps`, `rtk docker logs`
- **Git & Search**: `rtk git status`, `rtk diff`, `rtk rg <pattern>`, `rtk find <glob>`
