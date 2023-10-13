
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
import frappe.defaults
from frappe.utils import cint, flt, getdate, add_days, cstr, nowdate, get_link_to_form, formatdate
from frappe import _, msgprint, throw
from erpnext.accounts.party import get_party_account, get_due_date, get_party_details
from frappe.model.mapper import get_mapped_doc
from erpnext.controllers.selling_controller import SellingController
from erpnext.accounts.utils import get_account_currency
from erpnext.stock.doctype.delivery_note.delivery_note import update_billed_amount_based_on_so
from erpnext.projects.doctype.timesheet.timesheet import get_projectwise_timesheet_data
from erpnext.assets.doctype.asset.depreciation \
	import get_disposal_account_and_cost_center, get_gl_entries_on_asset_disposal
from erpnext.stock.doctype.batch.batch import set_batch_nos
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos, get_delivery_note_serial_no
from erpnext.setup.doctype.company.company import update_company_current_month_sales
from erpnext.accounts.general_ledger import get_round_off_account_and_cost_center
from erpnext.accounts.doctype.loyalty_program.loyalty_program import \
	get_loyalty_program_details_with_points, get_loyalty_details, validate_loyalty_points
from erpnext.accounts.deferred_revenue import validate_service_stop_date
from erpnext.accounts.doctype.tax_withholding_category.tax_withholding_category import get_party_tax_withholding_details
from frappe.model.utils import get_fetch_values
from frappe.contacts.doctype.address.address import get_address_display
from erpnext.accounts.doctype.tax_withholding_category.tax_withholding_category import get_party_tax_withholding_details

from erpnext.healthcare.utils import manage_invoice_submit_cancel
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

from frappe.model.naming import make_autoname, revert_series_if_last

from six import iteritems
from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
	check_if_return_invoice_linked_with_payment_entry,
	get_total_in_party_account_currency,
	is_overdue,
	unlink_inter_company_doc,
	update_linked_doc,
	validate_inter_company_party,
)

@frappe.whitelist()
def change_dn_date(self,method):
	for row in self.items:
		if row.so_detail:
			# cari dn  
			sql = frappe.db.sql(""" SELECT name, parent from `tabDelivery Note Item` WHERE 
				against_sales_order = "{}" AND docstatus = 1 LIMIT 1
			""".format(row.so_detail))
			if len(sql) > 0:
				row.dn_detail = sql[0][0]
				row.delivery_note = sql[0][1]

		if row.delivery_note:
			dn_doc = frappe.get_doc("Delivery Note", row.delivery_note)
			self.set_posting_time = 1
			self.posting_date = dn_doc.posting_date

		elif row.sales_order:
			so_doc = frappe.get_doc("Sales Order", row.sales_order)
			if so_doc.titipan == 0:
				if not row.delivery_note:
					frappe.throw("""SO {} is required to have Delivery Note. Please check.""".format(row.sales_order))
			else:
				self.set_posting_time = 1
				self.posting_date = so_doc.transaction_date


@frappe.whitelist()
def check_branch(doc,method):
	for row in doc.taxes:
		if doc.branch:
			row.branch = doc.branch


@frappe.whitelist()
def check_dn_date(doc,method):
	for row in doc.items:
		if row.delivery_note:
			dn_doc = frappe.get_doc("Delivery Note", row.delivery_note)
			if getdate(dn_doc.posting_date) > getdate(doc.posting_date):
				frappe.throw("Sales Invoice cannot have {} as posting date as it is set before Delivery Note {} posting date - {}".format(doc.posting_date, dn_doc.name, dn_doc.posting_date))

