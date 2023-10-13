
import frappe
from frappe import _
from frappe.utils import cstr, flt, get_link_to_form
from erpnext.hr.doctype.employee_advance.employee_advance import EmployeeAdvance

@frappe.whitelist()
def patchset_status():
	list_ead = frappe.db.sql(""" SELECT name FROM `tabEmployee Advance` WHERE docstatus = 1 """)
	for row in list_ead:
		print(row[0])
		doc = frappe.get_doc("Employee Advance", row[0])
		custom_set_status(doc)
		doc.db_update()

@frappe.whitelist()
def custom_set_status(self):
	if self.docstatus == 0:
		self.status = "Draft"
	if self.docstatus == 1:
		if self.claimed_amount and flt(self.claimed_amount) == flt(self.paid_amount):
			self.status = "Claimed"
		elif self.claimed_amount and flt(self.claimed_amount) + flt(self.return_amount) == flt(self.paid_amount):
			self.status = "Claimed"
		elif self.claimed_amount and flt(self.claimed_amount) <= flt(self.paid_amount):
			self.status = "Partial Claimed"
		elif self.paid_amount and self.advance_amount == flt(self.paid_amount):
			self.status = "Paid"
		else:
			self.status = "Unpaid"
	elif self.docstatus == 2:
		self.status = "Cancelled"

EmployeeAdvance.set_status = custom_set_status

@frappe.whitelist()
def check_exchange_rate(self,method):
	if self.exchange_rate == 0 and self.currency == "IDR":
		self.exchange_rate = 1



@frappe.whitelist()
def overwrite_set_status(self,method):
	EmployeeAdvance.set_status = custom_set_status

@frappe.whitelist()
def custom_get_expense_claim(
	employee_name, company, employee_advance_name, posting_date, paid_amount, claimed_amount):
	default_payable_account = frappe.get_cached_value('Company',  company,  "default_expense_claim_payable_account")
	default_cost_center = frappe.get_cached_value('Company',  company,  'cost_center')

	expense_claim = frappe.new_doc('Expense Claim')
	expense_claim.company = company
	expense_claim.employee = employee_name
	expense_claim.payable_account = default_payable_account
	expense_claim.cost_center = default_cost_center
	expense_claim.is_paid = 1 if flt(paid_amount) else 0
	expense_claim.append(
		'advances',
		{
			'employee_advance': employee_advance_name,
			'posting_date': posting_date,
			'advance_paid': flt(paid_amount),
			'unclaimed_amount': flt(paid_amount) - flt(claimed_amount),
			'allocated_amount': flt(paid_amount) - flt(claimed_amount)
		}
	)

	return expense_claim
