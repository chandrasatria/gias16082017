from erpnext.setup.utils import get_exchange_rate
import frappe,erpnext

from frappe.model.document import Document
from erpnext.accounts.doctype.journal_entry.journal_entry import JournalEntry
from frappe.utils import flt



@frappe.whitelist()
def check_tax_non_tax_by_document(self,method):
	if self.doctype == "Purchase Order":
		doctype1 = "Material Request"
		doctype2 = "Sales Order"
		docfield1 = "material_request"
		docfield2 = "sales_order"

	elif self.doctype == "Purchase Receipt":
		doctype1 = "Material Request"
		doctype2 = "Purchase Order"
		docfield1 = "material_request"
		docfield2 = "purchase_order"

	elif self.doctype == "Purchase Invoice":
		doctype1 = "Purchase Receipt"
		doctype2 = "Purchase Order"
		docfield1 = "purchase_receipt"
		docfield2 = "purchase_order"

	elif self.doctype == "Delivery Note":
		doctype1 = "Sales Invoice"
		doctype2 = "Sales Order"
		docfield1 = "against_sales_invoice"
		docfield2 = "against_sales_order"

	elif self.doctype == "Sales Invoice":
		doctype1 = "Delivery Note"
		doctype2 = "Sales Order"
		docfield1 = "delivery_note"
		docfield2 = "sales_order"

	for row in self.items:
		docname1 = row.get(docfield1)
		if docname1:
			document1 = frappe.get_doc(doctype1, docname1)
			if document1.tax_or_non_tax != self.tax_or_non_tax:
				frappe.throw("{} {} tax status is different with this {}".format(doctype1, docname1, self.doctype))

		docname2 = row.get(docfield2)
		if docname2:
			document2 = frappe.get_doc(doctype2, docname2)
			if document2.tax_or_non_tax != self.tax_or_non_tax:
				frappe.throw("{} {} tax status is different with this {}".format(doctype2, docname2, self.doctype))




@frappe.whitelist()
def check_tax_non_tax(self,method):
	for row in self.items:
		item_doc = frappe.get_doc("Item", row.item_code)
		if item_doc.tax_or_non_tax != self.tax_or_non_tax:
			frappe.throw("Item {} cannot be in {} Transactions.".format(item_doc.tax_or_non_tax, self.tax_or_non_tax))


@frappe.whitelist()
def calculate_total_prorate(self,method):
	for row in self.items:
		if row.prorate_discount:
			row.total_prorate = row.qty * row.prorate_discount

@frappe.whitelist()
def check_draft_cash_request(self,method):
	field_name = "document"
	doctype = "Cash Request Table"
	pas_doctype = "Purchase Invoice"
	parent = "Cash Request"

	for row in self.list_invoice:
		if row.get(field_name):
			sisa = frappe.db.sql(""" 
				SELECT IFNULL(doc_sumber.`rounded_total`-SUM(doc_patokan.amount),0), doc_patokan.document,GROUP_CONCAT(doc_patokan.parent), SUM(doc_patokan.amount)
				FROM `tab{}` doc_patokan
				JOIN `tab{}` doc_sumber ON doc_sumber.name = doc_patokan.{}
				JOIN `tab{}` doc_parent ON doc_parent.name = doc_patokan.parent
				
				WHERE doc_patokan.{} = "{}"
				AND doc_patokan.`docstatus` < 2 and doc_parent.workflow_state != "Rejected" """.format(doctype,pas_doctype,field_name,parent,field_name,row.get(field_name)))

			if len(sisa) > 0:
				terpakai = frappe.utils.flt(sisa[0][0])
				document = sisa[0][2]
				doc_lain = sisa[0][3]
				if row.amount > terpakai and document:
					frappe.throw(""" Purchase Invoice {} in row {} has been used in next document {} {} with amount {}. Please check again. """.format(row.document, row.idx, self.doctype, document, doc_lain))


