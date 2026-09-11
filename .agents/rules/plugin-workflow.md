<rule name="plugin-workflow">
  <description>
    Enforces automatic committing, pushing, and syncing of Antigravity plugins.
  </description>

  <constraints>
    - When modifying any Antigravity plugin code or configuration, always commit and push the changes to the remote repository.
    - Always ensure plugins are automatically updated by running `git pull` in the plugin directory before interacting with them.
  </constraints>

  <instructions>
    # Plugin Workflow Rule
    
    1. **Push Code**: Any modifications made to Antigravity plugins (e.g., `attention-guard`) MUST be committed and pushed to the upstream remote repository automatically.
    2. **Automatic Update Plugin**: Proactively run `rtk git pull` within the plugin directories to fetch the latest updates from GitHub before applying new modifications.
  </instructions>
</rule>
