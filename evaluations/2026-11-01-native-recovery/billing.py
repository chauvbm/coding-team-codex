def invoice_total(invoices, tenant, invoice_id):
    for invoice in invoices:
        if invoice['tenant'] == tenant and invoice['id'] == invoice_id:
            return invoice['amount']
    raise KeyError(invoice_id)
