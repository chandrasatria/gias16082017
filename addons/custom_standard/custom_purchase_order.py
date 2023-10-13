import frappe,erpnext
from frappe.utils import (today, flt, cint, fmt_money, formatdate,
	getdate, add_days, add_months, get_last_day, nowdate, get_link_to_form)
from frappe.model.naming import make_autoname, revert_series_if_last
from frappe.model.mapper import get_mapped_doc

@frappe.whitelist()
def get_purchase_tax():
	return frappe.db.sql(""" SELECT name FROM `tabPurchase Taxes and Charges Template` WHERE disabled = 0 and default_tax = 1 LIMIT 1 """, as_dict=1)

@frappe.whitelist()
def benerno_rate(self,method):
	for row in self.items:
		if row.rate != row.price_list_rate:
			if row.material_request:
				row.price_list_rate = row.rate
				row.discount_amount = 0
				row.margin_rate_or_amount = 0

	# self.calculate_taxes_and_totals()

@frappe.whitelist()
def validate_nomor_rq(self,method):

	for row in self.items:
		if row.material_request:
			if not self.nomor_rq:
				self.nomor_rq = row.material_request


	if self.docstatus < 2:
		if self.nomor_rq:
			if frappe.get_doc("Material Request", self.nomor_rq).docstatus == 2:
				self.nomor_rq = ""
				self.db_update()

@frappe.whitelist()
def cek_template_dan_tax(self,method):

	if self.set_warehouse:
		for row in self.items:
			row.warehouse = self.set_warehouse

	if self.taxes_and_charges and not self.taxes:
		frappe.throw("There are template for taxes but the table is empty. Please reapply the template.")


@frappe.whitelist()
def rename_po():
	list_po = frappe.db.sql(""" SELECT name FROM `tabPurchase Order` WHERE name LIKE "%{{initial_supplier}}%" """)
	for po in list_po:
		po_doc = frappe.get_doc("Purchase Order", po[0])
		supp_doc = frappe.get_doc("Supplier", po_doc.supplier)
		short_code = supp_doc.supplier_short_code


		string_name = po_doc.name.replace("{{initial_supplier}}", short_code)
		size = len(string_name)
		cut_name = string_name[:size - 2]
		search_name = string_name[:size - 5]
		cut_name = cut_name + "0"
		no_terakhir = 0
		no_series = frappe.db.sql(""" SELECT name, current FROM `tabSeries` WHERE name = "{}" """.format(search_name))
		if len(no_series) > 0:
			no_terakhir = int(no_series[0][1]) + 1
		else:
			frappe.db.sql(""" INSERT INTO `tabSeries` (name, current) VALUES ("{}",1) """.format(search_name))
			no_terakhir = 1

		cut_name = cut_name + str(no_terakhir)
		if no_terakhir > 1:
			frappe.db.sql(""" UPDATE `tabSeries` SET current = {} WHERE name = "{}" """.format(no_terakhir,search_name))
		frappe.rename_doc("Purchase Order",po_doc.name, cut_name)

@frappe.whitelist()
def cancel_flag(self,method):
	if self.is_pod == "POD": 
		self.flags.ignore_links = True
	
	check_pinv = frappe.db.sql(""" 
		SELECT sii.parent FROM `tabPurchase Invoice Item` sii
		JOIN `tabPurchase Invoice` tsi ON tsi.name = sii.parent
		WHERE sii.purchase_order = "{}" and sii.docstatus = 0 and tsi.workflow_state != "Rejected" """.format(self.name))
	if check_pinv:
		if check_pinv[0]:
			if check_pinv[0][0]:
				frappe.throw("There is Purchase Invoice Draft with number {} so this Purchase Order cannot be cancelled.".format(check_pinv[0][0]))
	
	check_prec = frappe.db.sql(""" 
		SELECT sii.parent FROM `tabPurchase Receipt Item` sii
		JOIN `tabPurchase Invoice` tsi ON tsi.name = sii.parent
		WHERE sii.purchase_order = "{}" and sii.docstatus = 0 and tsi.workflow_state != "Rejected" """.format(self.name))
	if check_prec:
		if check_prec[0]:
			if check_prec[0][0]:
				frappe.throw("There is Purchase Receipt Draft with number {} so this Purchase Order cannot be cancelled.".format(check_prec[0][0]))
	

