# ExpressSite_Node

**node-web (Express)** - Node/Express site with a JSON notes API (data/notes.json) and static front end.

**Try it:** Open, F5 - the IDE runs `npm install` (node_modules was removed) and starts server.js.

*Origin:* agents3 web-gallery (copied from the IDE's test runs, build output removed).

---

# Express Site

Node.js Express site (RAD IDE App Gallery).

- `npm install` (done when the project is created), then **F5** in RAD IDE or `npm start`.
- `server.js`: static files from `public/` and a JSON REST API: `GET /api/notes`, `POST /api/notes`
  (`{"text": "..."}`), `DELETE /api/notes/:id`, `GET /api/time`. Notes are saved in `data/notes.json`.
