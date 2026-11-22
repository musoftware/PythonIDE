# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# RingGuestbook - a web application in Ring (RingHTTPLib) with an SQLite database.
# Shows: routes (GET / POST), an HTML form, a page template, HTML escaping, a JSON API, SQLite storage,
# server-side validation and a redirect after POST.
# Run: F5 / Ctrl+F5, then open http://localhost:8080 (another port: set the PORT environment variable).

load "httplib.ring"
load "sqlitelib.ring"
load "stdlib.ring"

nPort = 8080
if sysget("PORT") != "" nPort = number(sysget("PORT")) ok

oDB = sqlite_init()
sqlite_open(oDB, "guestbook.db")
sqlite_execute(oDB, "create table if not exists entries (id integer primary key autoincrement, " +
                    "name text not null, message text not null, created text)")

oServer = new Server {
    route(:Get, "/", :pageHome)
    route(:Post, "/sign", :postSign)
    route(:Get, "/api/entries", :apiEntries)
    route(:Get, "/about", :pageAbout)
    ? "Guestbook listening on http://localhost:" + nPort
    listen("0.0.0.0", nPort)
}

# ---------------------------------------------------------------- pages
func pageHome
    ShowHome("")

func ShowHome cError
    cList = ""
    aRows = sqlite_execute(oDB, "select name, message, created from entries order by id desc limit 50")
    for aRow in aRows
        cList += "<li><b>" + Html(aRow[:name]) + "</b> <small>" + Html(aRow[:created]) + "</small><br>" +
                 Html(aRow[:message]) + "</li>" + nl
    next
    if cList = "" cList = "<li class='empty'>No entries yet - be the first! / لا توجد رسائل بعد</li>" ok
    cHtml = read("templates/index.html")
    cHtml = substr(cHtml, "{entries}", cList)
    cHtml = substr(cHtml, "{count}", "" + len(aRows))
    cErrorHtml = ""
    if cError != "" cErrorHtml = "<p class='error'>" + Html(cError) + "</p>" ok
    cHtml = substr(cHtml, "{error}", cErrorHtml)
    oServer.setContent(cHtml, "text/html; charset=utf-8")

func postSign
    cName = trim(oServer["name"])
    cMessage = trim(oServer["message"])
    if cName = "" or cMessage = ""
        ShowHome("Please write your name and a message.")
        return
    ok
    if len(cMessage) > 500 cMessage = left(cMessage, 500) ok
    sqlite_execute(oDB, "insert into entries (name, message, created) values (" + Sql(cName) + ", " +
                        Sql(cMessage) + ", " + Sql(date() + " " + time()) + ")")
    oServer.response().set_header("Location", "/")     # Post/Redirect/Get: a refresh does not post again
    oServer.setStatus(303)
    oServer.setContent("", "text/plain")

func apiEntries
    aRows = sqlite_execute(oDB, "select id, name, message, created from entries order by id")
    cJson = "["
    for i = 1 to len(aRows)
        if i > 1 cJson += "," ok
        cJson += '{"id": ' + aRows[i][:id] + ', "name": ' + Json(aRows[i][:name]) + ', "message": ' +
                 Json(aRows[i][:message]) + ', "created": ' + Json(aRows[i][:created]) + '}'
    next
    oServer.setContent(cJson + "]", "application/json; charset=utf-8")

func pageAbout
    oServer.setContent("<!doctype html><meta charset='utf-8'><title>About</title>" +
                       "<p>RingGuestbook - a RAD IDE example. (c) 2026 Musoftware - https://musoftwares.com</p>" +
                       "<p><a href='/'>Back</a></p>", "text/html; charset=utf-8")

# ---------------------------------------------------------------- helpers
func Html cText
    cText = substr(cText, "&", "&amp;")
    cText = substr(cText, "<", "&lt;")
    cText = substr(cText, ">", "&gt;")
    cText = substr(cText, '"', "&quot;")
    return cText

func Sql cText
    return "'" + substr(cText, "'", "''") + "'"

func Json cText
    cText = substr(cText, "\", "\\")
    cText = substr(cText, '"', '\"')
    cText = substr(cText, nl, "\n")
    cText = substr(cText, char(13), "")
    return '"' + cText + '"'
