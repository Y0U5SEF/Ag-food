"""
Language manager providing simple dictionary-based translations and RTL handling.
"""

from typing import Dict


class LanguageManager:
    """Minimal i18n layer for the app."""

    SUPPORTED = {
        'en': 'English',
        'fr': 'Français',
        'ar': 'العربية',
    }

    def __init__(self) -> None:
        self._lang = 'en'
        # Keys are semantic identifiers used across the UI
        self._translations: Dict[str, Dict[str, str]] = {
            'en': {
                'app.window_title': 'AG Food - Stock & Invoice Manager',
                'nav.stock_management': 'Stock Management',
                'nav.invoice_generation': 'Invoice Generation',
                'nav.inventory_control': 'Inventory Control',
                'nav.order_processing': 'Order Processing',
                'nav.supplier_management': 'Supplier Management',
                'nav.reports_analytics': 'Reports & Analytics',
                'nav.quality_control': 'Quality Control',
                'nav.settings': 'Settings',
                'settings.tab.general': 'General',
                'settings.language.label': 'Application Language',
                'settings.language.description': 'Choose the language for the app UI.',
                'content.stock.placeholder': 'Stock Management UI will be here.',
                'content.invoice.placeholder': 'Invoice Generation UI will be here.',
                'content.settings.placeholder': 'Settings UI will be here.',
            },
            'fr': {
                'app.window_title': 'AG Food - Gestion de Stock et Factures',
                'nav.stock_management': 'Gestion des stocks',
                'nav.invoice_generation': 'Génération de factures',
                'nav.inventory_control': 'Contrôle d’inventaire',
                'nav.order_processing': 'Traitement des commandes',
                'nav.supplier_management': 'Gestion des fournisseurs',
                'nav.reports_analytics': 'Rapports et analyses',
                'nav.quality_control': 'Contrôle qualité',
                'nav.settings': 'Paramètres',
                'settings.tab.general': 'Général',
                'settings.language.label': 'Langue de l’application',
                'settings.language.description': 'Choisissez la langue de l’interface.',
                'content.stock.placeholder': 'L’interface de gestion des stocks sera ici.',
                'content.invoice.placeholder': 'L’interface de génération de factures sera ici.',
                'content.settings.placeholder': 'L’interface des paramètres sera ici.',
            },
            'ar': {
                'app.window_title': 'AG Food - إدارة المخزون والفواتير',
                'nav.stock_management': 'إدارة المخزون',
                'nav.invoice_generation': 'إنشاء الفواتير',
                'nav.inventory_control': 'مراقبة المخزون',
                'nav.order_processing': 'معالجة الطلبات',
                'nav.supplier_management': 'إدارة المورّدين',
                'nav.reports_analytics': 'التقارير والتحليلات',
                'nav.quality_control': 'مراقبة الجودة',
                'nav.settings': 'الإعدادات',
                'settings.tab.general': 'عام',
                'settings.language.label': 'لغة التطبيق',
                'settings.language.description': 'اختر لغة واجهة المستخدم.',
                'content.stock.placeholder': 'واجهة إدارة المخزون ستكون هنا.',
                'content.invoice.placeholder': 'واجهة إنشاء الفواتير ستكون هنا.',
                'content.settings.placeholder': 'واجهة الإعدادات ستكون هنا.',
            },
        }

    def set_language(self, lang: str) -> None:
        if lang in self.SUPPORTED:
            self._lang = lang
        else:
            self._lang = 'en'

    def get_language(self) -> str:
        return self._lang

    def is_rtl(self) -> bool:
        return self._lang == 'ar'

    def tr(self, key: str) -> str:
        return self._translations.get(self._lang, {}).get(key, self._translations['en'].get(key, key))


# Global singleton for simplicity of access
language_manager = LanguageManager()

