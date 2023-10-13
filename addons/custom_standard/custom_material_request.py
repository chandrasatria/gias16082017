import frappe,erpnext
from frappe.model.mapper import get_mapped_doc
from erpnext.stock.doctype.item.item import get_item_defaults
from frappe.utils import cstr, flt, getdate, new_line_sep, nowdate, add_days, get_link_to_form
from frappe.model.naming import make_autoname, revert_series_if_last
from addons.custom_method import check_list_company_gias
import json
@frappe.whitelist()
def create_mr_resolve(self,method):
	company_doc = frappe.get_doc("Company",self.company)
	if self.tipe_dokumen == "Submit" and self.buat_je_di == "Pusat" and company_doc.server == "Pusat" :
		cabang_doc = frappe.get_doc("List Company GIAS",self.cabang)
		# buat je
		je_baru = json.loads(self.data)
		
		je = frappe.get_doc(je_baru)
		for row in je.items:
			row.warehouse = frappe.get_doc("List Company GIAS",company_doc.nama_cabang).warehouse_penerimaan_dari_pusat
			row.cost_center = company_doc.cost_center

		je.__islocal = 1
		je.no_mr_blkp = je.name
		je.workflow_state = "Pending"
		je.docstatus = 0
		je.save()

		frappe.db.sql(""" UPDATE `tabMaterial Request` SET docstatus = 1, workflow_state = "Approved" WHERE name = "{}" """.format(je.name))
		frappe.db.sql(""" UPDATE `tabMaterial Request Item` SET docstatus = 1 WHERE parent = "{}" """.format(je.name))
		frappe.db.sql(""" UPDATE `tabAttachment Table` SET docstatus = 1 WHERE parent = "{}" """.format(je.name))
		frappe.db.commit()

		self.submit()

@frappe.whitelist()
def create_mr_log_debug():
	list_mr = [
		"MR-PKU-1-23-03-00762",
		"MR-PKU-1-23-03-00763"
	]

	for baris in list_mr:
		self = frappe.get_doc("Material Request",baris)
		check = frappe.db.sql(""" 
			SELECT
			name
			FROM `tabCustom Field` 
			WHERE name = "Material Request-blkp_supplier_name" 
		""")
		if len(check) > 0:
			
			ste_log = frappe.new_doc("MR BLKP Log")
			ste_log.nama_dokumen = self.name
			ste_log.tipe_dokumen = "Submit"
			ste_log.buat_je_di = "Pusat"
			ste_log.cabang = frappe.get_doc("Company","GIAS").nama_cabang
			self_clone = self
			for row in self_clone.attachment:
				if "https" not in row.attachment:
					
					row.attachment = "https://"+str(check_list_company_gias(ste_log.cabang))+str(row.attachment)
			
			self_clone.set_from_warehouse = ""
			self_clone.set_warehouse = ""
			self_clone.blkp_is_not_null = 1

			ste_log.data = frappe.as_json(self_clone)
			
			ste_log.company = self.company
			ste_log.submit()

@frappe.whitelist()
def create_mr_log(self,method):
	if frappe.get_doc("Company","GIAS").server == "Cabang":
		check = frappe.db.sql(""" 
			SELECT
			name
			FROM `tabCustom Field` 
			WHERE name = "Material Request-blkp_supplier_name" 
		""")
		if len(check) > 0:
			if self.blkp_is_not_null == 1:
				ste_log = frappe.new_doc("MR BLKP Log")
				ste_log.nama_dokumen = self.name
				ste_log.tipe_dokumen = "Submit"
				ste_log.buat_je_di = "Pusat"
				ste_log.cabang = frappe.get_doc("Company","GIAS").nama_cabang
				self_clone = self
				for row in self_clone.attachment:
					if "https" not in row.attachment:
						
						row.attachment = "https://"+str(check_list_company_gias(ste_log.cabang))+str(row.attachment)
				
				self_clone.set_from_warehouse = ""
				self_clone.set_warehouse = ""
		
				ste_log.data = frappe.as_json(self_clone)
				print(ste_log.data)
				ste_log.company = self.company
				ste_log.submit()


