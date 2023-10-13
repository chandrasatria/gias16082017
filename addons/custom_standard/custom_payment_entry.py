
from __future__ import unicode_literals
import frappe, erpnext, json
from frappe import _, scrub, ValidationError, throw
from frappe.utils import flt, comma_or, nowdate, getdate, cint
from erpnext.accounts.utils import get_outstanding_invoices, get_account_currency, get_balance_on
from erpnext.accounts.party import get_party_account
from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account
from erpnext.setup.utils import get_exchange_rate
from erpnext.accounts.general_ledger import make_gl_entries, process_gl_map

from erpnext.hr.doctype.expense_claim.expense_claim import update_reimbursed_amount
from erpnext.accounts.doctype.bank_account.bank_account import get_party_bank_account, get_bank_account_details
from erpnext.controllers.accounts_controller import AccountsController, get_supplier_block_status
from erpnext.accounts.doctype.invoice_discounting.invoice_discounting import get_party_account_based_on_invoice_discounting
from erpnext.accounts.doctype.tax_withholding_category.tax_withholding_category import get_party_tax_withholding_details
from six import string_types, iteritems
from erpnext.accounts.doctype.payment_entry.payment_entry import set_party_type,set_party_account,set_party_account_currency,set_payment_type,set_grand_total_and_outstanding_amount,get_bank_cash_account,set_paid_amount_and_received_amount,apply_early_payment_discount,get_party_bank_account,get_reference_as_per_payment_terms, PaymentEntry

from erpnext.controllers.accounts_controller import validate_taxes_and_charges

@frappe.whitelist()
def override_validate(self,method):
	if self.payment_type == "Receive":
		if self.mode_of_payment:
			mod_doc = frappe.get_doc("Mode of Payment",self.mode_of_payment)
			if mod_doc.accounts:
				akun = mod_doc.accounts[0].default_account
				
			self.paid_to = akun

	if not self.references:
		frappe.throw("References is mandatory")

	for row in self.references:
		if row.reference_doctype == "Journal Entry":
			cust_doc = self.party
			je_doc = frappe.get_doc(row.reference_doctype, row.reference_name)

			if je_doc.tax_or_non_tax != self.tax_or_non_tax:
				frappe.throw("Journal {} cannot be in {} Transactions.".format(je_doc.tax_or_non_tax, self.tax_or_non_tax))


			check = 0
			for row_je in je_doc.accounts:
				if str(row_je.party) == str(cust_doc):
					check = 1

			if check == 0:
				frappe.throw("Journal Entry {} doesn't have party {}. Please check again.".format(row.reference_name, cust_doc))

	PaymentEntry.validate_journal_entry = custom_validate_journal_entry

@frappe.whitelist()
def delete_cancelled_entry(self,method):
	if self.docstatus == 2:
		frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(self.name))

@frappe.whitelist()
def custom_onload(self,method):
	for d in self.get("references"):
		if d.reference_doctype == "Purchase Invoice":
			out = frappe.get_doc(d.reference_doctype,d.reference_name).outstanding_amount
			if out != d.outstanding_amount:
				d.outstanding_amount = out
				d.db_update()

@frappe.whitelist()
def custom_validate_journal_entry(self):
	for d in self.get("references"):
		if d.allocated_amount and d.reference_doctype == "Journal Entry":
			je_accounts = frappe.db.sql("""select debit, credit from `tabJournal Entry Account`
				where account = %s and party=%s and docstatus = 1 and parent = %s
				and (reference_type is null or reference_type in ("", "Sales Order", "Purchase Order"))
				""", (self.party_account, self.party, d.reference_name), as_dict=True)

			# if not je_accounts:
			# 	frappe.throw(_("Row #{0}: Journal Entry {1} does not have account {2} or already matched against another voucher")
			# 		.format(d.idx, d.reference_name, self.party_account))
			# else:
			# 	dr_or_cr = "debit" if self.payment_type == "Receive" else "credit"
			# 	valid = False
			# 	for jvd in je_accounts:
			# 		if flt(jvd[dr_or_cr]) > 0:
			# 			valid = True
			# 	if not valid:
			# 		frappe.throw(_("Against Journal Entry {0} does not have any unmatched {1} entry")
			# 			.format(d.reference_name, dr_or_cr))

