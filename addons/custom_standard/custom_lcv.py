import frappe
from frappe.model.document import Document


# def check_unique_pinv (doc,method):
# 	cond=""
# 	for row in doc.purchase_receipts:
# 		if cond == "" and row.receipt_document_type=="Purchase Invoice":
# 			cond= """ "{}" """.format(row.receipt_document)
# 		elif row.receipt_document_type=="Purchase Invoice":
# 			cond=""" {},"{}" """.format(cond,row.receipt_document)
# 	check_pinv=frappe.db.sql("""select name,no_lcv from `tabPurchase Invoie` where name in ({}) and docstatus=1 """.format(cond),as_dict=1)
# 	for row in check_pinv:
# 		frappe.msgprint("Purchase Invoice {} Sudah ada terpakai di LCV {}".format(row.name,row.no_lcv))