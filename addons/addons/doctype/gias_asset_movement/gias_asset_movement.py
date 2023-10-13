# Copyright (c) 2021, das and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import math

@frappe.whitelist()
def get_accu(asset,posting_date):
	return frappe.db.sql(""" SELECT sum(ds.depreciation_amount), tas.gross_purchase_amount
		FROM `tabDepreciation Schedule` ds JOIN `tabAsset` tas on ds.parent = tas.name  
		where ds.schedule_date <= "{}" and tas.name = "{}"
		""".format(posting_date, asset))


@frappe.whitelist()
def debug_submit_by_name(gmm):
	self = frappe.get_doc("GIAS Asset Movement",gmm)
	if self.moving_type == "Move":
		asset_doc = frappe.get_doc("Asset", self.gias_asset)
		company_doc = frappe.get_doc("Company", asset_doc.company)
		
		# JE 1
		branch = "Jakarta"
		cabang = ""
		if asset_doc.cabang and asset_doc.server_kepemilikan == "Cabang":
			cabang_doc = frappe.get_doc("List Company GIAS", asset_doc.cabang)
			cabang = asset_doc.cabang
			branch = cabang_doc.accounting_dimension

		print("MEMBUAT JE")
		je_baru1 = frappe.new_doc("Journal Entry")
		je_baru1.posting_date = self.posting_date #frappe.utils.today()
		je_baru1.tax_or_non_tax = asset_doc.tax_or_non_tax
		je_baru1.user_remark = "Asset Movement From HO. {} - {} - {}".format(self.name,self.gias_asset, self.moving_type)
		je_baru1.remark = "Asset Movement From HO. {} - {} - {}".format(self.name,self.gias_asset, self.moving_type)
		je_baru1.gias_asset_movement = self.name
		je_baru1.total_debit = self.gross_purchase_amount
		je_baru1.total_credit = self.gross_purchase_amount

		je_baru1.voucher_type = "Journal Entry"
		gp = frappe.utils.flt(self.gross_purchase_amount,2)
		aca = frappe.utils.flt(self.accumulated_depreciation_amount,2)
		total = 0

		baris_baru = {
			"account" : self.rk_account,
			"debit": gp - aca,
			"debit_in_account_currency": gp - aca,
			"branch": branch,
			"cost_center" : company_doc.cost_center
		}
		if gp - aca != 0:
			je_baru1.append("accounts", baris_baru)

		baris_baru = {
			"account" : self.accumulated_depreciation_account,
			"debit": aca,
			"debit_in_account_currency": aca,
			"branch": branch,
			"cost_center" : company_doc.cost_center
		}
		if aca != 0:
			je_baru1.append("accounts", baris_baru)

		baris_baru = {
			"account" : self.fixed_asset_account,
			"credit": gp,
			"credit_in_account_currency": gp,
			"branch": branch,
			"cost_center" : company_doc.cost_center
		}
		if gp != 0:
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
		
		# JE 2
		branch = "Jakarta"
		cabang = ""
		if self.target_cabang and self.target == "Cabang":
			cabang_doc = frappe.get_doc("List Company GIAS", self.target_cabang)
			cabang = self.target_cabang
			branch = cabang_doc.accounting_dimension

		print("MEMBUAT JE")
		je_baru1 = frappe.new_doc("Journal Entry")
		je_baru1.posting_date = self.posting_date #frappe.utils.today()
		je_baru1.tax_or_non_tax = asset_doc.tax_or_non_tax
		je_baru1.user_remark = "Asset Movement From HO. {} - {} - {}".format(self.name,self.gias_asset, self.moving_type)
		je_baru1.remark = "Asset Movement From HO. {} - {} - {}".format(self.name,self.gias_asset, self.moving_type)
		je_baru1.gias_asset_movement = self.name
		je_baru1.total_debit = self.current_asset_amount
		je_baru1.total_credit = self.current_asset_amount

		je_baru1.voucher_type = "Journal Entry"
		total = 0

		gp = frappe.utils.flt(self.gross_purchase_amount,2)
		aca = frappe.utils.flt(self.accumulated_depreciation_amount,2)
		baris_baru = {
			"account" : self.rk_account,
			"credit": gp - aca,
			"credit_in_account_currency": gp - aca,
			"branch": branch,
			"cost_center" : company_doc.cost_center
		}
		if gp - aca != 0:
			je_baru1.append("accounts", baris_baru)


		baris_baru = {
			"account" : self.accumulated_depreciation_account,
			"credit": aca,
			"credit_in_account_currency": aca,
			"branch": branch,
			"cost_center" : company_doc.cost_center
		}
		if aca != 0:
			je_baru1.append("accounts", baris_baru)

		
		baris_baru = {
			"account" : self.fixed_asset_account,
			"debit": gp,
			"debit_in_account_currency": gp,
			"branch": branch,
			"cost_center" : company_doc.cost_center
		}
		if gp != 0:
			je_baru1.append("accounts", baris_baru)

		print("JE yang terbuat : {}".format(frappe.as_json(je_baru1)))

		ste_log = frappe.new_doc("JE Log")
		ste_log.nama_dokumen = asset_doc.name
		ste_log.tipe_dokumen = "Submit"
		if self.target == "Pusat":
			ste_log.buat_je_di = "Pusat"

		if self.target == "Cabang":
			ste_log.buat_je_di = "Cabang"
			ste_log.cabang = self.target_cabang

		ste_log.data = frappe.as_json(je_baru1)
		ste_log.company = asset_doc.company
		
		asset_doc.server_kepemilikan = self.target
		asset_doc.cabang = cabang

		for row in asset_doc.schedules:
			if not row.detil_je_log:
				if asset_doc.server_kepemilikan == "Pusat":
					row.list_company_gias = frappe.get_doc("Company", asset_doc.company).nama_cabang
					row.db_update()
				else:
					row.list_company_gias = asset_doc.cabang
					row.db_update()

			elif row.detil_je_log and frappe.utils.getdate(self.posting_date) < frappe.utils.getdate(row.schedule_date):
				simpan_untuk_dicancel = row.detil_je_log
				je_log_doc = frappe.get_doc("JE Log",simpan_untuk_dicancel)
				row.detil_je_log = ""
				row.list_company_gias = cabang
				row.db_update()


				ste_log = frappe.new_doc("JE Log")
				ste_log.nama_dokumen = self.name
				ste_log.tipe_dokumen = "Cancel"
				ste_log.je_log_yang_dicancel = je_log_doc.name
				ste_log.buat_je_di = "Cabang"
				ste_log.cabang = je_log_doc.cabang
				ste_log.company = self.company
				# ste_log.submit()

		asset_doc.db_update()
		frappe.db.commit()

