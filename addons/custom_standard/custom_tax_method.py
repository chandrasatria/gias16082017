import frappe,erpnext
from frappe.utils import flt
import json
@frappe.whitelist()
def check_tax_sales(self,method):
	tax_side = self.tax_or_non_tax
	for row in self.items:
		item_doc = frappe.get_doc("Item", row.item_code)

		if item_doc.tax_or_non_tax != tax_side:
			frappe.throw("{0} Item cant be in {1} transactions.".format(item_doc.tax_or_non_tax,tax_side))

	
	if tax_side == "Non Tax":
		self.taxes = []
		self.total_taxes_and_charges = 0


@frappe.whitelist()
def check_tax_from_sales_order(self,method):
	if self.is_return == 0:
		if self.tax_or_non_tax == "Non Tax":
			self.taxes = []
			
		for row in self.items:
			if row.against_sales_order:
				so = frappe.get_doc("Sales Order", row.against_sales_order)
				if len(so.taxes) != len(self.taxes):
					frappe.throw("Delivery Note has different taxes from Sales Order {}. Please check.".format(so.name))

@frappe.whitelist()
def check_tax_from_sales_order_inv(self,method):
	if self.is_return == 0:
		for row in self.items:
			if row.sales_order:
				so = frappe.get_doc("Sales Order", row.sales_order)
				if len(so.taxes) != len(self.taxes):
					pass
					# frappe.throw("Sales Invoice has different taxes from Sales Order {}. Please check.".format(so.name))

@frappe.whitelist()
def check_tax_payment(self,method):
	tax_side = self.tax_or_non_tax
	for row in self.references:
		# if row.reference_doctype in ("Sales Order", "Sales Invoice"):
		item_doc = frappe.get_doc(row.reference_doctype, row.reference_name)

		if item_doc.tax_or_non_tax != tax_side:
			frappe.throw("{0} Document cant be in {1} transactions.".format(item_doc.tax_or_non_tax,tax_side))

@frappe.whitelist()
def check_tax_cash_request(self,method):
	tax_side = self.tax_or_non_tax
	for row in self.list_invoice:
		trans_doc = frappe.get_doc("Purchase Invoice", row.document)

		if trans_doc.tax_or_non_tax != tax_side:
			frappe.throw("{0} Document cant be in {1} transactions.".format(trans_doc.tax_or_non_tax,tax_side))

# Item
# Sales Order
# Delivery Note
# Sales Invoice
# Payment Entry
# Stock Entry 
# Stock Reconciliation
# Journal Entry
# Cash Request

