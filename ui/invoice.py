"""
Invoice generation UI: build invoices linked to clients and stock.
"""

from typing import Optional
from PyQt6.QtCore import Qt, QSize, QPoint
from PyQt6.QtCore import QFile
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit, QToolButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QComboBox, QLabel,
    QSpinBox, QDoubleSpinBox, QDialog, QDialogButtonBox, QSizePolicy, QGroupBox, QCheckBox, QPushButton, QAbstractItemView, QFileDialog
)
from PyQt6.QtWidgets import QStyle
from PyQt6.QtGui import QIntValidator
from i18n.language_manager import language_manager as i18n
import tempfile
import arabic_reshaper
from bidi.algorithm import get_display


from typing import Optional
from PyQt6.QtCore import Qt, QSize, QPoint, QTimer, QModelIndex
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QToolButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QComboBox, QLabel,
    QSpinBox, QDoubleSpinBox, QDialog, QDialogButtonBox, QSizePolicy, QGroupBox, QCheckBox, QPushButton
)
from PyQt6.QtGui import QIntValidator, QIcon, QAction, QColor
from PyQt6.QtWidgets import QStyle, QFileDialog
from PyQt6.QtPrintSupport import QPrinter, QPrinterInfo, QPrintDialog

class InvoicePdfPreviewDialog(QDialog):
    """Minimal PDF viewer used for inline invoice previews with print support."""

    def __init__(self, pdf_path: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        try:
            from PyQt6.QtPdf import QPdfDocument
            from PyQt6.QtPdfWidgets import QPdfView
        except Exception as exc:
            raise ImportError('QtPdf components are not available') from exc

        self._pdf_doc_cls = QPdfDocument
        self._pdf_view_cls = QPdfView
        self._pdf_path = pdf_path

        self.setWindowTitle('Invoice Preview')
        self.setModal(True)

        self._valid = True
        self._document_ready = False
        self._page_count = 0

        self.document = QPdfDocument(self)
        self.view = QPdfView(self)
        self.view.setDocument(self.document)
        try:
            self.view.setPageMode(QPdfView.PageMode.MultiPageVertical)
        except Exception:
            pass
        try:
            self.view.setZoomMode(QPdfView.ZoomMode.FitInView)
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
        self.prev_btn.setIcon(self._load_icon(['previous.svg']))
        self.prev_btn.setAutoRaise(True)
        self.prev_btn.setToolTip('Previous page')

        self.next_btn = QToolButton(self)
        self.next_btn.setIcon(self._load_icon(['next.svg']))
        self.next_btn.setAutoRaise(True)
        self.next_btn.setToolTip('Next page')

        self.page_input = QLineEdit(self)
        self.page_input.setPlaceholderText('Page')
        self.page_input.setFixedWidth(70)
        self.page_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_input.setValidator(QIntValidator(1, 9999, self))
        self.page_input.setEnabled(False)

        self.zoom_in_btn = QToolButton(self)
        self.zoom_in_btn.setIcon(self._load_icon(['zoom_in.svg']))
        self.zoom_in_btn.setAutoRaise(True)
        self.zoom_in_btn.setToolTip('Zoom in')

        self.zoom_out_btn = QToolButton(self)
        self.zoom_out_btn.setIcon(self._load_icon(['zoom_out.svg']))
        self.zoom_out_btn.setAutoRaise(True)
        self.zoom_out_btn.setToolTip('Zoom out')

        self.zoom_reset_btn = QToolButton(self)
        self.zoom_reset_btn.setIcon(self._load_icon(['zoom_to_extents.svg']))
        self.zoom_reset_btn.setAutoRaise(True)
        self.zoom_reset_btn.setToolTip('Reset zoom')
        
        # New: Print Button
        self.print_btn = QPushButton(self)
        self.print_btn.setIcon(self._load_icon(['print.svg']))
        self.print_btn.setText('Print')
        self.print_btn.setToolTip('Print invoice')
        self.printer_combo = QComboBox(self)
        self.printer_combo.setToolTip('Select a printer')

        toolbar_layout.addWidget(self.prev_btn)
        toolbar_layout.addWidget(self.next_btn)
        toolbar_layout.addWidget(self.page_input)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self.zoom_in_btn)
        toolbar_layout.addWidget(self.zoom_out_btn)
        toolbar_layout.addWidget(self.zoom_reset_btn)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self.printer_combo)
        toolbar_layout.addWidget(self.print_btn)

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
        self.print_btn.clicked.connect(self._do_print)

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

        # Dialog size settings - adjust these values to change window dimensions
        self.setMinimumSize(1000, 700)  # Minimum width: 1000px, height: 700px
        self.resize(1200, 900)  # Default width: 1200px, height: 900px
        self._load_printers()

    def _get_icons_path(self) -> str:
        """Get the path to the icons directory."""
        try:
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            return os.path.join(project_root, "icons")
        except Exception:
            return "icons"

    def _load_icon(self, candidates: list[str]):
        """Load an icon from the icons directory."""
        import os
        from PyQt6.QtGui import QIcon
        base = self._get_icons_path()
        for name in candidates:
            p = os.path.join(base, name)
            if os.path.exists(p):
                return QIcon(p)
        return QIcon()

    def _load_printers(self):
        self.printer_combo.clear()
        printers = QPrinterInfo.availablePrinters()
        if not printers:
            self.printer_combo.addItem('No printers found')
            self.print_btn.setEnabled(False)
            return

        for printer in printers:
            self.printer_combo.addItem(printer.printerName(), printer)
            if printer.isDefault():
                self.printer_combo.setCurrentText(printer.printerName())
        self.print_btn.setEnabled(True)
        
    def _do_print(self):
        printer_info = self.printer_combo.currentData()
        if not printer_info:
            QMessageBox.warning(self, "Print Error", "No printer selected.")
            return

        try:
            printer = QPrinter(printer_info)
            if not printer.isValid():
                QMessageBox.warning(self, "Print Error", "Invalid printer.")
                return

            dialog = QPrintDialog(printer, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Use the printer's print method instead of view.print
                try:
                    # Use QPrinter's print method instead
                    printer.setOutputFileName("")  # Reset to print to printer, not file
                    # Fallback to view.print if document.print is not available
                    try:
                        # Use the printer's print method directly
                        pass
                    except Exception as e:
                        QMessageBox.critical(self, "Print Error", f"An error occurred during printing: {e}")
                except Exception as e:
                    QMessageBox.critical(self, "Print Error", f"An error occurred during printing: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Print Error", f"An error occurred during printing: {e}")

    # The rest of the methods remain the same as the original code
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

    # ----- PDF generation -----
    def generate_pdf(self, pdf_path: str, business_info: dict) -> bool:
        """Generate a PDF file from the current document. Returns True if successful."""
        try:
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)

            # Add business information
            pdf.cell(0, 10, business_info['name'], 0, 1, "C")
            pdf.cell(0, 5, business_info['address'], 0, 1, "C")

            # Add trade register number (RC) if available
            trade_reg = business_info.get('trade_register_number')
            if trade_reg:
                pdf.cell(0, 5, f"Registre de Commerce (RC): {trade_reg}", 0, 1, "L")
            
            # Close the PDF document
            pdf.output(pdf_path)
            return True
        except Exception:
            return False

    # ----- i18n -----
    def retranslate_ui(self):
        # This can be expanded to use i18n keys; keeping simple for now
        # Note: This method should be in InvoiceWidget class, not InvoicePdfPreviewDialog
        pass

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
            if self.view.zoomMode() == self._pdf_view_cls.ZoomMode.FitInView:
                suffix = ' (Fit page)'
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
            self.view.setZoomMode(self._pdf_view_cls.ZoomMode.FitInView)
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
                    result = getter()
                    if result is not None:
                        return int(result)
                    return 0
                except (ValueError, TypeError):
                    return 0
                except Exception:
                    pass
        getter = getattr(self.view, 'page', None)
        if callable(getter):
            try:
                result = getter()
                if result is not None:
                    return int(result)
                return 0
            except (ValueError, TypeError):
                return 0
            except Exception:
                pass
        return 0

    def _get_page_count(self) -> int:
        try:
            return max(int(self.document.pageCount() or 0), 0)
        except Exception:
            return max(self._page_count, 0)
