# Copyright (c) 2021, das and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json
import os
from addons.custom_method import check_list_company_gias
from erpnext.accounts.doctype.journal_entry.journal_entry import JournalEntry

@frappe.whitelist()
def custom_on_cancel(self):
	from erpnext.accounts.utils import unlink_ref_doc_from_payment_entries
	from erpnext.payroll.doctype.salary_slip.salary_slip import unlink_ref_doc_from_salary_slip
	unlink_ref_doc_from_payment_entries(self)
	unlink_ref_doc_from_salary_slip(self.name)
	self.ignore_linked_doctypes = ('GL Entry', 'Stock Ledger Entry', 'RK Tools')
	self.make_gl_entries(1)
	self.update_advance_paid()
	self.update_expense_claim()
	self.unlink_advance_entry_reference()
	self.unlink_asset_reference()
	self.unlink_inter_company_jv()
	self.unlink_asset_adjustment_entry()
	self.update_invoice_discounting()

JournalEntry.on_cancel = custom_on_cancel


class RKTools(Document):
	def before_submit(self):
		company_doc = frappe.get_doc("Company", self.company)
		if self.rk_type == "Cost Distribution":
			if self.distribution_detail:
				je_baru = frappe.new_doc("Journal Entry")
				je_baru.posting_date = self.posting_date
				je_baru.tax_or_non_tax = self.tax_or_non_tax
				je_baru.reference_number = self.name
				je_baru.remark = "Cost Distribution from {}.".format(self.name)
				total = 0
				for row in self.distribution_detail:
					if row.amount > 0:
						baris_baru = {
							"account" : self.account_from,
							"debit": row.amount,
							"debit_in_account_currency": row.amount,
							"branch": self.branch,
							"cost_center" : company_doc.cost_center
						}
						total = total+row.amount

						je_baru.append("accounts", baris_baru)
					else:
						baris_baru = {
							"account" : self.account_from,
							"credit": row.amount * -1,
							"credit_in_account_currency": row.amount * -1,
							"branch": self.branch,
							"cost_center" : company_doc.cost_center
						}
						total = total+row.amount

						je_baru.append("accounts", baris_baru)
				if total > 0:
					baris_baru = {
						"account" : self.account_to,
						"credit": total,
						"credit_in_account_currency": total,
						"branch": self.branch,
						"cost_center" : company_doc.cost_center
					}
				else:
					baris_baru = {
						"account" : self.account_to,
						"debit": total * -1,
						"debit_in_account_currency": total * -1,
						"branch": self.branch,
						"cost_center" : company_doc.cost_center
					}

				je_baru.append("accounts", baris_baru)
				je_baru.je_log = self.name
				je_baru.submit()

				# BUAT JE LOG
				list_company = []
				for row_dist in self.distribution_detail:
					if row_dist.target not in list_company:
						list_company.append(row_dist.target)

				for row_company in list_company:
					je_baru1 = frappe.new_doc("Journal Entry")
					je_baru1.posting_date = self.posting_date
					je_baru1.tax_or_non_tax = self.tax_or_non_tax
					je_baru1.reference_number = self.name
					je_baru1.remark = "Cost Distribution from {}".format(self.name)
					total = 0

					for row in self.distribution_detail:
						if row.target == row_company:
							if row.amount > 0:
								baris_baru = {
									"account" : self.account_from,
									"credit": row.amount,
									"credit_in_account_currency": row.amount,
									"branch": row.branch,
									"cost_center" : company_doc.cost_center
								}
								total = total+row.amount
								je_baru1.append("accounts", baris_baru)
							else:
								baris_baru = {
									"account" : self.account_from,
									"debit": row.amount * -1,
									"debit_in_account_currency": row.amount * -1,
									"branch": row.branch,
									"cost_center" : company_doc.cost_center
								}
								total = total+row.amount
								je_baru1.append("accounts", baris_baru)

					if total > 0:
						baris_baru = {
							"account" : self.account_to,
							"debit": total,
							"debit_in_account_currency": total,
							"branch": self.branch,
							"cost_center" : company_doc.cost_center
						}
					else:
						baris_baru = {
							"account" : self.account_to,
							"credit": total * -1,
							"credit_in_account_currency": total * -1,
							"branch": self.branch,
							"cost_center" : company_doc.cost_center
						}

					je_baru1.append("accounts", baris_baru)

					ste_log = frappe.new_doc("JE Log")
					ste_log.nama_dokumen = self.name
					ste_log.tipe_dokumen = "Submit"
					ste_log.buat_je_di = "Cabang"
					ste_log.cabang = row_company
					ste_log.data = frappe.as_json(je_baru1)
					ste_log.company = self.company
					ste_log.submit()

		elif self.rk_type == "GL Move":
			jumlah_document = []
			for row in self.gl_movement:
				if row.document_no not in jumlah_document:
					jumlah_document.append(row.document_no)

			for row_doc_no in jumlah_document:
				if self.gl_movement:
					
					for row in self.gl_movement:
						if row.document_no == row_doc_no:
							je_baru = frappe.new_doc("Journal Entry")
							je_baru.posting_date = self.posting_date
							je_baru.tax_or_non_tax = self.tax_or_non_tax
							je_baru.reference_number = self.name
							total_document = ""
							if row.document_no == row_doc_no:
								total_document += "{}-{}\n".format(row.document_type, row.document_no) 
							

							je_baru.remark = "GL Move from {}. Document number : \n {}".format(self.name, total_document)
							
							if not je_baru.remark:
								je_baru.remark = str(row.remarks).replace("None","")
							else:
								je_baru.remark = str(je_baru.remark) + "{}\n".format(str(row.remarks).replace("None",""))


							if row.document_type == "Expense Claim":
								exc_doc = frappe.get_doc("Expense Claim",row.document_no)
								for baris_exc in exc_doc.expenses:
									if not je_baru.user_remark:
										je_baru.user_remark = baris_exc.description
									else:
										je_baru.user_remark = str(je_baru.user_remark) + "{}\n".format(baris_exc.description)

							elif row.document_type == "Purchase Invoice":
								exc_doc = frappe.get_doc("Purchase Invoice",row.document_no)
								je_baru.user_remark = exc_doc.get("remarks")
								je_baru.remark = str(je_baru.remark) + "{}\n".format(str(je_baru.user_remark).replace("None",""))

							elif row.document_type == "Journal Entry":
								exc_doc = frappe.get_doc("Journal Entry",row.document_no)
								je_baru.user_remark = exc_doc.get("user_remark")
							

							total = 0
							if row.value > 0:
								baris_baru = {
									"account" : row.rk_account,
									"debit": row.value,
									"debit_in_account_currency": row.value,
									"branch": row.gl_entry_branch,
									"cost_center" : company_doc.cost_center,
									"user_remark": row.remarks

								}
								total = total+row.value
								je_baru.append("accounts", baris_baru)
							else:
								baris_baru = {
									"account" : row.rk_account,
									"credit": row.value * -1,
									"credit_in_account_currency": row.value * -1,
									"branch": row.gl_entry_branch,
									"cost_center" : company_doc.cost_center,
									"user_remark": row.remarks

								}
								total = total+row.value
								je_baru.append("accounts", baris_baru)

							if total > 0:
								baris_baru = {
									"account" : row.document_account,
									"credit": total,
									"credit_in_account_currency": total,
									"branch": row.gl_entry_branch,
									"cost_center" : company_doc.cost_center,
									"user_remark": row.remarks
								}
								je_baru.append("accounts", baris_baru)
							else:
								baris_baru = {
									"account" : row.document_account,
									"debit": total * -1,
									"debit_in_account_currency": total * -1,
									"branch": row.gl_entry_branch,
									"cost_center" : company_doc.cost_center,
									"user_remark": row.remarks
								}
								je_baru.append("accounts", baris_baru)

							je_baru.je_log = self.name
							je_baru.submit()
							row.nomor_je_pusat = je_baru.name		

							no_je_pusat = je_baru.name
							# BUAT JE LOG

							row_company = row.target_cabang

							je_baru1 = frappe.new_doc("Journal Entry")
							je_baru1.posting_date = self.posting_date
							je_baru1.tax_or_non_tax = self.tax_or_non_tax
							je_baru1.reference_number = self.name
							je_baru1.remark = "GL Move from {}. Journal Entry HO from {}".format(self.name, no_je_pusat)
	
							total = 0
							if row.value > 0:
								baris_baru = {
									"account" : row.rk_account,
									"credit": row.value,
									"credit_in_account_currency": row.value,
									"branch": frappe.get_doc("List Company GIAS",row.target_cabang).accounting_dimension,
									"cost_center" : company_doc.cost_center,
									"user_remark": row.remarks
								}
								total = total+row.value
							else:
								baris_baru = {
									"account" : row.rk_account,
									"debit": row.value * -1,
									"debit_in_account_currency": row.value * -1,
									"branch": frappe.get_doc("List Company GIAS",row.target_cabang).accounting_dimension,
									"cost_center" : company_doc.cost_center,
									"user_remark": row.remarks
								}
								total = total+row.value

							je_baru1.append("accounts", baris_baru)

							if total > 0:
								baris_baru = {
									"account" : row.document_account,
									"debit": total,
									"debit_in_account_currency": total,
									"branch": frappe.get_doc("List Company GIAS",row.target_cabang).accounting_dimension,
									"cost_center" : company_doc.cost_center,
									"user_remark": row.remarks
								}
								je_baru1.append("accounts", baris_baru)
							else:
								baris_baru = {
									"account" : row.document_account,
									"credit": total * -1,
									"credit_in_account_currency": total * -1,
									"branch": frappe.get_doc("List Company GIAS",row.target_cabang).accounting_dimension,
									"cost_center" : company_doc.cost_center,
									"user_remark": row.remarks
								}
								je_baru1.append("accounts", baris_baru)

							if not je_baru1.remark:
								je_baru1.remark = row.remarks
							else:
								je_baru1.remark = str(je_baru1.remark) + "{}\n".format(row.remarks)

							if row.document_type == "Expense Claim":
								exc_doc = frappe.get_doc("Expense Claim",row.document_no)
								for baris_exc in exc_doc.expenses:
									if not je_baru1.user_remark:
										je_baru1.user_remark = baris_exc.description
									else:
										je_baru1.user_remark = str(je_baru1.user_remark) + "{}\n".format(baris_exc.description)

							elif row.document_type == "Purchase Invoice":
								exc_doc = frappe.get_doc("Purchase Invoice",row.document_no)
								je_baru1.user_remark = exc_doc.get("remarks")
								je_baru1.remark = str(je_baru1.remark) + "{}\n".format(str(je_baru.user_remark).replace("None",""))

							elif row.document_type == "Journal Entry":
								exc_doc = frappe.get_doc("Journal Entry",row.document_no)
								je_baru.user_remark = exc_doc.get("user_remark")

							ste_log = frappe.new_doc("JE Log")
							ste_log.nama_dokumen = self.name
							ste_log.tipe_dokumen = "Submit"
							ste_log.buat_je_di = "Cabang"
							ste_log.cabang = row_company
							ste_log.data = frappe.as_json(je_baru1)
							ste_log.company = self.company
							ste_log.submit()



	def before_cancel(self):
		list_je_log = frappe.db.sql(""" SELECT name, cabang FROM `tabJE Log` WHERE nama_dokumen = "{}" and tipe_dokumen = "Submit" """.format(self.name))
		for row in list_je_log:
			ste_log = frappe.new_doc("JE Log")
			ste_log.nama_dokumen = self.name
			ste_log.tipe_dokumen = "Cancel"
			ste_log.je_log_yang_dicancel = row[0]
			ste_log.buat_je_di = "Cabang"
			ste_log.cabang = row[1]
			ste_log.company = self.company
			ste_log.submit()

		list_je = frappe.db.sql(""" SELECT name FROM `tabJournal Entry` WHERE je_log = '{}' """.format(self.name))
		for row in list_je:
			doc = frappe.get_doc("Journal Entry", row[0])
			if doc.docstatus == 1:
				doc.cancel()
			doc.workflow_state = "Cancelled"
			doc.db_update()

