# Copyright (c) 2021, das and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, add_months, cint, nowdate, getdate, today, date_diff, month_diff, add_days, get_last_day, get_datetime

class GIASAsset(Document):
	def onload(self):
		total_depreciation = 0
		for row_schedule in self.schedules:
			if row_schedule.detil_je_log:
				total_depreciation += row_schedule.depreciation_amount

		self.accumulated_depreciation_amount = total_depreciation
		if self.on_depreciation == 1:
			self.current_asset_amount = self.gross_purchase_amount - total_depreciation
		else:
			self.current_asset_amount = 0
		self.db_update()
		frappe.db.commit()

	def validate(self):

		self.make_depreciation_schedule()
		if self.cabang and self.server_kepemilikan == "Cabang":
			cabang_doc = frappe.get_doc("List Company GIAS", self.cabang)
			if not cabang_doc.accounting_dimension:
				frappe.throw("Accounting Dimension for Branch is mandatory. Please check List Company GIAS.")
			# if not cabang_doc.alamat_cabang:
			# 	frappe.throw("Alamat Cabang for Branch is mandatory. Please check List Company GIAS.")

	def before_submit(self):
		self.current_asset_amount = self.gross_purchase_amount
				
	def make_depreciation_schedule(self):
		self.schedules = []

		number_of_pending_depreciations = self.total_number_of_depreciations
		awal = 0
		akhir = 0
		if self.gross_purchase_amount:
			awal = self.gross_purchase_amount
		if self.expected_value_after_depreciation:
			akhir = self.expected_value_after_depreciation

		temp = self.gross_purchase_amount
		date = self.next_depreciation_date
		seringnya = self.frequency_of_depreciation
		satu_pending = (awal - akhir) / number_of_pending_depreciations

		for n in range(number_of_pending_depreciations):
			if n > 0:
				date = add_months(date, seringnya)

			if satu_pending <= temp:
				self.append("schedules", {
					"schedule_date": date,
					"depreciation_amount": satu_pending
				})
			else:
				self.append("schedules", {
					"schedule_date": date,
					"depreciation_amount": temp
				})

			temp = temp - satu_pending

@frappe.whitelist()
def make_book_asset():
	list_asset = frappe.db.sql(""" 
		SELECT tds.parent,tas.gross_purchase_amount,tds.`accumulated_depreciation_amount` 
		FROM `tabDepreciation Schedule` tds 
		JOIN `tabAsset` tas ON tas.name = tds.parent 
		WHERE tds.docstatus = 1 AND tds.detil_je_log IS NOT NULL
		AND (tds.book_value IS NULL OR tds.book_value = 0)
		AND tds.`accumulated_depreciation_amount` != tas.`gross_purchase_amount`
		GROUP BY parent """)
	for row in list_asset:
		asset_doc = frappe.get_doc("Asset", row[0])
		for baris in asset_doc.schedules:
			if baris.detil_je_log :
				baris.book_value = asset_doc.gross_purchase_amount - baris.accumulated_depreciation_amount
				baris.db_update()
		status = ""
		if not status:
			status = auto_status(asset_doc)
		asset_doc.db_set("status", status)

@frappe.whitelist()
def auto_status(self):
	if self.docstatus == 0:
		status = "Draft"
	elif self.docstatus == 1:
		status = "Submitted"
		if self.tanggal_scrap:
			status = "Scrapped"
		elif self.finance_books:
			idx = self.get_default_finance_book_idx() or 0

			depreciation_amount = self.depreciation_amount
			gross_purchase = self.gross_purchase_amount

			if flt(depreciation_amount,0) >= flt(gross_purchase,0):
				status = "Fully Depreciated"
			elif flt(depreciation_amount,0) > 0:
				status = 'Partially Depreciated'
	elif self.docstatus == 2:
		status = "Cancelled"
	print(status)
	return status

@frappe.whitelist()
def enqueue_make_je_log_asset():
	frappe.enqueue("addons.addons.doctype.gias_asset.gias_asset.make_je_log_asset")

@frappe.whitelist()
def custom_set_status(asset_doc):
	status = ""
	if not status:
		status = auto_status(asset_doc)
	asset_doc.db_set("status", status)

@frappe.whitelist()
def patch_asset():
	list_asset = frappe.db.sql(""" SELECT name FROM `tabAsset` WHERE status = "Fully Depreciated" and current_asset_amount > 0 """)
	for row in list_asset:
		asset_doc = frappe.get_doc("Asset",row[0])
		custom_set_status(asset_doc)

