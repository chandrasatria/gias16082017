import frappe,erpnext
from frappe.model.document import Document
import json
from frappe import msgprint, _
from frappe.utils import cstr, flt, get_link_to_form
from erpnext.hr.doctype.expense_claim.expense_claim import ExpenseClaim
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
from erpnext.hr.utils import set_employee_name, share_doc_with_approver, validate_active_employee
from erpnext.hr.doctype.employee.employee import (
	InactiveEmployeeStatusError,
	get_holiday_list_for_employee,
)

def check_advance(doc,method):
	if doc.total_sanctioned_amount == doc.total_advance_amount and doc.total_sanctioned_amount > 0:
		doc.is_paid =1
	else:
		doc.is_paid =0 

@frappe.whitelist()
def cek_ada_je(self,method):
	jeaccount = frappe.db.sql(""" 
		SELECT parent 
		FROM `tabJournal Entry Account` 
		WHERE reference_name = "{}" and docstatus = 1""".format(self.name))

	if len(jeaccount) > 0:
		frappe.throw("Expense Claim can't be cancelled as there is Journal Entry {} using as reference.".format(jeaccount[0][0]))

@frappe.whitelist()
def repai_all():
	list_ex = frappe.db.sql(""" SELECT name FROM `tabExpense Claim` WHERE docstatus = 1 and """)
	for row in list_ex:
		repair_gl_entry("Expense Claim", row[0])
		print(row[0])


@frappe.whitelist()
def repai():
	frappe.flags.repost_gl == "True"
	expense_claim = frappe.db.sql(""" SELECT name from `tabExpense Claim` WHERE docstatus = 1 """)
	for row in expense_claim:
		repair_gl_entry("Expense Claim",row[0])
		print(row[0])
		frappe.db.commit()

