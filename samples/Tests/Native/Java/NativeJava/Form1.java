// Event handlers for Form1 (native build test).
public class Form1 extends Form1Designer {
    static int ticks;

    static void Form1_Load(RadEvent e) {
        lblOut.setText("Loaded");
    }

    static void btnGreet_Click(RadEvent e) {
        String name = txtName.getText();
        String text = chkShout.getValue().equals("1") ? (String) radcall("Helper.shout", name) : Helper.greet(name);
        lblOut.setText(text);
        lstLog.addItem(text);
        lblCount.setText(lstLog.getListCount() + " items");
    }

    static void txtName_TextChanged(RadEvent e) {
        lblEcho.setText("echo:" + txtName.getText());
    }

    static void btnStart_Click(RadEvent e) {
        ticks = 0;
        tmrTick.setEnabled(true);
    }

    static void tmrTick_Tick(RadEvent e) {
        ticks++;
        lblTicks.setText(String.valueOf(ticks));
        if (ticks >= 5) tmrTick.setEnabled(false);
    }

    static void btnForm2_Click(RadEvent e) {
        show("Form2");
    }

    static void mnuFileHello_Click(RadEvent e) {
        lblOut.setText("Menu clicked");
    }

    static void mnuFileExit_Click(RadEvent e) {
        end();
    }

    static void btnClose_Click(RadEvent e) {
        end();
    }
}
