import frappe,erpnext
from frappe.utils import (today, flt, cint, fmt_money, formatdate,
	getdate, add_days, add_months, get_last_day, nowdate, get_link_to_form)
from frappe.model.mapper import get_mapped_doc
from erpnext.accounts.party import get_party_account, get_due_date
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt,get_item_account_wise_additional_cost
from erpnext.accounts.utils import get_account_currency
from frappe import _, throw
from six import iteritems
from frappe.model.naming import make_autoname, revert_series_if_last
import re

@frappe.whitelist()
def custom_onload(self,method):
	if self.docstatus == 1:
		if flt(self.per_billed) < 100:
			self.update_billing_status()
			self.db_update()
		
		if flt(self.per_billed) == 100:
			self.per_billed = 100
			self.status = "Completed"
			self.db_update()
			frappe.db.sql(""" UPDATE `tabPurchase Receipt` SET status = "Completed", per_billed = 100 WHERE name = "{}" """.format(self.name))
			frappe.db.commit()
@frappe.whitelist()
def lcv_after_submit(self,method):
	for row in self.purchase_receipts:
		repair_gl_entry("Purchase Receipt",row.receipt_document)
		from addons.custom_standard.view_ledger_create import create_gl_custom_purchase_receipt_by_name
		create_gl_custom_purchase_receipt_by_name(self,"on_submit")

def striphtml(data):
	if data:
	    p = re.compile(r'<.*?>')
	    return p.sub('', data)
	else:
		return data

@frappe.whitelist()
def check_uom(self,method):
	for row in self.items:
		if row.uom == row.stock_uom:
			row.conversion_factor = 1
			row.received_stock_qty = row.received_qty * row.conversion_factor
			row.stock_qty = row.qty * row.conversion_factor

@frappe.whitelist()
def submitted_rate(self,method):
	for row in self.items:
		row.submitted_rate = row.rate


@frappe.whitelist()
def cek_je(self,method):
	if self.is_return == 1:
		get_je = frappe.db.sql(""" Select name FROM `tabJournal Entry` WHERE from_return_prec = "{}" AND docstatus < 2 and workflow_state != "Rejected" """.format(self.name))
		for row in get_je:
			frappe.throw("PREC can't be cancelled. There is JE {}".format(row[0]))

@frappe.whitelist()
def cek_stock_re(self,method):
	if self.doctype == "Purchase Receipt":
		frappe.db.sql(""" UPDATE `tabSingles` SET value = "" WHERE doctype = "Stock Recount Tools" AND `field` = "purchase_receipt" """)
	if self.doctype == "Stock Entry":
		frappe.db.sql(""" UPDATE `tabSingles` SET value = "" WHERE doctype = "Stock Recount Tools" AND `field` = "stock_entry" """)
		
@frappe.whitelist()
def patch_purchase_receipt():
	list_pr = frappe.db.sql("""
		SELECT name FROM `tabPurchase Receipt` WHERE name in (
			"PRI-HO-1-23-07-00505"
		) """)
	for row in list_pr:
		repair_gl_entry("Purchase Receipt",row[0])
		print(row[0])
		frappe.db.commit()
	
	from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import debug_repost
	debug_repost()

@frappe.whitelist()
def repair_gl_entry_untuk_pr(doctype,docname):
	PurchaseReceipt.get_gl_entries = custom_get_gl_entries

	# docu = frappe.get_doc(doctype, docname)	
	# frappe.flags.repost_gl = True
	# delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(docname))
	# docu.make_gl_entries()

	docu = frappe.get_doc(doctype, docname)	
	
	docu.set_landed_cost_voucher_amount()
	docu.update_valuation_rate()

	for item in docu.get("items"):
		item.db_update()

	delete_sl = frappe.db.sql(""" DELETE FROM `tabStock Ledger Entry` WHERE voucher_no = "{}" """.format(docname))
	delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(docname))
	frappe.flags.repost_gl == True
	frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 1 WHERE `field` = "allow_negative_stock" """)
	docu.update_stock_ledger()
	docu.make_gl_entries()
	docu.repost_future_sle_and_gle()
	frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 0 WHERE `field` = "allow_negative_stock" """)
	from addons.custom_standard.view_ledger_create import create_gl_custom_purchase_receipt_by_name
	create_gl_custom_purchase_receipt_by_name(docname,"on_submit")

