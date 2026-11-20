# GradleHello - foreign project test (Gradle, `gradle init` layout)

Multi-project layout as created by `gradle init` (application): `settings.gradle` + `app/build.gradle`
with the `application` plugin (`mainClass = 'demo.App'`). Open the folder or `settings.gradle`'s folder:
RAD IDE uses `gradlew` if present, else `gradle` on PATH, else a Gradle distribution already downloaded by
a wrapper (`~/.gradle/wrapper/dists`). Targets: `gradle run` and `demo.App`.
