1. For VCS, use JuJutsu (jj) over Git.
2. Whenever writing new features or editing existing behavior, add unit tests.
3. Following completion of a task that involved changing code, push to Github.
4. Before doing any coding work, create and bookmark a new jujutsu working directory with a name related to the work.
5. Do not track binary files (e.g., databases). If accidentally tracked, use `jj file untrack <path>` (NOT `jj untrack`) and update `.gitignore`.

## Troubleshooting & Best Practices (for Agents)
- **Binary Files**: To stop tracking a file without deleting it, use `jj file untrack <path>`. The command `jj untrack` DOES NOT EXIST.
- **Pushing**: If `jj git push` fails, ensure you are tracking the remote bookmark: `jj bookmark track <name> --remote=origin`.
- **Status**: Run `jj status` frequently to verify your state.
