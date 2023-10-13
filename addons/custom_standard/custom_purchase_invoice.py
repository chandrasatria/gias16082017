
from __future__ import unicode_literals
import frappe, erpnext
from frappe.utils import cint, cstr, formatdate, flt, getdate, nowdate, get_link_to_form
from frappe import _, throw
import frappe.defaults

from erpnext.assets.doctype.asset_category.asset_category import get_asset_category_account
from erpnext.controllers.buying_controller import BuyingController
from erpnext.accounts.party import get_party_account, get_due_date
from erpnext.accounts.utils import get_account_currency, get_fiscal_year
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import update_billed_amount_based_on_po
from erpnext.stock import get_warehouse_account_map
from erpnext.accounts.general_ledger import make_gl_entries, merge_similar_entries, make_reverse_gl_entries
from erpnext.accounts.doctype.gl_entry.gl_entry import update_outstanding_amt
from erpnext.buying.utils import check_on_hold_or_closed_status
from erpnext.accounts.general_ledger import get_round_off_account_and_cost_center
from erpnext.assets.doctype.asset.asset import get_asset_account, is_cwip_accounting_enabled
from frappe.model.mapper import get_mapped_doc
from six import iteritems
from erpnext.accounts.doctype.sales_invoice.sales_invoice import validate_inter_company_party, update_linked_doc,\
	unlink_inter_company_doc
from erpnext.accounts.doctype.tax_withholding_category.tax_withholding_category import get_party_tax_withholding_details
from erpnext.accounts.deferred_revenue import validate_service_stop_date
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import get_item_account_wise_additional_cost

from erpnext.setup.utils import get_exchange_rate

from frappe.model.naming import make_autoname, revert_series_if_last
from frappe.model.document import Document
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice

from erpnext.accounts.general_ledger import (
	get_round_off_account_and_cost_center,
	make_gl_entries,
	make_reverse_gl_entries,
	merge_similar_entries,
)
from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
	check_if_return_invoice_linked_with_payment_entry,
	get_total_in_party_account_currency,
	is_overdue,
	unlink_inter_company_doc,
	update_linked_doc,
	validate_inter_company_party,
)
def get_outstanding_amount(against_voucher_type, against_voucher, account, party, party_type):
	bal = frappe.utils.flt(frappe.db.sql("""
		select sum(debit_in_account_currency) - sum(credit_in_account_currency)
		from `tabGL Entry`
		where against_voucher_type=%s and against_voucher=%s
		and account = %s and party = %s and party_type = %s""",
		(against_voucher_type, against_voucher, account, party, party_type))[0][0] or 0.0)

	if against_voucher_type == 'Purchase Invoice':
		bal = bal * -1

	return bal
	
@frappe.whitelist()
def onload_purchase_invoice(soi,method):
	if soi.docstatus == 1:
		soi.outstanding_amount = get_outstanding_amount(soi.doctype, soi.name, soi.credit_to, soi.supplier, "Supplier")
		outstanding_amount = soi.outstanding_amount 

		status = None
		total = get_total_in_party_account_currency(soi)
		if not status:
			if soi.docstatus == 2:
				status = "Cancelled"
			elif soi.docstatus == 1:
				if soi.is_internal_transfer():
					soi.status = 'Internal Transfer'
				elif is_overdue(soi, total):
					soi.status = "Overdue"
				elif 0 < outstanding_amount < total:
					soi.status = "Partly Paid"
				elif outstanding_amount > 0 and getdate(soi.due_date) >= getdate():
					soi.status = "Unpaid"
				#Check if outstanding amount is 0 due to debit note issued against invoice
				elif outstanding_amount <= 0 and soi.is_return == 0 and frappe.db.get_value('Purchase Invoice', {'is_return': 1, 'return_against': soi.name, 'docstatus': 1}):
					soi.status = "Debit Note Issued"
				elif soi.is_return == 1:
					soi.status = "Return"
				elif outstanding_amount<=0:
					soi.status = "Paid"
				else:
					soi.status = "Submitted"
			else:
				soi.status = "Draft"
		soi.db_update()
	# frappe.db.commit()

@frappe.whitelist()
def get_dashboard_data(data):
	return {
		'fieldname': 'purchase_invoice',
		'non_standard_fieldnames': {
			'Journal Entry': 'reference_name',
			'Payment Entry': 'reference_name',
			'Payment Request': 'reference_name',
			'Landed Cost Voucher': 'receipt_document',
			'Purchase Invoice': 'return_against',
			'Auto Repeat': 'reference_document',
			'Cash Request': 'document'
		},
		'internal_links': {
			'Purchase Order': ['items', 'purchase_order'],
			'Purchase Receipt': ['items', 'purchase_receipt'],
		},
		'transactions': [
			{
				'label': _('Payment'),
				'items': ['Payment Entry', 'Payment Request', 'Journal Entry', 'Cash Request']
			},
			{
				'label': _('Reference'),
				'items': ['Purchase Order', 'Purchase Receipt', 'Asset', 'Landed Cost Voucher']
			},
			{
				'label': _('Returns'),
				'items': ['Purchase Invoice']
			},
			{
				'label': _('Subscription'),
				'items': ['Auto Repeat']
			},
		]
	}

