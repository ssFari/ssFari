# One-Time Setup

1. **Create a Personal Access Token (classic)**
   - GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token (classic).
   - Scopes: `repo`, `read:user`.
   - Copy the token.

2. **Add it as a repo secret**
   - Repo `ssFari/ssFari` → Settings → Secrets and variables → Actions → New repository secret.
   - Name: `ACCESS_TOKEN`. Value: the token.

3. **Enable workflow write permission**
   - Repo → Settings → Actions → General → Workflow permissions → **Read and write permissions** → Save.

4. **First run**
   - Actions → "Update profile card" → Run workflow.
   - Actions → "Generate snake" → Run workflow.

The card refreshes automatically every 12 hours; the snake daily.
