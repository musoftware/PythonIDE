# Java_JUnit

Tests the Test Explorer with **JUnit 5** without Maven/Gradle: the IDE compiles `src/` and `test/` with
javac and runs the official JUnit Platform Console Launcher (downloaded once into
%LOCALAPPDATA%\RADIDE\tools\junit). With a `pom.xml` and Maven installed, `mvn test` is used instead.

**Try it:** open the folder, Test > Run All Tests -> 1 passed, 1 failed (`failsOnPurpose`). Needs a JDK.