@frappe.whitelist()
def check_draft_payment_entry(self,method):
	field_name = "reference_name"
	doctype = "Payment Entry Reference"
	parent = "Payment Entry"

	for row in self.references:
		if row.get(field_name):
			if row.get("reference_doctype") == "Sales Invoice" or row.get("reference_doctype") == "Purchase Invoice":
				
				pas_doctype = row.get("reference_doctype")
				sisa = frappe.db.sql(""" 
					SELECT 
					IFNULL(IF(doc_sumber.`rounded_total`=0,doc_sumber.grand_total,doc_sumber.rounded_total)- IFNULL(SUM(IFNULL(doc_patokan.allocated_amount,0)),0),0), doc_patokan.reference_name ,
					GROUP_CONCAT(doc_patokan.parent), SUM(doc_patokan.allocated_amount)
					FROM `tab{}` doc_sumber
					LEFT JOIN `tab{}` doc_patokan ON doc_sumber.name = doc_patokan.{}
					LEFT JOIN `tab{}` doc_parent ON doc_patokan.parent = doc_parent.name
					WHERE doc_patokan.{} = "{}"
					AND doc_patokan.`docstatus` < 2  and (doc_parent.workflow_state != "Rejected" or doc_parent.workflow_state IS NULL )
					""".format(pas_doctype,doctype,field_name,parent,field_name,row.get(field_name)))

				if len(sisa) > 0:
					terpakai = frappe.utils.flt(sisa[0][0])
					document = sisa[0][2]
					doc_lain = sisa[0][3]
					if row.allocated_amount > terpakai and document:
						frappe.throw(""" Reference Doctype {} in row {} has been used in next document {} {} with allocated amount {}. Please check again. """.format(row.reference_name, row.idx, self.doctype, document, doc_lain))

@frappe.whitelist()
def check_draft_journal_entry(self,method):
	field_name = "reference_name"
	doctype = "Journal Entry Account"
	parent = "Journal Entry"

	for row in self.accounts:
		if row.get(field_name):
			if row.get("reference_type") == "Sales Invoice" or row.get("reference_type") == "Purchase Invoice":
				pas_doctype = row.get("reference_type")
				if pas_doctype == "Purchase Invoice":
					sisa = frappe.db.sql(""" 
						SELECT IFNULL(doc_sumber.`rounded_total`-SUM(doc_patokan.debit_in_account_currency-doc_patokan.credit_in_account_currency),0), doc_patokan.reference_name ,GROUP_CONCAT(doc_patokan.parent), SUM(doc_patokan.debit_in_account_currency-doc_patokan.credit_in_account_currency)
						FROM `tab{}` doc_patokan
						JOIN `tab{}` doc_sumber ON doc_sumber.name = doc_patokan.{}
						JOIN `tab{}` doc_parent ON doc_parent.name = doc_patokan.parent
						WHERE doc_patokan.{} = "{}"
						AND doc_patokan.`docstatus` < 2 and (doc_parent.workflow_state != "Rejected" or doc_parent.workflow_state IS NULL ) """.format(doctype,pas_doctype,field_name,parent,field_name,row.get(field_name)),debug=1)

					if len(sisa) > 0:
						terpakai = frappe.utils.flt(sisa[0][0])
						document = sisa[0][2]
						doc_lain = sisa[0][3]
						if frappe.utils.flt(row.debit_in_account_currency) > frappe.utils.flt(terpakai) and document:
							frappe.throw(""" Reference Doctype {} in row {} has been used in next document {} {} with allocated amount {}. Please check again. """.format(row.reference_name, row.idx, self.doctype, document, doc_lain))
				elif pas_doctype == "Sales Invoice":
					sisa = frappe.db.sql(""" 
						SELECT IFNULL(doc_sumber.`rounded_total`-SUM(doc_patokan.credit_in_account_currency-doc_patokan.debit_in_account_currency),0), doc_patokan.reference_name ,GROUP_CONCAT(doc_patokan.parent), SUM(doc_patokan.credit_in_account_currency-doc_patokan.debit_in_account_currency)
						FROM `tab{}` doc_patokan
						JOIN `tab{}` doc_sumber ON doc_sumber.name = doc_patokan.{}
						JOIN `tab{}` doc_parent ON doc_parent.name = doc_patokan.parent
						WHERE doc_patokan.{} = "{}"
						AND doc_patokan.`docstatus` < 2 and (doc_parent.workflow_state != "Rejected" or doc_parent.workflow_state IS NULL ) """.format(doctype,pas_doctype,field_name,parent,field_name,row.get(field_name)))

					if len(sisa) > 0:
						terpakai = frappe.utils.flt(sisa[0][0])
						document = sisa[0][2]
						doc_lain = sisa[0][3]
						if row.credit_in_account_currency > terpakai and document:
							frappe.throw(""" Reference Doctype {} in row {} has been used in next document {} {} with allocated amount {}. Please check again. """.format(row.reference_name, row.idx, self.doctype, document, doc_lain))