@frappe.whitelist()
def get_je_to_cancel(no_doc):
	list_je = frappe.db.sql(""" SELECT name FROM `tabJournal Entry` WHERE name = "{}" and  docstatus = 1 """.format(no_doc))
	if len(list_je) == 0:
		return "No Journal Entry to be cancelled."
	else:
		for row in list_je:
			je_doc = frappe.get_doc("Journal Entry", row[0])
			je_doc.cancel()
			je_doc.workflow_state = "Cancelled"
			je_doc.db_update()
			
		return "Journal Entry has been cancelled."

@frappe.whitelist()
def debug_je_to_cancel():
	list_je = frappe.db.sql(""" SELECT name FROM `tabJournal Entry` WHERE name IN 
		(
		"JE-GIAS-SMD-1-22-07-00964",
		"JE-GIAS-SMD-1-22-07-00965",
		"JE-GIAS-SMD-1-22-07-00966",
		"JE-GIAS-SMD-1-22-07-00967"
		)
	""")
	for row in list_je:
		je_doc = frappe.get_doc("Journal Entry", row[0])
		print(row[0])
		je_doc.cancel()

@frappe.whitelist()
def debug_je_to_submit():
	list_je = frappe.db.sql(""" 
	) """)
	for row in list_je:
		je_doc = frappe.get_doc("Journal Entry", row[0])
		je_doc.docstatus = 0 
		je_doc.db_update()

	for row in list_je:
		je_doc = frappe.get_doc("Journal Entry", row[0])
		print(row[0])
		je_doc.submit()