@frappe.whitelist()
def patch_invoice():
	list_sinv = frappe.db.sql(""" 
		SELECT "PI-1-23-08-01529"
	""")
	

	for row in list_sinv:
		repair_gl_entry("Purchase Invoice", row[0])
		print(row[0])
		frappe.db.commit()

@frappe.whitelist()
def debug_get_stock_received_but_not_billed(pr_name):
	self = frappe.get_doc("Purchase Invoice", pr_name)
	for row in self.items:
		if row.purchase_receipt:
			if not row.asset_category:
				item_doc = frappe.get_doc("Item",row.item_code)
				if item_doc.is_stock_item == 1: 
					row.expense_account = self.get_company_default("stock_received_but_not_billed")
				else:
					row.expense_account = item_doc.item_defaults[0].expense_account

				row.db_update()

@frappe.whitelist()
def get_stock_received_but_not_billed(self,method):
	if self.is_new():
		if self.supplier:
			sup_doc = frappe.get_doc("Supplier", self.supplier)
			if sup_doc.accounts:
				self.credit_to = sup_doc.accounts[0].account

	for row in self.items:
		if row.purchase_receipt:
			if not row.asset_category:
				item_doc = frappe.get_doc("Item",row.item_code)
				if item_doc.is_stock_item == 1: 
					row.expense_account = self.get_company_default("stock_received_but_not_billed")
				else:
					row.expense_account = item_doc.item_defaults[0].expense_account

@frappe.whitelist()
def get_auto_account_retur(self,method):
	if self.is_return:
		if frappe.get_doc("Company", self.company).default_return_expense_account:
			for row in self.items:
				row.expense_account = frappe.get_doc("Company", self.company).default_return_expense_account
		else:
			frappe.throw("Please Set Default Return Expense Account in the Company {}".format(self.company))

@frappe.whitelist()
def validate_asset_account(self,method):
	company_doc = frappe.get_doc("Company", "GIAS")
	for row_item in self.items:
		doc_item = frappe.get_doc("Item", row_item.item_code)
		if row_item.asset_category:
			asset_cat_dog = frappe.get_doc("Asset Category", row_item.asset_category)
			if asset_cat_dog.accounts:
				row_item.expense_account = asset_cat_dog.accounts[0].fixed_asset_account

		# elif doc_item.is_stock_item == 0:
		# 	if doc_item.get("item_defaults"):
		# 		if doc_item.get("item_defaults")[0].get("expense_account"):
		# 			row_item.expense_account = doc_item.get("item_defaults")[0].get("expense_account")


@frappe.whitelist()
def validate_asset_account_debug():
	list_invoice = frappe.db.sql(""" SELECT
		NAME, expense_account, asset_category,parent
		FROM `tabPurchase Invoice Item`
		WHERE asset_category IS NOT NULL
		AND expense_account LIKE "%BARANG BELUM%" GROUP BY parent """)

	for row in list_invoice:
		doc = frappe.get_doc("Purchase Invoice", row[3])
		print(row[3])
		for row_item in doc.items:
			if row_item.asset_category:
				asset_cat_dog = frappe.get_doc("Asset Category", row_item.asset_category)
				if asset_cat_dog.accounts:
					row_item.expense_account = asset_cat_dog.accounts[0].fixed_asset_account
					row_item.db_update()

		repair_gl_entry(doc.doctype,doc.name)		


@frappe.whitelist()
def validate_cancel(self,method):
	company_doc = frappe.get_doc("Company", "GIAS")
	if company_doc.server != "Cabang":
		find = frappe.db.sql("""select c.parent from `tabCash Request Table` c left join `tabCash Request` p on p.name=c.parent where c.docstatus!=2 and c.document="{}" and p.workflow_state!="Rejected" """.format(self.name),as_list=1)
		if find and len(find)>0:
			frappe.throw("Purchase Invoice tidak boleh di cancel karena ada cash request yang suda di buat terhadap purchase invoice ini")

