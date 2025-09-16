"""
Invoice generation UI: build invoices linked to clients and stock.
"""

from typing import Optional
from PyQt6.QtCore import Qt, QSize, QPoint
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit, QToolButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QComboBox, QLabel,
    QSpinBox, QDoubleSpinBox, QDialog, QDialogButtonBox, QSizePolicy, QGroupBox, QCheckBox, QPushButton, QAbstractItemView, QFileDialog
)
from PyQt6.QtWidgets import QStyle
from PyQt6.QtGui import QIntValidator
from i18n.language_manager import language_manager as i18n



class InvoicePdfPreviewDialog(QDialog):
    """Minimal PDF viewer used for inline invoice previews."""

    def __init__(self, pdf_path: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        try:
            from PyQt6.QtPdf import QPdfDocument
            from PyQt6.QtPdfWidgets import QPdfView
        except Exception as exc:  # pragma: no cover - depends on QtPdf availability
            raise ImportError('QtPdf components are not available') from exc

        self._pdf_doc_cls = QPdfDocument
        self._pdf_view_cls = QPdfView

        self.setWindowTitle('Invoice Preview')
        self.setModal(True)
        

        self._valid = True
        self._document_ready = False
        self._page_count = 0

        self.document = QPdfDocument(self)
        self.view = QPdfView(self)
        self.view.setDocument(self.document)
        try:
            self.view.setPageMode(QPdfView.PageMode.SinglePage)
        except Exception:
            pass
        try:
            self.view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        except Exception:
            pass

        self._nav = None
        for attr in ('pageNavigator', 'pageNavigation'):
            method = getattr(self.view, attr, None)
            if callable(method):
                try:
                    self._nav = method()
                except Exception:
                    self._nav = None
                if self._nav is not None:
                    break

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(6)

        self.prev_btn = QToolButton(self)
        self.prev_btn.setText('\u2b05\ufe0f')
        self.prev_btn.setAutoRaise(True)
        self.prev_btn.setToolTip('Previous page')

        self.next_btn = QToolButton(self)
        self.next_btn.setText('\u27a1\ufe0f')
        self.next_btn.setAutoRaise(True)
        self.next_btn.setToolTip('Next page')

        self.page_input = QLineEdit(self)
        self.page_input.setPlaceholderText('Page')
        self.page_input.setFixedWidth(70)
        self.page_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_input.setValidator(QIntValidator(1, 9999, self))
        self.page_input.setEnabled(False)

        self.zoom_in_btn = QToolButton(self)
        self.zoom_in_btn.setText('\u2795')
        self.zoom_in_btn.setAutoRaise(True)
        self.zoom_in_btn.setToolTip('Zoom in')

        self.zoom_out_btn = QToolButton(self)
        self.zoom_out_btn.setText('\u2796')
        self.zoom_out_btn.setAutoRaise(True)
        self.zoom_out_btn.setToolTip('Zoom out')

        self.zoom_reset_btn = QToolButton(self)
        self.zoom_reset_btn.setText('\U0001f504')
        self.zoom_reset_btn.setAutoRaise(True)
        self.zoom_reset_btn.setToolTip('Reset zoom')

        toolbar_layout.addWidget(self.prev_btn)
        toolbar_layout.addWidget(self.next_btn)
        toolbar_layout.addWidget(self.page_input)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self.zoom_in_btn)
        toolbar_layout.addWidget(self.zoom_out_btn)
        toolbar_layout.addWidget(self.zoom_reset_btn)

        main_layout.addLayout(toolbar_layout)
        main_layout.addWidget(self.view, 1)

        status_widget = QWidget(self)
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(6)

        self.page_status = QLabel('Page - of -', status_widget)
        self.zoom_status = QLabel('Zoom: --', status_widget)
        self.zoom_status.setAlignment(Qt.AlignmentFlag.AlignRight)

        status_layout.addWidget(self.page_status)
        status_layout.addStretch(1)
        status_layout.addWidget(self.zoom_status)
        main_layout.addWidget(status_widget)

        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)

        self.prev_btn.clicked.connect(self._go_previous)
        self.next_btn.clicked.connect(self._go_next)
        self.page_input.returnPressed.connect(self._commit_page_input)
        self.page_input.editingFinished.connect(self._commit_page_input)
        self.zoom_in_btn.clicked.connect(self._zoom_in)
        self.zoom_out_btn.clicked.connect(self._zoom_out)
        self.zoom_reset_btn.clicked.connect(self._reset_zoom)

        if self._nav is not None:
            current_signal = getattr(self._nav, 'currentPageChanged', None)
            if current_signal is not None:
                try:
                    current_signal.connect(self._on_page_changed)
                except Exception:
                    pass

        for signal_name in ('zoomFactorChanged', 'zoomModeChanged'):
            signal = getattr(self.view, signal_name, None)
            if signal is not None:
                try:
                    signal.connect(self._on_zoom_changed)
                except Exception:
                    pass

        page_count_signal = getattr(self.document, 'pageCountChanged', None)
        if page_count_signal is not None:
            try:
                page_count_signal.connect(self._on_page_count_changed)
            except Exception:
                pass

        self.document.statusChanged.connect(self._on_document_status)
        try:
            self.document.load(pdf_path)
        except Exception:
            self._valid = False
        self._on_document_status(self.document.status())

        self.setMinimumSize(720, 520)
        self.resize(900, 700)

    @property
    def is_valid(self) -> bool:
        if not self._valid:
            return False
        if not self._document_ready:
            return True
        return self._page_count > 0

    def _on_document_status(self, status) -> None:
        if status == self._pdf_doc_cls.Status.Error:
            self._valid = False
            return
        if status == self._pdf_doc_cls.Status.Ready:
            self._initialize_document()

    def _initialize_document(self) -> None:
        if self._document_ready:
            return
        count = int(self.document.pageCount() or 0)
        if count <= 0:
            self._valid = False
            return
        self._document_ready = True
        self._page_count = count
        self.page_input.setEnabled(True)
        self._set_page(0)
        self._update_zoom_label()

    def _on_page_changed(self, *_) -> None:
        if not self._document_ready:
            return
        self._update_page_display()
        self._update_nav_state()

    def _on_page_count_changed(self, *_) -> None:
        if not self._document_ready:
            return
        self._page_count = max(int(self.document.pageCount() or 0), 0)
        self._update_nav_state()
        self._update_page_display()

    def _on_zoom_changed(self, *_) -> None:
        self._update_zoom_label()

    def _update_page_display(self) -> None:
        count = self._get_page_count()
        if count <= 0:
            self.page_status.setText('Page - of -')
            return
        current = self._get_current_page()
        self.page_status.setText(f'Page {current + 1} of {count}')
        blocked = self.page_input.blockSignals(True)
        self.page_input.setText(str(current + 1))
        self.page_input.blockSignals(blocked)

    def _update_nav_state(self) -> None:
        count = self._get_page_count()
        current = self._get_current_page()
        enabled = self._document_ready and count > 0
        self.prev_btn.setEnabled(enabled and current > 0)
        self.next_btn.setEnabled(enabled and (current + 1) < count)

    def _update_zoom_label(self) -> None:
        try:
            zoom = float(self.view.zoomFactor())
        except Exception:
            zoom = 1.0
        if zoom <= 0:
            zoom = 1.0
        suffix = ''
        try:
            if self.view.zoomMode() == self._pdf_view_cls.ZoomMode.FitToWidth:
                suffix = ' (Fit width)'
        except Exception:
            pass
        percent = int(round(zoom * 100))
        self.zoom_status.setText(f'Zoom: {percent}%{suffix}')

    def _go_previous(self) -> None:
        self._set_page(self._get_current_page() - 1)

    def _go_next(self) -> None:
        self._set_page(self._get_current_page() + 1)

    def _commit_page_input(self) -> None:
        if not self._document_ready:
            return
        text = self.page_input.text().strip()
        if not text:
            self._update_page_display()
            return
        try:
            target = int(text) - 1
        except ValueError:
            self._update_page_display()
            return
        self._set_page(target)

    def _set_page(self, index: int) -> None:
        if not self._document_ready:
            return
        count = self._get_page_count()
        if count <= 0:
            return
        index = max(0, min(index, count - 1))
        if self._nav is not None:
            setter = getattr(self._nav, 'setCurrentPage', None)
            if callable(setter):
                try:
                    setter(index)
                except Exception:
                    pass
            else:
                jumper = getattr(self._nav, 'jump', None)
                if callable(jumper):
                    try:
                        jumper(index)
                    except Exception:
                        pass
        else:
            set_page = getattr(self.view, 'setPage', None)
            if callable(set_page):
                try:
                    set_page(index)
                except Exception:
                    pass
        self._update_page_display()
        self._update_nav_state()

    def _zoom_in(self) -> None:
        self._apply_zoom_scale(1.2)

    def _zoom_out(self) -> None:
        self._apply_zoom_scale(1 / 1.2)

    def _apply_zoom_scale(self, factor: float) -> None:
        try:
            self.view.setZoomMode(self._pdf_view_cls.ZoomMode.Custom)
        except Exception:
            pass
        try:
            current = float(self.view.zoomFactor())
        except Exception:
            current = 1.0
        if current <= 0:
            current = 1.0
        new_factor = max(0.2, min(current * factor, 5.0))
        try:
            self.view.setZoomFactor(new_factor)
        except Exception:
            pass
        self._update_zoom_label()

    def _reset_zoom(self) -> None:
        try:
            self.view.setZoomMode(self._pdf_view_cls.ZoomMode.FitToWidth)
        except Exception:
            try:
                self.view.setZoomFactor(1.0)
            except Exception:
                pass
        self._update_zoom_label()

    def _get_current_page(self) -> int:
        if self._nav is not None:
            getter = getattr(self._nav, 'currentPage', None)
            if callable(getter):
                try:
                    return int(getter())
                except Exception:
                    pass
        getter = getattr(self.view, 'page', None)
        if callable(getter):
            try:
                return int(getter())
            except Exception:
                pass
        return 0

    def _get_page_count(self) -> int:
        try:
            return max(int(self.document.pageCount() or 0), 0)
        except Exception:
            return max(self._page_count, 0)


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
        self.btn_save_as = mkbtn('Save As')
        self.btn_history = mkbtn('History')
        self.btn_remove = mkbtn('Remove Item')
        for i,b in enumerate([self.btn_new, self.btn_save, self.btn_save_as, self.btn_history, self.btn_remove]):
            actions.addWidget(b, 0, i); actions.setColumnStretch(i,1)
        for c in range(8):
            actions.setColumnStretch(c, 1)
        v.addLayout(actions)

        # Filters row: client, location, product search
        filters = QHBoxLayout()
        self.client_cb = QComboBox(); self.client_cb.setEditable(True)
        self.location_cb = QComboBox(); self.location_cb.setEditable(False)
        self.search = QLineEdit(); self.search.setPlaceholderText('Search or scan product...')
        self.search.returnPressed.connect(self._on_search_return)
        # Use a QCompleter for inline results that doesn't steal focus
        from PyQt6.QtWidgets import QCompleter
        from PyQt6.QtGui import QStandardItemModel, QStandardItem
        self._compl_model = QStandardItemModel(self)
        self._completer = QCompleter(self._compl_model, self)
        try:
            self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self._completer.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        except Exception:
            pass
        self.search.setCompleter(self._completer)
        # Update results as the user types (only when user edits)
        self.search.textEdited.connect(self._on_search_text_changed)
        # PyQt6 unified activated signal
        self._completer.activated.connect(self._on_completer_activated)
        filters.addWidget(QLabel('Client'))
        filters.addWidget(self.client_cb, 1)
        filters.addWidget(QLabel('Location'))
        filters.addWidget(self.location_cb, 0)
        filters.addWidget(self.search, 1)
        v.addLayout(filters)

        # (Old custom popup replaced by QCompleter)

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

        # Totals + Settings row
        bottom_row = QHBoxLayout()
        # Left: totals
        totals_col = QVBoxLayout()
        self.subtotal_label = QLabel('Subtotal: 0.00')
        self.tax_label = QLabel('Tax: 0.00')
        self.total_label = QLabel('Total: 0.00')
        totals_col.addWidget(self.subtotal_label)
        totals_col.addWidget(self.tax_label)
        totals_col.addWidget(self.total_label)
        totals_col.addStretch(1)
        bottom_row.addLayout(totals_col, 1)

        # Right: quick settings (tax, currency, language, subject)
        settings_box = QGroupBox('Invoice Settings')
        sb_layout = QGridLayout(settings_box)
        self.tax_name = QLineEdit(); self.tax_value = QDoubleSpinBox(); self.tax_value.setRange(0, 100000); self.tax_value.setDecimals(2)
        self.tax_type = QComboBox(); self.tax_type.addItems(['Amount', 'Percentage'])
        self.tax_inclusive = QCheckBox('Prices tax-inclusive')
        self.lang_combo = QComboBox(); self.lang_combo.addItems(['English', 'French'])
        self.currency_combo = QComboBox(); self.currency_combo.addItems(['MAD','USD','EUR','GBP']); self.currency_combo.setCurrentText('MAD')
        self.include_subject = QCheckBox('Include subject')
        self.subject_field = QLineEdit(); self.subject_field.setEnabled(False)
        self.include_subject.toggled.connect(self.subject_field.setEnabled)
        self.include_unit_column = QCheckBox('Include Unit Column in PDF'); self.include_unit_column.setChecked(False)
        r=0
        sb_layout.addWidget(QLabel('Tax name'), r,0); sb_layout.addWidget(self.tax_name, r,1); r+=1
        sb_layout.addWidget(QLabel('Tax value'), r,0); sb_layout.addWidget(self.tax_value, r,1); r+=1
        sb_layout.addWidget(QLabel('Tax type'), r,0); sb_layout.addWidget(self.tax_type, r,1); r+=1
        sb_layout.addWidget(self.tax_inclusive, r,0,1,2); r+=1
        sb_layout.addWidget(QLabel('Language'), r,0); sb_layout.addWidget(self.lang_combo, r,1); r+=1
        sb_layout.addWidget(QLabel('Currency'), r,0); sb_layout.addWidget(self.currency_combo, r,1); r+=1
        sb_layout.addWidget(self.include_subject, r,0); sb_layout.addWidget(self.subject_field, r,1); r+=1
        sb_layout.addWidget(self.include_unit_column, r,0,1,2); r+=1
        bottom_row.addWidget(settings_box, 1)
        v.addLayout(bottom_row)

        # Wire actions
        self.btn_new.clicked.connect(self.on_new)
        self.btn_save.clicked.connect(self.on_save)
        self.btn_save_as.clicked.connect(self.on_save_as)
        self.btn_remove.clicked.connect(self.on_remove_item)
        self.btn_history.clicked.connect(self.on_history)
        self._attach_icons()
        # Recompute totals when tax settings change
        try:
            self.tax_name.textChanged.connect(lambda *_: self._recompute_total())
            self.tax_value.valueChanged.connect(lambda *_: self._recompute_total())
            self.tax_type.currentIndexChanged.connect(lambda *_: self._recompute_total())
            self.tax_inclusive.toggled.connect(lambda *_: self._recompute_total())
        except Exception:
            pass

        # QCompleter popup auto-hides on selection or focus change
        # Update available stock when location changes
        try:
            self.location_cb.currentIndexChanged.connect(self._refresh_available_for_all_rows)
        except Exception:
            pass

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
        self.btn_save_as.setIcon(self._load_icon(["save_as.svg","save-as.svg","save_alt.svg","save.svg"], QStyle.StandardPixmap.SP_DialogSaveButton)); self.btn_save_as.setIconSize(sz)
        self.btn_remove.setIcon(self._load_icon(["delete.svg"], QStyle.StandardPixmap.SP_TrashIcon)); self.btn_remove.setIconSize(sz)
        si = self._load_icon(["search.svg","find.svg","magnify.svg"], QStyle.StandardPixmap.SP_FileDialogContentsView)
        if si and not si.isNull():
            self.search.addAction(si, QLineEdit.ActionPosition.LeadingPosition)

    # ----- Data loaders -----
    def on_db_ready(self):
        self._load_clients(); self._load_locations()
        # Re-run search to show inline suggestions if user already typed
        try:
            self._on_search_text_changed(self.search.text())
        except Exception:
            pass

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
        # index
        idx_item = QTableWidgetItem(str(r+1)); idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter); idx_item.setFlags(idx_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(r, 0, idx_item)
        # product cell with id in UserRole
        prod_item = QTableWidgetItem(name); prod_item.setData(Qt.ItemDataRole.UserRole, product_id); prod_item.setToolTip(f"SKU: {sku or ''}  Barcode: {barcode or ''}")
        self.table.setItem(r, 1, prod_item)
        # qty as spin box
        qty_spin = QDoubleSpinBox(); qty_spin.setDecimals(2); qty_spin.setRange(0.01, 1_000_000.0); qty_spin.setValue(float(qty)); qty_spin.valueChanged.connect(lambda *_: self._on_line_changed(r))
        self.table.setCellWidget(r, 2, qty_spin)
        # price as spin box
        price_spin = QDoubleSpinBox(); price_spin.setDecimals(2); price_spin.setRange(0.0, 1_000_000.0); price_spin.setValue(float(unit_price)); price_spin.valueChanged.connect(lambda *_: self._on_line_changed(r))
        self.table.setCellWidget(r, 3, price_spin)
        # total item
        total_item = QTableWidgetItem(f"{float(qty)*float(unit_price):,.2f}"); total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter); total_item.setFlags(total_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(r, 4, total_item)
        # Available
        try:
            loc_id = self.location_cb.currentData()
            available = self.db.get_stock(product_id, loc_id)
            avail_item = QTableWidgetItem(str(available)); avail_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter); avail_item.setFlags(avail_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        except Exception:
            avail_item = QTableWidgetItem('')
        self.table.setItem(r, 5, avail_item)
        self._recompute_total()

    def _on_line_changed(self, row: int):
        # Update the line total cell when qty/price changes and recompute grand totals
        try:
            qty_widget = self.table.cellWidget(row, 2)
            price_widget = self.table.cellWidget(row, 3)
            qty = float(qty_widget.value()) if qty_widget else 0.0
            price = float(price_widget.value()) if price_widget else 0.0
            self.table.item(row, 4).setText(f"{qty*price:,.2f}")
        except Exception:
            pass
        self._recompute_total()

    def _recompute_total(self):
        subtotal = 0.0
        for r in range(self.table.rowCount()):
            try:
                qtyw = self.table.cellWidget(r,2); pricew = self.table.cellWidget(r,3)
                qty = float(qtyw.value()) if qtyw else float(self.table.item(r,2).text().replace(',',''))
                price = float(pricew.value()) if pricew else float(self.table.item(r,3).text().replace(',',''))
                line = qty*price
                self.table.item(r,4).setText(f"{line:,.2f}")
                subtotal += line
            except Exception:
                pass
        # Compute tax
        tax_amount = 0.0
        try:
            name = self.tax_name.text().strip()
            val = float(self.tax_value.value())
            ttype = self.tax_type.currentText()
            inclusive = self.tax_inclusive.isChecked()
            if name:
                if inclusive and ttype == 'Percentage' and val > 0:
                    tax_amount = subtotal * (val / (100.0 + val))
                elif ttype == 'Percentage':
                    tax_amount = subtotal * (val / 100.0)
                else:
                    tax_amount = val
        except Exception:
            tax_amount = 0.0
        total = subtotal + (0 if self.tax_inclusive.isChecked() else tax_amount)
        self.subtotal_label.setText(f"Subtotal: {subtotal:,.2f}")
        self.tax_label.setText(f"Tax: {tax_amount:,.2f}")
        self.total_label.setText(f"Total: {total:,.2f}")

    def _collect_items(self):
        items = []
        for r in range(self.table.rowCount()):
            prod_item = self.table.item(r,1)
            if not prod_item:
                continue
            pid = prod_item.data(Qt.ItemDataRole.UserRole)
            try:
                qtyw = self.table.cellWidget(r,2); pricew = self.table.cellWidget(r,3)
                qty = float(qtyw.value()) if qtyw else float(self.table.item(r,2).text().replace(',',''))
                price = float(pricew.value()) if pricew else float(self.table.item(r,3).text().replace(',',''))
            except Exception:
                qty = 0; price = 0
            items.append({'product_id': int(pid) if pid is not None else None, 'name': prod_item.text(), 'qty': qty, 'unit_price': price})
        return items

    # ----- Actions -----
    def on_new(self):
        # Clear current draft items
        self.table.setRowCount(0)
        self._recompute_total()
        # Reset client to Walk-in (if present)
        try:
            idx = self.client_cb.findData(None)
            if idx >= 0:
                self.client_cb.setCurrentIndex(idx)
        except Exception:
            pass
        # Keep current location selection (seller choice), but ensure control is usable
        # Clear and focus the search box for quick scanning
        try:
            self.search.clear()
            self.search.setFocus()
        except Exception:
            pass

    def on_remove_item(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)
        # Re-index numbers
        for r in range(self.table.rowCount()):
            self.table.setItem(r, 0, QTableWidgetItem(str(r+1)))
        self._recompute_total()

    def on_save(self):
        self._save_invoice(with_dialog=False)

    def on_save_as(self):
        self._save_invoice(with_dialog=True)

    def _save_invoice(self, *, with_dialog: bool) -> None:
        items = self._collect_items()
        if not items:
            QMessageBox.information(self, 'Invoice', 'Add at least one item')
            return
        client_id = self.client_cb.currentData()
        client_name = self.client_cb.currentText().strip() if client_id is None else None
        loc_id = self.location_cb.currentData()
        import os, datetime
        out_dir = os.path.join(os.getcwd(), 'receipts')
        os.makedirs(out_dir, exist_ok=True)
        chosen_path = None
        if with_dialog:
            default_name = f"invoice_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            default_path = os.path.join(out_dir, f"{default_name}.pdf")
            selected, _ = QFileDialog.getSaveFileName(self, 'Save Invoice PDF', default_path, 'PDF Files (*.pdf)')
            if not selected:
                return
            chosen_path = selected if selected.lower().endswith('.pdf') else f"{selected}.pdf"
            chosen_path = os.path.abspath(chosen_path)
        inv_id = self.db.create_invoice(items, client_id=client_id, client_name=client_name, location_id=loc_id)
        if inv_id is None:
            QMessageBox.critical(self, 'Invoice', 'Failed to create invoice (insufficient stock?)')
            return
        try:
            rec = self.db.get_invoice(inv_id)
            inv_no = rec[1] if rec and len(rec) > 1 else f"INV-{inv_id}"
        except Exception:
            inv_no = f"INV-{inv_id}"
        out_path = chosen_path if (with_dialog and chosen_path) else os.path.join(out_dir, f"invoice_{inv_no}.pdf")
        out_path = os.path.abspath(out_path)
        if with_dialog and chosen_path:
            os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
        ok = self.generate_invoice_pdf(out_path, items)
        if ok:
            if not self.view_pdf_inline(out_path):
                try:
                    if os.name == 'nt':
                        os.startfile(out_path)  # type: ignore[attr-defined]
                    else:
                        import subprocess
                        subprocess.Popen(['xdg-open', out_path])
                except Exception:
                    QMessageBox.information(self, 'Invoice', f'PDF saved to: {out_path}')
        else:
            QMessageBox.information(self, 'Invoice', f'Invoice #{inv_id} created (PDF generation skipped)')

    # ----- History -----
    def on_history(self):
        try:
            rows = self.db.list_invoices() or []
        except Exception:
            rows = []
        dlg = QDialog(self); dlg.setWindowTitle('Invoices')
        lay = QVBoxLayout(dlg)
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(['#','Number','Date','Client','Total'])
        table.verticalHeader().setVisible(False)
        h = table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        lay.addWidget(table)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        lay.addWidget(btns); btns.rejected.connect(dlg.reject); btns.accepted.connect(dlg.accept)
        for (iid, number, date, cname, cid, total) in rows:
            r = table.rowCount(); table.insertRow(r)
            table.setItem(r,0,QTableWidgetItem(str(r+1)))
            table.setItem(r,1,QTableWidgetItem(number or ''))
            table.setItem(r,2,QTableWidgetItem(str(date)))
            table.setItem(r,3,QTableWidgetItem(cname or ''))
            table.setItem(r,4,QTableWidgetItem(f"{float(total or 0):,.2f}"))
        dlg.resize(800, 400)
        dlg.exec()

    # ----- PDF -----
    def on_print_pdf(self):
        items = self._collect_items()
        if not items:
            QMessageBox.information(self, 'Invoice', 'Add at least one item to print')
            return
        # Recompute totals
        self._recompute_total()
        # Prepare output path
        import os, datetime, tempfile
        out_dir = os.path.join(os.getcwd(), 'receipts'); os.makedirs(out_dir, exist_ok=True)
        filename = f"invoice_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        out_path = os.path.join(out_dir, filename)
        ok = self.generate_invoice_pdf(out_path, items)
        if not ok:
            QMessageBox.warning(self, 'Invoice', 'Failed to generate PDF (missing dependencies?)')
            return
        # Try inline viewer; fall back to system viewer
        if not self.view_pdf_inline(out_path):
            try:
                if os.name == 'nt':
                    os.startfile(out_path)  # type: ignore[attr-defined]
                else:
                    import subprocess
                    subprocess.Popen(['xdg-open', out_path])
            except Exception:
                QMessageBox.information(self, 'Invoice', f'PDF saved to: {out_path}')

    def _refresh_available_for_all_rows(self):
        try:
            loc_id = self.location_cb.currentData()
            for r in range(self.table.rowCount()):
                prod_item = self.table.item(r,1)
                pid = int(prod_item.data(Qt.ItemDataRole.UserRole)) if prod_item else None
                if pid is None:
                    continue
                available = self.db.get_stock(pid, loc_id)
                self.table.setItem(r, 5, QTableWidgetItem(str(available)))
        except Exception:
            pass

    # ----- Inline search -----
    def _on_search_text_changed(self, text: str):
        text = (text or '').strip()
        # Query top matches and feed the completer's model
        try:
            rows = self.db.list_products(text if text else None, None) or []
        except Exception:
            rows = []
        # Rebuild model
        from PyQt6.QtGui import QStandardItem
        self._compl_model.clear()
        max_items = 20
        for rid, barcode, sku, name, category, qty, price, reorder_point in rows[:max_items]:
            label_parts = [name or '']
            code = barcode or sku
            if code:
                label_parts.append(f"[{code}]")
            label_parts.append(f"{float(price or 0):,.2f}")
            it = QStandardItem('  '.join(label_parts))
            payload = {'pid': rid, 'name': name or '', 'price': float(price or 0), 'barcode': barcode, 'sku': sku}
            it.setData(payload, Qt.ItemDataRole.UserRole)
            self._compl_model.appendRow(it)
        # Show popup
        try:
            self._completer.complete()
        except Exception:
            pass

    def _on_completer_activated(self, data):
        try:
            # data can be QModelIndex or string depending on signal binding
            if hasattr(data, 'data'):
                payload = data.data(Qt.ItemDataRole.UserRole)
            else:
                # Find first row text match (fallback)
                payload = None
                for r in range(self._compl_model.rowCount()):
                    idx = self._compl_model.index(r,0)
                    if self._compl_model.data(idx) == str(data):
                        payload = self._compl_model.data(idx, Qt.ItemDataRole.UserRole)
                        break
            if payload:
                self._add_item_row(payload['pid'], payload['name'], 1, payload['price'], sku=payload.get('sku'), barcode=payload.get('barcode'))
                self.search.clear()
        except Exception:
            pass

    def _on_search_return(self):
        # Let completer handle activation; otherwise fallback to barcode/name add
        self.on_add_from_search()

    def eventFilter(self, obj, event):
        # Keyboard navigation for the popup using the search line edit
        # Only intercept for navigation keys if completer popup is visible
        if obj is self.search:
            try:
                from PyQt6.QtCore import QEvent
                if event.type() == QEvent.Type.KeyPress:
                    key = event.key()
                    if key in (Qt.Key.Key_Escape,):
                        try:
                            self._completer.popup().hide()
                        except Exception:
                            pass
                        return False
            except Exception:
                pass
        return super().eventFilter(obj, event)

    # (No focusOut wrapper; Qt handles Popup close when clicking elsewhere)

    # ----- Hotel-style PDF generation -----
    def generate_invoice_pdf(self, pdf_path: str, items: list[dict]) -> bool:
        try:
            from fpdf import FPDF  # type: ignore
        except Exception:
            return False

        try:
            try:
                from num2words import num2words  # type: ignore
            except Exception:
                num2words = None  # optional
            # Gather context
            client_text = self.client_cb.currentText().strip() or 'Walk-in'
            currency = self.currency_combo.currentText()
            lang = 'fr' if (self.lang_combo.currentText() or '').lower().startswith('fr') else 'en'
            include_subject = self.include_subject.isChecked()
            subject = self.subject_field.text().strip()
            include_unit = self.include_unit_column.isChecked()
            # Totals
            # Parse from labels to avoid recompute drift
            def _parse_amount(lbl: QLabel) -> float:
                import re
                s = lbl.text().split(':',1)[-1].strip().split(' ')[0]
                s = s.replace(',','')
                try:
                    return float(s)
                except Exception:
                    return 0.0
            subtotal = _parse_amount(self.subtotal_label)
            tax_amount = _parse_amount(self.tax_label)
            total_amount = _parse_amount(self.total_label)

            # Strings
            strings = {
                'en': {
                    'invoice': 'INVOICE', 'invoice_details': 'Invoice Details:', 'billed_to': 'Billed To:',
                    'invoice_number': 'Invoice Number:', 'invoice_date': 'Invoice Date:', 'due_date': 'Due Date:',
                    'company': 'Company:', 'address': 'Address:', 'tax_id': 'ICE:', 'stay_details': 'Invoice Items:',
                    'check_in': 'Description', 'check_out': 'Quantity', 'nights': 'Unit Price', 'total': 'Line Total',
                    'subtotal': 'Subtotal', 'total_due': 'Total Due', 'total_in_words': 'This invoice has been finalized in the amount of',
                    'thank_you': 'Thank you for your business.'
                },
                'fr': {
                    'invoice': 'FACTURE', 'invoice_details': 'Détails de la facture:', 'billed_to': 'Facturé à:',
                    'invoice_number': 'Numéro de facture:', 'invoice_date': 'Date de facture:', 'due_date': "Date d'échéance:",
                    'company': 'Société:', 'address': 'Adresse:', 'tax_id': 'ICE:', 'stay_details': 'Articles de la facture:',
                    'check_in': 'Description', 'check_out': 'Quantité', 'nights': 'Prix Unitaire', 'total': 'Total Ligne',
                    'subtotal': 'Sous-total', 'total_due': 'Total dû', 'total_in_words': 'Arrêté la présente facture à la somme de',
                    'thank_you': "Merci pour votre confiance."
                }
            }
            # PDF init
            pdf = FPDF(orientation='P', unit='mm', format='A4')
            pdf.add_page()
            y_margin = 6; x_margin = 10
            pdf.set_auto_page_break(auto=True, margin=y_margin)
            pdf.set_left_margin(x_margin); pdf.set_top_margin(y_margin); pdf.set_right_margin(x_margin)
            # Fonts
            main_font = 'Arial'
            try:
                import os
                font_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'fonts')
                # Try Alexandria Regular/Bold if available
                alex_reg = os.path.join(font_dir, 'Alexandria-Regular.ttf')
                alex_bold = os.path.join(font_dir, 'Alexandria-Bold.ttf')
                if os.path.exists(alex_reg) and os.path.exists(alex_bold):
                    pdf.add_font('alex', '', alex_reg, uni=True)
                    pdf.add_font('alex', 'B', alex_bold, uni=True)
                    main_font = 'alex'
            except Exception:
                pass
            page_width = pdf.w - 2 * pdf.l_margin
            # Logo header
            try:
                import os, tempfile
                icons_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'icons')
                logo_path = os.path.join(icons_dir, 'logo.png')
                if os.path.exists(logo_path):
                    logo_width = 40
                    x_logo = pdf.w - pdf.r_margin - logo_width
                    y_logo = y_margin
                    pdf.image(logo_path, x=x_logo, y=y_logo, w=logo_width)
            except Exception:
                pass
            # Title
            pdf.set_font(main_font, 'B', 24)
            pdf.cell(0, 15, strings[lang]['invoice'], 0, 1, 'C')
            if include_subject and subject:
                pdf.set_font(main_font, 'B', 12)
                pdf.cell(0, 10, f"Subject: {subject}", 0, 1, 'L')
                pdf.ln(2)
            # Two columns headers
            gap_width = page_width * 0.10; col_width = page_width * 0.45
            pdf.set_font(main_font, 'B', 12)
            pdf.set_fill_color(200, 220, 255)
            pdf.cell(col_width, 8, strings[lang]['invoice_details'], 0, 0, 'L', 1)
            pdf.cell(gap_width, 5, '', 0, 0, 'C')
            pdf.cell(col_width, 8, strings[lang]['billed_to'], 0, 1, 'L', 1)
            pdf.ln(1)
            pdf.set_font(main_font, '', 10)
            # Left column
            import datetime as _dt
            inv_no = 'N/A'
            pdf.cell(col_width, 5, f"{strings[lang]['invoice_number']} {inv_no}", 0, 0, 'L')
            pdf.cell(gap_width, 5, '', 0, 0, 'C')
            # Right column (client)
            pdf.cell(col_width, 5, client_text, 0, 1, 'L')
            pdf.cell(col_width, 5, f"{strings[lang]['invoice_date']} {_dt.datetime.now().strftime('%Y-%m-%d')}", 0, 0, 'L')
            pdf.cell(gap_width, 5, '', 0, 0, 'C')
            pdf.cell(col_width, 5, '', 0, 1, 'L')
            pdf.ln(1)
            # Items section
            pdf.set_font(main_font, 'B', 12)
            pdf.set_draw_color(200, 200, 200)
            pdf.cell(0, 10, strings[lang]['stay_details'], 0, 1, 'L')
            pdf.set_fill_color(200, 220, 255)
            pdf.set_text_color(0,0,0)
            # Table width and headers
            table_width = page_width
            if include_unit:
                headers = [strings[lang]['check_in'], strings[lang]['check_out'], 'Unit', strings[lang]['nights'], strings[lang]['total']]
                widths = [table_width*0.35, table_width*0.15, table_width*0.15, table_width*0.15, table_width*0.20]
                aligns = ['L','C','C','R','R']
            else:
                headers = [strings[lang]['check_in'], strings[lang]['check_out'], strings[lang]['nights'], strings[lang]['total']]
                widths = [table_width*0.45, table_width*0.20, table_width*0.15, table_width*0.20]
                aligns = ['L','C','R','R']
            def write_row(cells, widths, aligns, is_header=False, row_height=7, fill=False):
                for cell, w, al in zip(cells, widths, aligns):
                    pdf.set_font(main_font, 'B', 10 if is_header else 10)
                    pdf.cell(w, row_height, str(cell), 1, 0, al, fill)
                pdf.ln()
            write_row(headers, widths, aligns, is_header=True, row_height=7, fill=True)
            for idx, it in enumerate(items):
                fill = (idx % 2 == 1)
                if fill:
                    pdf.set_fill_color(229,231,233)
                else:
                    pdf.set_fill_color(255,255,255)
                name = it.get('name') or ''
                qty = float(it.get('qty') or 0)
                price = float(it.get('unit_price') or 0)
                line_total = qty*price
                if include_unit:
                    row = [name, f"{qty:g}", '', f"{price:,.2f} {currency}", f"{line_total:,.2f} {currency}"]
                else:
                    row = [name, f"{qty:g}", f"{price:,.2f} {currency}", f"{line_total:,.2f} {currency}"]
                write_row(row, widths, aligns, is_header=False, row_height=7, fill=True)
            pdf.ln(2)
            # Totals
            total_w = widths[-1]
            pdf.set_font(main_font, '', 10)
            pdf.cell(table_width-total_w, 8, strings[lang]['subtotal'], 1, 0, 'R')
            pdf.cell(total_w, 8, f"{subtotal:,.2f} {currency}", 1, 1, 'R')
            pdf.cell(table_width-total_w, 8, 'Tax', 1, 0, 'R')
            pdf.cell(total_w, 8, f"{tax_amount:,.2f} {currency}", 1, 1, 'R')
            pdf.set_font(main_font, 'B', 12)
            pdf.cell(table_width-total_w, 8, strings[lang]['total_due'], 1, 0, 'R', 1)
            pdf.cell(total_w, 8, f"{total_amount:,.2f} {currency}", 1, 1, 'R', 1)
            pdf.ln(3)
            # Amount in words
            if num2words is not None:
                int_part = int(total_amount)
                dec_part = int(round((total_amount - int_part)*100))
                try:
                    if lang=='fr':
                        int_words = num2words(int_part, lang='fr')
                        dec_words = num2words(dec_part, lang='fr') if dec_part else ''
                        words = f"{int_words} dirhams" + (f", et {dec_words} centimes" if dec_part else '')
                    else:
                        int_words = num2words(int_part, lang='en')
                        dec_words = num2words(dec_part, lang='en') if dec_part else ''
                        words = f"{int_words} dirhams" + (f", and {dec_words} centimes" if dec_part else '')
                    pdf.set_font(main_font, '', 10)
                    pdf.multi_cell(page_width, 5, f"{strings[lang]['total_in_words']} {words}.", 0, 'L')
                except Exception:
                    pass
            # Footer
            pdf.set_font(main_font, '', 9)
            pdf.set_y(pdf.h - pdf.b_margin - 24)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.ln(1)
            pdf.cell(0, 5, strings[lang]['thank_you'], 0, 1, 'C')
            pdf.output(pdf_path)
            return True
        except Exception:
            return False

    # ----- Inline PDF viewer (lite) -----
    def view_pdf_inline(self, pdf_path: str) -> bool:
        """Display PDF inline using the bundled PDF viewer. Returns True if shown."""
        try:
            dlg = InvoicePdfPreviewDialog(pdf_path, self)
        except ImportError:
            return False
        except Exception:
            return False
        if not getattr(dlg, 'is_valid', False):
            return False
        dlg.exec()
        return True

    # ----- i18n -----
    def retranslate_ui(self):
        # This can be expanded to use i18n keys; keeping simple for now
        self.search.setPlaceholderText('Search or scan product...')
        self.total_label.setText(self.total_label.text())
