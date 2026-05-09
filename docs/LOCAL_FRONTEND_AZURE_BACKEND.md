# Local frontend → Azure dev backend

Goal: run **Next.js frontend locally** while calling the **backend in Azure Container Apps**.

## 1) Set frontend API URL

From repo root:

```bash
cd frontend
echo "NEXT_PUBLIC_API_URL=https://__YOUR_AZURE_BACKEND_FQDN__" > .env.local
```

Example value:

```text
NEXT_PUBLIC_API_URL=https://edgesenseai-backend-dev.<region>.azurecontainerapps.io
```

## 2) Install and run frontend

```bash
cd frontend
npm install
npm run dev
```

## 3) Verify frontend can call backend

- Open the frontend locally.
- Confirm network calls go to the Azure base URL.
- Backend health is also available directly:

```bash
curl -fsS "https://__YOUR_AZURE_BACKEND_FQDN__/health"
```