@frappe.whitelist()
def gen_cr(name,supplier,amount,grand_total,remarks,taxorno,branch,cost_center,terms=None):
# def gen_cr(data):	
	# frappe.msgprint("{},{}".format(str(name),str(supplier)))
	tax = frappe.db.get_list('Purchase Taxes and Charges',filters={'parent': name},fields=['*'])
	# suppliertax = frappe.db.get_doc('Suppler',filters={'name': supplier},fields=['tax_id'])
	# frappe.msgprint(str(suppliertax))
	target_doc = frappe.new_doc("Cash Request")
	target_doc.supplier = supplier
	target_doc.destination_account = frappe.get_doc("Supplier",supplier).destination_account
	target_doc.memo = terms
	target_doc.tax_or_non_tax = taxorno
	outstanding = frappe.db.sql("""select IFNULL(amount,0) from `tabCash Request Table` where document="{}" and docstatus=1 """.format(name))
	total_get=0
	for x in outstanding:
		total_get+=flt(x[0])
	if flt(amount)-total_get <= 0:
		frappe.throw("Invoice Telah Sepenuhnya di buat Cash Request")
	row = target_doc.append('list_invoice', {})
	row.document = name
	row.desc = supplier
	row.amount = flt(amount)-total_get
	row.grand_total = grand_total
	row.user_remarks = remarks
	row.branch = branch
	row.cost_center = cost_center
	# rowt = target_doc.append('list_tax_and_charges', {})
	# for i in tax:
	# 	rowt.account = i['account_head']
	# 	rowt.type = i['charge_type']
	# 	rowt.rate = i['rate']
	# 	rowt.amount = i['tax_amount']
	return target_doc.as_dict()

@frappe.whitelist()
def get_exchange_rate_from_supplier():
	print(get_exchange_rate("JPY","IDR",transaction_date = "2021-09-09"))

@frappe.whitelist()
def apply_cost_center(self,method):
	if not self.cost_center:
		company = frappe.get_doc("Company", self.company)
		self.cost_center = company.cost_center

@frappe.whitelist()
def auto_je_retur(self,method):
	if self.is_return == 1:
		company_doc = frappe.get_doc("Company", self.company)
		branch = self.branch

		coa = frappe.db.sql(""" SELECT value FROM `tabSingles` WHERE field = "coa_return" AND value IS NOT NULL and value != "" """)
		if len(coa) < 1:
			frappe.throw("Please check COA Return field in Buying Settings, as its needed for creating auto JE for PINV Return.")

		else:
			coa_return = coa[0][0]
			pinv_asal = frappe.get_doc("Purchase Invoice",self.return_against)
			coa_hutang = pinv_asal.credit_to

			new_je = frappe.new_doc("Journal Entry")
			new_je.dari_purchase_invoice = self.name
			new_je.posting_date = self.posting_date
			if pinv_asal.currency != "IDR":
				new_je.multi_currency = 1
			baris_baru = {
				"account": coa_hutang,
				"party_type": "Supplier",
				"party" : pinv_asal.supplier,
				"exchange_rate": pinv_asal.conversion_rate,
				"account_currency" : pinv_asal.currency,
				"branch" : branch,
				"credit_in_account_currency": self.grand_total * -1,
				"credit": self.grand_total * -1 * pinv_asal.conversion_rate,
				"reference_type" : "Purchase Invoice",
				"reference_name" : pinv_asal.name,
				"is_advance" : "Yes",
				"cost_center": company_doc.cost_center
			}
			new_je.append("accounts", baris_baru)

			baris_baru = {
				"account": coa_return,
				"branch" : branch,
				"debit_in_account_currency": self.grand_total * -1,
				"debit": self.grand_total * -1 * pinv_asal.conversion_rate,
				"cost_center": company_doc.cost_center
			}
			new_je.append("accounts", baris_baru)
			new_je.flags.ignore_permissions = True
			new_je.submit()




@frappe.whitelist()
def check_auto_je_retur(self,method):
	coa = frappe.db.sql(""" SELECT value FROM `tabSingles` WHERE field = "coa_return" AND value IS NOT NULL and value != "" """)
	if len(coa) < 1:
		frappe.throw("Please check COA Return field in Buying Settings, as its needed for creating auto JE for PINV Return.")

@frappe.whitelist()
def custom_autoname_pinv(doc,method):

	# pass

	month = frappe.utils.formatdate(frappe.utils.getdate(doc.posting_date),"MM")
	year = frappe.utils.formatdate(frappe.utils.getdate(doc.posting_date),"YY")

	if doc.tax_or_non_tax == "Tax":
		tax = 1
	else:
		tax = 2
	doc.name = make_autoname(doc.naming_series.replace("-{tax}-","-{}-".format(tax)).replace(".YY.",year).replace(".MM.",month))


