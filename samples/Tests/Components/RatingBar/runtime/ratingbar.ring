# RatingBar - ring-qt (RingQt) runtime of the RatingBar component package.
#
# The generated designer does (radide/components/codegen.py ring_control_lines):
#     rate1 = new RatingBar(Form1)
#     rate1.setValue(3)  rate1.setMaxStars(5) ...
#     rate1.radBind("ValueChanged", "rate1_ValueChanged()")
#     rate1.setGeometry(10, 10, 140, 28)
# Use it from code: rate1.setValue(4)   n = rate1.value()   rate1.reset()
#
# Ring copies objects when they are assigned, so the state of every RatingBar lives in the global list
# aRadRatingBar (the object only keeps its row number); copies of the object stay in sync.

aRadRatingBar = []     # [value, max, readonly, starColor, emptyColor, aButtons, aEvents, oFrame, w, h, enabled]

func RadRatingBar_Click nId, nStar
    row = aRadRatingBar[nId]
    if row[3] or not row[11] return ok
    if nStar = row[1] and nStar = 1
        nStar = 0
    ok
    RadRatingBar_Set(nId, nStar)

func RadRatingBar_Set nId, nValue
    nValue = 0 + nValue
    if nValue < 0 nValue = 0 ok
    if nValue > aRadRatingBar[nId][2] nValue = aRadRatingBar[nId][2] ok
    if nValue = aRadRatingBar[nId][1] return ok
    aRadRatingBar[nId][1] = nValue
    RadRatingBar_Draw(nId)
    for ev in aRadRatingBar[nId][7]
        if lower(ev[1]) = "valuechanged"
            eval(ev[2])
        ok
    next

func RadRatingBar_Draw nId
    row = aRadRatingBar[nId]
    nMax = row[2]
    nSize = floor(row[9] / nMax) - 2
    if nSize > row[10] - 2 nSize = row[10] - 2 ok
    if nSize < 6 nSize = 6 ok
    for i = 1 to len(row[6])
        btn = row[6][i]
        if i > nMax
            btn.hide()
            loop
        ok
        if i <= row[1] c = row[4] else c = row[5] ok
        if not row[11]
            if i <= row[1] c = "#B0B0B0" else c = "#E0E0E0" ok
        ok
        btn.setGeometry((i - 1) * (nSize + 2), 0, nSize + 2, row[10])
        btn.setStyleSheet("border:none; background:transparent; color:" + c + "; font-size:" + nSize + "px;")
        btn.show()
    next

class RatingBar
    nId = 0
    oFrame = NULL

    func init oParent
        oFrame = new qFrame(oParent, 0)
        aButtons = []
        aRadRatingBar + [3, 5, false, "#FFB400", "#C8CDD5", [], [], oFrame, 140, 28, true]
        nId = len(aRadRatingBar)
        for i = 1 to 10
            btn = new qPushButton(oFrame)
            btn.setText("★")
            btn.setClickEvent("RadRatingBar_Click(" + nId + ", " + i + ")")
            aButtons + btn
        next
        aRadRatingBar[nId][6] = aButtons
        RadRatingBar_Draw(nId)
        return self

    # ---- properties
    func setValue nValue
        RadRatingBar_Set(nId, nValue)

    func value
        return aRadRatingBar[nId][1]

    func setMaxStars n
        n = 0 + n
        if n < 1 n = 1 ok
        if n > 10 n = 10 ok
        aRadRatingBar[nId][2] = n
        if aRadRatingBar[nId][1] > n aRadRatingBar[nId][1] = n ok
        RadRatingBar_Draw(nId)

    func maxStars
        return aRadRatingBar[nId][2]

    func setReadOnly l
        aRadRatingBar[nId][3] = l

    func setStarColor c
        aRadRatingBar[nId][4] = c
        RadRatingBar_Draw(nId)

    func setEmptyColor c
        aRadRatingBar[nId][5] = c
        RadRatingBar_Draw(nId)

    # ---- methods
    func reset
        RadRatingBar_Set(nId, 0)

    func radBind cEvent, cCode
        aRadRatingBar[nId][7] + [cEvent, cCode]

    # ---- the QWidget methods the form code uses
    func setGeometry x, y, w, h
        oFrame.setGeometry(x, y, w, h)
        aRadRatingBar[nId][9] = w
        aRadRatingBar[nId][10] = h
        RadRatingBar_Draw(nId)

    func setEnabled l
        aRadRatingBar[nId][11] = l
        oFrame.setEnabled(l)
        RadRatingBar_Draw(nId)

    func show
        oFrame.show()

    func hide
        oFrame.hide()

    func raise
        oFrame.raise()

    func setToolTip t
        oFrame.setToolTip(t)

    func width
        return oFrame.width()

    func height
        return oFrame.height()