# class InvoicePdfPreviewDialog(QDialog):
#     """Minimal PDF viewer used for inline invoice previews."""

#     def __init__(self, pdf_path: str, parent: Optional[QWidget] = None):
#         super().__init__(parent)
#         try:
#             from PyQt6.QtPdf import QPdfDocument
#             from PyQt6.QtPdfWidgets import QPdfView
#         except Exception as exc:  # pragma: no cover - depends on QtPdf availability
#             raise ImportError('QtPdf components are not available') from exc

#         self._pdf_doc_cls = QPdfDocument
#         self._pdf_view_cls = QPdfView

#         self.setWindowTitle('Invoice Preview')
#         self.setModal(True)
        

#         self._valid = True
#         self._document_ready = False
#         self._page_count = 0

#         self.document = QPdfDocument(self)
#         self.view = QPdfView(self)
#         self.view.setDocument(self.document)
#         try:
#             self.view.setPageMode(QPdfView.PageMode.SinglePage)
#         except Exception:
#             pass
#         try:
#             self.view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
#         except Exception:
#             pass

#         self._nav = None
#         for attr in ('pageNavigator', 'pageNavigation'):
#             method = getattr(self.view, attr, None)
#             if callable(method):
#                 try:
#                     self._nav = method()
#                 except Exception:
#                     self._nav = None
#                 if self._nav is not None:
#                     break

#         main_layout = QVBoxLayout(self)
#         main_layout.setContentsMargins(12, 12, 12, 12)
#         main_layout.setSpacing(8)

#         toolbar_layout = QHBoxLayout()
#         toolbar_layout.setContentsMargins(0, 0, 0, 0)
#         toolbar_layout.setSpacing(6)

#         self.prev_btn = QToolButton(self)
#         self.prev_btn.setText('\u2b05\ufe0f')
#         self.prev_btn.setAutoRaise(True)
#         self.prev_btn.setToolTip('Previous page')

#         self.next_btn = QToolButton(self)
#         self.next_btn.setText('\u27a1\ufe0f')
#         self.next_btn.setAutoRaise(True)
#         self.next_btn.setToolTip('Next page')

#         self.page_input = QLineEdit(self)
#         self.page_input.setPlaceholderText('Page')
#         self.page_input.setFixedWidth(70)
#         self.page_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         self.page_input.setValidator(QIntValidator(1, 9999, self))
#         self.page_input.setEnabled(False)

#         self.zoom_in_btn = QToolButton(self)
#         self.zoom_in_btn.setText('\u2795')
#         self.zoom_in_btn.setAutoRaise(True)
#         self.zoom_in_btn.setToolTip('Zoom in')

#         self.zoom_out_btn = QToolButton(self)
#         self.zoom_out_btn.setText('\u2796')
#         self.zoom_out_btn.setAutoRaise(True)
#         self.zoom_out_btn.setToolTip('Zoom out')

#         self.zoom_reset_btn = QToolButton(self)
#         self.zoom_reset_btn.setText('\U0001f504')
#         self.zoom_reset_btn.setAutoRaise(True)
#         self.zoom_reset_btn.setToolTip('Reset zoom')

#         toolbar_layout.addWidget(self.prev_btn)
#         toolbar_layout.addWidget(self.next_btn)
#         toolbar_layout.addWidget(self.page_input)
#         toolbar_layout.addStretch(1)
#         toolbar_layout.addWidget(self.zoom_in_btn)
#         toolbar_layout.addWidget(self.zoom_out_btn)
#         toolbar_layout.addWidget(self.zoom_reset_btn)

#         main_layout.addLayout(toolbar_layout)
#         main_layout.addWidget(self.view, 1)

#         status_widget = QWidget(self)
#         status_layout = QHBoxLayout(status_widget)
#         status_layout.setContentsMargins(0, 0, 0, 0)
#         status_layout.setSpacing(6)

#         self.page_status = QLabel('Page - of -', status_widget)
#         self.zoom_status = QLabel('Zoom: --', status_widget)
#         self.zoom_status.setAlignment(Qt.AlignmentFlag.AlignRight)

#         status_layout.addWidget(self.page_status)
#         status_layout.addStretch(1)
#         status_layout.addWidget(self.zoom_status)
#         main_layout.addWidget(status_widget)

#         self.prev_btn.setEnabled(False)
#         self.next_btn.setEnabled(False)

#         self.prev_btn.clicked.connect(self._go_previous)
#         self.next_btn.clicked.connect(self._go_next)
#         self.page_input.returnPressed.connect(self._commit_page_input)
#         self.page_input.editingFinished.connect(self._commit_page_input)
#         self.zoom_in_btn.clicked.connect(self._zoom_in)
#         self.zoom_out_btn.clicked.connect(self._zoom_out)
#         self.zoom_reset_btn.clicked.connect(self._reset_zoom)

#         if self._nav is not None:
#             current_signal = getattr(self._nav, 'currentPageChanged', None)
#             if current_signal is not None:
#                 try:
#                     current_signal.connect(self._on_page_changed)
#                 except Exception:
#                     pass

#         for signal_name in ('zoomFactorChanged', 'zoomModeChanged'):
#             signal = getattr(self.view, signal_name, None)
#             if signal is not None:
#                 try:
#                     signal.connect(self._on_zoom_changed)
#                 except Exception:
#                     pass

#         page_count_signal = getattr(self.document, 'pageCountChanged', None)
#         if page_count_signal is not None:
#             try:
#                 page_count_signal.connect(self._on_page_count_changed)
#             except Exception:
#                 pass

#         self.document.statusChanged.connect(self._on_document_status)
#         try:
#             self.document.load(pdf_path)
#         except Exception:
#             self._valid = False
#         self._on_document_status(self.document.status())

