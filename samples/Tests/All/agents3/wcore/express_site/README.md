# ExpressSite

Node.js Express site (RAD IDE App Gallery).

- `npm install` (done when the project is created), then **F5** in RAD IDE or `npm start`.
- `server.js`: static files from `public/` and a JSON REST API: `GET /api/notes`, `POST /api/notes`
  (`{"text": "..."}`), `DELETE /api/notes/:id`, `GET /api/time`. Notes are saved in `data/notes.json`.
