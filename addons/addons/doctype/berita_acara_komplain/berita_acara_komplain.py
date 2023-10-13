# Copyright (c) 2021, das and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class BeritaAcaraKomplain(Document):
	def before_submit(self):
		if not self.attachment:
			frappe.throw("Attachment is Mandatory for submitting.")

	@frappe.whitelist()
	def set_item_from_rq(self):
		query_item = frappe.db.sql(""" 
			SELECT item_code,item_name,qty,stock_uom FROM `tabMaterial Request Item` 
			WHERE parent = "{}" """.format(self.no_rq),as_dict=1)

		for row in query_item:
			self.append("item",{

                "item_code" : row.item_code,
                "item_name" : row.item_name,
                "qty" : row.qty,
                "uom" : row.uom
			})

@frappe.whitelist()
def get_dn(dn):
	return frappe.db.sql(""" 
		SELECT item_code, item_name, qty, uom
		FROM `tabDelivery Note Item` WHERE parent = "{}" """.format(dn),as_dict=1)

@frappe.whitelist()
def get_rq(rq):
	# doc = frappe.get_doc("Material Request",rq)
	# if doc.type_request == "Group":
	# 	no_po = ""
	# 	query_po = frappe.db.sql(""" 
	# 		SELECT parent FROM `tabPurchase Order Item` 
	# 		WHERE material_request = "{}" """.format(rq),as_dict=1)
	# 	if len(query_po) > 0:
	# 		no_po = query_po[0].parent

	# 	return [doc.nama_supplier,no_po]
	# else:
	# perubahan
	query_detail = frappe.db.sql(""" 
		SELECT DISTINCT(pri.parent),me.eta,me.purchase_order,po.supplier FROM `tabMaterial Request Table` met join
		`tabMemo Ekspedisi` me on met.parent = me.name join
		`tabPurchase Order` po on me.purchase_order = po.name join
		`tabPurchase Receipt Item` pri on po.name = pri.purchase_order
		WHERE met.no_mrrq = "{}" """.format(rq),as_dict=1)
	query_item = frappe.db.sql(""" 
		SELECT item_code,item_name,qty,stock_uom FROM `tabMaterial Request Item` 
		WHERE parent = "{}" """.format(rq),as_dict=1)
	return query_detail,query_item

@frappe.whitelist()
def get_ste(ste):
	
	query_item = frappe.db.sql(""" 
		SELECT item_code,item_name,qty,stock_uom FROM `tabStock Entry Detail` 
		WHERE parent = "{}" """.format(ste),as_dict=1)
	
	return query_item

@frappe.whitelist()
def get_prec(prec):
	
	query_item = frappe.db.sql(""" 
		SELECT item_code,item_name,qty,stock_uom FROM `tabPurchase Receipt Item` 
		WHERE parent = "{}" """.format(prec),as_dict=1)
	
	return query_item

@frappe.whitelist()
def make_stock_entry(no_stock_entry,no_bak):
	target_doc = frappe.new_doc("Stock Entry")
	target_doc.stock_entry_type = "Material Issue"
	target_doc.purpose = "Material Issue"

	sumber_doc = frappe.get_doc("Berita Acara Komplain", no_bak)

	sumber_query = frappe.db.sql("""
	SELECT DISTINCT
	bak.no_stock_entry, 
	s_ste.item_code,
	s_ste.item_name,
	s_ste.uom,
	s_ste.stock_uom,
	s_ste.qty,
	s_ste.s_warehouse, 
	s_ste.t_warehouse, 
	s_ste.material_request, 
	s_ste.conversion_factor ,
	s_ste.cost_center,
	s_ste.branch,
	s_ste.material_request_item
	FROM `tabBerita Acara Komplain` bak 
	JOIN `tabTabel Berita Acara Komplain` tbak ON tbak.parent = bak.name 
	JOIN `tabStock Entry` ste ON ste.name = bak.no_stock_entry
	JOIN `tabStock Entry Detail` s_ste ON s_ste.parent = ste.name
	WHERE bak.name = "{}"
	""".format(no_bak), as_dict=1)

	for row in sumber_query:
		baris_baru = {
						"s_warehouse": row.s_warehouse,
						"t_warehouse": row.t_warehouse,
						"item_code" : row.item_code,
						"qty": row.qty,
						"uom" : row.uom,
						"stock_uom" : row.stock_uom,
						"conversion_factor" : row.conversion_factor,
						"material_request" : row.material_request,
						"material_request_item": row.material_request_item,
						"cost_center" : row.cost_center,
						"branch": row.branch,
						"against_stock_entry": no_stock_entry
					}
					
		target_doc.append("items",baris_baru)

	return target_doc.as_dict()

@frappe.whitelist()
def make_stock_entry_with_pr(no_purchase_receipt,no_bak):
	target_doc = frappe.new_doc("Stock Entry")
	target_doc.stock_entry_type = "Material Issue"
	target_doc.purpose = "Material Issue"

	sumber_doc = frappe.get_doc("Berita Acara Komplain", no_bak)

	sumber_query = frappe.db.sql("""
	SELECT DISTINCT
	bak.no_purchase_receipt, 
	s_ste.item_code,
	s_ste.item_name,
	s_ste.uom,
	s_ste.stock_uom,
	s_ste.qty,
	s_ste.warehouse as s_warehouse, 
	"" as t_warehouse, 
	s_ste.material_request, 
	s_ste.conversion_factor,
	s_ste.cost_center,
	s_ste.branch,
	s_ste.material_request_item
	FROM `tabBerita Acara Komplain` bak 
	JOIN `tabTabel Berita Acara Komplain` tbak ON tbak.parent = bak.name 
	JOIN `tabPurchase Receipt` ste ON ste.name = bak.no_purchase_receipt
	JOIN `tabPurchase Receipt Item` s_ste ON s_ste.parent = ste.name
	WHERE bak.name = "{}"
	""".format(no_bak), as_dict=1)

	for row in sumber_query:
		baris_baru = {
						"s_warehouse": row.s_warehouse,
						"t_warehouse": row.t_warehouse,
						"item_code" : row.item_code,
						"qty": row.qty,
						"uom" : row.uom,
						"stock_uom" : row.stock_uom,
						"conversion_factor" : row.conversion_factor,
						"material_request" : row.material_request,
						"material_request_item": row.material_request_item,
						"cost_center" : row.cost_center,
						"branch": row.branch
					}
					
		target_doc.append("items",baris_baru)

	return target_doc.as_dict()