PaymentEntry.validate_journal_entry = custom_validate_journal_entry

@frappe.whitelist()
def custom_add_party_gl_entries(self, gl_entries):
	if self.party_account:
		if self.payment_type=="Receive":
			against_account = self.paid_to
		else:
			against_account = self.paid_from

		party_gl_dict = self.get_gl_dict({
			"account": self.party_account,
			"party_type": self.party_type,
			"party": self.party,
			"against": against_account,
			"account_currency": self.party_account_currency,
			"cost_center": self.cost_center
		}, item=self)

		dr_or_cr = "credit" if erpnext.get_party_account_type(self.party_type) == 'Receivable' else "debit"

		for d in self.get("references"):
			cost_center = self.cost_center
			if d.reference_doctype == "Sales Invoice" and not cost_center:
				cost_center = frappe.db.get_value(d.reference_doctype, d.reference_name, "cost_center")
			gle = party_gl_dict.copy()
			gle.update({
				"against_voucher_type": d.reference_doctype,
				"against_voucher": d.reference_name,
				"cost_center": cost_center
			})

			if d.reference_doctype == "Journal Entry":
				je_doc = frappe.get_doc("Journal Entry", d.reference_name)
				for baris in je_doc.accounts:
					if baris.is_advance == "Yes":
						gle.update({
							"account": baris.account,
						})

			allocated_amount_in_company_currency = flt(flt(d.allocated_amount) * flt(d.exchange_rate),
				self.precision("paid_amount"))

			gle.update({
				dr_or_cr + "_in_account_currency": d.allocated_amount,
				dr_or_cr: allocated_amount_in_company_currency
			})

			gl_entries.append(gle)

		if self.unallocated_amount:
			exchange_rate = self.get_exchange_rate()
			base_unallocated_amount = (self.unallocated_amount * exchange_rate)
			check_dp = 0
			gle = party_gl_dict.copy()
			for d in self.get("references"):
				if d.reference_doctype == "Journal Entry":
					je_doc = frappe.get_doc("Journal Entry", d.reference_name)
					for baris in je_doc.accounts:
						if baris.is_advance == "Yes":
							gle.update({
								"account": baris.account,
							})

			gle.update({
				dr_or_cr + "_in_account_currency": self.unallocated_amount,
				dr_or_cr: base_unallocated_amount
			})
			if check_dp == 0:
				gl_entries.append(gle)

@frappe.whitelist()
def custom_add_bank_gl_entries(self, gl_entries):
	if self.payment_type in ("Pay", "Internal Transfer"):
		gl_entries.append(
			self.get_gl_dict({
				"account": self.paid_from,
				"account_currency": self.paid_from_account_currency,
				"against": self.party if self.payment_type=="Pay" else self.paid_to,
				"credit_in_account_currency": self.paid_amount,
				"credit": self.base_paid_amount,
				"cost_center": self.cost_center,
				"post_net_value": True
			}, item=self)
		)
	if self.payment_type in ("Receive", "Internal Transfer"):
		total_uang_muka = 0
		for d in self.get("references"):
			if d.reference_doctype == "Journal Entry":
				je_doc = frappe.get_doc("Journal Entry", d.reference_name)
				for baris in je_doc.accounts:
					if baris.is_advance == 'Yes':
						total_uang_muka += baris.credit_in_account_currency

		
		gl_entries.append(
			self.get_gl_dict({
				"account": self.paid_to,
				"account_currency": self.paid_to_account_currency,
				"against": self.party if self.payment_type=="Receive" else self.paid_from,
				"debit_in_account_currency": self.received_amount,
				"debit": self.base_received_amount,
				"cost_center": self.cost_center
			}, item=self)
		)

@frappe.whitelist()
def repair_gl_entries():
	PaymentEntry.make_gl_entries = custom_make_gl_entries
	repair_gl_entry_tanpa_sl("Payment Entry","PYI-GIAS-LOP-1-23-01-00018")