@frappe.whitelist()
def debug_create_je_resolve():
	liste = frappe.db.sql(""" SELECT jl.name,je.name FROM `tabJE Log` jl
		LEFT JOIN `tabJournal Entry` je 
		ON je.je_log = jl.name
		WHERE je.name IS NULL
		""")

	for row in liste:
		print(row[0])
		self = frappe.get_doc("JE Log",row[0])
		company_doc = frappe.get_doc("Company",self.company)
		if company_doc.server == "Cabang" and self.cabang == company_doc.nama_cabang and self.tipe_dokumen == "Submit" and (self.buat_je_di == "Cabang" or self.cabang == "TRIBUANA BUMIPUSAKA" or self.cabang == "TANJUNG PINANG" or self.cabang == "TANJUNG UNCANG" or self.cabang == "GBP"):
			cabang_doc = frappe.get_doc("List Company GIAS",self.cabang)
			# buat je
			je_baru = json.loads(self.data)
			je_baru["name"] = ""
			je_baru["workflow_state"] = "Pending"
			je_baru["docstatus"] = 0
			je_baru["amended_from"] = ""
			je_baru["je_log"] = self.name
			je_baru["tax_or_non_tax"] = "Non Tax"
			je_baru["cheque_no"] = "-"
			je = frappe.get_doc(je_baru)
			je.cheque_date = je_baru["posting_date"]
			
			je.submit()
			self.submit()

		elif company_doc.server == "Cabang" and self.cabang == company_doc.nama_cabang and self.tipe_dokumen == "Cancel" and self.buat_je_di == "Cabang":
			list_je = frappe.db.sql(""" SELECT name FROM `tabJournal Entry` WHERE je_log = "{}" """.format(self.je_log_yang_dicancel))
			for row in list_je:
				je_doc = frappe.get_doc("Journal Entry", row[0])
				je_doc.cancel()

			self.submit()

		elif company_doc.server == "Pusat" and self.tipe_dokumen == "Submit" and self.buat_je_di == "Pusat":
			# buat je
			je_baru = json.loads(self.data)
			je_baru["name"] = ""
			je_baru["workflow_state"] = "Pending"
			je_baru["docstatus"] = 0
			je_baru["amended_from"] = ""
			je_baru["je_log"] = self.name
			je_baru["tax_or_non_tax"] = "Non Tax"
			je_baru["cheque_no"] = "-"
			je = frappe.get_doc(je_baru)
			je.cheque_date = je_baru["posting_date"]
			if "HRIS" in self.name :
				je.save()
			else:
				je.submit()
