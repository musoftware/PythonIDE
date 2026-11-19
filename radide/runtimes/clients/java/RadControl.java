// RAD IDE - a control (or form) of a RAD IDE form, for Java (copied into _build/<lang> - do not edit).
// Property and method names are VB-style: getText/setText, getCaption/setCaption, addItem, clear ...
public class RadControl {
    public final String path;

    public RadControl(String path) { this.path = path; }

    public String get(String prop) { return Rad.get(path, prop); }
    public void set(String prop, Object value) { Rad.set(path, prop, value); }
    public String call(String method, Object... args) { return Rad.call(path, method, args); }

    public String getText() { return get("Text"); }
    public void setText(Object v) { set("Text", v); }
    public String getCaption() { return get("Caption"); }
    public void setCaption(Object v) { set("Caption", v); }
    public String getValue() { return get("Value"); }
    public void setValue(Object v) { set("Value", v); }
    public double getNumber() { return Rad.toNumber(getText()); }
    public boolean isEnabled() { return Rad.toBool(get("Enabled")); }
    public void setEnabled(boolean v) { set("Enabled", v); }
    public boolean isVisible() { return Rad.toBool(get("Visible")); }
    public void setVisible(boolean v) { set("Visible", v); }
    public int getLeft() { return Rad.toInt(get("Left")); }
    public void setLeft(int v) { set("Left", v); }
    public int getTop() { return Rad.toInt(get("Top")); }
    public void setTop(int v) { set("Top", v); }
    public int getWidth() { return Rad.toInt(get("Width")); }
    public void setWidth(int v) { set("Width", v); }
    public int getHeight() { return Rad.toInt(get("Height")); }
    public void setHeight(int v) { set("Height", v); }
    public String getBackColor() { return get("BackColor"); }
    public void setBackColor(Object v) { set("BackColor", v); }
    public String getForeColor() { return get("ForeColor"); }
    public void setForeColor(Object v) { set("ForeColor", v); }
    public int getListIndex() { return Rad.toInt(get("ListIndex")); }
    public void setListIndex(int v) { set("ListIndex", v); }
    public int getListCount() { return Rad.toInt(get("ListCount")); }
    public int getInterval() { return Rad.toInt(get("Interval")); }
    public void setInterval(int v) { set("Interval", v); }

    public void addItem(Object item) { call("AddItem", item); }
    public void removeItem(int index) { call("RemoveItem", index); }
    public void clear() { call("Clear"); }
    public String list(int index) { return call("List", index); }
    public void setFocus() { call("SetFocus"); }
    public void move(int left, int top, int width, int height) { call("Move", left, top, width, height); }
    public String showDialog() { return call("ShowDialog"); }
    public void show() { Rad.show(path); }
    public void hide() { Rad.hide(path); }

    @Override
    public String toString() { return getText(); }
}
