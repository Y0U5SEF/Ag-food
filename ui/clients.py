"""
Clients management UI: CRUD, payments, and recommendations.
"""

from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit, QToolButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QDialog,
    QFormLayout, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QDialogButtonBox, QLabel, QSizePolicy
)
from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QStyle
from PyQt6.QtCore import QDate
from i18n.language_manager import language_manager as i18n


class ClientDialog(QDialog):
    def __init__(self, parent=None, *, full_name: str = "", phone: str = "", email: str = "",
                 address_line: str = "", city: str = "", state: str = "", postal_code: str = "",
                 country: str = "", dob: str = "", gender: str = "", notes: str = ""):
        super().__init__(parent)
        self.setWindowTitle(i18n.tr('clients.dialog.title'))
        v = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit(full_name)
        self.phone_edit = QLineEdit(phone)
        self.email_edit = QLineEdit(email)
        self.addr_edit = QLineEdit(address_line)
        self.city_edit = QLineEdit(city)
        self.state_edit = QLineEdit(state)
        self.postal_edit = QLineEdit(postal_code)
        self.country_edit = QLineEdit(country)
        self.dob_edit = QDateEdit(); self.dob_edit.setCalendarPopup(True)
        try:
            if dob:
                self.dob_edit.setDate(QDate.fromString(dob, 'yyyy-MM-dd'))
            else:
                self.dob_edit.setDate(QDate(2000,1,1))
        except Exception:
            self.dob_edit.setDate(QDate(2000,1,1))
        self.gender_cb = QComboBox(); self.gender_cb.addItems(["", "Male", "Female", "Other"])
        if gender:
            idx = self.gender_cb.findText(gender)
            if idx >= 0:
                self.gender_cb.setCurrentIndex(idx)
        self.notes_edit = QLineEdit(notes)
        form.addRow(QLabel(i18n.tr('clients.name')), self.name_edit)
        form.addRow(QLabel(i18n.tr('clients.phone')), self.phone_edit)
        form.addRow(QLabel(i18n.tr('clients.email')), self.email_edit)
        form.addRow(QLabel(i18n.tr('clients.address')), self.addr_edit)
        form.addRow(QLabel(i18n.tr('clients.city')), self.city_edit)
        form.addRow(QLabel(i18n.tr('clients.state')), self.state_edit)
        form.addRow(QLabel(i18n.tr('clients.postal')), self.postal_edit)
        form.addRow(QLabel(i18n.tr('clients.country')), self.country_edit)
        form.addRow(QLabel(i18n.tr('clients.dob')), self.dob_edit)
        form.addRow(QLabel(i18n.tr('clients.gender')), self.gender_cb)
        form.addRow(QLabel(i18n.tr('clients.notes')), self.notes_edit)
        v.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        v.addWidget(btns)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

    def values(self) -> dict:
        return {
            'full_name': self.name_edit.text().strip(),
            'phone': self.phone_edit.text().strip(),
            'email': self.email_edit.text().strip(),
            'address_line': self.addr_edit.text().strip(),
            'city': self.city_edit.text().strip(),
            'state': self.state_edit.text().strip(),
            'postal_code': self.postal_edit.text().strip(),
            'country': self.country_edit.text().strip(),
            'dob': self.dob_edit.date().toString('yyyy-MM-dd'),
            'gender': self.gender_cb.currentText(),
            'notes': self.notes_edit.text().strip(),
        }


class PaymentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(i18n.tr('clients.payment.title'))
        v = QVBoxLayout(self)
        form = QFormLayout()
        self.amount = QDoubleSpinBox(); self.amount.setRange(0.01, 1_000_000.0); self.amount.setDecimals(2)
        self.method = QLineEdit()
        self.reference = QLineEdit()
        form.addRow(QLabel(i18n.tr('clients.payment.amount')), self.amount)
        form.addRow(QLabel(i18n.tr('clients.payment.method')), self.method)
        form.addRow(QLabel(i18n.tr('clients.payment.reference')), self.reference)
        v.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        v.addWidget(btns)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

    def values(self) -> dict:
        return {
            'amount': float(self.amount.value()),
            'method': self.method.text().strip(),
            'reference': self.reference.text().strip(),
        }


