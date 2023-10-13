# Copyright (c) 2023, das and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.stock.utils import get_stock_balance
from erpnext.stock.doctype.batch.batch import get_batch_qty
from frappe.utils import flt

class StockOpname(Document):
	def before_submit(self):
		# # buat m_receipt
		# ste = frappe.new_doc("Stock Entry")
		# ste.posting_date = self.posting_date
		# ste.posting_time = self.posting_time
		# ste.set_posting_time = self.set_posting_time
		# ste.stock_entry_type = "Material Receipt"
		# ste.purpose = "Material Receipt"
		# ste.tax_or_non_tax = self.tax_or_non_tax
		# ste.stock_opname = 1
		# ste.stock_opname_number = self.name
		# ste.transfer_ke_cabang_pusat = 0

		# ste2 = frappe.new_doc("Stock Entry")
		# ste2.posting_date = self.posting_date
		# ste2.posting_time = self.posting_time
		# ste2.set_posting_time = self.set_posting_time
		# ste2.stock_entry_type = "Material Issue"
		# ste2.purpose = "Material Issue"
		# ste2.tax_or_non_tax = self.tax_or_non_tax
		# ste2.stock_opname = 1
		# ste2.stock_opname_number = self.name
		# ste2.transfer_ke_cabang_pusat = 0

		# check_plus = 0
		# check_minus = 0
		# for row in self.items:
		# 	if row.qty > 0:
		# 		check_plus = 1
		# 		ste.append("items",
		# 			{
		# 				"item_code" : row.item_code,
		# 				"qty" : row.qty,
		# 				"t_warehouse" : row.warehouse,
		# 				"basic_rate" : row.valuation_rate,
		# 				"transfer_qty": row.qty,
		# 				"action": row.action,
		# 				"user_remark": row.description
		# 			}
		# 		)

		# 	elif row.qty < 0:
		# 		check_minus = 1
		# 		ste2.append("items",
		# 			{
		# 				"item_code": row.item_code,
		# 				"qty": row.qty * -1,
		# 				"s_warehouse" : row.warehouse,
		# 				"basic_rate" : row.valuation_rate,
		# 				"transfer_qty": row.qty,
		# 				"action": row.action,
		# 				"user_remark": row.description
		# 			}
		# 		)


		# if check_plus == 1:
		# 	ste.save()
		# 	frappe.msgprint("1")

		# if check_minus == 1:
		# 	ste2.save()
		# 	frappe.msgprint("2")

		# frappe.throw("FAIL")
		pass



@frappe.whitelist()
def buat_ste(self,method):
	# buat m_receipt
	ste = frappe.new_doc("Stock Entry")
	ste.posting_date = self.posting_date
	ste.posting_time = self.posting_time
	ste.set_posting_time = self.set_posting_time
	ste.stock_entry_type = "Material Receipt"
	ste.purpose = "Material Receipt"
	ste.tax_or_non_tax = self.tax_or_non_tax
	ste.stock_opname = 1
	ste.stock_opname_number = self.name
	ste.transfer_ke_cabang_pusat = 0

	ste2 = frappe.new_doc("Stock Entry")
	ste2.posting_date = self.posting_date
	ste2.posting_time = self.posting_time
	ste2.set_posting_time = self.set_posting_time
	ste2.stock_entry_type = "Material Issue"
	ste2.purpose = "Material Issue"
	ste2.tax_or_non_tax = self.tax_or_non_tax
	ste2.stock_opname = 1
	ste2.stock_opname_number = self.name
	ste2.transfer_ke_cabang_pusat = 0

	check_plus = 0
	check_minus = 0
	for row in self.items:
		if row.qty > 0:
			check_plus = 1
			zero_rate = 0
			if row.valuation_rate == 0:
				zero_rate = 1

			ste.append("items",
				{
					"item_code" : row.item_code,
					"qty" : row.qty,
					"t_warehouse" : row.warehouse,
					"basic_rate" : row.valuation_rate,
					"transfer_qty": row.qty,
					"action": row.action,
					"user_remark": row.description,
					"allow_zero_valuation_rate": zero_rate
				}
			)

		elif row.qty < 0:
			check_minus = 1
			zero_rate = 0
			if row.valuation_rate == 0:
				zero_rate = 1

			ste2.append("items",
				{
					"item_code": row.item_code,
					"qty": row.qty * -1,
					"s_warehouse" : row.warehouse,
					"basic_rate" : row.valuation_rate,
					"transfer_qty": row.qty,
					"action": row.action,
					"user_remark": row.description,
					"allow_zero_valuation_rate": zero_rate

				}
			)


	if check_plus == 1:
		ste.save()

	if check_minus == 1:
		ste2.save()

@frappe.whitelist()
def get_stock_balance_for(item_code, warehouse,
	posting_date, posting_time, batch_no=None, with_valuation_rate= True):
	frappe.has_permission("Stock Reconciliation", "write", throw = True)

	item_dict = frappe.db.get_value("Item", item_code,
		["has_serial_no", "has_batch_no"], as_dict=1)

	if not item_dict:
		# In cases of data upload to Items table
		msg = _("Item {} does not exist.").format(item_code)
		frappe.throw(msg, title=_("Missing"))

	serial_nos = ""
	with_serial_no = True if item_dict.get("has_serial_no") else False
	data = get_stock_balance(item_code, warehouse, posting_date, posting_time,
		with_valuation_rate=with_valuation_rate, with_serial_no=with_serial_no)

	if with_serial_no:
		qty, rate, serial_nos = data
	else:
		qty, rate = data

	if item_dict.get("has_batch_no"):
		qty = get_batch_qty(batch_no, warehouse, posting_date=posting_date, posting_time=posting_time) or 0

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
		AND ste.workflow_state != 'Rejected'
	""".format(item_code,warehouse),as_dict=1)

	ste_qty = 0
	if len(ste_check) > 0:
		for row_ste in ste_check:
			ste_qty = flt(row_ste.qty_booking)

	dne_qty = 0
	if len(dne_check) > 0:
		for row_dne in dne_check:
			dne_qty = flt(row_dne.qty_booking)


	return {
		'qty': qty,
		'rate': rate,
		'serial_nos': serial_nos,
		'ste_draft_qty': ste_qty,
		'dn_draft_qty': dne_qty
	}
# Copyright (c) 2023, das and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

class StockOpname(Document):
	pass