@frappe.whitelist()
def custom_autoname_sales_invoice(doc,method):
	for row in doc.items:
		if row.so_detail:
			# cari dn  
			sql = frappe.db.sql(""" SELECT name, parent from `tabDelivery Note Item` WHERE 
				against_sales_order = "{}" AND docstatus = 1 LIMIT 1
			""".format(row.so_detail))
			if len(sql) > 0:
				row.dn_detail = sql[0][0]
				row.delivery_note = sql[0][1]

		if row.delivery_note:
			dn_doc = frappe.get_doc("Delivery Note", row.delivery_note)
			doc.set_posting_time = 1
			doc.posting_date = dn_doc.posting_date

		if row.sales_order:
			so_doc = frappe.get_doc("Sales Order", row.sales_order)
			if so_doc.titipan == 0:
				if not row.delivery_note:
					frappe.throw("""SO {} is required to have Delivery Note. Please check.""".format(row.sales_order))

	singkatan = "HO"
	company_doc = frappe.get_doc("Company", doc.company)
	list_company_gias_doc = frappe.get_doc("List Company GIAS",company_doc.nama_cabang)
	singkatan = list_company_gias_doc.singkatan_cabang

	nama = doc.naming_series.replace("{{singkatan}}",singkatan)
	
	month = frappe.utils.formatdate(frappe.utils.getdate(doc.posting_date),"MM")
	year = frappe.utils.formatdate(frappe.utils.getdate(doc.posting_date),"YY")

	if doc.tax_or_non_tax == "Tax":
		tax = 1
	else:
		tax = 2
	doc.name = make_autoname(nama.replace("-{tax}-","-{}-".format(tax)).replace(".YY.",year).replace(".MM.",month), doc=doc)


@frappe.whitelist()
def initiate_pure_calculate():
	list_sinv = frappe.db.sql(""" SELECT name FROM `tabPurchase Invoice` where pure_total_amount = 0 """)
	for baris in list_sinv:
		self = frappe.get_doc("Purchase Invoice", baris[0])
		total = 0
		for row in self.items:
			row.pure_rate = row.net_rate + row.prorate_discount + row.discount_amount
			row.pure_amount = row.net_amount + (row.qty * (row.prorate_discount+row.discount_amount))
			total += row.pure_amount
			row.db_update()
		self.pure_total_amount = total
		self.db_update()

		print(self.name)
@frappe.whitelist()
def pure_calculate(self,method):
	total = 0
	for row in self.items:
		row.pure_rate = row.net_rate + row.prorate_discount + row.discount_amount
		row.pure_amount = row.qty * row.pure_rate
		total += row.pure_amount

	self.pure_total_amount = total

@frappe.whitelist()
def update_asset(self,method):
	for row in self.items:
		if row.asset:
			asset_doc = frappe.get_doc("Asset", row.asset)
			asset_doc.status_movement = "Dispose"
			asset_doc.tanggal_jual = self.posting_date
			asset_doc.db_update()

@frappe.whitelist()
def update_asset_cancel(self,method):
	for row in self.items:
		if row.asset:
			asset_doc = frappe.get_doc("Asset", row.asset)
			asset_doc.status_movement = "Active"
			asset_doc.tanggal_jual = ""
			asset_doc.db_update()

@frappe.whitelist()
def patch_assuming_customer():

	list_invoice = frappe.db.sql(""" SELECT name FROM `tabSales Invoice`
	WHERE tax_or_non_tax = "Tax"
	AND (tax_name IS NULL or alamat_pajak IS NULL or no_ktp is NULL or npwp IS NULL)
	 """)
	for row in list_invoice:
		self = frappe.get_doc("Sales Invoice", row[0])
		if self.customer:
			customer_doc = frappe.get_doc("Customer",self.customer)
			if not self.tax_name:
				self.tax_name = customer_doc.nama_pajak
			if not self.alamat_pajak:	
				self.alamat_pajak = customer_doc.alamat_pajak
			if not self.no_ktp:
				self.no_ktp = customer_doc.no_ktp
			if not self.npwp:
				self.npwp = customer_doc.tax_id
			self.db_update()

		print(row[0])

	frappe.db.commit()



@frappe.whitelist()
def assuming_customer(self,method):
	if self.customer:
		customer_doc = frappe.get_doc("Customer",self.customer)
		if customer_doc.is_cash_customer == 0:
			if not self.tax_name:
				self.tax_name = customer_doc.nama_pajak
			if not self.alamat_pajak:
				self.alamat_pajak = customer_doc.alamat_pajak
			if not self.no_ktp:
				self.no_ktp = customer_doc.no_ktp
			if not self.npwp:
				self.npwp = customer_doc.tax_id
			

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
def check_sales_invoice():
	list_sinv = frappe.db.sql(""" SELECT NAME, outstanding_amount, rounded_total
		FROM `tabSales Invoice`
		WHERE outstanding_amount > rounded_total
		AND is_return = 0  """)
	for row in list_sinv:
		soi = frappe.get_doc("Sales Invoice", row[0])
		if soi.outstanding_amount > soi.grand_total:
			if soi.outstanding_amount == soi.grand_total * 2:
				repair_gl_entry("Sales Invoice", soi.name)

