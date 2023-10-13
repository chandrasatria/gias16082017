# Copyright (c) 2023, das and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class AlokasiProductSpecialist(Document):
	def before_submit(self):
		for row in self.material_request_not_ready:
			if row.nama_mr_item:
				total = frappe.db.sql(""" SELECT SUM(IFNULL(qty_alokasi,0)) 
					FROM `tabAlokasi Product Specialist Table` 
					WHERE nama_mr_item = "{}" and docstatus = 1 """.format(row.nama_mr_item))
				if total:
					if total[0][0]:
						row.qty_outstanding = row.qty - frappe.utils.flt(total[0][0])

@frappe.whitelist()
def get_bin(item_code,source_warehouse):
	return frappe.db.sql("""
		SELECT tb.`actual_qty`
		FROM `tabBin` tb
		WHERE 
		tb.`item_code` = "{}"
		AND tb.`warehouse` = "{}"
	""".format(item_code,source_warehouse), as_dict=1)

@frappe.whitelist()
def get_mr(from_date,to_date,item_group,ps,branch):
	
	array_branch = str(branch).replace("[","(").replace("]",")")
	query_branch = ""
	if len(array_branch) > 0 and array_branch != "()":
		query_branch = """ AND mr.cabang IN {} """.format(array_branch)

	return frappe.db.sql("""
		SELECT 
		mr.transaction_date as mr_date, 
		mr.name as material_request,  
		mri.item_code, 
		mri.item_name, 
		mr.cabang, 
		mri.qty, 
		mri.qty_issued,
		mri.name as nama_mr_item,
		SUM(IFNULL(apst.qty_alokasi,0)) as qty_alokasi_total

		FROM `tabMaterial Request` mr 
		JOIN `tabMaterial Request Item` mri 
		ON mri.parent = mr.name
		JOIN `tabItem` tit 
		ON tit.name = mri.item_code
		LEFT JOIN `tabAlokasi Product Specialist Table` apst on apst.nama_mr_item = mri.name and apst.docstatus = 1

		WHERE mr.ps_approver = "{}"
		AND mr.transaction_date >= "{}"
		AND mr.transaction_date <= "{}"
		AND tit.item_group = "{}"
		{}
		AND mr.docstatus = 1
		AND mr.barang_ready = "Not Ready"
		and mr.material_request_type = "Material Transfer"
		GROUP BY mri.name
		ORDER BY mr.name,mri.item_code
	""".format(ps, from_date, to_date, item_group, query_branch), as_dict=1, debug=1)