@frappe.whitelist()
def create_je_resolve(self,method):
	company_doc = frappe.get_doc("Company",self.company)
	if ((company_doc.server == "Cabang" and self.buat_je_di == "Cabang") or (self.cabang == "TRIBUANA BUMIPUSAKA" or self.cabang == "TANJUNG PINANG" or self.cabang == "TANJUNG UNCANG" or self.cabang == "GBP")) and self.tipe_dokumen == "Submit" and self.cabang == company_doc.nama_cabang:
		cabang_doc = frappe.get_doc("List Company GIAS",self.cabang)
		# buat je
		je_baru = json.loads(self.data)
		je_baru["name"] = ""
		je_baru["workflow_state"] = "Pending"
		je_baru["docstatus"] = 0
		je_baru["amended_from"] = ""
		je_baru["je_log"] = self.name
		je_baru["cheque_no"] = "-"
		je = frappe.get_doc(je_baru)
		je.cheque_date = je_baru["posting_date"]
		if je.remark:
			if "Depreciation Entry" in je.remark:
				je.save()
			else:	
				je.submit()
		else:	
			je.submit()


		self.submit()

	elif company_doc.server == "Cabang" and self.cabang == company_doc.nama_cabang and self.tipe_dokumen == "Cancel" and self.buat_je_di == "Cabang":
		list_je = frappe.db.sql(""" SELECT name FROM `tabJournal Entry` WHERE je_log = "{}" """.format(self.je_log_yang_dicancel))
		for row in list_je:
			je_doc = frappe.get_doc("Journal Entry", row[0])
			if je_doc.docstatus == 1:
				je_doc.cancel()
				je_doc.workflow_state = "Cancelled"
				je_doc.db_update()
			elif je_doc.docstatus == 0:
				je_doc.workflow_state = "Rejected"
				je_doc.db_update()
				
		self.submit()

	elif company_doc.server == "Pusat" and self.tipe_dokumen == "Submit" and self.buat_je_di == "Pusat":
		# buat je
		je_baru = json.loads(self.data)
		je_baru["name"] = ""
		je_baru["workflow_state"] = "Pending"
		je_baru["docstatus"] = 0
		je_baru["amended_from"] = ""
		je_baru["je_log"] = self.name
		je_baru["cheque_no"] = "-"
		je = frappe.get_doc(je_baru)
		je.cheque_date = je_baru["posting_date"]
		if je.remark:
			if "HRIS" in self.name or "Depreciation Entry" in je.remark :
				je.save()
			else:
				je.submit()
		else:
			je.submit()
			