@frappe.whitelist()
def debug_ledger_detail():
	doctype = "Purchase Invoice"
	list_exc = frappe.db.sql(""" SELECT name FROM `tab{0}` WHERE docstatus = 1 and name not IN (select name FROM `tabLedger Detail` WHERE voucher_type = "{0}") """.format(doctype))
	for row in list_exc:
		self = frappe.get_doc(doctype,row[0])
		frappe.db.sql(""" DELETE FROM `tabLedger Detail` WHERE no_voucher = "{}" """.format(self.name))
		make_ledger_detail(self.name)
		print(row[0])

@frappe.whitelist()
def hooks_make_ledger_detail(self,method):
	make_ledger_detail(self.name)

@frappe.whitelist()
def make_ledger_detail(no):
	doctype = "Purchase Invoice"
	self = frappe.get_doc(doctype, no)	
	for item in self.items:
		expense_account = item.expense_account
		if item.purchase_receipt and frappe.get_doc("Item",item.item_code).is_stock_item:
			self.stock_received_but_not_billed = self.get_company_default("stock_received_but_not_billed")
			expense_account = self.stock_received_but_not_billed

		create_ledger_detail(self.posting_date,expense_account,flt(item.base_net_amount + item.item_tax_amount, item.precision("base_net_amount")),0,"","","Item Warehouse Account",self.remark,doctype,self.name,item.item_code,item.item_name,item.branch or self.branch,item.cost_center or self.cost_center,self.tax_or_non_tax)
		
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
	frappe.db.commit()

@frappe.whitelist()
def override_get_gl_entries(self,method):
	PurchaseInvoice.get_gl_entries = custom_get_gl_entries

@frappe.whitelist()
def repair_asset_entry():
	pinv_list = frappe.db.sql(""" SELECT pin.name
		FROM `tabPurchase Invoice` pin
		JOIN `tabPurchase Invoice Item` pii ON pii.parent = pin.name
		WHERE
		pin.name IN ("PI-1-23-03-01006")
		GROUP BY pin.name
	 """)

	for row in pinv_list:
		pinv_doc = frappe.get_doc("Purchase Invoice",row[0])
		repair_gl_entry(pinv_doc.doctype,pinv_doc.name)		


@frappe.whitelist()
def repair_gl_entry(doctype,docname):
	PurchaseInvoice.get_gl_entries = custom_get_gl_entries
	docu = frappe.get_doc(doctype, docname)	
	for row_item in docu.items:
		doc_item = frappe.get_doc("Item", row_item.item_code)
		if row_item.asset_category:
			asset_cat_dog = frappe.get_doc("Asset Category", row_item.asset_category)
			if asset_cat_dog.accounts:
				row_item.expense_account = asset_cat_dog.accounts[0].fixed_asset_account
				row_item.db_update()

		elif doc_item.is_stock_item == 0:
			row_item.expense_account = "2123 - BARANG BELUM TERTAGIH - G"

	frappe.flags.repost_gl = True
	delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(docname))
	# delete_gl = frappe.db.sql(""" DELETE FROM `tabStock Ledger Entry` WHERE voucher_no = "{}" """.format(docname))

	docu.make_gl_entries()
	# docu.repost_future_sle_and_gle()
	from addons.custom_standard.view_ledger_create import create_gl_custom_purchase_invoice_by_name
	create_gl_custom_purchase_invoice_by_name(docu,"on_submit")


@frappe.whitelist()	
def custom_get_gl_entries(self, warehouse_account=None):
	self.auto_accounting_for_stock = erpnext.is_perpetual_inventory_enabled(self.company)
	if self.auto_accounting_for_stock:
		self.stock_received_but_not_billed = self.get_company_default("stock_received_but_not_billed")
		self.expenses_included_in_valuation = self.get_company_default("expenses_included_in_valuation")
	else:
		self.stock_received_but_not_billed = None
		self.expenses_included_in_valuation = None

	self.negative_expense_to_be_booked = 0.0
	gl_entries = []

	# self.make_supplier_gl_entry(gl_entries)
	# self.make_item_gl_entries(gl_entries)
	custom_make_supplier_gl_entry(self, gl_entries)

	
	custom_make_item_gl_entries(self,gl_entries)

	self.make_discount_gl_entries(gl_entries)

	if self.check_asset_cwip_enabled():
		self.get_asset_gl_entry(gl_entries)

	self.make_tax_gl_entries(gl_entries)
	self.make_exchange_gain_loss_gl_entries(gl_entries)
	self.make_internal_transfer_gl_entries(gl_entries)


	gl_entries = make_regional_gl_entries(gl_entries, self)

	gl_entries = merge_similar_entries(gl_entries)

	self.make_payment_gl_entries(gl_entries)
	self.make_write_off_gl_entry(gl_entries)
	self.make_gle_for_rounding_adjustment(gl_entries)
	return gl_entries


