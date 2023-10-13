
import frappe
from frappe import _
from frappe.utils import cstr, flt, get_link_to_form


@frappe.whitelist()
def masukin_cabang(self,method):
	if self.docstatus == 1:
		for row in self.schedules:
			if not row.list_company_gias:
				if self.server_kepemilikan:
					row.list_company_gias = frappe.get_doc("Company", self.company).nama_cabang
					row.db_update()
				else:
					row.list_company_gias = self.cabang
					row.db_update()

@frappe.whitelist()
def isi_kosong():
	list_asset = frappe.db.sql(""" SELECT parent FROM `tabDepreciation Schedule` WHERE list_company_gias = "" or list_company_gias IS NULL """)
	for row in list_asset:
		doc = frappe.get_doc("Asset", row[0])
		masukin_cabang(doc,"on_submit")
		print(1)

@frappe.whitelist()
def masukin_prec(self,method):
	if self.purchase_receipt:
		prec_doc = frappe.get_doc("Purchase Receipt", self.purchase_receipt)
		for row_item in prec_doc.items:
			list_asset = frappe.db.sql(""" SELECT
				name
				FROM `tabAsset` 
				WHERE purchase_receipt = "{}" and item_code = "{}" 
				and docstatus = 1
			""".format(prec_doc.name, row_item.item_code))
			
			message = ""
			for row_asset in list_asset:
				message = message + row_asset[0] + "\n"

			row_item.asset_list = message
			row_item.db_update()

@frappe.whitelist()
def check_prec(self,method):
	if self.purchase_receipt:
		prec_doc = frappe.get_doc("Purchase Receipt", self.purchase_receipt)
		qty_prec = 0
		for row in prec_doc.items:
			if row.item_code == self.item_code:
				qty_prec += row.qty

		check_pr = frappe.db.sql(""" SELECT count(name), GROUP_CONCAT(name) FROM `tabAsset` 
			WHERE purchase_receipt = "{}" and docstatus = 1 
			and name != "{}" and item_code = "{}" 
			GROUP BY purchase_receipt """.format(self.purchase_receipt,self.name, self.item_code))
		if len(check_pr) > 0:
			if check_pr[0][0] >= qty_prec:
				frappe.throw(""" Purchase Receipt {} has been used in Asset {} for item {}. Please check again. """.format(self.purchase_receipt, check_pr[0][1], self.item_code))

	if self.purchase_invoice:
		prec_doc = frappe.get_doc("Purchase Invoice", self.purchase_invoice)
		qty_prec = 0
		for row in prec_doc.items:
			if row.item_code == self.item_code:
				qty_prec += row.qty

		check_pr = frappe.db.sql(""" SELECT count(name), GROUP_CONCAT(name) FROM `tabAsset` 
			WHERE purchase_invoice = "{}" and docstatus = 1 
			and name != "{}" and item_code = "{}" 
			GROUP BY purchase_invoice """.format(self.purchase_invoice,self.name, self.item_code))
		if len(check_pr) > 0:
			if check_pr[0][0] >= qty_prec:
				frappe.throw(""" Purchase Invoice {} has been used in Asset {} for item {}. Please check again. """.format(self.purchase_invoice, check_pr[0][1], self.item_code))
