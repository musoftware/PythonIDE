"""TabControl on the design surface: a tab bar, a page frame and a transparent *client* widget (the page area)
that hosts the previews of the controls on the pages (the designer puts child previews into ``.client``).

Children of a TabControl have ``TabPage`` = page index; their Left / Top are relative to the page's client
area, TAB_PAGE_X / TAB_PAGE_Y pixels inside the control (radide/controls.py)."""
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QFrame, QTabBar, QWidget

from radide.components.classic import apply_classic, prepare
from radide.controls import TAB_PAGE_X, TAB_PAGE_Y, split_items


class TabControlPreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bar = QTabBar(self)
        self.bar.setDrawBase(False)
        self.bar.setExpanding(False)
        self.page = QFrame(self)
        self.page.setFrameShape(QFrame.Shape.StyledPanel)
        self.page.setObjectName("rad_page")
        self.page.setStyleSheet("#rad_page { background:#FCFCFE; border:1px solid #919B9C; }")
        self.client = QWidget(self)
        self.client.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.bar.raise_()

    def set_tabs(self, captions: list, current: int) -> None:
        self.bar.blockSignals(True)
        while self.bar.count() > len(captions):
            self.bar.removeTab(self.bar.count() - 1)
        for i, text in enumerate(captions):
            if i < self.bar.count():
                self.bar.setTabText(i, text)
            else:
                self.bar.addTab(text)
        if 0 <= current < self.bar.count():
            self.bar.setCurrentIndex(current)
        self.bar.blockSignals(False)
        self._layout()

    def tab_at(self, pos: QPoint) -> int:
        """Index of the tab under *pos* (in this widget's coordinates), or -1."""
        return self.bar.tabAt(pos - self.bar.pos())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._layout()

    def _layout(self):
        w, h = self.width(), self.height()
        bh = min(self.bar.sizeHint().height(), TAB_PAGE_Y)
        self.bar.setGeometry(2, TAB_PAGE_Y - bh, max(10, w - 4), bh)
        self.page.setGeometry(0, TAB_PAGE_Y - 2, w, max(4, h - TAB_PAGE_Y + 2))
        self.client.setGeometry(TAB_PAGE_X, TAB_PAGE_Y, max(1, w - 2 * TAB_PAGE_X),
                                max(1, h - TAB_PAGE_Y - TAB_PAGE_X))


def create(parent, props, ctx):
    return prepare(TabControlPreview(parent))


def _tabs(w, p, ctx):
    w.set_tabs(split_items(p.get("TabPages", "")) or ["TabPage1"], int(p.get("SelectedIndex", 0) or 0))


def apply(w, props, ctx):
    apply_classic(w, props, ctx, special=_tabs)