@frappe.whitelist()
def make_je_log_asset():
	list_depreciation = frappe.db.sql(""" 
		SELECT bds.parent, bds.name, bds.schedule_date
		FROM `tabDepreciation Schedule` bds
		JOIN `tabAsset` ga ON ga.name = bds.parent
		WHERE DATE(NOW()) >= DATE(schedule_date) 
		and ga.on_depreciation = 1
		and ga.docstatus = 1 and (bds.detil_je_log = "" OR bds.detil_je_log IS NULL) """)

	for row_depre in list_depreciation:
		asset_doc = frappe.get_doc("Asset",row_depre[0])

		no_branch_asset = asset_doc.name
		akun_akumulasi = asset_doc.accumulated_depreciation_account
		akun_depresiasi = asset_doc.depreciation_account
		nilai_depresiasi = 0
		# tax_or_non_tax = asset_doc.tax_or_non_tax
		# minta jadi Non Tax - 11-01-2023

		tax_or_non_tax = asset_doc.tax_or_non_tax

		branch = "Jakarta"
		cabang = ""
		if asset_doc.cabang and asset_doc.server_kepemilikan == "Cabang":
			cabang_doc = frappe.get_doc("List Company GIAS", asset_doc.cabang)
			cabang = asset_doc.cabang
			branch = cabang_doc.accounting_dimension

		company_doc = frappe.get_doc("Company", asset_doc.company)

		# nama_site = cabang_doc.alamat_cabang

		for row in asset_doc.schedules:
			if str(row.schedule_date) <= str(frappe.utils.nowdate()) and not row.detil_je_log:
				nilai_depresiasi = row.depreciation_amount
				
				print("MEMBUAT JE")
				je_baru1 = frappe.new_doc("Journal Entry")
				je_baru1.posting_date = row.schedule_date
				je_baru1.tax_or_non_tax = tax_or_non_tax
				je_baru1.remark = "Depreciation Entry From HO. {} worth {}.".format(no_branch_asset, nilai_depresiasi)
				je_baru1.total_debit = nilai_depresiasi
				je_baru1.voucher_type = "Depreciation Entry"
				total = 0
				try:
					cabang_doc = frappe.get_doc("List Company GIAS", row.list_company_gias)
				except:
					frappe.throw(asset_doc.name)
				cabang = row.list_company_gias
				branch = cabang_doc.accounting_dimension

				baris_baru = {
					"account" : akun_depresiasi,
					"debit": nilai_depresiasi,
					"debit_in_account_currency": nilai_depresiasi,
					"branch": branch,
					"cost_center" : company_doc.cost_center,
					"user_remark" : "Depreciation Entry From HO. {} worth {}.".format(no_branch_asset, nilai_depresiasi)
				}
				je_baru1.append("accounts", baris_baru)

				baris_baru = {
					"account" : akun_akumulasi,
					"credit": nilai_depresiasi,
					"credit_in_account_currency": nilai_depresiasi,
					"branch": branch,
					"cost_center" : company_doc.cost_center,
					"user_remark" : "Depreciation Entry From HO. {} worth {}.".format(no_branch_asset, nilai_depresiasi)
				}
				je_baru1.append("accounts", baris_baru)
				print("JE yang terbuat : {}".format(frappe.as_json(je_baru1)))

				ste_log = frappe.new_doc("JE Log")
				ste_log.nama_dokumen = asset_doc.name
				ste_log.tipe_dokumen = "Submit"
				if asset_doc.server_kepemilikan == "Pusat":
					ste_log.buat_je_di = "Pusat"


				if asset_doc.server_kepemilikan == "Cabang":
					ste_log.buat_je_di = "Cabang"
					ste_log.cabang = cabang

				ste_log.data = frappe.as_json(je_baru1)
				ste_log.company = asset_doc.company
				ste_log.submit()

				row.detil_je_log = ste_log.name
				row.db_update()

				idx = cint(row.finance_book_id)
				finance_books = asset_doc.get('finance_books')[idx - 1]
				finance_books.value_after_depreciation -= row.depreciation_amount
				finance_books.db_update()

		custom_set_status(asset_doc)

		total_depreciation = 0
		times = 0
		for row_schedule in asset_doc.schedules:
			if row_schedule.detil_je_log:
				total_depreciation += row_schedule.depreciation_amount
				times += 1

		asset_doc.accumulated_depreciation_amount = flt(total_depreciation,0)
		asset_doc.depreciation_amount = flt(total_depreciation + asset_doc.opening_accumulated_depreciation,0)
		asset_doc.accumulated_depreciation_times = times + asset_doc.number_of_depreciations_booked
		
		asset_doc.current_asset_amount = asset_doc.gross_purchase_amount - total_depreciation - asset_doc.opening_accumulated_depreciation
		asset_doc.db_update()

		frappe.db.commit()