@frappe.whitelist()
def make_purchase_order_custom(source_name, target_doc=None):

	def postprocess(source, target_doc):
		if frappe.flags.args and frappe.flags.args.default_supplier:
			# items only for given default supplier
			supplier_items = []
			for d in target_doc.items:
				default_supplier = get_item_defaults(d.item_code, target_doc.company).get('default_supplier')
				if frappe.flags.args.default_supplier == default_supplier:
					supplier_items.append(d)
			target_doc.items = supplier_items

		set_missing_values(source, target_doc)

	def select_item(d):
		return d.ordered_qty < d.stock_qty

	doclist = get_mapped_doc("Material Request", source_name, 	{
		"Material Request": {
			"doctype": "Purchase Order",
			"validation": {
				"docstatus": ["=", 1],
				"material_request_type": ["=", "Purchase"]
			}
		},
		"Material Request Item": {
			"doctype": "Purchase Order Item",
			"field_map": [
				["name", "material_request_item"],
				["parent", "material_request"],
				["uom", "stock_uom"],
				["uom", "uom"],
				["sales_order", "sales_order"],
				["sales_order_item", "sales_order_item"]
			],
			"postprocess": update_item,
			"condition": select_item
		}
	}, target_doc, postprocess)

	sumber_doc = frappe.get_doc("Material Request", source_name)
	if sumber_doc.cabang:
		doclist.cabang = sumber_doc.cabang

	doclist.no_material_request = sumber_doc.name

	return doclist

@frappe.whitelist()
def check_ps_approver(doc,method):
	for row in doc.items:
		item_doc = frappe.get_doc("Item", row.item_code)
		if not item_doc.ps_approver:
			# frappe.throw("Please set PS Approver for Item {}".format(item_doc.item_name))
			pass
		else:
			if doc.ps_approver and item_doc.ps_approver:
				if item_doc.ps_approver != doc.ps_approver:
					if doc.dari_cabang == 0:
						frappe.throw("Material Request cannot have different items for different PS. Item being referenced {} - {} ".format(item_doc.name,item_doc.item_name))
@frappe.whitelist()
def custom_autoname_baru(doc,method):

	if doc.get("no_mr_blkp"):
		doc.name = doc.get("no_mr_blkp")
	else:
		company_doc = frappe.get_doc("Company", doc.company)
		list_company_gias_doc = frappe.get_doc("List Company GIAS",company_doc.nama_cabang)
		singkatan = list_company_gias_doc.singkatan_cabang
		
		if doc.type_pembelian == "Non Inventory":
			if company_doc.server == "Pusat":
				doc.naming_series = "MRN-H-{{singkatan}}-1-.YY.-.MM.-.#####"
			else:
				doc.naming_series = "MRN-{{singkatan}}-1-.YY.-.MM.-.#####"
		else:
			if company_doc.server == "Pusat":
				doc.naming_series = "MR-H-{{singkatan}}-1-.YY.-.MM.-.#####"
			else:
				doc.naming_series = "MR-{{singkatan}}-1-.YY.-.MM.-.#####"


		# doc.name = make_autoname(doc.naming_series.replace("{{singkatan}}",singkatan), doc=doc)

		month = frappe.utils.formatdate(frappe.utils.getdate(doc.transaction_date),"MM")
		year = frappe.utils.formatdate(frappe.utils.getdate(doc.transaction_date),"YY")

		if doc.tax_or_non_tax == "Tax":
			tax = 1
		else:
			tax = 2

		if doc.type_pembelian == "Non Inventory":
			if company_doc.server == "Pusat":
				doc.naming_series = "MRN-H-{{singkatan}}-1-.YY.-.MM.-.#####"
			else:
				doc.naming_series = "MRN-{{singkatan}}-1-.YY.-.MM.-.#####"
		else:
			if company_doc.server == "Pusat":
				doc.naming_series = "MR-H-{{singkatan}}-1-.YY.-.MM.-.#####"
			else:
				doc.naming_series = "MR-{{singkatan}}-1-.YY.-.MM.-.#####"

		doc.name = make_autoname(doc.naming_series.replace("-1-","-{}-".format(tax)).replace("{{singkatan}}",singkatan).replace(".YY.",year).replace(".MM.",month))


	
