# RestClient_Requests

**REST Client** (Tools > REST Client, Ctrl+Alt+K) and `.http` files in the VS Code *REST Client* syntax.

`requests.http`: file variable `@page`, `###` separated requests, `# @name items` + a request variable
(`{{items.response.body.$.items[0]}}`), `{{$guid}}` / `{{$randomInt}}`, JSON body.
`.vscode/settings.json`: environments `local` (`{{host}}` = http://127.0.0.1:3000) and `public-demo`
(https://httpbin.org) - the same file VS Code uses.

**Try it:** open the project, open `requests.http`: each request has a **Send Request** lens - click it (or put
the caret on it and press Ctrl+Alt+K). The answer opens in the REST Client tab (status, time, size, pretty JSON,
headers, raw). Choose *public-demo* in the Env box to hit httpbin.org, or run any local API on port 3000
(e.g. `samples/Tests/Web/ExpressSite_Node`, `/api/notes`). Save, History, Copy as cURL are in the tab.
