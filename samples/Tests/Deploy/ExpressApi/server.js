// A tiny Express server used to test RAD IDE's Docker generator and the Docker panel.
const express = require("express");
const app = express();
const port = process.env.PORT || 3000;

app.use(express.static("public"));
app.get("/api/health", (req, res) => res.json({ status: "ok", node: process.version }));

app.listen(port, () => console.log(`Express listening on http://localhost:${port}`));
