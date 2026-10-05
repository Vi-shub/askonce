# Deploy Askonce to Cloud Run

Contest rule: live URL on Cloud Run or Firebase. This image serves API + UI from one service.

```bash
cd askonce
gcloud run deploy askonce \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_MODEL=gemini-2.5-flash \
  --set-secrets GEMINI_API_KEY=GEMINI_API_KEY:latest
```

Create the secret once:

```bash
echo -n "YOUR_KEY" | gcloud secrets create GEMINI_API_KEY --data-file=-
```

After deploy, paste the HTTPS URL into README and the deck. CORS defaults to `*`; lock it with:

```
--set-env-vars CORS_ORIGINS=https://YOUR-SERVICE.run.app
```

Local production check:

```bash
cd frontend && npm run build
cd ../backend
.\.venv\Scripts\uvicorn app.main:app --port 8080
```

Open http://127.0.0.1:8080