@frappe.whitelist()
def check_draft_mr(self,method):
	retur = 0
	ws_field = "workflow_state"
	if self.doctype == "Purchase Order":
		field_name = "material_request_item"
		doctype = self.doctype
		pas_doctype = "Material Request"

	elif self.doctype == "Purchase Receipt":
		if self.is_return == 1:
			field_name = "purchase_receipt_item"
			doctype = self.doctype
			pas_doctype = "Purchase Receipt"
			retur = 1
		else:
			field_name = "purchase_order_item"
			doctype = self.doctype
			pas_doctype = "Purchase Order"

	elif self.doctype == "Purchase Invoice":
		field_name = "pr_detail"
		doctype = self.doctype
		pas_doctype = "Purchase Receipt"

	elif self.doctype == "Delivery Note":
		if self.is_return == 1:
			field_name = "dn_detail"
			doctype = self.doctype
			pas_doctype = "Delivery Note"
			retur = 1
		else:
			field_name = "so_detail"
			doctype = self.doctype
			pas_doctype = "Sales Order"

	elif self.doctype == "Sales Invoice":
		field_name = "dn_detail"
		doctype = self.doctype
		pas_doctype = "Delivery Note"
		ws_field = "workflow_states"

	for row in self.items:
		if row.get(field_name):
			if retur == 0:
				sisa = frappe.db.sql(""" 
					SELECT IFNULL(doc_sumber.`qty`-IFNULL(SUM(IFNULL(doc_patokan.qty,0)),0),0), doc_patokan.item_code,GROUP_CONCAT(doc_patokan.parent), IFNULL(SUM(IFNULL(doc_patokan.qty,0)),0)
					FROM `tab{} Item` doc_patokan
					JOIN `tab{} Item` doc_sumber ON doc_sumber.name = doc_patokan.{}
					JOIN `tab{}` doc_parent ON doc_parent.name = doc_patokan.parent
					WHERE doc_patokan.{} = "{}"
					AND doc_patokan.`docstatus` < 2 and (doc_parent.{} != "Rejected" or doc_parent.{} IS NULL) """.format(doctype,pas_doctype,field_name,doctype,field_name,row.get(field_name),ws_field,ws_field))

				if len(sisa) > 0:
					terpakai = frappe.utils.flt(sisa[0][0])
					document = sisa[0][2]
					doc_lain = sisa[0][3]
					if row.qty > terpakai and document:
						frappe.throw(""" Item {} in row {} has been used in next document {} {} with qty {}. Please check again. """.format(row.item_code,row.idx, self.doctype, document, doc_lain))
			elif retur == 1:
				sisa = frappe.db.sql(""" 
					SELECT IFNULL(doc_sumber.`qty`+ SUM(doc_patokan.qty),0), doc_patokan.item_code,GROUP_CONCAT(doc_patokan.parent), SUM(doc_patokan.qty)
					FROM `tab{} Item` doc_patokan
					JOIN `tab{} Item` doc_sumber ON doc_sumber.name = doc_patokan.{}
					JOIN `tab{}` doc_parent ON doc_parent.name = doc_patokan.parent
					WHERE doc_patokan.{} = "{}"
					AND doc_patokan.`docstatus` < 2 and (doc_parent.{} != "Rejected" or doc_parent.{} IS NULL) """.format(doctype,pas_doctype,field_name,doctype,field_name,row.get(field_name),ws_field,ws_field))

				if len(sisa) > 0:
					terpakai = frappe.utils.flt(sisa[0][0])
					document = sisa[0][2]
					doc_lain = sisa[0][3]
					if row.qty*-1 > terpakai and document:
						frappe.throw(""" Item {} in row {} has been used in next document {} {} with qty {}. Please check again. """.format(row.item_code,row.idx, self.doctype, document, doc_lain))



@frappe.whitelist()
def remove_generated(self,method):
	self.generated_name = ""

@frappe.whitelist()
def access(self,method):
	if("branch" not in frappe.session.user and "Administrator" not in frappe.session.user):
		frappe.throw("This User is not allowed to change Event Producer, please check again.")
	

@frappe.whitelist()
def check_tanggal_pe(self,method):
	for row in self.references:
		doc = frappe.get_doc(row.reference_doctype, row.reference_name)
		if row.reference_doctype == "Sales Invoice" or row.reference_doctype == "Purchase Invoice":
			if frappe.utils.getdate(doc.posting_date) > frappe.utils.getdate(self.posting_date):
				frappe.throw("Reference Doc {} has posting date {} bigger than this document {}. Please check again.".format(row.reference_name, doc.posting_date, self.posting_date))

