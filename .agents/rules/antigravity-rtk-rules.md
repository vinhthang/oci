<rule name="antigravity-rtk-rules">
  <description>
    Rust Token Killer (RTK) rules for minimizing token consumption and terminal noise across project shell commands.
  </description>

  <constraints>
    - Always prefix shell commands with `rtk` (or pipe heavy output to `rtk json` / `rtk log`) to minimize token consumption.
  </constraints>

  <instructions>
    # RTK - Rust Token Killer (Project Rule)

    Always prefix shell commands with `rtk` to minimize token consumption.

    - **Maven**: `rtk mvn test`, `rtk mvn clean package`
    - **Kubernetes**: `rtk kubectl get pods`, `rtk kubectl logs`
    - **Cloud & OCI**: `oci <cmd> | rtk json`, `rtk err oci <cmd>`
    - **Docker / Podman**: `rtk docker ps`, `rtk docker logs`
    - **Git & Search**: `rtk git status`, `rtk diff`, `rtk rg <pattern>`, `rtk find <glob>`
  </instructions>
</rule>