@frappe.whitelist()
def repair_gl_entry_tanpa_sl(doctype,docname):
    
    docu = frappe.get_doc(doctype, docname) 
    if doctype == "Stock Entry":
        if docu.purpose == "Material Issue":
            if docu.dari_branch == 1 and docu.stock_entry_type == "Material Issue":
                StockController.make_gl_entries = custom_make_gl_entries

    delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(docname))
    docu.make_gl_entries()


@frappe.whitelist()
def custom_make_gl_entries(self, cancel=0, adv_adj=0):
	if self.payment_type in ("Receive", "Pay") and not self.get("party_account_field"):
		self.setup_party_account_field()

	gl_entries = []
	custom_add_party_gl_entries(self,gl_entries)
	custom_add_bank_gl_entries(self,gl_entries)

	self.add_deductions_gl_entries(gl_entries)
	if self.name == "PYI-GIAS-LOP-1-23-01-00018":
		frappe.throw(str(gl_entries))
	self.add_tax_gl_entries(gl_entries)

	gl_entries = process_gl_map(gl_entries)
	make_gl_entries(gl_entries, cancel=cancel, adv_adj=adv_adj)

PaymentEntry.make_gl_entries = custom_make_gl_entries


@frappe.whitelist()
def custom_get_payment_entry(dt, dn, party_amount=None, bank_account=None, bank_amount=None):
	reference_doc = None
	doc = frappe.get_doc(dt, dn)
	if dt in ("Sales Order", "Purchase Order") and flt(doc.per_billed, 2) > 0:
		frappe.throw(_("Can only make payment against unbilled {0}").format(dt))

	party_type = set_party_type(dt)
	party_account = set_party_account(dt, dn, doc, party_type)
	party_account_currency = set_party_account_currency(dt, party_account, doc)
	payment_type = set_payment_type(dt, doc)
	grand_total, outstanding_amount = set_grand_total_and_outstanding_amount(party_amount, dt, party_account_currency, doc)

	# bank or cash
	bank = get_bank_cash_account(doc, bank_account)

	paid_amount, received_amount = set_paid_amount_and_received_amount(
		dt, party_account_currency, bank, outstanding_amount, payment_type, bank_amount, doc)

	paid_amount, received_amount, discount_amount = apply_early_payment_discount(paid_amount, received_amount, doc)

	pe = frappe.new_doc("Payment Entry")
	if dt in ("Sales Order", "Sales Invoice"):
		if doc.tax_or_non_tax:
			pe.tax_or_non_tax = doc.tax_or_non_tax
			
	pe.payment_type = payment_type
	pe.company = doc.company
	pe.cost_center = doc.get("cost_center")
	pe.posting_date = nowdate()
	pe.mode_of_payment = doc.get("mode_of_payment")
	pe.party_type = party_type
	pe.party = doc.get(scrub(party_type))
	pe.contact_person = doc.get("contact_person")
	pe.contact_email = doc.get("contact_email")
	pe.ensure_supplier_is_not_blocked()

	pe.paid_from = party_account if payment_type=="Receive" else bank.account
	pe.paid_to = party_account if payment_type=="Pay" else bank.account
	pe.paid_from_account_currency = party_account_currency \
		if payment_type=="Receive" else bank.account_currency
	pe.paid_to_account_currency = party_account_currency if payment_type=="Pay" else bank.account_currency
	pe.paid_amount = paid_amount
	pe.received_amount = received_amount
	pe.letter_head = doc.get("letter_head")

	if pe.party_type in ["Customer", "Supplier"]:
		bank_account = get_party_bank_account(pe.party_type, pe.party)
		pe.set("bank_account", bank_account)
		pe.set_bank_account_data()

	# only Purchase Invoice can be blocked individually
	if doc.doctype == "Purchase Invoice" and doc.invoice_is_blocked():
		frappe.msgprint(_('{0} is on hold till {1}').format(doc.name, doc.release_date))
	else:
		if (doc.doctype in ('Sales Invoice', 'Purchase Invoice')
			and frappe.get_value('Payment Terms Template',
			{'name': doc.payment_terms_template}, 'allocate_payment_based_on_payment_terms')):

			for reference in get_reference_as_per_payment_terms(doc.payment_schedule, dt, dn, doc, grand_total, outstanding_amount):
				pe.append('references', reference)
		else:
			if dt == "Dunning":
				pe.append("references", {
					'reference_doctype': 'Sales Invoice',
					'reference_name': doc.get('sales_invoice'),
					"bill_no": doc.get("bill_no"),
					"due_date": doc.get("due_date"),
					'total_amount': doc.get('outstanding_amount'),
					'outstanding_amount': doc.get('outstanding_amount'),
					'allocated_amount': doc.get('outstanding_amount')
				})
				pe.append("references", {
					'reference_doctype': dt,
					'reference_name': dn,
					"bill_no": doc.get("bill_no"),
					"due_date": doc.get("due_date"),
					'total_amount': doc.get('dunning_amount'),
					'outstanding_amount': doc.get('dunning_amount'),
					'allocated_amount': doc.get('dunning_amount')
				})
			else:
				pe.append("references", {
					'reference_doctype': dt,
					'reference_name': dn,
					"bill_no": doc.get("bill_no"),
					"due_date": doc.get("due_date"),
					'total_amount': grand_total,
					'outstanding_amount': outstanding_amount,
					'allocated_amount': outstanding_amount
				})

	pe.setup_party_account_field()
	pe.set_missing_values()

	if party_account and bank:
		if dt == "Employee Advance":
			reference_doc = doc
		pe.set_exchange_rate(ref_doc=reference_doc)
		pe.set_amounts()
		if discount_amount:
			pe.set_gain_or_loss(account_details={
				'account': frappe.get_cached_value('Company', pe.company, "default_discount_account"),
				'cost_center': pe.cost_center or frappe.get_cached_value('Company', pe.company, "cost_center"),
				'amount': discount_amount * (-1 if payment_type == "Pay" else 1)
			})
			pe.set_difference_amount()

	if doc.doctype == 'Purchase Order' and doc.apply_tds:
		pe.apply_tax_withholding_amount = 1
		pe.tax_withholding_category = doc.tax_withholding_category

		if not pe.advance_tax_account:
			pe.advance_tax_account = frappe.db.get_value('Company', pe.company, 'unrealized_profit_loss_account')

	return pe

