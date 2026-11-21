"""Builds the Flutter designer template gallery (radide/flutterdesign/templates/screens/*.fscreen.json + index.json).

    python -m radide.flutterdesign.templates.build_templates

All nine designs are original to RAD IDE. Images are the programmatic artwork of ``art.py`` (assets/), fonts come
from Google Fonts (SIL Open Font License) through ``google_fonts`` or, offline, ``fonts.add_to_project``.
Screens use handler events (stubs in the user file) and ``back``, so a template works on its own in any project.
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import animations as AN
from .. import model as M

HERE = Path(__file__).resolve().parent
IMG = "assets/images/"


# ------------------------------------------------------------------------------------------ helpers
def N(type_: str, props: dict | None = None, *, ctor=None, name=None, anim=None, events=None, children=None,
      **slots) -> dict:
    n: dict = {"type": type_}
    if ctor:
        n["ctor"] = ctor
    if name:
        n["name"] = name
    if props:
        n["props"] = props
    sl = {k: v for k, v in slots.items() if v is not None}
    if sl:
        n["slots"] = sl
    if children is not None:
        n["children"] = children
    if events:
        n["events"] = events
    if anim:
        n["anim"] = anim
    return n


def A(preset: str, delay: int = 0, duration: int | None = None) -> dict:
    return AN.make_anim(preset, delay, duration)


def style(size=None, weight=None, color=None, font=None, **kw) -> dict:
    s = {}
    if color:
        s["color"] = color
    if size:
        s["fontSize"] = size
    if weight:
        s["fontWeight"] = f"FontWeight.{weight}"
    if font:
        s["googleFont"] = font
    s.update(kw)
    return s


def T(text: str, size=14, weight=None, color=None, font=None, align=None, anim=None, **kw) -> dict:
    p = {"data": text, "style": style(size, weight, color, font, **{k: v for k, v in kw.items()
                                                                     if k in ("height", "letterSpacing")})}
    if align:
        p["textAlign"] = f"TextAlign.{align}"
    for k in ("maxLines", "overflow"):
        if k in kw:
            p[k] = kw[k]
    return N("Text", p, anim=anim)


def gap(h=None, w=None) -> dict:
    p = {}
    if h is not None:
        p["height"] = h
    if w is not None:
        p["width"] = w
    return N("SizedBox", p)


def pad(child: dict, anim=None, **edge) -> dict:
    return N("Padding", {"padding": edge}, child=child, anim=anim)


def icon(name: str, color=None, size=None) -> dict:
    p = {"icon": f"Icons.{name}"}
    if color:
        p["color"] = color
    if size:
        p["size"] = size
    return N("Icon", p)


def col(children, cross=None, main=None, size=None, anim=None, spacing=None) -> dict:
    p = {}
    if cross:
        p["crossAxisAlignment"] = f"CrossAxisAlignment.{cross}"
    if main:
        p["mainAxisAlignment"] = f"MainAxisAlignment.{main}"
    if size:
        p["mainAxisSize"] = f"MainAxisSize.{size}"
    if spacing:
        p["spacing"] = spacing
    return N("Column", p, children=children, anim=anim)


def row(children, cross=None, main=None, size=None, anim=None, spacing=None) -> dict:
    n = col(children, cross, main, size, anim, spacing)
    n["type"] = "Row"
    return n


def box(child=None, *, w=None, h=None, color=None, radius=None, gradient=None, shadow=None, border=None,
        image=None, circle=False, padding=None, margin=None, align=None, constraints=None, anim=None) -> dict:
    p: dict = {}
    if w is not None:
        p["width"] = w
    if h is not None:
        p["height"] = h
    if padding:
        p["padding"] = padding
    if margin:
        p["margin"] = margin
    if align:
        p["alignment"] = f"Alignment.{align}"
    if constraints:
        p["constraints"] = constraints
    d: dict = {}
    if color:
        d["color"] = color
    if gradient:
        d["gradient"] = gradient
    if image:
        d["image"] = {"source": "asset", "src": IMG + image, "fit": "BoxFit.cover"}
    if radius is not None:
        d["borderRadius"] = radius
    if border:
        d["border"] = border
    if shadow:
        d["boxShadow"] = shadow
    if circle:
        d["shape"] = "BoxShape.circle"
    if d:
        p["decoration"] = d
    return N("Container", p, child=child, anim=anim)


def lin(c1, c2, begin="topLeft", end="bottomRight") -> dict:
    return {"type": "linear", "begin": f"Alignment.{begin}", "end": f"Alignment.{end}", "colors": [c1, c2]}


def shadow(color, blur=20, dy=10, spread=0) -> list:
    s = {"color": color, "blur": blur, "offset": [0, dy]}
    if spread:
        s["spread"] = spread
    return [s]


def image(file: str, **p) -> dict:
    return N("Image", {"src": IMG + file, **p}, ctor="asset")


def avatar(file: str, r: float, anim=None) -> dict:
    return N("CircleAvatar", {"radius": r, "backgroundImage": {"source": "asset", "src": IMG + file}}, anim=anim)


def screen(sid: str, name: str, route: str, title: str, category: str, description: str, fonts: list[str],
           tree: dict) -> dict:
    scr = M.Screen.new(name, route)
    scr.data["fonts"] = [{"family": f, "source": "google"} for f in fonts]
    scr.tree = json.loads(json.dumps(tree))      # no shared sub-dicts
    scr.assign_ids(scr.tree)
    found = []
    for n, *_ in scr.walk():
        s = json.dumps(n.get("props") or {})
        for part in s.split('"'):
            if part.startswith(IMG) and part not in found:
                found.append(part)
    scr.data["assets"] = found
    errs = [str(i) for i in scr.validate() if i.level == "error"]
    if errs:
        raise ValueError(f"{name}: {errs}")
    return {"id": sid, "title": title, "category": category, "description": description, "screen": scr}


# ----------------------------------------------------------------------------------------- designs
def login() -> dict:
    F = "Poppins"
    P, P2, INK, MUTED = "#FF5B5FD9", "#FF9D6BF2", "#FF23233A", "#FF8E8FA6"
    line = "#FFEDEEF7"

    def field(name, hint, ico, obscure=False, suffix=None):
        dec = {"hintText": hint, "prefixIcon": f"Icons.{ico}", "border": "none",
               "contentPadding": {"h": 16, "v": 18}, "hintStyle": style(14, color=MUTED, font=F)}
        if suffix:
            dec["suffixIcon"] = f"Icons.{suffix}"
        p = {"decoration": dec, "style": style(15, color=INK, font=F)}
        if obscure:
            p["obscureText"] = True
        return N("TextField", p, name=name)

    social = {"foregroundColor": INK, "padding": {"v": 14},
              "shape": {"type": "rounded", "radius": 14, "side": {"color": "#FFE3E4EE", "width": 1}}}
    header = box(
        N("SafeArea", child=pad(col([
            icon("auto_awesome", "Colors.white", 34) | {"anim": A("fade_down", 100)},
            gap(18),
            T("Hello again!", 34, "w700", "Colors.white", F, anim=A("fade_up", 250)),
            gap(6),
            T("Welcome back, you've been missed.", 15, None, "#DDFFFFFF", F, anim=A("fade_up", 400)),
        ], cross="start"), all=28)),
        h=300, image="login_waves.png")
    form = pad(col([
        gap(8),
        box(col([field("txtEmail", "Email address", "alternate_email"),
                 N("Divider", {"height": 1, "color": line}),
                 field("txtPassword", "Password", "lock_outline", True, "visibility_off_outlined")]),
            color="Colors.white", radius=18, border={"color": line, "width": 1},
            shadow=shadow("#265B5FD9", 30, 12), anim=A("fade_up", 550)),
        N("Align", {"alignment": "Alignment.centerRight"},
          child=N("TextButton", child=T("Forgot password?", 13, "w500", P, F),
                  events={"onPressed": "onForgotPassword"}), anim=A("fade", 650)),
        gap(8),
        N("InkWell", {"borderRadius": 16}, events={"onTap": "onLogin"}, anim=A("fade_up", 750),
          child=box(T("Sign in", 17, "w600", "Colors.white", F), h=56, align="center", radius=16,
                    gradient=lin(P, P2, "centerLeft", "centerRight"), shadow=shadow("#405B5FD9", 20, 10))),
        gap(28),
        row([N("Expanded", child=N("Divider", {"color": "#FFE3E4EE"})),
             pad(T("or continue with", 13, None, MUTED, F), h=12),
             N("Expanded", child=N("Divider", {"color": "#FFE3E4EE"}))], anim=A("fade", 850)),
        gap(20),
        row([N("Expanded", child=N("OutlinedButton", {"style": social}, ctor="icon",
                                   icon=icon("phone_iphone"), label=T("Phone", 14, "w500", None, F),
                                   events={"onPressed": "onPhoneLogin"})),
             N("Expanded", child=N("OutlinedButton", {"style": social}, ctor="icon",
                                   icon=icon("mail_outline"), label=T("Email link", 14, "w500", None, F),
                                   events={"onPressed": "onEmailLink"}))],
            spacing=14, anim=A("fade_up", 950)),
        gap(28),
        row([T("New here?", 14, None, MUTED, F),
             N("TextButton", child=T("Create an account", 14, "w600", P, F), events={"onPressed": "onSignUp"})],
            main="center", anim=A("fade", 1050)),
        gap(24),
    ], cross="stretch"), h=28)
    tree = N("Scaffold", {"backgroundColor": "Colors.white"},
             body=N("SingleChildScrollView", child=col([header, form], cross="stretch")))
    return screen("login", "Login", "/login", "Login", "Authentication",
                  "Wave header artwork, a shadowed input card, gradient sign-in button, social row and "
                  "staggered fade-in animations.", [F], tree)


def signup() -> dict:
    F = "Nunito"
    V, INK, MUTED = "#FF8B5CF6", "#FF1F1B2E", "#FF8C8798"

    def field(name, label, ico, obscure=False, kb=None):
        p = {"decoration": {"labelText": label, "prefixIcon": f"Icons.{ico}", "border": "outline",
                            "borderRadius": 14, "borderColor": "#FFE6E1F5", "focusedBorderColor": V,
                            "filled": True, "fillColor": "#FFFAF8FF", "contentPadding": {"h": 16, "v": 16},
                            "labelStyle": style(14, color=MUTED, font=F)},
             "style": style(15, color=INK, font=F)}
        if obscure:
            p["obscureText"] = True
        if kb:
            p["keyboardType"] = f"TextInputType.{kb}"
        return N("TextField", p, name=name)

    sheet = box(N("SingleChildScrollView", child=col([
        field("txtName", "Full name", "person_outline", kb="name") | {"anim": A("fade_up", 300)},
        gap(14),
        field("txtEmail", "Email", "mail_outline", kb="emailAddress") | {"anim": A("fade_up", 380)},
        gap(14),
        field("txtPassword", "Password", "lock_outline", True) | {"anim": A("fade_up", 460)},
        gap(10),
        row([N("Checkbox", {"value": False, "activeColor": V}, name="chkTerms"),
             N("Expanded", child=T("I agree to the Terms of Service and the Privacy Policy", 13, None, MUTED,
                                   F))], anim=A("fade", 540)),
        gap(18),
        N("ElevatedButton", {"style": {"backgroundColor": V, "foregroundColor": "Colors.white",
                                       "padding": {"v": 16}, "elevation": 0,
                                       "shape": {"type": "rounded", "radius": 16}}},
          child=T("Sign up", 16, "w700", None, F), events={"onPressed": "onSignUp"}, anim=A("fade_up", 620)),
        gap(18),
        row([T("Already have an account?", 14, None, MUTED, F),
             N("TextButton", child=T("Log in", 14, "w700", V, F), events={"onPressed": "back"})],
            main="center", anim=A("fade", 700)),
    ], cross="stretch")), color="Colors.white", radius={"tl": 36, "tr": 36}, padding={"all": 28},
        margin={"t": 24})
    body = box(N("Stack", children=[
        N("Positioned", {"top": -80, "right": -140, "width": 440, "height": 440},
          child=image("signup_blobs.png", fit="BoxFit.contain"), anim=A("zoom", 0, 1200)),
        N("SafeArea", {"bottom": False}, child=col([
            pad(N("Align", {"alignment": "Alignment.centerLeft"},
                  child=N("IconButton", {"color": "Colors.white"}, icon=icon("arrow_back_ios_new"),
                          events={"onPressed": "back"})), all=8),
            pad(col([T("Create account", 32, "w800", "Colors.white", F, anim=A("fade_up", 100)),
                     gap(6),
                     T("Join and start designing in minutes.", 15, None, "#E6FFFFFF", F,
                       anim=A("fade_up", 200))], cross="start"), l=28, t=8, r=28),
            N("Expanded", child=sheet),
        ], cross="stretch")),
    ]), gradient=lin("#FFFF6A88", V))
    tree = N("Scaffold", {"resizeToAvoidBottomInset": True}, body=body)
    return screen("signup", "SignUp", "/signup", "Sign up", "Authentication",
                  "Full-screen gradient with translucent blobs, a rounded white sheet with outlined fields, a "
                  "terms checkbox and a solid call to action.", [F], tree)


def onboarding() -> dict:
    F = "Outfit"
    INK, MUTED, ACC = "#FF1E1B2E", "#FF7D7A8C", "#FFFF6B8A"
    pages = [("onboarding_1.png", "Stay in the loop", "Everything your team shares, gathered in one calm feed."),
             ("onboarding_2.png", "See your progress", "Simple charts show how far you have come each week."),
             ("onboarding_3.png", "Explore further", "Discover new spaces and people who build like you do.")]
    kids = []
    for i, (img, title, body) in enumerate(pages):
        kids.append(pad(col([
            image(img, height=300, fit="BoxFit.contain") | {"anim": A("zoom" if i == 0 else "scale", 0, 700)},
            gap(40),
            T(title, 28, "w700", INK, F, align="center", anim=A("fade_up", 200)),
            gap(14),
            T(body, 15, None, MUTED, F, align="center", height=1.5, anim=A("fade_up", 320)),
        ], main="center"), h=32))

    def dot(active):
        return box(w=26 if active else 8, h=8, color=ACC if active else "#FFE9DDE3", radius=4)

    tree = N("Scaffold", {"backgroundColor": "#FFFDFBF7"}, body=N("SafeArea", child=col([
        N("Align", {"alignment": "Alignment.centerRight"},
          child=pad(N("TextButton", child=T("Skip", 15, "w500", MUTED, F), events={"onPressed": "onSkip"}),
                    h=12, v=4)),
        N("Expanded", child=N("PageView", children=kids, events={"onPageChanged": "onPageChanged"})),
        pad(row([row([dot(True), dot(False), dot(False)], spacing=8),
                 N("InkWell", {"borderRadius": 32}, events={"onTap": "onNext"},
                   child=box(icon("arrow_forward_rounded", "Colors.white", 28), w=64, h=64, circle=True,
                             align="center", gradient=lin(ACC, "#FFFFB86B"), shadow=shadow("#55FF6B8A", 18, 8)))],
                main="spaceBetween"), h=32, v=28, anim=A("fade_up", 400)),
    ])))
    return screen("onboarding", "Onboarding", "/onboarding", "Onboarding", "Onboarding",
                  "Three swipeable pages with original illustrations, page dots and a round gradient next "
                  "button.", [F], tree)


def profile() -> dict:
    F = "Poppins"
    INK, MUTED, P = "#FF1F2333", "#FF8A8FA3", "#FF6A82FB"

    def stat(v, label):
        return col([T(v, 18, "w700", INK, F), gap(2), T(label, 12, None, MUTED, F)], size="min")

    def sep():
        return box(w=1, h=32, color="#FFE8EAF2")
    tiles = []
    grads = [("#FFFF9A8B", "#FFFF6A88"), ("#FF6A82FB", "#FFFC5C7D"), ("#FF43E97B", "#FF38F9D7"),
             ("#FFFA709A", "#FFFEE140"), ("#FF30CFD0", "#FF330867"), ("#FFA18CD1", "#FFFBC2EB")]
    icons_ = ["palette_outlined", "photo_camera_outlined", "eco_outlined", "wb_sunny_outlined", "nightlight_round",
              "favorite_border"]
    for i, ((c1, c2), ic) in enumerate(zip(grads, icons_)):
        tiles.append(box(icon(ic, "#E6FFFFFF", 30), radius=16, gradient=lin(c1, c2), align="center",
                         anim=A("scale", 600 + i * 70)))
    header = N("Stack", {"clipBehavior": "Clip.none", "alignment": "Alignment.topCenter"}, children=[
        box(h=220, image="profile_cover.png", radius={"bl": 32, "br": 32}),
        N("Positioned", {"top": 0, "left": 0, "right": 0}, child=N("SafeArea", child=pad(row([
            N("IconButton", {"color": "Colors.white"}, icon=icon("arrow_back_ios_new"), events={"onPressed": "back"}),
            N("IconButton", {"color": "Colors.white"}, icon=icon("more_horiz"), events={"onPressed": "onMore"}),
        ], main="spaceBetween"), h=8))),
        N("Positioned", {"left": 0, "right": 0, "bottom": -56}, child=N("Center", child=box(
            avatar("avatar_2.png", 54), padding={"all": 4}, color="Colors.white", circle=True,
            shadow=shadow("#33000000", 16, 6))), anim=A("zoom", 200, 600)),
    ])
    body = col([
        header,
        gap(68),
        T("Maya Collins", 22, "w700", INK, F, anim=A("fade_up", 300)),
        T("Product designer · Lisbon", 14, None, MUTED, F, anim=A("fade_up", 380)),
        gap(20),
        pad(box(row([stat("128", "Posts"), sep(), stat("12.4k", "Followers"), sep(), stat("312", "Following")],
                    main="spaceEvenly"), color="Colors.white", radius=20, padding={"v": 18},
                shadow=shadow("#0F1F2333", 24, 8)), h=24, anim=A("fade_up", 460)),
        gap(18),
        pad(row([N("Expanded", child=N("FilledButton", {"style": {"backgroundColor": P, "padding": {"v": 14},
                                                                  "shape": {"type": "rounded", "radius": 14}}},
                                       child=T("Follow", 15, "w600", None, F), events={"onPressed": "onFollow"})),
                 N("Expanded", child=N("OutlinedButton", {"style": {"foregroundColor": INK, "padding": {"v": 14},
                                                                    "shape": {"type": "rounded", "radius": 14,
                                                                              "side": {"color": "#FFDADDE8"}}}},
                                       child=T("Message", 15, "w600", None, F),
                                       events={"onPressed": "onMessage"}))], spacing=12),
            h=24, anim=A("fade_up", 540)),
        gap(22),
        pad(row([T("Recent work", 17, "w600", INK, F),
                 N("TextButton", child=T("See all", 13, "w500", P, F), events={"onPressed": "onSeeAll"})],
                main="spaceBetween"), h=24),
        pad(N("GridView", {"crossAxisCount": 3, "shrinkWrap": True, "physics": "NeverScrollableScrollPhysics",
                           "mainAxisSpacing": 10, "crossAxisSpacing": 10}, ctor="count", children=tiles),
            l=24, r=24, b=24),
    ])
    tree = N("Scaffold", {"backgroundColor": "#FFF6F7FB"}, body=N("SingleChildScrollView", child=body))
    return screen("profile", "Profile", "/profile", "Profile", "Social",
                  "Cover artwork with an overlapping avatar, stats card, follow / message buttons and a gradient "
                  "grid of recent work.", [F], tree)


def dashboard() -> dict:
    F = "Manrope"
    INK, MUTED, P, P2 = "#FF1B1F3B", "#FF8B90A7", "#FF3D5AFE", "#FF7C4DFF"
    card_shadow = shadow("#0D1B1F3B", 20, 6)

    def action(ic, label, color, i):
        return col([box(icon(ic, color, 26), w=58, h=58, color="Colors.white", radius=18, align="center",
                        shadow=card_shadow),
                    gap(8), T(label, 12, "w600", INK, F)], size="min", anim=A("fade_up", 250 + i * 80))

    bars = [("M", 60), ("T", 95), ("W", 70), ("T", 120), ("F", 85), ("S", 40), ("S", 55)]
    bar_kids = []
    for i, (d, h) in enumerate(bars):
        hl = i == 3
        bar_kids.append(col([
            box(w=26, h=h, radius=8, gradient=lin(P2, P, "topCenter", "bottomCenter") if hl else None,
                color=None if hl else "#FFE6E9F8"),
            gap(8), T(d, 11, "w600" if hl else None, INK if hl else MUTED, F)], main="end"))

    def tx(ic, tint, bg, title, sub, amount, positive, i):
        return box(N("ListTile", {"contentPadding": {"h": 14, "v": 4}},
                     leading=box(icon(ic, tint, 22), w=44, h=44, color=bg, radius=14, align="center"),
                     title=T(title, 15, "w700", INK, F), subtitle=T(sub, 12, None, MUTED, F),
                     trailing=T(amount, 15, "w700", "#FF16A34A" if positive else INK, F),
                     events={"onTap": "onTransaction"}),
                   color="Colors.white", radius=18, margin={"b": 10}, anim=A("fade_up", 700 + i * 90))

    body = N("SafeArea", child=N("SingleChildScrollView", {"padding": {"all": 20}}, child=col([
        row([avatar("avatar_1.png", 22), gap(w=12),
             N("Expanded", child=col([T("Good morning", 13, None, MUTED, F), T("Jordan Lee", 18, "w800", INK, F)],
                                     cross="start")),
             box(N("IconButton", icon=icon("notifications_none_rounded", INK), events={"onPressed": "onNotifications"}),
                 color="Colors.white", circle=True, shadow=card_shadow)], anim=A("fade_down", 0)),
        gap(22),
        box(col([
            row([T("Total balance", 14, None, "#CCFFFFFF", F), icon("more_horiz", "Colors.white")],
                main="spaceBetween"),
            gap(10),
            T("$24,562.80", 32, "w800", "Colors.white", F),
            gap(16),
            box(row([icon("trending_up", "Colors.white", 16), gap(w=4),
                     T("+3.2% this month", 12, "w600", "Colors.white", F)], size="min"),
                color="#33FFFFFF", radius=20, padding={"h": 10, "v": 6}),
        ], cross="start"), padding={"all": 22}, radius=24, gradient=lin(P, P2), shadow=shadow("#553D5AFE", 24, 12),
            anim=A("fade_up", 120)),
        gap(22),
        row([action("north_east_rounded", "Send", P, 0), action("south_west_rounded", "Request", "#FF16A34A", 1),
             action("add_card_outlined", "Top up", "#FFF59E0B", 2), action("grid_view_rounded", "More", P2, 3)],
            main="spaceBetween"),
        gap(24),
        box(col([
            row([T("Weekly activity", 16, "w800", INK, F), T("This week", 12, None, MUTED, F)], main="spaceBetween"),
            gap(18),
            N("SizedBox", {"height": 150}, child=row(bar_kids, cross="end", main="spaceBetween")),
        ], cross="start"), color="Colors.white", radius=22, padding={"all": 20}, shadow=card_shadow,
            anim=A("fade_up", 600)),
        gap(24),
        row([T("Recent transactions", 16, "w800", INK, F),
             N("TextButton", child=T("See all", 13, "w600", P, F), events={"onPressed": "onSeeAll"})],
            main="spaceBetween"),
        tx("shopping_bag_outlined", "#FFF97316", "#FFFFF1E7", "Corner market", "Today, 09:24", "-$32.40", False, 0),
        tx("work_outline", "#FF16A34A", "#FFE8F8EE", "Salary", "Yesterday", "+$3,200.00", True, 1),
        tx("local_cafe_outlined", "#FF7C4DFF", "#FFF1ECFF", "Morning coffee", "Mon, 08:10", "-$4.80", False, 2),
    ], cross="stretch")))
    tree = N("Scaffold", {"backgroundColor": "#FFF4F6FA"}, body=body, bottomNavigationBar=N(
        "BottomNavigationBar", {"type": "BottomNavigationBarType.fixed", "selectedItemColor": P,
                                "unselectedItemColor": "#FFA3A8BF", "backgroundColor": "Colors.white",
                                "items": [{"icon": "Icons.home_rounded", "label": "Home"},
                                          {"icon": "Icons.bar_chart_rounded", "label": "Stats"},
                                          {"icon": "Icons.credit_card_rounded", "label": "Cards"},
                                          {"icon": "Icons.person_outline_rounded", "label": "Profile"}]},
        name="navMain"))
    return screen("dashboard", "Dashboard", "/dashboard", "Dashboard", "Finance",
                  "Greeting header, gradient balance card, quick actions, a bar chart built from containers and "
                  "recent transactions with a bottom navigation bar.", [F], tree)


def shop() -> dict:
    F = "DM Sans"
    INK, MUTED, BG, ORANGE = "#FF2D3142", "#FF9095A5", "#FFF7F5F2", "#FFEF8354"
    products = [("product_headphones.png", "Aura Wireless", "Audio", "$249", "#FFFCE8DD"),
                ("product_watch.png", "Mono Watch", "Wearables", "$189", "#FFE5ECF6"),
                ("product_speaker.png", "Pulse Speaker", "Audio", "$129", "#FFE1EEF8"),
                ("product_plant.png", "Desk Fern", "Home", "$39", "#FFE4F3EA")]
    cards = []
    for i, (img, name, cat, price, tint) in enumerate(products):
        cards.append(N("GestureDetector", events={"onTap": "onOpenProduct"}, anim=A("scale", 500 + i * 90),
                       child=box(col([
                           N("Expanded", child=N("Stack", children=[
                               N("Positioned", ctor="fill",
                                 child=box(image(img, fit="BoxFit.contain"), color=tint, radius=16,
                                           padding={"all": 12})),
                               N("Positioned", {"top": 8, "right": 8},
                                 child=box(icon("favorite_border", INK, 18), w=32, h=32, circle=True,
                                           color="Colors.white", align="center")),
                           ])),
                           gap(10),
                           T(name, 15, "w700", INK, F),
                           gap(2),
                           T(cat, 12, None, MUTED, F),
                           gap(6),
                           row([T(price, 16, "w800", INK, F),
                                box(icon("add", "Colors.white", 18), w=30, h=30, radius=10, color=INK,
                                    align="center")], main="spaceBetween"),
                       ], cross="start"), color="Colors.white", radius=22, padding={"all": 12})))
    chips = []
    for i, c in enumerate(["All", "Audio", "Wearables", "Home", "Plants"]):
        sel = i == 0
        chips.append(box(T(c, 14, "w600", "Colors.white" if sel else INK, F), padding={"h": 18, "v": 10},
                         radius=20, color=INK if sel else "Colors.white", margin={"r": 10}, align="center",
                         anim=A("fade_left", 300 + i * 60)))
    body = N("ListView", {"padding": {"h": 20}}, children=[
        gap(8),
        row([N("Expanded", child=N("TextField", {"decoration": {
                "hintText": "Search products", "prefixIcon": "Icons.search", "border": "outline", "borderRadius": 16,
                "borderColor": "Colors.white", "focusedBorderColor": ORANGE, "filled": True,
                "fillColor": "Colors.white", "contentPadding": {"v": 14}, "hintStyle": style(14, color=MUTED, font=F)}},
                name="txtSearch")),
             box(icon("tune", "Colors.white"), w=52, h=52, radius=16, color=INK, align="center")],
            spacing=12, anim=A("fade_up", 100)),
        gap(20),
        box(row([
            N("Expanded", child=col([
                T("Summer drop", 20, "w700", "Colors.white", F), gap(6),
                T("Up to 40% off audio", 13, None, "#E6FFFFFF", F), gap(12),
                box(T("Shop now", 12, "w700", ORANGE, F), color="Colors.white", radius=20,
                    padding={"h": 14, "v": 8}),
            ], cross="start", main="center")),
            image("product_headphones.png", width=120, fit="BoxFit.contain"),
        ]), h=150, radius=22, padding={"all": 20}, gradient=lin(ORANGE, "#FFF7B267"),
            shadow=shadow("#40EF8354", 20, 10), anim=A("fade_up", 200)),
        gap(22),
        N("SizedBox", {"height": 42}, child=N("ListView", {"scrollDirection": "Axis.horizontal"}, children=chips)),
        gap(18),
        N("GridView", {"crossAxisCount": 2, "shrinkWrap": True, "physics": "NeverScrollableScrollPhysics",
                       "mainAxisSpacing": 16, "crossAxisSpacing": 16, "childAspectRatio": 0.68}, ctor="count",
          children=cards),
        gap(24),
    ])
    tree = N("Scaffold", {"backgroundColor": BG},
             appBar=N("AppBar", {"backgroundColor": BG, "elevation": 0, "centerTitle": False},
                      title=T("Discover", 24, "w700", INK, F),
                      actions=[N("IconButton", icon=icon("shopping_bag_outlined", INK),
                                 events={"onPressed": "onCart"}), gap(w=8)]),
             body=body,
             bottomNavigationBar=N("BottomNavigationBar", {
                 "type": "BottomNavigationBarType.fixed", "selectedItemColor": INK, "unselectedItemColor": MUTED,
                 "backgroundColor": "Colors.white", "showUnselectedLabels": False,
                 "items": [{"icon": "Icons.storefront_outlined", "label": "Shop"},
                           {"icon": "Icons.favorite_border", "label": "Saved"},
                           {"icon": "Icons.receipt_long_outlined", "label": "Orders"},
                           {"icon": "Icons.person_outline", "label": "Me"}]}, name="navShop"))
    return screen("shop", "Shop", "/shop", "Product list", "Shopping",
                  "Search field, promo banner, horizontal category chips and a two-column product grid with "
                  "original product artwork.", [F], tree)


def product() -> dict:
    F = "DM Sans"
    INK, MUTED, ORANGE, TINT = "#FF2D3142", "#FF8C90A0", "#FFEF8354", "#FFFCE8DD"

    def round_btn(ic, ev):
        return box(N("IconButton", icon=icon(ic, INK), events={"onPressed": ev}), color="Colors.white",
                   circle=True, shadow=shadow("#14000000", 12, 4))

    def dot(color, sel=False):
        return box(w=34, h=34, circle=True, color=color,
                   border={"color": "Colors.white" if sel else "#00FFFFFF", "width": 3},
                   shadow=shadow("#552D3142", 0, 0, 2) if sel else None)

    stars = [icon("star_rounded", "#FFFFB020", 20) for _ in range(4)] + [icon("star_half_rounded", "#FFFFB020", 20)]
    top = N("Stack", children=[
        N("Positioned", ctor="fill", child=box(gradient={"type": "radial", "center": "Alignment.center",
                                                         "radius": 0.8, "colors": ["#FFFFFFFF", TINT]})),
        N("Positioned", {"left": 40, "right": 40, "top": 80, "bottom": 10},
          child=N("Hero", {"tag": "product-aura"}, child=image("product_headphones.png", fit="BoxFit.contain")),
          anim=A("zoom", 100, 700)),
        N("Positioned", {"top": 0, "left": 0, "right": 0}, child=N("SafeArea", child=pad(row([
            round_btn("arrow_back_ios_new", "back"), round_btn("favorite_border", "onFavorite")],
            main="spaceBetween"), h=16, v=8))),
    ])
    sheet = box(col([
        row([N("Expanded", child=col([T("Aura Wireless", 24, "w800", INK, F), gap(6),
                                      row(stars + [gap(w=6), T("4.6 (1.2k reviews)", 12, None, MUTED, F)])],
                                     cross="start")),
             T("$249", 24, "w800", ORANGE, F)], cross="start", anim=A("fade_up", 200)),
        gap(16),
        T("Soft memory-foam cushions, forty hours of battery and a calm, balanced sound. Folds flat and "
          "charges fully in under two hours.", 14, None, MUTED, F, height=1.6, maxLines=4,
          anim=A("fade_up", 280)),
        gap(18),
        T("Color", 14, "w700", INK, F),
        gap(10),
        row([dot(INK, True), dot(ORANGE), dot("#FF9DB4C0"), dot("#FFE8E1D9")], spacing=12, anim=A("fade_up", 360)),
        N("Spacer"),
        row([box(row([N("IconButton", icon=icon("remove", INK), events={"onPressed": "onLess"}),
                      T("1", 16, "w700", INK, F),
                      N("IconButton", icon=icon("add", INK), events={"onPressed": "onMore"})], size="min"),
                 radius=16, border={"color": "#FFE5E5EA", "width": 1}),
             N("Expanded", child=N("ElevatedButton", {"style": {
                 "backgroundColor": INK, "foregroundColor": "Colors.white", "padding": {"v": 18}, "elevation": 0,
                 "shape": {"type": "rounded", "radius": 16}}}, ctor="icon",
                 icon=icon("shopping_bag_outlined"), label=T("Add to cart", 16, "w700", None, F),
                 events={"onPressed": "onAddToCart"}))], spacing=14, anim=A("fade_up", 440)),
    ], cross="start"), color="Colors.white", radius={"tl": 36, "tr": 36}, padding={"l": 26, "t": 28, "r": 26, "b": 24},
        shadow=shadow("#14000000", 30, -8))
    tree = N("Scaffold", {"backgroundColor": TINT}, body=col([
        N("Expanded", {"flex": 5}, child=top),
        N("Expanded", {"flex": 6}, child=sheet),
    ]))
    return screen("product", "ProductDetails", "/product", "Product details", "Shopping",
                  "Large product artwork on a radial glow (Hero), rating stars, colour swatches, quantity stepper "
                  "and an add-to-cart button on a rounded sheet.", [F], tree)


def settings() -> dict:
    F = "Inter"
    INK, MUTED, BG = "#FF111827", "#FF8A90A2", "#FFF5F6FA"

    def ibox(ic, color, tint):
        return box(icon(ic, color, 20), w=38, h=38, radius=12, color=tint, align="center")

    def tile(ic, color, tint, title, ev, trailing=None):
        return N("ListTile", leading=ibox(ic, color, tint), title=T(title, 15, "w500", INK, F),
                 trailing=trailing or icon("chevron_right_rounded", "#FFB0B5C3"), events={"onTap": ev})

    def div():
        return N("Divider", {"height": 1, "indent": 70, "color": "#FFF0F1F5"})

    def section(t):
        return pad(T(t.upper(), 12, "w600", MUTED, F, letterSpacing=1.1), l=6, b=10)

    def group(children, delay):
        return box(col(children), color="Colors.white", radius=20, anim=A("fade_up", delay))

    body = N("ListView", {"padding": {"h": 20, "v": 8}}, children=[
        box(row([avatar("avatar_3.png", 28), gap(w=14),
                 N("Expanded", child=col([T("Sam Rivera", 17, "w700", "Colors.white", F),
                                          T("sam@example.com", 13, None, "#CCFFFFFF", F)], cross="start")),
                 icon("chevron_right_rounded", "Colors.white")]),
            padding={"all": 18}, radius=22, gradient=lin("#FF0EA5E9", "#FF6366F1"), shadow=shadow("#406366F1", 20, 10),
            anim=A("fade_up", 0)),
        gap(26),
        section("General"),
        group([tile("person_outline", "#FF6366F1", "#1F6366F1", "Account", "onAccount"), div(),
               tile("lock_outline", "#FFF59E0B", "#1FF59E0B", "Privacy & security", "onPrivacy"), div(),
               tile("language", "#FF10B981", "#1F10B981", "Language", "onLanguage",
                    trailing=T("English", 14, None, MUTED, F))], 100),
        gap(26),
        section("Preferences"),
        group([N("SwitchListTile", {"value": True, "activeThumbColor": "#FF6366F1"}, name="swNotifications",
                 title=T("Notifications", 15, "w500", INK, F),
                 secondary=ibox("notifications_none", "#FFEF4444", "#1FEF4444")), div(),
               N("SwitchListTile", {"value": False, "activeThumbColor": "#FF6366F1"}, name="swDarkMode",
                 title=T("Dark mode", 15, "w500", INK, F),
                 secondary=ibox("dark_mode_outlined", "#FF8B5CF6", "#1F8B5CF6")), div(),
               pad(col([row([ibox("text_fields", "#FF0EA5E9", "#1F0EA5E9"), gap(w=16),
                             T("Text size", 15, "w500", INK, F)]),
                        N("Slider", {"value": 0.4, "activeColor": "#FF6366F1"}, name="sldTextSize")]),
                   l=16, t=12, r=8, b=4)], 200),
        gap(26),
        section("Support"),
        group([tile("help_outline", "#FF14B8A6", "#1F14B8A6", "Help center", "onHelp"), div(),
               tile("info_outline", "#FF64748B", "#1F64748B", "About", "onAbout")], 300),
        gap(20),
        N("TextButton", {"style": {"foregroundColor": "#FFEF4444", "padding": {"v": 16}}}, ctor="icon",
          icon=icon("logout_rounded"), label=T("Log out", 15, "w600", None, F), events={"onPressed": "onLogout"},
          anim=A("fade", 400)),
        gap(24),
    ])
    tree = N("Scaffold", {"backgroundColor": BG},
             appBar=N("AppBar", {"backgroundColor": BG, "elevation": 0, "centerTitle": True},
                      title=T("Settings", 18, "w700", INK, F),
                      leading=N("IconButton", icon=icon("arrow_back_ios_new", INK), events={"onPressed": "back"})),
             body=body)
    return screen("settings", "Settings", "/settings", "Settings", "Utility",
                  "Gradient account card and grouped rounded sections with tinted icon boxes, switches, a slider "
                  "and a log-out action.", [F], tree)


def chat() -> dict:
    F = "Plus Jakarta Sans"
    INK, MUTED, P, P2, BG = "#FF1E2235", "#FF8D92A6", "#FF6366F1", "#FF8B5CF6", "#FFF3F4F9"

    def bubble(me: bool, text: str, time: str, delay: int):
        return N("Align", {"alignment": "Alignment.centerRight" if me else "Alignment.centerLeft"},
                 anim=A("fade_left" if not me else "fade_right", delay),
                 child=box(col([T(text, 14, None, "Colors.white" if me else INK, F, height=1.4),
                                gap(4), T(time, 10, None, "#B3FFFFFF" if me else MUTED, F)],
                               cross="end" if me else "start", size="min"),
                           constraints={"maxWidth": 280}, margin={"b": 10}, padding={"h": 16, "v": 12},
                           gradient=lin(P, P2) if me else None, color=None if me else "Colors.white",
                           radius={"tl": 20, "tr": 20, "bl": 20 if me else 6, "br": 6 if me else 20},
                           shadow=None if me else shadow("#0A1E2235", 10, 4)))

    def tdot(a):
        return box(w=8, h=8, circle=True, color=a)

    msgs = N("ListView", {"padding": {"all": 16}}, children=[
        N("Center", child=box(T("Today", 11, "w600", MUTED, F), color="#FFE4E7F2", radius=12,
                              padding={"h": 12, "v": 4})),
        gap(14),
        bubble(False, "Hey! Did you get a chance to look at the new screens?", "09:41", 100),
        bubble(True, "Yes - the onboarding flow looks great. Love the colours.", "09:42", 250),
        bubble(False, "Thanks! I will share the prototype link later today.", "09:43", 400),
        bubble(True, "Perfect, talk soon!", "09:45", 550),
        N("Align", {"alignment": "Alignment.centerLeft"}, anim=A("fade", 800),
          child=box(row([tdot("#FFB9BDCC"), tdot("#FFD0D3DE"), tdot("#FFE2E4EC")], size="min", spacing=5),
                    color="Colors.white", padding={"h": 16, "v": 14},
                    radius={"tl": 20, "tr": 20, "bl": 6, "br": 20})),
    ])
    bar = box(N("SafeArea", {"top": False}, child=row([
        N("IconButton", {"color": P}, icon=icon("add_circle_outline"), events={"onPressed": "onAttach"}),
        N("Expanded", child=N("TextField", {"decoration": {
            "hintText": "Type a message", "border": "outline", "borderRadius": 24, "borderColor": BG,
            "focusedBorderColor": P, "filled": True, "fillColor": BG, "contentPadding": {"h": 18, "v": 12},
            "hintStyle": style(14, color=MUTED, font=F)}, "style": style(14, color=INK, font=F)},
            name="txtMessage")),
        N("IconButton", ctor="filled", icon=icon("send_rounded"), events={"onPressed": "onSend"}),
    ], spacing=6)), color="Colors.white", padding={"l": 8, "t": 10, "r": 12, "b": 10},
        shadow=shadow("#0F1E2235", 16, -4))
    tree = N("Scaffold", {"backgroundColor": BG},
             appBar=N("AppBar", {"backgroundColor": "Colors.white", "elevation": 0, "centerTitle": False,
                                 "toolbarHeight": 66},
                      leading=N("IconButton", icon=icon("arrow_back_ios_new", INK), events={"onPressed": "back"}),
                      title=row([avatar("avatar_4.png", 20), gap(w=12),
                                 col([T("Lina Haddad", 15, "w700", INK, F), T("Online", 12, "w500", "#FF22C55E", F)],
                                     cross="start", size="min")]),
                      actions=[N("IconButton", icon=icon("call_outlined", INK), events={"onPressed": "onCall"}),
                               N("IconButton", icon=icon("videocam_outlined", INK), events={"onPressed": "onVideo"}),
                               gap(w=6)]),
             body=col([N("Expanded", child=msgs), bar]))
    return screen("chat", "Chat", "/chat", "Chat", "Social",
                  "Conversation with gradient / white bubbles that slide in from their side, a typing indicator "
                  "and a rounded message bar.", [F], tree)


DESIGNS = [login, signup, onboarding, profile, dashboard, shop, product, settings, chat]


def build() -> list[dict]:
    out_dir = HERE / "screens"
    out_dir.mkdir(exist_ok=True)
    index = []
    for fn in DESIGNS:
        t = fn()
        scr: M.Screen = t["screen"]
        path = out_dir / f"{scr.name}{M.SCREEN_EXT}"
        scr.save(path)
        index.append({"id": t["id"], "title": t["title"], "category": t["category"],
                      "description": t["description"], "file": f"screens/{path.name}",
                      "thumbnail": f"thumbs/{t['id']}.png",
                      "assets": [a.rsplit("/", 1)[-1] for a in scr.data["assets"]],
                      "fonts": [f["family"] for f in scr.data["fonts"]]})
    (HERE / "index.json").write_text(json.dumps({"version": 1, "templates": index}, indent=1) + "\n",
                                     encoding="utf-8")
    return index


if __name__ == "__main__":
    for t in build():
        print(t["id"], t["file"], len(t["assets"]), "assets")
