import frappe,erpnext
from erpnext.accounts.party import get_party_account
from frappe.utils import (today, flt, cint, fmt_money, formatdate,
	getdate, add_days, add_months, get_last_day, nowdate, get_link_to_form)
from frappe.model.mapper import get_mapped_doc

@frappe.whitelist()
def pusat_check_so(self,method):
	company_doc = frappe.get_doc("Company", self.company)
	if company_doc.server != "Cabang":
		for row in self.items:
			if not row.against_sales_order:
				frappe.throw(""" Delivery Note for HO must have Sales Order as base, please check {} in row {}.""".format(row.item_code, row.idx))
		

@frappe.whitelist()
def check_tanggal(self,method):
	company_doc = frappe.get_doc("Company", self.company)
	if "Input Backdate Delivery Note" not in frappe.get_roles():
		frappe.throw("5")
		if self.get("__islocal") != 1:
			frappe.throw("4")
			if getdate(str(self.posting_date)) < getdate(str(self.creation)):
				frappe.throw("Posting Date for Delivery Note are not allowed backdate from creation. Please check the posting date again.")
		else:
			frappe.throw("3")
			if getdate(str(self.posting_date)) < getdate(str(frappe.utils.today())):
				frappe.throw("Posting Date for Delivery Note are not allowed backdate. Please check the posting date again.")
	else:
		frappe.throw("2")

	for row in self.items:
		if row.against_sales_order:
			so_doc = frappe.get_doc("Sales Order",row.against_sales_order)
			so_date = so_doc.transaction_date
			if getdate(str(self.posting_date)) < getdate(str(so_date)):
				frappe.throw("Posting Date for Delivery Note are not allowed backdate from Sales Order {}. Please check the posting date again.".format(so_doc.name))




@frappe.whitelist()
def auto_je_retur(self,method):
	if self.is_return == 1:
		company_doc = frappe.get_doc("Company", self.company)
		branch = self.branch

		coa = frappe.db.sql(""" SELECT value FROM `tabSingles` WHERE field = "coa_selling_return" AND value IS NOT NULL and value != "" """)
		if len(coa) < 1:
			frappe.throw("Please check COA Selling Return field in Selling Settings, as its needed for creating auto JE for DN Return.")

		else:
			coa_return = coa[0][0]
			prec_asal = frappe.get_doc("Delivery Note",self.return_against)
			coa_hutang = get_party_account("Customer", prec_asal.customer, prec_asal.company)

			new_je = frappe.new_doc("Journal Entry")
			new_je.from_return_dn = self.name
			new_je.posting_date = self.posting_date
			if prec_asal.currency != "IDR":
				new_je.multi_currency = 1

			total = 0

			baris_baru = {
				"account": coa_hutang,
				"party_type": "Customer",
				"party" : prec_asal.customer,
				"exchange_rate": prec_asal.conversion_rate,
				"account_currency" : prec_asal.currency,
				"branch" : branch,
				"credit_in_account_currency": self.grand_total * -1,
				"credit": self.grand_total * -1 * prec_asal.conversion_rate,
				
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
							"debit_in_account_currency": row.tax_amount_after_discount_amount * -1,
							"debit": row.tax_amount_after_discount_amount * -1 * prec_asal.conversion_rate,
							"cost_center": company_doc.cost_center
						}
						new_je.append("accounts", baris_baru)
						total += row.tax_amount_after_discount_amount

			baris_baru = {
				"account": coa_return,
				"branch" : branch,
				"debit_in_account_currency": total,
				"debit": total * prec_asal.conversion_rate,
				"cost_center": company_doc.cost_center
			}

			new_je.append("accounts", baris_baru)
			
			new_je.voucher_type = "Credit Note - Penjualan"
			new_je.tax_or_non_tax = self.tax_or_non_tax
			new_je.naming_series = "CN-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
			new_je.cheque_no = "-"
			new_je.cheque_date = self.posting_date
			new_je.flags.ignore_permissions = True

			new_je.save()

			self.return_journal_entry = new_je.name
			# self.db_update()

@frappe.whitelist()
def debug_auto_je_retur():
	self = frappe.get_doc("Delivery Note", "DO-2-23-04-00003")
	if self.is_return == 1:
		company_doc = frappe.get_doc("Company", self.company)
		branch = self.branch

		coa = frappe.db.sql(""" SELECT value FROM `tabSingles` WHERE field = "coa_selling_return" AND value IS NOT NULL and value != "" """)
		if len(coa) < 1:
			frappe.throw("Please check COA Selling Return field in Selling Settings, as its needed for creating auto JE for DN Return.")

		else:
			coa_return = coa[0][0]
			prec_asal = frappe.get_doc("Delivery Note",self.return_against)
			coa_hutang = get_party_account("Customer", prec_asal.customer, prec_asal.company)

			new_je = frappe.new_doc("Journal Entry")
			new_je.from_return_dn = self.name
			new_je.posting_date = self.posting_date
			if prec_asal.currency != "IDR":
				new_je.multi_currency = 1

			total = 0

			baris_baru = {
				"account": coa_hutang,
				"party_type": "Customer",
				"party" : prec_asal.customer,
				"exchange_rate": prec_asal.conversion_rate,
				"account_currency" : prec_asal.currency,
				"branch" : branch,
				"credit_in_account_currency": self.grand_total * -1,
				"credit": self.grand_total * -1 * prec_asal.conversion_rate,
				
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
							"debit_in_account_currency": row.tax_amount_after_discount_amount * -1,
							"debit": row.tax_amount_after_discount_amount * -1 * prec_asal.conversion_rate,
							"cost_center": company_doc.cost_center
						}
						new_je.append("accounts", baris_baru)
						total += row.tax_amount_after_discount_amount

			baris_baru = {
				"account": coa_return,
				"branch" : branch,
				"debit_in_account_currency": total,
				"debit": total * prec_asal.conversion_rate,
				"cost_center": company_doc.cost_center
			}
			new_je.append("accounts", baris_baru)
			new_je.voucher_type = "Credit Note - Penjualan"
			new_je.naming_series = "CN-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
			new_je.tax_or_non_tax = self.tax_or_non_tax
			new_je.flags.ignore_permissions = True
			new_je.save()

			print(new_je.name)
			self.return_journal_entry = new_je.name
			self.db_update()