@frappe.whitelist()
def debug_make_je():
	self = frappe.get_doc("RK Tools","RK-000049")
	company_doc = frappe.get_doc("Company", self.company)
	print("1")
	if self.rk_type == "GL Move":
		jumlah_document = []
		jumlah_document_expense_claim = []
		for row in self.gl_movement:
			if row.document_no not in jumlah_document and row.document_type != "Expense Claim" and row.document_type != "Purchase Invoice":
				jumlah_document.append(row.document_no)
			elif row.document_no not in jumlah_document_expense_claim and (row.document_type == "Expense Claim" or row.document_type == "Purchase Invoice"):
				jumlah_document_expense_claim.append(row.document_no)

		for row_doc_no in jumlah_document:
			if self.gl_movement:
				print("1")
				je_baru = frappe.new_doc("Journal Entry")
				je_baru.posting_date = self.posting_date
				je_baru.tax_or_non_tax = self.tax_or_non_tax
				je_baru.reference_number = self.name
				total_document = ""
				for row in self.gl_movement:
					if row.document_no == row_doc_no:
						total_document += "{}-{}\n".format(row.document_type, row.document_no) 
					

				je_baru.remark = "GL Move from {}. Document number : \n {}".format(self.name, total_document)
				print(str(je_baru.remark))
				
				for row in self.gl_movement:
					if row.document_no == row_doc_no:
						if row.document_type == "Expense Claim":
							exc_doc = frappe.get_doc("Expense Claim",row.document_no)
							for baris_exc in exc_doc.expenses:
								if not je_baru.user_remark:
									je_baru.user_remark = baris_exc.description
								else:
									je_baru.user_remark = str(je_baru.user_remark) + "{}\n".format(baris_exc.description)

						elif row.document_type == "Purchase Invoice":
							exc_doc = frappe.get_doc("Purchase Invoice",row.document_no)
							for baris_exc in exc_doc.items:
								if not je_baru.user_remark:
									je_baru.user_remark = baris_exc.user_remark
								else:
									je_baru.user_remark = str(je_baru.user_remark) + "{}\n".format(baris_exc.user_remark)

						if not je_baru.remark:
							je_baru.remark = row.remarks
						else:
							je_baru.remark = str(je_baru.remark) + "{}\n".format(row.remarks)

						total = 0
						baris_baru = {
							"account" : row.rk_account,
							"debit": row.value,
							"debit_in_account_currency": row.value,
							"branch": frappe.get_doc("List Company GIAS",row.target_cabang).accounting_dimension,
							"cost_center" : company_doc.cost_center,
							"user_remark": je_baru.user_remark
						}
						total = total+row.value
						je_baru.append("accounts", baris_baru)

						baris_baru = {
							"account" : row.document_account,
							"credit": total,
							"credit_in_account_currency": total,
							"branch": frappe.get_doc("List Company GIAS",row.target_cabang).accounting_dimension,
							"cost_center" : company_doc.cost_center,
							"user_remark": je_baru.user_remark
						}
						je_baru.append("accounts", baris_baru)

						

						
				je_baru.je_log = self.name
				
				# je_baru.save()
				print("SUDD")

		for row_doc_no in jumlah_document_expense_claim:
			if self.gl_movement:
				
				for row in self.gl_movement:
					if row.document_no == row_doc_no:
						je_baru = frappe.new_doc("Journal Entry")
						je_baru.posting_date = self.posting_date
						je_baru.tax_or_non_tax = self.tax_or_non_tax
						je_baru.reference_number = self.name
						total_document = ""
						if row.document_no == row_doc_no:
							total_document += "{}-{}\n".format(row.document_type, row.document_no) 
						

						je_baru.remark = "GL Move from {}. Document number : \n {}".format(self.name, total_document)
						
						if not je_baru.remark:
							je_baru.remark = str(row.remarks).replace("None","")
						else:
							je_baru.remark = str(je_baru.remark) + "{}\n".format(str(row.remarks).replace("None",""))

						print(je_baru.remark)

						
						if row.document_type == "Expense Claim":
							exc_doc = frappe.get_doc("Expense Claim",row.document_no)
							for baris_exc in exc_doc.expenses:
								if not je_baru.user_remark:
									je_baru.user_remark = baris_exc.description
								else:
									je_baru.user_remark = str(je_baru.user_remark) + "{}\n".format(baris_exc.description)
						elif row.document_type == "Purchase Invoice":
							exc_doc = frappe.get_doc("Purchase Invoice",row.document_no)
							je_baru.user_remark = exc_doc.get("remarks")
							
						total = 0
						baris_baru = {
							"account" : row.rk_account,
							"debit": row.value,
							"debit_in_account_currency": row.value,
							"branch": frappe.get_doc("List Company GIAS",row.target_cabang).accounting_dimension,
							"cost_center" : company_doc.cost_center,
							"user_remark": row.remarks

						}
						total = total+row.value
						je_baru.append("accounts", baris_baru)

						baris_baru = {
							"account" : row.document_account,
							"credit": total,
							"credit_in_account_currency": total,
							"branch": frappe.get_doc("List Company GIAS",row.target_cabang).accounting_dimension,
							"cost_center" : company_doc.cost_center,
							"user_remark": row.remarks
						}
						je_baru.append("accounts", baris_baru)

						je_baru.je_log = self.name
						# je_baru.save()