@frappe.whitelist()
def custom_autoname(doc,method):

	if doc.material_request_type == "Purchase":
		if doc.type_pembelian == "Inventory":
			singkatan = ""
			if doc.cabang:
				singkatan = frappe.get_doc("List Company GIAS", doc.cabang).singkatan_cabang
			else:
				singkatan = "HO"

			type_ = ""
			if doc.type_request == "WH Pusat":
				type_ = "Type_1"
			elif doc.type_request == "Pembelian Lokal Full":
				type_ = "Type_2"
			elif doc.type_request == "Import":
				type_ = "Type_3"
			elif doc.type_request == "Group":
				type_ = "Type_4"

			if "branch" not in str(frappe.utils.get_url()):
				doc.naming_series = """RQ-HO-{{request_type}}-{{singkatan_cabang}}-.YYYY.-.MM.-.####""".replace("{{singkatan_cabang}}",singkatan).replace("{{request_type}}",type_)
			else:
				doc.naming_series = """RQ-{{request_type}}-{{singkatan_cabang}}-.YYYY.-.MM.-.####""".replace("{{singkatan_cabang}}",singkatan).replace("{{request_type}}",type_)
		
		else:
			singkatan = ""
			if doc.cabang:
				singkatan = frappe.get_doc("List Company GIAS", doc.cabang).singkatan_cabang
			else:
				singkatan = "HO"

			if "branch" not in str(frappe.utils.get_url()):
				doc.naming_series = """RQN-HO-{{singkatan_cabang}}-.YYYY.-.MM.-.####""".replace("{{singkatan_cabang}}",singkatan)
			else:
				doc.naming_series = """RQN-{{singkatan_cabang}}-.YYYY.-.MM.-.####""".replace("{{singkatan_cabang}}",singkatan)

			
	
	else:
		singkatan = ""
		if doc.cabang:
			singkatan = frappe.get_doc("List Company GIAS", doc.cabang).singkatan_cabang
		else:
			singkatan = "HO"

		if "branch" not in str(frappe.utils.get_url()):
			doc.naming_series = """MR-HO-{{singkatan_cabang}}-.YYYY.-.MM.-.####""".replace("{{singkatan_cabang}}",singkatan)
		else:
			doc.naming_series = """MR-{{singkatan_cabang}}-.YYYY.-.MM.-.####""".replace("{{singkatan_cabang}}",singkatan)

			
		

	doc.name = make_autoname(doc.naming_series, doc=doc)
	# validasi autoname
	ambil_4 = str(doc.name)[:-4]
	# nomor = frappe.db.sql("""
	# 	SELECT LPAD(SUBSTRING(NAME, -4) + 1,4,0) AS nomor_sekarang 
	# 	FROM `tabMaterial Request`
	# 	WHERE NAME LIKE "%{}%"
	# 	ORDER BY SUBSTRING(NAME, -4) DESC
	# 	LIMIT 1 """.format(ambil_4), as_dict=1)

	# if len(nomor) < 1:
	# 	doc.name = ambil_4 + "0001"
	# else:
	# 	doc.name = ambil_4 + nomor[0].nomor_sekarang


@frappe.whitelist()
def set_requested(doc,method):
	check = frappe.db.sql(""" 
		SELECT
		name
		FROM `tabCustom Field` 
		WHERE name = "Material Request-cabang_material_request" 
	""")
	list_mr = []
	if len(check) > 0:
		for row in doc.items:
			if row.cabang_material_request:
				if row.cabang_material_request not in list_mr:
					list_mr.append(row.cabang_material_request)

	for row in list_mr:
		mreq = frappe.get_doc("Material Request", row)
		mreq.mr_gabungan = doc.name
		mreq.db_update()
		
		mreq = frappe.get_doc("Material Request", row)
		mreq.workflow_state = "Requested"
		mreq.db_update()