@frappe.whitelist()
def custom_get_reference_details(reference_doctype, reference_name, party_account_currency):
	total_amount = outstanding_amount = exchange_rate = bill_no = None
	ref_doc = frappe.get_doc(reference_doctype, reference_name)
	company_currency = ref_doc.get("company_currency") or erpnext.get_company_currency(ref_doc.company)

	if reference_doctype == "Fees":
		total_amount = ref_doc.get("grand_total")
		exchange_rate = 1
		outstanding_amount = ref_doc.get("outstanding_amount")
	elif reference_doctype == "Donation":
		total_amount = ref_doc.get("amount")
		outstanding_amount = total_amount
		exchange_rate = 1
	elif reference_doctype == "Dunning":
		total_amount = ref_doc.get("dunning_amount")
		exchange_rate = 1
		outstanding_amount = ref_doc.get("dunning_amount")
	elif reference_doctype == "Journal Entry" and ref_doc.docstatus == 1:
		je_doc = frappe.get_doc("Journal Entry", reference_name)
		dp = 0
		account_dp = ""
		for row in je_doc.accounts:
			if row.is_advance == "Yes":
				dp = 1

		if dp == 1:
			total_amount = ref_doc.get("total_amount")
			for row in je_doc.accounts:
				if row.is_advance == "Yes":
					total_amount = row.debit_in_account_currency - row.credit_in_account_currency
					account_dp = row.account

			if ref_doc.multi_currency:
				exchange_rate = get_exchange_rate(party_account_currency, company_currency, ref_doc.posting_date)
			else:
				exchange_rate = 1
				outstanding_amount = get_outstanding_on_journal_entry_account(reference_name,account_dp)
		else:
			total_amount = ref_doc.get("total_amount")
			if ref_doc.multi_currency:
				exchange_rate = get_exchange_rate(party_account_currency, company_currency, ref_doc.posting_date)
			else:
				exchange_rate = 1
				outstanding_amount = get_outstanding_on_journal_entry(reference_name)
	elif reference_doctype != "Journal Entry":
		if ref_doc.doctype == "Expense Claim":
				total_amount = flt(ref_doc.total_sanctioned_amount) + flt(ref_doc.total_taxes_and_charges)
		elif ref_doc.doctype == "Employee Advance":
			total_amount = ref_doc.advance_amount
			exchange_rate = ref_doc.get("exchange_rate")
			if party_account_currency != ref_doc.currency:
				total_amount = flt(total_amount) * flt(exchange_rate)
		elif ref_doc.doctype == "Gratuity":
				total_amount = ref_doc.amount
		if not total_amount:
			if party_account_currency == company_currency:
				total_amount = ref_doc.base_grand_total
				exchange_rate = 1
			else:
				total_amount = ref_doc.grand_total
		if not exchange_rate:
			# Get the exchange rate from the original ref doc
			# or get it based on the posting date of the ref doc.
			exchange_rate = ref_doc.get("conversion_rate") or \
				get_exchange_rate(party_account_currency, company_currency, ref_doc.posting_date)
		if reference_doctype in ("Sales Invoice", "Purchase Invoice"):
			outstanding_amount = ref_doc.get("outstanding_amount")
			bill_no = ref_doc.get("bill_no")
		elif reference_doctype == "Expense Claim":
			outstanding_amount = flt(ref_doc.get("total_sanctioned_amount")) + flt(ref_doc.get("total_taxes_and_charges"))\
				- flt(ref_doc.get("total_amount_reimbursed")) - flt(ref_doc.get("total_advance_amount"))
		elif reference_doctype == "Employee Advance":
			outstanding_amount = (flt(ref_doc.advance_amount) - flt(ref_doc.paid_amount))
			if party_account_currency != ref_doc.currency:
				outstanding_amount = flt(outstanding_amount) * flt(exchange_rate)
				if party_account_currency == company_currency:
					exchange_rate = 1
		elif reference_doctype == "Gratuity":
			outstanding_amount = ref_doc.amount - flt(ref_doc.paid_amount)
		else:
			outstanding_amount = flt(total_amount) - flt(ref_doc.advance_paid)
	else:
		# Get the exchange rate based on the posting date of the ref doc.
		exchange_rate = get_exchange_rate(party_account_currency,
			company_currency, ref_doc.posting_date)

	return frappe._dict({
		"due_date": ref_doc.get("due_date"),
		"total_amount": flt(total_amount),
		"outstanding_amount": flt(outstanding_amount),
		"exchange_rate": flt(exchange_rate),
		"bill_no": bill_no
	})