@frappe.whitelist()
def make_je_depreciation_by_name(name):
	list_depreciation = frappe.db.sql(""" 
		SELECT bds.parent, bds.name 
		FROM `tabDepreciation Schedule` bds
		JOIN `tabAsset` ga ON ga.name = bds.parent
		WHERE DATE(NOW()) >= DATE(schedule_date) 
		and ga.on_depreciation = 1
		and bds.name = "{}"
		and ga.docstatus = 1 and (bds.detil_je_log = "" OR bds.detil_je_log IS NULL) 
		""".format(name))

	for row_depre in list_depreciation:
		asset_doc = frappe.get_doc("Asset",row_depre[0])

		no_branch_asset = asset_doc.name
		akun_akumulasi = asset_doc.accumulated_depreciation_account
		akun_depresiasi = asset_doc.depreciation_account
		nilai_depresiasi = 0
		tax_or_non_tax = asset_doc.tax_or_non_tax
		# tax_or_non_tax = "Non Tax"

		branch = "Jakarta"
		cabang = ""
		if asset_doc.cabang and asset_doc.server_kepemilikan == "Cabang":
			cabang_doc = frappe.get_doc("List Company GIAS", asset_doc.cabang)
			cabang = asset_doc.cabang
			branch = cabang_doc.accounting_dimension

		company_doc = frappe.get_doc("Company", asset_doc.company)

		# nama_site = cabang_doc.alamat_cabang

		for row in asset_doc.schedules:
			if str(row.schedule_date) <= str(frappe.utils.nowdate()) and not row.detil_je_log:
				nilai_depresiasi = row.depreciation_amount
				
				print("MEMBUAT JE")
				je_baru1 = frappe.new_doc("Journal Entry")
				je_baru1.posting_date = frappe.utils.today()
				je_baru1.tax_or_non_tax = tax_or_non_tax
				je_baru1.remark = "Depreciation Entry From HO. {} worth {}.".format(no_branch_asset, nilai_depresiasi)
				je_baru1.total_debit = nilai_depresiasi
				je_baru1.voucher_type = "Depreciation Entry"
				total = 0

				cabang_doc = frappe.get_doc("List Company GIAS", row.list_company_gias)
				cabang = row.list_company_gias
				branch = cabang_doc.accounting_dimension

				baris_baru = {
					"account" : akun_depresiasi,
					"debit": nilai_depresiasi,
					"debit_in_account_currency": nilai_depresiasi,
					"branch": branch,
					"cost_center" : company_doc.cost_center
				}
				je_baru1.append("accounts", baris_baru)

				baris_baru = {
					"account" : akun_akumulasi,
					"credit": nilai_depresiasi,
					"credit_in_account_currency": nilai_depresiasi,
					"branch": branch,
					"cost_center" : company_doc.cost_center
				}
				je_baru1.append("accounts", baris_baru)
				je_baru1.naming_series = "JE-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
				print("JE yang terbuat : {}".format(frappe.as_json(je_baru1)))

				ste_log = frappe.new_doc("JE Log")
				ste_log.nama_dokumen = asset_doc.name
				ste_log.tipe_dokumen = "Submit"
				if asset_doc.server_kepemilikan == "Pusat":
					ste_log.buat_je_di = "Pusat"

				if asset_doc.server_kepemilikan == "Cabang":
					ste_log.buat_je_di = "Cabang"
					ste_log.cabang = cabang

				ste_log.data = frappe.as_json(je_baru1)
				ste_log.company = asset_doc.company
				ste_log.submit()

				row.detil_je_log = ste_log.name
				row.db_update()


		total_depreciation = 0
		for row_schedule in asset_doc.schedules:
			if row_schedule.detil_je_log:
				total_depreciation += row_schedule.depreciation_amount

		asset_doc.accumulated_depreciation_amount = total_depreciation
		asset_doc.current_asset_amount = asset_doc.gross_purchase_amount - total_depreciation
		asset_doc.db_update()
		frappe.db.commit()