@frappe.whitelist()
def set_requested_cancel(doc,method):
	check = frappe.db.sql(""" 
		SELECT
		name
		FROM `tabCustom Field` 
		WHERE name = "Material Request-cabang_material_request" 
	""")

	list_mr = []
	if len(check) > 0:
		for row in doc.items:
			if row.cabang_material_request:
				if row.cabang_material_request not in list_mr:
					list_mr.append(row.cabang_material_request)

	for row in list_mr:
		mreq = frappe.get_doc("Material Request", row)
		mreq.mr_gabungan = doc.name
		mreq.db_update()

		mreq = frappe.get_doc("Material Request", row)
		mreq.workflow_state = "Approved"
		mreq.db_update()


@frappe.whitelist()
def get_items_mr_non_ready(mreq):
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
		tmr.cabang

		FROM `tabMaterial Request Item` tmri
		JOIN `tabMaterial Request` tmr ON tmr.name = tmri.parent
		WHERE 
		tmri.parent = "{}"
	""".format(mreq), as_dict=1)


@frappe.whitelist()
def get_cabang(user):
	return frappe.db.sql(""" SELECT cabang 
		FROM `tabUser Cabang Connection` ucc WHERE name = "{}" """.format(user),as_dict=1)

@frappe.whitelist()
def get_user():
	print(frappe.user)

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_cabang_query(doctype, txt, searchfield, start, page_len, filters):
	from erpnext.controllers.queries import get_match_cond

	if not filters: filters = {}
	list_cabang = frappe.db.sql(""" SELECT cabang 
		FROM `tabUser Cabang Connection` ucc WHERE name = "{}" """.format(frappe.session.user),as_dict=1)
	
	if len(list_cabang) > 0:
		condition = ""
		condition += """ and name = "{}" """.format(list_cabang[0].cabang)

		return frappe.db.sql("""select name FROM
			`tabList Company GIAS` WHERE
				(name LIKE %(txt)s
				{condition}) {match_condition}"""
			.format(condition=condition, key=searchfield,
				match_condition=get_match_cond(doctype)), {
				'company': filters.get("company", ""),
				'txt': '%' + txt + '%'
			})

@frappe.whitelist()
def calculate_total(doc,method):
	total = 0
	for row in doc.items:
		if row.rate == 0:
			frappe.throw("Rate in row {} - {} is mandatory".format(row.idx, row.item_code))
		else:
			row.amount = frappe.utils.flt(row.rate) * frappe.utils.flt(row.qty)
		total = total + frappe.utils.flt(row.amount) or 0

	doc.total = total

	check = frappe.db.sql(""" 
		SELECT
		name
		FROM `tabCustom Field` 
		WHERE name = "Material Request-blkp_supplier_name" 
	""")
	if len(check) > 0:
		if doc.blkp_supplier_name:
			doc.blkp_is_not_null = 1
		else:
			doc.blkp_is_not_null = 0

@frappe.whitelist()
def onload_calculate_total(doc,method):
	total = 0
	for row in doc.items:
		row.amount = frappe.utils.flt(row.rate) * frappe.utils.flt(row.qty)
		total = total + frappe.utils.flt(row.amount) or 0

	doc.total = total
	doc.db_update()

def update_item(obj, target, source_parent):
	target.conversion_factor = obj.conversion_factor
	target.qty = flt(flt(obj.stock_qty) - flt(obj.ordered_qty))/ target.conversion_factor
	target.stock_qty = (target.qty * target.conversion_factor)
	if getdate(target.schedule_date) < getdate(nowdate()):
		target.schedule_date = None

def set_missing_values(source, target_doc):
	if target_doc.doctype == "Purchase Order" and getdate(target_doc.schedule_date) <  getdate(nowdate()):
		target_doc.schedule_date = None
	target_doc.run_method("set_missing_values")
	target_doc.run_method("calculate_taxes_and_totals")

@frappe.whitelist()
def custom_make_purchase_order(source_name, target_doc=None):

	def postprocess(source, target_doc):
		if frappe.flags.args and frappe.flags.args.default_supplier:
			# items only for given default supplier
			supplier_items = []
			for d in target_doc.items:
				default_supplier = get_item_defaults(d.item_code, target_doc.company).get('default_supplier')
				if frappe.flags.args.default_supplier == default_supplier:
					supplier_items.append(d)
			target_doc.items = supplier_items

		set_missing_values(source, target_doc)

	def select_item(d):
		return d.ordered_qty < d.stock_qty

	doclist = get_mapped_doc("Material Request", source_name, 	{
		"Material Request": {
			"doctype": "Purchase Order",
			"validation": {
				"docstatus": ["=", 1],
				"material_request_type": ["=", "Purchase"]
			}
		},
		"Material Request Item": {
			"doctype": "Purchase Order Item",
			"field_map": [
				["name", "material_request_item"],
				["parent", "material_request"],
				["uom", "stock_uom"],
				["uom", "uom"],
				["sales_order", "sales_order"],
				["sales_order_item", "sales_order_item"]
			],
			"postprocess": update_item,
			"condition": select_item
		}
	}, target_doc, postprocess)

	doc_asli = frappe.get_doc("Material Request",source_name)
	if doc_asli.cabang:	
		doclist.cabang = doc_asli.cabang
	if doc_asli.nama_supplier:	
		doclist.supplier = doc_asli.nama_supplier
		doclist.supplier_name = frappe.get_doc("Supplier",doclist.supplier).supplier_name
	for row in doclist.items:
		row.mr_rate = row.rate

	doclist.tipe_inventory_pembelian = doc_asli.type_pembelian
	doclist.no_material_request = source_name
	return doclist

@frappe.whitelist()
def make_stock_entry(source_name, target_doc=None):
	def update_item(obj, target, source_parent):

		if source_parent.material_request_type == "Purchase" and source_parent.cabang:
			qty = flt(flt(obj.stock_qty)/ target.conversion_factor)
		else:
			qty = flt(flt(obj.stock_qty) - flt(obj.ordered_qty))/ target.conversion_factor \
				if flt(obj.stock_qty) > flt(obj.ordered_qty) else 0

		target.qty = qty
		target.transfer_qty = qty * obj.conversion_factor
		target.conversion_factor = obj.conversion_factor
		target.weight_per_stock_qty = frappe.get_doc("Item", obj.item_code).weight_per_unit
		target.volume_per_stock_qty = frappe.get_doc("Item", obj.item_code).volume

		if source_parent.material_request_type == "Material Transfer" or source_parent.material_request_type == "Customer Provided":
			target.t_warehouse = obj.warehouse
		else:
			target.s_warehouse = obj.warehouse

		if source_parent.material_request_type == "Customer Provided":
			target.allow_zero_valuation_rate = 1

		if source_parent.material_request_type == "Material Transfer":
			target.s_warehouse = obj.from_warehouse

	def set_missing_values(source, target):
		target.purpose = source.material_request_type
		if source.job_card:
			target.purpose = 'Material Transfer for Manufacture'

		if source.material_request_type == "Customer Provided":
			target.purpose = "Material Receipt"

		if source.material_request_type == "Purchase":
			target.purpose = "Material Transfer"

		target.run_method("calculate_rate_and_amount")
		target.set_stock_entry_type()
		target.set_job_card_data()

	doc_asli = frappe.get_doc("Material Request", source_name)

	if doc_asli.material_request_type != "Purchase":
		doclist = get_mapped_doc("Material Request", source_name, {
			"Material Request": {
				"doctype": "Stock Entry",
				"validation": {
					"docstatus": ["=", 1],
					"material_request_type": ["in", ["Material Transfer", "Material Issue", "Customer Provided", "Purchase"]]
				}
			},
			"Material Request Item": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"name": "material_request_item",
					"parent": "material_request",
					"uom": "stock_uom"
				},
				"postprocess": update_item,
				"condition": lambda doc: doc.ordered_qty < doc.stock_qty
			}
		}, target_doc, set_missing_values)
	else:
		doclist = get_mapped_doc("Material Request", source_name, {
			"Material Request": {
				"doctype": "Stock Entry",
				"validation": {
					"docstatus": ["=", 1],
					"material_request_type": ["in", ["Material Transfer", "Material Issue", "Customer Provided", "Purchase"]]
				}
			},
			"Material Request Item": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"name": "material_request_item",
					"parent": "material_request",
					"uom": "stock_uom"
				},
				"postprocess": update_item
			}
		}, target_doc, set_missing_values)

	if doclist.cabang:
		doclist.branch = frappe.get_doc("List Company GIAS", doclist.cabang).accounting_dimension

	return doclist

@frappe.whitelist()
def make_stock_entry_kecabang(source_name, target_doc=None):
	def update_item(obj, target, source_parent):

		if source_parent.material_request_type == "Purchase" and source_parent.cabang:
			qty = flt(flt(obj.stock_qty)/ target.conversion_factor)
		else:
			qty = flt(flt(obj.stock_qty) - flt(obj.ordered_qty))/ target.conversion_factor \
				if flt(obj.stock_qty) > flt(obj.ordered_qty) else 0

		target.qty = qty
		target.transfer_qty = qty * obj.conversion_factor
		target.conversion_factor = obj.conversion_factor
		target.weight_per_stock_qty = frappe.get_doc("Item", obj.item_code).weight_per_unit
		target.volume_per_stock_qty = frappe.get_doc("Item", obj.item_code).volume

		if source_parent.material_request_type == "Material Transfer" or source_parent.material_request_type == "Customer Provided":
			target.t_warehouse = obj.warehouse
		else:
			target.s_warehouse = obj.warehouse

		if source_parent.material_request_type == "Customer Provided":
			target.allow_zero_valuation_rate = 1

		if source_parent.material_request_type == "Material Transfer":
			target.s_warehouse = obj.from_warehouse

	def set_missing_values(source, target):
		
		target.purpose = 'Material Issue'
		target.stock_entry_type = 'Material Issue'

		target.run_method("calculate_rate_and_amount")
		target.set_stock_entry_type()
		target.set_job_card_data()

	doc_asli = frappe.get_doc("Material Request", source_name)

	if doc_asli.material_request_type != "Purchase":
		doclist = get_mapped_doc("Material Request", source_name, {
			"Material Request": {
				"doctype": "Stock Entry",
				"validation": {
					"docstatus": ["=", 1],
					"material_request_type": ["in", ["Material Transfer", "Material Issue", "Customer Provided", "Purchase"]]
				}
			},
			"Material Request Item": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"name": "material_request_item",
					"parent": "material_request",
					"uom": "stock_uom"
				},
				"postprocess": update_item,
				"condition": lambda doc: doc.ordered_qty < doc.stock_qty
			}
		}, target_doc, set_missing_values)
	else:
		doclist = get_mapped_doc("Material Request", source_name, {
			"Material Request": {
				"doctype": "Stock Entry",
				"validation": {
					"docstatus": ["=", 1],
					"material_request_type": ["in", ["Material Transfer", "Material Issue", "Customer Provided", "Purchase"]]
				}
			},
			"Material Request Item": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"name": "material_request_item",
					"parent": "material_request",
					"uom": "stock_uom"
				},
				"postprocess": update_item
			}
		}, target_doc, set_missing_values)

	if doclist.cabang:
		doclist.branch = frappe.get_doc("List Company GIAS", doclist.cabang).accounting_dimension

	doclist.transfer_ke_cabang_pusat = 1
	doclist.transfer_ke_cabang_mana = doc_asli.cabang
	doclist.purpose = 'Material Issue'
	doclist.stock_entry_type = 'Material Issue'


	return doclist