def custom_make_supplier_gl_entry(self, gl_entries):
	# Checked both rounding_adjustment and rounded_total
	# because rounded_total had value even before introcution of posting GLE based on rounded total
	grand_total = self.rounded_total if (self.rounding_adjustment and self.rounded_total) else self.grand_total

	# for row in self.items:
		# discount_account = ""
		# get_account = frappe.db.sql(""" SELECT value FROM `tabSingles` WHERE field = "prorate_discount_account" AND value IS NOT NULL and value != "" AND doctype = "Buying Settings" """)
		# if len(get_account) > 0:
		# 	discount_account = get_account[0][0]

		# if not discount_account:
		# 	frappe.throw("Please set a Prorate Discount Account in Buying Settings before submitting this document.")
		# else:
		# 	if flt(row.prorate_discount) > 0:
		# 		total_discount = flt(row.prorate_discount) * row.qty
		# 		gl_entries.append(
		# 			self.get_gl_dict({
		# 				"account": discount_account,
		# 				"credit": total_discount,
		# 				"credit_in_account_currency": total_discount,
		# 				"cost_center": self.cost_center,
		# 				"project": self.project
		# 			}, frappe.get_doc("Account",discount_account).account_currency, item=self)
		# 		)

		# 		gl_entries.append(
		# 			self.get_gl_dict({
		# 				"account": row.expense_account,
		# 				"debit": total_discount,
		# 				"debit_in_account_currency": total_discount,
		# 				"cost_center": self.cost_center,
		# 				"project": self.project
		# 			}, frappe.get_doc("Account",row.expense_account).account_currency, item=self)
		# 		)

	if self.discount_2:
		get_account = frappe.db.sql(""" SELECT value FROM `tabSingles` WHERE field = "prorate_discount_account" AND value IS NOT NULL and value != "" AND doctype = "Buying Settings" """)
		if len(get_account) > 0:
			discount_account = get_account[0][0]

		if not discount_account:
			frappe.throw("Please set a Prorate Discount Account in Buying Settings before submitting this document.")
		else:
			if flt(self.discount_2) > 0:
				total_discount = 0
				variable = 100

				for row in self.taxes:
					if row.rate and variable == 100 and row.included_in_print_rate == 1:
						variable += row.rate

				total_discount = self.discount_2 / (variable / 100)
				# gl_entries.append(
				# 	self.get_gl_dict({
				# 		"account": discount_account,
				# 		"credit": total_discount,
				# 		"credit_in_account_currency": total_discount,
				# 		"cost_center": self.cost_center_discount_2,
				# 		"branch": self.branch_discount_2,
				# 		"remarks": self.remark_discount_2,
				# 		"project": self.project
				# 	}, self.party_account_currency, item=self)
				# )
				gl_entries.append(
					self.get_gl_dict({
						"account": discount_account,
						"credit": total_discount,
						"credit_in_account_currency": total_discount,
						"cost_center": self.cost_center,
						"project": self.project
					}, self.party_account_currency, item=self)
				)

	if self.discount_amount:

		variable = 100

		for row in self.taxes:
			if row.rate and variable == 100 and row.included_in_print_rate == 1:
				variable += row.rate

		discount_account = ""
		get_account = frappe.db.sql(""" SELECT value FROM `tabSingles` WHERE field = "global_discount_account" AND value IS NOT NULL and value != "" AND doctype = "Buying Settings" """)
		if len(get_account) > 0:
			discount_account = get_account[0][0]

		if not discount_account:
			frappe.throw("Please set a DP Invoice Account in Buying Settings before submitting this document.")
		else:
			account = frappe.get_doc("Account",discount_account)
			if account.account_type == "Payable":
				gl_entries.append(
					self.get_gl_dict({
						"account": discount_account,
						"due_date": self.due_date,
						"against": self.against_expense_account,
						"credit": self.discount_amount - self.discount_2,
						"credit_in_account_currency": self.discount_amount - self.discount_2,
						"cost_center": self.cost_center,
						"project": self.project,
						"party_type" : "Supplier",
						"party" : self.supplier
					}, self.party_account_currency, item=self)
				)
			else:
				gl_entries.append(
					self.get_gl_dict({
						"account": discount_account,
						"due_date": self.due_date,
						"against": self.against_expense_account,
						"credit": self.discount_amount - self.discount_2,
						"credit_in_account_currency": self.discount_amount - self.discount_2,
						"cost_center": self.cost_center,
						"project": self.project
					}, self.party_account_currency, item=self)
				)

	# for row in self.items:
	# 	discount_account = ""
	# 	get_account = frappe.db.sql(""" SELECT value FROM `tabSingles` WHERE field = "item_discount_account" AND value IS NOT NULL and value != "" AND doctype = "Buying Settings" """)
	# 	if len(get_account) > 0:
	# 		discount_account = get_account[0][0]

	# 	if not discount_account:
	# 		frappe.throw("Please set a Prorate Discount Account in Buying Settings before submitting this document.")
	# 	else:
	# 		if flt(row.discount_amount) > 0:
	# 			total_discount = flt(row.discount_amount) * row.qty
	# 			gl_entries.append(
	# 				self.get_gl_dict({
	# 					"account": discount_account,
	# 					"credit": total_discount,
	# 					"credit_in_account_currency": total_discount,
	# 					"cost_center": self.cost_center,
	# 					"project": self.project
	# 				}, frappe.get_doc("Account",discount_account).account_currency, item=self)
	# 			)

	# 			gl_entries.append(
	# 				self.get_gl_dict({
	# 					"account": row.expense_account,
	# 					"debit": total_discount,
	# 					"debit_in_account_currency": total_discount,
	# 					"cost_center": self.cost_center,
	# 					"project": self.project
	# 				}, frappe.get_doc("Account",row.expense_account).account_currency, item=self)
	# 			)

	# if not discount_account:
	# 	frappe.throw("Please set a DP Invoice Account in Buying Settings before submitting this document.")
	# else:
	# 	gl_entries.append(
	# 		self.get_gl_dict({
	# 			"account": discount_account,
	# 			"due_date": self.due_date,
	# 			"against": self.against_expense_account,
	# 			"credit": self.discount_amount,
	# 			"credit_in_account_currency": self.discount_amount,
	# 			"against_voucher": self.return_against if cint(self.is_return) and self.return_against else self.name,
	# 			"against_voucher_type": self.doctype,
	# 			"project": self.project,
	# 			"cost_center": self.cost_center
	# 		}, frappe.get_doc("Account",discount_account).account_currency, item=self)
	# 	)

	if grand_total and not self.is_internal_transfer():
		# Did not use base_grand_total to book rounding loss gle
		grand_total_in_company_currency = flt(grand_total * self.conversion_rate,
			self.precision("grand_total"))

		gl_entries.append(
			self.get_gl_dict({
				"account": self.credit_to,
				"party_type": "Supplier",
				"party": self.supplier,
				"due_date": self.due_date,
				"against": self.against_expense_account,
				"credit": grand_total_in_company_currency,
				"credit_in_account_currency": grand_total_in_company_currency \
					if self.party_account_currency==self.company_currency else grand_total,
				"against_voucher": self.return_against if cint(self.is_return) and self.return_against else self.name,
				"against_voucher_type": self.doctype,
				"project": self.project,
				"cost_center": self.cost_center
			}, self.party_account_currency, item=self)
		)

		