@frappe.whitelist()
def get_sq(doc,method):
	for d in doc.items:
		if d.supplier_quotation:
			data = frappe.get_value("Supplier Quotation",{"name" : d.supplier_quotation}, "grand_total")
			if doc.grand_total != data:
				frappe.throw("Harga Berbeda dengan Supplier Quotation !")

@frappe.whitelist()
def get_memo(memo_ekspedisi):
	query_detail = frappe.db.sql(""" 
		SELECT me.purchase_order,me.nama_kapal,me.rute_from,po.supplier 
		FROM `tabMemo Ekspedisi` me 
		join `tabPurchase Order` po on me.purchase_order = po.name
		WHERE me.name = "{}" """.format(memo_ekspedisi),as_dict=1)
	query_rute = frappe.db.sql(""" 
		SELECT rt.rute_to FROM `tabTabel Rute To Memo Permintaan Ekspedisi Eksternal` rt
		WHERE rt.parent = "{}" """.format(memo_ekspedisi),as_dict=1)
	query_kontainer = frappe.db.sql("""
		SELECT * FROM `tabMemo Pengiriman Table` WHERE parent = "{}"
	""".format(memo_ekspedisi),as_dict=1)
	
	return query_detail,query_rute,query_kontainer

@frappe.whitelist()
def update_pod(doc,method):
	# frappe.throw("coba pod")
	if doc.is_pod == "POD" and doc.no_memo_ekspedisi:
		frappe.db.sql("""UPDATE `tabMemo Ekspedisi` SET purchase_order_delivery_pod='"""+doc.name+"""' WHERE name='"""+doc.no_memo_ekspedisi+"""'""")
		frappe.db.commit()

	for row in doc.items:
		row.billed_amt = 0

@frappe.whitelist()
def check_tax_purchase(doc,method):
	for row in doc.taxes:
		account_doc = frappe.get_doc("Account",row.account_head)
		if account_doc.account_type == "Receivable" or account_doc.account_type == "Payable":
			frappe.throw("Account Receivable or Payable are not allowed in taxes.")


@frappe.whitelist()
def check_material_request(doc,method):
	for row in doc.items:
		if row.material_request_item:
			list_mr_item = frappe.db.sql(""" 
			SELECT name, parent FROM `tabPurchase Order Item`
			WHERE material_request_item = "{}" 
			AND parent != "{}"
			AND docstatus = 1
			""".format(row.material_request_item, doc.name))

			if len(list_mr_item) > 0:
				frappe.throw("Item {} - {} has been made Purchase Order in {}".format(row.item_code, row.item_name, row.parent))
			