class ClientsManagementWidget(QWidget):
    def __init__(self, db_manager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db_manager
        self._build_ui()
        if getattr(self.db, 'cursor', None) is not None:
            self.refresh()
        else:
            try:
                self.db.database_ready.connect(self.refresh)
            except Exception:
                pass

    def _build_ui(self):
        self.setObjectName("clientsRoot")
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(10)

        # Actions grid like Stock
        actions_grid = QGridLayout(); actions_grid.setContentsMargins(0,0,0,0); actions_grid.setHorizontalSpacing(8); actions_grid.setVerticalSpacing(6)
        def mkbtn(text: str) -> QToolButton:
            b = QToolButton(); b.setText(text); b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon); b.setIconSize(QSize(20,20)); b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed); return b
        self.btn_add = mkbtn(i18n.tr('stock.add'))
        self.btn_edit = mkbtn(i18n.tr('stock.edit'))
        self.btn_delete = mkbtn(i18n.tr('stock.delete'))
        self.btn_payment = mkbtn(i18n.tr('clients.payment.record'))
        self.btn_history = mkbtn(i18n.tr('clients.history'))
        self.btn_recommend = mkbtn(i18n.tr('clients.recommend'))
        buttons = [self.btn_add, self.btn_edit, self.btn_delete, self.btn_payment, self.btn_history, self.btn_recommend]
        for i,b in enumerate(buttons):
            actions_grid.addWidget(b, 0, i)
            actions_grid.setColumnStretch(i,1)
        # Ensure layout reserves space for 8 equal-width slots
        for c in range(8):
            actions_grid.setColumnStretch(c, 1)
        v.addLayout(actions_grid)

        # Filters row: search input
        filters = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText(i18n.tr('clients.search.placeholder'))
        self.search.textChanged.connect(self.refresh)
        filters.addWidget(self.search, 1)
        v.addLayout(filters)

        # Table
        self.table = QTableWidget(0, 8)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setHorizontalHeaderLabels([
            "#",
            i18n.tr('stock.col.id'),
            i18n.tr('clients.name'),
            i18n.tr('clients.phone'),
            i18n.tr('clients.email'),
            i18n.tr('clients.city'),
            i18n.tr('clients.balance'),
            i18n.tr('clients.last_purchase'),
        ])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        v.addWidget(self.table)

        # Wire actions
        self.btn_add.clicked.connect(self.on_add)
        self.btn_edit.clicked.connect(self.on_edit)
        self.btn_delete.clicked.connect(self.on_delete)
        self.btn_payment.clicked.connect(self.on_payment)
        self.btn_history.clicked.connect(self.on_history)
        self.btn_recommend.clicked.connect(self.on_recommend)
        self._attach_icons()

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
        self.btn_payment.setIcon(self._load_icon(["payment.svg","dollar.svg"], QStyle.StandardPixmap.SP_DialogApplyButton)); self.btn_payment.setIconSize(sz)
        self.btn_history.setIcon(self._load_icon(["history.svg"], QStyle.StandardPixmap.SP_BrowserReload)); self.btn_history.setIconSize(sz)
        self.btn_recommend.setIcon(self._load_icon(["star.svg","recommend.svg"], QStyle.StandardPixmap.SP_DialogHelpButton)); self.btn_recommend.setIconSize(sz)
        # Input icons
        si = self._load_icon(["search.svg","find.svg","magnify.svg"], QStyle.StandardPixmap.SP_FileDialogContentsView)
        if si and not si.isNull():
            self.search.addAction(si, QLineEdit.ActionPosition.LeadingPosition)

    def retranslate_ui(self):
        self.search.setPlaceholderText(i18n.tr('clients.search.placeholder'))
        self.btn_add.setText(i18n.tr('stock.add'))
        self.btn_edit.setText(i18n.tr('stock.edit'))
        self.btn_delete.setText(i18n.tr('stock.delete'))
        self.btn_payment.setText(i18n.tr('clients.payment.record'))
        self.btn_history.setText(i18n.tr('clients.history'))
        self.btn_recommend.setText(i18n.tr('clients.recommend'))
        self.table.setHorizontalHeaderLabels([
            "#",
            i18n.tr('stock.col.id'),
            i18n.tr('clients.name'),
            i18n.tr('clients.phone'),
            i18n.tr('clients.email'),
            i18n.tr('clients.city'),
            i18n.tr('clients.balance'),
            i18n.tr('clients.last_purchase'),
        ])
        self.table.setColumnHidden(1, False)

    def refresh(self):
        if getattr(self.db, 'cursor', None) is None:
            return
        query = self.search.text().strip()
        rows = self.db.list_clients(query if query else None)
        self.table.setRowCount(0)
        for cid, name, phone, email, city in rows:
            r = self.table.rowCount(); self.table.insertRow(r)
            idx_item = QTableWidgetItem(str(r+1)); idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 0, idx_item)
            id_item = QTableWidgetItem(str(cid)); id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 1, id_item)
            self.table.setItem(r, 2, QTableWidgetItem(name or ""))
            self.table.setItem(r, 3, QTableWidgetItem(phone or ""))
            self.table.setItem(r, 4, QTableWidgetItem(email or ""))
            self.table.setItem(r, 5, QTableWidgetItem(city or ""))
            # Balance
            bal = self.db.get_client_balance(cid)
            bal_item = QTableWidgetItem(f"{bal:,.2f}"); bal_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if bal > 0:
                bal_item.setForeground(Qt.GlobalColor.darkYellow)
            elif bal < 0:
                bal_item.setForeground(Qt.GlobalColor.darkGreen)
            self.table.setItem(r, 6, bal_item)
            # Last purchase date
            last_date = ""
            try:
                invs = self.db.list_client_invoices(cid)
                if invs:
                    last_date = str(invs[0][2])  # date field
            except Exception:
                pass
            self.table.setItem(r, 7, QTableWidgetItem(last_date))

    def _selected_client_id(self) -> Optional[int]:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 1)
        try:
            return int(item.text()) if item else None
        except Exception:
            return None

    def on_add(self):
        dlg = ClientDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            vals = dlg.values()
            if not vals['full_name']:
                QMessageBox.information(self, i18n.tr('msg.validation'), i18n.tr('msg.name_required'))
                return
            cid = self.db.add_client(**vals)
            if cid is None:
                QMessageBox.critical(self, i18n.tr('msg.error'), i18n.tr('clients.msg.failed_add'))
                return
            self.refresh()

    def on_edit(self):
        cid = self._selected_client_id()
        if cid is None:
            QMessageBox.information(self, i18n.tr('msg.validation'), i18n.tr('clients.msg.select_client'))
            return
        row = self.table.currentRow()
        # Could fetch full row but we will query DB for full record
        rec = self.db.get_client(cid)
        vals = {
            'full_name': rec[1] if rec else '',
            'phone': rec[2] if rec else '',
            'email': rec[3] if rec else '',
            'address_line': rec[4] if rec else '',
            'city': rec[5] if rec else '',
            'state': rec[6] if rec else '',
            'postal_code': rec[7] if rec else '',
            'country': rec[8] if rec else '',
            'dob': rec[9] if rec else '',
            'gender': rec[10] if rec else '',
            'notes': rec[11] if rec else '',
        }
        dlg = ClientDialog(self, **vals)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_vals = dlg.values()
            if not new_vals['full_name']:
                QMessageBox.information(self, i18n.tr('msg.validation'), i18n.tr('msg.name_required'))
                return
            ok = self.db.update_client(cid, **new_vals)
            if not ok:
                QMessageBox.critical(self, i18n.tr('msg.error'), i18n.tr('clients.msg.failed_update'))
                return
            self.refresh()

    def on_delete(self):
        cid = self._selected_client_id()
        if cid is None:
            QMessageBox.information(self, i18n.tr('msg.validation'), i18n.tr('clients.msg.select_client'))
            return
        reply = QMessageBox.question(self, i18n.tr('msg.confirm'), i18n.tr('clients.msg.confirm_delete'),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        ok = self.db.delete_client(cid)
        if not ok:
            QMessageBox.critical(self, i18n.tr('msg.error'), i18n.tr('clients.msg.failed_delete_in_use'))
            return
        self.refresh()

    def on_payment(self):
        cid = self._selected_client_id()
        if cid is None:
            QMessageBox.information(self, i18n.tr('msg.validation'), i18n.tr('clients.msg.select_client'))
            return
        dlg = PaymentDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            vals = dlg.values()
            if vals['amount'] <= 0:
                return
            pid = self.db.record_payment(cid, vals['amount'], method=vals['method'], reference=vals['reference'])
            if pid is None:
                QMessageBox.critical(self, i18n.tr('msg.error'), i18n.tr('clients.msg.failed_payment'))
                return
            self.refresh()

    def on_history(self):
        cid = self._selected_client_id()
        if cid is None:
            QMessageBox.information(self, i18n.tr('msg.validation'), i18n.tr('clients.msg.select_client'))
            return
        # Simple dialog showing invoices and payments counts
        invs = self.db.list_client_invoices(cid) or []
        pays = self.db.list_client_payments(cid) or []
        msg = i18n.tr('clients.history') + f"\n{len(invs)} invoices, {len(pays)} payments."
        QMessageBox.information(self, i18n.tr('clients.history'), msg)

    def on_recommend(self):
        cid = self._selected_client_id()
        if cid is None:
            QMessageBox.information(self, i18n.tr('msg.validation'), i18n.tr('clients.msg.select_client'))
            return
        recs = self.db.get_client_recommendations(cid, limit=10)
        if not recs:
            QMessageBox.information(self, i18n.tr('clients.recommend'), i18n.tr('clients.recommend.none'))
            return
        lines = [f"{name} — {qty:g}" for (_pid, name, qty) in recs]
        QMessageBox.information(self, i18n.tr('clients.recommend'), "\n".join(lines))