@frappe.whitelist()
def debug_make_je_log_asset():

	list_depreciation = frappe.db.sql(""" 
		SELECT bds.parent, bds.name 
		FROM `tabDepreciation Schedule` bds
		JOIN `tabAsset` ga ON ga.name = bds.parent
		WHERE DATE(NOW()) >= DATE(schedule_date) 
		and ga.on_depreciation = 1
		and ga.docstatus = 1 and (bds.detil_je_log = "" OR bds.detil_je_log IS NULL)  
		 """)

	for row_depre in list_depreciation:
		asset_doc = frappe.get_doc("Asset",row_depre[0])

		no_branch_asset = asset_doc.name
		akun_akumulasi = asset_doc.accumulated_depreciation_account
		akun_depresiasi = asset_doc.depreciation_account
		nilai_depresiasi = 0
		tax_or_non_tax = asset_doc.tax_or_non_tax
		# tax_or_non_tax = "Non Tax"

		branch = "Jakarta"
		cabang = ""
		if asset_doc.cabang and asset_doc.server_kepemilikan == "Cabang":
			cabang_doc = frappe.get_doc("List Company GIAS", asset_doc.cabang)
			cabang = asset_doc.cabang
			branch = cabang_doc.accounting_dimension

		company_doc = frappe.get_doc("Company", asset_doc.company)

		# nama_site = cabang_doc.alamat_cabang

		for row in asset_doc.schedules:
			if str(row.schedule_date) <= str(frappe.utils.nowdate()) and not row.detil_je_log:
				nilai_depresiasi = row.depreciation_amount
				
				print("MEMBUAT JE")
				je_baru1 = frappe.new_doc("Journal Entry")
				je_baru1.posting_date = row.schedule_date
				je_baru1.tax_or_non_tax = tax_or_non_tax
				je_baru1.remark = "Depreciation Entry From HO. {} worth {}.".format(no_branch_asset, nilai_depresiasi)
				je_baru1.total_debit = nilai_depresiasi
				je_baru1.voucher_type = "Depreciation Entry"
				total = 0

				baris_baru = {
					"account" : akun_depresiasi,
					"debit": nilai_depresiasi,
					"debit_in_account_currency": nilai_depresiasi,
					"branch": branch,
					"cost_center" : company_doc.cost_center
				}
				je_baru1.append("accounts", baris_baru)

				baris_baru = {
					"account" : akun_akumulasi,
					"credit": nilai_depresiasi,
					"credit_in_account_currency": nilai_depresiasi,
					"branch": branch,
					"cost_center" : company_doc.cost_center
				}
				je_baru1.append("accounts", baris_baru)
				je_baru1.naming_series = "JE-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
				print("JE yang terbuat : {}".format(frappe.as_json(je_baru1)))

				ste_log = frappe.new_doc("JE Log")
				ste_log.nama_dokumen = asset_doc.name
				ste_log.tipe_dokumen = "Submit"
				if asset_doc.server_kepemilikan == "Pusat":
					ste_log.buat_je_di = "Pusat"

				if asset_doc.server_kepemilikan == "Cabang":
					ste_log.buat_je_di = "Cabang"
					ste_log.cabang = cabang

				ste_log.data = frappe.as_json(je_baru1)
				ste_log.company = asset_doc.company
				ste_log.submit()

				row.detil_je_log = ste_log.name
				row.db_update()

				idx = cint(row.finance_book_id)
				finance_books = asset_doc.get('finance_books')[idx - 1]
				finance_books.value_after_depreciation -= row.depreciation_amount
				finance_books.db_update()

		custom_set_status(asset_doc)

		total_depreciation = 0
		for row_schedule in asset_doc.schedules:
			if row_schedule.detil_je_log:
				total_depreciation += row_schedule.depreciation_amount

		asset_doc.accumulated_depreciation_amount = total_depreciation
		asset_doc.current_asset_amount = asset_doc.gross_purchase_amount - total_depreciation - asset_doc.opening_accumulated_depreciation
		asset_doc.db_update()

		frappe.db.commit()

@frappe.whitelist()
def get_item_asset_detail(item_code):
	return frappe.db.sql(""" 
		SELECT 

		ti.asset_category,
		tac.fixed_asset_account, 
		tac.accumulated_depreciation_account, 
		tac.depreciation_expense_account 

		FROM `tabItem` ti 
		LEFT JOIN `tabAsset Category Account` tac ON ti.asset_category = tac.parent
		WHERE ti.item_code = "{}" """.format(item_code))


