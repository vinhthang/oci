<rule name="blog-workflow">
  <description>
    Workflow exception for Hugo blog posts permitting direct commits and pushes to main branch.
  </description>

  <constraints>
    - When creating, editing, or publishing Hugo blog posts in `blog/content/posts/`, MUST commit and push the changes directly to the `main` branch.
    - Do NOT create feature branches or Pull Requests for blog content. This rule explicitly overrides any global branch protection policies for blog-related tasks.
  </constraints>

  <instructions>
    # Blog Workflow Exception

    When creating, editing, or publishing Hugo blog posts in `blog/content/posts/`, you MUST commit and push the changes directly to the `main` branch. 

    Do NOT create feature branches or Pull Requests for blog content. This rule explicitly overrides any global branch protection policies for blog-related tasks.
  </instructions>
</rule>