def custom_make_item_gl_entries(self, gl_entries):
	# item gl entries

	stock_items = self.get_stock_items()
	if self.update_stock and self.auto_accounting_for_stock:
		warehouse_account = get_warehouse_account_map(self.company)

	landed_cost_entries = get_item_account_wise_additional_cost(self.name)

	voucher_wise_stock_value = {}
	if self.update_stock:
		for d in frappe.get_all('Stock Ledger Entry',
			fields = ["voucher_detail_no", "stock_value_difference", "warehouse"], filters={'voucher_no': self.name}):
			voucher_wise_stock_value.setdefault((d.voucher_detail_no, d.warehouse), d.stock_value_difference)

	valuation_tax_accounts = [d.account_head for d in self.get("taxes")
		if d.category in ('Valuation', 'Total and Valuation')
		and flt(d.base_tax_amount_after_discount_amount)]

	if self.discount_amount:
		item = self.items[0]
		expense_account = item.expense_account

		account_currency = get_account_currency(expense_account)
		gl_entries.append(
			self.get_gl_dict({
				"account": expense_account,
				"against": self.supplier,
				"debit": flt(self.discount_amount, item.precision("base_amount")),
				"debit_in_account_currency": flt(self.discount_amount, item.precision("base_amount")),
				"cost_center": item.cost_center,
				"project": item.project or self.project
			}, account_currency, item=item)
		)
	for item in self.get("items"):
		if flt(item.base_net_amount):
			account_currency = get_account_currency(item.expense_account)
			if item.item_code:
				asset_category = frappe.get_cached_value("Item", item.item_code, "asset_category")

			if self.update_stock and self.auto_accounting_for_stock and item.item_code in stock_items:
				# warehouse account
				warehouse_debit_amount = self.make_stock_adjustment_entry(gl_entries,
					item, voucher_wise_stock_value, account_currency)

				if item.from_warehouse:
					gl_entries.append(self.get_gl_dict({
						"account":  warehouse_account[item.warehouse]['account'],
						"against": warehouse_account[item.from_warehouse]["account"],
						"cost_center": item.cost_center,
						"project": item.project or self.project,
						"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
						"debit": warehouse_debit_amount,
					}, warehouse_account[item.warehouse]["account_currency"], item=item))

					# Intentionally passed negative debit amount to avoid incorrect GL Entry validation
					gl_entries.append(self.get_gl_dict({
						"account":  warehouse_account[item.from_warehouse]['account'],
						"against": warehouse_account[item.warehouse]["account"],
						"cost_center": item.cost_center,
						"project": item.project or self.project,
						"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
						"debit": -1 * flt(item.base_net_amount, item.precision("base_net_amount")),
					}, warehouse_account[item.from_warehouse]["account_currency"], item=item))

					# Do not book expense for transfer within same company transfer
					if not self.is_internal_transfer():
						gl_entries.append(
							self.get_gl_dict({
								"account": item.expense_account,
								"against": self.supplier,
								"debit": flt(item.base_net_amount, item.precision("base_net_amount")),
								"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
								"cost_center": item.cost_center,
								"project": item.project
							}, account_currency, item=item)
						)

				else:

					if not self.is_internal_transfer():
						gl_entries.append(
							self.get_gl_dict({
								"account": item.expense_account,
								"against": self.supplier,
								"debit": warehouse_debit_amount,
								"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
								"cost_center": item.cost_center,
								"project": item.project or self.project
							}, account_currency, item=item)
						)

				# Amount added through landed-cost-voucher
				if landed_cost_entries:
					for account, amount in iteritems(landed_cost_entries[(item.item_code, item.name)]):
						gl_entries.append(self.get_gl_dict({
							"account": account,
							"against": item.expense_account,
							"cost_center": item.cost_center,
							"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
							"credit": flt(amount["base_amount"]),
							"credit_in_account_currency": flt(amount["amount"]),
							"project": item.project or self.project
						}, item=item))

				# sub-contracting warehouse
				if flt(item.rm_supp_cost):
					supplier_warehouse_account = warehouse_account[self.supplier_warehouse]["account"]
					if not supplier_warehouse_account:
						frappe.throw(_("Please set account in Warehouse {0}")
							.format(self.supplier_warehouse))
					gl_entries.append(self.get_gl_dict({
						"account": supplier_warehouse_account,
						"against": item.expense_account,
						"cost_center": item.cost_center,
						"project": item.project or self.project,
						"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
						"credit": flt(item.rm_supp_cost)
					}, warehouse_account[self.supplier_warehouse]["account_currency"], item=item))

			elif not item.is_fixed_asset or (item.is_fixed_asset and not is_cwip_accounting_enabled(asset_category)):
				
				expense_account = (item.expense_account
					if (not item.enable_deferred_expense or self.is_return) else item.deferred_expense_account)

				if not item.is_fixed_asset:
					amount = flt(item.base_net_amount, item.precision("base_net_amount"))
				else:
					amount = flt(item.base_net_amount + item.item_tax_amount, item.precision("base_net_amount"))

				auto_accounting_for_non_stock_items = cint(frappe.db.get_value('Company', self.company, 'enable_perpetual_inventory_for_non_stock_items'))

				if auto_accounting_for_non_stock_items:
					
					service_received_but_not_billed_account = self.get_company_default("service_received_but_not_billed")

					if item.purchase_receipt:
						# Post reverse entry for Stock-Received-But-Not-Billed if it is booked in Purchase Receipt
					
						expense_booked_in_pr = frappe.db.get_value('GL Entry', {'is_cancelled': 0,
							'voucher_type': 'Purchase Receipt', 'voucher_no': item.purchase_receipt, 'voucher_detail_no': item.pr_detail,
							'account':service_received_but_not_billed_account}, ['name'])

						if expense_booked_in_pr:
							expense_account = service_received_but_not_billed_account

				if not self.is_internal_transfer():

					gl_entries.append(self.get_gl_dict({
							"account": expense_account,
							"against": self.supplier,
							"debit": amount,
							"cost_center": item.cost_center,
							"project": item.project or self.project
						}, account_currency, item=item))

				# If asset is bought through this document and not linked to PR
				if self.update_stock and item.landed_cost_voucher_amount:
					expenses_included_in_asset_valuation = self.get_company_default("expenses_included_in_asset_valuation")
					# Amount added through landed-cost-voucher
					gl_entries.append(self.get_gl_dict({
						"account": expenses_included_in_asset_valuation,
						"against": expense_account,
						"cost_center": item.cost_center,
						"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
						"credit": flt(item.landed_cost_voucher_amount),
						"project": item.project or self.project
					}, item=item))

					gl_entries.append(self.get_gl_dict({
						"account": expense_account,
						"against": expenses_included_in_asset_valuation,
						"cost_center": item.cost_center,
						"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
						"debit": flt(item.landed_cost_voucher_amount),
						"project": item.project or self.project
					}, item=item))

					# update gross amount of asset bought through this document
					assets = frappe.db.get_all('Asset',
						filters={ 'purchase_invoice': self.name, 'item_code': item.item_code }
					)
					for asset in assets:
						frappe.db.set_value("Asset", asset.name, "gross_purchase_amount", flt(item.valuation_rate))
						frappe.db.set_value("Asset", asset.name, "purchase_receipt_amount", flt(item.valuation_rate))

		if self.auto_accounting_for_stock and self.is_opening == "No" and \
			item.item_code in stock_items and item.item_tax_amount:
				# Post reverse entry for Stock-Received-But-Not-Billed if it is booked in Purchase Receipt
				if item.purchase_receipt and valuation_tax_accounts:
					negative_expense_booked_in_pr = frappe.db.sql("""select name from `tabGL Entry`
						where voucher_type='Purchase Receipt' and voucher_no=%s and account in %s""",
						(item.purchase_receipt, valuation_tax_accounts))

					if not negative_expense_booked_in_pr:
						gl_entries.append(
							self.get_gl_dict({
								"account": self.stock_received_but_not_billed,
								"against": self.supplier,
								"debit": flt(item.item_tax_amount, item.precision("item_tax_amount")),
								"remarks": self.remarks or "Accounting Entry for Stock",
								"cost_center": self.cost_center,
								"project": item.project or self.project
							}, item=item)
						)

						self.negative_expense_to_be_booked += flt(item.item_tax_amount, \
							item.precision("item_tax_amount"))

	if self.discount_amount:
		item = self.items[0]
		expense_account = (item.expense_account)

		variable = 100

		for row in self.taxes:
			if row.rate and variable == 100 and row.included_in_print_rate == 1:
				variable += row.rate

		account_currency = get_account_currency(expense_account)
		gl_entries.append(
			self.get_gl_dict({
				"account": expense_account,
				"against": self.supplier,
				"debit": flt(-1*(self.discount_amount-(self.discount_amount/(variable/100))), item.precision("base_amount")),
				"debit_in_account_currency": flt(-1*(self.discount_amount-(self.discount_amount/(variable/100))), item.precision("base_amount")),
				"cost_center": item.cost_center,
				"project": item.project or self.project
			}, account_currency, item=item)
		)



