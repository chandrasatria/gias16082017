# Copyright (c) 2021, das and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

class MemoEkspedisi(Document):
	def validate(self):
		if self.eta and self.etd:
			if self.eta <= self.etd:
				frappe.throw("ETA is not allowed to be same or smaller date than ETD.")
		total = 0
		for row in self.items:
			if frappe.get_doc("Item",row.kode_material).weight_per_unit:
				row.berat = frappe.get_doc("Item",row.kode_material).weight_per_unit
			else:
				row.berat = 0
			total += flt(row.berat) * flt(row.stuffing)

		self.tonase__kg_ = total

	def before_insert(self):
		items = []
		for d in self.get('items'):
			data = {
				"item_code": d.kode_material,
				"qty": d.qty_rq
			}
			items.append(data)
		if self.stock_entry:
			cek_validasi2(self.stock_entry,items)
			cek_validasi(self.stock_entry)
	
	def onload(self):
		if self.purchase_order_delivery_pod:
			pod = self.purchase_order_delivery_pod
			pod_amount = frappe.db.sql(""" 
				SELECT 
				poi.net_total as total, poi.`total_taxes_and_charges`
				FROM `tabPurchase Order` poi WHERE poi.name = "{}"

				""".format(pod),as_dict=1)

			if len(pod_amount) > 0:
				self.total_harga_dpp = frappe.utils.flt(pod_amount[0].total)
				self.db_update()

@frappe.whitelist()
def get_rq_from_ste(ste):
	return frappe.db.sql(""" 
		SELECT tpo.material_request , tpo.parent
		FROM `tabStock Entry Detail` std 
		LEFT JOIN `tabPurchase Receipt Item` tpr ON tpr.parent = std.reference_purchase_receipt AND tpr.docstatus = 1
		LEFT JOIN `tabPurchase Order Item` tpo ON tpr.purchase_order = tpo.parent and tpo.docstatus = 1
		WHERE std.parent = "{}"
		GROUP BY tpo.material_request

		""".format(ste),as_dict=1)

@frappe.whitelist()
def get_items_from_ste(ste):
	list_me = []
	data_me = frappe.db.sql(""" SELECT name FROM `tabMemo Ekspedisi` WHERE stock_entry = "{}" and docstatus = 1 """.format(ste))
	for row in data_me:
		if row[0] not in list_me:
			list_me.append(row[0])

	if list_me:
		string = str(list_me)
		pencarian = str(string.replace("[", "").replace("]", ""))
	
		return frappe.db.sql(""" 
			SELECT 
			sted.item_code,
			sted.item_name,
			SUM(sted.`qty`) as qty, 
			sted.`uom`,
			ti.`weight_per_unit`,
			ti.`weight_uom`,
			mpt.kode_material,
			mpt.nama_barang,
			mpt.qty_rq as qty_rq,
			mpt.qty_uom,
			sted.name as ste_name

			FROM `tabStock Entry Detail` sted
			left JOIN `tabItem` ti ON ti.`item_code` = sted.`item_code`
			left join `tabMemo Pengiriman Table` mpt on mpt.kode_material = sted.item_code
			WHERE sted.parent = "{}" and mpt.parent in ({}) and mpt.docstatus = 1 and sted.docstatus < 2
			GROUP BY sted.item_code, sted.parent
			ORDER BY sted.idx
			""".format(ste,pencarian),as_dict=1)
	else:
		return frappe.db.sql(""" 

			SELECT
			a.item_code,
			a.item_name,
			sum(a.qty) as qty,
			a.uom,
			a.weight_per_unit,
			a.weight_uom,
			SUM(a.qty_rq) as qty_rq,
			SUM(a.total_qty) as total_qty,
			a.ste_name
			FROM
			(
			SELECT 
			sted.item_code,
			sted.item_name,
			sted.`qty`, 
			sted.`uom`,
			ti.`weight_per_unit`,
			ti.`weight_uom`,
			sted.reference_purchase_receipt,
			IF(sted.material_request_item IS NOT NULL,mri.qty,sted.qty) AS qty_rq,
			IF(sted.`docstatus` = 1, sted.qty,0) AS total_qty,
			sted.parent,
			sted.name as ste_name,
			sted.idx

			FROM `tabStock Entry Detail` sted
			JOIN `tabItem` ti ON ti.`item_code` = sted.`item_code`
			LEFT JOIN `tabPurchase Receipt Item` tpri 
			ON tpri.parent = sted.`reference_purchase_receipt`
			LEFT JOIN `tabMaterial Request Item` mri 
			ON mri.parent = sted.`material_request` AND mri.name = sted.`material_request_item`

			WHERE sted.parent = "{}"
			AND sted.docstatus < 2
			GROUP BY sted.name, sted.parent
			) a

			GROUP BY a.item_code, a.parent
			ORDER BY a.idx
			
			""".format(ste),as_dict=1)

