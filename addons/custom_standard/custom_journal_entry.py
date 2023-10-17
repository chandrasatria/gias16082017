from erpnext.setup.utils import get_exchange_rate
import frappe,erpnext
from frappe import msgprint, _, scrub
from frappe.model.document import Document
from erpnext.accounts.doctype.journal_entry.journal_entry import JournalEntry
from frappe.utils import cstr, flt, fmt_money, formatdate, getdate, nowdate, cint, get_link_to_form
from frappe.frappeclient import FrappeClient
import json
import os
import requests
import subprocess
from frappe.utils.background_jobs import enqueue
from frappe.utils.password import check_password,get_decrypted_password
from frappe.utils import get_site_name
from datetime import datetime
from erpnext.accounts.utils import (
	check_if_stock_and_account_balance_synced,
	get_account_currency,
	get_balance_on,
	get_stock_accounts,
	get_stock_and_account_balance,
)
from addons.custom_method import check_list_company_gias

@frappe.whitelist()
def bersihin_from_return_dn(self,method):
	if self.docstatus == 0 and not self.is_new() and self.from_return_dn:
		dn_doc = frappe.get_doc("Delivery Note",self.from_return_dn)
		if dn_doc.docstatus == 2:
			self.from_return_dn = ""
			self.db_update()
			frappe.db.commit()

@frappe.whitelist()
def cek_jedp(self,method):
	for row in self.accounts:
		if row.reference_type == "Journal Entry" and "JEDP" in row.reference_name:
			cek_sisa = frappe.db.sql(""" SELECT
				SUM(debit-credit)
				FROM
				`tabGL Entry`
				WHERE 
				(voucher_no = "{0}" OR `against_voucher` = "{0}")
				AND
				account = "{1}"
				AND is_cancelled = 0 """.format(row.reference_name, row.account))
			if len(cek_sisa) > 0:
				if cek_sisa[0][0] == 0:
					frappe.throw("Document {} are not allowed to be referred again, as the outstanding of the document is 0.".format(row.reference_name))



@frappe.whitelist()
def check_tax_naming(self,method):
	if self.doctype == "Journal Entry":
		if self.get("voucher_type") == "Depreciation Entry":
			return


	if not self.is_new():
		if "-1-" in self.name:
			if self.tax_or_non_tax == "Non Tax":
				frappe.throw("Tax or Non Tax are not allowed to changed after insert.")

		elif "-2-" in self.name:
			if self.tax_or_non_tax == "Tax":
				frappe.throw("Tax or Non Tax are not allowed to changed after insert.")

@frappe.whitelist()
def debug_cancel():
	self = frappe.get_doc("Journal Entry","JE-GIAS-HO-1-22-08-01702")

	company_doc = frappe.get_doc("Company", "GIAS")
	if company_doc.server == "Pusat":
		if self.je_log:
			check_rk = frappe.db.sql(""" select name from `tabRK Tools` WHERE name = "{}" """.format(self.je_log))
			if check_rk:
				if check_rk[0]:
					if check_rk[0][0]:
						rk_doc = frappe.get_doc("RK Tools", check_rk[0][0])
						for row in rk_doc.gl_movement:
							total_document = "{}-{}\n".format(row.document_type, row.document_no) 
							check_remark = """GL Move from {}. Document number : \n {}""".format(rk_doc.name, total_document)
							if check_remark == self.remark:
								site = check_list_company_gias(row.target_cabang)
								command = """ cd /home/frappe/frappe-bench/ && bench --site {} execute addons.custom_standard.custom_journal_entry.cancel_by_remark --kwargs "{{'rk_name':'{}','je_name':'{}'}}" """.format(site,rk_doc.name,self.name)
								os.system(command)
							else:
								print(check_remark)