#         self.setMinimumSize(720, 520)
#         self.resize(900, 700)

#     @property
#     def is_valid(self) -> bool:
#         if not self._valid:
#             return False
#         if not self._document_ready:
#             return True
#         return self._page_count > 0

#     def _on_document_status(self, status) -> None:
#         if status == self._pdf_doc_cls.Status.Error:
#             self._valid = False
#             return
#         if status == self._pdf_doc_cls.Status.Ready:
#             self._initialize_document()

#     def _initialize_document(self) -> None:
#         if self._document_ready:
#             return
#         count = int(self.document.pageCount() or 0)
#         if count <= 0:
#             self._valid = False
#             return
#         self._document_ready = True
#         self._page_count = count
#         self.page_input.setEnabled(True)
#         self._set_page(0)
#         self._update_zoom_label()

#     def _on_page_changed(self, *_) -> None:
#         if not self._document_ready:
#             return
#         self._update_page_display()
#         self._update_nav_state()

#     def _on_page_count_changed(self, *_) -> None:
#         if not self._document_ready:
#             return
#         self._page_count = max(int(self.document.pageCount() or 0), 0)
#         self._update_nav_state()
#         self._update_page_display()

#     def _on_zoom_changed(self, *_) -> None:
#         self._update_zoom_label()

#     def _update_page_display(self) -> None:
#         count = self._get_page_count()
#         if count <= 0:
#             self.page_status.setText('Page - of -')
#             return
#         current = self._get_current_page()
#         self.page_status.setText(f'Page {current + 1} of {count}')
#         blocked = self.page_input.blockSignals(True)
#         self.page_input.setText(str(current + 1))
#         self.page_input.blockSignals(blocked)

#     def _update_nav_state(self) -> None:
#         count = self._get_page_count()
#         current = self._get_current_page()
#         enabled = self._document_ready and count > 0
#         self.prev_btn.setEnabled(enabled and current > 0)
#         self.next_btn.setEnabled(enabled and (current + 1) < count)

#     def _update_zoom_label(self) -> None:
#         try:
#             zoom = float(self.view.zoomFactor())
#         except Exception:
#             zoom = 1.0
#         if zoom <= 0:
#             zoom = 1.0
#         suffix = ''
#         try:
#             if self.view.zoomMode() == self._pdf_view_cls.ZoomMode.FitToWidth:
#                 suffix = ' (Fit width)'
#         except Exception:
#             pass
#         percent = int(round(zoom * 100))
#         self.zoom_status.setText(f'Zoom: {percent}%{suffix}')

#     def _go_previous(self) -> None:
#         self._set_page(self._get_current_page() - 1)

#     def _go_next(self) -> None:
#         self._set_page(self._get_current_page() + 1)

#     def _commit_page_input(self) -> None:
#         if not self._document_ready:
#             return
#         text = self.page_input.text().strip()
#         if not text:
#             self._update_page_display()
#             return
#         try:
#             target = int(text) - 1
#         except ValueError:
#             self._update_page_display()
#             return
#         self._set_page(target)

#     def _set_page(self, index: int) -> None:
#         if not self._document_ready:
#             return
#         count = self._get_page_count()
#         if count <= 0:
#             return
#         index = max(0, min(index, count - 1))
#         if self._nav is not None:
#             setter = getattr(self._nav, 'setCurrentPage', None)
#             if callable(setter):
#                 try:
#                     setter(index)
#                 except Exception:
#                     pass
#             else:
#                 jumper = getattr(self._nav, 'jump', None)
#                 if callable(jumper):
#                     try:
#                         jumper(index)
#                     except Exception:
#                         pass
#         else:
#             set_page = getattr(self.view, 'setPage', None)
#             if callable(set_page):
#                 try:
#                     set_page(index)
#                 except Exception:
#                     pass
#         self._update_page_display()
#         self._update_nav_state()

#     def _zoom_in(self) -> None:
#         self._apply_zoom_scale(1.2)

#     def _zoom_out(self) -> None:
#         self._apply_zoom_scale(1 / 1.2)

#     def _apply_zoom_scale(self, factor: float) -> None:
#         try:
#             self.view.setZoomMode(self._pdf_view_cls.ZoomMode.Custom)
#         except Exception:
#             pass
#         try:
#             current = float(self.view.zoomFactor())
#         except Exception:
#             current = 1.0
#         if current <= 0:
#             current = 1.0
#         new_factor = max(0.2, min(current * factor, 5.0))
#         try:
#             self.view.setZoomFactor(new_factor)
#         except Exception:
#             pass
#         self._update_zoom_label()

#     def _reset_zoom(self) -> None:
#         try:
#             self.view.setZoomMode(self._pdf_view_cls.ZoomMode.FitToWidth)
#         except Exception:
#             try:
#                 self.view.setZoomFactor(1.0)
#             except Exception:
#                 pass
#         self._update_zoom_label()

#     def _get_current_page(self) -> int:
#         if self._nav is not None:
#             getter = getattr(self._nav, 'currentPage', None)
#             if callable(getter):
#                 try:
#                     return int(getter())
#                 except Exception:
#                     pass
#         getter = getattr(self.view, 'page', None)
#         if callable(getter):
#             try:
#                 return int(getter())
#             except Exception:
#                 pass
#         return 0