@frappe.whitelist()
def get_gl(branch, tax, filter_by="",from_date="",to_date="",account="",document_no="",module="" ):
	list_gl = frappe.db.sql(""" 

		SELECT gle.voucher_type,gle.no_voucher,ste.value as account,gle.debit,gle.remarks, gle.`name`
		FROM `tabCustom GL Entry` gle
		JOIN `tabSingles` ste ON ste.field = 'default_rk_account_for_tools'

		WHERE gle.branch = "{}"
		
		AND gle.`name` NOT IN (SELECT gl_entry_name FROM `tabRK Tools GL Move` WHERE docstatus < 2)
		and is_cancelled = 0

		UNION

		SELECT 
		gle.voucher_type,
		gle.no_voucher,
		gle.account,
		gle.debit,
		REPLACE(gle.remarks,"None",""), 
		gle.`name`
		FROM `tabGL Entry Custom` gle

		WHERE gle.branch = ""
		AND gle.`name` NOT IN (SELECT gl_entry_name FROM `tabRK Tools GL Move` WHERE docstatus < 2)
		AND is_cancelled = 0

	 """.format(branch))

	dict_gl = []
	for row in list_gl:
		one_row = {}
		docu = frappe.get_doc(row[0], row[1])
		if docu.tax_or_non_tax == tax and docu.docstatus == 1:
			one_row["voucher_type"] = row[0]
			one_row["voucher_no"] = row[1]
			one_row["account"] = frappe.get_doc("Company","GIAS").default_rk_account_for_tools
			one_row["debit"] = row[3]
			one_row["remarks"] = row[4]
			one_row["name"] = row[5]

			dict_gl.append(one_row)
	return dict_gl