@frappe.whitelist()
def before_cancel_check_rk_tools(self,method):
	company_doc = frappe.get_doc("Company", "GIAS")
	if company_doc.server == "Pusat":
		if self.je_log:
			check_rk = frappe.db.sql(""" select name from `tabRK Tools` WHERE name = "{}" """.format(self.je_log))
			if check_rk:
				if check_rk[0]:
					if check_rk[0][0]:
						rk_doc = frappe.get_doc("RK Tools", check_rk[0][0])
						for row in rk_doc.gl_movement:
							total_document = "{}-{}\n".format(row.document_type, row.document_no) 
							check_remark = """GL Move from {}. Document number : \n {}""".format(rk_doc.name, total_document)
							if check_remark in self.remark:
								site = check_list_company_gias(row.target_cabang)
								if self.old_name:
									command = """ cd /home/frappe/frappe-bench/ && bench --site {} execute addons.custom_standard.custom_journal_entry.cancel_by_remark --kwargs "{{'rk_name':'{}','je_name':'{}'}}" """.format(site,rk_doc.name,self.old_name)
									os.system(command)
								else:
									command = """ cd /home/frappe/frappe-bench/ && bench --site {} execute addons.custom_standard.custom_journal_entry.cancel_by_remark --kwargs "{{'rk_name':'{}','je_name':'{}'}}" """.format(site,rk_doc.name,self.name)
									os.system(command)
							else:
								print(check_remark)

@frappe.whitelist()
def before_cancel_check_rk_tools_debug():
	self = frappe.get_doc("Journal Entry","JE-GIAS-HO-1-23-01-00004")
	company_doc = frappe.get_doc("Company", "GIAS")
	if company_doc.server == "Pusat":
		if self.je_log:
			check_rk = frappe.db.sql(""" select name from `tabRK Tools` WHERE name = "{}" """.format(self.je_log))
			if check_rk:
				if check_rk[0]:
					if check_rk[0][0]:
						rk_doc = frappe.get_doc("RK Tools", check_rk[0][0])
						for row in rk_doc.gl_movement:
							total_document = "{}-{}\n".format(row.document_type, row.document_no) 
							check_remark = """GL Move from {}. Document number : \n {}""".format(rk_doc.name, total_document)
							if check_remark in self.remark:
								site = check_list_company_gias(row.target_cabang)
								if self.old_name:
									command = """ cd /home/frappe/frappe-bench/ && bench --site {} execute addons.custom_standard.custom_journal_entry.cancel_by_remark --kwargs "{{'rk_name':'{}','je_name':'{}'}}" """.format(site,rk_doc.name,self.old_name)
									os.system(command)
								else:
									command = """ cd /home/frappe/frappe-bench/ && bench --site {} execute addons.custom_standard.custom_journal_entry.cancel_by_remark --kwargs "{{'rk_name':'{}','je_name':'{}'}}" """.format(site,rk_doc.name,self.name)
									os.system(command)
							else:
								print(check_remark)


@frappe.whitelist()
def cancel_by_remark(rk_name,je_name):
	# pass
	check_remark = """GL Move from {}. Journal Entry HO from {}""".format(rk_name,je_name)
	list_je = frappe.db.sql(""" SELECT name FROM `tabJournal Entry` WHERE remark LIKE "{}%" AND docstatus = 1 """.format(check_remark))
	for row in list_je:
		je_doc = frappe.get_doc("Journal Entry", row[0])
		je_doc.cancel()
		je_doc.workflow_state = "Canceled"
		je_doc.db_update()
		print(je_doc.name)

@frappe.whitelist()
def before_cancel_remove_dn(self,method):
	if self.from_return_dn:
		dn = frappe.get_doc("Delivery Note", self.from_return_dn)
		dn.return_journal_entry = ""
		dn.db_update()
		self.from_return_dn = ""
		self.db_update()
	if self.from_return_prec:
		dn = frappe.get_doc("Purchase Receipt", self.from_return_prec)
		dn.return_journal_entry = ""
		dn.db_update()
		self.from_return_prec = ""
		self.db_update()

