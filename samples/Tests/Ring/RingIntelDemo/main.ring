load "stdlib.ring"
load "libcurl.ring"
load "guilib.ring"
load "shapes.ring"

func main
    see "Hello" + nl
    x = len("abc")
    cPart = substr("Hello World", "World")
    oP = new Point(1, 2)
    oP.moveBy(1, 1)
    oCurl = curl_easy_init()
    oBtn = new QPushButton(NULL)
    nRes = addNums(3, 4)
