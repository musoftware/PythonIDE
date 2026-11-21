"""Writes the designed screens of the DataFormsScreens test project (screens/*.fscreen.json), the Lottie
animation used by the Splash screen and the generated Dart (lib/). From the repository root:

    python samples/Tests/FlutterDesigner/DataFormsScreens/make_screens.py

All designs and the animation are original to RAD IDE.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
from radide.flutterdesign import codegen as CG, model as M  # noqa: E402


def T(type_, props=None, slots=None, children=None, **extra):
    return M.T(type_, props, slots, children, **extra)


def txt(s, **style):
    return T("Text", {"data": s, **({"style": style} if style else {})})


CATALOG = {
    "version": 1, "name": "Catalog", "route": "/", "theme": {}, "assets": [], "fonts": [],
    "tree": T("Scaffold", slots={
        "appBar": T("AppBar", slots={"title": T("Text", {"spans": [
            {"text": "Fruit "}, {"text": "Market", "style": {"fontWeight": "FontWeight.bold",
                                                             "color": "#FF6750A4"}}]}, ctor="rich")}),
        "body": T("Column", {"crossAxisAlignment": "CrossAxisAlignment.stretch"}, children=[
            T("Padding", {"padding": {"all": 16}}, {"child": T("RichText", {
                "spans": [{"text": "Fresh ", "style": {"color": "#FF1F1F1F", "fontSize": 18}},
                          {"text": "today", "style": {"color": "#FF00897B", "fontSize": 18,
                                                      "fontStyle": "FontStyle.italic",
                                                      "shadows": [{"color": "#55000000", "blur": 2,
                                                                   "offset": [1, 1]}]}},
                          {"text": " - tap a fruit", "style": {"color": "#FF757575", "fontSize": 14}}],
                "textAlign": "TextAlign.center"})}),
            T("Expanded", {"flex": 2}, {"child": T("ListView", {
                "itemCount": 6, "items": ["Apple", "Banana", "Cherry", "Mango", "Orange", "Pear"],
                "padding": {"h": 8}}, {"itemBuilder": T("Card", slots={"child": T("ListTile", slots={
                    "leading": T("CircleAvatar", slots={"child": T("Text", {"data": {"$code": "'${index + 1}'"}})}),
                    "title": T("Text", {"data": {"$code": "item"}}),
                    "subtitle": T("Text", {"data": {"$code": "'Item number $index'"}}),
                    "trailing": T("Icon", {"icon": "Icons.chevron_right"})})})}, ctor="builder",
                name="lstFruit")}),
            T("Expanded", {"flex": 1}, {"child": T("GridView", {
                "crossAxisCount": 3, "mainAxisSpacing": 8, "crossAxisSpacing": 8, "itemCount": 9,
                "padding": {"all": 8}},
                {"itemBuilder": T("Container", {"alignment": "Alignment.center", "decoration": {
                    "color": "#FFE8DEF8", "borderRadius": 12}}, {"child": T("Text", {
                        "data": {"$code": "'Box $index'"}})})}, ctor="builder")}),
        ])}),
}

SIGNUP = {
    "version": 1, "name": "SignUp", "route": "/sign_up", "theme": {}, "assets": [], "fonts": [],
    "tree": T("Scaffold", slots={
        "appBar": T("AppBar", slots={"title": txt("Create account")}),
        "body": T("Form", {"autovalidateMode": "AutovalidateMode.onUserInteraction"}, {"child": T(
            "SingleChildScrollView", {"padding": {"all": 20}}, {"child": T("Column", {"spacing": 12}, children=[
                T("TextFormField", {"decoration": {"labelText": "Name", "border": "outline"},
                                    "validators": [{"rule": "required", "message": "Please enter your name"}]},
                  name="txtName"),
                T("TextFormField", {"decoration": {"labelText": "E-mail", "border": "outline",
                                                   "prefixIcon": "Icons.email_outlined"},
                                    "keyboardType": "TextInputType.emailAddress",
                                    "validators": [{"rule": "required"}, {"rule": "email"}]}, name="txtEmail"),
                T("TextFormField", {"decoration": {"labelText": "Password", "border": "outline"},
                                    "obscureText": True,
                                    "validators": [{"rule": "required"},
                                                   {"rule": "minLength", "value": 8,
                                                    "message": "At least 8 characters"}]}, name="txtPassword"),
                T("TextFormField", {"decoration": {"labelText": "Phone (digits)", "border": "outline"},
                                    "keyboardType": "TextInputType.phone",
                                    "validators": [{"rule": "regex", "value": "^[0-9]{7,15}$",
                                                    "message": "7 to 15 digits"}, {"rule": "maxLength", "value": 15}]},
                  name="txtPhone", events={"validator": "checkPhone"}),
                T("TextFormField", {"decoration": {"labelText": "Promo code", "border": "outline"}},
                  name="txtPromo", events={"validator": "checkPromo"}),
                txt("Plan", fontWeight="FontWeight.bold"),
                T("RadioGroup", {"groupValue": "free"}, {"child": T("Column", {"mainAxisSize": "MainAxisSize.min"},
                                                                     children=[
                    T("RadioListTile", {"value": "free"}, {"title": txt("Free")}),
                    T("RadioListTile", {"value": "pro"}, {"title": txt("Pro"), "subtitle": txt("5 USD / month")}),
                    T("Row", children=[T("Radio", {"value": "team"}), txt("Team")]),
                ])}, name="rdoPlan", events={"onChanged": "planChanged"}),
                T("FilledButton", slots={"child": txt("Sign up")}, events={"onPressed": "validate:form1:onSubmit"},
                  name="btnSignUp"),
                T("OutlinedButton", slots={"child": txt("Check")}, events={"onPressed": "validate:form1"}),
            ])})}, name="form1"),
    }),
}

PULSE = {
    "version": 1, "name": "Pulse", "route": "/pulse", "theme": {}, "assets": [], "fonts": [],
    "timelines": [{"name": "grow", "durationMs": 1200, "autostart": True, "repeat": True, "reverse": True}],
    "tree": T("Scaffold", slots={
        "appBar": T("AppBar", slots={"title": txt("Timeline on numbers")}),
        "body": T("Center", slots={"child": T("Column", {"mainAxisSize": "MainAxisSize.min", "spacing": 16},
                                                children=[
            T("Container", {"width": {"$timeline": "grow", "from": 80, "to": 220, "curve": "Curves.easeInOut"},
                            "height": 80, "decoration": {"color": "#FF6750A4", "borderRadius": 16}},
              name="boxGrow"),
            T("Opacity", {"opacity": {"$timeline": "grow", "from": 0.2, "to": 1, "interval": [0, 0.5]}},
              {"child": txt("Fading text", fontSize=20)}),
            T("Text", {"data": "Lines follow the timeline as well",
                       "maxLines": {"$timeline": "grow", "from": 1, "to": 3}}),
            T("Lottie", {"name": "assets/animations/pulse.json", "width": 120, "height": 120}, ctor="asset"),
        ])})}),
}

SCREENS = [CATALOG, SIGNUP, PULSE]


def pulse_lottie() -> dict:
    """A small original Lottie animation: a purple circle that pulses inside a teal ring (60 frames)."""
    def kf(t, v, ease=True):
        k = {"t": t, "s": v}
        if ease:
            k.update({"i": {"x": [0.4], "y": [1]}, "o": {"x": [0.6], "y": [0]}})
        return k

    def ks(scale=None):
        return {"o": {"a": 0, "k": 100}, "r": {"a": 0, "k": 0}, "p": {"a": 0, "k": [100, 100, 0]},
                "a": {"a": 0, "k": [0, 0, 0]},
                "s": scale or {"a": 0, "k": [100, 100, 100]}}
    circle = {"ty": "gr", "nm": "dot", "it": [
        {"ty": "el", "nm": "ellipse", "p": {"a": 0, "k": [0, 0]}, "s": {"a": 0, "k": [90, 90]}},
        {"ty": "fl", "nm": "fill", "c": {"a": 0, "k": [0.404, 0.314, 0.643, 1]}, "o": {"a": 0, "k": 100}},
        {"ty": "tr", "p": {"a": 0, "k": [0, 0]}, "a": {"a": 0, "k": [0, 0]}, "s": {"a": 0, "k": [100, 100]},
         "r": {"a": 0, "k": 0}, "o": {"a": 0, "k": 100}}]}
    ring = {"ty": "gr", "nm": "ring", "it": [
        {"ty": "el", "nm": "ellipse", "p": {"a": 0, "k": [0, 0]}, "s": {"a": 0, "k": [160, 160]}},
        {"ty": "st", "nm": "stroke", "c": {"a": 0, "k": [0, 0.749, 0.647, 1]}, "o": {"a": 0, "k": 100},
         "w": {"a": 0, "k": 8}},
        {"ty": "tr", "p": {"a": 0, "k": [0, 0]}, "a": {"a": 0, "k": [0, 0]}, "s": {"a": 0, "k": [100, 100]},
         "r": {"a": 0, "k": 0}, "o": {"a": 0, "k": 100}}]}
    return {"v": "5.7.4", "fr": 30, "ip": 0, "op": 60, "w": 200, "h": 200, "nm": "RAD pulse", "ddd": 0,
            "assets": [], "layers": [
                {"ddd": 0, "ind": 1, "ty": 4, "nm": "dot", "sr": 1, "ip": 0, "op": 60, "st": 0, "bm": 0,
                 "ks": ks({"a": 1, "k": [kf(0, [70, 70, 100]), kf(30, [110, 110, 100]), {"t": 60, "s": [70, 70, 100]}]}),
                 "shapes": [circle]},
                {"ddd": 0, "ind": 2, "ty": 4, "nm": "ring", "sr": 1, "ip": 0, "op": 60, "st": 0, "bm": 0,
                 "ks": ks(), "shapes": [ring]}]}


def main() -> int:
    (HERE / "screens").mkdir(exist_ok=True)
    for d in SCREENS:
        scr = M.Screen(json.loads(json.dumps(d)))
        for n, *_ in scr.walk():
            if not n.get("id"):
                n["id"] = scr.new_id()
        if any(n.get("type") == "Lottie" for n, *_ in scr.walk()):
            scr.data["assets"] = ["assets/animations/pulse.json"]
        scr.save(HERE / "screens" / f"{scr.name}{M.SCREEN_EXT}")
    anim = HERE / "assets" / "animations" / "pulse.json"
    anim.parent.mkdir(parents=True, exist_ok=True)
    anim.write_text(json.dumps(pulse_lottie(), separators=(",", ":")), encoding="utf-8")
    written, warnings = CG.write_all(HERE)
    main_dart = HERE / "lib" / "main.dart"
    screens = [M.Screen.load(p) for p in M.find_screens(HERE)]
    text = CG.standalone_main("Data Forms Screens", screens, "/")
    if not main_dart.exists() or main_dart.read_text(encoding="utf-8") != text:
        main_dart.write_text(text, encoding="utf-8")
    print("written:", written)
    print("warnings:", warnings)
    return 1 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