@frappe.whitelist()
def debug_submit():
	self = frappe.get_doc("GIAS Asset Movement","ASMV-GIAS-HO-1-23-04-00005")
	if self.moving_type == "Move":
		asset_doc = frappe.get_doc("Asset", self.gias_asset)
		company_doc = frappe.get_doc("Company", asset_doc.company)
		
		# JE 1
		branch = "Jakarta"
		cabang = ""
		if asset_doc.cabang and asset_doc.server_kepemilikan == "Cabang":
			cabang_doc = frappe.get_doc("List Company GIAS", asset_doc.cabang)
			cabang = asset_doc.cabang
			branch = cabang_doc.accounting_dimension

		print("MEMBUAT JE")
		je_baru1 = frappe.new_doc("Journal Entry")
		je_baru1.posting_date = self.posting_date #frappe.utils.today()
		je_baru1.tax_or_non_tax = asset_doc.tax_or_non_tax
		je_baru1.user_remark = "Asset Movement From HO. {} - {} - {}".format(self.name,self.gias_asset, self.moving_type)
		je_baru1.remark = "Asset Movement From HO. {} - {} - {}".format(self.name,self.gias_asset, self.moving_type)
		je_baru1.gias_asset_movement = self.name
		je_baru1.total_debit = self.gross_purchase_amount
		je_baru1.total_credit = self.gross_purchase_amount

		je_baru1.voucher_type = "Journal Entry"
		gp = frappe.utils.flt(self.gross_purchase_amount,2)
		aca = frappe.utils.flt(self.accumulated_depreciation_amount,2)
		total = 0

		baris_baru = {
			"account" : self.rk_account,
			"debit": gp - aca,
			"debit_in_account_currency": gp - aca,
			"branch": branch,
			"cost_center" : company_doc.cost_center
		}
		if gp - aca != 0:
			je_baru1.append("accounts", baris_baru)

		baris_baru = {
			"account" : self.accumulated_depreciation_account,
			"debit": aca,
			"debit_in_account_currency": aca,
			"branch": branch,
			"cost_center" : company_doc.cost_center
		}
		if aca != 0:
			je_baru1.append("accounts", baris_baru)

		baris_baru = {
			"account" : self.fixed_asset_account,
			"credit": gp,
			"credit_in_account_currency": gp,
			"branch": branch,
			"cost_center" : company_doc.cost_center
		}
		if gp != 0:
			je_baru1.append("accounts", baris_baru)

		print("JE yang terbuat : {}".format(frappe.as_json(je_baru1)))

		ste_log = frappe.new_doc("JE Log")
		ste_log.nama_dokumen = asset_doc.name
		ste_log.tipe_dokumen = "Submit"
		if self.lokasi_kepemilikan == "Pusat":
			ste_log.buat_je_di = "Pusat"

		elif self.lokasi_kepemilikan == "Cabang":
			ste_log.buat_je_di = "Cabang"
			ste_log.cabang = self.lokasi_cabang

		ste_log.data = frappe.as_json(je_baru1)
		ste_log.company = asset_doc.company
		
		# JE 2
		branch = "Jakarta"
		cabang = ""
		if self.target_cabang and self.target == "Cabang":
			cabang_doc = frappe.get_doc("List Company GIAS", self.target_cabang)
			cabang = self.target_cabang
			branch = cabang_doc.accounting_dimension

		print("MEMBUAT JE")
		je_baru1 = frappe.new_doc("Journal Entry")
		je_baru1.posting_date = self.posting_date #frappe.utils.today()
		je_baru1.tax_or_non_tax = asset_doc.tax_or_non_tax
		je_baru1.user_remark = "Asset Movement From HO. {} - {} - {}".format(self.name,self.gias_asset, self.moving_type)
		je_baru1.remark = "Asset Movement From HO. {} - {} - {}".format(self.name,self.gias_asset, self.moving_type)
		je_baru1.gias_asset_movement = self.name
		je_baru1.total_debit = self.current_asset_amount
		je_baru1.total_credit = self.current_asset_amount

		je_baru1.voucher_type = "Journal Entry"
		total = 0

		gp = frappe.utils.flt(self.gross_purchase_amount,2)
		aca = frappe.utils.flt(self.accumulated_depreciation_amount,2)
		baris_baru = {
			"account" : self.rk_account,
			"credit": gp - aca,
			"credit_in_account_currency": gp - aca,
			"branch": branch,
			"cost_center" : company_doc.cost_center
		}
		if gp - aca != 0:
			je_baru1.append("accounts", baris_baru)


		baris_baru = {
			"account" : self.accumulated_depreciation_account,
			"credit": aca,
			"credit_in_account_currency": aca,
			"branch": branch,
			"cost_center" : company_doc.cost_center
		}
		if aca != 0:
			je_baru1.append("accounts", baris_baru)

		
		baris_baru = {
			"account" : self.fixed_asset_account,
			"debit": gp,
			"debit_in_account_currency": gp,
			"branch": branch,
			"cost_center" : company_doc.cost_center
		}
		if gp != 0:
			je_baru1.append("accounts", baris_baru)

		print("JE yang terbuat : {}".format(frappe.as_json(je_baru1)))

		ste_log = frappe.new_doc("JE Log")
		ste_log.nama_dokumen = asset_doc.name
		ste_log.tipe_dokumen = "Submit"
		if self.target == "Pusat":
			ste_log.buat_je_di = "Pusat"

		if self.target == "Cabang":
			ste_log.buat_je_di = "Cabang"
			ste_log.cabang = self.target_cabang

		ste_log.data = frappe.as_json(je_baru1)
		ste_log.company = asset_doc.company
		
		asset_doc.server_kepemilikan = self.target
		asset_doc.cabang = cabang

		for row in asset_doc.schedules:
			if not row.detil_je_log:
				if asset_doc.server_kepemilikan == "Pusat":
					row.list_company_gias = frappe.get_doc("Company", asset_doc.company).nama_cabang
					row.db_update()
				else:
					row.list_company_gias = asset_doc.cabang
					row.db_update()

			elif row.detil_je_log and frappe.utils.getdate(self.posting_date) < frappe.utils.getdate(row.schedule_date):
				simpan_untuk_dicancel = row.detil_je_log
				je_log_doc = frappe.get_doc("JE Log",simpan_untuk_dicancel)
				row.detil_je_log = ""
				row.list_company_gias = cabang
				row.db_update()


				ste_log = frappe.new_doc("JE Log")
				ste_log.nama_dokumen = self.name
				ste_log.tipe_dokumen = "Cancel"
				ste_log.je_log_yang_dicancel = je_log_doc.name
				ste_log.buat_je_di = "Cabang"
				ste_log.cabang = je_log_doc.cabang
				ste_log.company = self.company
				# ste_log.submit()

		asset_doc.db_update()
		frappe.db.commit()

		