@frappe.whitelist()
def get_cash_request(cash_request):
	hasil = []
	iterasi = frappe.db.sql(""" 
		SELECT
		IF(pin.is_return = 0,tct.`document`,pin.return_against) AS document,
		tgl.account, 
		tct.amount AS difference,
		pin.supplier,
		tcr.currency, 
		pin.conversion_rate as exchange_rate,
		
		tgl.party,
		tgl.party_type,
		tcr.currency_exchange,
		tcr.type,
		tcr.tax_or_non_tax,
		tcr.cash_or_bank_account,
		acc.account_currency

		FROM `tabCash Request` tcr
		JOIN `tabCash Request Table` tct ON tct.parent = tcr.name
		JOIN `tabPurchase Invoice` pin ON pin.name = tct.`document`
		JOIN `tabGL Entry` tgl ON tgl.`voucher_no` = pin.name 
		AND pin.`credit_to` = tgl.`account`
		JOIN `tabAccount` acc ON acc.name = tgl.account
		WHERE tcr.name = "{}" AND pin.outstanding_amount > 0 

		UNION
		SELECT
		"",
		tct.account, 
		tct.amount AS difference,
		"",
		tcr.currency, 
		tcr.currency_exchange as exchange_rate,
		"",
		"",
		tcr.currency_exchange,
		tcr.type,
		tcr.tax_or_non_tax,
		tcr.cash_or_bank_account,
		acc.account_currency

		FROM `tabCash Request` tcr
		JOIN `tabCash Request Taxes and Charges` tct ON tct.parent = tcr.name
		JOIN `tabCash Request Table` tctc ON tctc.parent = tcr.name
		JOIN `tabPurchase Invoice` pin ON pin.name = tctc.`document`
		JOIN `tabAccount` acc ON acc.name = tct.account
		WHERE tcr.name = "{}" AND pin.outstanding_amount > 0 


		""".format(cash_request,cash_request), as_dict=1)

	for row in iterasi:
		change_rate = row.exchange_rate
		if row.document:
			sumber_invoice = frappe.get_doc(row.type, row.document)
			apakah_exchange_rate_baru = frappe.db.sql(""" 
				SELECT erra.`new_exchange_rate`
				FROM `tabExchange Rate Revaluation Account` erra
				JOIN `tabExchange Rate Revaluation` err
				ON err.name = erra.parent
				WHERE 
				erra.`account` = "{}"
				AND
				err.`posting_date` <= "{}"
				AND
				err.`posting_date` >= "{}"
				AND
				err.docstatus = 1 
				ORDER BY err.`posting_date` DESC
				LIMIT 1 """.format(row.account, frappe.utils.nowdate(), sumber_invoice.posting_date))


			if len(apakah_exchange_rate_baru) > 0:
				change_rate = apakah_exchange_rate_baru[0][0]

		account_document = frappe.get_doc("Account", row.account)

		get_je = frappe.db.sql(""" 
			SELECT sum(debit) FROM `tabJournal Entry Account` jea 
			WHERE jea.docstatus = 1 and sumber_cash_request = "{}" and reference_name = "{}" """.format(cash_request, row.document))

		sisa = 0
		if len(get_je) > 0:
			sisa = frappe.utils.flt(row.difference) - frappe.utils.flt(get_je[0][0])

		temp = {
			"document" : row.document,
			"account" : row.account,
			"difference": sisa,
			"supplier" : row.supplier,
			"currency": row.currency,
			"exchange_rate" : row.exchange_rate,
			"party" : row.party,
			"party_type": row.party_type,
			"currency_exchange": row.currency_exchange,
			"cash_or_bank_account" : row.cash_or_bank_account,
			"new_rate" : change_rate,
			"account_currency": row.account_currency,
			"tax_or_non_tax": row.tax_or_non_tax
		}

		hasil.append(temp)

	return hasil