@frappe.whitelist()
def repair_gl_entry(doctype,docname):
	PurchaseReceipt.get_gl_entries = custom_get_gl_entries

	# docu = frappe.get_doc(doctype, docname)	
	# frappe.flags.repost_gl = True
	# delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(docname))
	# docu.make_gl_entries()

	docu = frappe.get_doc(doctype, docname)	
	
	docu.set_landed_cost_voucher_amount()
	docu.update_valuation_rate()

	for item in docu.get("items"):
		item.db_update()

	delete_sl = frappe.db.sql(""" DELETE FROM `tabStock Ledger Entry` WHERE voucher_no = "{}" """.format(docname))
	delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(docname))
	frappe.flags.repost_gl == True
	frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 1 WHERE `field` = "allow_negative_stock" """)
	docu.update_stock_ledger()
	docu.make_gl_entries()
	docu.repost_future_sle_and_gle()
	frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 0 WHERE `field` = "allow_negative_stock" """)
	from addons.custom_standard.view_ledger_create import create_gl_custom_purchase_receipt_by_name
	create_gl_custom_purchase_receipt_by_name(docname,"on_submit")
	
@frappe.whitelist()
def override_get_gl_entries(self,method):
	PurchaseReceipt.get_gl_entries = custom_get_gl_entries

@frappe.whitelist()
def custom_get_gl_entries(self, warehouse_account=None):
	from erpnext.accounts.general_ledger import process_gl_map
	gl_entries = []

	custom_make_item_gl_entries(self, gl_entries, warehouse_account=warehouse_account)

	frappe.throw(str(gl_entries))
	self.make_tax_gl_entries(gl_entries)
	self.get_asset_gl_entry(gl_entries)

	return process_gl_map(gl_entries)

@frappe.whitelist()
def debug_ledger_detail():
	doctype = "Purchase Receipt"
	list_exc = frappe.db.sql(""" SELECT name FROM `tab{0}` WHERE docstatus = 1 and name not IN (select no_voucher FROM `tabLedger Detail` WHERE voucher_type = "{0}") """.format(doctype))
	for row in list_exc:
		self = frappe.get_doc(doctype,row[0])
		print(row[0])
		frappe.db.sql(""" DELETE FROM `tabLedger Detail` WHERE no_voucher = "{}" """.format(self.name))
		make_ledger_detail(self.name)
		frappe.db.commit()

@frappe.whitelist()
def hooks_make_ledger_detail(self,method):
	make_ledger_detail(self.name)

@frappe.whitelist()
def make_ledger_detail(no):
	doctype = "Purchase Receipt"
	self = frappe.get_doc(doctype, no)	
	for item in self.items:
		if frappe.get_doc("Item",item.item_code).is_stock_item == 1:
			expense_account = frappe.get_doc("Warehouse", item.warehouse).account
			cost_center = ""
			create_ledger_detail(self.posting_date,expense_account,flt(item.base_net_amount + item.item_tax_amount, item.precision("base_net_amount")),0,"","","Item Warehouse Account",self.remark,doctype,self.name,item.item_code,item.item_name,item.branch or self.branch,item.cost_center or cost_center,self.tax_or_non_tax)
		
@frappe.whitelist()
def create_ledger_detail(posting_date,account,debit,credit,party_type,party,remarks,doc_remarks,voucher_type,voucher_no,item_code,item_name,branch,cost_center,tax_or_non_tax):
	new_ledger_detail = frappe.new_doc("Ledger Detail")
	new_ledger_detail.posting_date = posting_date
	new_ledger_detail.account = account
	new_ledger_detail.debit = debit
	new_ledger_detail.credit = credit
	new_ledger_detail.party_type = party_type
	new_ledger_detail.party = party
	new_ledger_detail.remarks = remarks
	new_ledger_detail.doc_remarks = doc_remarks
	new_ledger_detail.voucher_type = voucher_type
	new_ledger_detail.no_voucher = voucher_no
	new_ledger_detail.item_code = item_code
	new_ledger_detail.item_name = item_name
	new_ledger_detail.branch = branch
	new_ledger_detail.cost_center = cost_center
	new_ledger_detail.tax_or_non_tax = tax_or_non_tax
	new_ledger_detail.save()


