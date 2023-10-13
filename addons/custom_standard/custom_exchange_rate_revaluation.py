import frappe,erpnext
from frappe.model.document import Document
import json
from frappe import msgprint, _
from frappe.utils import flt, cint, cstr, today, get_formatted_email
# from erpnext.accounts.doctype.exchange_rate_revaluation.exchange_rate_revaluation import ExchangeRateRevaluation
from erpnext.accounts.doctype.journal_entry.journal_entry import get_balance_on
from erpnext.setup.utils import get_exchange_rate


# ExchangeRateRevaluation.make_jv_entry = custom_make_jv_entry

@frappe.whitelist()
def custom_make_jv_entry(name):
	self=frappe.get_doc("Exchange Rate Revaluation", name)
	if self.total_gain_loss == 0:
		return

	unrealized_exchange_gain_loss_account = frappe.get_cached_value('Company',  self.company,
		"unrealized_exchange_gain_loss_account")
	if not unrealized_exchange_gain_loss_account:
		frappe.throw(_("Please set Unrealized Exchange Gain/Loss Account in Company {0}")
			.format(self.company))

	journal_entry = frappe.new_doc('Journal Entry')
	journal_entry.voucher_type = 'Exchange Rate Revaluation'
	journal_entry.company = self.company
	journal_entry.posting_date = self.posting_date
	journal_entry.multi_currency = 1

	journal_entry_accounts = []
	for d in self.accounts:
		dr_or_cr = "debit_in_account_currency" \
			if d.get("balance_in_account_currency") > 0 else "credit_in_account_currency"

		reverse_dr_or_cr = "debit_in_account_currency" \
			if dr_or_cr=="credit_in_account_currency" else "credit_in_account_currency"

		journal_entry_accounts.append({
			"account": d.get("account"),
			"party_type": d.get("party_type"),
			"party": d.get("party"),
			"account_currency": d.get("account_currency"),
			"balance": flt(d.get("balance_in_account_currency"), d.precision("balance_in_account_currency")),
			dr_or_cr: flt(abs(d.get("balance_in_account_currency")), d.precision("balance_in_account_currency")),
			"exchange_rate": flt(d.get("new_exchange_rate"), d.precision("new_exchange_rate")),
			"reference_type": "Exchange Rate Revaluation",
			"reference_name": self.name,
			})
		journal_entry_accounts.append({
			"account": d.get("account"),
			"party_type": d.get("party_type"),
			"party": d.get("party"),
			"account_currency": d.get("account_currency"),
			"balance": flt(d.get("balance_in_account_currency"), d.precision("balance_in_account_currency")),
			reverse_dr_or_cr: flt(abs(d.get("balance_in_account_currency")), d.precision("balance_in_account_currency")),
			"exchange_rate": flt(d.get("current_exchange_rate"), d.precision("current_exchange_rate")),
			"reference_type": "Exchange Rate Revaluation",
			"reference_name": self.name
			})

	# journal_entry_accounts.append({
	# 	"account": unrealized_exchange_gain_loss_account,
	# 	"balance": get_balance_on(unrealized_exchange_gain_loss_account),
	# 	"debit_in_account_currency": abs(self.total_gain_loss) if self.total_gain_loss < 0 else 0,
	# 	"credit_in_account_currency": self.total_gain_loss if self.total_gain_loss > 0 else 0,
	# 	"exchange_rate": 1,
	# 	"reference_type": "Exchange Rate Revaluation",
	# 	"reference_name": self.name,
	# 	})

	journal_entry.set("accounts", journal_entry_accounts)
	journal_entry.set_amounts_in_company_currency()
	journal_entry.set_total_debit_credit()
	# custom chandra - 12-07-2022

	journal_entry.append("accounts",{
		"account": unrealized_exchange_gain_loss_account,
		"balance": get_balance_on(unrealized_exchange_gain_loss_account),
		"debit_in_account_currency": abs(journal_entry.difference) if journal_entry.difference < 0 else 0,
		"credit_in_account_currency": journal_entry.difference if journal_entry.difference > 0 else 0,
		"exchange_rate": 1,
		"reference_type": "Exchange Rate Revaluation",
		"reference_name": self.name,
		})

	journal_entry.set_amounts_in_company_currency()
	journal_entry.set_total_debit_credit()
	return journal_entry.as_dict()