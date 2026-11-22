public static partial class Form2
{
    static void Form2_Load(RadEvent e)
    {
        lblMsg.Text = "Form2 loaded";
    }

    static void btnBack_Click(RadEvent e)
    {
        Set("Form1.lblOut", "Text", "From Form2");
        Hide("Form2");
    }
}
