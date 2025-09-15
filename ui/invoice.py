"""
Invoice generation UI: build invoices linked to clients and stock.
"""

from typing import Optional
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit, QToolButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QComboBox, QLabel,
    QSpinBox, QDoubleSpinBox, QDialog, QDialogButtonBox, QSizePolicy
)
from PyQt6.QtWidgets import QStyle
from i18n.language_manager import language_manager as i18n


class InvoiceWidget(QWidget):
    def __init__(self, db_manager, stock_widget: Optional[QWidget] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db_manager
        self.stock_widget = stock_widget
        self._build_ui()
        # Load initial data when DB is ready
        if getattr(self.db, 'cursor', None) is not None:
            self._load_clients()
            self._load_locations()
        else:
            try:
                self.db.database_ready.connect(self.on_db_ready)
            except Exception:
                pass

    def _build_ui(self):
        self.setObjectName('invoiceRoot')
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(10)

        # Actions grid (8 slots)
        actions = QGridLayout(); actions.setContentsMargins(0,0,0,0); actions.setHorizontalSpacing(8); actions.setVerticalSpacing(6)
        def mkbtn(text: str) -> QToolButton:
            b = QToolButton(); b.setText(text); b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon); b.setIconSize(QSize(20,20)); b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed); return b
        self.btn_new = mkbtn('New')
        self.btn_save = mkbtn('Save')
        self.btn_print = mkbtn('Print')
        self.btn_remove = mkbtn('Remove Item')
        for i,b in enumerate([self.btn_new, self.btn_save, self.btn_print, self.btn_remove]):
            actions.addWidget(b, 0, i); actions.setColumnStretch(i,1)
        for c in range(8):
            actions.setColumnStretch(c, 1)
        v.addLayout(actions)

        # Filters row: client, location, product search
        filters = QHBoxLayout()
        self.client_cb = QComboBox(); self.client_cb.setEditable(True)
        self.location_cb = QComboBox(); self.location_cb.setEditable(False)
        self.search = QLineEdit(); self.search.setPlaceholderText('Search or scan product...')
        self.search.returnPressed.connect(self.on_add_from_search)
        filters.addWidget(QLabel('Client'))
        filters.addWidget(self.client_cb, 1)
        filters.addWidget(QLabel('Location'))
        filters.addWidget(self.location_cb, 0)
        filters.addWidget(self.search, 1)
        v.addLayout(filters)

        # Items table
        self.table = QTableWidget(0, 6)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setHorizontalHeaderLabels([
            '#', 'Product', 'Qty', 'Unit Price', 'Line Total', 'Available'
        ])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        v.addWidget(self.table)

        # Totals row
        totals = QHBoxLayout()
        totals.addStretch(1)
        self.total_label = QLabel('Total: 0.00')
        totals.addWidget(self.total_label)
        v.addLayout(totals)

        # Wire actions
        self.btn_new.clicked.connect(self.on_new)
        self.btn_save.clicked.connect(self.on_save)
        self.btn_remove.clicked.connect(self.on_remove_item)
        self._attach_icons()

    # ----- Icons helpers -----
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
        self.btn_new.setIcon(self._load_icon(["add.svg","file_add.svg"], QStyle.StandardPixmap.SP_FileIcon)); self.btn_new.setIconSize(sz)
        self.btn_save.setIcon(self._load_icon(["save.svg"], QStyle.StandardPixmap.SP_DialogSaveButton)); self.btn_save.setIconSize(sz)
        self.btn_print.setIcon(self._load_icon(["print.svg"], QStyle.StandardPixmap.SP_DialogOkButton)); self.btn_print.setIconSize(sz)
        self.btn_remove.setIcon(self._load_icon(["delete.svg"], QStyle.StandardPixmap.SP_TrashIcon)); self.btn_remove.setIconSize(sz)
        si = self._load_icon(["search.svg","find.svg","magnify.svg"], QStyle.StandardPixmap.SP_FileDialogContentsView)
        if si and not si.isNull():
            self.search.addAction(si, QLineEdit.ActionPosition.LeadingPosition)

    # ----- Data loaders -----
    def on_db_ready(self):
        self._load_clients(); self._load_locations()

    def _load_clients(self):
        try:
            self.client_cb.clear(); self.client_cb.addItem('(Walk-in)', userData=None)
            for cid, name, phone, email, city in (self.db.list_clients() or []):
                label = name if not phone else f"{name} ({phone})"
                self.client_cb.addItem(label, userData=cid)
        except Exception:
            pass

    def _load_locations(self):
        try:
            self.location_cb.clear(); self.location_cb.addItem('All', userData=None)
            for lid, name, kind in (self.db.list_locations() or []):
                self.location_cb.addItem(name, userData=lid)
        except Exception:
            pass

    # ----- Line items -----
    def on_add_from_search(self):
        text = self.search.text().strip()
        if not text:
            return
        pid = None; name = None; price = 0.0; sku=None; barcode=None
        # Try barcode first
        try:
            rec = self.db.get_product_by_barcode(text)
            if rec:
                pid = int(rec[0]); barcode = rec[1]; sku = rec[2]; name = rec[3]; price = float(rec[7])
        except Exception:
            rec = None
        if not pid:
            # Fallback: search by name/code
            try:
                rows = self.db.list_products(text, None) or []
                if rows:
                    pid = int(rows[0][0]); barcode = rows[0][1]; sku = rows[0][2]; name = rows[0][3]; price = float(rows[0][6]) if len(rows[0])>6 else 0.0
            except Exception:
                pass
        if not pid:
            QMessageBox.information(self, 'Invoice', 'Product not found')
            return
        self._add_item_row(pid, name or '', 1, price, sku=sku, barcode=barcode)
        self.search.clear()

    def _add_item_row(self, product_id: int, name: str, qty: int | float, unit_price: float, *, sku: Optional[str] = None, barcode: Optional[str] = None):
        r = self.table.rowCount(); self.table.insertRow(r)
        idx_item = QTableWidgetItem(str(r+1)); idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter); self.table.setItem(r, 0, idx_item)
        prod_item = QTableWidgetItem(name); prod_item.setData(Qt.ItemDataRole.UserRole, product_id); prod_item.setToolTip(f"SKU: {sku or ''}  Barcode: {barcode or ''}"); self.table.setItem(r, 1, prod_item)
        qty_item = QTableWidgetItem(str(qty)); qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter); self.table.setItem(r, 2, qty_item)
        price_item = QTableWidgetItem(f"{unit_price:,.2f}"); price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter); self.table.setItem(r, 3, price_item)
        total_item = QTableWidgetItem(f"{qty*unit_price:,.2f}"); total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter); self.table.setItem(r, 4, total_item)
        # Available
        try:
            loc_id = self.location_cb.currentData()
            available = self.db.get_stock(product_id, loc_id)
            avail_item = QTableWidgetItem(str(available)); avail_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception:
            avail_item = QTableWidgetItem('')
        self.table.setItem(r, 5, avail_item)
        self._recompute_total()

    def _recompute_total(self):
        total = 0.0
        for r in range(self.table.rowCount()):
            try:
                qty = float(self.table.item(r,2).text().replace(',',''))
                price = float(self.table.item(r,3).text().replace(',',''))
                line = qty*price
                self.table.item(r,4).setText(f"{line:,.2f}")
                total += line
            except Exception:
                pass
        self.total_label.setText(f"Total: {total:,.2f}")

    def _collect_items(self):
        items = []
        for r in range(self.table.rowCount()):
            prod_item = self.table.item(r,1)
            if not prod_item:
                continue
            pid = prod_item.data(Qt.ItemDataRole.UserRole)
            try:
                qty = float(self.table.item(r,2).text().replace(',',''))
                price = float(self.table.item(r,3).text().replace(',',''))
            except Exception:
                qty = 0; price = 0
            items.append({'product_id': int(pid) if pid is not None else None, 'name': prod_item.text(), 'qty': qty, 'unit_price': price})
        return items

    # ----- Actions -----
    def on_new(self):
        self.table.setRowCount(0)
        self._recompute_total()

    def on_remove_item(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)
        # Re-index numbers
        for r in range(self.table.rowCount()):
            self.table.setItem(r, 0, QTableWidgetItem(str(r+1)))
        self._recompute_total()

    def on_save(self):
        items = self._collect_items()
        if not items:
            QMessageBox.information(self, 'Invoice', 'Add at least one item')
            return
        client_id = self.client_cb.currentData()
        client_name = self.client_cb.currentText().strip() if client_id is None else None
        loc_id = self.location_cb.currentData()
        inv_id = self.db.create_invoice(items, client_id=client_id, client_name=client_name, location_id=loc_id)
        if inv_id is None:
            QMessageBox.critical(self, 'Invoice', 'Failed to create invoice (insufficient stock?)')
            return
        QMessageBox.information(self, 'Invoice', f'Invoice #{inv_id} created successfully')
        self.on_new()

    # ----- i18n -----
    def retranslate_ui(self):
        # This can be expanded to use i18n keys; keeping simple for now
        self.search.setPlaceholderText('Search or scan product...')
        self.total_label.setText(self.total_label.text())