@frappe.whitelist()
def custom_autoname_po(doc,method):

	company_doc = frappe.get_doc("Company", doc.company)
	singkatan = "HO"
	tipe = "INV"

	company_doc = frappe.get_doc("Company", doc.company)
	list_company_gias_doc = frappe.get_doc("List Company GIAS",company_doc.nama_cabang)
	singkatan = list_company_gias_doc.singkatan_cabang
	
	if doc.nomor_rq:
		rq = frappe.get_doc("Material Request", doc.nomor_rq)
		if rq.cabang:
			singkatan = frappe.get_doc("List Company GIAS", rq.cabang).singkatan_cabang
		if rq.type_pembelian != "Inventory":
			tipe = "NON-INV"
	
	if doc.type_pembelian != "Inventory":
		tipe = "NON-INV"

	if doc.is_pod == "POD":
		doc.naming_series = """POD-{{singkatan}}-{tax}-.YY.-.MM.-.#####""".replace("{{singkatan}}",singkatan)
	elif tipe == "NON-INV" :
		doc.naming_series = """PO-NON-INV-{tax}-.YY.-.MM.-.#####"""
	else:
		initial_supplier = ""
		if doc.supplier:
			doc_supp = frappe.get_doc("Supplier", doc.supplier)
			if not doc_supp.supplier_short_code:
				frappe.throw("Please complete supplier short code in supplier {} as its needed for naming series.".format(doc.supplier))
			else:
				initial_supplier = doc_supp.supplier_short_code
		
		doc.naming_series = """PO-{{initial_supplier}}-INV-{tax}-.YY.-.MM.-.#####""".replace("{{initial_supplier}}",initial_supplier)
	
	# doc.name = make_autoname(doc.naming_series, doc=doc)

	month = frappe.utils.formatdate(frappe.utils.getdate(doc.transaction_date),"MM")
	year = frappe.utils.formatdate(frappe.utils.getdate(doc.transaction_date),"YY")

	if doc.tax_or_non_tax == "Tax":
		tax = 1
	else:
		tax = 2
	doc.name = make_autoname(doc.naming_series.replace("-{tax}-","-{}-".format(tax)).replace(".YY.",year).replace(".MM.",month), doc=doc)



@frappe.whitelist()
def save_purchase_order():
	doc = frappe.get_doc("Purchase Order", "PUR-ORD-2021-00059-2")
	doc.save()

@frappe.whitelist()
def initial_outstanding_qty(self,method):
	total_qty = 0
	for row in self.items:
		total_qty += row.qty

	self.outstanding_qty_po = total_qty

@frappe.whitelist()
def calculate_advance_paid(self,method):
	if self.doctype == "Sales Order":
		dr_or_cr = "credit_in_account_currency"
		rev_dr_or_cr = "debit_in_account_currency"
		party = self.customer
	else:
		dr_or_cr = "debit_in_account_currency"
		rev_dr_or_cr = "credit_in_account_currency"
		party = self.supplier

	advance = frappe.db.sql("""
		select
			account_currency, sum({dr_or_cr}) - sum({rev_dr_cr}) as amount
		from
			`tabGL Entry`
		where
			against_voucher_type = %s and against_voucher = %s and party=%s
			and docstatus = 1
	""".format(dr_or_cr=dr_or_cr, rev_dr_cr=rev_dr_or_cr), (self.doctype, self.name, party), as_dict=1) #nosec

	if advance:
		advance = advance[0]

		advance_paid = flt(advance.amount, self.precision("advance_paid"))
		formatted_advance_paid = fmt_money(advance_paid, precision=self.precision("advance_paid"),
										   currency=advance.account_currency)

		frappe.db.set_value(self.doctype, self.name, "party_account_currency",
							advance.account_currency)

		if advance.account_currency == self.currency:
			order_total = self.get("rounded_total") or self.grand_total
			precision = "rounded_total" if self.get("rounded_total") else "grand_total"
		else:
			order_total = self.get("base_rounded_total") or self.base_grand_total
			precision = "base_rounded_total" if self.get("base_rounded_total") else "base_grand_total"

		formatted_order_total = fmt_money(order_total, precision=self.precision(precision),
										  currency=advance.account_currency)

		if self.currency == self.company_currency and advance_paid > order_total:
			frappe.throw(_("Total advance ({0}) against Order {1} cannot be greater than the Grand Total ({2})")
						 .format(formatted_advance_paid, self.name, formatted_order_total))


		doc = frappe.get_doc(self.doctype, self.name)
		doc.advance_paid = advance_paid
		doc.db_update()
		frappe.db.commit()
	else:
		doc = frappe.get_doc(self.doctype, self.name)
		doc.advance_paid = advance_paid
		doc.db_update()
		frappe.db.commit()


