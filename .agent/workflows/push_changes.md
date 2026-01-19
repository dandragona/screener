---
description: Push local changes to GitHub with Jujutsu
---

// turbo
1. Check the status of the repository.
```bash
jj status
```

2. Describe the changes with a commit message.
```bash
jj describe -m "message"
```

3. Create a bookmark for the current changes.
```bash
jj bookmark create <bookmark_name> -r @
```

// turbo
4. Track the bookmark on the remote repository.
```bash
jj bookmark track <bookmark_name> --remote=origin
```

// turbo
5. Push the bookmark to GitHub.
```bash
jj git push --bookmark <bookmark_name>
```
