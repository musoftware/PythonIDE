package hello;

import javax.swing.*;
import java.awt.event.*;

public class MainFrame extends JFrame {
    private JTextField txtName;
    private JLabel lblResult;
    private JButton btnGreet;
    private JCheckBox chkUpper;
    private int count = 0;

    public MainFrame() {
        setTitle("Hello Swing");
        setSize(360, 220);
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        getContentPane().setLayout(null);

        txtName = new JTextField("World");
        txtName.setBounds(12, 12, 200, 24);
        getContentPane().add(txtName);

        btnGreet = new JButton("Greet");
        btnGreet.setBounds(224, 12, 100, 26);
        btnGreet.addActionListener(new ActionListener() {
            public void actionPerformed(ActionEvent e) {
                btnGreet_Click();
            }
        });
        getContentPane().add(btnGreet);

        chkUpper = new JCheckBox("Upper case");
        chkUpper.setBounds(12, 44, 150, 24);
        getContentPane().add(chkUpper);

        lblResult = new JLabel("Type a name");
        lblResult.setBounds(12, 80, 312, 28);
        getContentPane().add(lblResult);
    }

    private void btnGreet_Click() {
        String name = txtName.getText().trim();
        if (name.isEmpty()) {
            JOptionPane.showMessageDialog(this, "Please type a name");
            return;
        }
        if (chkUpper.isSelected()) {
            name = name.toUpperCase();
        }
        count++;
        lblResult.setText("Hello, " + name + "! (" + count + ")");
    }

    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> new MainFrame().setVisible(true));
    }
}