@frappe.whitelist()
def check_tanggal_po(self,method):
	for row in self.items:
		if row.purchase_order:
			doc = frappe.get_doc("Purchase Order",row.purchase_order)
			if frappe.utils.getdate(doc.transaction_date) > frappe.utils.getdate(self.posting_date):
				frappe.throw("Reference Doc {} has posting date {} bigger than this document {}. Please check again.".format(row.purchase_order, doc.transaction_date, self.posting_date))

@frappe.whitelist()
def check_tanggal_mr(self,method):
	for row in self.items:
		if row.material_request:
			doc = frappe.get_doc("Material Request",row.material_request)
			if frappe.utils.getdate(doc.transaction_date) > frappe.utils.getdate(self.transaction_date):
				frappe.throw("Reference Doc {} has posting date {} bigger than this document {}. Please check again.".format(row.material_request, doc.transaction_date, self.transaction_date))

@frappe.whitelist()
def patch_no_tax():
	list_si = frappe.db.sql(""" SELECT name FROM `tabSales Invoice` 
		WHERE discount_2 > 0 and discount_2_no_tax = 0 group by parent """)
	for row in list_si:
		print(row[0])
		patch_set_discount_no_tax(row[0],"Sales Invoice")


@frappe.whitelist()
def patch_set_discount_no_tax(no, dt):
	self = frappe.get_doc(dt,no)
	variable = 100
	for row in self.taxes:
		if row.rate and variable == 100 and row.included_in_print_rate == 1:
			variable += row.rate

	# for row in self.items:
	# 	if row.discount_amount:
	# 		row.discount_1_no_tax = row.discount_amount / (variable / 100)
	# 		row.db_update()

	# 	if row.prorate_discount:
	# 		row.discount_2_no_tax = row.prorate_discount / (variable / 100)
	# 		row.db_update()


	if self.discount_2:
		self.discount_2_no_tax = self.discount_2 / (variable/100)
		self.db_update()

@frappe.whitelist()
def set_discount_no_tax(self,method):
	variable = 100
	for row in self.taxes:
		if row.rate and variable == 100 and row.included_in_print_rate == 1:
			variable += row.rate

	for row in self.items:
		if row.discount_amount:
			row.discount_1_no_tax = row.discount_amount / (variable / 100)

		if row.prorate_discount:
			row.discount_2_no_tax = row.prorate_discount / (variable / 100)

	if self.discount_2:
		self.discount_2_no_tax = self.discount_2 / (variable/100)

@frappe.whitelist()
def onload_dimension(company):
	hasil = frappe.db.sql(""" 
		SELECT default_dimension 
		FROM `tabAccounting Dimension Detail` 
		WHERE company = "{}"
		and parent = "Branch"
		 """.format(company),as_dict=1)
	
	return hasil

