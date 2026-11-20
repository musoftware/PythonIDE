# RingWebDemo - a web application written in Ring (RingHTTPLib)
# Run (F5 / Ctrl+F5) and open http://localhost:8080 in the browser. Stop with Debug > Stop.

load "httplib.ring"
load "stdlib.ring"

nPort = 8080
aMessages = []

oServer = new Server {
    route(:Get, "/", :pageHome)
    route(:Get, "/api/hello", :apiHello)
    route(:Post, "/messages", :postMessage)
    ? "Listening on http://localhost:" + nPort
    listen("0.0.0.0", nPort)
}

func pageHome
    cHtml = read("templates/index.html")
    cList = ""
    for cMsg in aMessages
        cList += "<li>" + htmlEncode(cMsg) + "</li>"
    next
    cHtml = substr(cHtml, "{messages}", cList)
    oServer.setContent(cHtml, "text/html")

func apiHello
    oServer.setContent('{"message": "Hello from Ring", "count": ' + len(aMessages) + '}', "application/json")

func postMessage
    cText = oServer["text"]            # a form field (oServer.variable("text") does the same)
    if trim(cText) != ""
        aMessages + cText
    ok
    pageHome()

func htmlEncode cText
    cText = substr(cText, "&", "&amp;")
    cText = substr(cText, "<", "&lt;")
    cText = substr(cText, ">", "&gt;")
    return cText