def get_outstanding_on_journal_entry(name):
	res = frappe.db.sql(
			'SELECT '
			'CASE WHEN party_type IN ("Customer", "Student") '
			'THEN ifnull(sum(debit_in_account_currency - credit_in_account_currency), 0) '
			'ELSE ifnull(sum(credit_in_account_currency - debit_in_account_currency), 0) '
			'END as outstanding_amount '
			'FROM `tabGL Entry` WHERE (voucher_no=%s OR against_voucher=%s) '
			'AND party_type IS NOT NULL '
			'AND party_type != ""',
			(name, name), as_dict=1
		)

	outstanding_amount = res[0].get('outstanding_amount', 0) if res else 0

	return outstanding_amount

def get_outstanding_on_journal_entry_account(name,account):
	res = frappe.db.sql(
			'SELECT '
			'CASE WHEN party_type IN ("Customer", "Student") '
			'THEN ifnull(sum(debit_in_account_currency - credit_in_account_currency), 0) '
			'ELSE ifnull(sum(credit_in_account_currency - debit_in_account_currency), 0) '
			'END as outstanding_amount '
			'FROM `tabGL Entry` WHERE (voucher_no=%s OR against_voucher=%s) '
			'AND party_type IS NOT NULL AND account = %s '
			'AND party_type != ""',
			(name, name, account), as_dict=1
		)

	outstanding_amount = res[0].get('outstanding_amount', 0) if res else 0

	return outstanding_amount
