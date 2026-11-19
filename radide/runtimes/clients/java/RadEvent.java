// RAD IDE - arguments of a GUI event, for Java (copied into _build/<lang> - do not edit).
public class RadEvent {
    public String sender = "";   // control or form name
    public String name = "";     // event name (Click, TextChanged, ...)
    public String args = "";     // raw argument text
    public int x, y, button, keyCode;
    public String keyChar = "";

    public static RadEvent parse(String sender, String name, String args) {
        RadEvent e = new RadEvent();
        e.sender = sender;
        e.name = name;
        e.args = args == null ? "" : args;
        String[] p = e.args.trim().isEmpty() ? new String[0] : e.args.trim().split("\\s+");
        e.x = num(p, 0);
        e.y = num(p, 1);
        e.button = num(p, 2);
        e.keyCode = num(p, 3);
        e.keyChar = p.length > 4 ? p[4] : "";
        return e;
    }

    private static int num(String[] p, int i) {
        try {
            return i < p.length ? Integer.parseInt(p[i]) : 0;
        } catch (NumberFormatException ex) {
            return 0;
        }
    }
}
