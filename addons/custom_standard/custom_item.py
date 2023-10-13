
import frappe,erpnext
from frappe.model.document import Document
from frappe.utils import flt

@frappe.whitelist()
def check_item_group(self,method):
	if self.item_group:
		item_group_doc = frappe.get_doc("Item Group",self.item_group)
		if item_group_doc.disabled == 1:
			frappe.throw("Item Group {} cannot be used. Please use another.".format(self.item_group))

@frappe.whitelist()
def check_uoms(self,method):
	list_uom = []
	hasil_baris = []

	for row_uom in self.uoms:
		if row_uom.uom not in list_uom:
			list_uom.append(row_uom.uom)
			hasil_baris.append(row_uom)

	self.uoms = hasil_baris

@frappe.whitelist()
def validate_check(self,method):
	if not self.is_new():
		if "SPV ACC Cabang" not in frappe.get_roles():
			frappe.throw("Only SPV ACC Cabang role can update Item.")
