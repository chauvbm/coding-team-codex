# Invoice lookup contract s1
Provide invoice_total(invoices, tenant, invoice_id) in billing.py. Each record has tenant, id, and amount (integer cents). Return the matching amount. Invoice IDs may repeat across tenants; lookup must never return another tenant data. Missing invoice raises KeyError. Inputs are not mutated. No dependencies or external services.
