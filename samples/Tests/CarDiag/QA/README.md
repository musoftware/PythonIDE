# CarDiag/QA - car diagnostics end to end

`qa_cardiag_e2e.py` uses the real IDE (samples/Tests/QA/Integration/qh.py: QSettings org RADIDE-TEST,
RADIDE_NO_BROWSER=1, screenshots only with widget.grab()) the way a car owner / mechanic would, with one Demo car
(Tools > Car Diagnostics... > Demo car through the ELM327 simulator) for the scan tool, the fault guide and the
service functions:

connect -> Read the Car's Lights -> Read Codes + Scan All Control Units -> explanation and causes -> freeze frame ->
live data -> symptom wizard ("العربية بتسخن") -> Explain with AI (mock provider) -> cooling-system bleed (refused with
the engine running, then completed with the checklist and progress) -> radiator fan test (control returned) ->
clear P0171 alone after confirming the repair (gone in the Faults tab, P0301 kept) -> readiness -> HTML report ->
policy filter and no excluded functions in the code.

    set RADIDE_NO_BROWSER=1 & .venv\Scripts\python.exe samples\Tests\CarDiag\QA\qa_cardiag_e2e.py
    set QA_LANG=ar & set QA_THEME=dark & .venv\Scripts\python.exe samples\Tests\CarDiag\QA\qa_cardiag_e2e.py

The Arabic course: `python radide/tutorials/car-diagnostics/tools/check_lessons.py` and
`python tools/build_chm.py car-diagnostics --verify`.
