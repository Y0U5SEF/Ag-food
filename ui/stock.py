"""
Stock management UI: searchable table with CRUD and stock adjustments.
"""

from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit, QPushButton, QToolButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QDialog,
    QFormLayout, QSpinBox, QDoubleSpinBox, QDialogButtonBox, QLabel, QStyle,
    QComboBox, QDateEdit, QFileDialog, QSizePolicy
)
from PyQt6.QtCore import QSize, QDate
from PyQt6.QtGui import QIcon
from PyQt6.QtGui import QIcon
from i18n.language_manager import language_manager as i18n


class ProductDialog(QDialog):
    """Dialog for adding/editing a product with basic and advanced fields."""

    def __init__(self, parent=None, db=None, *, name: str = "", description: str = "",
                 quantity: int = 0, price: float = 0.0, barcode: str = "", sku: str = "",
                 category: str = "", reorder_point: int = 0, supplier_id=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle(i18n.tr('nav.stock_management'))
        layout = QVBoxLayout(self)
        # Increase default width for better usability
        try:
            self.setMinimumWidth(500)
        except Exception:
            pass

        # Basic fields
        form = QFormLayout()
        self.barcode_edit = QLineEdit(barcode)
        self.sku_edit = QLineEdit(sku)
        self.name_edit = QLineEdit(name)
        self.category_cb = QComboBox(); self.category_cb.setEditable(True)
        self._load_default_categories(category)
        self.qty_spin = QSpinBox(); self.qty_spin.setRange(0, 10_000_000); self.qty_spin.setValue(max(0, quantity))
        self.uom_cb = QComboBox(); self.uom_cb.addItems(["pcs", "box", "kg", "g", "liter", "ml"])
        self.cost_spin = QDoubleSpinBox(); self.cost_spin.setRange(0.0, 1_000_000.0); self.cost_spin.setDecimals(2)
        self.price_spin = QDoubleSpinBox(); self.price_spin.setRange(0.0, 1_000_000.0); self.price_spin.setDecimals(2); self.price_spin.setValue(max(0.0, float(price)))
        self.expiry_edit = QDateEdit(); self.expiry_edit.setCalendarPopup(True); self.expiry_edit.setDate(QDate.currentDate())
        self.location_cb = QComboBox(); self._load_locations()

        form.addRow(QLabel(i18n.tr('stock.form.barcode')), self.barcode_edit)
        form.addRow(QLabel(i18n.tr('stock.form.sku')), self.sku_edit)
        form.addRow(QLabel(i18n.tr('stock.form.name')), self.name_edit)
        form.addRow(QLabel(i18n.tr('stock.form.category')), self.category_cb)
        form.addRow(QLabel(i18n.tr('stock.form.quantity')), self.qty_spin)
        form.addRow(QLabel(i18n.tr('stock.form.unit')), self.uom_cb)
        form.addRow(QLabel(i18n.tr('stock.form.cost_price')), self.cost_spin)
        form.addRow(QLabel(i18n.tr('stock.form.selling_price')), self.price_spin)
        form.addRow(QLabel(i18n.tr('stock.form.expiry_date')), self.expiry_edit)
        form.addRow(QLabel(i18n.tr('stock.form.location')), self.location_cb)

        layout.addLayout(form)

        # Advanced section
        self.advanced_btn = QPushButton(i18n.tr('stock.more_details.show'))
        self.advanced_btn.setCheckable(True)
        self.advanced_btn.setChecked(False)
        self.advanced_btn.toggled.connect(self._toggle_advanced)
        layout.addWidget(self.advanced_btn)

        self.advanced_widget = QWidget(); adv = QFormLayout(self.advanced_widget)
        self.reorder_spin = QSpinBox(); self.reorder_spin.setRange(0, 1_000_000); self.reorder_spin.setValue(max(0, reorder_point))
        self.supplier_cb = QComboBox(); self._load_suppliers(supplier_id)
        self.batch_edit = QLineEdit()
        self.mfg_edit = QDateEdit(); self.mfg_edit.setCalendarPopup(True); self.mfg_edit.setDate(QDate.currentDate())
        self.desc_edit = QLineEdit(description)
        adv.addRow(QLabel(i18n.tr('stock.form.reorder_level')), self.reorder_spin)
        adv.addRow(QLabel(i18n.tr('stock.form.supplier')), self.supplier_cb)
        adv.addRow(QLabel(i18n.tr('stock.form.batch_no')), self.batch_edit)
        adv.addRow(QLabel(i18n.tr('stock.form.mfg_date')), self.mfg_edit)
        adv.addRow(QLabel(i18n.tr('stock.form.notes')), self.desc_edit)
        self.advanced_widget.setVisible(False)
        layout.addWidget(self.advanced_widget)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _toggle_advanced(self, checked: bool):
        self.advanced_btn.setText(i18n.tr('stock.more_details.show') if not checked else i18n.tr('stock.more_details.hide'))
        self.advanced_widget.setVisible(checked)

    def _load_default_categories(self, current: str = ""):
        cats = ["Beverages", "Cleaning", "Snacks", "Dairy", "Produce", "Frozen", "Household", "Personal Care", "Other"]
        self.category_cb.addItems(cats)
        if current:
            if self.category_cb.findText(current) == -1:
                self.category_cb.addItem(current)
            self.category_cb.setCurrentText(current)

    def _load_locations(self):
        try:
            self.location_cb.clear()
            if self.db:
                for lid, name, kind in (self.db.list_locations() or []):
                    self.location_cb.addItem(name, userData=lid)
        except Exception:
            pass

    def _load_suppliers(self, supplier_id=None):
        try:
            self.supplier_cb.clear(); self.supplier_cb.addItem("(None)", userData=None)
            if self.db:
                for sid, name, info in (self.db.list_suppliers() or []):
                    self.supplier_cb.addItem(name, userData=sid)
                if supplier_id is not None:
                    idx = self.supplier_cb.findData(supplier_id)
                    if idx >= 0:
                        self.supplier_cb.setCurrentIndex(idx)
        except Exception:
            pass

    def get_values(self) -> dict:
        return {
            'barcode': self.barcode_edit.text().strip(),
            'sku': self.sku_edit.text().strip(),
            'name': self.name_edit.text().strip(),
            'category': self.category_cb.currentText().strip(),
            'quantity': int(self.qty_spin.value()),
            'uom': self.uom_cb.currentText(),
            'cost_price': float(self.cost_spin.value()),
            'selling_price': float(self.price_spin.value()),
            'expiry': self.expiry_edit.date().toString('yyyy-MM-dd') if self.expiry_edit.date() else None,
            'location_id': self.location_cb.currentData(),
            'reorder_point': int(self.reorder_spin.value()),
            'supplier_id': self.supplier_cb.currentData(),
            'batch_no': self.batch_edit.text().strip(),
            'mfg_date': self.mfg_edit.date().toString('yyyy-MM-dd') if self.mfg_edit.date() else None,
            'description': self.desc_edit.text().strip(),
        }


class StockManagementWidget(QWidget):
    def __init__(self, db_manager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db_manager
        self._build_ui()
        # Delay initial load until DB is ready, if needed
        if getattr(self.db, 'cursor', None) is not None:
            self._set_actions_enabled(True)
            self.refresh()
        else:
            try:
                self.db.database_ready.connect(self.on_db_ready)
            except Exception:
                pass

    def _build_ui(self):
        self.setObjectName("stockRoot")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Top controls split into two rows
        # Row 1: action buttons
        actions_grid = QGridLayout()
        # No left/right padding on the buttons container
        actions_grid.setContentsMargins(0, 0, 0, 0)
        # Explicit gaps between buttons
        actions_grid.setHorizontalSpacing(8)
        actions_grid.setVerticalSpacing(6)

        # Create tool buttons so text can sit under icon
        def mkbtn(text: str, obj: str) -> QToolButton:
            b = QToolButton()
            b.setText(text)
            b.setObjectName(obj)
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            b.setIconSize(QSize(20, 20))
            # Let buttons expand to maximum possible width within their column
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            return b

        self.btn_add = mkbtn(i18n.tr('stock.add'), "actionAdd")
        self.btn_edit = mkbtn(i18n.tr('stock.edit'), "actionEdit")
        self.btn_delete = mkbtn(i18n.tr('stock.delete'), "actionDelete")
        self.btn_restock = mkbtn(i18n.tr('stock.restock'), "actionRestock")
        self.btn_consume = mkbtn(i18n.tr('stock.consume'), "actionConsume")
        self.btn_adjust = mkbtn(i18n.tr('stock.btn.adjust'), "actionAdjust")
        self.btn_transfer = mkbtn(i18n.tr('stock.btn.transfer'), "actionTransfer")
        self.btn_batch = mkbtn(i18n.tr('stock.btn.batch'), "actionBatch")
        self.btn_reorder = mkbtn(i18n.tr('stock.btn.reorder'), "actionReorder")
        self.btn_stocktake = mkbtn(i18n.tr('stock.btn.stocktake'), "actionStocktake")
        self.btn_history = mkbtn(i18n.tr('stock.btn.history'), "actionHistory")
        self.btn_export = mkbtn(i18n.tr('stock.btn.export'), "actionExport")

        buttons = [
            self.btn_add, self.btn_edit, self.btn_delete, self.btn_restock,
            self.btn_consume, self.btn_adjust, self.btn_transfer, self.btn_batch,
            self.btn_reorder, self.btn_stocktake, self.btn_history, self.btn_export,
        ]
        for i, b in enumerate(buttons):
            row = i // 8
            col = i % 8
            actions_grid.addWidget(b, row, col)
        # Ensure up to 8 columns expand evenly across the row
        for c in range(8):
            actions_grid.setColumnStretch(c, 1)

        # Row 2: barcode + search inputs
        filters = QHBoxLayout()
        self.location_combo = QComboBox()
        self.location_combo.addItem(i18n.tr('stock.all_locations'), userData=None)
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText(i18n.tr('stock.scan.placeholder'))
        self.barcode_input.returnPressed.connect(self.on_scan_barcode)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(i18n.tr('stock.search.placeholder'))
        filters.addWidget(self.location_combo)
        filters.addWidget(self.barcode_input, 1)
        filters.addWidget(self.search_edit, 1)

        # Object names for targeted styling
        self.btn_add.setObjectName("actionAdd")
        self.btn_edit.setObjectName("actionEdit")
        self.btn_delete.setObjectName("actionDelete")
        self.btn_restock.setObjectName("actionRestock")
        self.btn_consume.setObjectName("actionConsume")

        # Load icons and attach to inputs/buttons
        self._attach_icons()
        layout.addLayout(actions_grid)
        layout.addLayout(filters)

        # Table: add index column (#) on the far left; keep ID hidden in column 1
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "#",                                  # 0 index
            i18n.tr('stock.col.id'),               # 1 (hidden)
            i18n.tr('stock.col.code'),             # 2 Barcode/SKU
            i18n.tr('stock.col.name'),             # 3
            i18n.tr('stock.col.category'),         # 4
            i18n.tr('stock.col.quantity'),         # 5
            i18n.tr('stock.col.expiry'),           # 6
            i18n.tr('stock.col.price'),            # 7
            i18n.tr('stock.col.location'),         # 8
            i18n.tr('stock.col.status'),           # 9
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # index
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # hidden id
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # code
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)           # name
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # category
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # qty
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # expiry
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # price
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)  # location
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)           # status
        self.table.setColumnHidden(1, True)
        layout.addWidget(self.table)
        # Row double-click opens details
        self.table.itemDoubleClicked.connect(self.on_row_double_clicked)

        # Signals
        self.search_edit.textChanged.connect(self.refresh)
        self.location_combo.currentIndexChanged.connect(self.refresh)
        self.btn_add.clicked.connect(self.on_add)
        self.btn_edit.clicked.connect(self.on_edit)
        self.btn_delete.clicked.connect(self.on_delete)
        self.btn_restock.clicked.connect(lambda: self.on_adjust_stock(+1))
        self.btn_consume.clicked.connect(lambda: self.on_adjust_stock(-1))
        self.btn_adjust.clicked.connect(self.on_adjust_dialog)
        self.btn_transfer.clicked.connect(self.on_transfer_dialog)
        self.btn_batch.clicked.connect(self.on_batch_dialog)
        self.btn_reorder.clicked.connect(self.on_reorder_dialog)
        self.btn_stocktake.clicked.connect(self.on_stocktake_dialog)
        self.btn_history.clicked.connect(self.on_history_dialog)
        self.btn_export.clicked.connect(self.on_export_dialog)

        # Disable actions until DB is ready
        ready = getattr(self.db, 'cursor', None) is not None
        for w in (self.btn_add, self.btn_edit, self.btn_delete, self.btn_restock, self.btn_consume):
            w.setEnabled(ready)
        for w in (self.btn_adjust, self.btn_transfer, self.btn_batch, self.btn_reorder, self.btn_stocktake, self.btn_history, self.btn_export, self.location_combo):
            w.setEnabled(ready)

        # Ensure barcode input is focused and ready for scanning
        self._focus_barcode()

    def _set_actions_enabled(self, enabled: bool):
        for w in (self.btn_add, self.btn_edit, self.btn_delete, self.btn_restock, self.btn_consume, self.btn_adjust, self.btn_transfer, self.btn_history, self.location_combo):
            w.setEnabled(enabled)

    def on_db_ready(self):
        self._set_actions_enabled(True)
        self.refresh()
        self._focus_barcode()
        self._load_locations()

    def _get_icons_path(self) -> str:
        try:
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            return os.path.join(project_root, "icons")
        except Exception:
            return "icons"

    def _load_icon(self, candidates: list[str], fallback_sp: QStyle.StandardPixmap | None = None) -> QIcon:
        import os
        base = self._get_icons_path()
        for name in candidates:
            p = os.path.join(base, name)
            if os.path.exists(p):
                return QIcon(p)
        if fallback_sp is not None:
            try:
                style = self.style()
                return style.standardIcon(fallback_sp)
            except Exception:
                pass
        return QIcon()

    def _attach_icons(self):
        # Buttons
        sz = QSize(18, 18)
        # Use user-provided icons in icons/ directory
        self.btn_add.setIcon(self._load_icon(["add.svg"], QStyle.StandardPixmap.SP_DialogYesButton))
        self.btn_add.setIconSize(sz)
        self.btn_edit.setIcon(self._load_icon(["Edit.svg"], QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.btn_edit.setIconSize(sz)
        self.btn_delete.setIcon(self._load_icon(["delete.svg"], QStyle.StandardPixmap.SP_TrashIcon))
        self.btn_delete.setIconSize(sz)
        self.btn_restock.setIcon(self._load_icon(["up.svg"], QStyle.StandardPixmap.SP_ArrowUp))
        self.btn_restock.setIconSize(sz)
        self.btn_consume.setIcon(self._load_icon(["down.svg"], QStyle.StandardPixmap.SP_ArrowDown))
        self.btn_consume.setIconSize(sz)
        # Additional action icons
        self.btn_adjust.setIcon(self._load_icon(["adjust.svg"], QStyle.StandardPixmap.SP_BrowserReload))
        self.btn_adjust.setIconSize(sz)
        self.btn_transfer.setIcon(self._load_icon(["transfer.svg"], QStyle.StandardPixmap.SP_ArrowRight))
        self.btn_transfer.setIconSize(sz)
        self.btn_batch.setIcon(self._load_icon(["expiry.svg"], QStyle.StandardPixmap.SP_FileDialogInfoView))
        self.btn_batch.setIconSize(sz)
        self.btn_reorder.setIcon(self._load_icon(["reorder.svg"], QStyle.StandardPixmap.SP_DialogYesButton))
        self.btn_reorder.setIconSize(sz)
        self.btn_stocktake.setIcon(self._load_icon(["stocktake.svg"], QStyle.StandardPixmap.SP_DialogResetButton))
        self.btn_stocktake.setIconSize(sz)
        self.btn_history.setIcon(self._load_icon(["history.svg"], QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.btn_history.setIconSize(sz)
        self.btn_export.setIcon(self._load_icon(["export.svg"], QStyle.StandardPixmap.SP_DialogSaveButton))
        self.btn_export.setIconSize(sz)

        # Inputs with leading icons
        bi = self._load_icon(["barcode.svg", "qr.svg", "scan.svg"], QStyle.StandardPixmap.SP_DialogOpenButton)
        if not bi.isNull():
            self.barcode_input.addAction(bi, QLineEdit.ActionPosition.LeadingPosition)
        si = self._load_icon(["search.svg", "find.svg", "magnify.svg"], QStyle.StandardPixmap.SP_FileDialogContentsView)
        if not si.isNull():
            self.search_edit.addAction(si, QLineEdit.ActionPosition.LeadingPosition)

    def retranslate_ui(self):
        # Top controls
        self.search_edit.setPlaceholderText(i18n.tr('stock.search.placeholder'))
        self.barcode_input.setPlaceholderText(i18n.tr('stock.scan.placeholder'))
        self.btn_add.setText(i18n.tr('stock.add'))
        self.btn_edit.setText(i18n.tr('stock.edit'))
        self.btn_delete.setText(i18n.tr('stock.delete'))
        self.btn_restock.setText(i18n.tr('stock.restock'))
        self.btn_consume.setText(i18n.tr('stock.consume'))
        # Headers
        self.table.setHorizontalHeaderLabels([
            "#",
            i18n.tr('stock.col.id'),
            i18n.tr('stock.col.code'),
            i18n.tr('stock.col.name'),
            i18n.tr('stock.col.category'),
            i18n.tr('stock.col.quantity'),
            i18n.tr('stock.col.expiry'),
            i18n.tr('stock.col.price'),
            i18n.tr('stock.col.location'),
            i18n.tr('stock.col.status'),
        ])
        self.table.setColumnHidden(1, True)

    def refresh(self):
        # If DB not connected yet, skip
        if getattr(self.db, 'cursor', None) is None:
            return
        query = self.search_edit.text().strip()
        loc_id = self.location_combo.currentData()
        rows = self.db.list_products(query if query else None, loc_id)
        self.table.setRowCount(0)
        for rid, barcode, sku, name, category, qty, price, reorder_point in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            # Index and hidden ID
            idx_item = QTableWidgetItem(str(r + 1))
            idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 0, idx_item)
            id_item = QTableWidgetItem(str(rid))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 1, id_item)
            # Code: Barcode/SKU
            code = barcode or sku or ""
            self.table.setItem(r, 2, QTableWidgetItem(code))
            # Name (left)
            name_item = QTableWidgetItem(name)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.table.setItem(r, 3, name_item)
            # Category
            self.table.setItem(r, 4, QTableWidgetItem(category or ""))
            # Quantity (bold, colored)
            qty_item = QTableWidgetItem(str(qty))
            f = qty_item.font(); f.setBold(True); qty_item.setFont(f)
            status_text = ""
            if qty <= 0:
                qty_item.setForeground(Qt.GlobalColor.red)
                status_text = "❌ Out of Stock"
            elif reorder_point and qty < reorder_point:
                qty_item.setForeground(Qt.GlobalColor.darkYellow)
                status_text = "⚠️ Low Stock"
            else:
                qty_item.setForeground(Qt.GlobalColor.darkGreen)
                status_text = "✅ In Stock"
            self.table.setItem(r, 5, qty_item)
            # Expiry indicator
            date_str, exp_status = (None, None)
            try:
                date_str, exp_status = self.db.get_earliest_expiry(rid)
            except Exception:
                pass
            exp_item = QTableWidgetItem(date_str or "")
            if exp_status == 'expired':
                exp_item.setForeground(Qt.GlobalColor.red)
            elif exp_status == 'soon':
                exp_item.setForeground(Qt.GlobalColor.darkYellow)
            else:
                exp_item.setForeground(Qt.GlobalColor.darkGreen)
            self.table.setItem(r, 6, exp_item)
            # Price (right aligned, currency)
            price_item = QTableWidgetItem(f"{price:,.2f}")
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(r, 7, price_item)
            # Location
            loc_name = self.location_combo.currentText()
            if loc_name is None or loc_name.strip() == "":
                loc_name = i18n.tr('stock.all_locations')
            self.table.setItem(r, 8, QTableWidgetItem(loc_name))
            # Status (icon/tag text)
            status_item = QTableWidgetItem(status_text)
            if "Out" in status_text:
                status_item.setForeground(Qt.GlobalColor.red)
            elif "Low" in status_text:
                status_item.setForeground(Qt.GlobalColor.darkYellow)
            else:
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            self.table.setItem(r, 9, status_item)

    def _selected_product_id(self) -> Optional[int]:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 1)
        try:
            return int(item.text()) if item else None
        except Exception:
            return None

    def on_add(self):
        dlg = ProductDialog(self, db=self.db)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            vals = dlg.get_values()
            if not vals['name']:
                QMessageBox.warning(self, i18n.tr('msg.validation'), i18n.tr('msg.name_required'))
                return
            # Create product with zero stock; we will log initial stock with movement to capture cost/location/batch
            pid = self.db.add_product(
                name=vals['name'],
                description=vals['description'],
                stock_quantity=0,
                price=vals['selling_price'],
                barcode=vals['barcode'] or None,
                sku=vals['sku'] or None,
                reorder_point=vals['reorder_point'],
                supplier_id=vals['supplier_id'],
            )
            if pid is None:
                QMessageBox.critical(self, i18n.tr('msg.error'), i18n.tr('msg.failed_add'))
                return
            # Update category and uom if available
            try:
                cur = self.db.cursor
                cur.execute("UPDATE products SET category = COALESCE(?, category), uom = COALESCE(?, uom) WHERE id = ?",
                            (vals['category'] or None, vals['uom'] or None, pid))
                self.db.conn.commit()
            except Exception:
                pass
            # Add batch if provided
            batch_id = None
            if vals['batch_no'] or vals['expiry']:
                try:
                    batch_id = self.db.add_batch(pid, vals['batch_no'] or f"B-{pid}", vals['expiry'])
                except Exception:
                    batch_id = None
            # Log initial stock
            if vals['quantity'] > 0:
                ok = self.db.adjust_stock(
                    pid, int(vals['quantity']), movement_type='Initial', reason='Initial Stock',
                    location_id=vals['location_id'], batch_id=batch_id, unit=vals['uom'], unit_qty=1.0,
                    cost_per_unit=vals['cost_price']
                )
                if not ok:
                    QMessageBox.critical(self, i18n.tr('msg.error'), i18n.tr('msg.failed_adjust'))
                    return
            self.refresh()

    def on_edit(self):
        pid = self._selected_product_id()
        if pid is None:
            QMessageBox.information(self, i18n.tr('msg.validation'), i18n.tr('msg.select_to_edit'))
            return
        # Load full product details from DB for editing
        data = self.db.get_product(pid)
        barcode = data[1] if data and len(data) > 1 else ""
        sku = data[2] if data and len(data) > 2 else ""
        name = data[3] if data and len(data) > 3 else ""
        desc = data[5] if data and len(data) > 5 else ""
        qty = int(data[6]) if data and len(data) > 6 else 0
        price = float(data[7]) if data and len(data) > 7 else 0.0
        category = data[4] if data and len(data) > 4 else ""
        dlg = ProductDialog(self, db=self.db, name=name, description=desc, quantity=qty, price=price, barcode=barcode)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            vals = dlg.get_values()
            if not vals['name']:
                QMessageBox.warning(self, i18n.tr('msg.validation'), i18n.tr('msg.name_required'))
                return
            ok = self.db.update_product(
                pid,
                vals['name'],
                vals['description'],
                int(vals['quantity']),
                float(vals['selling_price']),
                vals['barcode'] or None,
                vals['sku'] or None,
                vals['reorder_point'],
                vals['supplier_id'],
            ) if hasattr(self.db, 'update_product') else True
            if ok and not hasattr(self.db, 'update_product'):
                # Fallback: raw update
                try:
                    cur = self.db.cursor
                    cur.execute("UPDATE products SET name=?, description=?, price=?, barcode=?, sku=?, reorder_point=?, category=COALESCE(?, category), uom=COALESCE(?, uom) WHERE id=?",
                                (vals['name'], vals['description'], float(vals['selling_price']), vals['barcode'] or None, vals['sku'] or None, vals['reorder_point'], vals['category'] or None, vals['uom'] or None, pid))
                    self.db.conn.commit()
                    # adjust stock difference
                    cur.execute("SELECT current_stock_quantity FROM products WHERE id=?", (pid,))
                    current_qty = int(cur.fetchone()[0] or 0)
                    delta = int(vals['quantity']) - current_qty
                    if delta != 0:
                        self.db.adjust_stock(pid, delta, movement_type='Adjustment', reason='Edit Adjustment', location_id=self.location_combo.currentData())
                except Exception:
                    ok = False
            if ok and hasattr(self.db, 'update_product'):
                # Also persist category and uom if provided
                try:
                    cur = self.db.cursor
                    cur.execute(
                        "UPDATE products SET category = COALESCE(?, category), uom = COALESCE(?, uom) WHERE id = ?",
                        (vals['category'] or None, vals['uom'] or None, pid)
                    )
                    self.db.conn.commit()
                except Exception:
                    pass
            if not ok:
                QMessageBox.critical(self, i18n.tr('msg.error'), i18n.tr('msg.failed_update'))
                return
            self.refresh()

    def on_delete(self):
        pid = self._selected_product_id()
        if pid is None:
            QMessageBox.information(self, i18n.tr('msg.validation'), i18n.tr('msg.select_to_delete'))
            return
        if QMessageBox.question(self, i18n.tr('msg.confirm'), i18n.tr('msg.confirm_delete')) == QMessageBox.StandardButton.Yes:
            ok = self.db.delete_product(pid)
            if not ok:
                QMessageBox.critical(self, i18n.tr('msg.error'), i18n.tr('msg.failed_delete'))
                return
            self.refresh()

    def on_adjust_stock(self, sign: int):
        pid = self._selected_product_id()
        if pid is None:
            QMessageBox.information(self, i18n.tr('msg.validation'), i18n.tr('msg.select_product'))
            return
        # Simple prompt via spinbox dialog
        dlg = QDialog(self)
        dlg.setWindowTitle(i18n.tr('stock.adjust.title'))
        v = QVBoxLayout(dlg)
        form = QFormLayout()
        spin = QSpinBox()
        spin.setRange(1, 1_000_000)
        spin.setValue(1)
        form.addRow(QLabel(i18n.tr('stock.adjust.amount')), spin)
        v.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        v.addWidget(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            delta = int(spin.value()) * sign
            loc_id = self.location_combo.currentData()
            ok = self.db.adjust_stock(pid, delta, reason='Quick Adjust', location_id=loc_id)
            if not ok:
                QMessageBox.critical(self, i18n.tr('msg.error'), i18n.tr('msg.failed_adjust'))
                return
            self.refresh()

    def _load_locations(self):
        if getattr(self.db, 'cursor', None) is None:
            return
        self.location_combo.blockSignals(True)
        current = self.location_combo.currentData()
        self.location_combo.clear()
        self.location_combo.addItem("All Locations", userData=None)
        for lid, name, kind in (self.db.list_locations() or []):
            self.location_combo.addItem(name, userData=lid)
        # restore selection
        if current is not None:
            idx = self.location_combo.findData(current)
            if idx >= 0:
                self.location_combo.setCurrentIndex(idx)
        self.location_combo.blockSignals(False)

    def on_adjust_dialog(self):
        pid = self._selected_product_id()
        if pid is None:
            QMessageBox.information(self, i18n.tr('msg.validation'), i18n.tr('msg.select_product'))
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Stock Adjustment")
        v = QVBoxLayout(dlg)
        form = QFormLayout()
        reason = QComboBox()
        reason.addItems(["Damaged", "Stolen", "Expired", "Giveaway", "Correction"]) 
        loc = QComboBox()
        loc.addItem("Current Selection", userData=self.location_combo.currentData())
        loc.addItem("All Locations", userData=None)
        for lid, name, kind in (self.db.list_locations() or []):
            loc.addItem(name, userData=lid)
        qty = QSpinBox()
        qty.setRange(-1_000_000, 1_000_000)
        qty.setValue(0)
        form.addRow(QLabel("Reason"), reason)
        form.addRow(QLabel("Location"), loc)
        form.addRow(QLabel("Quantity (+/-)"), qty)
        v.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        v.addWidget(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            delta = int(qty.value())
            if delta == 0:
                return
            ok = self.db.adjust_stock(pid, delta, movement_type='Adjustment', reason=reason.currentText(), location_id=loc.currentData())
            if not ok:
                QMessageBox.critical(self, i18n.tr('msg.error'), i18n.tr('msg.failed_adjust'))
                return
            self.refresh()

    def on_transfer_dialog(self):
        pid = self._selected_product_id()
        if pid is None:
            QMessageBox.information(self, i18n.tr('msg.validation'), i18n.tr('msg.select_product'))
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Transfer Stock")
        v = QVBoxLayout(dlg)
        form = QFormLayout()
        from_cb = QComboBox()
        to_cb = QComboBox()
        for lid, name, kind in (self.db.list_locations() or []):
            from_cb.addItem(name, userData=lid)
            to_cb.addItem(name, userData=lid)
        # default from current selected location if any
        sel_loc = self.location_combo.currentData()
        if sel_loc is not None:
            idx = from_cb.findData(sel_loc)
            if idx >= 0:
                from_cb.setCurrentIndex(idx)
        qty = QSpinBox()
        qty.setRange(1, 1_000_000)
        qty.setValue(1)
        form.addRow(QLabel("From"), from_cb)
        form.addRow(QLabel("To"), to_cb)
        form.addRow(QLabel("Quantity"), qty)
        v.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        v.addWidget(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if from_cb.currentData() == to_cb.currentData():
                return
            ok = self.db.transfer_stock(pid, from_cb.currentData(), to_cb.currentData(), int(qty.value()))
            if not ok:
                QMessageBox.critical(self, i18n.tr('msg.error'), i18n.tr('msg.failed_adjust'))
                return
            self.refresh()

    def on_history_dialog(self):
        pid = self._selected_product_id()
        if pid is None:
            QMessageBox.information(self, i18n.tr('msg.validation'), i18n.tr('msg.select_product'))
            return
        rows = self.db.list_movements(pid, 200)
        dlg = QDialog(self)
        dlg.setWindowTitle("Movement History")
        v = QVBoxLayout(dlg)
        table = QTableWidget(0, 7)
        table.setHorizontalHeaderLabels(["Date", "Qty", "Type", "Reason", "Location", "Batch", "User"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        h = table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        for (ts, qty, mtype, reason, loc_id, batch_id, user) in rows:
            r = table.rowCount(); table.insertRow(r)
            table.setItem(r, 0, QTableWidgetItem(str(ts)))
            table.setItem(r, 1, QTableWidgetItem(str(qty)))
            table.setItem(r, 2, QTableWidgetItem(mtype or ""))
            table.setItem(r, 3, QTableWidgetItem(reason or ""))
            # Fetch names best-effort
            loc_name = ""; batch_no = ""
            try:
                if loc_id:
                    for lid, name, kind in (self.db.list_locations() or []):
                        if lid == loc_id:
                            loc_name = name; break
                if batch_id:
                    self.db.cursor.execute("SELECT batch_no FROM batches WHERE id = ?", (batch_id,))
                    rr = self.db.cursor.fetchone(); batch_no = rr[0] if rr else ""
            except Exception:
                pass
            table.setItem(r, 4, QTableWidgetItem(loc_name))
            table.setItem(r, 5, QTableWidgetItem(batch_no))
            table.setItem(r, 6, QTableWidgetItem(user or ""))
        v.addWidget(table)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(dlg.reject)
        btns.accepted.connect(dlg.accept)
        v.addWidget(btns)
        dlg.resize(800, 400)
        dlg.exec()

    def on_batch_dialog(self):
        pid = self._selected_product_id()
        if pid is None:
            QMessageBox.information(self, i18n.tr('msg.validation'), i18n.tr('msg.select_product'))
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Batch / Expiry")
        v = QVBoxLayout(dlg)
        form = QFormLayout()
        batch_edit = QLineEdit()
        expiry = QDateEdit()
        expiry.setCalendarPopup(True)
        expiry.setDate(QDate.currentDate())
        qty = QSpinBox(); qty.setRange(0, 1_000_000); qty.setValue(0)
        form.addRow(QLabel("Batch Number"), batch_edit)
        form.addRow(QLabel("Expiry Date"), expiry)
        form.addRow(QLabel("Add Quantity"), qty)
        v.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        v.addWidget(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            batch_no = batch_edit.text().strip()
            if not batch_no and qty.value() > 0:
                QMessageBox.warning(self, i18n.tr('msg.validation'), "Batch number is required when adding quantity")
                return
            batch_id = None
            if batch_no:
                batch_id = self.db.add_batch(pid, batch_no, expiry.date().toString('yyyy-MM-dd'))
            add_qty = int(qty.value())
            if add_qty > 0:
                ok = self.db.adjust_stock(pid, add_qty, movement_type='Purchase', reason='Batch Add', location_id=self.location_combo.currentData(), batch_id=batch_id)
                if not ok:
                    QMessageBox.critical(self, i18n.tr('msg.error'), i18n.tr('msg.failed_adjust'))
                    return
            self.refresh()

    def on_reorder_dialog(self):
        pid = self._selected_product_id()
        if pid is None:
            QMessageBox.information(self, i18n.tr('msg.validation'), i18n.tr('msg.select_product'))
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Reorder")
        v = QVBoxLayout(dlg)
        form = QFormLayout()
        qty = QSpinBox(); qty.setRange(1, 1_000_000); qty.setValue(10)
        cost = QDoubleSpinBox(); cost.setRange(0, 1_000_000); cost.setDecimals(2); cost.setValue(0)
        form.addRow(QLabel("Quantity"), qty)
        form.addRow(QLabel("Cost per unit"), cost)
        v.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        v.addWidget(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ok = self.db.adjust_stock(pid, int(qty.value()), movement_type='Purchase', reason='Reorder', location_id=self.location_combo.currentData(), cost_per_unit=float(cost.value()))
            if not ok:
                QMessageBox.critical(self, i18n.tr('msg.error'), i18n.tr('msg.failed_adjust'))
                return
            self.refresh()

    def on_stocktake_dialog(self):
        loc_id = self.location_combo.currentData()
        dlg = QDialog(self)
        dlg.setWindowTitle("Stocktake")
        v = QVBoxLayout(dlg)
        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["ID", "Name", "Recorded", "Counted"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        h = table.horizontalHeader(); h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents); h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents); h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        # populate with current rows
        rows = self.db.list_products(None, loc_id)
        for pid, barcode, name, desc, qty, price in rows:
            r = table.rowCount(); table.insertRow(r)
            table.setItem(r, 0, QTableWidgetItem(str(pid)))
            table.setItem(r, 1, QTableWidgetItem(name))
            table.setItem(r, 2, QTableWidgetItem(str(qty)))
            spin = QSpinBox(); spin.setRange(0, 1_000_000); spin.setValue(int(qty))
            table.setCellWidget(r, 3, spin)
        v.addWidget(table)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        v.addWidget(btns)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            for r in range(table.rowCount()):
                pid = int(table.item(r, 0).text())
                recorded = int(table.item(r, 2).text())
                spin = table.cellWidget(r, 3)
                counted = int(spin.value()) if isinstance(spin, QSpinBox) else recorded
                delta = counted - recorded
                if delta != 0:
                    self.db.adjust_stock(pid, delta, movement_type='Stocktake', reason='Stocktake', location_id=loc_id)
            self.refresh()

    def on_export_dialog(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Stock", "stock.csv", "CSV Files (*.csv)")
        if not path:
            return
        loc_id = self.location_combo.currentData()
        rows = self.db.list_products(None, loc_id)
        try:
            import csv
            with open(path, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(["ID", "Barcode", "Name", "Description", "Expiry", "Quantity", "Price"]) 
                for pid, barcode, name, desc, qty, price in rows:
                    exp, _status = self.db.get_earliest_expiry(pid)
                    w.writerow([pid, barcode or '', name, desc or '', exp or '', qty, f"{price:.2f}"])
            QMessageBox.information(self, "Export", "Export completed")
        except Exception as e:
            QMessageBox.critical(self, "Export", f"Failed to export: {e}")

    def on_row_double_clicked(self, item):
        row = item.row()
        try:
            pid = int(self.table.item(row, 1).text())
        except Exception:
            return
        data = self.db.get_product(pid)
        if not data:
            return
        (_id, barcode, sku, name, desc, category, qty, price, rop, supplier_id) = data
        dlg = QDialog(self)
        dlg.setWindowTitle("Product Details")
        v = QVBoxLayout(dlg)
        info = QTableWidget(0, 2)
        info.verticalHeader().setVisible(False)
        info.horizontalHeader().setVisible(False)
        info.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        details = [
            ("Code", barcode or sku or ""),
            ("Name", name or ""),
            ("Category", category or ""),
            ("Description", desc or ""),
            ("Quantity", str(qty)),
            ("Reorder Point", str(rop or 0)),
            ("Price", f"{price:,.2f}"),
        ]
        for k, vval in details:
            r = info.rowCount(); info.insertRow(r)
            info.setItem(r, 0, QTableWidgetItem(k))
            info.setItem(r, 1, QTableWidgetItem(vval))
        v.addWidget(info)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(dlg.reject)
        btns.accepted.connect(dlg.accept)
        v.addWidget(btns)
        dlg.resize(500, 300)
        dlg.exec()
        v.addWidget(table)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(dlg.reject)
        btns.accepted.connect(dlg.accept)
        v.addWidget(btns)
        dlg.resize(800, 400)
        dlg.exec()

    def on_scan_barcode(self):
        code = self.barcode_input.text().strip()
        if not code:
            return
        # If DB not ready, ignore
        if getattr(self.db, 'cursor', None) is None:
            return
        existing = self.db.get_product_by_barcode(code)
        if existing:
            # Offer quick +1 stock
            if QMessageBox.question(self, i18n.tr('msg.confirm'), i18n.tr('stock.scan.exists_prompt')) == QMessageBox.StandardButton.Yes:
                self.db.adjust_stock(existing[0], +1, movement_type='Scan In', reason='Scan In', location_id=self.location_combo.currentData())
                self.refresh()
        else:
            # Create new product with barcode pre-filled
            dlg = ProductDialog(self, barcode=code)
            # When launched from barcode, focus and select the Name field for quick typing
            try:
                dlg.name_edit.setFocus()
                dlg.name_edit.selectAll()
            except Exception:
                pass
            if dlg.exec() == QDialog.DialogCode.Accepted:
                b, n, d, q, p = dlg.get_values()
                if not n:
                    QMessageBox.warning(self, i18n.tr('msg.validation'), i18n.tr('msg.name_required'))
                    return
                pid = self.db.add_product(n, d, q, p, b)
                if pid is None:
                    QMessageBox.critical(self, i18n.tr('msg.error'), i18n.tr('msg.failed_add'))
                    return
                self.refresh()
        self.barcode_input.clear()
        self._focus_barcode()

    def _focus_barcode(self):
        try:
            self.barcode_input.setFocus()
            # Select all so new scans overwrite any leftover text
            self.barcode_input.selectAll()
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        self._focus_barcode()
