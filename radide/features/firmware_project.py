"""ECU / firmware projects in the IDE (radide/firmware/project, radide/firmware/checksum, docs/FIRMWARE.md):

* Project > ECU Project: Set Original..., View Original (read-only), Edit Working Copy, Checksums... (blocks,
  finder, profiles), Versions..., Build, Open Build Output, Export Modification Report..., Export / Import Patch
  (IPS / BPS / UPS), Build Settings..., and Checksum Toolkit... (for any binary, also without a project).
* Solution Explorer: an "ECU Project" node (original, working copy, versions, checksums, build output).
* Saving the working copy in the hex editor recalculates the checksum blocks (when "correct on save" is on)
  and reports which blocks changed in the Output window.
* The one-time safety / legal notice (radide/firmware/project/notice.py) is shown when the first ECU project
  is created or opened.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QDialog, QFileDialog, QMessageBox, QTreeWidgetItem

ROLE = Qt.ItemDataRole.UserRole
LANG = "firmware-ecu"


class FirmwareProjectFeature:
    def __init__(self, win):
        self.win = win
        self._notice_pending = False
        self._correcting = False
        self._menus()
        self._wrap()
        try:
            win.solution.itemDoubleClicked.connect(self._on_tree_dclick)
        except Exception:  # noqa: BLE001
            pass
        try:
            from ..retro.filebus import subscribe
            subscribe(win, self._on_file_written)
        except Exception:  # noqa: BLE001 - the shared bus is optional
            pass

    # ================================================================== helpers
    def _log(self, text: str) -> None:
        try:
            self.win.log(text)
            self.win.statusBar().showMessage(text.splitlines()[0] if text else "", 6000)
        except Exception:  # noqa: BLE001
            pass

    def project(self, proj=None):
        """The active ECU project (EcuProject) or None."""
        p = proj or getattr(self.win, "project", None)
        if p is None or getattr(p, "language", "") != LANG:
            return None
        from ..firmware.project.model import EcuProject
        try:
            return EcuProject.load(p.folder)
        except (OSError, ValueError) as e:
            self._log(f"[ecu project] cannot read ecu.json: {e}")
            return None

    def _need(self):
        ep = self.project()
        if ep is None:
            QMessageBox.information(self.win, "ECU Project", "Open an ECU / Firmware project first.")
        return ep

    def _rom(self):
        return getattr(self.win, "rom_workbench", None)

    def open_hex(self, path, read_only: bool = False):
        rw = self._rom()
        if rw is None:
            return None
        p = Path(path)
        if read_only:
            rw._read_only_paths.add(str(p.resolve()).lower())
        return rw.open_hex(p, read_only=read_only)

    def _refresh_tree(self) -> None:
        try:
            self.win._fill_solution()
        except Exception:  # noqa: BLE001
            pass

    def _reload(self, path) -> None:
        try:
            from ..retro.filebus import file_changed
            file_changed(self.win, path, source=self)
        except Exception:  # noqa: BLE001
            pass

    def _start_dir(self) -> str:
        p = getattr(self.win, "project", None)
        return str(p.folder) if p is not None else ""

    # ================================================================== window glue
    def _wrap(self) -> None:
        win = self.win
        orig_fill = win._fill_solution

        def fill_solution(*a, **k):
            r = orig_fill(*a, **k)
            try:
                self._add_tree_nodes()
                self._maybe_notice()
            except Exception as e:  # noqa: BLE001 - never break Solution Explorer
                win.log(f"[ecu project] {e}")
            return r
        win._fill_solution = fill_solution
        win.ecu_project_feature = self

    def _maybe_notice(self) -> None:
        if self._notice_pending or self.project() is None:
            return
        from ..firmware.project import notice
        if notice.accepted():
            return
        self._notice_pending = True
        QTimer.singleShot(0, self.show_notice)

    def show_notice(self) -> bool:
        from ..firmware.project import notice
        try:
            from ..i18n import tr
        except Exception:  # noqa: BLE001
            tr = None
        try:
            return notice.ensure_accepted(self.win, tr)
        finally:
            self._notice_pending = False

    # ================================================================== menus
    def _menu(self, title: str):
        return next((a.menu() for a in self.win.menuBar().actions() if a.menu() is not None and
                     a.text().replace("&", "") == title), None)

    def _menus(self) -> None:
        pm = self._menu("Project")
        if pm is None:
            return
        sub = pm.addMenu("ECU &Project")
        self.menu = sub
        self.acts = {}

        def act(key, text, slot, needs=True):
            a = sub.addAction(text, slot)
            a.setObjectName("ecu_" + key)
            if needs:
                self.acts[key] = a
            return a
        act("set_original", "Set &Original...", self.set_original)
        act("view_original", "&View Original (read-only)", self.view_original)
        act("edit_work", "Edit &Working Copy", self.edit_work)
        sub.addSeparator()
        act("checksums", "&Checksums...", self.checksums)
        act("verify", "&Verify Checksums", self.verify_checksums)
        act("versions", "Versio&ns...", self.versions)
        act("compare", "Compare with Original", self.compare_original)
        sub.addSeparator()
        act("build", "&Build ECU Project", self.build)
        act("output", "Open Build &Output", self.open_output)
        act("report", "Export Modification &Report...", self.export_report)
        act("export_patch", "&Export Patch (IPS / BPS)...", self.export_patch)
        act("import_patch", "&Import Patch...", self.import_patch)
        act("settings", "Build &Settings...", self.build_settings)
        sub.addSeparator()
        act("toolkit", "Checksum &Toolkit (any file)...", self.checksum_toolkit, needs=False)
        sub.aboutToShow.connect(self._update_menu)

    def _update_menu(self) -> None:
        on = self.project() is not None
        for a in self.acts.values():
            a.setEnabled(on)

    # ================================================================== original / working copy
    def set_original(self, path: str = "", base: int | None = None):
        ep = self._need()
        if ep is None:
            return None
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self.win, "Choose the Original Firmware File", self._start_dir(),
                "Firmware files (*.bin *.ori *.rom *.hex *.s19 *.s28 *.s37 *.srec *.mot *.elf *.dump *.img);;"
                "All files (*)")
            if not path:
                return None
        if ep.original and ep.work_path is not None and ep.work_path.is_file() and \
                QMessageBox.question(self.win, "Set Original", "Replace the original and start a new working copy?\n"
                                     "Save a version first if you want to keep the current one.") \
                != QMessageBox.StandardButton.Yes:
            return None
        from ..firmware.project.model import EcuProjectError
        try:
            ep.set_original(path, copy=True, base=base or 0)
            ep.save()
        except (EcuProjectError, OSError, ValueError) as e:
            QMessageBox.warning(self.win, "Set Original", str(e))
            return None
        self._log(f"ECU project: original {ep.original} ({ep.original_size:,} bytes, {ep.original_format}, "
                  f"SHA-256 {ep.original_sha256[:16]}...) - working copy {ep.work}")
        self._refresh_tree()
        return ep

    def view_original(self):
        ep = self._need()
        if ep is None or ep.original_path is None:
            return None
        return self.open_hex(ep.original_path, read_only=True)

    def edit_work(self):
        ep = self._need()
        if ep is None:
            return None
        try:
            ep.work_bytes()                         # creates the working copy when missing
            ep.save()
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self.win, "ECU Project", str(e))
            return None
        return self.open_hex(ep.work_path, read_only=False)

    def _flush_work(self, ep) -> None:
        """Save an open, modified hex document of the working copy first."""
        rw = self._rom()
        if rw is None or ep.work_path is None:
            return
        key = str(ep.work_path.resolve()).lower()
        d = rw.docs.get(key)
        try:
            if d is not None and d.is_modified():
                d.save()
        except RuntimeError:
            pass

    # ================================================================== checksums
    def checksums(self):
        ep = self._need()
        if ep is None:
            return None
        from ..firmware.checksum.ui import ChecksumDialog
        self._flush_work(ep)
        try:
            data = ep.work_bytes()
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self.win, "Checksums", str(e))
            return None
        try:
            orig = ep.original_bytes()
        except Exception:  # noqa: BLE001
            orig = None
        dlg = ChecksumDialog(self.win, data, ep.checksums, orig, True, f"Checksums - {ep.name}",
                             str(ep.folder / "profiles"))
        self.last_dialog = dlg
        if dlg.exec() == QDialog.DialogCode.Accepted:
            fresh = self.project()
            fresh.checksums = dlg.blocks
            fresh.save()
            if dlg.corrected_data is not None and dlg.corrected_data != data:
                fresh.write_work(dlg.corrected_data)
                self._reload(fresh.work_path)
                self._log("Checksums written into the working copy:\n" +
                          "\n".join("  " + r.line() for r in dlg.last_results))
            self._refresh_tree()
        return dlg

    def verify_checksums(self):
        ep = self._need()
        if ep is None:
            return None
        from ..firmware.checksum.blocks import report
        self._flush_work(ep)
        res = ep.verify_checksums()
        self._log(report(res, f"Verify checksums ({ep.name})"))
        return res

    def checksum_toolkit(self, path: str = ""):
        """The checksum dialog for any binary (the current hex document, or a chosen file)."""
        from ..firmware.checksum.ui import ChecksumDialog
        rw = self._rom()
        doc = rw.current() if rw is not None else None
        if not path and doc is not None and getattr(doc, "path", None):
            path = str(doc.path)
        if not path:
            path, _ = QFileDialog.getOpenFileName(self.win, "Checksum Toolkit", self._start_dir(), "All files (*)")
            if not path:
                return None
        p = Path(path)
        try:
            from ..firmware.project.model import load_image
            data = doc.data() if doc is not None and doc.path and Path(doc.path) == p else load_image(p)[0]
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self.win, "Checksum Toolkit", str(e))
            return None
        dlg = ChecksumDialog(self.win, data, [], data, False, f"Checksum Toolkit - {p.name}", str(p.parent))
        self.last_dialog = dlg
        dlg.exec()
        return dlg

    def _on_file_written(self, path, source=None) -> None:
        """filebus: the working copy was saved -> recalculate the checksum blocks (correct on save)."""
        if self._correcting or source is self:
            return
        ep = self.project()
        if ep is None or not ep.correct_on_save or not ep.checksums or ep.work_path is None:
            return
        try:
            if Path(path).resolve() != ep.work_path.resolve():
                return
        except OSError:
            return
        self._correcting = True
        try:
            res = ep.correct_work()
        except Exception as e:  # noqa: BLE001
            self._log(f"[ecu project] checksum correction failed: {e}")
            return
        finally:
            self._correcting = False
        fixed = [r for r in res if r.corrected]
        bad = [r for r in res if r.error]
        if fixed:
            self._reload(ep.work_path)
            self._log(f"Checksums recalculated on save ({len(fixed)} of {len(res)} block(s)):\n" +
                      "\n".join("  " + r.line() for r in fixed))
        for r in bad:
            self._log("  " + r.line())
        self.last_correction = res

    # ================================================================== versions / compare
    def versions(self):
        ep = self._need()
        if ep is None:
            return None
        from ..firmware.project.ui import VersionsDialog
        self._flush_work(ep)
        dlg = VersionsDialog(self.win, ep)
        dlg.workChanged.connect(lambda: (self._reload(ep.work_path), self._refresh_tree()))
        dlg.compareRequested.connect(self._compare)
        self.last_dialog = dlg
        dlg.exec()
        self._refresh_tree()
        return dlg

    def _compare(self, a, b):
        rw = self._rom()
        return rw.compare(a, b) if rw is not None else None

    def compare_original(self):
        ep = self._need()
        if ep is None or ep.original_path is None:
            return None
        self._flush_work(ep)
        try:
            d = ep.diff("original", "work")
            self._log(f"ECU project {ep.name}: original -> working copy: {d.summary()}" +
                      "".join("\n  map " + m.line() for m in d.maps))
        except Exception as e:  # noqa: BLE001
            self._log(f"[ecu project] diff: {e}")
        if ep.original_format == "raw":
            return self._compare(str(ep.original_path), str(ep.work_path))
        return None

    # ================================================================== build / report / patches
    def build(self):
        ep = self._need()
        if ep is None:
            return None
        try:
            self.win.save_all()
        except Exception:  # noqa: BLE001
            pass
        from ..firmware.project.model import EcuProjectError
        try:
            res = ep.build(log=self.win.log)
        except (EcuProjectError, OSError, ValueError) as e:
            self.win.log(f"*** ECU build failed: {e}")
            QMessageBox.warning(self.win, "Build", str(e))
            return None
        rec = res.recalculated
        self.win.statusBar().showMessage(
            f"Built {res.output.name}: {len(rec)} checksum block(s) recalculated"
            + (f", {len(res.problems)} with problems" if res.problems else ""), 8000)
        self.last_build = res
        self._refresh_tree()
        return res

    def open_output(self):
        ep = self._need()
        if ep is None:
            return None
        if not ep.output_path.is_file():
            if self.build() is None:
                return None
        if ep.output_format() == "raw":
            return self.open_hex(ep.output_path, read_only=True)
        try:
            return self.win.open_any_file(str(ep.output_path))
        except Exception:  # noqa: BLE001
            return None

    def export_report(self, path: str = ""):
        ep = self._need()
        if ep is None:
            return None
        from ..firmware.checksum.blocks import correct
        from ..firmware.project.report import modification_report, modification_report_html
        self._flush_work(ep)
        if not path:
            path, _ = QFileDialog.getSaveFileName(self.win, "Export Modification Report",
                                                  str(ep.folder / "build" / f"{ep.name}_report.html"),
                                                  "HTML page (*.html);;Text (*.txt)")
            if not path:
                return None
        data = bytearray(ep.work_bytes())
        res = correct(data, ep.checksums) if ep.correct_on_build else ep.verify_checksums(bytes(data))
        p = Path(path)
        fn = modification_report_html if p.suffix.lower() in (".html", ".htm") else modification_report
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(fn(ep, bytes(data), res), encoding="utf-8")
        self._log(f"Modification report written: {p}")
        return p

    def export_patch(self, path: str = ""):
        ep = self._need()
        if ep is None:
            return None
        self._flush_work(ep)
        if not path:
            path, _ = QFileDialog.getSaveFileName(self.win, "Export Patch", str(ep.folder / "build" / f"{ep.name}.bps"),
                                                  "BPS patch (*.bps);;IPS patch (*.ips);;UPS patch (*.ups)")
            if not path:
                return None
        try:
            p = ep.export_patch(path, target="build")
        except Exception as e:  # noqa: BLE001 - PatchError (IPS > 16 MB ...) / OSError
            QMessageBox.warning(self.win, "Export Patch", str(e))
            return None
        self._log(f"Patch written: {p} ({p.stat().st_size:,} bytes, against the original, checksums corrected)")
        return p

    def import_patch(self, path: str = ""):
        ep = self._need()
        if ep is None:
            return None
        if not path:
            path, _ = QFileDialog.getOpenFileName(self.win, "Import Patch", self._start_dir(),
                                                  "Patches (*.ips *.bps *.ups);;All files (*)")
            if not path:
                return None
        self._flush_work(ep)
        try:
            saved = ep.import_patch(path)
            ep.save()
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self.win, "Import Patch", str(e))
            return None
        self._reload(ep.work_path)
        self._log(f"Patch {Path(path).name} applied to the original -> working copy"
                  + (f" (previous working copy saved as {saved.id})" if saved else ""))
        self._refresh_tree()
        return ep

    def build_settings(self):
        ep = self._need()
        if ep is None:
            return None
        from ..firmware.project.ui import BuildSettingsDialog
        dlg = BuildSettingsDialog(self.win, ep)
        self.last_dialog = dlg
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ep.save()
            self._refresh_tree()
        return dlg

    # ================================================================== Solution Explorer
    def _add_tree_nodes(self) -> None:
        win = self.win
        try:
            from .solution_ui import PROJECT_ROLE
        except ImportError:
            return
        tree = win.solution
        style = win.style()
        stack = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
        while stack:
            it = stack.pop()
            stack.extend(it.child(i) for i in range(it.childCount()))
            data = it.data(0, ROLE)
            if not data or data[0] != "project":
                continue
            key = it.data(0, PROJECT_ROLE)
            st = getattr(win, "_pstates", {}).get(key)
            project = st["project"] if st else None
            ep = self.project(project) if project is not None else None
            if ep is None or any((it.child(i).data(0, ROLE) or ("",))[0] == "ecuproj" for i in range(it.childCount())):
                continue

            def node(text, kind, path, tip, icon):
                n = QTreeWidgetItem([text])
                n.setData(0, ROLE, (kind, str(path)))
                n.setData(0, PROJECT_ROLE, key)
                n.setToolTip(0, tip)
                n.setIcon(0, style.standardIcon(icon))
                return n
            sp = style.StandardPixmap
            root = node("ECU Project", "ecuproj", ep.folder, "Double-click: Checksums", sp.SP_DriveHDIcon)
            if ep.original_path is not None:
                root.addChild(node(f"Original: {ep.original_path.name} (read-only)", "ecuproj_original",
                                   ep.original_path, f"SHA-256 {ep.original_sha256}", sp.SP_FileIcon))
            if ep.work_path is not None and ep.work_path.is_file():
                root.addChild(node(f"Working copy: {ep.work_path.name}", "ecuproj_work", ep.work_path,
                                   "Edit and save - checksums are recalculated on save", sp.SP_FileIcon))
            vn = node(f"Versions ({len(ep.versions)})", "ecuproj_versions", ep.folder, "Double-click: Versions",
                      sp.SP_DirIcon)
            for v in ep.versions:
                vn.addChild(node(f"{v.id} {v.name}", "ecuproj_version", ep.path(v.file), v.note or v.created,
                                 sp.SP_FileIcon))
            root.addChild(vn)
            verified = sum(1 for b in ep.checksums if b.verified)
            root.addChild(node(f"Checksums ({len(ep.checksums)} block(s), {verified} verified)", "ecuproj_checksums",
                               ep.folder, "Double-click: Checksums", sp.SP_FileDialogDetailedView))
            if ep.output_path.is_file():
                root.addChild(node(f"Build: {ep.output_path.name}", "ecuproj_output", ep.output_path,
                                   "Build output (checksums corrected)", sp.SP_DialogApplyButton))
            pos = 1 if it.childCount() and (it.child(0).data(0, ROLE) or ("",))[0] == "references" else 0
            it.insertChild(pos, root)
            root.setExpanded(True)

    def _on_tree_dclick(self, item, _col) -> None:
        data = item.data(0, ROLE)
        if not data or not str(data[0]).startswith("ecuproj"):
            return
        try:
            from .solution_ui import PROJECT_ROLE
            key = item.data(0, PROJECT_ROLE)
            st = getattr(self.win, "_pstates", {}).get(key)
            if st and st.get("project") is not None and st["project"] is not self.win.project:
                self.win.activate_project(st["project"])
        except Exception:  # noqa: BLE001
            pass
        kind, path = data[0], data[1]
        if kind in ("ecuproj", "ecuproj_checksums"):
            QTimer.singleShot(0, self.checksums)
        elif kind == "ecuproj_versions":
            QTimer.singleShot(0, self.versions)
        elif kind in ("ecuproj_original", "ecuproj_version"):
            self.open_hex(path, read_only=True)
        elif kind == "ecuproj_output":
            self.open_output()
        elif kind == "ecuproj_work":
            self.open_hex(path, read_only=False)


def install(win) -> None:
    win.firmware_project = FirmwareProjectFeature(win)
