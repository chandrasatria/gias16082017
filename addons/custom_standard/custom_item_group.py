
import frappe,erpnext
from frappe.model.document import Document
from frappe.utils import flt

@frappe.whitelist()
def apply_to_child_item(self,method):
	if self.is_group:
		if self.code and self.parent_code:
			if self.lft and self.rgt:
				frappe.db.sql(""" UPDATE `tabItem Group` SET code ="{}", parent_code="{}" WHERE lft > {} and rgt < {} """.format(self.code,self.parent_code,self.lft,self.rgt))
				frappe.db.commit()
		else:
			frappe.throw("Please insert Code or Parent Code into the Item Group " + self.name)