#     def _get_page_count(self) -> int:
#         try:
#             return max(int(self.document.pageCount() or 0), 0)
#         except Exception:
#             return max(self._page_count, 0)


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

    def showEvent(self, a0):
        super().showEvent(a0)
        try:
            self._load_clients()
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

        # Main content area with two panels
        main_content_layout = QHBoxLayout()
        v.addLayout(main_content_layout)

        # Left panel for the invoice table
        invoice_panel = QWidget()
        invoice_layout = QVBoxLayout(invoice_panel)
        main_content_layout.addWidget(invoice_panel, 2) # Give more space to the invoice table

        # Right panel for the items list
        items_panel = QWidget()
        items_layout = QVBoxLayout(items_panel)
        main_content_layout.addWidget(items_panel, 1)

        # Filters row: client, location, product search
        filters = QHBoxLayout()
        self.client_cb = QComboBox(); self.client_cb.setEditable(True)
        self.location_cb = QComboBox(); self.location_cb.setEditable(False)
        self.search = QLineEdit(); self.search.setPlaceholderText('Search or scan product...')
        self.search.textChanged.connect(self._on_search_text_changed)

        # Add clear button to search bar
        clear_icon = self._load_icon(["clear_black.svg"])
        if not clear_icon.isNull():
            clear_action = QAction(clear_icon, "Clear search", self)
            clear_action.triggered.connect(self.search.clear)
            self.search.addAction(clear_action, QLineEdit.ActionPosition.TrailingPosition)

        filters.addWidget(QLabel('Client'))
        filters.addWidget(self.client_cb, 1)

        invoice_layout.addLayout(filters)

        # Items table
        self.table = QTableWidget(0, 7)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.verticalHeader().setVisible(False)
        # Increase row height for better visibility
        self.table.verticalHeader().setDefaultSectionSize(35)
        self.table.setHorizontalHeaderLabels([
            '#', 'Product', 'Qty', 'Unit', 'Unit Price', 'Line Total', 'Available'
        ])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        invoice_layout.addWidget(self.table)

        # Items panel content
        items_layout.addWidget(QLabel("Available Items"))
        items_filters = QHBoxLayout()
        items_layout.addLayout(items_filters)
        items_filters.addWidget(self.search, 1)
        items_filters.addWidget(self.location_cb, 0)

        self.items_table = QTableWidget(0, 3)
        self.items_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.items_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.setHorizontalHeaderLabels(['Product', 'Price', 'Available'])
        h = self.items_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        items_layout.addWidget(self.items_table)

        add_item_button = QPushButton("Add to Invoice")
        add_item_button.clicked.connect(self.on_add_item_from_panel)
        items_layout.addWidget(add_item_button)

        self.items_table.doubleClicked.connect(self._on_items_table_double_clicked)

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
        self.lang_combo = QComboBox(); self.lang_combo.addItems(['English', 'French', 'Arabic'])
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

    def _load_clients(self, *, preserve_selection: bool = True):
        prev_id = None
        prev_text = None
        if preserve_selection:
            try:
                prev_id = self.client_cb.currentData()
                prev_text = (self.client_cb.currentText() or '').strip()
            except Exception:
                prev_id = None
                prev_text = None
        try:
            self.client_cb.blockSignals(True)
            self.client_cb.clear()
            self.client_cb.addItem('(Walk-in)', userData=None)
            for cid, name, phone, email, city in (self.db.list_clients() or []):
                label = name if not phone else f"{name} ({phone})"
                self.client_cb.addItem(label, userData=cid)
            if preserve_selection:
                target_id = prev_id
                if target_id is not None:
                    idx = self.client_cb.findData(target_id)
                    if idx >= 0:
                        self.client_cb.setCurrentIndex(idx)
                    elif prev_text:
                        idx = self.client_cb.findText(prev_text)
                        if idx >= 0:
                            self.client_cb.setCurrentIndex(idx)
                elif prev_text:
                    idx = self.client_cb.findText(prev_text)
                    if idx >= 0:
                        self.client_cb.setCurrentIndex(idx)
        except Exception:
            pass
        finally:
            try:
                self.client_cb.blockSignals(False)
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
        pid = None; name = None; price = 0.0; sku=None; barcode=None; uom=None
        # Try barcode first
        try:
            rec = self.db.get_product_by_barcode(text)
            if rec:
                pid = int(rec[0]); barcode = rec[1]; sku = rec[2]; name = rec[3]; price = float(rec[7]); uom = rec[10] if len(rec) > 10 else None
        except Exception:
            rec = None
        if not pid:
            # Fallback: search by name/code
            try:
                rows = self.db.list_products(text, None) or []
                if rows:
                    pid = int(rows[0][0]); barcode = rows[0][1]; sku = rows[0][2]; name = rows[0][3]; price = float(rows[0][6]) if len(rows[0])>6 else 0.0; uom = rows[0][8] if len(rows[0]) > 8 else None
            except Exception:
                pass
        if not pid:
            QMessageBox.information(self, 'Invoice', 'Product not found')
            return
        # Ensure UOM is fetched from database
        if pid and not uom:
            try:
                product_data = self.db.get_product(pid)
                if product_data and len(product_data) > 10:
                    uom = product_data[10] or ''
            except Exception:
                uom = ''
        self._add_item_row(pid, name or '', 1, price, sku=sku, barcode=barcode, uom=uom)
        self.search.clear()

    def _add_item_row(self, product_id: int, name: str, qty: int | float, unit_price: float, *, sku: Optional[str] = None, barcode: Optional[str] = None, uom: Optional[str] = None):
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
        # unit column - non-editable text showing UOM from database
        unit_item = QTableWidgetItem(uom or '')
        unit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        unit_item.setFlags(unit_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(r, 3, unit_item)
        # price as non-editable item (not a spin box)
        price_item = QTableWidgetItem(f"{float(unit_price):,.2f}")
        price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        price_item.setFlags(price_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        price_item.setData(Qt.ItemDataRole.UserRole, float(unit_price))  # Store actual price value
        self.table.setItem(r, 4, price_item)
        # total item
        total_item = QTableWidgetItem(f"{float(qty)*float(unit_price):,.2f}"); total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter); total_item.setFlags(total_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(r, 5, total_item)
        # Available
        try:
            loc_id = self.location_cb.currentData()
            available = self.db.get_stock(product_id, loc_id)
            avail_item = QTableWidgetItem(str(available)); avail_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter); avail_item.setFlags(avail_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        except Exception:
            avail_item = QTableWidgetItem('')
        self.table.setItem(r, 6, avail_item)
        self._recompute_total()

    def _on_line_changed(self, row: int):
        # Update the line total cell when qty changes (price is now non-editable)
        try:
            qty_widget = self.table.cellWidget(row, 2)
            price_item = self.table.item(row, 4)
            qty = float(qty_widget.value()) if qty_widget else 0.0
            price = float(price_item.data(Qt.ItemDataRole.UserRole)) if price_item else 0.0
            total = qty * price
            self.table.item(row, 5).setText(f"{total:,.2f}")
        except Exception:
            pass
        self._recompute_total()

    def _recompute_total(self):
        subtotal = 0.0
        for r in range(self.table.rowCount()):
            try:
                qtyw = self.table.cellWidget(r,2)
                price_item = self.table.item(r,4)
                qty = float(qtyw.value()) if qtyw else 0.0
                price = float(price_item.data(Qt.ItemDataRole.UserRole)) if price_item else 0.0
                line = qty*price
                self.table.item(r,5).setText(f"{line:,.2f}")
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
                qty_widget = self.table.cellWidget(r, 2)
                qty = float(qty_widget.value()) if qty_widget else float(self.table.item(r, 2).text().replace(',', ''))
            except Exception:
                qty = 0.0
            try:
                price_item = self.table.item(r, 4)
                if price_item is None:
                    raise ValueError()
                data = price_item.data(Qt.ItemDataRole.UserRole)
                price = float(data) if data is not None else float(price_item.text().replace(',', ''))
            except Exception:
                price = 0.0
            try:
                unit_item = self.table.item(r, 3)
                uom = unit_item.text() if unit_item else ''
            except Exception:
                uom = ''
            items.append({'product_id': int(pid) if pid is not None else None, 'name': prod_item.text(), 'qty': qty, 'unit_price': price, 'uom': uom})
        return items

    def _selected_client_payload(self):
        """Return the current client selection as (id, name, details dict)."""
        raw_id = None
        try:
            raw_id = self.client_cb.currentData()
        except Exception:
            raw_id = None
        client_id = None
        if raw_id not in (None, ''):
            try:
                client_id = int(raw_id)
            except (TypeError, ValueError):
                client_id = None
        client_text = (self.client_cb.currentText() or '').strip()
        if client_text.startswith('(') and client_text.endswith(')'):
            client_text = client_text.strip('() ')
        client_record = None
        if client_id is not None:
            try:
                client_record = self.db.get_client(client_id)
            except Exception:
                client_record = None
                client_id = None
        display_name = client_text or ''
        if client_record and len(client_record) > 1:
            display_name = client_record[1] or display_name
        if not display_name:
            display_name = 'Walk-in'
        details = {'name': display_name}
        if client_record:
            index_map = {
                'phone': 2,
                'email': 3,
                'address_line': 4,
                'city': 5,
                'state': 6,
                'postal_code': 7,
                'country': 8,
            }
            for key, idx in index_map.items():
                if len(client_record) > idx and client_record[idx]:
                    details[key] = client_record[idx]
        return client_id, display_name, details

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
        removed_pids = set()
        for r in rows:
            item = self.table.item(r, 1)
            if item and item.data(Qt.ItemDataRole.UserRole):
                removed_pids.add(item.data(Qt.ItemDataRole.UserRole))
            self.table.removeRow(r)

        # Re-index numbers
        for r in range(self.table.rowCount()):
            self.table.setItem(r, 0, QTableWidgetItem(str(r+1)))
        self._recompute_total()

        # Un-highlight the removed items in the items_table
        for r in range(self.items_table.rowCount()):
            item = self.items_table.item(r, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) in removed_pids:
                for col in range(self.items_table.columnCount()):
                    self.items_table.item(r, col).setBackground(QColor('white'))

    def on_save(self):
        self._save_invoice(with_dialog=False)

    def on_save_as(self):
        self._save_invoice(with_dialog=True)

    def _save_invoice(self, *, with_dialog: bool) -> None:
        items = self._collect_items()
        if not items:
            QMessageBox.information(self, 'Invoice', 'Add at least one item')
            return
        client_id, client_name, client_details = self._selected_client_payload()
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
        inv_id = self.db.create_invoice(items, client_id=client_id, client_name=client_name or None, location_id=loc_id)
        if inv_id is None:
            QMessageBox.critical(self, 'Invoice', 'Failed to create invoice (insufficient stock?)')
            return
        invoice_number = f"INV-{inv_id}"
        invoice_date = None
        try:
            rec = self.db.get_invoice(inv_id)
            if rec and len(rec) > 1 and rec[1]:
                invoice_number = rec[1]
            if rec and len(rec) > 4 and rec[4]:
                invoice_date = rec[4]
        except Exception:
            pass
        invoice_meta = {
            'number': invoice_number,
            'date': invoice_date,
            'client': client_details,
        }
        out_path = chosen_path if (with_dialog and chosen_path) else os.path.join(out_dir, f"invoice_{invoice_number}.pdf")
        out_path = os.path.abspath(out_path)
        if with_dialog and chosen_path:
            os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
        ok = self.generate_invoice_pdf(out_path, items, invoice_meta=invoice_meta)
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
        _, _, client_details = self._selected_client_payload()
        invoice_meta = {
            'number': 'Draft',
            'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'client': client_details,
        }
        ok = self.generate_invoice_pdf(out_path, items, invoice_meta=invoice_meta)
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
                self.table.setItem(r, 6, QTableWidgetItem(str(available)))
        except Exception:
            pass

    def on_add_item_from_panel(self):
        selected_rows = self.items_table.selectionModel().selectedRows()
        if not selected_rows:
            return

        for row in selected_rows:
            pid = self.items_table.item(row.row(), 0).data(Qt.ItemDataRole.UserRole)
            name = self.items_table.item(row.row(), 0).text()
            price = float(self.items_table.item(row.row(), 1).text().replace(',', ''))
            uom = self.items_table.item(row.row(), 0).data(Qt.ItemDataRole.UserRole+1)
            self._add_item_row(pid, name, 1, price, uom=uom)

            # Highlight the added row in the items_table
            for r in range(self.items_table.rowCount()):
                item = self.items_table.item(r, 0)
                if item and item.data(Qt.ItemDataRole.UserRole) == pid:
                    for col in range(self.items_table.columnCount()):
                        self.items_table.item(r, col).setBackground(QColor('lightgreen'))
                    break # Exit loop once found and highlighted

    def _on_items_table_double_clicked(self, index: QModelIndex):
        row = index.row()
        pid = self.items_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        name = self.items_table.item(row, 0).text()
        price = float(self.items_table.item(row, 1).text().replace(',', ''))
        uom = self.items_table.item(row, 0).data(Qt.ItemDataRole.UserRole+1)
        self._add_item_row(pid, name, 1, price, uom=uom)

        # Highlight the added row in the items_table
        for r in range(self.items_table.rowCount()):
            item = self.items_table.item(r, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == pid:
                for col in range(self.items_table.columnCount()):
                    self.items_table.item(r, col).setBackground(QColor('lightgreen'))
                break # Exit loop once found and highlighted

    # ----- Inline search -----
    def _on_search_text_changed(self, text: str):
        text = (text or '').strip()
        # Query top matches and feed the items table
        try:
            rows = self.db.list_products(text if text else None, None) or []
        except Exception:
            rows = []
        
        # Get set of product IDs already in the invoice table for quick lookups
        added_product_ids = set()
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 1)  # Product name is in column 1
            if item and item.data(Qt.ItemDataRole.UserRole):
                added_product_ids.add(item.data(Qt.ItemDataRole.UserRole))

        # Rebuild model
        self.items_table.setRowCount(0)
        max_items = 100
        for rid, barcode, sku, name, category, qty, price, reorder_point, uom in rows[:max_items]:
            r = self.items_table.rowCount()
            self.items_table.insertRow(r)

            name_item = QTableWidgetItem(name or '')
            name_item.setData(Qt.ItemDataRole.UserRole, rid)
            name_item.setData(Qt.ItemDataRole.UserRole+1, uom)
            self.items_table.setItem(r, 0, name_item)

            price_item = QTableWidgetItem(f"{float(price or 0):,.2f}")
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.items_table.setItem(r, 1, price_item)

            available_item = QTableWidgetItem(str(qty))
            available_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.items_table.setItem(r, 2, available_item)

            # Highlight row if item is already in the invoice
            if rid in added_product_ids:
                for col in range(self.items_table.columnCount()):
                    self.items_table.item(r, col).setBackground(QColor('lightgreen'))



    # (No focusOut wrapper; Qt handles Popup close when clicking elsewhere)

    # ----- PDF generation -----
    def generate_invoice_pdf(self, pdf_path: str, items: list[dict], invoice_meta: Optional[dict] = None) -> bool:
        try:
            from fpdf import FPDF  # type: ignore
        except Exception:
            return False

        try:
            try:
                from num2words import num2words  # type: ignore
            except Exception:
                num2words = None  # optional
            meta = invoice_meta or {}
            client_details = meta.get('client') or {}
            # Gather context
            client_text = client_details.get('name') or self.client_cb.currentText().strip() or 'Walk-in'
            currency = self.currency_combo.currentText()
            lang = 'fr' if (self.lang_combo.currentText() or '').lower().startswith('fr') else 'ar' if (self.lang_combo.currentText() or '').lower().startswith('ar') else 'en'
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

            invoice_number = meta.get('number') or 'N/A'
            invoice_date_raw = meta.get('date')
            import datetime as _dt
            if invoice_date_raw:
                try:
                    invoice_date = _dt.datetime.fromisoformat(str(invoice_date_raw)).strftime('%Y-%m-%d')
                except Exception:
                    invoice_date = str(invoice_date_raw).split(' ')[0]
            else:
                invoice_date = _dt.datetime.now().strftime('%Y-%m-%d')

            # Strings
            strings = {
                'en': {
                    'invoice': 'INVOICE',
                    'invoice_details': 'Invoice Details:',
                    'billed_to': 'Billed To:',
                    'invoice_number': 'Invoice Number:',
                    'invoice_date': 'Invoice Date:',
                    'due_date': 'Due Date:',
                    'company': 'Company:',
                    'address': 'Address:',
                    'tax_id': 'ICE:',
                    'item_details': 'Invoice Items:',
                    'description': 'Description',
                    'quantity': 'Quantity',
                    'unit_price': 'Unit Price',
                    'total': 'Line Total',
                    'subtotal': 'Subtotal',
                    'total_due': 'Total Due',
                    'total_in_words': 'This invoice has been finalized in the amount of',
                    'thank_you': 'Thank you for your business.',
                    'phone': 'Phone:',
                    'email': 'Email:',
                    'uom': 'Unit'
                },
                'fr': {
                    'invoice': 'FACTURE',
                    'invoice_details': 'Détails de la facture:',
                    'billed_to': 'Facturé à:',
                    'invoice_number': 'Numéro de facture:',
                    'invoice_date': 'Date de facture:',
                    'due_date': "Date d'échéance:",
                    'company': 'Société:',
                    'address': 'Adresse:',
                    'tax_id': 'ICE:',
                    'item_details': 'Articles de la facture:',
                    'description': 'Description',
                    'quantity': 'Quantité',
                    'unit_price': 'Prix Unitaire',
                    'total': 'Total Ligne',
                    'subtotal': 'Sous-total',
                    'total_due': 'Total dû',
                    'total_in_words': 'Arrêté la présente facture à la somme de',
                    'thank_you': "Merci pour votre confiance.",
                    'phone': 'Telephone:',
                    'uom': 'Unité'
                },
                'ar': {
                    'invoice': 'فاتورة', 'invoice_details': 'تفاصيل الفاتورة:', 'billed_to': 'عميل:',
                    'invoice_number': 'رقم الفاتورة:', 'invoice_date': 'تاريخ الفاتورة:', 'due_date': 'تاريخ الاستحقاق:',
                    'company': 'الشركة:', 'address': 'العنوان:', 'tax_id': 'المعرف الضريبي:', 'item_details': 'تفاصيل الفاتورة:',
                    'description': 'البيان', 'quantity': 'الكمية', 'unit_price': 'سعر الوحدة', 'total': 'المجموع',
                    'subtotal': 'المجموع الفرعي', 'total_due': 'المبلغ الإجمالي', 'total_in_words': 'المبلغ الإجمالي بالحروف هو',
                    'thank_you': 'شكرا لتعاملكم معنا.', 'phone': 'الهاتف:', 'email': 'البريد الإلكتروني:', 'uom': 'الوحدة', 'tax': 'الضريبة'
                }
            }
            client_lines = [client_text]
            phone_val = client_details.get('phone')
            if phone_val:
                client_lines.append(f"{strings[lang]['phone']} {phone_val}")
            email_val = client_details.get('email')
            if email_val:
                client_lines.append(f"{strings[lang]['email']} {email_val}")
            address_parts = []
            for key in ('address_line', 'city', 'state', 'postal_code', 'country'):
                val = client_details.get(key)
                if val:
                    address_parts.append(str(val))
            if address_parts:
                client_lines.append(f"{strings[lang]['address']} {' '.join(address_parts)}")
            # PDF init
            pdf = FPDF(orientation='P', unit='mm', format='A4')
            pdf.add_page()
            y_margin = 6
            x_margin = 10
            pdf.set_auto_page_break(auto=True, margin=y_margin)
            pdf.set_left_margin(x_margin); pdf.set_top_margin(y_margin); pdf.set_right_margin(x_margin)
            # Fonts
            main_font = 'Arial'
            try:
                import os
                font_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'fonts')
                # Try Alexandria Regular/Bold if available
                alex_reg = os.path.join(font_dir, 'Alexandria-Regular.ttf')
                alex_bold = os.path.join(font_dir, 'Alexandria-Bold.ttf')
                calibri_reg = os.path.join(font_dir, 'calibri.ttf')
                calibri_bold = os.path.join(font_dir, 'calibrib.ttf')
                if os.path.exists(alex_reg) and os.path.exists(alex_bold):
                    pdf.add_font('alex', '', alex_reg, uni=True)
                    pdf.add_font('alex', 'B', alex_bold, uni=True)
                    pdf.add_font('calibri', '', calibri_reg, uni=True)
                    pdf.add_font('calibri', 'B', calibri_bold, uni=True)
                    main_font = 'calibri'
            except Exception:
                pass
            page_width = pdf.w - 2 * pdf.l_margin
            # Logo header
            # try:
            #     import os, tempfile
            #     icons_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'icons')
            #     logo_path = os.path.join(icons_dir, 'logo.png')
            #     if os.path.exists(logo_path):
            #         logo_width = 40
            #         x_logo = pdf.w - pdf.r_margin - logo_width
            #         y_logo = y_margin
            #         pdf.image(logo_path, x=x_logo, y=y_logo, w=logo_width)
            # except Exception:
            #     pass
            
            pdf.set_font(main_font, '', 10)
            logo_width = 50  # mm
            logo_path = "images/logo.png"
            qfile = QFile(logo_path)
            if qfile.open(QFile.OpenModeFlag.ReadOnly):
                data = qfile.readAll()
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(data.data())
                    tmp_path = tmp.name
                x_logo = pdf.w - pdf.r_margin - logo_width
                y_logo = y_margin
                try:
                    pdf.image(tmp_path, x=x_logo, y=y_logo, w=logo_width)
                    pdf.ln(logo_width * 0.2)
                except Exception:
                    pass
            pdf.set_font(main_font, 'B', 16)
            pdf.set_x(x_margin)
            pdf.set_y(y_margin)
            
            # Fetch business information from database
            business_info = self.db.get_business_info()
            
            # Use business name from database or fallback to hardcoded value
            business_name = business_info.get('business_name') if business_info.get('business_name') else "AG Food"
            business_name = get_display(arabic_reshaper.reshape(business_name))
            pdf.cell(page_width * 0.7, 10, business_name, 0, 1, "L")
            pdf.set_font(main_font, '', 10)
            
            # Add business address if available
            address_line = business_info.get('address_line')
            if address_line:
                address_line = get_display(arabic_reshaper.reshape(address_line))
                pdf.cell(0, 5, address_line, 0, 1, "L")
            
            # Add phone numbers if available
            phone_landline = business_info.get('phone_landline')
            phone_mobile = business_info.get('phone_mobile')
            
            if phone_landline:
                phone_landline = get_display(arabic_reshaper.reshape(phone_landline))
                pdf.cell(18, 5, "Tél", 0, 0, "L")
                pdf.cell(3, 5, ":", 0, 0, "L")
                pdf.cell(0, 5, phone_landline, 0, 1, "L")
            
            if phone_mobile and phone_mobile != phone_landline:
                phone_mobile = get_display(arabic_reshaper.reshape(phone_mobile))
                pdf.cell(18, 5, "Mobile", 0, 0, "L")
                pdf.cell(3, 5, ":", 0, 0, "L")
                pdf.cell(0, 5, phone_mobile, 0, 1, "L")
            
            # Add fax if available
            fax_number = business_info.get('fax_number')
            if fax_number:
                fax_number = get_display(arabic_reshaper.reshape(fax_number))
                pdf.cell(18, 5, "Fax", 0, 0, "L")
                pdf.cell(3, 5, ":", 0, 0, "L")
                pdf.cell(0, 5, fax_number, 0, 1, "L")
            
            # Add email if available
            email_address = business_info.get('email_address')
            if email_address:
                email_address = get_display(arabic_reshaper.reshape(email_address))
                pdf.cell(18, 5, "Courriel", 0, 0, "L")
                pdf.cell(3, 5, ":", 0, 0, "L")
                pdf.cell(0, 5, email_address, 0, 1, "L")
            
            pdf.ln(2)
            # Title
            pdf.set_font(main_font, 'B', 24)
            invoice_title = get_display(arabic_reshaper.reshape(strings[lang]['invoice']))
            pdf.cell(0, 15, invoice_title, 0, 1, 'C')
            if include_subject and subject:
                pdf.set_font(main_font, 'B', 12)
                subject = get_display(arabic_reshaper.reshape(subject))
                pdf.cell(0, 10, f"Subject: {subject}", 0, 1, 'L')
                pdf.ln(2)
            # Two columns headers
            global_row_height = 7
            gap_width = page_width * 0.10; col_width = page_width * 0.45
            pdf.set_font(main_font, 'B', 12)
            pdf.set_fill_color(200, 220, 255)
            invoice_details_title = get_display(arabic_reshaper.reshape(strings[lang]['invoice_details']))
            billed_to_title = get_display(arabic_reshaper.reshape(strings[lang]['billed_to']))
            if lang == "ar":
                pdf.cell(col_width, global_row_height, invoice_details_title, 0, 0, 'R', 1)
            else:
                pdf.cell(col_width, global_row_height, invoice_details_title, 0, 0, 'L', 1)
            pdf.cell(gap_width, 5, '', 0, 0, 'C')
            if lang == "ar":
                pdf.cell(col_width, global_row_height, billed_to_title, 0, 1, 'R', 1)
            else:
                pdf.cell(col_width, global_row_height, billed_to_title, 0, 1, 'L', 1)
            pdf.ln(1)
            pdf.set_font(main_font, '', 10)
            # Left/right columns with client details
            first_line = get_display(arabic_reshaper.reshape(client_lines[0])) if client_lines else ''
            invoice_number_text = get_display(arabic_reshaper.reshape(f"{strings[lang]['invoice_number']} {invoice_number}"))
            if lang == "ar":
                pdf.cell(col_width, 5, invoice_number_text, 0, 0, 'R')
            else:
                pdf.cell(col_width, 5, invoice_number_text, 0, 0, 'L')
            pdf.cell(gap_width, 5, '', 0, 0, 'C')
            pdf.cell(col_width, 5, first_line, 0, 1, 'L')
            invoice_date_text = get_display(arabic_reshaper.reshape(f"{strings[lang]['invoice_date']} {invoice_date}"))
            if lang == "ar":
                pdf.cell(col_width, 5, invoice_date_text, 0, 0, 'R')
            else:
                pdf.cell(col_width, 5, invoice_date_text, 0, 0, 'L')
            pdf.cell(gap_width, 5, '', 0, 0, 'C')
            remaining = client_lines[1:]
            if remaining:
                remaining_line = get_display(arabic_reshaper.reshape(remaining[0]))
                pdf.cell(col_width, 5, remaining_line, 0, 1, 'L')
                for line in remaining[1:]:
                    pdf.cell(col_width, 5, '', 0, 0, 'L')
                    pdf.cell(gap_width, 5, '', 0, 0, 'C')
                    line = get_display(arabic_reshaper.reshape(line))
                    pdf.cell(col_width, 5, line, 0, 1, 'L')
            else:
                pdf.cell(col_width, 5, '', 0, 1, 'L')
            pdf.ln(1)
            # Items section
            pdf.set_font(main_font, 'B', 12)
            pdf.set_draw_color(200, 200, 200)
            item_details_title = get_display(arabic_reshaper.reshape(strings[lang]['item_details']))
            pdf.set_font(main_font, 'B', 12)
            if lang == "ar":
                pdf.cell(0, 10, item_details_title, 0, 1, 'R')
            else:
                pdf.cell(0, 10, item_details_title, 0, 1, 'L')
            pdf.set_fill_color(200, 220, 255)
            pdf.set_text_color(0,0,0)
            # Table width and headers
            table_width = page_width
            if lang == 'ar':
                if include_unit:
                    headers = [strings[lang]['total'], strings[lang]['unit_price'], strings[lang]['quantity'], strings[lang]['uom'], strings[lang]['description'], '#']
                    widths = [table_width*0.18, table_width*0.15, table_width*0.15, table_width*0.12, table_width*0.35, table_width*0.05]
                    aligns = ['R','R','C','C','R','C']
                else:
                    headers = ['المجموع', 'سعر الوحدة', 'الكمية', 'البيان', '#']
                    widths = [table_width*0.18, table_width*0.15, table_width*0.15, table_width*0.47, table_width*0.05]
                    aligns = ['R','R','C','R','C']
            else:
                if include_unit:
                    headers = ['#', strings[lang]['description'], strings[lang]['quantity'], strings[lang]['uom'], strings[lang]['unit_price'], strings[lang]['total']]
                    widths = [table_width*0.05, table_width*0.35, table_width*0.15, table_width*0.12, table_width*0.15, table_width*0.18]
                    aligns = ['C','L','C','C','R','R']
                else:
                    headers = ['#', strings[lang]['description'], strings[lang]['quantity'], strings[lang]['unit_price'], strings[lang]['total']]
                    widths = [table_width*0.05, table_width*0.47, table_width*0.15, table_width*0.15, table_width*0.18]
                    aligns = ['C','L','C','R','R']
            def write_row(cells, widths, aligns, is_header=False, row_height=7, fill=False):
                for cell, w, al in zip(cells, widths, aligns):
                    pdf.set_font(main_font, 'B', 10 if is_header else 10)
                    cell = get_display(arabic_reshaper.reshape(str(cell)))
                    pdf.cell(w, row_height, cell, 1, 0, al, fill)
                pdf.ln()
            write_row(headers, widths, aligns, is_header=True, row_height=7, fill=True)
            def format_price(value, decimals=2):
                format_spec = f",.{decimals}f"
                return format(value, format_spec).replace(",", " ")

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
                
                # Get unit from item data (already fetched when item was added)
                unit = it.get('uom', '')
                
                # If for some reason UOM is not available in item data, fetch from database
                if not unit:
                    product_id = it.get('product_id')
                    if product_id:
                        try:
                            product_data = self.db.get_product(product_id)
                            if product_data and len(product_data) > 10:
                                unit = product_data[10] or ''
                        except Exception:
                            unit = ''
                
                if include_unit:
                    row = [str(idx + 1), name, unit, f"{qty:g}", f"{format_price(price)} {currency}", f"{format_price(line_total)} {currency}"]
                else:
                    row = [str(idx + 1), name, f"{qty:g}", f"{format_price(price)} {currency}", f"{format_price(line_total)} {currency}"]
                if lang == 'ar':
                    row.reverse()
                write_row(row, widths, aligns, is_header=False, row_height=7, fill=True)
            pdf.ln(2)
            # Totals
            total_w_ar = widths[0]
            total_w = widths[-1]
            pdf.set_font(main_font, '', 10)
            if lang == 'ar':
                subtotal_text = get_display(arabic_reshaper.reshape(strings[lang]['subtotal']))
                pdf.cell(total_w_ar, 8, f"{format_price(subtotal)} {currency}", 1, 0, 'L')
                pdf.cell(table_width-total_w_ar, 8, subtotal_text, 1, 1, 'L')
                tax_text = get_display(arabic_reshaper.reshape(strings[lang]['tax']))
                pdf.cell(total_w_ar, 8, f"{format_price(tax_amount)} {currency}", 1, 0, 'L')
                pdf.cell(table_width-total_w_ar, 8, tax_text, 1, 1, 'L')
                pdf.set_font(main_font, 'B', 12)
                total_due_text = get_display(arabic_reshaper.reshape(strings[lang]['total_due']))
                pdf.cell(total_w_ar, 8, f"{format_price(total_amount)} {currency}", 1, 0, 'L', 1)
                pdf.cell(table_width-total_w_ar, 8, total_due_text, 1, 1, 'L', 1)
            else:
                subtotal_text = strings[lang]['subtotal']
                pdf.cell(table_width-total_w, 8, subtotal_text, 1, 0, 'R')
                pdf.cell(total_w, 8, f"{format_price(subtotal)} {currency}", 1, 1, 'R')
                tax_text = 'Tax'
                pdf.cell(table_width-total_w, 8, tax_text, 1, 0, 'R')
                pdf.cell(total_w, 8, f"{format_price(tax_amount)} {currency}", 1, 1, 'R')
                pdf.set_font(main_font, 'B', 12)
                total_due_text = strings[lang]['total_due']
                pdf.cell(table_width-total_w, 8, total_due_text, 1, 0, 'R', 1)
                pdf.cell(total_w, 8, f"{format_price(total_amount)} {currency}", 1, 1, 'R', 1)
            pdf.ln(3)
            # Amount in words
            if num2words is not None:
                int_part = int(total_amount)
                dec_part = int(round((total_amount - int_part)*100))
                try:
                    if lang == 'ar':
                        int_words = num2words(int_part, lang='ar')
                        dec_words = num2words(dec_part, lang='ar') if dec_part else ''
                        words = f"{int_words} درهم" + (f" و {dec_words} سنتيم" if dec_part else '')
                    elif lang=='fr':
                        int_words = num2words(int_part, lang='fr')
                        dec_words = num2words(dec_part, lang='fr') if dec_part else ''
                        words = f"{int_words} dirhams" + (f", et {dec_words} centimes" if dec_part else '')
                    else:
                        int_words = num2words(int_part, lang='en')
                        dec_words = num2words(dec_part, lang='en') if dec_part else ''
                        words = f"{int_words} dirhams" + (f", and {dec_words} centimes" if dec_part else '')
                    pdf.set_font(main_font, '', 10)
                    total_in_words_text = get_display(arabic_reshaper.reshape(f"{strings[lang]['total_in_words']} {words}."))
                    if lang == "ar":
                        pdf.multi_cell(page_width, 5, total_in_words_text, 0, 'R')
                    else:
                        pdf.multi_cell(page_width, 5, total_in_words_text, 0, 'L')
                except Exception:
                    pass
            # Footer - Add business information from database
            pdf.set_font(main_font, '', 10)
            pdf.set_y(pdf.h - pdf.b_margin - 27)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.ln(1)
            
            # Add bank information if available
            bank_identity = business_info.get('bank_identity_statement')
            bank_name = business_info.get('bank_name')
            if bank_identity and bank_name:
                bank_text = get_display(arabic_reshaper.reshape(f"Relevé d'Identité Bancaire (RIB): {bank_identity} - {bank_name}"))
                pdf.cell(0, 5, bank_text, 0, 1, "L")
            elif bank_identity:
                bank_text = get_display(arabic_reshaper.reshape(f"Relevé d'Identité Bancaire (RIB): {bank_identity}"))
                pdf.cell(0, 5, bank_text, 0, 1, "L")
            
            # Add common company identifier (ICE) if available
            company_id = business_info.get('common_company_identifier')
            if company_id:
                company_id_text = get_display(arabic_reshaper.reshape(f"Identifiant Commun de l'Entreprise (ICE): {company_id}"))
                pdf.cell(0, 5, company_id_text, 0, 1, "L")
            
            # Add patente number if available
            patente = business_info.get('patente_number')
            if patente:
                patente_text = get_display(arabic_reshaper.reshape(f"Patente: {patente}"))
                pdf.cell(0, 5, patente_text, 0, 1, "L")
            
            # Add tax identifier (IF) if available
            tax_id = business_info.get('tax_identifier')
            if tax_id:
                tax_id_text = get_display(arabic_reshaper.reshape(f"Identifiant Fiscal (IF): {tax_id}"))
                pdf.cell(0, 5, tax_id_text, 0, 1, "L")
            
            # Add trade register number (RC) if available
            trade_reg = business_info.get('trade_register_number')
            if trade_reg:
                trade_reg_text = get_display(arabic_reshaper.reshape(f"Registre de Commerce (RC): {trade_reg}"))
                pdf.cell(0, 5, trade_reg_text, 0, 1, "L")

            pdf.output(pdf_path)
            return True
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False

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