@frappe.whitelist()
def calculate_difference_rate(doc,method):
	difference = 0
	for row in doc.items:
		if row.material_request_item:
			if not row.mr_rate:
				rate = frappe.db.sql(""" SELECT rate FROM `tabMaterial Request Item` WHERE name = "{}" """.format(row.material_request_item), as_dict=1)
				if len(rate) > 0:
					row.mr_rate = flt(rate[0].rate)

		difference += row.rate - row.mr_rate

	doc.total_difference_rate = difference



@frappe.whitelist()
def get_pod_taxes():
	return frappe.db.sql(""" 
		SELECT `value` FROM `tabSingles` 
		WHERE `field` = "pod_taxes_template" """, as_dict=1)

@frappe.whitelist()
def get_pod_naming_series():
	return frappe.db.sql(""" 
		SELECT `value` FROM `tabSingles` 
		WHERE `field` = "pod_naming_series" """, as_dict=1)

@frappe.whitelist()
def get_non_pod_naming_series():
	return frappe.db.sql(""" 
		SELECT `value` FROM `tabSingles` 
		WHERE `field` = "non_pod_naming_series" """, as_dict=1)

@frappe.whitelist()
def get_rute_to(no_me):
	return frappe.db.sql(""" 
		SELECT `rute_to` FROM `tabTabel Rute To Memo Permintaan Ekspedisi Eksternal` 
		WHERE `parent` = "{}" """.format(no_me), as_dict=1)

@frappe.whitelist()
def make_stock_entry(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		qty = flt(flt(obj.stock_qty) - flt(obj.ordered_qty))/ target.conversion_factor \
			if flt(obj.stock_qty) > flt(obj.ordered_qty) else 0
		target.qty = qty
		target.transfer_qty = qty * obj.conversion_factor
		target.conversion_factor = obj.conversion_factor

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

		target.run_method("calculate_rate_and_amount")
		target.set_stock_entry_type()
		target.set_job_card_data()

	doclist = get_mapped_doc("Material Request", source_name, {
		"Material Request": {
			"doctype": "Stock Entry",
			"validation": {
				"docstatus": ["=", 1],
				"material_request_type": ["in", ["Material Transfer", "Material Issue", "Customer Provided"]]
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

	return doclist

@frappe.whitelist()
def custom_make_purchase_receipt(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	def update_item(obj, target, source_parent):
		target.qty = flt(obj.qty) - flt(obj.received_qty)
		target.stock_qty = (flt(obj.qty) - flt(obj.received_qty)) * flt(obj.conversion_factor)
		target.amount = (flt(obj.qty) - flt(obj.received_qty)) * flt(obj.rate)
		target.base_amount = (flt(obj.qty) - flt(obj.received_qty)) * \
			flt(obj.rate) * flt(source_parent.conversion_rate)

	doc = get_mapped_doc("Purchase Order", source_name,	{
		"Purchase Order": {
			"doctype": "Purchase Receipt",
			"field_map": {
				"supplier_warehouse":"supplier_warehouse"
			},
			"validation": {
				"docstatus": ["=", 1],
			}
		},
		"Purchase Order Item": {
			"doctype": "Purchase Receipt Item",
			"field_map": {
				"name": "purchase_order_item",
				"parent": "purchase_order",
				"bom": "bom",
				"material_request": "material_request",
				"material_request_item": "material_request_item"
			},
			"postprocess": update_item,
			"condition": lambda doc: abs(doc.received_qty) < abs(doc.qty) and doc.delivered_by_supplier!=1
		},
		"Purchase Taxes and Charges": {
			"doctype": "Purchase Taxes and Charges",
			"add_if_empty": False
		}
	}, target_doc, set_missing_values)
	doc.tipe_inventory_pembelian = frappe.get_doc("Purchase Order", source_name).type_pembelian
	doc.cabang = frappe.get_doc("Purchase Order", source_name).cabang

	return doc