def custom_make_item_gl_entries(self, gl_entries, warehouse_account=None):
	stock_rbnb = self.get_company_default("stock_received_but_not_billed")
	landed_cost_entries = get_item_account_wise_additional_cost(self.name)

	expenses_included_in_valuation = self.get_company_default("expenses_included_in_valuation")
	auto_accounting_for_non_stock_items = cint(frappe.db.get_value('Company', self.company, 'enable_perpetual_inventory_for_non_stock_items'))

	warehouse_with_no_account = []
	stock_items = self.get_stock_items()

	for d in self.get("items"):
		if d.item_code in stock_items and flt(d.valuation_rate) and flt(d.qty):
			if warehouse_account.get(d.warehouse):
				stock_value_diff = frappe.db.get_value("Stock Ledger Entry",
					{"voucher_type": "Purchase Receipt", "voucher_no": self.name,
					"voucher_detail_no": d.name, "warehouse": d.warehouse}, "stock_value_difference")

				if not stock_value_diff:
					continue

				warehouse_account_name = warehouse_account[d.warehouse]["account"]
				warehouse_account_currency = warehouse_account[d.warehouse]["account_currency"]
				supplier_warehouse_account = warehouse_account.get(self.supplier_warehouse, {}).get("account")
				supplier_warehouse_account_currency = warehouse_account.get(self.supplier_warehouse, {}).get("account_currency")
				remarks = self.get("remarks") or _("Accounting Entry for Stock")

				# If PR is sub-contracted and fg item rate is zero
				# in that case if account for source and target warehouse are same,
				# then GL entries should not be posted
				if flt(stock_value_diff) == flt(d.rm_supp_cost) \
					and warehouse_account.get(self.supplier_warehouse) \
					and warehouse_account_name == supplier_warehouse_account:
						continue

				self.add_gl_entry(
					gl_entries=gl_entries,
					account=warehouse_account_name,
					cost_center=d.cost_center,
					debit=stock_value_diff,
					credit=0.0,
					remarks=remarks,
					against_account=stock_rbnb,
					account_currency=warehouse_account_currency,
					item=d)

				# GL Entry for from warehouse or Stock Received but not billed
				# Intentionally passed negative debit amount to avoid incorrect GL Entry validation
				credit_currency = get_account_currency(warehouse_account[d.from_warehouse]['account']) \
					if d.from_warehouse else get_account_currency(stock_rbnb)

				credit_amount = flt(d.base_net_amount, d.precision("base_net_amount")) \
					if credit_currency == self.company_currency else flt(d.net_amount, d.precision("net_amount"))
				if credit_amount:
					account = warehouse_account[d.from_warehouse]['account'] \
							if d.from_warehouse else stock_rbnb

					self.add_gl_entry(
						gl_entries=gl_entries,
						account=account,
						cost_center=d.cost_center,
						debit=-1 * flt(d.base_net_amount, d.precision("base_net_amount")),
						credit=0.0,
						remarks=remarks,
						against_account=warehouse_account_name,
						debit_in_account_currency=-1 * credit_amount,
						account_currency=credit_currency,
						item=d)

				# Amount added through landed-cos-voucher

				if d.landed_cost_voucher_amount and landed_cost_entries:
					for account, amount in iteritems(landed_cost_entries[(d.item_code, d.name)]):
						account_currency = get_account_currency(account)
						credit_amount = (flt(amount["base_amount"]) if (amount["base_amount"] or
							account_currency!=self.company_currency) else flt(amount["amount"]))

						self.add_gl_entry(
							gl_entries=gl_entries,
							account=account,
							cost_center=d.cost_center,
							debit=0.0,
							credit=credit_amount,
							remarks=remarks,
							against_account=warehouse_account_name,
							credit_in_account_currency=flt(amount["amount"]),
							account_currency=account_currency,
							project=d.project,
							item=d)

				elif self.is_return == 1:
					doc_item = frappe.get_doc("Purchase Receipt Item",d.purchase_receipt_item)
					lcv_amount = doc_item.landed_cost_voucher_amount
					if lcv_amount > 0:
						lcv_untuk_return = lcv_amount / doc_item.qty * d.qty
						account = ""
						coa = frappe.db.sql(""" SELECT value FROM `tabSingles` WHERE field = "lcv_return_account" AND value IS NOT NULL and value != "" """)
						if len(coa) < 1:
							frappe.throw("Please check LCV Return field in Buying Settings, as its needed for creating journal for PINV Return.")
						else:
							account = coa[0][0]
						remarks = "Return LCV"

						account_currency = get_account_currency(account)

						# self.add_gl_entry(
						# 	gl_entries=gl_entries,
						# 	account=account,
						# 	cost_center=d.cost_center,
						# 	debit=0.0,
						# 	credit=lcv_untuk_return,
						# 	remarks=remarks,
						# 	against_account=warehouse_account_name,
						# 	credit_in_account_currency=flt(lcv_untuk_return),
						# 	account_currency=account_currency,
						# 	project=d.project,
						# 	item=d)

						# self.add_gl_entry(
						# 	gl_entries=gl_entries,
						# 	account=warehouse_account_name,
						# 	cost_center=d.cost_center,
						# 	credit=0.0,
						# 	debit=lcv_untuk_return,
						# 	remarks=remarks,
						# 	against_account=account,
						# 	debit_in_account_currency=flt(lcv_untuk_return),
						# 	account_currency=account_currency,
						# 	project=d.project,
						# 	item=d)


				# sub-contracting warehouse
				if flt(d.rm_supp_cost) and warehouse_account.get(self.supplier_warehouse):
					self.add_gl_entry(
						gl_entries=gl_entries,
						account=supplier_warehouse_account,
						cost_center=d.cost_center,
						debit=0.0,
						credit=flt(d.rm_supp_cost),
						remarks=remarks,
						against_account=warehouse_account_name,
						account_currency=supplier_warehouse_account_currency,
						item=d)

				# divisional loss adjustment
				valuation_amount_as_per_doc = flt(d.base_net_amount, d.precision("base_net_amount")) + \
					flt(d.landed_cost_voucher_amount) + flt(d.rm_supp_cost) + flt(d.item_tax_amount)

				divisional_loss = flt(valuation_amount_as_per_doc - stock_value_diff,
					d.precision("base_net_amount"))

				if divisional_loss:
					if self.is_return or flt(d.item_tax_amount):
						loss_account = expenses_included_in_valuation
						coa = frappe.db.sql(""" SELECT value FROM `tabSingles` WHERE field = "lcv_return_account" AND value IS NOT NULL and value != "" """)
						if len(coa) < 1:
							frappe.throw("Please check LCV Return field in Buying Settings, as its needed for creating journal for PINV Return.")
						else:
							loss_account = coa[0][0]
						remarks = "Return LCV"
					else:
						loss_account = self.get_company_default("round_off_account", ignore_validation=True) or stock_rbnb

					cost_center = d.cost_center or frappe.get_cached_value("Company", self.company, "cost_center")

					self.add_gl_entry(
						gl_entries=gl_entries,
						account=loss_account,
						cost_center=cost_center,
						debit=divisional_loss,
						credit=0.0,
						remarks=remarks,
						against_account=warehouse_account_name,
						account_currency=credit_currency,
						project=d.project,
						item=d)

			elif d.warehouse not in warehouse_with_no_account or \
				d.rejected_warehouse not in warehouse_with_no_account:
					warehouse_with_no_account.append(d.warehouse)
		elif d.item_code not in stock_items and not d.is_fixed_asset and flt(d.qty) and auto_accounting_for_non_stock_items:
			service_received_but_not_billed_account = self.get_company_default("service_received_but_not_billed")
			credit_currency = get_account_currency(service_received_but_not_billed_account)
			debit_currency = get_account_currency(d.expense_account)
			remarks = self.get("remarks") or _("Accounting Entry for Service")

			self.add_gl_entry(
				gl_entries=gl_entries,
				account=service_received_but_not_billed_account,
				cost_center=d.cost_center,
				debit=0.0,
				credit=d.amount,
				remarks=remarks,
				against_account=d.expense_account,
				account_currency=credit_currency,
				project=d.project,
				voucher_detail_no=d.name, item=d)

			self.add_gl_entry(
				gl_entries=gl_entries,
				account=d.expense_account,
				cost_center=d.cost_center,
				debit=d.amount,
				credit=0.0,
				remarks=remarks,
				against_account=service_received_but_not_billed_account,
				account_currency = debit_currency,
				project=d.project,
				voucher_detail_no=d.name,
				item=d)

	if warehouse_with_no_account:
		frappe.msgprint(_("No accounting entries for the following warehouses") + ": \n" +
			"\n".join(warehouse_with_no_account))


