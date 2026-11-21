# Car diagnostics course (Arabic)

`course.json` + 9 lessons (`NN-slug.md`) for car owners and mechanics using RAD IDE's car diagnostics tool
(docs/CARDIAG.md): how car computers, OBD-II, UDS and ELM327 / STN / J2534 adapters work; connecting and the Demo
car; dashboard warning lights (Read the Car's Lights); reading and understanding fault codes (stored / pending /
permanent, UDS failure-type byte, manufacturer-specific codes, Scan All Control Units); live data and freeze frames;
readiness monitors and the drive cycle; service functions (cooling-system bleed with its checklist and progress,
radiator fan test with control returned, definition packs, the policy filter, security access only through the
user's own plug-in); clearing faults correctly (one specific fault after confirming the repair, safety-relevant
faults, units that cannot clear a single fault); and a full diagnosis project with a report.

Scope: diagnosis, repair and normal service routines. The course has no immobiliser / key, odometer, security
cracking, emissions-defeat, permanent fault-masking or readiness-faking content (the tool has none either).
Every example runs against the built-in Demo car simulator (radide/cardiag/sim) - no hardware, no vehicle.

Block kinds besides the usual `python run` / `exercise` / `solution`, `text output` and `quiz`:

| Fence | Checked by `tools/check_lessons.py` |
|---|---|
| `carpy run` | Python that uses RAD IDE's car-diagnostics library (`radide.cardiag.*`) against the Demo car simulator, run in a fresh folder with the repository on PYTHONPATH (and `RADIDE_CARDIAG_HOME` inside that folder); output = the following `text output` block. The lesson viewer shows it as code. |

    python radide/tutorials/car-diagnostics/tools/check_lessons.py [-v] [lesson-id-prefix ...]
    python radide/tutorials/car-diagnostics/tools/check_lessons.py --fill     # maintainer: fill "TODO" outputs
    python tools/build_chm.py car-diagnostics --verify
