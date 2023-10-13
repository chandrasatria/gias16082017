# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext, json
from frappe.utils import cstr, flt, fmt_money, formatdate, getdate, nowdate, cint, get_link_to_form
from frappe import msgprint, _, scrub
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.utils import get_balance_on, get_stock_accounts, get_stock_and_account_balance, \
	get_account_currency, check_if_stock_and_account_balance_synced
from erpnext.accounts.party import get_party_account
from erpnext.hr.doctype.expense_claim.expense_claim import update_reimbursed_amount
from erpnext.accounts.doctype.invoice_discounting.invoice_discounting \
	import get_party_account_based_on_invoice_discounting
from erpnext.accounts.deferred_revenue import get_deferred_booking_accounts

from six import string_types, iteritems
from frappe.model.document import Document
class StockAccountInvalidTransaction(frappe.ValidationError): pass


class JournalEntryTax(Document):
	def validate(self):
		for d in self.get("accounts"):
			account_type = frappe.db.get_value("Account", d.account, "account_type")
			if account_type in ["Receivable", "Payable"]:
				if not (d.party_type and d.party):
					frappe.throw(_("Row {0}: Party Type and Party is required for Receivable / Payable account {1}").format(d.idx, d.account))
