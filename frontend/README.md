# Knowledge chatbot frontend

Next.js and React UI for chat sessions, streamed answers, citations, and document management. See the [main README](../README.md) for full setup.

From this directory:

```powershell
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Open http://localhost:3000 for chat and `/admin` for PDF/TXT upload and deletion. `NEXT_PUBLIC_API_URL` controls the backend URL; restart/rebuild after changing it.

Validation and production startup:

```powershell
npm run lint
npm run build
npm run start
```

Authentication is not implemented; admin endpoints and session history are unprotected.