@frappe.whitelist()
def update_outstanding_qty_po(self,method):
	array_po = []
	for row in self.items:
		if row.purchase_order:
			if row.purchase_order not in array_po:
				array_po.append(row.purchase_order)

	for row in array_po:
		purchase_order = frappe.get_doc("Purchase Order",row)
		check_field = frappe.db.sql(""" SELECT * FROM `tabCustom Field` WHERE name = "Purchase Order-outstanding_qty_po" """)
		if len(check_field) > 0:
			hasil_outstanding = frappe.db.sql(""" 
				SELECT poi.name,(poi.qty) - SUM(IFNULL(pri.qty,0)) as sisa, poi.item_code, pri.name
				FROM `tabPurchase Order Item` poi
				LEFT JOIN `tabPurchase Receipt Item` pri 
				ON pri.`purchase_order_item` = poi.name
				AND pri.docstatus = 1 

				WHERE poi.parent = "{}"
				GROUP BY poi.name """.format(row), as_dict=1)
			sisa = 0
			for baris_out in hasil_outstanding:
				sisa += baris_out.sisa

			purchase_order.outstanding_qty_po = sisa
			purchase_order.db_update()

@frappe.whitelist()
def auto_je_retur(self,method):
	if self.is_return == 1 and self.return_against != "PRI-HO-1-22-09-02303":
		company_doc = frappe.get_doc("Company", self.company)
		branch = self.branch

		coa = frappe.db.sql(""" SELECT value FROM `tabSingles` WHERE field = "coa_return" AND value IS NOT NULL and value != "" """)
		if len(coa) < 1:
			frappe.throw("Please check COA Return field in Buying Settings, as its needed for creating auto JE for PINV Return.")

		else:
			coa_return = coa[0][0]
			prec_asal = frappe.get_doc("Purchase Receipt",self.return_against)
			coa_hutang = get_party_account("Supplier", prec_asal.supplier, prec_asal.company)

			new_je = frappe.new_doc("Journal Entry")
			new_je.from_return_prec = self.name
			new_je.posting_date = self.posting_date
			if prec_asal.currency != "IDR":
				new_je.multi_currency = 1

			total = 0

			baris_baru = {
				"account": coa_hutang,
				"party_type": "Supplier",
				"party" : prec_asal.supplier,
				"exchange_rate": prec_asal.conversion_rate,
				"account_currency" : prec_asal.currency,
				"branch" : branch,
				"debit_in_account_currency": self.grand_total * -1,
				"debit": self.grand_total * -1 * prec_asal.conversion_rate,
				
				"is_advance" : "Yes",
				"cost_center": company_doc.cost_center
			}
			total += self.grand_total * -1
			new_je.append("accounts", baris_baru)

			if self.taxes:
				for row in self.taxes:
					if row.rate:
						baris_baru = {
							"account": row.account_head,
							"branch" : branch,
							"credit_in_account_currency": row.tax_amount_after_discount_amount * -1,
							"credit": row.tax_amount_after_discount_amount * -1 * prec_asal.conversion_rate,
							"cost_center": company_doc.cost_center
						}
						new_je.append("accounts", baris_baru)
						total += row.tax_amount_after_discount_amount

			baris_baru = {
				"account": coa_return,
				"branch" : branch,
				"credit_in_account_currency": total,
				"credit": total * prec_asal.conversion_rate,
				"cost_center": company_doc.cost_center
			}

			new_je.append("accounts", baris_baru)

			new_je.voucher_type = "Debit Note - Pembelian"
			new_je.tax_or_non_tax = self.tax_or_non_tax
			new_je.naming_series = "DN-GIAS-{{singkatan}}-1-.YY.-.MM.-.#####"
			new_je.cheque_no = "-"
			new_je.cheque_date = self.posting_date
			new_je.flags.ignore_permissions = True
			new_je.save()
			# new_je.submit()

			self.return_journal_entry = new_je.name