@frappe.whitelist()
def get_cash_request_dr_supplier(supplier):
	hasil = []

	iterasi = frappe.db.sql(""" 
		SELECT
		tct.`document` AS document,
		tgl.account, 
		tct.amount AS difference,
		pin.supplier,
		tcr.currency, 
		pin.conversion_rate as exchange_rate,
		
		tgl.party,
		tgl.party_type,
		tcr.type,
		tcr.cash_or_bank_account,
		acc.account_currency

		FROM `tabCash Request` tcr
		JOIN `tabCash Request Table` tct ON tct.parent = tcr.name
		JOIN `tabPurchase Invoice` pin ON pin.name = tct.`document`
		JOIN `tabGL Entry` tgl ON tgl.`voucher_no` = pin.name 
		AND pin.`credit_to` = tgl.`account`
		JOIN `tabAccount` acc ON acc.name = tgl.account
		WHERE tcr.supplier = "{}" AND pin.outstanding_amount > 0 
		and tcr.docstatus = 1
		UNION
		SELECT
		"",
		tct.account, 
		tct.amount AS difference,
		"",
		tcr.currency, 
		tcr.currency_exchange as exchange_rate,
		"",
		"",
		tcr.type,
		tcr.cash_or_bank_account,
		acc.account_currency

		FROM `tabCash Request` tcr
		JOIN `tabCash Request Taxes and Charges` tct ON tct.parent = tcr.name
		JOIN `tabCash Request Table` tctc ON tctc.parent = tcr.name
		JOIN `tabPurchase Invoice` pin ON pin.name = tctc.`document`
		JOIN `tabAccount` acc ON acc.name = tct.account

		WHERE tcr.supplier = "{}" AND pin.outstanding_amount > 0 
		and tcr.docstatus =1 


		""".format(supplier,supplier), as_dict=1)


	for row in iterasi:
		change_rate = row.exchange_rate
		if row.document:
			sumber_invoice = frappe.get_doc(row.type, row.document)
			apakah_exchange_rate_baru = frappe.db.sql(""" 
				SELECT erra.`new_exchange_rate`
				FROM `tabExchange Rate Revaluation Account` erra
				JOIN `tabExchange Rate Revaluation` err
				ON err.name = erra.parent
				WHERE 
				erra.`account` = "{}"
				AND
				err.`posting_date` <= "{}"
				AND
				err.`posting_date` >= "{}"
				AND
				err.docstatus = 1 
				ORDER BY err.`posting_date` DESC
				LIMIT 1 """.format(row.account, frappe.utils.nowdate(), sumber_invoice.posting_date))


			if len(apakah_exchange_rate_baru) > 0:
				change_rate = apakah_exchange_rate_baru[0][0]

		temp = {
			"document" : row.document,
			"account" : row.account,
			"difference": row.difference,
			"supplier" : row.supplier,
			"currency": row.currency,
			"exchange_rate" : row.exchange_rate,
			"party" : row.party,
			"party_type": row.party_type,
			"currency_exchange": row.currency_exchange,
			"cash_or_bank_account" : row.cash_or_bank_account,
			"new_rate" : change_rate,
			"account_currency": row.account_currency
		}

		hasil.append(temp)

	return hasil

	return frappe.db.sql(""" 
		SELECT
		IF(pin.is_return = 0,tct.`document`,pin.return_against) AS document,
		tgl.account, 
		tct.amount AS difference,
		pin.supplier,
		tcr.currency, 
		pin.conversion_rate as exchange_rate,
		
		tgl.party,
		tgl.party_type

		FROM `tabCash Request` tcr
		JOIN `tabCash Request Table` tct ON tct.parent = tcr.name
		JOIN `tabPurchase Invoice` pin ON pin.name = tct.`document`
		JOIN `tabGL Entry` tgl ON tgl.`voucher_no` = pin.name 
		AND pin.`credit_to` = tgl.`account`
		WHERE tcr.supplier = "{}" AND pin.outstanding_amount > 0 

		UNION
		SELECT
		"",
		tct.account, 
		tct.amount AS difference,
		"",
		tcr.currency, 
		tcr.currency_exchange as exchange_rate,
		"",
		""

		FROM `tabCash Request` tcr
		JOIN `tabCash Request Taxes and Charges` tct ON tct.parent = tcr.name
		JOIN `tabCash Request Table` tctc ON tctc.parent = tcr.name
		JOIN `tabPurchase Invoice` pin ON pin.name = tctc.`document`

		WHERE tcr.supplier = "{}" AND pin.outstanding_amount > 0 


		""".format(supplier,supplier), as_dict=1)

@frappe.whitelist()
def overwrite_validate(self,method):
	JournalEntry.validate = custom_validate

def custom_validate_against_jv(self):
	for d in self.get('accounts'):
		if d.reference_type=="Journal Entry":
			account_root_type = frappe.db.get_value("Account", d.account, "root_type")
			# if account_root_type == "Asset" and flt(d.debit) > 0:
			# 	frappe.throw(_("Row #{0}: For {1}, you can select reference document only if account gets credited")
			# 		.format(d.idx, d.account))
			# elif account_root_type == "Liability" and flt(d.credit) > 0:
			# 	frappe.throw(_("Row #{0}: For {1}, you can select reference document only if account gets debited")
			# 		.format(d.idx, d.account))

			if d.reference_name == self.name:
				frappe.throw(_("You can not enter current voucher in 'Against Journal Entry' column"))

			against_entries = frappe.db.sql("""select * from `tabJournal Entry Account`
				where account = %s and docstatus = 1 and parent = %s
				and (reference_type is null or reference_type in ("", "Sales Order", "Purchase Order"))
				""", (d.account, d.reference_name), as_dict=True)

			if not against_entries:
				frappe.throw(_("Journal Entry {0} does not have account {1} or already matched against other voucher")
					.format(d.reference_name, d.account))
			else:
				dr_or_cr = "debit" if d.credit > 0 else "credit"
				valid = False
				for jvd in against_entries:
					if flt(jvd[dr_or_cr]) > 0:
						valid = True
				if not valid:
					frappe.throw(_("Against Journal Entry {0} does not have any unmatched {1} entry")
						.format(d.reference_name, dr_or_cr))