@frappe.whitelist()
def get_gl_from_date(from_date,to_date,array_branch,array_account, tax):
	branch = str(array_branch).replace("[","(").replace("]",")")
	account = str(array_account).replace("[","(").replace("]",")")

	query_branch = ""
	if len(array_branch) > 0 and branch != "()":
		query_branch = """ AND gle.branch IN {} """.format(branch)

	list_gl = frappe.db.sql(""" 

		SELECT 
		gle.voucher_type,
		gle.no_voucher as voucher_no,
		gle.account,
		IF(gle.debit > 0, gle.debit, gle.credit * -1),
		REPLACE(gle.remarks,"None",""), 
		gle.`name`,
		gle.account as doc_account,
		gle.branch,
		lcg.name
		FROM `tabGL Entry Custom` gle
		LEFT JOIN `tabList Company GIAS` lcg on lcg.accounting_dimension = gle.branch

		WHERE gle.posting_date >= "{0}"
		AND gle.posting_date <= "{1}"
		and gle.account in {2}
		{3} 
		
		AND gle.`name` NOT IN (SELECT gl_entry_name FROM `tabRK Tools GL Move` WHERE docstatus < 2)
		AND gle.no_voucher NOT IN (SELECT name FROM `tabJournal Entry` WHERE je_log LIKE "RK%")
		AND is_cancelled = 0
		ORDER BY voucher_no

	 """.format(from_date, to_date, account, query_branch))

	dict_gl = []
	for row in list_gl:
		one_row = {}
		docu = frappe.get_doc(row[0], row[1])
		if docu.tax_or_non_tax == tax and docu.docstatus == 1:
			one_row["voucher_type"] = row[0]
			one_row["voucher_no"] = row[1]
			one_row["account"] = frappe.get_doc("Company","GIAS").default_rk_account_for_tools
			one_row["debit"] = row[3]
			one_row["remarks"] = row[4]
			one_row["name"] = row[5]
			one_row["doc_account"] = row[6]
			one_row["gl_entry_branch"] = row[7]
			one_row["lcg"] = row[8]

			dict_gl.append(one_row)
	return dict_gl