@frappe.whitelist()
def update_all_outstanding_qty_po():

	list_po = frappe.db.sql(""" SELECT name FROM `tabPurchase Order` """)
	for po in list_po:
		purchase_order = frappe.get_doc("Purchase Order",po[0])
		check_field = frappe.db.sql(""" SELECT * FROM `tabCustom Field` WHERE name = "Purchase Order-outstanding_qty_po" """)
		if len(check_field) > 0:
			hasil_outstanding = frappe.db.sql(""" 
				SELECT poi.name,(poi.qty) - SUM(IFNULL(pri.qty,0)) as sisa, poi.item_code, pri.name
				FROM `tabPurchase Order Item` poi
				LEFT JOIN `tabPurchase Receipt Item` pri 
				ON pri.`purchase_order_item` = poi.name
				AND pri.docstatus = 1 

				WHERE poi.parent = "{}"
				GROUP BY poi.name """.format(po[0]), as_dict=1)
			sisa = 0
			for baris_out in hasil_outstanding:
				sisa += baris_out.sisa

			purchase_order.outstanding_qty_po = sisa
			purchase_order.db_update()

@frappe.whitelist()
def make_stock_entry(source_name, target_doc=None):
	doc = get_mapped_doc("Purchase Receipt", source_name, {
		"Purchase Receipt": {
			"doctype": "Stock Entry",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Purchase Receipt Item": {
			"doctype": "Stock Entry Detail",
			"field_map": {
				"stock_qty": "transfer_qty",
				"batch_no": "batch_no",
				"warehouse":"s_warehouse",
				"material_request":"material_request",
				"material_request_item":"material_request_item",
				"name":"pr_detail"
			},
		}
	}, target_doc)
	doc.set_posting_time = 1
	# doc.stock_entry_type = "Material Transfer"

	prec = frappe.get_doc("Purchase Receipt", source_name)
	# doc.from_warehouse = prec.set_warehouse
	# for row in doc.items:
	# 	row.s_warehouse = prec.set_warehouse

	return doc