@frappe.whitelist()
def get_rq_from_po(po):
	return frappe.db.sql(""" 
		SELECT std.material_request , tpo.name
		FROM `tabPurchase Order Item` std 
		LEFT JOIN `tabPurchase Order` tpo ON tpo.name = std.parent AND tpo.docstatus = 1
		WHERE std.parent = "{}"
		GROUP BY std.material_request

		""".format(po),as_dict=1)

@frappe.whitelist()
def get_items_from_po(po):
	return frappe.db.sql(""" 
		SELECT 
		sted.item_code,
		sted.item_name,
		sted.`qty`, 
		sted.`uom`,
		ti.`weight_per_unit`,
		ti.`weight_uom`

		FROM `tabPurchase Order Item` sted
		JOIN `tabItem` ti ON ti.`item_code` = sted.`item_code`

		WHERE sted.parent = "{}"

		""".format(po),as_dict=1)


@frappe.whitelist()
def get_dpp_ppn_from_pod(pod):
	return frappe.db.sql(""" 
		SELECT 
		poi.net_total as total, poi.`total_taxes_and_charges`
		FROM `tabPurchase Order` poi WHERE poi.name = "{}"

		""".format(pod),as_dict=1)


@frappe.whitelist()
def make_pod(memo_ekspedisi,po):
	supplier = frappe.get_value("Purchase Order",{"name": po}, "supplier")
	source = frappe.get_doc("Memo Ekspedisi",memo_ekspedisi)
	nama_kapal = frappe.get_value("Memo Ekspedisi",{"name": memo_ekspedisi}, "nama_kapal")
	rute_from = frappe.get_value("Memo Ekspedisi",{"name": memo_ekspedisi}, "rute_from")
	rute_to = frappe.db.get_list('Tabel Rute To Memo Permintaan Ekspedisi Eksternal',filters={'parent': memo_ekspedisi},fields=['rute_to'])
	# frappe.msgprint(supplier)
	target_doc = frappe.new_doc("Purchase Order")
	target_doc.is_pod = "POD"
	target_doc.supplier = ""
	target_doc.no_po = po
	target_doc.nama_kapal = nama_kapal
	target_doc.rute_from = rute_from
	target_doc.estimasi_tanggal_tiba=source.estimasi_tanggal_tiba
	target_doc.ukuran_bak_pod=source.ukuran_bak__kontainer
	if source.tujuan=="GIAS":
		target_doc.list_company_gias_pod=source.list_company_gias
	target_doc.alamat=source.alamat
	target_doc.tonase=source.tonase__kg_
	target_doc.tanggal_pengiriman=source.tanggal_pengiriman
	
	# for item in source.items:
	# 	row=target_doc.append('items', {})
	# 	row.item_code=item.kode_material
	# 	row.item_name=item.nama_barang
	# 	row.qty=item.stuffing
		
	row = target_doc.append('rute_to', {})
	for i in rute_to:
		row.rute_to = i['rute_to']

	target_doc.no_memo_ekspedisi = memo_ekspedisi
	naming_series = frappe.db.sql(""" 
		SELECT `value` FROM `tabSingles` 
		WHERE `field` = "pod_naming_series" """, as_dict=1)

	if len(naming_series) > 0:
		target_doc.naming_series = naming_series[0].value

	pod_taxes_template = frappe.db.sql(""" 
		SELECT `value` FROM `tabSingles` 
		WHERE `field` = "pod_taxes_template" """, as_dict=1)
	
	if len(pod_taxes_template) > 0:
		target_doc.taxes_and_charges = pod_taxes_template[0].value

	return target_doc.as_dict()

