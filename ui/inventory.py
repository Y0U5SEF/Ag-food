"""
Inventory Control UI: Manage locations with a styled, striped table.
"""

from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QToolButton, QDialog, QFormLayout, QLineEdit,
    QDialogButtonBox, QLabel, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QStyle
from i18n.language_manager import language_manager as i18n


class InventoryControlWidget(QWidget):
    def __init__(self, db_manager, stock_widget: Optional[QWidget] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db_manager
        self.stock_widget = stock_widget
        self._build_ui()
        # Defer initial load until DB is ready
        if getattr(self.db, 'cursor', None) is not None:
            self.refresh()
        else:
            try:
                self.db.database_ready.connect(self.on_db_ready)
            except Exception:
                pass

    def _build_ui(self):
        self.setObjectName("inventoryRoot")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Top actions grid
        actions_grid = QGridLayout(); actions_grid.setContentsMargins(0,0,0,0); actions_grid.setHorizontalSpacing(8); actions_grid.setVerticalSpacing(6)
        def mkbtn(text: str) -> QToolButton:
            b = QToolButton(); b.setText(text); b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon); b.setIconSize(QSize(20,20)); b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed); return b
        self.btn_add = mkbtn(i18n.tr('stock.add'))
        self.btn_edit = mkbtn(i18n.tr('stock.edit'))
        self.btn_delete = mkbtn(i18n.tr('stock.delete'))
        for i,b in enumerate([self.btn_add, self.btn_edit, self.btn_delete]):
            actions_grid.addWidget(b, 0, i); actions_grid.setColumnStretch(i,1)
        # Reserve 8 equal-width slots so fewer buttons don't fill the full width
        for c in range(8):
            actions_grid.setColumnStretch(c, 1)
        layout.addLayout(actions_grid)

        # Filters row
        filters = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText('Search locations...')
        self.search.textChanged.connect(self.refresh)
        filters.addWidget(self.search, 1)
        layout.addLayout(filters)

        # Locations table
        self.table = QTableWidget(0, 3)
        self.table.setAlternatingRowColors(True)
        self.table.setHorizontalHeaderLabels([
            i18n.tr('stock.col.id'),
            i18n.tr('stock.col.name'),
            'Type',
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)

        # Wire
        self.btn_add.clicked.connect(self.on_add)
        self.btn_edit.clicked.connect(self.on_edit)
        self.btn_delete.clicked.connect(self.on_delete)
        self._attach_icons()

        # Initial load is handled after DB ready

    def refresh(self):
        try:
            rows = self.db.list_locations() or []
        except Exception:
            rows = []
        self.table.setRowCount(0)
        q = (self.search.text().strip().lower() if hasattr(self, 'search') and self.search is not None else '')
        for lid, name, kind in rows:
            if q and q not in (name or '').lower() and q not in (kind or '').lower():
                continue
            r = self.table.rowCount(); self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(lid)))
            self.table.setItem(r, 1, QTableWidgetItem(name))
            self.table.setItem(r, 2, QTableWidgetItem(kind or ''))

    def _selected_location_id(self) -> Optional[int]:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        try:
            return int(item.text()) if item else None
        except Exception:
            return None

    def _edit_dialog(self, *, title: str, name: str = "", kind: str = "") -> tuple[bool, str, str]:
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        v = QVBoxLayout(dlg)
        form = QFormLayout()
        name_edit = QLineEdit(name)
        kind_edit = QLineEdit(kind)
        form.addRow(QLabel(i18n.tr('stock.dialog.name')), name_edit)
        form.addRow(QLabel('Type'), kind_edit)
        v.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        v.addWidget(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        ok = dlg.exec() == QDialog.DialogCode.Accepted
        return ok, name_edit.text().strip(), kind_edit.text().strip()

    def on_add(self):
        ok, name, kind = self._edit_dialog(title=i18n.tr('stock.add'))
        if not ok:
            return
        if not name:
            QMessageBox.information(self, i18n.tr('msg.validation'), i18n.tr('msg.name_required'))
            return
        lid = self.db.add_location(name, kind)
        if lid is None:
            QMessageBox.critical(self, i18n.tr('msg.error'), 'Failed to add location (duplicate name?)')
            return
        self.refresh()
        self._refresh_stock_locations()

    def on_edit(self):
        lid = self._selected_location_id()
        if lid is None:
            QMessageBox.information(self, i18n.tr('msg.validation'), 'Select a location to edit')
            return
        row = self.table.currentRow()
        current_name = self.table.item(row, 1).text() if row >= 0 else ''
        current_kind = self.table.item(row, 2).text() if row >= 0 else ''
        ok, name, kind = self._edit_dialog(title=i18n.tr('stock.edit'), name=current_name, kind=current_kind)
        if not ok:
            return
        if not name:
            QMessageBox.information(self, i18n.tr('msg.validation'), i18n.tr('msg.name_required'))
            return
        ok2 = self.db.update_location(lid, name, kind)
        if not ok2:
            QMessageBox.critical(self, i18n.tr('msg.error'), 'Failed to update location (duplicate name?)')
            return
        self.refresh()
        self._refresh_stock_locations()

    def on_delete(self):
        lid = self._selected_location_id()
        if lid is None:
            QMessageBox.information(self, i18n.tr('msg.validation'), 'Select a location to delete')
            return
        reply = QMessageBox.question(self, i18n.tr('msg.confirm'), 'Delete selected location?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        ok = self.db.delete_location(lid)
        if not ok:
            QMessageBox.critical(self, i18n.tr('msg.error'), 'Cannot delete a location that has stock movements.')
            return
        self.refresh()
        self._refresh_stock_locations()

    def _refresh_stock_locations(self):
        try:
            if self.stock_widget is not None and hasattr(self.stock_widget, '_load_locations'):
                self.stock_widget._load_locations()
        except Exception:
            pass

    def on_db_ready(self):
        self.refresh()

    def _get_icons_path(self) -> str:
        try:
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            return os.path.join(project_root, "icons")
        except Exception:
            return "icons"

    def _load_icon(self, candidates: list[str], fallback_sp: QStyle.StandardPixmap | None = None):
        import os
        base = self._get_icons_path()
        for name in candidates:
            p = os.path.join(base, name)
            if os.path.exists(p):
                from PyQt6.QtGui import QIcon
                return QIcon(p)
        if fallback_sp is not None:
            try:
                style = self.style(); from PyQt6.QtGui import QIcon; return style.standardIcon(fallback_sp)
            except Exception:
                pass
        from PyQt6.QtGui import QIcon
        return QIcon()

    def _attach_icons(self):
        sz = QSize(18,18)
        self.btn_add.setIcon(self._load_icon(["add.svg"], QStyle.StandardPixmap.SP_DialogYesButton)); self.btn_add.setIconSize(sz)
        self.btn_edit.setIcon(self._load_icon(["Edit.svg"], QStyle.StandardPixmap.SP_FileDialogDetailedView)); self.btn_edit.setIconSize(sz)
        self.btn_delete.setIcon(self._load_icon(["delete.svg"], QStyle.StandardPixmap.SP_TrashIcon)); self.btn_delete.setIconSize(sz)
        # Search input icon
        si = self._load_icon(["search.svg","find.svg","magnify.svg"], QStyle.StandardPixmap.SP_FileDialogContentsView)
        if si and not si.isNull():
            self.search.addAction(si, QLineEdit.ActionPosition.LeadingPosition)