class GIASAssetMovement(Document):
	# def on_submit(self):
	# 	debug_submit_by_name(self.name)

	def validate(self):
		if self.moving_type == "Move":
			if self.lokasi_kepemilikan == "Pusat":
				if self.target == "Pusat":
					frappe.throw("Moving Asset cannot be in the same location.")
			else:
				if self.lokasi_cabang == self.target_cabang:
					frappe.throw("Moving Asset cannot be in the same location.")	 

		self.accumulated_depreciation_amount = math.ceil(self.accumulated_depreciation_amount)

	def before_submit(self):
		if self.moving_type == "Scrap":
			asset_doc = frappe.get_doc("Asset", self.gias_asset)
			company_doc = frappe.get_doc("Company", asset_doc.company)
			reason = self.reason
			branch = "Jakarta"
			cabang = ""
			if asset_doc.cabang and asset_doc.server_kepemilikan == "Cabang":
				cabang_doc = frappe.get_doc("List Company GIAS", asset_doc.cabang)
				cabang = asset_doc.cabang
				branch = cabang_doc.accounting_dimension

			print("MEMBUAT JE")
			je_baru1 = frappe.new_doc("Journal Entry")
			je_baru1.posting_date = self.posting_date #frappe.utils.today()
			je_baru1.tax_or_non_tax = asset_doc.tax_or_non_tax
			je_baru1.user_remark = "Reason : {} ".format(self.reason)
			je_baru1.remark = "Asset Movement From HO. {} - {} - {}".format(self.name,self.gias_asset, self.moving_type)
			je_baru1.gias_asset_movement = self.name

			je_baru1.total_debit = self.current_asset_amount
			je_baru1.total_credit = self.current_asset_amount

			je_baru1.voucher_type = "Journal Entry"
			total = 0

			gp = frappe.utils.flt(self.gross_purchase_amount,2)
			aca = frappe.utils.flt(self.accumulated_depreciation_amount,2)

			baris_baru = {
				"account" : self.scrap_account,
				"debit": gp-aca,
				"debit_in_account_currency": gp-aca,
				"branch": branch,
				"cost_center" : company_doc.cost_center
			}
			if gp-aca != 0:
				je_baru1.append("accounts", baris_baru)

			baris_baru = {
				"account" : self.accumulated_depreciation_account,
				"debit": aca,
				"debit_in_account_currency": aca,
				"branch": branch,
				"cost_center" : company_doc.cost_center
			}
			if asset_doc.depreciation_amount != 0:
				je_baru1.append("accounts", baris_baru)

			baris_baru = {
				"account" : self.fixed_asset_account,
				"credit": gp,
				"credit_in_account_currency": gp,
				"branch": branch,
				"cost_center" : company_doc.cost_center
			}
			if asset_doc.gross_purchase_amount != 0:
				je_baru1.append("accounts", baris_baru)

			print("JE yang terbuat : {}".format(frappe.as_json(je_baru1)))

			ste_log = frappe.new_doc("JE Log")
			ste_log.nama_dokumen = asset_doc.name
			ste_log.tipe_dokumen = "Submit"
			if self.lokasi_kepemilikan == "Pusat":
				ste_log.buat_je_di = "Pusat"

			elif self.lokasi_kepemilikan == "Cabang":
				ste_log.buat_je_di = "Cabang"
				ste_log.cabang = self.lokasi_cabang

			ste_log.data = frappe.as_json(je_baru1)
			ste_log.company = asset_doc.company
			ste_log.submit()

			asset_doc.on_depreciation = 0
			asset_doc.current_asset_amount = 0
			asset_doc.status_movement = "Write Off"
			asset_doc.tanggal_scrap = self.posting_date
			asset_doc.db_update()

			for row in asset_doc.schedules:
				if row.detil_je_log and frappe.utils.getdate(self.posting_date) < frappe.utils.getdate(row.schedule_date):
					simpan_untuk_dicancel = row.detil_je_log
					je_log_doc = frappe.get_doc("JE Log",simpan_untuk_dicancel)
					row.detil_je_log = ""
					row.db_update()

					ste_log = frappe.new_doc("JE Log")
					ste_log.nama_dokumen = self.name
					ste_log.tipe_dokumen = "Cancel"
					ste_log.je_log_yang_dicancel = je_log_doc.name
					ste_log.buat_je_di = "Cabang"
					ste_log.cabang = je_log_doc.cabang
					ste_log.company = self.company
					ste_log.submit()

			asset_doc.db_update()
			frappe.db.commit()

		elif self.moving_type == "Move":
			asset_doc = frappe.get_doc("Asset", self.gias_asset)
			company_doc = frappe.get_doc("Company", asset_doc.company)
			
			# JE 1
			branch = "Jakarta"
			cabang = ""
			if self.lokasi_cabang and self.lokasi_kepemilikan == "Cabang":
				cabang_doc = frappe.get_doc("List Company GIAS", self.lokasi_cabang)
				cabang = self.lokasi_cabang
				branch = cabang_doc.accounting_dimension

			print("MEMBUAT JE")
			je_baru1 = frappe.new_doc("Journal Entry")
			je_baru1.posting_date = self.posting_date #frappe.utils.today()
			je_baru1.tax_or_non_tax = asset_doc.tax_or_non_tax
			je_baru1.user_remark = "Asset Movement From HO. {} - {} - {}".format(self.name,self.gias_asset, self.moving_type)
			je_baru1.remark = "Asset Movement From HO. {} - {} - {}".format(self.name,self.gias_asset, self.moving_type)
			je_baru1.gias_asset_movement = self.name
			je_baru1.total_debit = self.gross_purchase_amount
			je_baru1.total_credit = self.gross_purchase_amount

			je_baru1.voucher_type = "Journal Entry"
			gp = frappe.utils.flt(self.gross_purchase_amount,2)
			aca = frappe.utils.flt(self.accumulated_depreciation_amount,2)
			total = 0

			baris_baru = {
				"account" : self.rk_account,
				"debit": gp - aca,
				"debit_in_account_currency": gp - aca,
				"branch": branch,
				"cost_center" : company_doc.cost_center
			}
			if gp - aca != 0:
				je_baru1.append("accounts", baris_baru)

			baris_baru = {
				"account" : self.accumulated_depreciation_account,
				"debit": aca,
				"debit_in_account_currency": aca,
				"branch": branch,
				"cost_center" : company_doc.cost_center
			}
			if aca != 0:
				je_baru1.append("accounts", baris_baru)

			baris_baru = {
				"account" : self.fixed_asset_account,
				"credit": gp,
				"credit_in_account_currency": gp,
				"branch": branch,
				"cost_center" : company_doc.cost_center
			}
			if gp != 0:
				je_baru1.append("accounts", baris_baru)

			print("JE yang terbuat : {}".format(frappe.as_json(je_baru1)))

			ste_log = frappe.new_doc("JE Log")
			ste_log.nama_dokumen = asset_doc.name
			ste_log.tipe_dokumen = "Submit"
			if self.lokasi_kepemilikan == "Pusat":
				ste_log.buat_je_di = "Pusat"

			elif self.lokasi_kepemilikan == "Cabang":
				ste_log.buat_je_di = "Cabang"
				ste_log.cabang = self.lokasi_cabang

			ste_log.data = frappe.as_json(je_baru1)
			ste_log.company = asset_doc.company
			ste_log.submit()

			# JE 2
			branch = "Jakarta"
			cabang = ""
			if self.target_cabang and self.target == "Cabang":
				cabang_doc = frappe.get_doc("List Company GIAS", self.target_cabang)
				cabang = self.target_cabang
				branch = cabang_doc.accounting_dimension

			print("MEMBUAT JE")
			je_baru1 = frappe.new_doc("Journal Entry")
			je_baru1.posting_date = self.posting_date #frappe.utils.today()
			je_baru1.tax_or_non_tax = asset_doc.tax_or_non_tax
			je_baru1.user_remark = "Asset Movement From HO. {} - {} - {}".format(self.name,self.gias_asset, self.moving_type)
			je_baru1.remark = "Asset Movement From HO. {} - {} - {}".format(self.name,self.gias_asset, self.moving_type)
			je_baru1.gias_asset_movement = self.name
			je_baru1.total_debit = self.current_asset_amount
			je_baru1.total_credit = self.current_asset_amount

			je_baru1.voucher_type = "Journal Entry"
			total = 0

			gp = frappe.utils.flt(self.gross_purchase_amount,2)
			aca = frappe.utils.flt(self.accumulated_depreciation_amount,2)
			baris_baru = {
				"account" : self.rk_account,
				"credit": gp - aca,
				"credit_in_account_currency": gp - aca,
				"branch": branch,
				"cost_center" : company_doc.cost_center
			}
			if gp - aca != 0:
				je_baru1.append("accounts", baris_baru)


			baris_baru = {
				"account" : self.accumulated_depreciation_account,
				"credit": aca,
				"credit_in_account_currency": aca,
				"branch": branch,
				"cost_center" : company_doc.cost_center
			}
			if aca != 0:
				je_baru1.append("accounts", baris_baru)

			
			baris_baru = {
				"account" : self.fixed_asset_account,
				"debit": gp,
				"debit_in_account_currency": gp,
				"branch": branch,
				"cost_center" : company_doc.cost_center
			}
			if gp != 0:
				je_baru1.append("accounts", baris_baru)

			print("JE yang terbuat : {}".format(frappe.as_json(je_baru1)))

			ste_log = frappe.new_doc("JE Log")
			ste_log.nama_dokumen = asset_doc.name
			ste_log.tipe_dokumen = "Submit"
			if self.target == "Pusat":
				ste_log.buat_je_di = "Pusat"

			elif self.target == "Cabang":
				ste_log.buat_je_di = "Cabang"
				ste_log.cabang = self.target_cabang

			ste_log.data = frappe.as_json(je_baru1)
			ste_log.company = asset_doc.company
			ste_log.submit()

			asset_doc.server_kepemilikan = self.target
			asset_doc.cabang = cabang

			for row in asset_doc.schedules:
				if not row.detil_je_log:
					if asset_doc.server_kepemilikan == "Pusat":
						row.list_company_gias = frappe.get_doc("Company", asset_doc.company).nama_cabang
						row.db_update()
					else:
						row.list_company_gias = asset_doc.cabang
						row.db_update()

				elif row.detil_je_log and frappe.utils.getdate(self.posting_date) < frappe.utils.getdate(row.schedule_date):
					simpan_untuk_dicancel = row.detil_je_log
					je_log_doc = frappe.get_doc("JE Log",simpan_untuk_dicancel)
					row.detil_je_log = ""
					row.list_company_gias = cabang
					row.db_update()


					ste_log = frappe.new_doc("JE Log")
					ste_log.nama_dokumen = self.name
					ste_log.tipe_dokumen = "Cancel"
					ste_log.je_log_yang_dicancel = je_log_doc.name

					if self.lokasi_kepemilikan == "Pusat":
						ste_log.buat_je_di = "Pusat"
					else:
						ste_log.buat_je_di = "Cabang"
						ste_log.cabang = je_log_doc.cabang
						
					ste_log.company = self.company
					ste_log.submit()

			asset_doc.db_update()
			# frappe.db.commit()

	def before_cancel(self):
		if self.moving_type == "Move":
			asset_doc = frappe.get_doc("Asset", self.gias_asset)
			company_doc = frappe.get_doc("Company", asset_doc.company)
			asset_doc.server_kepemilikan = self.lokasi_kepemilikan
			asset_doc.cabang = self.lokasi_cabang

			for row in asset_doc.schedules:
				if not row.detil_je_log:

					row.list_company_gias = self.lokasi_cabang
					row.db_update()