@frappe.whitelist()
def custom_autoname_pr(doc,method):

	company_doc = frappe.get_doc("Company", doc.company)
	list_company_gias_doc = frappe.get_doc("List Company GIAS",company_doc.nama_cabang)
	singkatan = list_company_gias_doc.singkatan_cabang
	
	if doc.is_return == 1:
		initial_supplier = ""
		if doc.supplier:
			doc_supp = frappe.get_doc("Supplier", doc.supplier)
			if not doc_supp.supplier_short_code:
				frappe.throw("Please complete supplier short code in supplier {} as its needed for naming series.".format(doc.supplier))
			else:
				initial_supplier = doc_supp.supplier_short_code
			
		doc.naming_series = """PRT-{{initial_supplier}}-INV-{tax}-.YY.-.MM.-.#####""".replace("{{initial_supplier}}",initial_supplier)
	else:
		if doc.type_pembelian == "Inventory":
			doc.naming_series = """PRI-{{singkatan}}-{tax}-.YY.-.MM.-.#####""".replace("{{singkatan}}",singkatan)
		else:
			doc.naming_series = """PRN-{{singkatan}}-{tax}-.YY.-.MM.-.#####""".replace("{{singkatan}}",singkatan)


	month = frappe.utils.formatdate(frappe.utils.getdate(doc.posting_date),"MM")
	year = frappe.utils.formatdate(frappe.utils.getdate(doc.posting_date),"YY")

	if doc.tax_or_non_tax == "Tax":
		tax = 1
	else:
		tax = 2
	doc.name = make_autoname(doc.naming_series.replace("-{tax}-","-{}-".format(tax)).replace(".YY.",year).replace(".MM.",month), doc=doc)