@erpnext.allow_regional
def make_regional_gl_entries(gl_entries, doc):
	return gl_entries

@frappe.whitelist()
def validate_lcv(doc,method):
	if doc.no_lcv:
		data = frappe.get_value("Landed Cost Voucher",{"name" : doc.no_lcv}, "no_pinv")

		if data and data != "":
			doc_pinv = frappe.get_doc("Purchase Invoice", data)
			if doc_pinv.docstatus == 1:
				frappe.throw("Landed Cost Voucher {} sudah memiliki Tagihan {}".format(doc.no_lcv,data))
@frappe.whitelist()
def get_lcv(doc,method):
	if doc.no_lcv:
		frappe.db.sql("""update `tabLanded Cost Voucher` set no_pinv="{}" where name="{}" """.format(doc.name,doc.no_lcv))
		#doc1 = frappe.get_doc("Landed Cost Voucher",doc.no_lcv)
		#doc1.no_pinv = doc.name
		#doc1.db.update()
		#frappe.db.commit()

@frappe.whitelist()
def get_sq(doc,method):
	for d in doc.items:
		if d.supplier_quotation:
			data = frappe.get_value("Supplier Quotation",{"name" : d.supplier_quotation}, "grand_total")
			if doc.grand_total != data:
				frappe.throw("Harga Berbeda dengan Supplier Quotation !")
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_dp_invoice(doctype, txt, searchfield, start, page_len, filters):
	from erpnext.controllers.queries import get_match_cond

	if not filters: filters = {}
	condition = ""
	return frappe.db.sql("""select name FROM
		`tabPurchase Invoice` WHERE
			dp_or_not = "DP" AND docstatus = 1 and outstanding_amount=0
			AND supplier = %(supplier)s
			AND name not in (SELECT invoice_dp from `tabPurchase Invoice DP` 
			WHERE docstatus = 1  AND invoice_dp IS NOT NULL)
			AND 
			(name LIKE %(txt)s
			{condition}) {match_condition}"""
		.format(condition=condition, key=searchfield,
			match_condition=get_match_cond(doctype)), {
			'company': filters.get("company", ""),
			'txt': '%' + txt + '%',
			'supplier':  filters.get("supplier", "")
		})

@erpnext.allow_regional
def make_regional_gl_entries(gl_entries, doc):
	return gl_entries