@frappe.whitelist()
def patch_onload_sales_invoice():
	list_sales_invoice = frappe.db.sql(""" SELECT name FROM `tabSales Invoice` WHERE outstanding_amount = 0 and docstatus = 1 
		AND name = "SI-GIAS-SMD-1-22-11-01643" """)
	for row in list_sales_invoice:
		soi = frappe.get_doc("Sales Invoice",row[0])

		harusnya = get_outstanding_amount(soi.doctype, soi.name, soi.debit_to, soi.customer, "Customer")
		print(harusnya)
		print(soi.outstanding_amount)
		if harusnya != soi.outstanding_amount:
			soi.outstanding_amount = harusnya
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
			print(soi.name)
			frappe.db.commit()

@frappe.whitelist()
def onload_sales_invoice(soi,method):
	soi.outstanding_amount = get_outstanding_amount(soi.doctype, soi.name, soi.debit_to, soi.customer, "Customer")
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
def get_auto_account_retur(self,method):
	if self.is_return:
		if frappe.get_doc("Company", self.company).default_return_income_account:
			for row in self.items:
				row.income_account = frappe.get_doc("Company", self.company).default_return_income_account
		else:
			frappe.throw("Please Set Default Return Income Account in the Company {}".format(self.company))
			
@frappe.whitelist()
def apply_nomor_awalan_pajak(self,method):
	if self.customer:
		cust_doc = frappe.get_doc("Customer", self.customer)
		self.nomor_awalan_pajak = cust_doc.nomor_awalan_pajak

@frappe.whitelist()
def apply_hs_code(self,method):
	if not self.cost_center:
		company = frappe.get_doc("Company", self.company)
		self.cost_center = company.cost_center

	for row in self.items:
		row.hs_code = frappe.get_doc("Item",row.item_code).hs_code


@frappe.whitelist()
def repair_gl_entry_invoice():
	company = frappe.get_doc("Company", "GIAS")
	if company.nama_cabang not in ["GIAS BANDUNG","GIAS BALI","GIAS BANJARMASIN","GIAS BENGKULU"]:

		invoice_list = frappe.db.sql(""" SELECT name FROM `tabSales Invoice` WHERE docstatus = 1""")
		for row in invoice_list:
			inv_doc = frappe.get_doc("Sales Invoice",row[0])
			cust_doc = frappe.get_doc("Customer", inv_doc.customer)
			tanda = 0
			if inv_doc.items[0].item_name == "SALDO AWAL":
				if cust_doc.disabled == 1:
					cust_doc.disabled = 0
					tanda = 1
					cust_doc.db_update()

				repair_gl_entry("Sales Invoice",row[0])
				frappe.db.commit()
				print(str(row[0]))

				if tanda == 1:
					cust_doc.disabled = 1
					cust_doc.db_update()
					

@frappe.whitelist()
def patch_sales_invoice():
	list_sinv = frappe.db.sql(""" 
		SELECT sinv.name
		FROM `tabSales Invoice` sinv
		JOIN `tabStock Ledger Entry` sle ON sle.`voucher_no` = sinv.name
		WHERE sinv.docstatus = 1
		AND sinv.name = "SI-GIAS-JBI-1-23-03-00588"
		GROUP BY sinv.name
		;
		 """)
	
	for row in list_sinv:
		repair_gl_entry("Sales Invoice", row[0])
		print(row[0])


@frappe.whitelist()
def validate_gl(self,method):
	delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(self.name))	

@frappe.whitelist()
def repair_gl_entry(doctype,docname):
	SalesInvoice.get_gl_entries = custom_get_gl_entries
	docu = frappe.get_doc(doctype, docname)	

	# for row in docu.items:
	# 	row.price_list_rate = row.rate
	# 	row.discount_amount = 0
	# 	row.discount_percentage = 0
	# 	row.db_update()

	frappe.flags.repost_gl = True
	delete_sl = frappe.db.sql(""" DELETE FROM `tabStock Ledger Entry` WHERE voucher_no = "{}" """.format(docname))
	delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(docname))
	print(1)
	# frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 1 WHERE `field` = "allow_negative_stock" """)
	# docu.update_stock_ledger()
	docu.make_gl_entries()
	# frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 0 WHERE `field` = "allow_negative_stock" """)