@frappe.whitelist()
def repair_gl_entry(doctype,docname):
	
	docu = frappe.get_doc(doctype, docname)	
	# for row in docu.expenses:
	# 	typee = row.expense_type
	# 	typee_doc = frappe.get_doc("Expense Claim Type", typee)
	# 	account = typee_doc.accounts[0].default_account

	# 	if account != row.default_account:
	# 		row.default_account = account
	# 		row.db_update()

	ExpenseClaim.get_gl_entries = custom_get_gl_entries
	
	delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(docname))
	frappe.flags.repost_gl == True
	docu.make_gl_entries()
	frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 0 WHERE `field` = "allow_negative_stock" """)



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


import re
def striphtml(data):
	if data:
	    p = re.compile(r'<.*?>')
	    return p.sub('', data)
	else:
		return data

@frappe.whitelist()
def debug_ledger_detail():
	if frappe.get_doc("Company","GIAS").server == "Pusat":
		return

	list_exc = frappe.db.sql(""" SELECT name FROM `tabExpense Claim` WHERE docstatus = 1 """)
	for row in list_exc:
		self = frappe.get_doc("Expense Claim",row[0])
		frappe.db.sql(""" DELETE FROM `tabLedger Detail` WHERE no_voucher = "{}" """.format(self.name))
		make_ledger_detail(self.name)
		print(row[0])

@frappe.whitelist()
def hooks_make_ledger_detail(self,method):
	make_ledger_detail(self.name)

@frappe.whitelist()
def make_ledger_detail(no):
	self = frappe.get_doc("Expense Claim", no)
	for row in self.expenses:
		typee = row.expense_type
		typee_doc = frappe.get_doc("Expense Claim Type", typee)
		account = typee_doc.accounts[0].default_account

		if account != row.default_account:
			row.default_account = account
			row.db_update()

	
	for data in self.expenses:
		create_ledger_detail(self.posting_date,data.default_account,data.sanctioned_amount,0,"","",striphtml(data.description),self.remark,"Expense Claim",self.name,"","",data.branch or self.branch,data.cost_center or self.cost_center,self.tax_or_non_tax)
		

@frappe.whitelist()
def custom_get_gl_entries(self):
	
	for row in self.expenses:
		typee = row.expense_type
		typee_doc = frappe.get_doc("Expense Claim Type", typee)
		account = typee_doc.accounts[0].default_account

		if account != row.default_account:
			row.default_account = account
			row.db_update()

	gl_entry = []
	self.validate_account_details()

	# payable entry
	if self.grand_total - self.total_taxes_and_charges:
		gl_entry.append(
			self.get_gl_dict({
				"account": self.payable_account,
				"credit": self.grand_total-self.total_taxes_and_charges,
				"credit_in_account_currency": self.grand_total-self.total_taxes_and_charges,
				"against": ",".join([d.default_account for d in self.expenses]),
				"party_type": "Employee",
				"party": self.employee,
				"against_voucher_type": self.doctype,
				"against_voucher": self.name,
				"cost_center": self.cost_center
			}, item=self)
		)

	# expense entries
	for data in self.expenses:
		gl_entry.append(
			self.get_gl_dict({
				"account": data.default_account,
				"debit": data.sanctioned_amount,
				"debit_in_account_currency": data.sanctioned_amount,
				"against": self.employee,
				"cost_center": data.cost_center or self.cost_center
			}, item=data)
		)

	for data in self.advances:
		gl_entry.append(
			self.get_gl_dict({
				"account": data.advance_account,
				"credit": data.allocated_amount,
				"credit_in_account_currency": data.allocated_amount,
				"against": ",".join([d.default_account for d in self.expenses]),
				"party_type": "Employee",
				"party": self.employee,
				"against_voucher_type": "Employee Advance",
				"against_voucher": data.employee_advance
			})
		)

	# self.add_tax_gl_entries(gl_entry)

	if self.is_paid and self.grand_total:
		# payment entry
		payment_account = get_bank_cash_account(self.mode_of_payment, self.company).get("account")
		gl_entry.append(
			self.get_gl_dict({
				"account": payment_account,
				"credit": self.grand_total-self.total_taxes_and_charges,
				"credit_in_account_currency": self.grand_total-self.total_taxes_and_charges,
				"against": self.employee
			}, item=self)
		)

		gl_entry.append(
			self.get_gl_dict({
				"account": self.payable_account,
				"party_type": "Employee",
				"party": self.employee,
				"against": payment_account,
				"debit": self.grand_total-self.total_taxes_and_charges,
				"debit_in_account_currency": self.grand_total-self.total_taxes_and_charges,
				"against_voucher": self.name,
				"against_voucher_type": self.doctype,
			}, item=self)
		)

	return gl_entry

@frappe.whitelist()
def custom_calculate_taxes(self):
	self.total_taxes_and_charges = 0

	total_jasa = 0
	for jasa in self.expenses:
		if jasa.nilai_jasa:
			total_jasa += flt(jasa.nilai_jasa)

	for tax in self.taxes:
		if tax.rate:
			tax.tax_amount = flt(total_jasa) * flt(tax.rate/100)

		tax.total = flt(tax.tax_amount) + flt(self.total_sanctioned_amount)
		self.total_taxes_and_charges += flt(tax.tax_amount)

	self.grand_total = flt(self.total_sanctioned_amount) + flt(self.total_taxes_and_charges) - flt(self.total_advance_amount)

@frappe.whitelist()
def custom_validate_active_employee(employee,posting_date):
	if frappe.db.get_value("Employee", employee, "status") == "Inactive":
		if frappe.utils.getdate(frappe.db.get_value("Employee", employee, "date_of_retirement")):
			if frappe.utils.getdate(frappe.db.get_value("Employee", employee, "date_of_retirement")) <= frappe.utils.getdate(posting_date):
				frappe.throw(_("Transactions cannot be created for an Inactive Employee {0}. Retirement date is {1}").format(
					get_link_to_form("Employee", employee),frappe.utils.getdate(frappe.db.get_value("Employee", employee, "date_of_retirement"))), InactiveEmployeeStatusError)
		else:
			frappe.throw(_("Transactions cannot be created for an Inactive Employee {0}.").format(
				get_link_to_form("Employee", employee)), InactiveEmployeeStatusError)

@frappe.whitelist()
def custom_validate(self):
	for row in self.expenses:
		if row.sanctioned_amount == 0 or not row.sanctioned_amount:
			frappe.throw(""" Sanctioned amount need to be filled in row "{}." """.format(row.idx))
	custom_validate_active_employee(self.employee, self.posting_date)
	self.calculate_total_amount()
	self.validate_advances()
	self.validate_sanctioned_amount()
	self.calculate_total_amount()
	set_employee_name(self)
	self.set_expense_account(validate=True)
	self.set_payable_account()
	self.set_cost_center()
	self.calculate_taxes()
	self.set_status()
	if self.task and not self.project:
		self.project = frappe.db.get_value("Task", self.task, "project")

ExpenseClaim.validate = custom_validate

@frappe.whitelist()
def onload_validate(self,method):
	ExpenseClaim.validate = custom_validate

@frappe.whitelist()
def calculate_nilai_jasa(self,method):
	ExpenseClaim.calculate_taxes = custom_calculate_taxes
	ExpenseClaim.get_gl_entries = custom_get_gl_entries
	ExpenseClaim.validate_advances = custom_validate_advances
	ExpenseClaim.set_status = custom_set_status


def custom_validate_advances(self):
	self.total_advance_amount = 0
	for d in self.get("advances"):
		ref_doc = frappe.db.get_value("Employee Advance", d.employee_advance,
			["posting_date", "paid_amount", "claimed_amount", "advance_account"], as_dict=1)
		d.posting_date = ref_doc.posting_date
		d.advance_account = ref_doc.advance_account
		d.advance_paid = ref_doc.paid_amount
		d.unclaimed_amount = flt(ref_doc.paid_amount) - flt(ref_doc.claimed_amount)

		if d.allocated_amount and flt(d.allocated_amount,2) > flt(d.unclaimed_amount,2):
			frappe.throw(_("Row {0}# Allocated amount {1} cannot be greater than unclaimed amount {2}")
				.format(d.idx, d.allocated_amount, d.unclaimed_amount))

		self.total_advance_amount += flt(d.allocated_amount)

	if self.total_advance_amount:
		precision = self.precision("total_advance_amount")
		if flt(flt(self.total_advance_amount, precision),2) > flt(flt(self.total_claimed_amount) + flt(self.total_taxes_and_charges),2):
			frappe.throw(_("Total advance amount cannot be greater than total claimed amount {} > {}".format(flt(self.total_advance_amount, precision) , flt(self.total_claimed_amount) + flt(self.total_taxes_and_charges)) ))

		if self.total_sanctioned_amount and flt(self.total_advance_amount, precision) > flt(self.total_sanctioned_amount,precision) + flt(self.total_taxes_and_charges, precision):
			frappe.throw(_("Total advance amount cannot be greater than total sanctioned amount"))

@frappe.whitelist()
def custom_set_status_onload(self, method):
	if frappe.db.exists(self.doctype, self.name):
		status = {
			"0": "Draft",
			"1": "Submitted",
			"2": "Cancelled"
		}[cstr(self.docstatus or 0)]

		paid_amount = flt(self.total_amount_reimbursed) + flt(self.total_advance_amount)
		precision = self.precision("grand_total")
		if (self.is_paid or (flt(self.total_sanctioned_amount) > 0 and self.docstatus == 1
			and flt(self.total_claimed_amount, precision) <= flt(paid_amount, precision))) and self.approval_status == 'Approved':
			status = "Paid"
		elif flt(self.total_sanctioned_amount) > 0 and self.docstatus == 1 and self.approval_status == 'Approved':
			status = "Unpaid"
		elif self.docstatus == 1 and self.approval_status == 'Rejected':
			status = 'Rejected'

		self.status = status
		self.db_update()
		frappe.db.commit()

def custom_set_status(self, update=False):
	status = {
		"0": "Draft",
		"1": "Submitted",
		"2": "Cancelled"
	}[cstr(self.docstatus or 0)]

	paid_amount = flt(self.total_amount_reimbursed) + flt(self.total_advance_amount)
	precision = self.precision("grand_total")
	if (self.is_paid or (flt(self.total_sanctioned_amount) > 0 and self.docstatus == 1
		and flt(self.total_claimed_amount, precision) == flt(paid_amount, precision))) and self.approval_status == 'Approved':
		status = "Paid"
	elif flt(self.total_sanctioned_amount) > 0 and self.docstatus == 1 and self.approval_status == 'Approved':
		status = "Unpaid"
	elif self.docstatus == 1 and self.approval_status == 'Rejected':
		status = 'Rejected'

	if update:
		self.db_set("status", status)
	else:
		self.status = status

ExpenseClaim.calculate_taxes = custom_calculate_taxes
ExpenseClaim.get_gl_entries = custom_get_gl_entries
ExpenseClaim.validate_advances = custom_validate_advances
ExpenseClaim.set_status = custom_set_status

@frappe.whitelist()
def custom_make_bank_entry(dt, dn):
	from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account

	expense_claim = frappe.get_doc(dt, dn)
	default_bank_cash_account = get_default_bank_cash_account(expense_claim.company, "Bank")
	if not default_bank_cash_account:
		default_bank_cash_account = get_default_bank_cash_account(expense_claim.company, "Cash")

	payable_amount = flt(expense_claim.grand_total) \
		- flt(expense_claim.total_amount_reimbursed) - flt(expense_claim.total_advance_amount)

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = 'Bank Entry'
	je.company = expense_claim.company
	je.remark = 'Payment against Expense Claim: ' + dn

	tax_amount = flt(expense_claim.total_taxes_and_charges)

	original_total = flt(expense_claim.total_sanctioned_amount) \
		- flt(expense_claim.total_amount_reimbursed) - flt(expense_claim.total_advance_amount)
	# if tax_amount < 0:
	# 	payable_total = original_total + tax_amount
	# else:
	# 	payable_total = original_total - tax_amount

	if original_total > 0:
		je.append("accounts", {
			"account": expense_claim.payable_account,
			"debit_in_account_currency": original_total,
			"reference_type": "Expense Claim",
			"party_type": "Employee",
			"party": expense_claim.employee,
			"cost_center": erpnext.get_default_cost_center(expense_claim.company),
			"reference_name": expense_claim.name
		})
	payable_total = 0

	for row in expense_claim.taxes:
		if row.tax_amount < 0:
			je.append("accounts", {
				"account": row.account_head,
				"credit_in_account_currency": row.tax_amount * -1,
				"reference_type": "Expense Claim",
				"party_type": "Employee",
				"party": expense_claim.employee,
				"cost_center": erpnext.get_default_cost_center(expense_claim.company),
				"reference_name": expense_claim.name
			})
			payable_total = original_total + row.tax_amount
		else:
			je.append("accounts", {
				"account": row.account_head,
				"debit_in_account_currency": row.tax_amount,
				"reference_type": "Expense Claim",
				"party_type": "Employee",
				"party": expense_claim.employee,
				"cost_center": erpnext.get_default_cost_center(expense_claim.company),
				"reference_name": expense_claim.name
			})
			payable_total = original_total + row.tax_amount
			
	# if payable_amount > 0:
	# 	je.append("accounts", {
	# 		"account": expense_claim.payable_account,
	# 		"debit_in_account_currency": payable_amount,
	# 		"reference_type": "Expense Claim",
	# 		"party_type": "Employee",
	# 		"party": expense_claim.employee,
	# 		"cost_center": erpnext.get_default_cost_center(expense_claim.company),
	# 		"reference_name": expense_claim.name
	# 	})

	if payable_total > 0:
		je.append("accounts", {
			"account": default_bank_cash_account.account,
			"credit_in_account_currency": payable_total,
			"reference_type": "Expense Claim",
			"reference_name": expense_claim.name,
			"balance": default_bank_cash_account.balance,
			"account_currency": default_bank_cash_account.account_currency,
			"cost_center": erpnext.get_default_cost_center(expense_claim.company),
			"account_type": default_bank_cash_account.account_type
		})
	else:
		je.append("accounts", {
			"account": default_bank_cash_account.account,
			"debit_in_account_currency": payable_total * -1,
			"reference_type": "Expense Claim",
			"reference_name": expense_claim.name,
			"balance": default_bank_cash_account.balance,
			"account_currency": default_bank_cash_account.account_currency,
			"cost_center": erpnext.get_default_cost_center(expense_claim.company),
			"account_type": default_bank_cash_account.account_type
		})

	return je.as_dict()