@frappe.whitelist()
def remove_tax_transactions():
	print(str(frappe.utils.get_url()))
	if "tax" in frappe.utils.get_url():
		# get all journal entry and delete them
		list_journal_entry = frappe.db.sql(""" SELECT name FROM `tabJournal Entry` WHERE tax_or_non_tax = "Non Tax" """,as_dict=1)
		list_je = []
		for row in list_journal_entry:
			if row.name not in list_je:
				list_je.append(row.name)
		if list_je:
			gabungan_je = str(list_je).replace("[","(").replace("]",")")
			
			frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no IN {} and voucher_type = "Journal Entry"  """.format(gabungan_je))
			frappe.db.sql(""" DELETE FROM `tabJournal Entry Account` WHERE parent IN {} """.format(gabungan_je))
			frappe.db.sql(""" DELETE FROM `tabJournal Entry` WHERE name IN {} """.format(gabungan_je))

		# get all stock recon and delete them
		list_stock_recon = frappe.db.sql(""" SELECT name FROM `tabStock Reconciliation` WHERE tax_or_non_tax = "Non Tax" """,as_dict=1)
		list_sr = []
		for row in list_stock_recon:
			if row.name not in list_sr:
				list_sr.append(row.name)
		if list_sr:
			gabungan_sr = str(list_sr).replace("[","(").replace("]",")")
			frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no IN {} and voucher_type = "Stock Reconciliation" """.format(gabungan_sr))
			frappe.db.sql(""" DELETE FROM `tabStock Ledger Entry` WHERE voucher_no IN {} and voucher_type = "Stock Reconciliation" """.format(gabungan_sr))
			frappe.db.sql(""" DELETE FROM `tabStock Reconciliation Item` WHERE parent IN {} """.format(gabungan_sr))
			frappe.db.sql(""" DELETE FROM `tabStock Reconciliation` WHERE name IN {} """.format(gabungan_sr))

		# get all stock entry and delete them
		list_stock_entry = frappe.db.sql(""" SELECT name FROM `tabStock Entry` WHERE tax_or_non_tax = "Non Tax" """,as_dict=1)
		list_se = []
		for row in list_stock_entry:
			if row.name not in list_se:
				list_se.append(row.name)
		if list_se:
			gabungan_se = str(list_se).replace("[","(").replace("]",")")
			frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no IN {} and voucher_type = "Stock Entry" """.format(gabungan_se))
			frappe.db.sql(""" DELETE FROM `tabStock Ledger Entry` WHERE voucher_no IN {} and voucher_type = "Stock Entry" """.format(gabungan_se))
			frappe.db.sql(""" DELETE FROM `tabStock Entry Item` WHERE parent IN {} """.format(gabungan_se))
			frappe.db.sql(""" DELETE FROM `tabStock Entry` WHERE name IN {} """.format(gabungan_se))

		# get all payment entry and delete them
		list_payment_entry = frappe.db.sql(""" SELECT name FROM `tabPayment Entry` WHERE tax_or_non_tax = "Non Tax" """,as_dict=1)
		list_pe = []
		for row in list_payment_entry:
			if row.name not in list_pe:
				list_pe.append(row.name)
		if list_pe:
			gabungan_pe = str(list_pe).replace("[","(").replace("]",")")
			frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no IN {} and voucher_type = "Payment Entry" """.format(gabungan_pe))
			frappe.db.sql(""" DELETE FROM `tabPayment Entry Item` WHERE parent IN {} """.format(gabungan_pe))
			frappe.db.sql(""" DELETE FROM `tabPayment Entry` WHERE name IN {} """.format(gabungan_pe))

		# get all sales invoice and delete them
		list_sales_invoice = frappe.db.sql(""" SELECT name FROM `tabSales Invoice` WHERE tax_or_non_tax = "Non Tax" """,as_dict=1)
		list_si = []
		for row in list_sales_invoice:
			if row.name not in list_si:
				list_si.append(row.name)
		if list_si:
			gabungan_si = str(list_si).replace("[","(").replace("]",")")
			frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no IN {} and voucher_type = "Sales Invoice" """.format(gabungan_si))
			frappe.db.sql(""" DELETE FROM `tabStock Ledger Entry` WHERE voucher_no IN {} and voucher_type = "Sales Invoice" """.format(gabungan_si))
			frappe.db.sql(""" DELETE FROM `tabSales Invoice Item` WHERE parent IN {} """.format(gabungan_si))
			frappe.db.sql(""" DELETE FROM `tabSales Invoice` WHERE name IN {} """.format(gabungan_si))

		# get all purchase invoice and delete them
		list_purchase_invoice = frappe.db.sql(""" SELECT name FROM `tabPurchase Invoice` WHERE tax_or_non_tax = "Non Tax" """,as_dict=1)
		list_pi = []
		for row in list_purchase_invoice:
			if row.name not in list_pi:
				list_pi.append(row.name)
		if list_pi:
			gabungan_pi = str(list_pi).replace("[","(").replace("]",")")
			frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no IN {} and voucher_type = "Purchase Invoice" """.format(gabungan_pi))
			frappe.db.sql(""" DELETE FROM `tabStock Ledger Entry` WHERE voucher_no IN {} and voucher_type = "Purchase Invoice" """.format(gabungan_pi))
			frappe.db.sql(""" DELETE FROM `tabPurchase Invoice Item` WHERE parent IN {} """.format(gabungan_pi))
			frappe.db.sql(""" DELETE FROM `tabPurchase Invoice` WHERE name IN {} """.format(gabungan_pi))

		# get all delivery note and delete them
		list_delivery_note = frappe.db.sql(""" SELECT name FROM `tabDelivery Note` WHERE tax_or_non_tax = "Non Tax" """,as_dict=1)
		list_dn = []
		for row in list_delivery_note:
			if row.name not in list_dn:
				list_dn.append(row.name)
		if list_dn:
			gabungan_dn = str(list_dn).replace("[","(").replace("]",")")
			frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no IN {} and voucher_type = "Delivery Note" """.format(gabungan_dn))
			frappe.db.sql(""" DELETE FROM `tabStock Ledger Entry` WHERE voucher_no IN {} and voucher_type = "Delivery Note" """.format(gabungan_dn))
			frappe.db.sql(""" DELETE FROM `tabDelivery Note Item` WHERE parent IN {} """.format(gabungan_dn))
			frappe.db.sql(""" DELETE FROM `tabDelivery Note` WHERE name IN {} """.format(gabungan_dn))


		# get all purchase_receipt and delete them
		list_purchase_receipt = frappe.db.sql(""" SELECT name FROM `tabPurchase Receipt` WHERE tax_or_non_tax = "Non Tax" """,as_dict=1)
		list_pr = []
		for row in list_purchase_receipt:
			if row.name not in list_pr:
				list_pr.append(row.name)
		if list_pr:
			gabungan_pr = str(list_pr).replace("[","(").replace("]",")")
			frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no IN {} and voucher_type = "Purchase Receipt" """.format(gabungan_pr))
			frappe.db.sql(""" DELETE FROM `tabStock Ledger Entry` WHERE voucher_no IN {} and voucher_type = "Purchase Receipt" """.format(gabungan_pr))
			frappe.db.sql(""" DELETE FROM `tabPurchase Receipt Item` WHERE parent IN {} """.format(gabungan_pr))
			frappe.db.sql(""" DELETE FROM `tabPurchase Receipt` WHERE name IN {} """.format(gabungan_pr))

		# get all sales order and delete them
		list_sales_order = frappe.db.sql(""" SELECT name FROM `tabSales Order` WHERE tax_or_non_tax = "Non Tax" """,as_dict=1)
		list_so = []
		for row in list_sales_order:
			if row.name not in list_so:
				list_so.append(row.name)
		if list_so:
			gabungan_so = str(list_so).replace("[","(").replace("]",")")
			frappe.db.sql(""" DELETE FROM `tabSales Order Item` WHERE parent IN {} """.format(gabungan_so))
			frappe.db.sql(""" DELETE FROM `tabSales Order` WHERE name IN {} """.format(gabungan_so))


		# get all material request and delete them
		list_material_request = frappe.db.sql(""" SELECT name FROM `tabMaterial Request` WHERE tax_or_non_tax = "Non Tax" """,as_dict=1)
		list_mr = []
		for row in list_material_request:
			if row.name not in list_mr:
				list_mr.append(row.name)
		if list_mr:
			gabungan_mr = str(list_mr).replace("[","(").replace("]",")")
			frappe.db.sql(""" DELETE FROM `tabMaterial Request Item` WHERE parent IN {} """.format(gabungan_mr))
			frappe.db.sql(""" DELETE FROM `tabMaterial Request` WHERE name IN {} """.format(gabungan_mr))

		# get all purchase order and delete them
		list_purchase_order = frappe.db.sql(""" SELECT name FROM `tabPurchase Order` WHERE tax_or_non_tax = "Non Tax" """,as_dict=1)
		list_po = []
		for row in list_purchase_order:
			if row.name not in list_po:
				list_po.append(row.name)
		if list_po:
			gabungan_po = str(list_po).replace("[","(").replace("]",")")
			frappe.db.sql(""" DELETE FROM `tabPurchase Order Item` WHERE parent IN {} """.format(gabungan_po))
			frappe.db.sql(""" DELETE FROM `tabPurchase Order` WHERE name IN {} """.format(gabungan_po))


		# get all item and delete them
		list_item = frappe.db.sql(""" SELECT name FROM `tabItem` WHERE tax_or_non_tax = "Non Tax" """,as_dict=1)
		list_it = []
		for row in list_item:
			if row.name not in list_it:
				list_it.append(row.name)

		if list_it:
			gabungan_it = str(list_it).replace("[","(").replace("]",")")
			frappe.db.sql(""" DELETE FROM `tabItem` WHERE name IN {} """.format(gabungan_it))


		# get all cash_request and delete them
		list_cash_req = frappe.db.sql(""" SELECT name FROM `tabCash Request` WHERE tax_or_non_tax = "Non Tax" """,as_dict=1)
		list_cr = []
		for row in list_cash_req:
			if row.name not in list_cr:
				list_cr.append(row.name)

		if list_cr:
			gabungan_cr = str(list_cr).replace("[","(").replace("]",")")
			frappe.db.sql(""" DELETE FROM `tabCash Request` WHERE name IN {} """.format(gabungan_cr))
			frappe.db.sql(""" DELETE FROM `tabCash Request Table` WHERE parent IN {} """.format(gabungan_cr))
			frappe.db.sql(""" DELETE FROM `tabCash Request Taxes and Charges` WHERE parent IN {} """.format(gabungan_cr))

		# get all employee_expense and delete them
		list_emp_adv = frappe.db.sql(""" SELECT name FROM `tabEmployee Advance` WHERE tax_or_non_tax = "Non Tax" """,as_dict=1)
		list_ea = []
		for row in list_emp_adv:
			if row.name not in list_ea:
				list_ea.append(row.name)

		if list_ea:
			gabungan_ea = str(list_ea).replace("[","(").replace("]",")")
			frappe.db.sql(""" DELETE FROM `tabEmployee Advance` WHERE name IN {} """.format(gabungan_ea))

		# get all employee_expense and delete them
		list_exp_cla = frappe.db.sql(""" SELECT name FROM `tabExpense Claim` WHERE tax_or_non_tax = "Non Tax" """,as_dict=1)
		list_ec = []
		for row in list_exp_cla:
			if row.name not in list_ec:
				list_ec.append(row.name)

		if list_ec:
			gabungan_ec = str(list_ec).replace("[","(").replace("]",")")
			frappe.db.sql(""" DELETE FROM `tabExpense Claim` WHERE name IN {} """.format(gabungan_ec))

			
		# buat semua journal entry tax 
		list_je = frappe.db.sql(""" SELECT name FROM `tabJournal Entry Tax` WHERE docstatus = 1 """)
		for row in list_je:
			je_tax = frappe.get_doc("Journal Entry Tax", row[0])
			je_tax_fields = json.loads(frappe.as_json(je_tax))
			je_tax_fields["name"] = ""
			je_tax_fields["doctype"] = "Journal Entry"
			for row_je in je_tax_fields["accounts"]:
				row_je["doctype"] = "Journal Entry Account"
			je = frappe.get_doc(je_tax_fields)
			je.save()
			je.submit()

	else:
		frappe.throw("Forbidden Method to use in non tax sites.")

@frappe.whitelist()
def debug_make_je():
	list_je = frappe.db.sql(""" SELECT name FROM `tabJournal Entry Tax` WHERE docstatus = 1 """)
	for row in list_je:
		je_tax = frappe.get_doc("Journal Entry Tax", row[0])
		je_tax_fields = json.loads(frappe.as_json(je_tax))
		je_tax_fields["name"] = ""
		je_tax_fields["doctype"] = "Journal Entry"
		for row_je in je_tax_fields["accounts"]:
			row_je["doctype"] = "Journal Entry Account"
		je = frappe.get_doc(je_tax_fields)
		je.save()
		je.submit()