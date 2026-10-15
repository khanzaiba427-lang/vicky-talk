"""Notes view: objectives (WORK/PERSONAL) backed by memory.Memory."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLabel,
    QPushButton, QLineEdit, QComboBox, QCheckBox, QProgressBar,
    QScrollArea, QButtonGroup, QMessageBox,
)

from memory import Memory
from theme import GOLD


class _ObjectiveCard(QFrame):
    """One objective card: checkbox, title, tag pill, progress bar, meta."""

    toggled = Signal(int, bool)  # objective id, completed?

    def __init__(self, obj: dict, parent=None):
        super().__init__(parent)
        self._id = obj.get("id")
        self.setProperty("card", True)
        completed = str(obj.get("status", "pending")).lower() == "completed"
        if completed:
            # dim the card, like the design's .ncard.done
            self.setStyleSheet("QFrame[card=\"true\"] { background-color: #0d0904; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        top = QHBoxLayout()
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(completed)
        self.checkbox.stateChanged.connect(self._on_check)
        top.addWidget(self.checkbox)
        top.addStretch(1)
        tag = str(obj.get("tag", "WORK")).upper()
        tag_lbl = QLabel(tag)
        tag_lbl.setProperty("pill", True)
        top.addWidget(tag_lbl)
        layout.addLayout(top)

        title = QLabel(str(obj.get("title", "")))
        title.setWordWrap(True)
        title.setStyleSheet(
            "font-size: 14.5px;"
            + ("text-decoration: line-through; color: #a89a7c;" if completed else "")
        )
        layout.addWidget(title)

        progress = int(obj.get("progress", 0) or 0)
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(max(0, min(100, progress)))
        bar.setTextVisible(False)
        layout.addWidget(bar)

        meta = QLabel(str(obj.get("meta", "") or f"{progress}%"))
        meta.setStyleSheet(f"color: {GOLD['dim']}; font-size: 11px;")
        layout.addWidget(meta)

    def _on_check(self, state: int) -> None:
        self.toggled.emit(self._id, state == Qt.CheckState.Checked.value)


class NotesView(QWidget):
    """Objectives list with add-box and ALL/WORK/PERSONAL + PENDING/COMPLETED filters."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mem = Memory()
        self._tag_filter = "ALL"       # ALL | WORK | PERSONAL
        self._status_filter = "PENDING"  # PENDING | COMPLETED

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(14)

        # ---- add row ----
        add_row = QHBoxLayout()
        add_row.setSpacing(10)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText(
            "+ Add new objective...  (e.g. 'Kal subah apartment book karna hai')"
        )
        self.title_edit.returnPressed.connect(self._add_objective)
        self.tag_combo = QComboBox()
        self.tag_combo.addItems(["WORK", "PERSONAL"])
        self.tag_combo.setFixedWidth(130)
        self.add_button = QPushButton("ADD")
        self.add_button.setProperty("gold", True)
        self.add_button.clicked.connect(self._add_objective)
        add_row.addWidget(self.title_edit, 1)
        add_row.addWidget(self.tag_combo, 0)
        add_row.addWidget(self.add_button, 0)
        layout.addLayout(add_row)

        # ---- filters ----
        filters = QHBoxLayout()
        filters.setSpacing(8)
        self._tag_group = QButtonGroup(self)
        self._tag_group.setExclusive(True)
        for label in ("ALL", "WORK", "PERSONAL"):
            btn = QPushButton(label)
            btn.setProperty("chip", True)
            btn.setCheckable(True)
            btn.setChecked(label == "ALL")
            btn.clicked.connect(lambda _c, l=label: self._set_tag_filter(l))
            self._tag_group.addButton(btn)
            filters.addWidget(btn)
        filters.addSpacing(12)
        self._status_group = QButtonGroup(self)
        self._status_group.setExclusive(True)
        for label in ("PENDING", "COMPLETED"):
            btn = QPushButton(label)
            btn.setProperty("chip", True)
            btn.setCheckable(True)
            btn.setChecked(label == "PENDING")
            btn.clicked.connect(lambda _c, l=label: self._set_status_filter(l))
            self._status_group.addButton(btn)
            filters.addWidget(btn)
        filters.addStretch(1)
        layout.addLayout(filters)

        # ---- cards ----
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._cards_host = QWidget()
        self._cards_grid = QGridLayout(self._cards_host)
        self._cards_grid.setSpacing(14)
        self._cards_grid.setContentsMargins(2, 2, 2, 2)
        scroll.setWidget(self._cards_host)
        layout.addWidget(scroll, 1)

    # ------------------------------------------------------------------ data
    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        """Rebuild cards from memory, honouring the active filters."""
        # clear grid
        while self._cards_grid.count():
            item = self._cards_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        try:
            if self._status_filter == "ALL":
                objs = self._mem.list_objectives()
            else:
                objs = self._mem.list_objectives(status=self._status_filter.lower())
        except Exception as exc:  # backend hiccup -> show nothing, no crash
            objs = []
            print(f"[notes] list_objectives failed: {exc}")

        if self._tag_filter != "ALL":
            objs = [o for o in objs if str(o.get("tag", "")).upper() == self._tag_filter]

        for i, obj in enumerate(objs):
            card = _ObjectiveCard(obj)
            card.toggled.connect(self._on_toggled)
            self._cards_grid.addWidget(card, i // 3, i % 3)
        # keep grid left-aligned when the last row is short
        self._cards_grid.setColumnStretch(3, 1)

    # ---------------------------------------------------------------- events
    def _add_objective(self) -> None:
        title = self.title_edit.text().strip()
        if not title:
            return
        try:
            self._mem.add_objective(title, tag=self.tag_combo.currentText())
        except Exception as exc:
            QMessageBox.warning(self, "Could not save", f"Objective was not saved:\n{exc}")
            return
        self.title_edit.clear()
        self.refresh()

    def _on_toggled(self, obj_id: int, completed: bool) -> None:
        try:
            self._mem.update_objective(
                obj_id, status="completed" if completed else "pending"
            )
        except Exception as exc:
            QMessageBox.warning(self, "Could not update", f"Status was not updated:\n{exc}")
        self.refresh()

    def _set_tag_filter(self, label: str) -> None:
        self._tag_filter = label
        self.refresh()

    def _set_status_filter(self, label: str) -> None:
        self._status_filter = label
        self.refresh()