@frappe.whitelist()
def debug_submit_asset_movement():
	self = frappe.get_doc("GIAS Asset Movement","ASMV-GIAS-HO-1-23-07-00001")
	asset_doc = frappe.get_doc("Asset", self.gias_asset)
	company_doc = frappe.get_doc("Company", asset_doc.company)
	
	# JE 1
	branch = "Jakarta"
	cabang = ""
	if self.lokasi_cabang and self.lokasi_kepemilikan == "Cabang":
		cabang_doc = frappe.get_doc("List Company GIAS", self.lokasi_cabang)
		cabang = self.lokasi_cabang
		branch = cabang_doc.accounting_dimension

	print("MEMBUAT JE")
	je_baru1 = frappe.new_doc("Journal Entry")
	je_baru1.posting_date = self.posting_date #frappe.utils.today()
	je_baru1.tax_or_non_tax = asset_doc.tax_or_non_tax
	je_baru1.user_remark = "Asset Movement From HO. {} - {} - {}".format(self.name,self.gias_asset, self.moving_type)
	je_baru1.remark = "Asset Movement From HO. {} - {} - {}".format(self.name,self.gias_asset, self.moving_type)
	je_baru1.gias_asset_movement = self.name
	je_baru1.total_debit = self.gross_purchase_amount
	je_baru1.total_credit = self.gross_purchase_amount

	je_baru1.voucher_type = "Journal Entry"
	gp = frappe.utils.flt(self.gross_purchase_amount,2)
	aca = frappe.utils.flt(self.accumulated_depreciation_amount,2)
	total = 0

	baris_baru = {
		"account" : self.rk_account,
		"debit": gp - aca,
		"debit_in_account_currency": gp - aca,
		"branch": branch,
		"cost_center" : company_doc.cost_center
	}
	if gp - aca != 0:
		je_baru1.append("accounts", baris_baru)

	baris_baru = {
		"account" : self.accumulated_depreciation_account,
		"debit": aca,
		"debit_in_account_currency": aca,
		"branch": branch,
		"cost_center" : company_doc.cost_center
	}
	if aca != 0:
		je_baru1.append("accounts", baris_baru)

	baris_baru = {
		"account" : self.fixed_asset_account,
		"credit": gp,
		"credit_in_account_currency": gp,
		"branch": branch,
		"cost_center" : company_doc.cost_center
	}
	if gp != 0:
		je_baru1.append("accounts", baris_baru)

	print("JE yang terbuat : {}".format(frappe.as_json(je_baru1)))

	ste_log = frappe.new_doc("JE Log")
	ste_log.nama_dokumen = asset_doc.name
	ste_log.tipe_dokumen = "Submit"
	if self.lokasi_kepemilikan == "Pusat":
		ste_log.buat_je_di = "Pusat"

	elif self.lokasi_kepemilikan == "Cabang":
		ste_log.buat_je_di = "Cabang"
		ste_log.cabang = self.lokasi_cabang

	ste_log.data = frappe.as_json(je_baru1)
	ste_log.company = asset_doc.company
	print(str(ste_log))
	# ste_log.submit()

	# JE 2
	branch = "Jakarta"
	cabang = ""
	if self.target_cabang and self.target == "Cabang":
		cabang_doc = frappe.get_doc("List Company GIAS", self.target_cabang)
		cabang = self.target_cabang
		branch = cabang_doc.accounting_dimension

	print("MEMBUAT JE")
	je_baru1 = frappe.new_doc("Journal Entry")
	je_baru1.posting_date = self.posting_date #frappe.utils.today()
	je_baru1.tax_or_non_tax = asset_doc.tax_or_non_tax
	je_baru1.user_remark = "Asset Movement From HO. {} - {} - {}".format(self.name,self.gias_asset, self.moving_type)
	je_baru1.remark = "Asset Movement From HO. {} - {} - {}".format(self.name,self.gias_asset, self.moving_type)
	je_baru1.gias_asset_movement = self.name
	je_baru1.total_debit = self.current_asset_amount
	je_baru1.total_credit = self.current_asset_amount

	je_baru1.voucher_type = "Journal Entry"
	total = 0

	gp = frappe.utils.flt(self.gross_purchase_amount,2)
	aca = frappe.utils.flt(self.accumulated_depreciation_amount,2)
	baris_baru = {
		"account" : self.rk_account,
		"credit": gp - aca,
		"credit_in_account_currency": gp - aca,
		"branch": branch,
		"cost_center" : company_doc.cost_center
	}
	if gp - aca != 0:
		je_baru1.append("accounts", baris_baru)


	baris_baru = {
		"account" : self.accumulated_depreciation_account,
		"credit": aca,
		"credit_in_account_currency": aca,
		"branch": branch,
		"cost_center" : company_doc.cost_center
	}
	if aca != 0:
		je_baru1.append("accounts", baris_baru)

	
	baris_baru = {
		"account" : self.fixed_asset_account,
		"debit": gp,
		"debit_in_account_currency": gp,
		"branch": branch,
		"cost_center" : company_doc.cost_center
	}
	if gp != 0:
		je_baru1.append("accounts", baris_baru)

	print("JE yang terbuat : {}".format(frappe.as_json(je_baru1)))

	ste_log = frappe.new_doc("JE Log")
	ste_log.nama_dokumen = asset_doc.name
	ste_log.tipe_dokumen = "Submit"
	if self.target == "Pusat":
		ste_log.buat_je_di = "Pusat"

	elif self.target == "Cabang":
		ste_log.buat_je_di = "Cabang"
		ste_log.cabang = self.target_cabang

	ste_log.data = frappe.as_json(je_baru1)
	ste_log.company = asset_doc.company
	print(str(ste_log))
	# ste_log.submit()

	asset_doc.server_kepemilikan = self.target
	asset_doc.cabang = cabang

	for row in asset_doc.schedules:
		if not row.detil_je_log:
			if asset_doc.server_kepemilikan == "Pusat":
				row.list_company_gias = frappe.get_doc("Company", asset_doc.company).nama_cabang
				row.db_update()
			else:
				row.list_company_gias = asset_doc.cabang
				row.db_update()

		elif row.detil_je_log and frappe.utils.getdate(self.posting_date) < frappe.utils.getdate(row.schedule_date):
			simpan_untuk_dicancel = row.detil_je_log
			je_log_doc = frappe.get_doc("JE Log",simpan_untuk_dicancel)
			row.detil_je_log = ""
			row.list_company_gias = cabang
			row.db_update()


			ste_log = frappe.new_doc("JE Log")
			ste_log.nama_dokumen = self.name
			ste_log.tipe_dokumen = "Cancel"
			ste_log.je_log_yang_dicancel = je_log_doc.name

			if self.lokasi_kepemilikan == "Pusat":
				ste_log.buat_je_di = "Pusat"
			else:
				ste_log.buat_je_di = "Cabang"
				ste_log.cabang = je_log_doc.cabang
				
			ste_log.company = self.company
			ste_log.submit()

	asset_doc.db_update()