def custom_validate(self):
	if self.voucher_type == 'Opening Entry':
		self.is_opening = 'Yes'

	if not self.is_opening:
		self.is_opening='No'

	self.clearance_date = None

	self.validate_party()
	self.validate_entries_for_advance()
	custom_validate_multi_currency(self)
	self.set_amounts_in_company_currency()
	self.validate_debit_credit_amount()

	# Do not validate while importing via data import
	if not frappe.flags.in_import:
		custom_validate_total_debit_and_credit(self)

	custom_validate_against_jv(self)
	# centang = 0
	# check = frappe.db.sql(""" SELECT name FROM `tabCustom Field` WHERE name = "Journal Entry Account-sumber_cash_request" """)
	# if len(check) > 0:
	# 	centang = 1
	# if centang == 0:
	self.validate_reference_doc()
		
	self.set_against_account()
	if not self.je_log:
		if not self.cheque_date and self.cheque_no:
			self.cheque_date = self.posting_date
		self.create_remarks()
	self.set_print_format_fields()
	self.validate_expense_claim()
	self.validate_credit_debit_note()
	self.validate_empty_accounts_table()
	self.set_account_and_party_balance()
	self.validate_inter_company_accounts()
	self.validate_stock_accounts()
	if not self.title:
		self.title = self.get_title()

def custom_validate_total_debit_and_credit(self):
	custom_set_total_debit_credit(self)
	# if self.difference:
	# 	frappe.throw(_("Total Debit must be equal to Total Credit. The difference is {0}. {1} {2}")
	# 		.format(self.difference, self.total_debit,self.total_credit))

def custom_set_total_debit_credit(self):
	self.total_debit, self.total_credit, self.difference = 0, 0, 0
	for d in self.get("accounts"):
		if d.debit and d.credit:
			frappe.throw(_("You cannot credit and debit same account at the same time"))

		self.total_debit = flt(self.total_debit) + flt(d.debit, d.precision("debit"))
		self.total_credit = flt(self.total_credit) + flt(d.credit, d.precision("credit"))

	self.difference = flt(self.total_debit, self.precision("total_debit")) - \
		flt(self.total_credit, self.precision("total_credit"))

JournalEntry.validate = custom_validate

@frappe.whitelist()
def custom_validate_multi_currency(self):
	alternate_currency = []
	for d in self.get("accounts"):
		account = frappe.db.get_value("Account", d.account, ["account_currency", "account_type"], as_dict=1)
		if account:
			d.account_currency = account.account_currency
			d.account_type = account.account_type

		if not d.account_currency:
			d.account_currency = self.company_currency

		if d.account_currency != self.company_currency and d.account_currency not in alternate_currency:
			alternate_currency.append(d.account_currency)

	if alternate_currency:
		if not self.multi_currency:
			frappe.throw(_("Please check Multi Currency option to allow accounts with other currency"))

	custom_set_exchange_rate(self)

@frappe.whitelist()
def custom_set_exchange_rate(self):
	for d in self.get("accounts"):
		if d.account_currency == self.company_currency:
			d.exchange_rate = 1
		elif not d.exchange_rate or d.exchange_rate == 1 or \
			(d.reference_type in ("Sales Invoice", "Purchase Invoice")
			and d.reference_name and self.posting_date):
				centang = 0
				check = frappe.db.sql(""" SELECT name FROM `tabCustom Field` WHERE name = "Journal Entry Account-sumber_cash_request" """)
				if len(check) > 0:
					centang = 1

				if centang == 0:
					# Modified to include the posting date for which to retreive the exchange rate
					d.exchange_rate = get_exchange_rate(self.posting_date, d.account, d.account_currency,
						self.company, d.reference_type, d.reference_name, d.debit, d.credit, d.exchange_rate)

				else:
					if not d.sumber_cash_request:
						d.exchange_rate = get_exchange_rate(self.posting_date, d.account, d.account_currency,
							self.company, d.reference_type, d.reference_name, d.debit, d.credit, d.exchange_rate)

		if not d.exchange_rate:
			frappe.throw(_("Row {0}: Exchange Rate is mandatory").format(d.idx))

