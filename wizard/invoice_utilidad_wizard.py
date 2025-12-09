# -*- coding: utf-8 -*-

import base64
from io import BytesIO
from datetime import datetime, timedelta

import xlsxwriter

from odoo import fields, models, api, _


class XlsInvoiceLineasFac(models.TransientModel):
    _name = "xls.invoice.lineasfac"
    _description = "Invoice Líneas"

    fecha_ini = fields.Date(string='Fecha inicial', required=True)
    fecha_fin = fields.Date(string='Fecha final', required=True)
    no_resultado = fields.Boolean(string='No Result', default=False)
    file_data = fields.Binary("File Data")
    tipo_factura = fields.Selection(
        selection=[
            ('out_invoice', 'Clientes'),
            ('in_invoice', 'Proveedor'),
        ],
        string=_('Tipo de factura'),
        default='out_invoice',
        required=True,
    )

    def get_lines(self):
        self.ensure_one()
        lines = []

        domain = [
            ('invoice_date', '>=', self.fecha_ini),
            ('invoice_date', '<=', self.fecha_fin),
            ('move_type', '=', self.tipo_factura),
            ('state', '=', 'posted'),
        ]

        invoices = self.env['account.move'].search(domain)

        if not invoices:
            self.no_resultado = True
            return lines

        for invoice in invoices:

            # Variables que antes usabas, las dejo por si luego las ocupas
            EI = IU = ID = IT = 0.0

            for line in invoice.invoice_line_ids:
                # Estos campos dependen normalmente del módulo CFDI que uses
                # Si en 19 no existe 'impuesto', comenta este bloque.
                if line.tax_ids and hasattr(line.tax_ids, 'impuesto'):
                    if line.tax_ids.impuesto == '002':
                        if line.tax_ids.amount == 0.0:
                            IU += ((line.price_unit * line.quantity) * (line.tax_ids.amount / 100))
                        elif line.tax_ids.amount == 16:
                            ID += ((line.price_unit * line.quantity) * (line.tax_ids.amount / 100))
                    elif line.tax_ids.impuesto == '003':
                        IT += ((line.price_unit * line.quantity) * (line.tax_ids.amount / 100))

                # Campo tipo_comprobante también suele venir de módulo CFDI
                comproban = ''
                if hasattr(invoice, 'tipo_comprobante'):
                    if invoice.tipo_comprobante == 'I':
                        comproban = 'Ingreso'
                    elif invoice.tipo_comprobante == 'E':
                        comproban = 'Egreso'
                    elif invoice.tipo_comprobante == 'T':
                        comproban = 'Traslado'

                vals = {
                    'folio': invoice.name or '',
                    'cliente': invoice.partner_id.name or '',
                    'fecha': invoice.invoice_date,
                    'vencimiento': invoice.invoice_date_due,
                    'cantidad': line.quantity or 0.0,
                    'codigo': line.product_id.default_code or '',
                    'nombre': line.product_id.name or '',
                    'unitario': line.price_unit or 0.0,
                    'subtotal': line.price_subtotal or 0.0,
                    'impuesto': (line.price_total or 0.0) - (line.price_subtotal or 0.0),
                    'total': line.price_total or 0.0,
                    'estado': invoice.state or '',
                    'pago': invoice.payment_state or '',
                    'ref': invoice.ref or '',
                }
                lines.append(vals)

        return lines

    def print_xls_lineas(self):
        self.ensure_one()
        lines = self.get_lines()

        if not lines:
            # No hay resultados: marcar flag y solo recargar el wizard
            self.no_resultado = True
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'new',
            }

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Reporte de Lineas de factura')

        # Formatos
        bold_centered_format = workbook.add_format(
            {'bold': True, 'font_size': 12, 'align': 'center'}
        )
        header_format = workbook.add_format(
            {'bold': True, 'font_size': 10, 'align': 'center'}
        )
        num_format_currency = workbook.add_format(
            {'num_format': '$#,##0.00', 'align': 'right'}
        )
        num_format_qty = workbook.add_format(
            {'num_format': '#,##0.00', 'align': 'right'}
        )
        text_center = workbook.add_format({'align': 'center'})
        date_format = workbook.add_format(
            {'num_format': 'dd/mm/yyyy', 'align': 'center'}
        )

        # Ancho de columnas
        worksheet.set_column(0, 0, 15)   # Folio
        worksheet.set_column(1, 1, 25)   # Cliente
        worksheet.set_column(2, 3, 12)   # Fechas
        worksheet.set_column(4, 4, 10)   # Cantidad
        worksheet.set_column(5, 5, 15)   # Código
        worksheet.set_column(6, 6, 40)   # Descripción
        worksheet.set_column(7, 10, 15)  # precios y totales
        worksheet.set_column(11, 13, 18) # estados y referencia

        # Título
        worksheet.merge_range(0, 0, 0, 1, 'Líneas de factura', bold_centered_format)

        # Encabezados
        row = 2
        worksheet.write(row, 0, 'Folio', header_format)
        worksheet.write(row, 1, 'Cliente', header_format)
        worksheet.write(row, 2, 'Fecha', header_format)
        worksheet.write(row, 3, 'Vencimiento', header_format)
        worksheet.write(row, 4, 'Cantidad', header_format)
        worksheet.write(row, 5, 'Código', header_format)
        worksheet.write(row, 6, 'Descripción', header_format)
        worksheet.write(row, 7, 'Precio unitario', header_format)
        worksheet.write(row, 8, 'Subtotal', header_format)
        worksheet.write(row, 9, 'Impuestos', header_format)
        worksheet.write(row, 10, 'Total', header_format)
        worksheet.write(row, 11, 'Estado factura', header_format)
        worksheet.write(row, 12, 'Estado pago', header_format)
        if self.tipo_factura == 'out_invoice':
            worksheet.write(row, 13, 'Referencia de cliente', header_format)
        else:
            worksheet.write(row, 13, 'Referencia de factura', header_format)

        # Datos
        row += 1
        for res in lines:
            worksheet.write(row, 0, res['folio'], text_center)
            worksheet.write(row, 1, res['cliente'])

            if res['fecha']:
                worksheet.write_datetime(row, 2, datetime.combine(res['fecha'], datetime.min.time()), date_format)
            else:
                worksheet.write(row, 2, '', text_center)

            if res['vencimiento']:
                worksheet.write_datetime(row, 3, datetime.combine(res['vencimiento'], datetime.min.time()), date_format)
            else:
                worksheet.write(row, 3, '', text_center)

            worksheet.write_number(row, 4, float(res['cantidad']), num_format_qty)
            worksheet.write(row, 5, res['codigo'], text_center)
            worksheet.write(row, 6, res['nombre'])
            worksheet.write_number(row, 7, float(res['unitario']), num_format_currency)
            worksheet.write_number(row, 8, float(res['subtotal']), num_format_currency)
            worksheet.write_number(row, 9, float(res['impuesto']), num_format_currency)
            worksheet.write_number(row, 10, float(res['total']), num_format_currency)
            worksheet.write(row, 11, res['estado'], text_center)
            worksheet.write(row, 12, res['pago'], text_center)
            worksheet.write(row, 13, res['ref'] or '', text_center)
            row += 1

        workbook.close()
        output.seek(0)
        data = output.read()
        output.close()

        self.file_data = base64.b64encode(data)

        # Usamos la misma URL que ya tenías, pero apuntando a .xlsx
        action = {
            'name': 'Líneas de factura',
            'type': 'ir.actions.act_url',
            'url': "/web/content/?model="
                   + self._name
                   + "&id="
                   + str(self.id)
                   + "&field=file_data&download=true&filename=lineas_factura.xlsx",
            'target': 'self',
        }
        return action