@frappe.whitelist()
def submit_apa():
	submit_invoices("Sales Invoice","SI-GIAS-HO-1-23-07-00218-2")

@frappe.whitelist()
def submit_invoices(doctype,docname):
	SalesInvoice.get_gl_entries = custom_get_gl_entries
	docu = frappe.get_doc(doctype, docname)	
	docu.submit()
	# delete_sl = frappe.db.sql(""" DELETE FROM `tabStock Ledger Entry` WHERE voucher_no = "{}" """.format(docname))
	# delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(docname))

	# # frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 1 WHERE `field` = "allow_negative_stock" """)
	# # docu.update_stock_ledger()
	# docu.make_gl_entries()
	# # frappe.db.sql(""" UPDATE 

# @frappe.whitelist()
# def repair_gl_entry(doctype,docname):
	
# 	docu = frappe.get_doc(doctype, docname)	
# 	delete_sl = frappe.db.sql(""" DELETE FROM `tabStock Ledger Entry` WHERE voucher_no = "{}" """.format(docname))
# 	delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(docname))

# 	frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 1 WHERE `field` = "allow_negative_stock" """)
# 	docu.update_stock_ledger()
# 	custom_make_gl_entries(docu)
# 	frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 0 WHERE `field` = "allow_negative_stock" """)

@frappe.whitelist()
def custom_make_gl_entries(self, gl_entries=None, from_repost=False):
	from erpnext.accounts.general_ledger import make_gl_entries, make_reverse_gl_entries

	auto_accounting_for_stock = erpnext.is_perpetual_inventory_enabled(self.company)
	if not gl_entries:
		gl_entries = custom_get_gl_entries(self)

	if gl_entries:
		# if POS and amount is written off, updating outstanding amt after posting all gl entries
		update_outstanding = "No" if (cint(self.is_pos) or self.write_off_account or
			cint(self.redeem_loyalty_points)) else "Yes"

		if self.docstatus == 1:
			make_gl_entries(gl_entries, update_outstanding=update_outstanding, merge_entries=False, from_repost=from_repost)
		elif self.docstatus == 2:
			make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

		if update_outstanding == "No":
			from erpnext.accounts.doctype.gl_entry.gl_entry import update_outstanding_amt
			update_outstanding_amt(self.debit_to, "Customer", self.customer,
				self.doctype, self.return_against if cint(self.is_return) and self.return_against else self.name)

	elif self.docstatus == 2 and cint(self.update_stock) \
		and cint(auto_accounting_for_stock):
			make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

@frappe.whitelist()
def custom_get_gl_entries(self, warehouse_account=None):
	from erpnext.accounts.general_ledger import merge_similar_entries

	gl_entries = []

	custom_make_customer_gl_entry(self,gl_entries)
	
	self.make_tax_gl_entries(gl_entries)
	self.make_exchange_gain_loss_gl_entries(gl_entries)
	self.make_internal_transfer_gl_entries(gl_entries)

	# self.allocate_advance_taxes(gl_entries)

	custom_make_item_gl_entries(self,gl_entries)
			
	# merge gl entries before adding pos entries
	gl_entries = merge_similar_entries(gl_entries)

	self.make_loyalty_point_redemption_gle(gl_entries)
	self.make_pos_gl_entries(gl_entries)

	self.make_write_off_gl_entry(gl_entries)
	self.make_gle_for_rounding_adjustment(gl_entries)
	return gl_entries

@frappe.whitelist()
def override_get_gl_entries(self,method):
	SalesInvoice.get_gl_entries = custom_get_gl_entries
	SalesInvoice.make_gl_entries = custom_make_gl_entries

SalesInvoice.get_gl_entries = custom_get_gl_entries
SalesInvoice.make_gl_entries = custom_make_gl_entries

