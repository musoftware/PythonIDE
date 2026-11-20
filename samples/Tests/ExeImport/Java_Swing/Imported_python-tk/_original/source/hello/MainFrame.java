package hello;

import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import javax.swing.JButton;
import javax.swing.JCheckBox;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.JTextField;
import javax.swing.SwingUtilities;

public class MainFrame extends JFrame {
   private JTextField txtName;
   private JLabel lblResult;
   private JButton btnGreet;
   private JCheckBox chkUpper;
   private int count = 0;

   public MainFrame() {
      this.setTitle("Hello Swing");
      this.setSize(360, 220);
      this.setDefaultCloseOperation(3);
      this.getContentPane().setLayout(null);
      this.txtName = new JTextField("World");
      this.txtName.setBounds(12, 12, 200, 24);
      this.getContentPane().add(this.txtName);
      this.btnGreet = new JButton("Greet");
      this.btnGreet.setBounds(224, 12, 100, 26);
      this.btnGreet.addActionListener(new ActionListener() {
         @Override
         public void actionPerformed(ActionEvent var1) {
            MainFrame.this.btnGreet_Click();
         }
      });
      this.getContentPane().add(this.btnGreet);
      this.chkUpper = new JCheckBox("Upper case");
      this.chkUpper.setBounds(12, 44, 150, 24);
      this.getContentPane().add(this.chkUpper);
      this.lblResult = new JLabel("Type a name");
      this.lblResult.setBounds(12, 80, 312, 28);
      this.getContentPane().add(this.lblResult);
   }

   private void btnGreet_Click() {
      String var1 = this.txtName.getText().trim();
      if (var1.isEmpty()) {
         JOptionPane.showMessageDialog(this, "Please type a name");
      } else {
         if (this.chkUpper.isSelected()) {
            var1 = var1.toUpperCase();
         }

         this.count++;
         this.lblResult.setText("Hello, " + var1 + "! (" + this.count + ")");
      }
   }

   public static void main(String[] var0) {
      SwingUtilities.invokeLater(() -> new MainFrame().setVisible(true));
   }
}
