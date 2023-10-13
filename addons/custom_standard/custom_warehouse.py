import frappe, erpnext

@frappe.whitelist()
def check_dua_cabang(doc,method):

	cek_field = frappe.db.sql(""" SELECT name FROM `tabCustom Field` WHERE name = "Warehouse-cabang" """)
	if len(cek_field) > 0:
		if doc.cabang and doc.warehouse_type == "Transit":
			cek = frappe.db.sql(""" SELECT name FROM `tabWarehouse` WHERE cabang = "{}" and name != "{}" and warehouse_type = "Transit" """.format(doc.cabang, doc.name))
			if len(cek) > 0:
				frappe.throw("One GIAS Branch Company can only have 1 Transit Warehouse.")

@frappe.whitelist()
def check_transit_pusat(doc,method):
	if doc.warehouse_type == "Transit Pusat":
		cek = frappe.db.sql(""" SELECT name FROM `tabWarehouse` WHERE warehouse_type = "Transit Pusat" and name != "{}" """.format(doc.name))
		if len(cek) > 0:
			frappe.throw("One GIAS Branch Company can only have 1 Transit Pusat Warehouse.")
