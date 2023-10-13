# Copyright (c) 2021, das and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class FormPengisianPolisAsuransi(Document):
	pass

@frappe.whitelist()
def get_mpee(mpee):
	return frappe.db.sql(""" 
		SELECT isi_kontainer
		FROM `tabTabel Isi Kontainer Memo Permintaan Ekspedisi Eksternal` 
		WHERE parent = "{}" """.format(mpee),as_dict=1)