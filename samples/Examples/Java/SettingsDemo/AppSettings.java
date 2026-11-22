// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// AppSettings - the settings of the Greeting Cards example (a code module shared by its three forms), kept in
// settings.properties (java.util.Properties written as UTF-8, so the Arabic language name stays readable).
import java.io.IOException;
import java.io.Reader;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Properties;

public class AppSettings {
    static final Path FILE = Paths.get("settings.properties");
    static String user = "Friend";
    static String language = "English";          // "English" or "العربية"
    static int fontSize = 11;
    static boolean formal = false;

    static boolean arabic() { return !language.equals("English"); }

    static void load() {
        if (!Files.exists(FILE)) return;
        Properties p = new Properties();
        try (Reader r = Files.newBufferedReader(FILE, StandardCharsets.UTF_8)) {
            p.load(r);
        } catch (IOException ex) {
            return;
        }
        user = p.getProperty("user", user);
        language = p.getProperty("language", language);
        try {
            int size = Integer.parseInt(p.getProperty("font_size", "11"));
            if (size >= 8 && size <= 24) fontSize = size;
        } catch (NumberFormatException ignored) {
            // keep the default
        }
        formal = "1".equals(p.getProperty("formal"));
    }

    static boolean save() {
        Properties p = new Properties();
        p.setProperty("user", user);
        p.setProperty("language", language);
        p.setProperty("font_size", String.valueOf(fontSize));
        p.setProperty("formal", formal ? "1" : "0");
        try (Writer w = Files.newBufferedWriter(FILE, StandardCharsets.UTF_8)) {
            p.store(w, "Greeting Cards settings");
            return true;
        } catch (IOException ex) {
            return false;
        }
    }
}
