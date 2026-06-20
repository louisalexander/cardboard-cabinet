# Deploying Cardboard Cabinet to Cloudflare Pages

The deployed site is fully static — it serves `frontend/` and reads
`frontend/data/games.json` in the browser. There is no backend on Cloudflare.

## Update the collection data

```bash
make export      # fetches your BGG collection -> frontend/data/games.json
```

Commit the regenerated file. Data is only as fresh as your last export.

## Option A — Git integration (recommended)

1. Push this repo to GitHub (already at `origin`).
2. Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** →
   **Connect to Git** → select `cardboard-cabinet`.
3. Build settings:
   - **Framework preset:** None
   - **Build command:** *(leave empty)*
   - **Build output directory:** `frontend`
4. Save and deploy. Every push to `main` auto-deploys.

## Option B — Wrangler CLI

```bash
npx wrangler login                 # one-time
make deploy                        # = wrangler pages deploy frontend
```

The first `deploy` will offer to create the `cardboard-cabinet` Pages project.

## Notes

- The "🔄 Refresh from BGG" button is hidden — refresh is `make export` + redeploy.
- To preview the production build locally: `cd frontend && python3 -m http.server 8787`.
