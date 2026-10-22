# SupriTech frontend security patch — Vite 8.2.4

This isolated branch was created from `feature/partner-multitenancy`. No deploy or production changes are authorized by this document.

## Apply the dependency patch (in a network-enabled checkout)

```bash
git checkout security/vite-8-2-4-supritech
cd frontend
npm install --save-dev vite@8.2.4 --save-exact
npm ci
npm audit --audit-level=high
npm run build
npm run lint
git add package.json package-lock.json
git commit -m "security(frontend): patch Vite to 8.2.4"
git push origin security/vite-8-2-4-supritech
```

Check the complete `npm audit` output and CI results. Do not merge if high/critical vulnerabilities or failing required checks remain. Open a pull request into `feature/partner-multitenancy` only after the lockfile and build are validated. No automatic Render deployment or merge.

Context: `frontend/package-lock.json` currently resolves `vite@8.2.2`. Both manifest and lockfile must be updated together by npm, not by manually editing lockfile integrity hashes.
