# NetBeansSwingGreeter - foreign project test (NetBeans Ant project + Swing GUI Builder)

`nbproject/project.xml` + `project.properties` (main.class = greeter.GreeterFrame) and a Free Design
(GroupLayout) form `src/greeter/GreeterFrame.form` with the matching NetBeans-generated `GreeterFrame.java`
(CRLF, guarded blocks `//GEN-BEGIN:initComponents`, `//GEN-BEGIN:variables`, an event handler).

Open `nbproject/project.xml` (or the folder, or the .form): the form opens in the designer; saving writes the
changes into the .form and regenerates initComponents()/variables like NetBeans (RAD IDE's generator
reproduces this file's initComponents exactly). Built with ant when installed, else javac; F5 runs/debugs (JDWP).