@frappe.whitelist()
def cek_validasi2(stock_entry,item):
	# return
	# frappe.throw(str(item))
	data = frappe.db.sql(""" 
		SELECT 
		mpt.kode_material,
		sum(mpt.qty_rq) as qty_rq 
		
		FROM `tabMemo Ekspedisi` me 
		left join `tabMemo Pengiriman Table` mpt on mpt.parent = me.name
		WHERE me.stock_entry = "{}" and me.docstatus !=2 
		AND workflow_state != "Rejected"
		group by mpt.kode_material
		""".format(stock_entry),as_dict=1)

	data2 = frappe.db.sql(""" 
		SELECT 
		sted.item_code,
		sted.`qty` 
		
		FROM `tabStock Entry Detail` sted
		JOIN `tabItem` ti ON ti.`item_code` = sted.`item_code`
		JOIN `tabStock Entry` ste ON ste.name = sted.parent

		WHERE sted.parent = "{}" AND ste.workflow_state != "Rejected"

		""".format(stock_entry),as_dict=1)
	
	# frappe.throw(str(data))	
	l_total = []
	for it in item:
		for dt in data:
			if it['item_code'] == dt['kode_material']:
				total = it['qty'] + dt['qty_rq']
				d_total = {
					"item_code": it['item_code'],
					"qty": total
				}
				l_total.append(d_total)
				# frappe.throw(str(l_total))
	
	cek = 0
	for i in l_total:
		for j in data2:
			if i['item_code'] == j['item_code']:
					if i['qty'] > j['qty']:
						frappe.throw(i['item_code']+ " di ME Melebihi qty di STE !")
						cek = cek + 1
				
	# if cek == len(l_total):
	# 	frappe.throw("QTY melebihi stock !")
	# else:
	# 	return

@frappe.whitelist()
def cek_validasi(stock_entry):
	# return
	# frappe.throw("tes123")
	data = frappe.db.sql(""" 
		SELECT 
		mpt.kode_material,
		sum(mpt.qty_rq) as qty_rq 
		
		FROM `tabMemo Ekspedisi` me 
		left join `tabMemo Pengiriman Table` mpt on mpt.parent = me.name
		WHERE me.stock_entry = "{}" and me.docstatus !=2 group by mpt.kode_material
		AND workflow_state != "Rejected"
		""".format(stock_entry),as_dict=1)

	data2 = frappe.db.sql(""" 
		SELECT 
		sted.item_code,
		sted.`qty` 
		
		FROM `tabStock Entry Detail` sted
		JOIN `tabItem` ti ON ti.`item_code` = sted.`item_code`
		JOIN `tabStock Entry` ste ON ste.name = sted.parent
		WHERE sted.parent = "{}" AND ste.workflow_state != "Rejected"

		""".format(stock_entry),as_dict=1)
	
	# frappe.throw(str(data))	
	cek = 0
	for i in data:
		for j in data2:
			if i['kode_material'] == j['item_code']:
					if i['qty_rq'] == j['qty']:
						cek = cek + 1
				
	if cek == len(data2):
		frappe.throw("Stock Entry sudah cukup !")
	else:
		return


