# CSharp_XUnit

Tests the Test Explorer with **dotnet test** and xUnit: `[Fact]` and `[Theory]` + `[InlineData]` (the two
cases are shown on one test), results read from the TRX report. `FailsOnPurpose` fails.

**Try it:** open the folder, Test > Run All Tests -> 2 passed, 1 failed (first run restores NuGet packages
and builds; bin/obj are not kept in the sample). Needs the .NET 9 SDK.
