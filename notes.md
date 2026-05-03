git remote add origin https://github.com/yourusername/llama-config.git
   git branch -M main
   git push -u origin main


add to AGENTS.md
## Git Practices

- Commit after each module is completed and tested
- Use conventional commit messages: `feat:`, `fix:`, `refactor:`, `docs:`
- Never commit to main directly — create a feature branch for each module
- Push to remote after each commit
- Do not commit secrets, API keys, or hardcoded paths
- Always include a .gitignore appropriate for a Python/uv project before first commit