@frappe.whitelist()
def get_exchange_rate(posting_date, account=None, account_currency=None, company=None,
		reference_type=None, reference_name=None, debit=None, credit=None, exchange_rate=None):
	from erpnext.setup.utils import get_exchange_rate
	account_details = frappe.db.get_value("Account", account,
		["account_type", "root_type", "account_currency", "company"], as_dict=1)

	if not account_details:
		frappe.throw(_("Please select correct account"))

	if not company:
		company = account_details.company

	if not account_currency:
		account_currency = account_details.account_currency

	company_currency = erpnext.get_company_currency(company)

	if account_currency != company_currency:
		if reference_type in ("Sales Invoice", "Purchase Invoice") and reference_name:
			exchange_rate = frappe.db.get_value(reference_type, reference_name, "conversion_rate")

		# The date used to retreive the exchange rate here is the date passed
		# in as an argument to this function.
		elif (not exchange_rate or flt(exchange_rate)==1) and account_currency and posting_date:
			exchange_rate = get_exchange_rate(account_currency, company_currency, posting_date)
	else:
		exchange_rate = 1

	# don't return None or 0 as it is multipled with a value and that value could be lost
	return exchange_rate or 1

@frappe.whitelist()
def make_depreciation_entry_to_cabang():

	list_depreciation = frappe.db.sql(""" SELECT parent FROM `tabBranch Depreciation Schedule` WHERE DATE(NOW()) >= DATE(schedule_date) and docstatus = 1 and (no_je_di_cabang = "" OR no_je_di_cabang IS NULL) """)
	for row in list_depreciation:
		asset_doc = frappe.get_doc("Branch Asset",row[0])

		no_branch_asset = asset_doc.name
		akun_akumulasi = asset_doc.accumulated_depreciation_account
		akun_depresiasi = asset_doc.depreciation_account
		nilai_depresiasi = 0
		tax_or_non_tax = asset_doc.tax_or_non_tax

		cabang_doc = frappe.get_doc("List Company GIAS", asset_doc.cabang)
		branch = cabang_doc.accounting_dimension
		nama_site = cabang_doc.alamat_cabang

		for row in asset_doc.schedules:
			if str(row.schedule_date) == str(frappe.utils.nowdate()):
				print("Test Login To {}".format(nama_site))
				nilai_depresiasi = row.depreciation_amount
				clientroot = FrappeClient("https://{}/".format(nama_site),"administrator","admin")

				pr_doc = {}
				pr_doc.update({"doctype":"Journal Entry"})
				pr_doc.update({"docstatus":1})
				pr_doc.update({"voucher_type":"Depreciation Entry"})
				pr_doc.update({"tax_or_non_tax":tax_or_non_tax})
				pr_doc.update({"posting_date":frappe.utils.today()})
				pr_doc.update({"remark":"Depreciation Entry From HO. {} worth {}.".format(no_branch_asset, nilai_depresiasi)})
				pr_doc.update({"total_debit":nilai_depresiasi})
				pr_doc.update({"total_credit":nilai_depresiasi})
				pr_doc_items = []

				pr_doc_child = {}
				pr_doc_child.update({ "account" : akun_akumulasi })
				pr_doc_child.update({ "branch" : branch })
				pr_doc_child.update({ "credit" : nilai_depresiasi })
				pr_doc_child.update({ "credit_in_account_currency" : nilai_depresiasi })
			
				pr_doc_items.append(pr_doc_child)

				pr_doc_child = {}
				pr_doc_child.update({ "account" : akun_depresiasi })
				pr_doc_child.update({ "branch" : branch })
				pr_doc_child.update({ "debit" : nilai_depresiasi })
				pr_doc_child.update({ "debit_in_account_currency" : nilai_depresiasi })
			
				pr_doc_items.append(pr_doc_child)

				pr_doc.update({"accounts":pr_doc_items})

				clientroot.submit(pr_doc)
				row.no_je_di_cabang = "YES"
				row.db_update()

