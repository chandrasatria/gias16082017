# Copyright (c) 2022, das and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class AlokasiMRbyPS(Document):
	pass

@frappe.whitelist()
def get_item_from_material_request(mreq):
	return frappe.db.sql("""
		SELECT 
		tmri.parent,
		tmri.`item_code`,
		tmri.`item_name`,
		tmri.`description`,
		tmri.`qty`,
		tmri.`uom`,
		tmri.`stock_uom`,
		tmri.`stock_qty`,
		tmri.`conversion_factor`,
		tmri.`warehouse`,
		tmri.`rate`,
		tmr.cabang,
		tmri.name as material_request_item

		FROM `tabMaterial Request Item` tmri
		JOIN `tabMaterial Request` tmr ON tmr.name = tmri.parent
		WHERE 
		tmri.parent = "{}"
	""".format(mreq), as_dict=1)