def custom_make_customer_gl_entry(self, gl_entries):
	# Checked both rounding_adjustment and rounded_total
	# because rounded_total had value even before introcution of posting GLE based on rounded total
	grand_total = self.rounded_total if (self.rounding_adjustment and self.rounded_total) else self.grand_total
	if grand_total and not self.is_internal_transfer():
		# Didnot use base_grand_total to book rounding loss gle
		grand_total_in_company_currency = flt(grand_total * self.conversion_rate,
			self.precision("grand_total"))

		gl_entries.append(
			self.get_gl_dict({
				"account": self.debit_to,
				"party_type": "Customer",
				"party": self.customer,
				"due_date": self.due_date,
				"against": self.against_income_account,
				"debit": grand_total_in_company_currency,
				"debit_in_account_currency": grand_total_in_company_currency \
					if self.party_account_currency==self.company_currency else grand_total,
				"against_voucher": self.return_against if cint(self.is_return) and self.return_against else self.name,
				"against_voucher_type": self.doctype,
				"cost_center": self.cost_center,
				"project": self.project
			}, self.party_account_currency, item=self)
		)


		for row in self.items:
			discount_account = ""
			get_account = frappe.db.sql(""" SELECT value FROM `tabSingles` WHERE field = "prorate_discount_account" AND value IS NOT NULL and value != "" AND doctype = "Selling Settings" """)
			if len(get_account) > 0:
				discount_account = get_account[0][0]

			if not discount_account:
				frappe.throw("Please set a Prorate Discount Account in Selling Settings before submitting this document.")
			else:
				if flt(row.discount_amount) > 0:
					total_discount = 0
					variable = 100
					centang = 0
					for rowtax in self.taxes:
						if rowtax.rate and variable == 100 and rowtax.included_in_print_rate == 1:
							variable += rowtax.rate
							
						if rowtax.included_in_print_rate == 1:
							centang = 1

					if centang == 1:
						total_discount = (flt(row.discount_amount)) * row.qty / (variable / 100)
					else:
						total_discount = (flt(row.discount_amount)) * row.qty

					gl_entries.append(
						self.get_gl_dict({
							"account": discount_account,
							"debit": total_discount,
							"debit_in_account_currency": total_discount,
							"cost_center": self.cost_center,
							"project": self.project
						}, self.party_account_currency, item=self)
					)

					gl_entries.append(
						self.get_gl_dict({
							"account": row.income_account,
							"credit": total_discount,
							"credit_in_account_currency": total_discount,
							"cost_center": self.cost_center,
							"project": self.project
						}, self.party_account_currency, item=self)
					)
	if self.discount_2:
		get_account = frappe.db.sql(""" SELECT value FROM `tabSingles` WHERE field = "prorate_discount_account" AND value IS NOT NULL and value != "" AND doctype = "Selling Settings" """)
		if len(get_account) > 0:
			discount_account = get_account[0][0]

		if not discount_account:
			frappe.throw("Please set a Prorate Discount Account in Selling Settings before submitting this document.")
		else:
			if flt(self.discount_2) > 0:
				total_discount = 0
				variable = 100
				centang = 0
				for row in self.taxes:
					if row.rate and variable == 100 and row.included_in_print_rate == 1:
						variable += row.rate
						
					if row.included_in_print_rate == 1:
						centang = 1

				if centang == 1:
					total_discount = self.discount_2 / (variable / 100)
				else:
					total_discount = self.discount_2

				# gl_entries.append(
				# 	self.get_gl_dict({
				# 		"account": discount_account,
				# 		"debit": total_discount,
				# 		"debit_in_account_currency": total_discount,
				# 		"cost_center": self.cost_center_discount_2,
				# 		"branch": self.branch_discount_2,
				# 		"remarks": self.remark_discount_2,
				# 		"project": self.project
				# 	}, self.party_account_currency, item=self)
				# )
				gl_entries.append(
					self.get_gl_dict({
						"account": discount_account,
						"debit": total_discount,
						"debit_in_account_currency": total_discount,
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
		get_account = frappe.db.sql(""" SELECT value FROM `tabSingles` WHERE field = "global_discount_account" AND value IS NOT NULL and value != "" AND doctype = "Selling Settings" """)
		if len(get_account) > 0:
			discount_account = get_account[0][0]

		if not discount_account:
			frappe.throw("Please set a DP Invoice Account in Selling Settings before submitting this document.")
		else:
			account = frappe.get_doc("Account",discount_account)
			if account.account_type == "Receivable":
				gl_entries.append(
					self.get_gl_dict({
						"account": discount_account,
						"due_date": self.due_date,
						"against": self.against_income_account,
						"debit": (self.discount_amount - self.discount_2)/(variable/100),
						"debit_in_account_currency": (self.discount_amount - self.discount_2)/(variable/100),
						"cost_center": self.cost_center,
						"project": self.project,
						"party_type" : "Customer",
						"party" : self.customer
					}, self.party_account_currency, item=self)
				)
			else:
				gl_entries.append(
					self.get_gl_dict({
						"account": discount_account,
						"due_date": self.due_date,
						"against": self.against_income_account,
						"debit": (self.discount_amount - self.discount_2)/(variable/100),
						"debit_in_account_currency": (self.discount_amount - self.discount_2)/(variable/100),
						"cost_center": self.cost_center,
						"project": self.project
					}, self.party_account_currency, item=self)
				)

def custom_make_item_gl_entries(self, gl_entries):
	# income account gl entries
	for item in self.get("items"):
		if flt(item.base_net_amount, item.precision("base_net_amount")):
			if item.is_fixed_asset:
				asset = frappe.get_doc("Asset", item.asset)

				if (len(asset.finance_books) > 1 and not item.finance_book
					and asset.finance_books[0].finance_book):
					frappe.throw(_("Select finance book for the item {0} at row {1}")
						.format(item.item_code, item.idx))

				if self.discount_amount:
					fixed_asset_gl_entries = get_gl_entries_on_asset_disposal(asset,
						item.base_amount, item.finance_book)
				else:
					fixed_asset_gl_entries = get_gl_entries_on_asset_disposal(asset,
						item.base_net_amount, item.finance_book)

				for gle in fixed_asset_gl_entries:
					gle["against"] = self.customer
					gl_entries.append(self.get_gl_dict(gle, item=item))

				asset.db_set("disposal_date", self.posting_date)
				asset.set_status("Sold" if self.docstatus==1 else None)
			else:
				# Do not book income for transfer within same company
				if not self.is_internal_transfer():
					income_account = (item.income_account
						if (not item.enable_deferred_revenue or self.is_return) else item.deferred_revenue_account)

					account_currency = get_account_currency(income_account)
					gl_entries.append(
						self.get_gl_dict({
							"account": income_account,
							"against": self.customer,
							"credit": flt(item.base_net_amount, item.precision("base_net_amount")),
							"credit_in_account_currency": (flt(item.base_net_amount, item.precision("base_net_amount"))
								if account_currency==self.company_currency
								else flt(item.net_amount, item.precision("net_amount"))),
							"cost_center": item.cost_center,
							"project": item.project or self.project
						}, account_currency, item=item)
					)

	if self.discount_amount:
		item = self.items[0]
		income_account = (item.income_account
			if (not item.enable_deferred_revenue or self.is_return) else item.deferred_revenue_account)

		variable = 100

		for row in self.taxes:
			if row.rate and variable == 100 and row.included_in_print_rate == 1:
				variable += row.rate

		account_currency = get_account_currency(income_account)
		gl_entries.append(
			self.get_gl_dict({
				"account": income_account,
				"against": self.customer,
				"credit": flt((self.discount_amount/(variable/100)), item.precision("base_amount")),
				"credit_in_account_currency": flt((self.discount_amount/(variable/100)), item.precision("base_amount")),
				"cost_center": item.cost_center,
				"project": item.project or self.project
			}, account_currency, item=item)
		)


	# expense account gl entries
	if cint(self.update_stock) and \
		erpnext.is_perpetual_inventory_enabled(self.company):
		gl_entries += super(SalesInvoice, self).get_gl_entries()


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_dp_invoice(doctype, txt, searchfield, start, page_len, filters):
	from erpnext.controllers.queries import get_match_cond

	if not filters: filters = {}
	condition = ""
	return frappe.db.sql("""select name FROM
		`tabSales Invoice` WHERE
			dp_or_not = "DP" AND docstatus = 1 and outstanding_amount=0
			AND customer = %(customer)s
			AND name not in (SELECT invoice_dp from `tabSales Invoice DP` WHERE docstatus = 1  AND invoice_dp IS NOT NULL)
			AND 
			(name LIKE %(txt)s
			{condition}) {match_condition}"""
		.format(condition=condition, key=searchfield,
			match_condition=get_match_cond(doctype)), {
			'company': filters.get("company", ""),
			'txt': '%' + txt + '%',
			'customer':  filters.get("customer", "")
		})

@frappe.whitelist()
def get_net_total_dp(invoice):
	doc_invoice = frappe.get_doc("Sales Invoice", invoice)
	return doc_invoice.net_total