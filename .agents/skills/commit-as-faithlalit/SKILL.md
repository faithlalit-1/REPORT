---
name: commit-as-faithlalit
description: Safely commit and push Git changes for the faithlalit-1/REPORT repository only. Use whenever the user asks Codex to commit, push, publish, sync, or send changes while working in that repository, including requests such as "commit this", "commit and push", or "push to main". Enforce the repository-local author faithlalit-1 using faith.lalit@gmail.com, reject every other repository or GitHub owner, preserve unrelated changes, and verify the resulting commit and remote branch.
---

# Commit as Faith Lalit

Use this skill only in the GitHub repository `faithlalit-1/REPORT`. Refuse to commit or push if `origin` is missing, is not a recognized GitHub URL, or identifies any other repository.

Use these fixed identity values:

- Git author and committer name: `faithlalit-1`
- Git author and committer email: `faith.lalit@gmail.com`
- GitHub account and expected repository owner: `faithlalit-1`
- Expected GitHub repository: `faithlalit-1/REPORT`

Never store, print, request, or embed passwords, personal access tokens, credential-manager records, or SSH private keys.

## Workflow

1. Inspect before changing anything:
   - Run `git status --short`, `git branch --show-current`, `git remote -v`, and the relevant unstaged/staged diffs.
   - Respect the branch requested by the user. If it differs from the current branch and changing branches may affect uncommitted work, stop and ask for direction.
   - Preserve unrelated user changes. Stage only files belonging to the requested task unless the user explicitly requests a broader scope.

2. Enforce identity before staging or committing:
   - Run `python -X utf8 <skill-directory>/scripts/git_identity_preflight.py` from the target repository.
   - Require the script to confirm `origin` is exactly `faithlalit-1/REPORT` before it updates repository-local identity settings.
   - The script may update only repository-local Git configuration. Never change global or system Git identity.
   - If the script reports a conflicting `GIT_AUTHOR_*` or `GIT_COMMITTER_*` environment override, stop. Do not commit until the override is removed or corrected.
   - Never pass `--author`, `-c user.name`, or `-c user.email` to a commit command.

3. Validate the intended commit:
   - Run `git diff --check` before staging.
   - Stage explicit task-related paths.
   - Run `git diff --cached --check`, review `git diff --cached --name-only`, and inspect the cached diff when needed.
   - If nothing is staged, report that there is nothing to commit.

4. Commit:
   - Use the user's commit message when supplied; otherwise write a concise message describing the staged change.
   - Run a non-interactive `git commit` without identity overrides.
   - Verify the created commit with `git show -s --format="%H%n%an%n%ae%n%cn%n%ce%n%s" HEAD`.
   - Require both author and committer to be exactly `faithlalit-1 <faith.lalit@gmail.com>`. If verification fails, do not push; report the mismatch.

5. Push only when requested:
   - Rerun the same preflight immediately before pushing.
   - Require the `origin` push URL to identify exactly `faithlalit-1/REPORT`. Do not silently rewrite a missing or mismatched remote.
   - If using GitHub CLI for any operation, require `gh api user --jq .login` to return `faithlalit-1`. Do not use another active CLI account.
   - For a normal push, use `git push origin <requested-branch>`. Never force-push unless the user explicitly requests it and the exact overwrite risk has been confirmed.
   - If rejected as non-fast-forward, fetch and inspect before deciding how to reconcile. Never replace remote history automatically.
   - Verify with `git ls-remote origin refs/heads/<branch>` that the remote SHA equals the local commit SHA.

6. Report the outcome:
   - Give the commit SHA and subject, pushed remote/branch when applicable, identity used, and whether the working tree still contains changes.
   - Distinguish remote ownership/credential selection from authenticated actor verification. Do not claim the push actor was API-verified unless an authenticated GitHub API call confirmed `faithlalit-1`.
