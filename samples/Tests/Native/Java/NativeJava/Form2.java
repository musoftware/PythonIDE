public class Form2 extends Form2Designer {
    static void Form2_Load(RadEvent e) {
        lblMsg.setText("Form2 loaded");
    }

    static void btnBack_Click(RadEvent e) {
        set("Form1.lblOut", "Text", "From Form2");
        hide("Form2");
    }
}