@frappe.whitelist()
def make_depreciation_entry_dari_pusat2():
	print("2")

@frappe.whitelist()
def make_depreciation_entry_dari_pusat(no_branch_asset, akun_akumulasi, akun_depresiasi, nilai_depresiasi, tax_or_non_tax, branch):
	new_je = frappe.new_doc("Journal Entry")
	new_je.tax_or_non_tax = tax_or_non_tax
	new_je.voucher_type = "Depreciation Entry"
	new_je.posting_date = frappe.utils.today()
	new_je.remark = "Depreciation Entry From HO. {} worth {}.".format(no_branch_asset, nilai_depresiasi)

	new_je.append("accounts",{
		"account": akun_akumulasi,
		"branch": branch,
		"credit": nilai_depresiasi,
		"credit_in_account_currency": nilai_depresiasi
	})

	new_je.append("accounts",{
		"account": akun_depresiasi,
		"branch": branch,
		"debit": nilai_depresiasi,
		"debit_in_account_currency": nilai_depresiasi
	})

	new_je.submit()
	print(new_je.name)


@frappe.whitelist()
def get_account_balance_and_party_type_custom(account, date, company, debit=None, credit=None, exchange_rate=None, cost_center=None,party=None,reference_type=None):
	"""Returns dict of account balance and party type to be set in Journal Entry on selection of account."""
	# frappe.msgprint("tes123")
	# frappe.msgprint(party+"2334")
	if not frappe.has_permission("Account"):
		frappe.msgprint(_("No Permission"), raise_exception=1)

	company_currency = erpnext.get_company_currency(company)
	account_details = frappe.db.get_value("Account", account, ["account_type", "account_currency"], as_dict=1)

	party_tmp = ""
	if not account_details:
		return

	if reference_type != 'Employee Advance':
		if account_details.account_type == "Receivable":
			party_type = "Customer"
		elif account_details.account_type == "Payable":
			party_type = "Supplier"
		else:
			party_type = ""
	else:
		party_type = "Employee"
		party_tmp = party

	grid_values = {
		"balance": get_balance_on(account, date, cost_center=cost_center),
		"party_type": party_type,
		"party": party_tmp,
		"account_type": account_details.account_type,
		"account_currency": account_details.account_currency or company_currency,

		# The date used to retreive the exchange rate here is the date passed in
		# as an argument to this function. It is assumed to be the date on which the balance is sought
		"exchange_rate": get_exchange_rate(date, account, account_details.account_currency,
			company, debit=debit, credit=credit, exchange_rate=exchange_rate)
	}

	# un-set party if not party type
	if reference_type != 'Employee Advance':
		if not party_type:
			grid_values["party"] = ""
	# if reference_type == 'Employee Advance':
	# 	frappe.msgprint(party)
	# 	grid_values["party"] = party

	return grid_values

@frappe.whitelist()
def get_exchange_rate(posting_date, account=None, account_currency=None, company=None,
		reference_type=None, reference_name=None, debit=None, credit=None, exchange_rate=None):
	from erpnext.setup.utils import get_exchange_rate
	account_details = frappe.db.get_value("Account", account,
		["account_type", "root_type", "account_currency", "company"], as_dict=1)

	if not account_details:
		frappe.throw(_("Please select correct account"))

	if not company:
		company = account_details.company

	if not account_currency:
		account_currency = account_details.account_currency

	company_currency = erpnext.get_company_currency(company)

	if account_currency != company_currency:
		if reference_type in ("Sales Invoice", "Purchase Invoice") and reference_name:
			exchange_rate = frappe.db.get_value(reference_type, reference_name, "conversion_rate")

		# The date used to retreive the exchange rate here is the date passed
		# in as an argument to this function.
		elif (not exchange_rate or flt(exchange_rate)==1) and account_currency and posting_date:
			exchange_rate = get_exchange_rate(account_currency, company_currency, posting_date)
	else:
		exchange_rate = 1

	# don't return None or 0 as it is multipled with a value and that value could be lost
	return exchange_rate or 1