@frappe.whitelist()
def check_item_terbooking(self,method):
	if self.doctype == "Delivery Note":

		for row in self.items:
			item_doc = frappe.get_doc("Item", row.item_code)
			if item_doc.is_stock_item == 0:
				return

			warehouse = row.warehouse
			item_code = row.item_code

			from erpnext.stock.stock_balance import repost_stock
			repost_stock(item_code=item_code,warehouse=warehouse,only_bin=True)
			frappe.db.commit()
					
			bin_check = frappe.db.sql(""" 
				SELECT IFNULL(actual_qty,0) AS qty_booking 
				FROM `tabBin` std
				WHERE std.item_code = "{}"
				and std.warehouse = "{}"
			""".format(item_code,warehouse),as_dict=1)

			ste_check = frappe.db.sql(""" 
				SELECT sum(IFNULL(qty,0)) AS qty_booking 
				FROM `tabStock Entry Detail` std
				JOIN `tabStock Entry` ste ON ste.name = std.parent  
				WHERE std.item_code = "{}"
				AND std.s_warehouse = "{}"
				AND ste.docstatus = 0
				AND ste.workflow_state != 'Rejected'
			""".format(item_code,warehouse),as_dict=1)

			dne_check = frappe.db.sql(""" 
				SELECT sum(IFNULL(qty,0)) AS qty_booking 
				FROM `tabDelivery Note Item` std
				JOIN `tabDelivery Note` ste ON ste.name = std.parent  
				WHERE std.item_code = "{}"
				AND std.warehouse = "{}"
				AND ste.docstatus = 0
				and ste.name != "{}"
				AND ste.workflow_state != 'Rejected'
			""".format(item_code,warehouse, self.name),as_dict=1)

			current_qty = 0
			bin_qty = 0
			current_txt_qty = ""
			if len(bin_check) > 0:
				for row_bin in bin_check:
					bin_qty = flt(row_bin.qty_booking)

			ste_qty = 0
			if len(ste_check) > 0:
				for row_ste in ste_check:
					ste_qty = flt(row_ste.qty_booking)

			dne_qty = 0
			if len(dne_check) > 0:
				for row_dne in dne_check:
					dne_qty = flt(row_dne.qty_booking)

			for row_check in self.items:
				if row_check.item_code == row.item_code and row_check.warehouse == row.warehouse:
					current_qty += row_check.stock_qty
			
			if self.is_return != 1:
				if flt(flt(current_qty) + flt(ste_qty) + flt(dne_qty),2) > flt(bin_qty,2):
					frappe.throw("Booking Qty for item {} - {} is occupying the bin Stock ({}). Bin = {}. STE Draft = {}. DN Draft = {}. Delivery Note cannot be created.".format(item_code, row.item_name, warehouse,bin_qty,ste_qty,dne_qty))

	elif self.doctype == "Stock Entry":
		if self.stock_entry_type != "Material Receipt":
			for row in self.items:
				item_doc = frappe.get_doc("Item", row.item_code)
				if item_doc.is_stock_item == 0:
					return
				
				if row.s_warehouse :
					sumber_warehouse = row.s_warehouse
					item_code = row.item_code

					# check update bin
					from erpnext.stock.stock_balance import repost_stock
					repost_stock(item_code=item_code,warehouse=sumber_warehouse,only_bin=True)
					frappe.db.commit()


					bin_check = frappe.db.sql(""" 
						SELECT IFNULL(actual_qty,0) AS qty_booking 
						FROM `tabBin` std
						WHERE std.item_code = "{}"
						and std.warehouse = "{}"
					""".format(item_code, sumber_warehouse),as_dict=1)

					ste_check = frappe.db.sql(""" 
						SELECT sum(IFNULL(qty,0)) AS qty_booking 
						FROM `tabStock Entry Detail` std
						JOIN `tabStock Entry` ste ON ste.name = std.parent  
						WHERE std.item_code = "{}"
						AND std.s_warehouse = "{}"
						AND ste.docstatus = 0
						and ste.name != "{}"
						AND ste.workflow_state != 'Rejected'
					""".format(item_code,sumber_warehouse, self.name),as_dict=1)

					dne_check = frappe.db.sql(""" 
						SELECT sum(IFNULL(qty,0)) AS qty_booking 
						FROM `tabDelivery Note Item` std
						JOIN `tabDelivery Note` ste ON ste.name = std.parent  
						WHERE std.item_code = "{}"
						AND std.warehouse = "{}"
						AND ste.docstatus = 0
						AND ste.workflow_state != 'Rejected'
					""".format(item_code,sumber_warehouse),as_dict=1)

					current_qty = 0
					bin_qty = 0
					if len(bin_check) > 0:
						for row_bin in bin_check:
							bin_qty = flt(row_bin.qty_booking)

					ste_qty = 0
					if len(ste_check) > 0:
						for row_ste in ste_check:
							ste_qty = flt(row_ste.qty_booking)

					dne_qty = 0
					if len(dne_check) > 0:
						for row_dne in dne_check:
							dne_qty = flt(row_dne.qty_booking)

					for row_check in self.items:
						if row_check.item_code == row.item_code and row_check.s_warehouse == sumber_warehouse:
							current_qty += flt(row_check.transfer_qty)

					# current_qty = row.qty
					if flt(flt(current_qty) + flt(ste_qty) + flt(dne_qty),2) > flt(bin_qty,2):
						frappe.throw("Booking Qty for item {} - {} is occupying the bin Stock ({}). Bin = {}. STE Draft = {}. DN Draft = {}. Stock Entry cannot be created.{}".format(item_code, row.item_name, sumber_warehouse,bin_qty,ste_qty,dne_qty,flt(flt(current_qty) + flt(ste_qty) + flt(dne_qty),2)))
