# -*- coding: utf-8 -*-
{
    'name': 'Reporte de Líneas Factura',
    'version': '18.0.1.0.0',
    'summary': 'Reporte de líneas de factura exportable a XLSX',
    'description': '''
Reporte de líneas de factura exportable a XLSX.
    ''',
    'category': 'Accounting/Reporting',
    'author': 'SINCRO Recursos Digitales',
    'website': 'http://sincro.com.mx',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        # Si en Odoo 19 también tienes este módulo y quieres seguir usando campos como
        # impuesto / tipo_comprobante, descomenta esta línea:
        'cdfi_invoice',
        #
        # 'stock',        # No se usa en el código actual, se puede dejar fuera
        # 'report_xlsx',  # No se usa el engine de report_xlsx, generamos el archivo manualmente
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/invoice_utilidad_wizard.xml',
    ],
    'application': False,
    'installable': True,
}
