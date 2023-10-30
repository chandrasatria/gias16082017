import frappe,erpnext
from frappe.model.mapper import get_mapped_doc
from erpnext.stock.doctype.item.item import get_item_defaults
from frappe.utils import cstr, flt, getdate, new_line_sep, nowdate, add_days, get_link_to_form, cint
from frappe.model.document import Document
from frappe.event_streaming.doctype.event_producer.event_producer import get_producer_site,get_config,get_updates,get_mapped_update,sync
import json
from frappe import msgprint, _

from frappe.utils.background_jobs import get_jobs
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from erpnext.controllers.stock_controller import StockController
from erpnext.accounts.general_ledger import make_gl_entries, make_reverse_gl_entries, process_gl_map, ClosedAccountingPeriod, merge_similar_entries
from erpnext.stock import get_warehouse_account_map
from frappe.model.naming import make_autoname, revert_series_if_last

from frappe.utils.data import get_url, get_link_to_form
import datetime

from six import iteritems, itervalues, string_types

@frappe.whitelist()
def pasang_mr_untuk_not_ready(self,method):
	list_mr_kompilasi = []
	if self.purpose == "Material Issue":
		for row in self.items:
			item = row.item_code
			
			if row.material_request not in list_mr_kompilasi:
				if row.material_request:
					list_mr_kompilasi.append(row.material_request)

		for row in list_mr_kompilasi:
			
			mr_doc = frappe.get_doc("Material Request",row)
			nomor_mr = row
			for row_mr in mr_doc.items:
				if row_mr.cabang_material_request:

					cabang_mr_doc = frappe.get_doc("Material Request",row_mr.cabang_material_request)
					for row_mr_cabang in cabang_mr_doc.items:
						item_code = row_mr_cabang.item_code
						get_issued = frappe.db.sql(""" SELECT
							SUM(IFNULL(sted.`transfer_qty`,0))
							FROM `tabStock Entry Detail` sted
							JOIN `tabStock Entry` ste ON ste.name = sted.parent
							WHERE sted.material_request = "{}"
							AND sted.item_code = "{}"
							AND sted.docstatus = 1
							AND ste.purpose = "Material Issue" """.format(nomor_mr,item_code))
						if len(get_issued) > 0:
							
							row_mr_cabang.qty_issued = frappe.utils.flt(get_issued[0][0])
							row_mr_cabang.db_update()


@frappe.whitelist()
def pasang_mr_untuk_not_ready_debug_start():
	li = frappe.db.sql(""" SELECT
		sted.`parent`
		FROM `tabStock Entry Detail` sted
		JOIN `tabStock Entry` ste ON ste.name = sted.parent
		WHERE sted.material_request = "MR-H-HO-1-23-08-00146"

		AND sted.docstatus = 1
		AND ste.purpose = "Material Issue"
		GROUP BY sted.`parent` 
		LIMIT 1
		""")
	for row in li:
		pasang_mr_untuk_not_ready_debug(row[0])

@frappe.whitelist()
def pasang_mr_untuk_not_ready_debug(nomor_mr):
	self = frappe.get_doc("Stock Entry",nomor_mr)
	list_mr_kompilasi = []
	
	for row in self.items:
		item = row.item_code
		
		if row.material_request not in list_mr_kompilasi:
			list_mr_kompilasi.append(row.material_request)

	for row in list_mr_kompilasi:
		
		mr_doc = frappe.get_doc("Material Request",row)
		nomor_mr = row
		for row_mr in mr_doc.items:
			if row_mr.cabang_material_request:

				cabang_mr_doc = frappe.get_doc("Material Request",row_mr.cabang_material_request)
				for row_mr_cabang in cabang_mr_doc.items:
					item_code = row_mr_cabang.item_code
					get_issued = frappe.db.sql(""" SELECT
						SUM(IFNULL(sted.`transfer_qty`,0))
						FROM `tabStock Entry Detail` sted
						JOIN `tabStock Entry` ste ON ste.name = sted.parent
						WHERE sted.material_request = "{}"
						AND sted.item_code = "{}"
						AND sted.docstatus = 1
						AND ste.purpose = "Material Issue" """.format(nomor_mr,item_code))
					if len(get_issued) > 0:
						
						row_mr_cabang.qty_issued = frappe.utils.flt(get_issued[0][0])
						row_mr_cabang.db_update()
				



@frappe.whitelist()
def pasang_persen_transfer(self,method):
	for row in self.items:
		if row.material_request_item:
			jumlah_issued = frappe.db.sql(""" SELECT SUM(transfer_qty) FROM `tabStock Entry Detail`
				WHERE material_request_item = "{}" and docstatus = 1 """.format(row.material_request_item))

			if len(jumlah_issued) > 0:
				doc = frappe.get_doc("Material Request Item", row.material_request_item)
				doc.qty_issued = jumlah_issued[0][0]
				print("asd")
				doc.db_update()

				parent_doc = frappe.get_doc("Material Request", row.material_request)
				pembagi_atas = 0
				pembagi_bawah = 0
				for row_mr in parent_doc.items:
					pembagi_atas = pembagi_atas + row_mr.qty_issued
					pembagi_bawah = pembagi_bawah + row_mr.stock_qty

				parent_doc.transferred_percentage = pembagi_atas / pembagi_bawah * 100
				# frappe.throw(str(pembagi_atas / pembagi_bawah * 100))
				parent_doc.db_update()
				
@frappe.whitelist()
def onload_transfer(self,method):
	for row in self.items:
		if row.additional_cost_transfer == 0:
			row.valuation_rate_transfer = row.valuation_rate
			row.db_update()

@frappe.whitelist()
def validate_ste_stock(self,method):
	for row in self.items:
		if row.s_warehouse:
			list_ste = frappe.db.sql(""" 
				SELECT qty_after_transaction
				FROM `tabStock Ledger Entry`
				WHERE warehouse = "{}"
				AND item_code = "{}"
				AND TIMESTAMP(posting_date,posting_time) <= TIMESTAMP("{}","{}")
				AND is_cancelled != 1

				ORDER BY TIMESTAMP(posting_date,posting_time) DESC,creation DESC,  NAME DESC 

				LIMIT 1
			""".format(row.s_warehouse, row.item_code, self.posting_date, self.posting_time))

			qty = 0
			if len(list_ste) == 1:
				qty = frappe.utils.flt(list_ste[0][0])

			if frappe.utils.flt(row.transfer_qty) > frappe.utils.flt(qty):
				frappe.throw(""" Qty for item {} in warehouse {} are not enough in posting date {} posting time {} (qty = {}).""".format(row.item_code,row.s_warehouse,self.posting_date,self.posting_time,qty))



@frappe.whitelist()
def reject_document(name):
	ste_doc = frappe.get_doc("Stock Entry",name)
	if ste_doc.docstatus != 0:
		frappe.throw("Document cannot be rejected as is not draft.")
	ste_doc.workflow_state = "Rejected"
	ste_doc.rejected = "Yes"
	ste_doc.db_update()


@frappe.whitelist()
def cancel_period_flag(self,method):
	accounting_periods = frappe.db.sql(""" SELECT
			ap.name as name
		FROM
			`tabAccounting Period` ap, `tabClosed Document` cd
		WHERE
			ap.name = cd.parent
			AND ap.company = %(company)s
			AND cd.closed = 1
			AND cd.document_type = %(voucher_type)s
			AND %(date)s between ap.start_date and ap.end_date
			""", {
				'date': self.posting_date,
				'company': self.company,
				'voucher_type': "Stock Entry"
			}, as_dict=1)

	if accounting_periods:
		frappe.throw(_("You cannot create or cancel any accounting entries with in the closed Accounting Period {0}")
			.format(frappe.bold(accounting_periods[0].name)), ClosedAccountingPeriod)
	self.flags.ignore_links = True

@frappe.whitelist()
def cancel_flag(self,method):
	self.flags.ignore_links = True
	
def custom_check_docstatus_transition(self, docstatus):
	"""Ensures valid `docstatus` transition.
	Valid transitions are (number in brackets is `docstatus`):

	- Save (0) > Save (0)
	- Save (0) > Submit (1)
	- Submit (1) > Submit (1)
	- Submit (1) > Cancel (2)

	"""
	if self.docstatus == "0":
		self.docstatus = 0

	if not self.docstatus:
		self.docstatus = 0
	if docstatus==0:
		if self.docstatus==0:
			self._action = "save"
		elif self.docstatus==1:
			self._action = "submit"
			self.check_permission("submit")
		else:
			raise frappe.DocstatusTransitionError(_("Cannot change docstatus from 0 to 2"))

	elif docstatus==1:
		if self.docstatus==1:
			self._action = "update_after_submit"
			self.check_permission("submit")
		elif self.docstatus==2:
			self._action = "cancel"
			self.check_permission("cancel")
		else:
			raise frappe.DocstatusTransitionError(_("Cannot change docstatus from 1 to 0 {}").format(self.docstatus))

	elif docstatus==2:
		raise frappe.ValidationError(_("Cannot edit cancelled document"))

Document.check_docstatus_transition = custom_check_docstatus_transition

def custom_make_gl_entries2(self, gl_entries=None, from_repost=False):
	if self.docstatus == 2:
		make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

	if cint(erpnext.is_perpetual_inventory_enabled(self.company)):
		warehouse_account = get_warehouse_account_map(self.company)

		if self.docstatus==1:
			if not gl_entries:
				if self.doctype == "Stock Entry":
					gl_entries = custom_get_gl_entries2(self,warehouse_account)
				else:
					gl_entries = self.get_gl_entries(warehouse_account)

			make_gl_entries(gl_entries, from_repost=from_repost)

	elif self.doctype in ['Purchase Receipt', 'Purchase Invoice'] and self.docstatus == 1:
		gl_entries = []
		gl_entries = self.get_asset_gl_entry(gl_entries)
		make_gl_entries(gl_entries, from_repost=from_repost)

def custom_make_gl_entries(self, gl_entries=None, from_repost=False):
	if self.docstatus == 2:
		make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

	if cint(erpnext.is_perpetual_inventory_enabled(self.company)):
		warehouse_account = get_warehouse_account_map(self.company)

		if self.docstatus==1:
			if not gl_entries:
				gl_entries = custom_get_gl_entries(self,warehouse_account)

			make_gl_entries(gl_entries, from_repost=from_repost)

	elif self.doctype in ['Purchase Receipt', 'Purchase Invoice'] and self.docstatus == 1:
		gl_entries = []
		gl_entries = self.get_asset_gl_entry(gl_entries)
		make_gl_entries(gl_entries, from_repost=from_repost)

@frappe.whitelist()
def cek_document_sync(doc,method):

	# if frappe.get_doc("Company", doc.company).server == "Cabang":
	if doc.ste_log:
		for row in doc.items:
			if row.pusat_valuation_rate:
				row.basic_rate = row.pusat_valuation_rate
				row.valuation_rate = flt(flt(row.basic_rate) + (flt(row.additional_cost) / flt(row.transfer_qty)))


	# else:
	# 	if doc.ste_log:
	# 		for row in doc.items:
	# 			if row.valuation_rate_transfer:
	# 				row.basic_rate = row.valuation_rate_transfer
	# 				row.valuation_rate = row.valuation_rate_transfer
@frappe.whitelist()
def set_tonase(doc,method):
	total = 0
	for row in doc.items:
		document_item = frappe.get_doc("Item", row.item_code)
		if document_item.weight_per_unit:
			row.weight_per_stock_qty = document_item.weight_per_unit
			row.total_weight = document_item.weight_per_unit * row.transfer_qty
			total += row.total_weight

	doc.total_tonase = total

@frappe.whitelist()
def debug_repair():
	frappe.flags.repost_gl == True
	list_ste = frappe.db.sql(""" 
		SELECT ste.name
		FROM `tabStock Entry` ste
		
		WHERE ste.name in ("STE-BKL-1-23-06-00010")
		;

		 """)
	for row in list_ste:
		repair_gl_entry("Stock Entry",row[0])
		print(row[0])


@frappe.whitelist()
def debug_repair_gl_entry():
	list_ste = frappe.db.sql(""" SELECT
	ste.name

	FROM `tabStock Entry` ste
	WHERE name IN ("STEI-HO-1-23-06-03458")

	""")

	for row in list_ste:
		
		repair_gl_entry_untuk_ste("Stock Entry",row[0])
		print(row[0])



@frappe.whitelist()
def repair_gl_entry_untuk_ste(doctype,docname):
	doc = frappe.get_doc(doctype,docname)
	doc.auto_assign_to_rk_account = 1
	doc.db_update()
	company_doc = frappe.get_doc("Company",doc.company)

	check = 0
	for row in doc.items:
		row.expense_account = "5001 - HARGA POKOK PENJUALAN - G"
		row.db_update()
		if row.expense_account != "3131 - SALDO AWAL STOCK - G":
			if doc.stock_entry_type == "Material Receipt":
				if row.t_warehouse:
					wh_doc = frappe.get_doc("Warehouse", row.t_warehouse)
					if wh_doc.rk_stock_account_1:
						if row.expense_account != wh_doc.rk_stock_account_1:
							row.expense_account = wh_doc.rk_stock_account_1 
							check = 1
							row.db_update()

	for row in doc.items:
		row.additional_cost_transfer = row.additional_cost
		row.valuation_rate_transfer = row.valuation_rate
		row.db_update()
		
	if company_doc.server == "Cabang":
		if doc.sync_name:
			rk_value = frappe.db.sql(""" 
				SELECT SUM(debit) FROM `db_pusat`.`tabGL Entry` 
				WHERE account = "1168.04 - R/K STOCK - G" and voucher_no = "{}" """.format(doc.sync_name))[0][0]
			doc.rk_value = rk_value
			print(doc.rk_value)
			doc.db_update()


	if doc.stock_entry_type == "Material Receipt" and frappe.utils.flt(doc.rk_value) > 0 :
		StockController.make_gl_entries = custom_make_gl_entries2

	if company_doc.server == "Pusat":
		check = frappe.db.sql(""" SELECT * FROM `tabCustom Field` WhERE name = "Stock Entry-dari_branch" """)
		if len(check) > 0 and doc.purpose == "Material Issue":
			if doc.dari_branch == 1 and doc.stock_entry_type == "Material Issue":
				StockController.make_gl_entries = custom_make_gl_entries	

	repair_gl_entry(doctype,docname)
	from addons.custom_standard.view_ledger_create import create_gl_custom_stock_entry_by_name
	create_gl_custom_stock_entry_by_name(docname,"on_submit")

	# from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import debug_repost
	# debug_repost()

@frappe.whitelist()
def overwrite_on_submit(doc,method):
	company_doc = frappe.get_doc("Company",doc.company)

	if company_doc.server == "Cabang":
		if doc.sync_name:
			doc.rk_value = 0
			rk_value = frappe.db.sql(""" SELECT SUM(debit) FROM `db_pusat`.`tabGL Entry` WHERE account = "1168.04 - R/K STOCK - G" and voucher_no = "{}" """.format(doc.sync_name))
			if rk_value:
				if rk_value[0]:
					if rk_value[0][0]:
						doc.rk_value = rk_value[0][0]
		
	if doc.stock_entry_type == "Material Receipt" and doc.rk_value > 0 and doc.doctype == "Stock Entry":
		StockController.make_gl_entries = custom_make_gl_entries2

	if company_doc.server == "Pusat":
		check = frappe.db.sql(""" SELECT * FROM `tabCustom Field` WhERE name = "Stock Entry-dari_branch" """)
		if len(check) > 0 and doc.purpose == "Material Issue":
			if doc.dari_branch == 1 and doc.stock_entry_type == "Material Issue":
				StockController.make_gl_entries = custom_make_gl_entries

def custom_get_gl_entries2(self, warehouse_account):
	gl_entries = super(StockEntry, self).get_gl_entries(warehouse_account)

	if self.purpose in ("Repack", "Manufacture"):
		total_basic_amount = sum(flt(t.basic_amount) for t in self.get("items") if t.is_finished_item)
	else:
		total_basic_amount = sum(flt(t.basic_amount) for t in self.get("items") if t.t_warehouse)

	divide_based_on = total_basic_amount

	if self.get("additional_costs") and not total_basic_amount:
		# if total_basic_amount is 0, distribute additional charges based on qty
		divide_based_on = sum(item.qty for item in list(self.get("items")))

	item_account_wise_additional_cost = {}

	for t in self.get("additional_costs"):
		for d in self.get("items"):
			if self.purpose in ("Repack", "Manufacture") and not d.is_finished_item:
				continue
			elif not d.t_warehouse:
				continue

			item_account_wise_additional_cost.setdefault((d.item_code, d.name), {})
			item_account_wise_additional_cost[(d.item_code, d.name)].setdefault(t.expense_account, {
				"amount": 0.0,
				"base_amount": 0.0
			})

			multiply_based_on = d.basic_amount if total_basic_amount else d.qty

			item_account_wise_additional_cost[(d.item_code, d.name)][t.expense_account]["amount"] += \
				flt(t.amount * multiply_based_on) / divide_based_on

			item_account_wise_additional_cost[(d.item_code, d.name)][t.expense_account]["base_amount"] += \
				flt(t.base_amount * multiply_based_on) / divide_based_on

	if item_account_wise_additional_cost:
		for d in self.get("items"):
			for account, amount in iteritems(item_account_wise_additional_cost.get((d.item_code, d.name), {})):
				if not amount: continue

				gl_entries.append(self.get_gl_dict({
					"account": account,
					"against": d.expense_account,
					"cost_center": d.cost_center,
					"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
					"credit_in_account_currency": flt(amount["amount"]),
					"credit": flt(amount["base_amount"])
				}, item=d))

				gl_entries.append(self.get_gl_dict({
					"account": d.expense_account,
					"against": account,
					"cost_center": d.cost_center,
					"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
					"credit": -1 * amount['base_amount'] # put it as negative credit instead of debit purposefully
				}, item=d))
	
	precision = self.get_debit_field_precision()
	gl_list = merge_similar_entries(gl_entries, precision)

	rk_account = self.items[0].expense_account

	for row in gl_list:
		if row.account == rk_account:
			if self.rk_value > 0:
				if self.rk_value - row.credit > 0:
					gl_list.append(self.get_gl_dict({
						"account": "8113 - BIAYA LAIN-LAIN - G",
						"against": rk_account,
						"cost_center": self.get("items")[0].cost_center,
						"remarks": ("Adjustment RK Entry for Stock"),
						"debit": self.rk_value - row.credit,
						"debit_in_account_currency": self.rk_value - row.credit
					}))
				else:
					gl_list.append(self.get_gl_dict({
						"account": "8113 - BIAYA LAIN-LAIN - G",
						"against": rk_account,
						"cost_center": self.get("items")[0].cost_center,
						"remarks": ("Adjustment RK Entry for Stock"),
						"credit":  row.credit - self.rk_value,
						"credit_in_account_currency": row.credit - self.rk_value
					}))

				row.credit = self.rk_value
				row.credit_in_account_currency = self.rk_value
		
	return process_gl_map(gl_list)

def custom_get_gl_entries(self, warehouse_account=None, default_expense_account=None,
			default_cost_center=None):

	if not warehouse_account:
		warehouse_account = get_warehouse_account_map(self.company)

	sle_map = self.get_stock_ledger_details()
	voucher_details = self.get_voucher_details(default_expense_account, default_cost_center, sle_map)

	gl_list = []
	warehouse_with_no_account = []
	precision = self.get_debit_field_precision()
	for item_row in voucher_details:

		sle_list = sle_map.get(item_row.name)
		if sle_list:
			for sle in sle_list:
				if warehouse_account.get(sle.warehouse):
					# from warehouse account

					self.check_expense_account(item_row)

					# If the item does not have the allow zero valuation rate flag set
					# and ( valuation rate not mentioned in an incoming entry
					# or incoming entry not found while delivering the item),
					# try to pick valuation rate from previous sle or Item master and update in SLE
					# Otherwise, throw an exception

					if not sle.stock_value_difference and self.doctype != "Stock Reconciliation" \
						and not item_row.get("allow_zero_valuation_rate"):

						sle = self.update_stock_ledger_entries(sle)

					# expense account/ target_warehouse / source_warehouse
					if item_row.get('target_warehouse'):
						warehouse = item_row.get('target_warehouse')
						expense_account = warehouse_account[warehouse]["account"]
					else:
						expense_account = item_row.expense_account

					check_rk = frappe.db.sql("""
						SELECT 
						IF(valuation_rate_dari_cabang != 0, valuation_rate_dari_cabang * qty, valuation_rate * qty) 
						FROM `tabStock Entry Detail` WHERE name = "{}"
						""".format(sle.voucher_detail_no))

					ste_difference = sle.stock_value_difference
					if len(check_rk) > 0 :
						ste_difference = flt(check_rk[0][0]) * -1

					gl_list.append(self.get_gl_dict({
						"account": warehouse_account[sle.warehouse]["account"],
						"against": expense_account,
						"cost_center": item_row.cost_center,
						"project": item_row.project or self.get('project'),
						"remarks": self.get("remarks") or "Accounting Entry for Stock",
						"debit": flt(ste_difference, precision),
						"is_opening": item_row.get("is_opening") or self.get("is_opening") or "No",
					}, warehouse_account[sle.warehouse]["account_currency"], item=item_row))

					gl_list.append(self.get_gl_dict({
						"account": expense_account,
						"against": warehouse_account[sle.warehouse]["account"],
						"cost_center": item_row.cost_center,
						"remarks": self.get("remarks") or "Accounting Entry for Stock",
						"credit": flt(ste_difference, precision),
						"project": item_row.get("project") or self.get("project"),
						"is_opening": item_row.get("is_opening") or self.get("is_opening") or "No"
					}, item=item_row))
				elif sle.warehouse not in warehouse_with_no_account:
					warehouse_with_no_account.append(sle.warehouse)

	if warehouse_with_no_account:
		for wh in warehouse_with_no_account:
			if frappe.db.get_value("Warehouse", wh, "company"):
				frappe.throw(_("Warehouse {0} is not linked to any account, please mention the account in the warehouse record or set default inventory account in company {1}.").format(wh, self.company))
	
	
	return process_gl_map(gl_list, precision=precision)

@frappe.whitelist()
def update_null_removed(self,method):
	if self.ref_doctype == "Material Request" and self.update_type == "Update":
		self.data = self.data.replace('"removed": {\n  "null": [' , '"removed": {\n  "items": [')


@frappe.whitelist()
def debug_event_sync_log():
	update = frappe.get_doc("Event Sync Log","72fff2babe")
	update.data = json.loads(update.data)
	if "attachment" in update.data["added"]:
		for row in update.data["added"] :
			if "attachment" in row:
				for row2 in update.data["added"][row]:
					if row2["attachment"] != "":
						if "https" not in row2["attachment"] and "Material Request" in row2["parenttype"]:
							row2["attachment"] = str(event_producer.name) + str(row2["attachment"])
							print(row2["attachment"])

@frappe.whitelist()
def custom_pull_from_node(event_producer):
	"""pull all updates after the last update timestamp from event producer site"""
	# custom chandra
	# requires for ssl

	event_producer = event_producer.replace("http://","https://")
			
	event_producer = frappe.get_doc('Event Producer', event_producer)
	user = event_producer.user
	producer_site = get_producer_site(event_producer.producer_url)
	last_update = event_producer.get_last_update()
	print(str(last_update))
	(doctypes, mapping_config, naming_config) = get_config(event_producer.producer_doctypes)
	
	updates = get_updates(producer_site, last_update, doctypes)
		
	for update in updates:
		print(str(update))

		update.use_same_name = naming_config.get(update.ref_doctype)
		mapping = mapping_config.get(update.ref_doctype)
		if mapping:
			update.mapping = mapping
			update = get_mapped_update(update, producer_site)
		if not update.update_type == 'Delete':
			update.data = json.loads(update.data)


			if "letter_head" in update.data:
				if update.data["letter_head"] != "":
					update.data["letter_head"] = ""

			# if "owner" in update.data:
			# 	if update.data["owner"] != "":
			# 		update.data["owner"] = user

			if "docstatus" in update.data:
				if update.data["docstatus"] == "0":
					update.data["docstatus"] = 0

			if "additional_costs" in update.data:
				if update.data["additional_costs"] == "[]":
					update.data["additional_costs"] = []	

			if "attachment_test" in update.data:
				if update.data["attachment_test"] != "" and update.data["doctype"] == "Item":
					if "https" not in update.data["attachment_test"]:
						update.data["attachment_test"] = str(event_producer.name) + str(update.data["attachment_test"])

			if "attachment" in update.data:
				for row in update.data["attachment"] :
					if "attachment" in row:
						if row["attachment"] != "":
							if "https" not in row["attachment"] and "Material Request" in row["parenttype"]:
								row["attachment"] = str(event_producer.name) + str(row["attachment"])
			if "added" in update.data:
				if "attachment" in update.data["added"]:
					for row in update.data["added"] :
						if "attachment" in row:
							for row2 in update.data["added"][row]:
								if row2["attachment"] != "":
									if "https" not in row2["attachment"] and "Material Request" in row2["parenttype"]:
										row2["attachment"] = str(event_producer.name) + str(row2["attachment"])
										print(row2["attachment"])
								

			# if "changed" in update.data and update.data["doctype"] != "Material Request":
			# 	if "attachment" in update.data["changed"]:
			# 		if update.data["changed"]["attachment"] != "":
			# 			if "https" not in update.data["changed"]["attachment"]:
			# 				update.data["changed"]["attachment"] = str(event_producer.name) + str(update.data["changed"]["attachment"])




			if "amended_from" in update.data:
				if update.data["doctype"] == "Stock Entry":
					update.data["amended_from"] = ""
			
			if "workflow_state" in update.data:
				if update.data["doctype"] == "Stock Entry" and update.data["workflow_state"] == "Draft":
					update.data["workflow_state"] = "Pending"
					
			if "items" in update.data and update.data["doctype"] == "Stock Entry":
				for row in update.data["items"] :
					if "basic_rate" in row:
						if row["basic_rate"] == 0:
							row["allow_zero_valuation_rate"] = 1
						else:
							row["allow_zero_valuation_rate"] = 0
				
			if "stat" in update.data and update.data["doctype"] == "STE Log":
				if update.data["stat"] == "Terbuat di Pusat" and update.data["transfer_ke"] == "Pusat":
					update.data["docstatus"] = 0

			
			if "doctype" in update.data:
				if update.data["doctype"] == "Berita Acara Komplain":
					if "attachment" in update.data:
						if update.data["attachment"] != "":
							if "https" not in update.data["attachment"]:
								update.data["attachment"] = str(event_producer.name) + str(update.data["attachment"])
					if "no_stock_entry" in update.data:
						if update.data["no_stock_entry"] != "":
							update.data["no_stock_entry"] = ""

					# if "no_surat_jalan" in update.data:
					# 	if update.data["no_surat_jalan"] != "":
					# 		update.data["no_surat_jalan"] = ""

					if "no_purchase_receipt" in update.data:
						if update.data["no_purchase_receipt"] != "":
							update.data["no_purchase_receipt"] = ""


			if update.ref_doctype == "Material Request":
				
				if "set_from_warehouse" in update.data:
					update.data["set_from_warehouse"] = ""
				if "set_warehouse" in update.data:
					update.data["set_warehouse"] = ""

	
				if "items" in update.data:
					for row in update.data["items"]:
						if "from_warehouse" in row:
							row["from_warehouse"] = ""
						if "warehouse" in row:
							company_doc = frappe.get_doc("Company", "GIAS")
							if company_doc.server == "Pusat":
								lcg = frappe.get_doc("List Company GIAS",company_doc.nama_cabang).warehouse_penerimaan_dari_pusat
								row["warehouse"] = lcg

						# if "cost_center" in row:
						# 	company_doc = frappe.get_doc("Company", "GIAS")
						# 	row["cost_center"] = company_doc.cost_center

				if "changed" in update.data:

					if "set_from_warehouse" in update.data["changed"]:
						update.data["changed"]["set_from_warehouse"] = ""
					if "set_warehouse" in update.data["changed"]:
						update.data["changed"]["set_warehouse"] = ""

					if "items" in update.data["changed"]:
						for row in update.data["changed"]["items"]:
							if "from_warehouse" in row:
								row["from_warehouse"] = ""
							if "warehouse" in row:
								company_doc = frappe.get_doc("Company", "GIAS")
								if company_doc.server == "Pusat":
									lcg = frappe.get_doc("List Company GIAS",company_doc.nama_cabang).warehouse_penerimaan_dari_pusat
									row["warehouse"] = lcg

							# if "cost_center" in row:
							# 	company_doc = frappe.get_doc("Company", "GIAS")
							# 	row["cost_center"] = company_doc.cost_center

				if "added" in update.data:
					if "set_from_warehouse" in update.data["added"]:
						update.data["added"]["set_from_warehouse"] = ""
					if "set_warehouse" in update.data["added"]:
						update.data["added"]["set_warehouse"] = ""

					if "items" in update.data["added"]:
						for row in update.data["added"]["items"]:
							if "from_warehouse" in row:
								row["from_warehouse"] = ""
							if "warehouse" in row:
								company_doc = frappe.get_doc("Company", "GIAS")
								if company_doc.server == "Pusat":
									lcg = frappe.get_doc("List Company GIAS",company_doc.nama_cabang).warehouse_penerimaan_dari_pusat
									row["warehouse"] = lcg

							# if "cost_center" in row:
							# 	company_doc = frappe.get_doc("Company", "GIAS")
							# 	row["cost_center"] = company_doc.cost_center

				if "row_changed" in update.data:

					if "set_from_warehouse" in update.data["row_changed"]:
						update.data["row_changed"]["set_from_warehouse"] = ""
					if "set_warehouse" in update.data["row_changed"]:
						update.data["row_changed"]["set_warehouse"] = ""

					if "items" in update.data["row_changed"]:
						for row in update.data["row_changed"]["items"]:
							if "from_warehouse" in row:
								row["from_warehouse"] = ""
							if "warehouse" in row:
								company_doc = frappe.get_doc("Company", "GIAS")
								if company_doc.server == "Pusat":
									lcg = frappe.get_doc("List Company GIAS",company_doc.nama_cabang).warehouse_penerimaan_dari_pusat
									row["warehouse"] = lcg

							# if "cost_center" in row:
							# 	company_doc = frappe.get_doc("Company", "GIAS")
							# 	row["cost_center"] = company_doc.cost_center
			# if "doctype" in update.data:
			# 	if update.data["doctype"] == "Material Request":
			# 		ambil_4 = str(update.data["name"])[:-4]
			# 		nomor = frappe.db.sql("""
			# 			SELECT LPAD(SUBSTRING(NAME, -4) + 1,4,0) AS nomor_sekarang 
			# 			FROM `tabMaterial Request`
			# 			WHERE NAME LIKE "%{}%"
			# 			ORDER BY SUBSTRING(NAME, -4) DESC
			# 			LIMIT 1 """.format(ambil_4), as_dict=1)

			# 		if len(nomor) < 1:
			# 			update.data["name"] = ambil_4 + "0001"
			# 		else:
			# 			update.data["name"] = ambil_4 + nomor[0].nomor_sekarang

		print(str(update.docname))
		sync(update, producer_site, event_producer)
		frappe.db.commit()


@frappe.whitelist()
def custom_pull_from_node_pusat(event_producer):
	"""pull all updates after the last update timestamp from event producer site"""
	# custom chandra
	# requires for ssl

	event_producer = event_producer.replace("http://","https://")
			
	event_producer = frappe.get_doc('Event Producer', event_producer)
	user = event_producer.user
	producer_site = get_producer_site(event_producer.producer_url)
	last_update = event_producer.get_last_update()
	
	(doctypes, mapping_config, naming_config) = get_config(event_producer.producer_doctypes)
	
	# updates = get_updates(producer_site, last_update, doctypes)
	updates = custom_get_updates(producer_site, last_update, doctypes)		
	for update in updates:

		update.use_same_name = naming_config.get(update.ref_doctype)
		mapping = mapping_config.get(update.ref_doctype)
		if mapping:
			update.mapping = mapping
			update = get_mapped_update(update, producer_site)
		if not update.update_type == 'Delete':
			update.data = json.loads(update.data)

			if "letter_head" in update.data:
				if update.data["letter_head"] != "":
					update.data["letter_head"] = ""

			# if "owner" in update.data:
			# 	if update.data["owner"] != "":
			# 		update.data["owner"] = user

			if "docstatus" in update.data:
				if update.data["docstatus"] == "0":
					update.data["docstatus"] = 0

			if "additional_costs" in update.data:
				if update.data["additional_costs"] == "[]":
					update.data["additional_costs"] = []	

			if "attachment_test" in update.data:
				if update.data["attachment_test"] != "" and update.data["doctype"] == "Item":
					if "https" not in update.data["attachment_test"]:
						update.data["attachment_test"] = str(event_producer.name) + str(update.data["attachment_test"])

			if "attachment" in update.data:
				for row in update.data["attachment"] :
					if "attachment" in row:
						if row["attachment"] != "":
							if "https" not in row["attachment"] and "Material Request" in row["parenttype"]:
								row["attachment"] = str(event_producer.name) + str(row["attachment"])
			
			if "added" in update.data:
				if "attachment" in update.data["added"]:
					for row in update.data["added"] :
						if "attachment" in row:
							for row2 in update.data["added"][row]:
								if row2["attachment"] != "":
									if "https" not in row2["attachment"] and "Material Request" in row2["parenttype"]:
										row2["attachment"] = str(event_producer.name) + str(row2["attachment"])
										print(row2["attachment"])

			# if "changed" in update.data and update.data["doctype"] != "Material Request":
			# 	if "attachment" in update.data["changed"]:
			# 		if update.data["changed"]["attachment"] != "":
			# 			if "https" not in update.data["changed"]["attachment"]:
			# 				update.data["changed"]["attachment"] = str(event_producer.name) + str(update.data["changed"]["attachment"])




			if "amended_from" in update.data:
				if update.data["doctype"] == "Stock Entry":
					update.data["amended_from"] = ""
			
			if "workflow_state" in update.data:
				if update.data["doctype"] == "Stock Entry" and update.data["workflow_state"] == "Draft":
					update.data["workflow_state"] = "Pending"
					
			if "items" in update.data and update.data["doctype"] == "Stock Entry":
				for row in update.data["items"] :
					if "basic_rate" in row:
						if row["basic_rate"] == 0:
							row["allow_zero_valuation_rate"] = 1
						else:
							row["allow_zero_valuation_rate"] = 0
				
			if "stat" in update.data and update.data["doctype"] == "STE Log":
				if update.data["stat"] == "Terbuat di Pusat" and update.data["transfer_ke"] == "Pusat":
					update.data["docstatus"] = 0

			
			if "doctype" in update.data:
				if update.data["doctype"] == "Berita Acara Komplain":
					if "attachment" in update.data:
						if update.data["attachment"] != "":
							if "https" not in update.data["attachment"]:
								update.data["attachment"] = str(event_producer.name) + str(update.data["attachment"])
					if "no_stock_entry" in update.data:
						if update.data["no_stock_entry"] != "":
							update.data["no_stock_entry"] = ""

					# if "no_surat_jalan" in update.data:
					# 	if update.data["no_surat_jalan"] != "":
					# 		update.data["no_surat_jalan"] = ""

					if "no_purchase_receipt" in update.data:
						if update.data["no_purchase_receipt"] != "":
							update.data["no_purchase_receipt"] = ""


			if update.ref_doctype == "Material Request":
				
				if "set_from_warehouse" in update.data:
					update.data["set_from_warehouse"] = ""
				if "set_warehouse" in update.data:
					update.data["set_warehouse"] = ""

	
				if "items" in update.data:
					for row in update.data["items"]:
						if "from_warehouse" in row:
							row["from_warehouse"] = ""
						if "warehouse" in row:
							company_doc = frappe.get_doc("Company", "GIAS")
							if company_doc.server == "Pusat":
								lcg = frappe.get_doc("List Company GIAS",company_doc.nama_cabang).warehouse_penerimaan_dari_pusat
								row["warehouse"] = lcg

						if "cost_center" in row:
							company_doc = frappe.get_doc("Company", "GIAS")
							row["cost_center"] = company_doc.cost_center

				if "changed" in update.data:

					if "set_from_warehouse" in update.data["changed"]:
						update.data["changed"]["set_from_warehouse"] = ""
					if "set_warehouse" in update.data["changed"]:
						update.data["changed"]["set_warehouse"] = ""

					if "items" in update.data["changed"]:
						for row in update.data["changed"]["items"]:
							if "from_warehouse" in row:
								row["from_warehouse"] = ""
							if "warehouse" in row:
								company_doc = frappe.get_doc("Company", "GIAS")
								if company_doc.server == "Pusat":
									lcg = frappe.get_doc("List Company GIAS",company_doc.nama_cabang).warehouse_penerimaan_dari_pusat
									row["warehouse"] = lcg

							## if "cost_center" in row:
								## company_doc = frappe.get_doc("Company", "GIAS")
								## row["cost_center"] = company_doc.cost_center

				if "added" in update.data:
					if "set_from_warehouse" in update.data["added"]:
						update.data["added"]["set_from_warehouse"] = ""
					if "set_warehouse" in update.data["added"]:
						update.data["added"]["set_warehouse"] = ""

					if "items" in update.data["added"]:
						for row in update.data["added"]["items"]:
							if "from_warehouse" in row:
								row["from_warehouse"] = ""
							if "warehouse" in row:
								company_doc = frappe.get_doc("Company", "GIAS")
								if company_doc.server == "Pusat":
									lcg = frappe.get_doc("List Company GIAS",company_doc.nama_cabang).warehouse_penerimaan_dari_pusat
									row["warehouse"] = lcg

							## if "cost_center" in row:
								## company_doc = frappe.get_doc("Company", "GIAS")
								## row["cost_center"] = company_doc.cost_center

				if "row_changed" in update.data:

					if "set_from_warehouse" in update.data["row_changed"]:
						update.data["row_changed"]["set_from_warehouse"] = ""
					if "set_warehouse" in update.data["row_changed"]:
						update.data["row_changed"]["set_warehouse"] = ""

					if "items" in update.data["row_changed"]:
						for row in update.data["row_changed"]["items"]:
							if "from_warehouse" in row:
								row["from_warehouse"] = ""
							if "warehouse" in row:
								company_doc = frappe.get_doc("Company", "GIAS")
								if company_doc.server == "Pusat":
									lcg = frappe.get_doc("List Company GIAS",company_doc.nama_cabang).warehouse_penerimaan_dari_pusat
									row["warehouse"] = lcg

							## if "cost_center" in row:
								## company_doc = frappe.get_doc("Company", "GIAS")
								## row["cost_center"] = company_doc.cost_center
			# if "doctype" in update.data:
			# 	if update.data["doctype"] == "Material Request":
			# 		ambil_4 = str(update.data["name"])[:-4]
			# 		nomor = frappe.db.sql("""
			# 			SELECT LPAD(SUBSTRING(NAME, -4) + 1,4,0) AS nomor_sekarang 
			# 			FROM `tabMaterial Request`
			# 			WHERE NAME LIKE "%{}%"
			# 			ORDER BY SUBSTRING(NAME, -4) DESC
			# 			LIMIT 1 """.format(ambil_4), as_dict=1)

			# 		if len(nomor) < 1:
			# 			update.data["name"] = ambil_4 + "0001"
			# 		else:
			# 			update.data["name"] = ambil_4 + nomor[0].nomor_sekarang

		print(str(update.docname))
		sync(update, producer_site, event_producer)

@frappe.whitelist()
def debug_pusat_custom_pull_from_node(event_producer, debug=True):
	"""pull all updates after the last update timestamp from event producer site"""
	# custom chandra
	# requires for ssl	
	event_producer = event_producer.replace("http://","https://")
	nama_db = event_producer.replace("https://erp-","db_").replace(".gias.co.id","")
	if nama_db == "db_pal":
		nama_db = "db_palu"

	event_producer = frappe.get_doc('Event Producer', event_producer)
	producer_site = get_producer_site(event_producer.producer_url)
	last_update = event_producer.get_last_update()
	
	(doctypes, mapping_config, naming_config) = get_config(event_producer.producer_doctypes)
	
	frappe.flags.debug=True
	# updates = get_updates(producer_site, last_update, 	)
	# updates = custom_get_updates(producer_site, last_update, doctypes)
	updates =  frappe.db.sql(""" SELECT 
			`update_type`, 
			`ref_doctype`,
			`docname`, `data`, `name`, `creation` 
			FROM `{}`.`tabEvent Update Log`  
			WHERE
			creation >= "{}"
			GROUP BY docname, `data`
			
			
			ORDER BY creation ASC
	""".format(nama_db,last_update), as_dict=1,debug=1)

	result = []
	to_update_history = []
	nama_cabang = frappe.get_doc("Company","GIAS").nama_cabang
	singkatan_cabang = frappe.get_doc("List Company GIAS",nama_cabang).singkatan_cabang
	
	for update in updates:
		
		print(update.docname)
		update.use_same_name = naming_config.get(update.ref_doctype)
		mapping = mapping_config.get(update.ref_doctype)
		if mapping:
			update.mapping = mapping
			update = get_mapped_update(update, producer_site)
		if not update.update_type == 'Delete':
			update.data = json.loads(update.data)

			if "letter_head" in update.data:
				if update.data["letter_head"] != "":
					update.data["letter_head"] = ""

			if "docstatus" in update.data:
				if update.data["docstatus"] == "0":
					update.data["docstatus"] = 0

			if "additional_costs" in update.data:
				if update.data["additional_costs"] == "[]":
					update.data["additional_costs"] = []	

			if "attachment_test" in update.data:
				if update.data["attachment_test"] != "" and update.data["doctype"] == "Item":
					if "https" not in update.data["attachment_test"]:
						update.data["attachment_test"] = str(event_producer.name) + str(update.data["attachment_test"])

			if "attachment" in update.data and update.data["doctype"] == "Material Request":
				for row in update.data["attachment"] :
					if "attachment" in row:
						if row["attachment"] != "":
							if "https" not in row["attachment"]:
								row["attachment"] = str(event_producer.name) + str(row["attachment"])

			if "added" in update.data:
				if "attachment" in update.data["added"]:
					for row in update.data["added"] :
						if "attachment" in row:
							for row2 in update.data["added"][row]:
								if row2["attachment"] != "":
									if "https" not in row2["attachment"] and "Material Request" in row2["parenttype"]:
										row2["attachment"] = str(event_producer.name) + str(row2["attachment"])
										print(row2["attachment"])
							

			# if "changed" in update.data and update.data["doctype"] != "Material Request":
			# 	if "attachment" in update.data["changed"]:
			# 		if update.data["changed"]["attachment"] != "":
			# 			if "https" not in update.data["changed"]["attachment"]:
			# 				update.data["changed"]["attachment"] = str(event_producer.name) + str(update.data["changed"]["attachment"])

			if "amended_from" in update.data:
				if update.data["doctype"] == "Stock Entry":
					update.data["amended_from"] = ""
			
			if "workflow_state" in update.data:
				if update.data["doctype"] == "Stock Entry" and update.data["workflow_state"] == "Draft":
					update.data["workflow_state"] = "Pending"
					
			if "items" in update.data and update.data["doctype"] == "Stock Entry":
				for row in update.data["items"] :
					if "basic_rate" in row:
						if row["basic_rate"] == 0:
							row["allow_zero_valuation_rate"] = 1
						else:
							row["allow_zero_valuation_rate"] = 0
				
			if "stat" in update.data and update.data["doctype"] == "STE Log":
				if update.data["stat"] == "Terbuat di Pusat" and update.data["transfer_ke"] == "Pusat":
					update.data["docstatus"] = 0

			
			if "doctype" in update.data:
				if update.data["doctype"] == "Berita Acara Komplain":
					if "attachment" in update.data:
						if update.data["attachment"] != "":
							update.data["attachment"] = str(event_producer.name) + str(update.data["attachment"])
					if "no_stock_entry" in update.data:
						if update.data["no_stock_entry"] != "":
							update.data["no_stock_entry"] = ""

					# if "no_surat_jalan" in update.data:
					# 	if update.data["no_surat_jalan"] != "":
					# 		update.data["no_surat_jalan"] = ""

					if "no_purchase_receipt" in update.data:
						if update.data["no_purchase_receipt"] != "":
							update.data["no_purchase_receipt"] = ""


			if update.ref_doctype == "Material Request":
				
				if "set_from_warehouse" in update.data:
					update.data["set_from_warehouse"] = ""
				if "set_warehouse" in update.data:
					update.data["set_warehouse"] = ""

	
				if "items" in update.data:
					for row in update.data["items"]:
						if "from_warehouse" in row:
							row["from_warehouse"] = ""
						if "warehouse" in row:
							company_doc = frappe.get_doc("Company", "GIAS")
							if company_doc.server == "Pusat":
								lcg = frappe.get_doc("List Company GIAS",company_doc.nama_cabang).warehouse_penerimaan_dari_pusat
								row["warehouse"] = lcg

						if "cost_center" in row:
							company_doc = frappe.get_doc("Company", "GIAS")
							row["cost_center"] = company_doc.cost_center

				if "changed" in update.data:

					if "set_from_warehouse" in update.data["changed"]:
						update.data["changed"]["set_from_warehouse"] = ""
					if "set_warehouse" in update.data["changed"]:
						update.data["changed"]["set_warehouse"] = ""

					if "items" in update.data["changed"]:
						for row in update.data["changed"]["items"]:
							if "from_warehouse" in row:
								row["from_warehouse"] = ""
							if "warehouse" in row:
								company_doc = frappe.get_doc("Company", "GIAS")
								if company_doc.server == "Pusat":
									lcg = frappe.get_doc("List Company GIAS",company_doc.nama_cabang).warehouse_penerimaan_dari_pusat
									row["warehouse"] = lcg

							## if "cost_center" in row:
								## company_doc = frappe.get_doc("Company", "GIAS")
								## row["cost_center"] = company_doc.cost_center

				if "added" in update.data:
					if "set_from_warehouse" in update.data["added"]:
						update.data["added"]["set_from_warehouse"] = ""
					if "set_warehouse" in update.data["added"]:
						update.data["added"]["set_warehouse"] = ""

					if "items" in update.data["added"]:
						for row in update.data["added"]["items"]:
							if "from_warehouse" in row:
								row["from_warehouse"] = ""
							if "warehouse" in row:
								company_doc = frappe.get_doc("Company", "GIAS")
								if company_doc.server == "Pusat":
									lcg = frappe.get_doc("List Company GIAS",company_doc.nama_cabang).warehouse_penerimaan_dari_pusat
									row["warehouse"] = lcg

							## if "cost_center" in row:
								## company_doc = frappe.get_doc("Company", "GIAS")
								## row["cost_center"] = company_doc.cost_center

				if "row_changed" in update.data:

					if "set_from_warehouse" in update.data["row_changed"]:
						update.data["row_changed"]["set_from_warehouse"] = ""
					if "set_warehouse" in update.data["row_changed"]:
						update.data["row_changed"]["set_warehouse"] = ""

					if "items" in update.data["row_changed"]:
						for row in update.data["row_changed"]["items"]:
							if "from_warehouse" in row:
								row["from_warehouse"] = ""
							if "warehouse" in row:
								company_doc = frappe.get_doc("Company", "GIAS")
								if company_doc.server == "Pusat":
									lcg = frappe.get_doc("List Company GIAS",company_doc.nama_cabang).warehouse_penerimaan_dari_pusat
									row["warehouse"] = lcg

							## if "cost_center" in row:
								## company_doc = frappe.get_doc("Company", "GIAS")
								## row["cost_center"] = company_doc.cost_center
			# if "doctype" in update.data:
			# 	if update.data["doctype"] == "Material Request":
			# 		ambil_4 = str(update.data["name"])[:-4]
			# 		nomor = frappe.db.sql("""
			# 			SELECT LPAD(SUBSTRING(NAME, -4) + 1,4,0) AS nomor_sekarang 
			# 			FROM `tabMaterial Request`
			# 			WHERE NAME LIKE "%{}%"
			# 			ORDER BY SUBSTRING(NAME, -4) DESC
			# 			LIMIT 1 """.format(ambil_4), as_dict=1)

			# 		if len(nomor) < 1:
			# 			update.data["name"] = ambil_4 + "0001"
			# 		else:
			# 			update.data["name"] = ambil_4 + nomor[0].nomor_sekarang

		sync(update, producer_site, event_producer)

@frappe.whitelist()
def debug_custom_pull_from_node(event_producer, debug=True):
	"""pull all updates after the last update timestamp from event producer site"""
	# custom chandra
	# requires for ssl
	if frappe.get_doc("Company", "GIAS").server != "Cabang":
		return

	
	event_producer = event_producer.replace("http://","https://")

	event_producer = frappe.get_doc('Event Producer', event_producer)
	producer_site = get_producer_site(event_producer.producer_url)
	last_update = event_producer.get_last_update()
	
	(doctypes, mapping_config, naming_config) = get_config(event_producer.producer_doctypes)
	
	frappe.flags.debug=True
	# updates = get_updates(producer_site, last_update, 	)
	# updates = custom_get_updates(producer_site, last_update, doctypes)
	updates =  frappe.db.sql(""" SELECT 
			`update_type`, 
			`ref_doctype`,
			`docname`, `data`, `name`, `creation` 
			FROM `db_pusat`.`tabEvent Update Log`  
			WHERE
			creation >= "{}"
			AND `data` NOT LIKE "%ps_approver%"
			GROUP BY docname, `data`
			
			
			ORDER BY creation ASC
	""".format(last_update), as_dict=1,debug=1)

	result = []
	to_update_history = []
	nama_cabang = frappe.get_doc("Company","GIAS").nama_cabang
	singkatan_cabang = frappe.get_doc("List Company GIAS",nama_cabang).singkatan_cabang
	
	for update in updates:
		if update.ref_doctype == "Berita Acara Komplain":
			if not singkatan_cabang in update.docname:
				continue

		if update.ref_doctype == "Material Request":
			if not singkatan_cabang in update.docname:
				continue

		if update.ref_doctype == "STE Log":
			
			if "cabang" in str(update.data):
				if not '"cabang": "{}"'.format(nama_cabang) in update.data:
					continue
		print(update.docname)
		update.use_same_name = naming_config.get(update.ref_doctype)
		mapping = mapping_config.get(update.ref_doctype)
		if mapping:
			update.mapping = mapping
			update = get_mapped_update(update, producer_site)
		if not update.update_type == 'Delete':
			update.data = json.loads(update.data)

			if "letter_head" in update.data:
				if update.data["letter_head"] != "":
					update.data["letter_head"] = ""

			if "docstatus" in update.data:
				if update.data["docstatus"] == "0":
					update.data["docstatus"] = 0

			if "additional_costs" in update.data:
				if update.data["additional_costs"] == "[]":
					update.data["additional_costs"] = []	

			if "attachment_test" in update.data:
				if update.data["attachment_test"] != "" and update.data["doctype"] == "Item":
					if "https" not in update.data["attachment_test"]:
						update.data["attachment_test"] = str(event_producer.name) + str(update.data["attachment_test"])

			if "attachment" in update.data and update.data["doctype"] == "Material Request":
				for row in update.data["attachment"] :
					if "attachment" in row:
						if row["attachment"] != "":
							if "https" not in row["attachment"]:
								row["attachment"] = str(event_producer.name) + str(row["attachment"])
							

			# if "changed" in update.data and update.data["doctype"] != "Material Request":
			# 	if "attachment" in update.data["changed"]:
			# 		if update.data["changed"]["attachment"] != "":
			# 			if "https" not in update.data["changed"]["attachment"]:
			# 				update.data["changed"]["attachment"] = str(event_producer.name) + str(update.data["changed"]["attachment"])

			if "amended_from" in update.data:
				if update.data["doctype"] == "Stock Entry":
					update.data["amended_from"] = ""
			
			if "workflow_state" in update.data:
				if update.data["doctype"] == "Stock Entry" and update.data["workflow_state"] == "Draft":
					update.data["workflow_state"] = "Pending"
					
			if "items" in update.data and update.data["doctype"] == "Stock Entry":
				for row in update.data["items"] :
					if "basic_rate" in row:
						if row["basic_rate"] == 0:
							row["allow_zero_valuation_rate"] = 1
						else:
							row["allow_zero_valuation_rate"] = 0
				
			if "stat" in update.data and update.data["doctype"] == "STE Log":
				if update.data["stat"] == "Terbuat di Pusat" and update.data["transfer_ke"] == "Pusat":
					update.data["docstatus"] = 0

			
			if "doctype" in update.data:
				if update.data["doctype"] == "Berita Acara Komplain":
					if "attachment" in update.data:
						if update.data["attachment"] != "":
							update.data["attachment"] = str(event_producer.name) + str(update.data["attachment"])
					if "no_stock_entry" in update.data:
						if update.data["no_stock_entry"] != "":
							update.data["no_stock_entry"] = ""

					# if "no_surat_jalan" in update.data:
					# 	if update.data["no_surat_jalan"] != "":
					# 		update.data["no_surat_jalan"] = ""

					if "no_purchase_receipt" in update.data:
						if update.data["no_purchase_receipt"] != "":
							update.data["no_purchase_receipt"] = ""


			if update.ref_doctype == "Material Request":
				
				if "set_from_warehouse" in update.data:
					update.data["set_from_warehouse"] = ""
				if "set_warehouse" in update.data:
					update.data["set_warehouse"] = ""

	
				if "items" in update.data:
					for row in update.data["items"]:
						if "from_warehouse" in row:
							row["from_warehouse"] = ""
						if "warehouse" in row:
							company_doc = frappe.get_doc("Company", "GIAS")
							if company_doc.server == "Pusat":
								lcg = frappe.get_doc("List Company GIAS",company_doc.nama_cabang).warehouse_penerimaan_dari_pusat
								row["warehouse"] = lcg

						if "cost_center" in row:
							company_doc = frappe.get_doc("Company", "GIAS")
							row["cost_center"] = company_doc.cost_center

				if "changed" in update.data:

					if "set_from_warehouse" in update.data["changed"]:
						update.data["changed"]["set_from_warehouse"] = ""
					if "set_warehouse" in update.data["changed"]:
						update.data["changed"]["set_warehouse"] = ""

					if "items" in update.data["changed"]:
						for row in update.data["changed"]["items"]:
							if "from_warehouse" in row:
								row["from_warehouse"] = ""
							if "warehouse" in row:
								company_doc = frappe.get_doc("Company", "GIAS")
								if company_doc.server == "Pusat":
									lcg = frappe.get_doc("List Company GIAS",company_doc.nama_cabang).warehouse_penerimaan_dari_pusat
									row["warehouse"] = lcg

							## if "cost_center" in row:
								## company_doc = frappe.get_doc("Company", "GIAS")
								## row["cost_center"] = company_doc.cost_center

				if "added" in update.data:
					if "set_from_warehouse" in update.data["added"]:
						update.data["added"]["set_from_warehouse"] = ""
					if "set_warehouse" in update.data["added"]:
						update.data["added"]["set_warehouse"] = ""

					if "items" in update.data["added"]:
						for row in update.data["added"]["items"]:
							if "from_warehouse" in row:
								row["from_warehouse"] = ""
							if "warehouse" in row:
								company_doc = frappe.get_doc("Company", "GIAS")
								if company_doc.server == "Pusat":
									lcg = frappe.get_doc("List Company GIAS",company_doc.nama_cabang).warehouse_penerimaan_dari_pusat
									row["warehouse"] = lcg

							## if "cost_center" in row:
								## company_doc = frappe.get_doc("Company", "GIAS")
								## row["cost_center"] = company_doc.cost_center

				if "row_changed" in update.data:

					if "set_from_warehouse" in update.data["row_changed"]:
						update.data["row_changed"]["set_from_warehouse"] = ""
					if "set_warehouse" in update.data["row_changed"]:
						update.data["row_changed"]["set_warehouse"] = ""

					if "items" in update.data["row_changed"]:
						for row in update.data["row_changed"]["items"]:
							if "from_warehouse" in row:
								row["from_warehouse"] = ""
							if "warehouse" in row:
								company_doc = frappe.get_doc("Company", "GIAS")
								if company_doc.server == "Pusat":
									lcg = frappe.get_doc("List Company GIAS",company_doc.nama_cabang).warehouse_penerimaan_dari_pusat
									row["warehouse"] = lcg

							## if "cost_center" in row:
								## company_doc = frappe.get_doc("Company", "GIAS")
								## row["cost_center"] = company_doc.cost_center
			# if "doctype" in update.data:
			# 	if update.data["doctype"] == "Material Request":
			# 		ambil_4 = str(update.data["name"])[:-4]
			# 		nomor = frappe.db.sql("""
			# 			SELECT LPAD(SUBSTRING(NAME, -4) + 1,4,0) AS nomor_sekarang 
			# 			FROM `tabMaterial Request`
			# 			WHERE NAME LIKE "%{}%"
			# 			ORDER BY SUBSTRING(NAME, -4) DESC
			# 			LIMIT 1 """.format(ambil_4), as_dict=1)

			# 		if len(nomor) < 1:
			# 			update.data["name"] = ambil_4 + "0001"
			# 		else:
			# 			update.data["name"] = ambil_4 + nomor[0].nomor_sekarang

		sync(update, producer_site, event_producer)

@frappe.whitelist()
def debug_custom_pull_from_node_2(event_producer, debug=True):
	"""pull all updates after the last update timestamp from event producer site"""
	# custom chandra
	# requires for ssl
	if frappe.get_doc("Company", "GIAS").server != "Cabang":
		return

	event_producer = event_producer.replace("http://","https://")

	event_producer = frappe.get_doc('Event Producer', event_producer)
	producer_site = get_producer_site(event_producer.producer_url)
	last_update = event_producer.get_last_update()
	
	(doctypes, mapping_config, naming_config) = get_config(event_producer.producer_doctypes)
	
	frappe.flags.debug=True
	updates =  frappe.db.sql(""" SELECT 
			`update_type`, 
			`ref_doctype`,
			`docname`, `data`, `name`, `creation` 
			FROM `tabEvent Update Log_copy` 
			WHERE
			creation >= "{}"
			AND `data` NOT LIKE "%ps_approver%"
			GROUP BY docname, `data`
			
			
			ORDER BY creation ASC
	""".format(last_update), as_dict=1,debug=1)

	result = []
	to_update_history = []
	nama_cabang = frappe.get_doc("Company","GIAS").nama_cabang
	singkatan_cabang = frappe.get_doc("List Company GIAS",nama_cabang).singkatan_cabang
	
	for update in updates:
		if update.ref_doctype == "Berita Acara Komplain":
			if not singkatan_cabang in update.docname:
				continue

		if update.ref_doctype == "Material Request":
			if not singkatan_cabang in update.docname:
				continue

		if update.ref_doctype == "STE Log":
			
			if "cabang" in str(update.data):
				if not '"cabang": "{}"'.format(nama_cabang) in update.data:
					continue
		print(update.docname)
		update.use_same_name = naming_config.get(update.ref_doctype)
		mapping = mapping_config.get(update.ref_doctype)
		if mapping:
			update.mapping = mapping
			update = get_mapped_update(update, producer_site)
		if not update.update_type == 'Delete':
			update.data = json.loads(update.data)

			if "letter_head" in update.data:
				if update.data["letter_head"] != "":
					update.data["letter_head"] = ""

			if "docstatus" in update.data:
				if update.data["docstatus"] == "0":
					update.data["docstatus"] = 0

			if "additional_costs" in update.data:
				if update.data["additional_costs"] == "[]":
					update.data["additional_costs"] = []	

			if "attachment_test" in update.data:
				if update.data["attachment_test"] != "" and update.data["doctype"] == "Item":
					if "https" not in update.data["attachment_test"]:
						update.data["attachment_test"] = str(event_producer.name) + str(update.data["attachment_test"])

			if "attachment" in update.data and update.data["doctype"] == "Material Request":
				for row in update.data["attachment"] :
					if "attachment" in row:
						if row["attachment"] != "":
							if "https" not in row["attachment"]:
								row["attachment"] = str(event_producer.name) + str(row["attachment"])
							

			# if "changed" in update.data and update.data["doctype"] != "Material Request":
			# 	if "attachment" in update.data["changed"]:
			# 		if update.data["changed"]["attachment"] != "":
			# 			if "https" not in update.data["changed"]["attachment"]:
			# 				update.data["changed"]["attachment"] = str(event_producer.name) + str(update.data["changed"]["attachment"])

			if "amended_from" in update.data:
				if update.data["doctype"] == "Stock Entry":
					update.data["amended_from"] = ""
			
			if "workflow_state" in update.data:
				if update.data["doctype"] == "Stock Entry" and update.data["workflow_state"] == "Draft":
					update.data["workflow_state"] = "Pending"
					
			if "items" in update.data and update.data["doctype"] == "Stock Entry":
				for row in update.data["items"] :
					if "basic_rate" in row:
						if row["basic_rate"] == 0:
							row["allow_zero_valuation_rate"] = 1
						else:
							row["allow_zero_valuation_rate"] = 0
				
			if "stat" in update.data and update.data["doctype"] == "STE Log":
				if update.data["stat"] == "Terbuat di Pusat" and update.data["transfer_ke"] == "Pusat":
					update.data["docstatus"] = 0

			
			if "doctype" in update.data:
				if update.data["doctype"] == "Berita Acara Komplain":
					if "attachment" in update.data:
						if update.data["attachment"] != "":
							update.data["attachment"] = str(event_producer.name) + str(update.data["attachment"])
					if "no_stock_entry" in update.data:
						if update.data["no_stock_entry"] != "":
							update.data["no_stock_entry"] = ""

					# if "no_surat_jalan" in update.data:
					# 	if update.data["no_surat_jalan"] != "":
					# 		update.data["no_surat_jalan"] = ""

					if "no_purchase_receipt" in update.data:
						if update.data["no_purchase_receipt"] != "":
							update.data["no_purchase_receipt"] = ""


			if update.ref_doctype == "Material Request":
				
				if "set_from_warehouse" in update.data:
					update.data["set_from_warehouse"] = ""
				if "set_warehouse" in update.data:
					update.data["set_warehouse"] = ""

	
				if "items" in update.data:
					for row in update.data["items"]:
						if "from_warehouse" in row:
							row["from_warehouse"] = ""
						if "warehouse" in row:
							company_doc = frappe.get_doc("Company", "GIAS")
							if company_doc.server == "Pusat":
								lcg = frappe.get_doc("List Company GIAS",company_doc.nama_cabang).warehouse_penerimaan_dari_pusat
								row["warehouse"] = lcg

						if "cost_center" in row:
							company_doc = frappe.get_doc("Company", "GIAS")
							row["cost_center"] = company_doc.cost_center

				if "changed" in update.data:

					if "set_from_warehouse" in update.data["changed"]:
						update.data["changed"]["set_from_warehouse"] = ""
					if "set_warehouse" in update.data["changed"]:
						update.data["changed"]["set_warehouse"] = ""

					if "items" in update.data["changed"]:
						for row in update.data["changed"]["items"]:
							if "from_warehouse" in row:
								row["from_warehouse"] = ""
							if "warehouse" in row:
								company_doc = frappe.get_doc("Company", "GIAS")
								if company_doc.server == "Pusat":
									lcg = frappe.get_doc("List Company GIAS",company_doc.nama_cabang).warehouse_penerimaan_dari_pusat
									row["warehouse"] = lcg

							## if "cost_center" in row:
								## company_doc = frappe.get_doc("Company", "GIAS")
								## row["cost_center"] = company_doc.cost_center

				if "added" in update.data:
					if "set_from_warehouse" in update.data["added"]:
						update.data["added"]["set_from_warehouse"] = ""
					if "set_warehouse" in update.data["added"]:
						update.data["added"]["set_warehouse"] = ""

					if "items" in update.data["added"]:
						for row in update.data["added"]["items"]:
							if "from_warehouse" in row:
								row["from_warehouse"] = ""
							if "warehouse" in row:
								company_doc = frappe.get_doc("Company", "GIAS")
								if company_doc.server == "Pusat":
									lcg = frappe.get_doc("List Company GIAS",company_doc.nama_cabang).warehouse_penerimaan_dari_pusat
									row["warehouse"] = lcg

							## if "cost_center" in row:
								## company_doc = frappe.get_doc("Company", "GIAS")
								## row["cost_center"] = company_doc.cost_center

				if "row_changed" in update.data:

					if "set_from_warehouse" in update.data["row_changed"]:
						update.data["row_changed"]["set_from_warehouse"] = ""
					if "set_warehouse" in update.data["row_changed"]:
						update.data["row_changed"]["set_warehouse"] = ""

					if "items" in update.data["row_changed"]:
						for row in update.data["row_changed"]["items"]:
							if "from_warehouse" in row:
								row["from_warehouse"] = ""
							if "warehouse" in row:
								company_doc = frappe.get_doc("Company", "GIAS")
								if company_doc.server == "Pusat":
									lcg = frappe.get_doc("List Company GIAS",company_doc.nama_cabang).warehouse_penerimaan_dari_pusat
									row["warehouse"] = lcg

							## if "cost_center" in row:
								## company_doc = frappe.get_doc("Company", "GIAS")
								## row["cost_center"] = company_doc.cost_center
			# if "doctype" in update.data:
			# 	if update.data["doctype"] == "Material Request":
			# 		ambil_4 = str(update.data["name"])[:-4]
			# 		nomor = frappe.db.sql("""
			# 			SELECT LPAD(SUBSTRING(NAME, -4) + 1,4,0) AS nomor_sekarang 
			# 			FROM `tabMaterial Request`
			# 			WHERE NAME LIKE "%{}%"
			# 			ORDER BY SUBSTRING(NAME, -4) DESC
			# 			LIMIT 1 """.format(ambil_4), as_dict=1)

			# 		if len(nomor) < 1:
			# 			update.data["name"] = ambil_4 + "0001"
			# 		else:
			# 			update.data["name"] = ambil_4 + nomor[0].nomor_sekarang

		sync(update, producer_site, event_producer)
	
@frappe.whitelist()
def custom_new_event_notification(producer_url):
	"""Pull data from producer when notified"""
	enqueued_method = 'addons.custom_standard.custom_stock_entry.custom_pull_from_node'
	jobs = get_jobs()
	if not jobs or enqueued_method not in jobs[frappe.local.site]:
		frappe.enqueue(enqueued_method, queue='default', **{'event_producer': producer_url})



@frappe.whitelist()
def get_memope(memope):

	list_memo = frappe.db.sql(""" 
		SELECT 
		total_harga_dpp, name
		FROM `tabMemo Ekspedisi` WHERE name = "{}"

		""".format(memope))
	for row in list_memo:
		self = frappe.get_doc("Memo Ekspedisi", row[1])
		if self.purchase_order_delivery_pod:
			pod = self.purchase_order_delivery_pod
			pod_amount = frappe.db.sql(""" 
				SELECT 
				poi.net_total as total, poi.`total_taxes_and_charges`
				FROM `tabPurchase Order` poi WHERE poi.name = "{}"

				""".format(pod),as_dict=1)

			if len(pod_amount) > 0:
				self.total_harga_dpp = frappe.utils.flt(pod_amount[0].total)
				self.db_update()
	return frappe.db.sql(""" 
		SELECT 
		total_harga_dpp, name
		FROM `tabMemo Ekspedisi` WHERE name = "{}"

		""".format(memope),as_dict=1)
				

@frappe.whitelist()
def get_memope_item(memope):

	return frappe.db.sql(""" 
		SELECT kode_material ,qty_rq, stuffing,nama_dokumen
		FROM `tabMemo Pengiriman Table` 
		WHERE parent = "{}"

		""".format(memope),as_dict=1)

@frappe.whitelist()
def remove_dependency(doc,method):
	check = frappe.db.sql(""" SELECT * FROM `tabCustom Field` WhERE name = "Stock Entry Detail-warehouse_pusat" """)
	if len(check) > 0 and doc.purpose == "Material Receipt":
		company_doc = frappe.get_doc("Company",doc.company)
		if company_doc.server == "Cabang":
			for row in doc.items:
				row.material_request = ""
				row.material_request_item = ""
				row.reference_purchase_receipt = ""
				# row.warehouse_pusat = row.t_warehouse
				
				if doc.transfer_ke_cabang_mana:
					cabang_doc = frappe.get_doc("List Company GIAS", doc.transfer_ke_cabang_mana)
					row.t_warehouse = cabang_doc.warehouse_penerimaan_dari_pusat
					doc.to_warehouse = cabang_doc.warehouse_penerimaan_dari_pusat
					
				if row.additional_cost:
					row.additional_cost = 0

				if doc.ste_log:
					if row.pusat_valuation_rate == 0:
						row.allow_zero_valuation_rate = 1
					else:
						row.allow_zero_valuation_rate = 0

			# if doc.total_additional_costs:
			# 	doc.additional_costs = []
			# 	doc.total_additional_costs = 0

	elif len(check) == 0:
		for row in doc.items:
			if doc.stock_entry_type == "Material Issue":
				if row.t_warehouse and not row.s_warehouse:
					row.s_warehouse = row.t_warehouse
				if row.t_warehouse and row.s_warehouse:
					row.t_warehouse = ""




@frappe.whitelist()
def set_warehouse_pusat(doc,method):
	company_doc = frappe.get_doc("Company",doc.company)
	# if company_doc.server == "Pusat":
	# 	if doc.transfer_ke_cabang_pusat == 1 and doc.cabang_atau_pusat == "Cabang" and doc.transfer_ke_cabang_mana and doc.purpose == "Material Transfer":
	# 		for row in doc.items:
	# 			if row.t_warehouse:
	# 				ware_doc = frappe.get_doc("Warehouse",row.t_warehouse)
	# 				if str(ware_doc.cabang) != str(doc.transfer_ke_cabang_mana) or str(ware_doc.warehouse_type) != "Transit" :
	# 					frappe.throw("Stock Entry yang mempunyai detil Cabang {} harus Transfer ke Gudang Transit Cabang {}".format(doc.transfer_ke_cabang_mana, doc.transfer_ke_cabang_mana))

	# elif company_doc.server == "Cabang":
	# 	if doc.transfer_ke_cabang_pusat == 1 and doc.cabang_atau_pusat == "Pusat" and doc.purpose == "Material Transfer":
	# 		for row in doc.items:
	# 			if row.t_warehouse:
	# 				ware_doc = frappe.get_doc("Warehouse",row.t_warehouse)
	# 				if ware_doc.warehouse_type != "Transit Pusat":
	# 					frappe.throw("Stock Entry yang mempunyai detil tujuan ke Pusat harus Transfer ke Gudang Transit Pusat yang warehouse Typenya Transit Pusat")
						
	# 	elif doc.transfer_ke_cabang_pusat == 1 and doc.cabang_atau_pusat == "Cabang" and doc.transfer_ke_cabang_mana and doc.purpose == "Material Transfer":
	# 		for row in doc.items:
	# 			if row.t_warehouse:
	# 				ware_doc = frappe.get_doc("Warehouse",row.t_warehouse)
	# 				if str(ware_doc.cabang) != str(doc.transfer_ke_cabang_mana) or str(ware_doc.warehouse_type) != "Transit" :
	# 					frappe.throw("Stock Entry yang mempunyai detil Cabang {} harus Transfer ke Gudang Transit Cabang {}".format(doc.transfer_ke_cabang_mana, doc.transfer_ke_cabang_mana))


	check = frappe.db.sql(""" SELECT * FROM `tabCustom Field` WhERE name = "Stock Entry Detail-warehouse_pusat" """)
	if len(check) > 0 and doc.purpose == "Material Receipt":
		for row in doc.items:
			if not row.warehouse_pusat:
				row.material_request = ""
				row.material_request_item = ""
				row.reference_purchase_receipt = ""
				# row.warehouse_pusat = row.t_warehouse
			
			if row.additional_cost:
				row.additional_cost = 0

			row.basic_rate = flt(row.pusat_valuation_rate)
			row.valuation_rate = flt(flt(row.basic_rate) + (flt(row.additional_cost) / flt(row.transfer_qty)))

		if doc.total_additional_costs:
			doc.additional_costs = []
			doc.total_additional_costs = 0

@frappe.whitelist()
def list_patch_cost():
	list_ste = frappe.db.sql(""" 
		SELECT name FROM `tabStock Entry` WHERE 
		name = "STER-BNK-1-22-08-00015" """)
	
	# for row in list_ste:
	# 	patch_cost(row[0])
	# 	print(row[0])

	for row in list_ste:
		patch_cost_ste(row[0])

	# for row in list_ste:
	# 	patch_cost_transfer(row[0])
	# 	print(row[0])

	
	# 	print(row[0])

@frappe.whitelist()
def patch_cost_transfer(row):
	doc = frappe.get_doc("Stock Entry",row)
	# custom_distribute_additional_costs_transfer(doc,"validate")
	for row in doc.items:
		row.basic_amount = row.basic_rate * row.transfer_qty
		row.amount = row.valuation_rate * row.transfer_qty
		row.db_update()

	doc.set_total_incoming_outgoing_value()
	doc.db_update()
	for row in doc.items:
		row.additional_cost_transfer = row.additional_cost
		row.valuation_rate_transfer = row.valuation_rate
		row.db_update()


@frappe.whitelist()
def patch_cost(row):
	doc = frappe.get_doc("Stock Entry",row)
	custom_distribute_additional_costs(doc)
	for row in doc.items:
		row.additional_cost_transfer = row.additional_cost
		row.valuation_rate_transfer = row.valuation_rate
		row.valuation_rate = flt(flt(row.basic_rate) + (flt(row.additional_cost) / flt(row.transfer_qty)))
		row.db_update()

	doc.calculate_rate_and_amount()
	doc.set_total_incoming_outgoing_value()
	print(doc.total_incoming_value)
	doc.db_update()

@frappe.whitelist()
def patch_cost_stei(row):
	doc = frappe.get_doc("Stock Entry",row)
	custom_distribute_additional_costs_transfer(doc,"validate")
	for row in doc.items:
		row.db_update()

@frappe.whitelist()
def patch_cost_ste(row):
	list_ste = frappe.db.sql(""" SELECT name FROM `tabStock Entry` WHERE
	name = "{}" """.format(row))

	frappe.flags.repost_gl = True
	for rows in list_ste:
		ste_doc = frappe.get_doc("Stock Entry", rows[0])
		for row in ste_doc.items:
			row.basic_rate = flt(row.pusat_valuation_rate,2)
			row.valuation_rate = flt(flt(row.basic_rate) + (flt(row.additional_cost) / flt(row.transfer_qty)))
			row.allow_zero_valuation_rate = 0
			row.db_update()

		ste_doc.calculate_rate_and_amount()
		ste_doc.db_update()

		repair_gl_entry("Stock Entry", rows[0])
		print(rows[0])

	frappe.db.commit()

@frappe.whitelist()
def rge_dn():
	frappe.flags.repost_gl == True
	StockController.make_gl_entries = custom_make_gl_entries2
	list_ste = frappe.db.sql("""
	 SELECT ste.name,gle.name FROM `tabStock Entry` ste
		LEFT JOIN `tabGL Entry` gle ON gle.`voucher_no` = ste.name AND gle.account = "1168.04 - R/K STOCK - G"
		WHERE ste.`purpose` = "Material Receipt"
		AND ste.`sync_name` IS NOT NULL
		AND ste.`docstatus` = 1
		HAVING gle.`name` IS NULL """)
	for row in list_ste:
		repair_gl_entry_2("Stock Entry",row[0])
		print(str(row[0]))

@frappe.whitelist()
def repair_gl_entry_2(doctype,docname):
	doc = frappe.get_doc(doctype, docname)	

	docu = frappe.get_doc(doctype, docname)	
	delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(docname))
	frappe.flags.repost_gl == True
	docu.make_gl_entries()
	docu.repost_future_sle_and_gle()

@frappe.whitelist()
def repair_gl_entry(doctype,docname):
	
	docu = frappe.get_doc(doctype, docname)	
	delete_sl = frappe.db.sql(""" DELETE FROM `tabStock Ledger Entry` WHERE voucher_no = "{}" """.format(docname))
	delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(docname))
	frappe.flags.repost_gl == True
	frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 1 WHERE `field` = "allow_negative_stock" """)
	docu.update_stock_ledger()
	docu.make_gl_entries()
	docu.repost_future_sle_and_gle()
	frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 0 WHERE `field` = "allow_negative_stock" """)


def custom_distribute_additional_costs(self):
	# If no incoming items, set additional costs blank
	check_field = frappe.db.sql(""" SELECT name FROM `tabCustom Field` WHERE name = "Stock Entry-cost_by" """)
	if len(check_field) > 0:
		if not any([d.item_code for d in self.items if d.t_warehouse]):
			self.additional_costs = []

		self.total_additional_costs = sum([flt(t.base_amount) for t in self.get("additional_costs")])

		if self.cost_by == "By Value" :
			if self.purpose in ("Repack", "Manufacture"):
				incoming_items_cost = sum([flt(t.basic_amount) for t in self.get("items") if t.is_finished_item])
			else:
				incoming_items_cost = sum([flt(t.basic_amount) for t in self.get("items") if t.t_warehouse])

			if incoming_items_cost:
				for d in self.get("items"):
					if (self.purpose in ("Repack", "Manufacture") and d.is_finished_item) or d.t_warehouse:
						d.additional_cost = (flt(d.basic_amount) / incoming_items_cost) * self.total_additional_costs
					else:
						d.additional_cost = 0

		elif self.cost_by == "By Qty":
			if self.purpose in ("Repack", "Manufacture"):
				incoming_items_cost = sum([flt(t.qty)*flt(t.conversion_factor) for t in self.get("items") if t.is_finished_item])
			else:
				incoming_items_cost = sum([flt(t.qty)*flt(t.conversion_factor) for t in self.get("items") if t.t_warehouse])

			if incoming_items_cost:
				for d in self.get("items"):
					if (self.purpose in ("Repack", "Manufacture") and d.is_finished_item) or d.t_warehouse:
						d.additional_cost = (flt(d.qty)*flt(d.conversion_factor) / incoming_items_cost) * self.total_additional_costs
					else:
						d.additional_cost = 0

		elif self.cost_by == "By Volume":
			if self.purpose in ("Repack", "Manufacture"):
				incoming_items_cost = sum([flt(t.qty)*flt(t.conversion_factor)*flt(t.volume_per_stock_qty) for t in self.get("items") if t.is_finished_item])
			else:
				incoming_items_cost = sum([flt(t.qty)*flt(t.conversion_factor)*flt(t.volume_per_stock_qty) for t in self.get("items") if t.t_warehouse])

			if incoming_items_cost:
				for d in self.get("items"):
					if (self.purpose in ("Repack", "Manufacture") and d.is_finished_item) or d.t_warehouse:
						d.additional_cost = (flt(d.qty)*flt(d.conversion_factor)*flt(d.volume_per_stock_qty) / incoming_items_cost) * self.total_additional_costs
					else:
						d.additional_cost = 0

		elif self.cost_by == "By Tonase":
			if self.purpose in ("Repack", "Manufacture"):
				incoming_items_cost = sum([flt(t.qty)*flt(t.conversion_factor)*flt(t.weight_per_stock_qty) for t in self.get("items") if t.is_finished_item])
			else:
				incoming_items_cost = sum([flt(t.qty)*flt(t.conversion_factor)*flt(t.weight_per_stock_qty) for t in self.get("items") if t.t_warehouse])

			if incoming_items_cost:
				for d in self.get("items"):
					if (self.purpose in ("Repack", "Manufacture") and d.is_finished_item) or d.t_warehouse:
						d.additional_cost = (flt(d.qty)*flt(d.conversion_factor)*flt(d.weight_per_stock_qty) / incoming_items_cost) * self.total_additional_costs
					else:
						d.additional_cost = 0
		elif self.cost_by == "Manual" or not self.cost_by:
			if self.total_additional_costs:
				total_cost = 0
				for row in self.items:
					row.additional_cost = row.additional_cost_transfer

				if self.purpose in ("Repack", "Manufacture"):
					total_cost = sum([flt(t.additional_cost) for t in self.get("items") if t.is_finished_item])
				else:
					total_cost = sum([flt(t.additional_cost) for t in self.get("items") if t.t_warehouse])

				

				if flt(total_cost) != flt(self.total_additional_costs) and abs(flt(total_cost)-flt(self.total_additional_costs))>0.01:
					frappe.throw("Please set additional cost manually till total of {} as you chose the costing by Manual {}.".format(self.total_additional_costs, total_cost))


	else:
		if not any([d.item_code for d in self.items if d.t_warehouse]):
			self.additional_costs = []

		self.total_additional_costs = sum([flt(t.base_amount) for t in self.get("additional_costs")])

		if self.purpose in ("Repack", "Manufacture"):
			incoming_items_cost = sum([flt(t.basic_amount) for t in self.get("items") if t.is_finished_item])
		else:
			incoming_items_cost = sum([flt(t.basic_amount) for t in self.get("items") if t.t_warehouse])

		if incoming_items_cost:
			for d in self.get("items"):
				if (self.purpose in ("Repack", "Manufacture") and d.is_finished_item) or d.t_warehouse:
					d.additional_cost = (flt(d.basic_amount) / incoming_items_cost) * self.total_additional_costs
				else:
					d.additional_cost = 0

	# for row in self.items:
	# 	row.additional_cost_transfer = row.additional_cost
	# 	row.valuation_rate_transfer = row.valuation_rate

StockEntry.distribute_additional_costs = custom_distribute_additional_costs

@frappe.whitelist()
def debug_ste():
	doc = frappe.get_doc("Stock Entry","STEI-HO-1-22-10-03158")
	doc.append("additional_costs_transfer_table",{
		"expense_account": "1168.02 - R/K BIAYA ANGKUT - G",
		"amount": 20277120,
		"description": "patria"
	})

	for row in doc.items:
		if row.idx == 1:
			row.additional_cost_transfer = 17397120
		elif row.idx == 2:
			row.additional_cost_transfer = 2880000

	doc.save()


@frappe.whitelist()
def custom_distribute_additional_costs_transfer(self,method):
	# If no incoming items, set additional costs blank
	for row in self.additional_costs_transfer_table:
		if not row.expense_account:
			frappe.throw("Please input expense account to additional costs you entered.")

	if self.transfer_ke_cabang_pusat == 1 and self.purpose == "Material Issue":
		check_field = frappe.db.sql(""" SELECT name FROM `tabCustom Field` WHERE name = "Stock Entry-cost_by_transfer" """)
		if len(check_field) > 0:
			if not any([d.item_code for d in self.items if d.s_warehouse]):
				self.additional_costs_transfer_table = []

			self.total_additional_costs_transfer = sum([flt(t.amount) for t in self.get("additional_costs_transfer_table")])

			if self.cost_by_transfer == "By Value":
				incoming_items_cost = sum([flt(t.basic_amount) for t in self.get("items") if t.s_warehouse])

				if incoming_items_cost:
					for d in self.get("items"):
						if (self.purpose in ("Repack", "Manufacture") and d.is_finished_item) or d.s_warehouse:
							d.additional_cost_transfer = (flt(d.basic_amount) / incoming_items_cost) * self.total_additional_costs_transfer
						else:
							d.additional_cost_transfer = 0
				else:
					incoming_items_cost = sum([flt(t.qty)*flt(t.conversion_factor) for t in self.get("items") if t.s_warehouse])

					if incoming_items_cost:
						for d in self.get("items"):
							if (self.purpose in ("Repack", "Manufacture") and d.is_finished_item) or d.s_warehouse:
								d.additional_cost_transfer = (flt(d.qty)*flt(d.conversion_factor) / incoming_items_cost) * self.total_additional_costs_transfer
							else:
								d.additional_cost_transfer = 0


			elif self.cost_by_transfer == "By Qty":
				incoming_items_cost = sum([flt(t.qty)*flt(t.conversion_factor) for t in self.get("items") if t.s_warehouse])

				if incoming_items_cost:
					for d in self.get("items"):
						if (self.purpose in ("Repack", "Manufacture") and d.is_finished_item) or d.s_warehouse:
							d.additional_cost_transfer = (flt(d.qty)*flt(d.conversion_factor) / incoming_items_cost) * self.total_additional_costs_transfer
						else:
							d.additional_cost_transfer = 0

			elif self.cost_by_transfer == "By Volume":
				incoming_items_cost = sum([flt(t.qty)*flt(t.conversion_factor)*flt(t.volume_per_stock_qty) for t in self.get("items") if t.s_warehouse])

				if incoming_items_cost:
					for d in self.get("items"):
						if (self.purpose in ("Repack", "Manufacture") and d.is_finished_item) or d.s_warehouse:
							d.additional_cost_transfer = (flt(d.qty)*flt(d.conversion_factor)*flt(d.volume_per_stock_qty) / incoming_items_cost) * self.total_additional_costs_transfer
						else:
							d.additional_cost_transfer = 0

			elif self.cost_by_transfer == "By Tonase":
				incoming_items_cost = sum([flt(t.qty)*flt(t.conversion_factor)*flt(t.weight_per_stock_qty) for t in self.get("items") if t.s_warehouse])

				if incoming_items_cost:
					for d in self.get("items"):
						if (self.purpose in ("Repack", "Manufacture") and d.is_finished_item) or d.s_warehouse:
							d.additional_cost_transfer = (flt(d.qty)*flt(d.conversion_factor)*flt(d.weight_per_stock_qty) / incoming_items_cost) * self.total_additional_costs_transfer
						else:
							d.additional_cost_transfer = 0

			elif self.cost_by_transfer == "Manual":
				if self.total_additional_costs_transfer:
					total_cost = 0
					total_cost = sum([flt(t.additional_cost_transfer) for t in self.get("items") if t.s_warehouse])

					if flt(total_cost) != flt(self.total_additional_costs_transfer) and abs(flt(total_cost)-flt(self.total_additional_costs_transfer))>0.01:
						frappe.throw("Please set additional cost transfer manually till total of {} as you chose the costing by Manual.".format(self.total_additional_costs_transfer))
				
			for d in self.get("items"):
				if (flt(d.transfer_qty)):
					d.valuation_rate_transfer = flt(flt(d.basic_rate) + (flt(d.additional_cost_transfer) / flt(d.transfer_qty)))
				else:
					d.valuation_rate_transfer = flt(flt(d.basic_rate) + flt(d.additional_cost_transfer))

		for d in self.get("items"):
			if (flt(d.transfer_qty)):
				d.valuation_rate_transfer = flt(flt(d.basic_rate) + (flt(d.additional_cost_transfer) / flt(d.transfer_qty)))
			else:
				d.valuation_rate_transfer = flt(flt(d.basic_rate) + flt(d.additional_cost_transfer))


@frappe.whitelist()
def set_accounting_dimension(self,method):
	if self.transfer_ke_cabang_mana:
		self.branch = frappe.get_doc("List Company GIAS", self.transfer_ke_cabang_mana).accounting_dimension
		for row in self.items:
			row.branch = frappe.get_doc("List Company GIAS", self.transfer_ke_cabang_mana).accounting_dimension
			if not row.volume_per_stock_qty:
				row.volume_per_stock_qty = frappe.get_doc("Item",row.item_code).volume

			if not row.weight_per_stock_qty:
				row.weight_per_stock_qty = frappe.get_doc("Item",row.item_code).weight_per_unit


@frappe.whitelist()
def patch_every_volume():
	list_ste = frappe.db.sql(""" SELECT name FROM `tabStock Entry`  """)
	for list_ste_satu in list_ste:
		doc = frappe.get_doc("Stock Entry", list_ste_satu[0])

		for row in doc.items:
			if not row.volume_per_stock_qty:
				row.volume_per_stock_qty = frappe.get_doc("Item", row.item_code).volume

			if not row.weight_per_stock_qty:
				row.weight_per_stock_qty = frappe.get_doc("Item",row.item_code).weight_per_unit

			row.db_update()


@frappe.whitelist()
def buat_ste_log(self,method):
	company_doc = frappe.get_doc("Company",self.company)
	
	self.transfer_status = "Not Transfer"

	for row in self.items:
		row.valuation_rate_transfer = flt(flt(row.basic_rate) + flt(row.additional_cost_transfer))

	if company_doc.server == "Cabang" and self.transfer_ke_cabang_pusat == 1 and (self.cabang_atau_pusat == "Pusat" or (self.cabang_atau_pusat == "Cabang" and self.transfer_ke_cabang_mana == "GIAS SPRINGHILL") ) and self.purpose == "Material Issue":
		ste_log = frappe.new_doc("STE Log")
		ste_log.nama_dokumen = self.name
		ste_log.transfer_ke = "Pusat"
		ste_log.data = frappe.as_json(self)
		ste_log.stat = "Terbuat di Pusat"
		ste_log.company = self.company
		ste_log.buat_ste_di = "Pusat"
		ste_log.tipe_ste = "Material Receipt"
		ste_log.sumber_branch = company_doc.nama_cabang
		ste_log.apakan_ste = "Buat STE"
		ste_log.submit()
		self.transfer_status = "On The Way"

	elif company_doc.server == "Cabang" and self.transfer_ke_cabang_pusat == 1 and self.cabang_atau_pusat == "Cabang" and self.transfer_ke_cabang_mana and self.purpose == "Material Issue":
		ste_log = frappe.new_doc("STE Log")
		ste_log.nama_dokumen = self.name
		ste_log.transfer_ke = "Cabang"
		ste_log.data = frappe.as_json(self)
		ste_log.stat = "Terbuat di Cabang"
		ste_log.company = self.company
		ste_log.buat_ste_di = "Cabang"
		ste_log.tipe_ste = "Material Receipt"
		ste_log.sumber_branch = company_doc.nama_cabang
		ste_log.cabang = self.transfer_ke_cabang_mana
		ste_log.apakan_ste = "Buat STE"
		ste_log.submit()
		self.transfer_status = "On The Way"

	elif company_doc.server == "Pusat" and self.transfer_ke_cabang_pusat == 1 and self.cabang_atau_pusat == "Cabang" and self.transfer_ke_cabang_mana and self.purpose == "Material Issue":
		if self.transfer_ke_cabang_mana != "GIAS SPRINGHILL":
			ste_log = frappe.new_doc("STE Log")
			ste_log.nama_dokumen = self.name
			ste_log.transfer_ke = "Cabang"
			ste_log.data = frappe.as_json(self)
			ste_log.stat = "Terbuat di Cabang"
			ste_log.company = self.company
			ste_log.buat_ste_di = "Cabang"
			ste_log.tipe_ste = "Material Receipt"
			ste_log.cabang = self.transfer_ke_cabang_mana
			ste_log.sumber_branch = company_doc.nama_cabang
			ste_log.apakan_ste = "Buat STE"
			ste_log.submit()
			self.transfer_status = "On The Way"
		else:
			ste_log = frappe.new_doc("STE Log")
			ste_log.nama_dokumen = self.name
			ste_log.transfer_ke = "Pusat"
			ste_log.data = frappe.as_json(self)
			ste_log.stat = "Terbuat di Pusat"
			ste_log.company = self.company
			ste_log.buat_ste_di = "Pusat"
			ste_log.tipe_ste = "Material Receipt"
			ste_log.cabang = self.transfer_ke_cabang_mana
			ste_log.sumber_branch = company_doc.nama_cabang
			ste_log.apakan_ste = "Buat STE"
			ste_log.submit()
			self.transfer_status = "On The Way"

	elif self.ste_log and company_doc.server == "Pusat" and self.purpose == "Material Receipt" :
		ste_log_document = frappe.get_doc("STE Log", self.ste_log)

		ste_log = frappe.new_doc("STE Log")
		ste_log.nama_dokumen = self.name
		ste_log.transfer_ke = "Pusat"
		ste_log.data = frappe.as_json(self)
		ste_log.stat = "Terbuat di Pusat - DONE"
		ste_log.company = self.company
		ste_log.buat_ste_di = "Cabang"
		ste_log.tipe_ste = "Material Issue"
		ste_log.cabang = ste_log_document.cabang
		ste_log.sumber_branch = ste_log_document.sumber_branch
		ste_log.apakan_ste = "Update STE"
		ste_log.ste_yang_diupdate = ste_log_document.nama_dokumen
		ste_log.submit()
		self.transfer_status = "From Sync"

	elif self.ste_log and company_doc.server == "Cabang" and self.purpose == "Material Receipt" :
		ste_log_document = frappe.get_doc("STE Log", self.ste_log)
		self.transfer_status = "From Sync"
		if ste_log_document.sumber_branch ==  company_doc.nama_cabang :
			ste_log = frappe.new_doc("STE Log")
			ste_log.nama_dokumen = self.name
			ste_log.transfer_ke = "Cabang"
			ste_log.data = frappe.as_json(self)
			ste_log.stat = "Terbuat di Cabang - DONE"
			ste_log.company = self.company
			ste_log.buat_ste_di = "Pusat"
			ste_log.tipe_ste = "Material Issue"
			ste_log.cabang = ste_log_document.sumber_branch
			ste_log.sumber_branch = ste_log_document.sumber_branch
			ste_log.apakan_ste = "Update STE"
			ste_log.ste_yang_diupdate = ste_log_document.nama_dokumen
			ste_log.submit()
		elif ste_log_document.sumber_branch != company_doc.nama_cabang:
			ste_log = frappe.new_doc("STE Log")
			ste_log.nama_dokumen = self.name
			ste_log.transfer_ke = "Cabang"
			ste_log.data = frappe.as_json(self)
			ste_log.stat = "Terbuat di Cabang - DONE"
			ste_log.company = self.company
			ste_log.buat_ste_di = "Cabang"
			ste_log.tipe_ste = "Material Issue"
			ste_log.cabang =  ste_log_document.sumber_branch
			ste_log.sumber_branch = ste_log_document.sumber_branch
			ste_log.apakan_ste = "Update STE"
			ste_log.ste_yang_diupdate = ste_log_document.nama_dokumen
			ste_log.submit()

@frappe.whitelist()
def debug_buat_ste_log(ste):
	self = frappe.get_doc("Stock Entry", ste)
	company_doc = frappe.get_doc("Company",self.company)
	
	self.transfer_status = "Not Transfer"

	for row in self.items:
		row.valuation_rate_transfer = flt(flt(row.basic_rate) + flt(row.additional_cost_transfer))

	if company_doc.server == "Cabang" and self.transfer_ke_cabang_pusat == 1 and self.cabang_atau_pusat == "Pusat" and self.purpose == "Material Issue":
		ste_log = frappe.new_doc("STE Log")
		ste_log.nama_dokumen = self.name
		ste_log.transfer_ke = "Pusat"
		ste_log.data = frappe.as_json(self)
		ste_log.stat = "Terbuat di Pusat"
		ste_log.company = self.company
		ste_log.buat_ste_di = "Pusat"
		ste_log.tipe_ste = "Material Receipt"
		ste_log.sumber_branch = company_doc.nama_cabang
		ste_log.apakan_ste = "Buat STE"
		ste_log.submit()
		self.transfer_status = "On The Way"

	elif company_doc.server == "Cabang" and self.transfer_ke_cabang_pusat == 1 and self.cabang_atau_pusat == "Cabang" and self.transfer_ke_cabang_mana and self.purpose == "Material Issue":
		ste_log = frappe.new_doc("STE Log")
		ste_log.nama_dokumen = self.name
		ste_log.transfer_ke = "Cabang"
		ste_log.data = frappe.as_json(self)
		ste_log.stat = "Terbuat di Cabang"
		ste_log.company = self.company
		ste_log.buat_ste_di = "Cabang"
		ste_log.tipe_ste = "Material Receipt"
		ste_log.sumber_branch = company_doc.nama_cabang
		ste_log.cabang = self.transfer_ke_cabang_mana
		ste_log.apakan_ste = "Buat STE"
		ste_log.submit()
		self.transfer_status = "On The Way"

	elif company_doc.server == "Pusat" and self.transfer_ke_cabang_pusat == 1 and self.cabang_atau_pusat == "Cabang" and self.transfer_ke_cabang_mana and self.purpose == "Material Issue":
		ste_log = frappe.new_doc("STE Log")
		ste_log.nama_dokumen = self.name
		ste_log.transfer_ke = "Cabang"
		ste_log.data = frappe.as_json(self)
		ste_log.stat = "Terbuat di Cabang"
		ste_log.company = self.company
		ste_log.buat_ste_di = "Cabang"
		ste_log.tipe_ste = "Material Receipt"
		ste_log.cabang = self.transfer_ke_cabang_mana
		ste_log.sumber_branch = company_doc.nama_cabang
		ste_log.apakan_ste = "Buat STE"
		ste_log.submit()
		self.transfer_status = "On The Way"

	elif self.ste_log and company_doc.server == "Pusat" and self.purpose == "Material Receipt" :
		ste_log_document = frappe.get_doc("STE Log", self.ste_log)

		ste_log = frappe.new_doc("STE Log")
		ste_log.nama_dokumen = self.name
		ste_log.transfer_ke = "Pusat"
		ste_log.data = frappe.as_json(self)
		ste_log.stat = "Terbuat di Pusat - DONE"
		ste_log.company = self.company
		ste_log.buat_ste_di = "Cabang"
		ste_log.tipe_ste = "Material Issue"
		ste_log.cabang = ste_log_document.cabang
		ste_log.sumber_branch = ste_log_document.sumber_branch
		ste_log.apakan_ste = "Update STE"
		ste_log.ste_yang_diupdate = ste_log_document.nama_dokumen
		ste_log.submit()
		self.transfer_status = "From Sync"

	elif self.ste_log and company_doc.server == "Cabang" and self.purpose == "Material Receipt" :
		ste_log_document = frappe.get_doc("STE Log", self.ste_log)
		self.transfer_status = "From Sync"
		if ste_log_document.sumber_branch ==  company_doc.nama_cabang :
			ste_log = frappe.new_doc("STE Log")
			ste_log.nama_dokumen = self.name
			ste_log.transfer_ke = "Cabang"
			ste_log.data = frappe.as_json(self)
			ste_log.stat = "Terbuat di Cabang - DONE"
			ste_log.company = self.company
			ste_log.buat_ste_di = "Pusat"
			ste_log.tipe_ste = "Material Issue"
			ste_log.cabang = ste_log_document.sumber_branch
			ste_log.sumber_branch = ste_log_document.sumber_branch
			ste_log.apakan_ste = "Update STE"
			ste_log.ste_yang_diupdate = ste_log_document.nama_dokumen
			ste_log.submit()
		elif ste_log_document.sumber_branch != company_doc.nama_cabang:
			ste_log = frappe.new_doc("STE Log")
			ste_log.nama_dokumen = self.name
			ste_log.transfer_ke = "Cabang"
			ste_log.data = frappe.as_json(self)
			ste_log.stat = "Terbuat di Cabang - DONE"
			ste_log.company = self.company
			ste_log.buat_ste_di = "Cabang"
			ste_log.tipe_ste = "Material Issue"
			ste_log.cabang =  ste_log_document.sumber_branch
			ste_log.sumber_branch = ste_log_document.sumber_branch
			ste_log.apakan_ste = "Update STE"
			ste_log.ste_yang_diupdate = ste_log_document.nama_dokumen
			ste_log.submit()


@frappe.whitelist()
def debug_ste_log():
	list_ste = ["STEI-HO-1-22-07-01396",
		"STEI-HO-1-22-07-01427",
		"STEI-HO-1-22-07-01434",
		"STEI-HO-1-22-07-01435",
		"STEI-HO-1-22-07-01436",
		"STEI-HO-1-22-07-01437",
		"STEI-HO-1-22-07-01444",
		"STEI-HO-1-22-07-01445",
		"STEI-HO-1-22-07-01446",
		"STEI-HO-1-22-07-01447",
		"STEI-HO-1-22-07-01448",
		"STEI-HO-1-22-07-01449",
		"STEI-HO-1-22-07-01450",
		"STEI-HO-1-22-07-01451",
		"STEI-HO-1-22-07-01452",
		"STEI-HO-1-22-07-01453",
		"STEI-HO-1-22-07-01454",
		"STEI-HO-1-22-07-01455",
		"STEI-HO-1-22-07-01456",
		"STEI-HO-1-22-07-01457",
		"STEI-HO-1-22-07-01458",
		"STEI-HO-1-22-07-01459",
		"STEI-HO-1-22-07-01460",
		"STEI-HO-1-22-07-01461",
		"STEI-HO-1-22-07-01462",
		"STEI-HO-1-22-07-01463",
		"STEI-HO-1-22-07-01465",
		"STEI-HO-1-22-07-01466",
		"STEI-HO-1-22-07-01467",
		"STEI-HO-1-22-07-01468",
		"STEI-HO-1-22-07-01469",
		"STEI-HO-1-22-07-01470",
		"STEI-HO-1-22-07-01471",
		"STEI-HO-1-22-07-01472",
		"STEI-HO-1-22-07-01473",
		"STEI-HO-1-22-07-01474"]
	for row in list_ste:
		debug_buat_ste_log(row)

@frappe.whitelist()
def create_ste_resolve_debug():

	company_doc = frappe.get_doc("Company","GIAS")
	if company_doc.server == "Pusat":
		return

	list_ste = frappe.db.sql(""" SELECT docname FROM
		`tabEvent Sync Log` WHERE 
		`error` LIKE "%cannot import name 'check_list_company_gias' from 'addons.custom_method' (apps/addons/addons/custom_method.py)%"

		AND NAME NOT IN (SELECT ste_log FROM `tabStock Entry`) """)

	for row_baris in list_ste:
		print(row_baris[0])
		self = frappe.get_doc("STE Log",row_baris[0])
		if self.company:
			company_doc = frappe.get_doc("Company",self.company)
			
			if company_doc.server == "Pusat" and self.buat_ste_di == "Pusat" and self.tipe_ste == "Material Receipt":
				if self.apakan_ste == "Buat STE":
					cabang_doc = frappe.get_doc("List Company GIAS",company_doc.nama_cabang)
					self.stat = "Terbuat di Pusat - Resolve"
					self.db_update()
					# buat ste
					ste_baru = json.loads(self.data)
					ste_baru["name"] = ""
					ste_baru["cabang"] = ""
					ste_baru["branch"] = cabang_doc.accounting_dimension
					ste_baru["cabang_atau_pusat"] = ""
					ste_baru["purpose"] = self.tipe_ste
					ste_baru["stock_entry_type"] = self.tipe_ste
					ste_baru["title"] = self.tipe_ste
					ste_baru["transfer_ke_cabang_pusat"] = 0
					ste_baru["ste_log"] = self.name
					ste_baru["workflow_state"] = "Pending"
					ste_baru["docstatus"] = 0
					ste_baru["from_warehouse"] = ""
					ste_baru["to_warehouse"] = ""
					ste_baru["sync_name"] = self.nama_dokumen
					ste_baru["letter_head"] = ""
								
					ste_baru["amended_from"] = ""
					for row in ste_baru["items"]:
						if self.tipe_ste == "Material Receipt":
							row["s_warehouse"] = ""
							# row["warehouse_cabang"] = row["t_warehouse"]
							row["t_warehouse"] = cabang_doc.warehouse_penerimaan_dari_pusat
							
							row["basic_rate"] = row["valuation_rate"]
							row["pusat_valuation_rate"] = row["valuation_rate"]

							if row["basic_rate"] == 0:
								row["allow_zero_valuation_rate"] = 1
							else:
								row["allow_zero_valuation_rate"] = 0

						row["cost_center"] = company_doc.cost_center

						row["material_request"] = ""
						row["material_request_item"] = ""

						row["branch"] = cabang_doc.accounting_dimension

					if ste_baru["total_additional_costs_transfer"]:
						ste_baru["total_additional_costs"] = ste_baru["total_additional_costs_transfer"]
						ste_baru["cost_by"] = ste_baru["cost_by_transfer"]
						ste_baru["additional_costs"] = ste_baru["additional_costs_transfer_table"]
						ste_baru["total_additional_costs_transfer"] = 0
						ste_baru["cost_by_transfer"] = ""
						ste_baru["additional_costs_transfer_table"] = []

					ste = frappe.get_doc(ste_baru)
					ste.save()
					self.submit()

			elif company_doc.server == "Cabang" and self.buat_ste_di == "Cabang" and self.tipe_ste == "Material Receipt" and self.cabang == company_doc.nama_cabang:
				if self.apakan_ste == "Buat STE":
					cabang_doc = frappe.get_doc("List Company GIAS",self.cabang)
					self.stat = "Terbuat di Cabang - Resolve"
					self.db_update()
					# buat ste
					ste_baru = json.loads(self.data)
					ste_baru["name"] = ""
					ste_baru["cabang"] = ""
					ste_baru["branch"] = cabang_doc.accounting_dimension
					ste_baru["cabang_atau_pusat"] = ""
					ste_baru["purpose"] = self.tipe_ste
					ste_baru["stock_entry_type"] = self.tipe_ste
					ste_baru["title"] = self.tipe_ste
					ste_baru["transfer_ke_cabang_pusat"] = 0
					ste_baru["ste_log"] = self.name
					ste_baru["workflow_state"] = "Pending"
					ste_baru["docstatus"] = 0
					ste_baru["from_warehouse"] = ""
					ste_baru["to_warehouse"] = ""
					ste_baru["amended_from"] = ""
					ste_baru["dari_list_company"] = self.sumber_branch
					ste_baru["sync_name"] = self.nama_dokumen
					ste_baru["letter_head"] = ""
					ste_baru["deleted_items"] = []

					for row in ste_baru["items"]:
						if self.tipe_ste == "Material Receipt":
							row["s_warehouse"] = ""
							# warehouse_dari_pusat = row["t_warehouse"]
							# row["warehouse_pusat"] = warehouse_dari_pusat
							row["t_warehouse"] = cabang_doc.warehouse_penerimaan_dari_pusat
							row["basic_rate"] = row["valuation_rate"]
							row["pusat_valuation_rate"] = row["valuation_rate"]
							
							if row["basic_rate"] == 0:
								row["allow_zero_valuation_rate"] = 1
							else:
								row["allow_zero_valuation_rate"] = 0

						row["material_request"] = ""
						row["material_request_item"] = ""
						row["cost_center"] = company_doc.cost_center

						row["branch"] = cabang_doc.accounting_dimension

					if ste_baru["total_additional_costs_transfer"]:
						ste_baru["total_additional_costs"] = ste_baru["total_additional_costs_transfer"]
						ste_baru["cost_by"] = ste_baru["cost_by_transfer"]
						ste_baru["additional_costs"] = ste_baru["additional_costs_transfer_table"]
						ste_baru["total_additional_costs_transfer"] = 0
						ste_baru["cost_by_transfer"] = ""
						ste_baru["additional_costs_transfer_table"] = []

					ste = frappe.get_doc(ste_baru)
					ste.save()
					self.submit()


@frappe.whitelist()
def create_ste_resolve(self,method):
	if self.company:
		company_doc = frappe.get_doc("Company",self.company)
		
		if ((company_doc.server == "Pusat" and self.buat_ste_di == "Pusat") or (company_doc.server == "Pusat" and company_doc.nama_cabang) == self.cabang ) and self.tipe_ste == "Material Receipt":
			if self.apakan_ste == "Buat STE":
				cabang_doc = frappe.get_doc("List Company GIAS",company_doc.nama_cabang)
				self.stat = "Terbuat di Pusat - Resolve"
				self.db_update()
				# buat ste
				ste_baru = json.loads(self.data)
				ste_baru["name"] = ""
				ste_baru["cabang"] = ""
				ste_baru["branch"] = cabang_doc.accounting_dimension
				ste_baru["cabang_atau_pusat"] = ""
				ste_baru["purpose"] = self.tipe_ste
				ste_baru["stock_entry_type"] = self.tipe_ste
				ste_baru["title"] = self.tipe_ste
				ste_baru["transfer_ke_cabang_pusat"] = 0
				ste_baru["ste_log"] = self.name
				ste_baru["workflow_state"] = "Pending"
				ste_baru["docstatus"] = 0
				ste_baru["from_warehouse"] = ""
				ste_baru["to_warehouse"] = ""
				ste_baru["sync_name"] = self.nama_dokumen
				ste_baru["letter_head"] = ""
							
				ste_baru["amended_from"] = ""
				for row in ste_baru["items"]:
					if self.tipe_ste == "Material Receipt":
						row["s_warehouse"] = ""
						# row["warehouse_cabang"] = row["t_warehouse"]
						row["t_warehouse"] = cabang_doc.warehouse_penerimaan_dari_pusat
						
						row["basic_rate"] = row["valuation_rate"]
						row["pusat_valuation_rate"] = row["valuation_rate"]

						if row["basic_rate"] == 0:
							row["allow_zero_valuation_rate"] = 1
						else:
							row["allow_zero_valuation_rate"] = 0

					row["cost_center"] = company_doc.cost_center

					row["material_request"] = ""
					row["material_request_item"] = ""

					row["branch"] = cabang_doc.accounting_dimension

				if ste_baru["total_additional_costs_transfer"]:
					ste_baru["total_additional_costs"] = ste_baru["total_additional_costs_transfer"]
					ste_baru["cost_by"] = ste_baru["cost_by_transfer"]
					ste_baru["additional_costs"] = ste_baru["additional_costs_transfer_table"]
					ste_baru["total_additional_costs_transfer"] = 0
					ste_baru["cost_by_transfer"] = ""
					ste_baru["additional_costs_transfer_table"] = []

				ste = frappe.get_doc(ste_baru)
				ste.save()
				self.submit()

		elif company_doc.server == "Cabang" and self.buat_ste_di == "Cabang" and self.tipe_ste == "Material Receipt" and self.cabang == company_doc.nama_cabang:
			if self.apakan_ste == "Buat STE":
				cabang_doc = frappe.get_doc("List Company GIAS",self.cabang)
				self.stat = "Terbuat di Cabang - Resolve"
				self.db_update()
				# buat ste
				ste_baru = json.loads(self.data)
				ste_baru["name"] = ""
				ste_baru["cabang"] = ""
				ste_baru["branch"] = cabang_doc.accounting_dimension
				ste_baru["cabang_atau_pusat"] = ""
				ste_baru["purpose"] = self.tipe_ste
				ste_baru["stock_entry_type"] = self.tipe_ste
				ste_baru["title"] = self.tipe_ste
				ste_baru["transfer_ke_cabang_pusat"] = 0
				ste_baru["ste_log"] = self.name
				ste_baru["workflow_state"] = "Pending"
				ste_baru["docstatus"] = 0
				ste_baru["from_warehouse"] = ""
				ste_baru["to_warehouse"] = ""
				ste_baru["amended_from"] = ""
				ste_baru["dari_list_company"] = self.sumber_branch
				ste_baru["sync_name"] = self.nama_dokumen
				ste_baru["letter_head"] = ""
				ste_baru["deleted_items"] = []
				

				for row in ste_baru["items"]:
					if self.tipe_ste == "Material Receipt":
						row["s_warehouse"] = ""
						# warehouse_dari_pusat = row["t_warehouse"]
						# row["warehouse_pusat"] = warehouse_dari_pusat
						row["t_warehouse"] = cabang_doc.warehouse_penerimaan_dari_pusat
						row["basic_rate"] = row["valuation_rate"]
						row["pusat_valuation_rate"] = row["valuation_rate"]
						
						if row["basic_rate"] == 0:
							row["allow_zero_valuation_rate"] = 1
						else:
							row["allow_zero_valuation_rate"] = 0

					row["material_request"] = ""
					row["material_request_item"] = ""
					row["cost_center"] = company_doc.cost_center

					row["branch"] = cabang_doc.accounting_dimension

				if ste_baru["total_additional_costs_transfer"]:
					ste_baru["total_additional_costs"] = ste_baru["total_additional_costs_transfer"]
					ste_baru["cost_by"] = ste_baru["cost_by_transfer"]
					ste_baru["additional_costs"] = ste_baru["additional_costs_transfer_table"]
					ste_baru["total_additional_costs_transfer"] = 0
					ste_baru["cost_by_transfer"] = ""
					ste_baru["additional_costs_transfer_table"] = []

				ste = frappe.get_doc(ste_baru)
				ste.save()
				self.submit()


@frappe.whitelist()
def debug_create_ste_resolve_plg():

	if frappe.get_doc("Company", "GIAS").server != "Cabang":
		return

	print(frappe.get_doc("Company", "GIAS").nama_cabang)
	list_kosong= frappe.db.sql("""  SELECT ste.name, stei.name
		FROM `tabSTE Log` ste
		LEFT JOIN `tabStock Entry Detail` stei ON ste.`nama_dokumen` = stei.parent
		WHERE `data` LIKE "%STEI-PWT-1-23-10-00001%"
		HAVING stei.name IS NULL
	""")
	for sterow in list_kosong:
		list_ste_cabang = frappe.db.sql(""" 
			SELECT name FROM `tabSTE Log` WHERE `name` = "{}" ;
		""".format(sterow[0]))
		for satu_ste in list_ste_cabang:
			nama_ste_log = satu_ste[0]
			list_ste_log = frappe.db.sql(""" SELECT name FROM `tabSTE Log`  WHERE name = "{}" """.format(nama_ste_log))
			for row_log in list_ste_log:
				print("YES - {}".format(nama_ste_log))
				self = frappe.get_doc("STE Log", row_log[0])
				if self.company:
					company_doc = frappe.get_doc("Company",self.company)
					
					if company_doc.server == "Pusat" and self.buat_ste_di == "Pusat" and self.tipe_ste == "Material Receipt":
						if self.apakan_ste == "Buat STE":
							cabang_doc = frappe.get_doc("List Company GIAS",company_doc.nama_cabang)
							self.stat = "Terbuat di Pusat - Resolve"
							self.db_update()
							# buat ste
							ste_baru = json.loads(self.data)
							ste_baru["name"] = ""
							ste_baru["cabang"] = ""
							ste_baru["branch"] = cabang_doc.accounting_dimension
							ste_baru["cabang_atau_pusat"] = ""
							ste_baru["purpose"] = self.tipe_ste
							ste_baru["stock_entry_type"] = self.tipe_ste
							ste_baru["title"] = self.tipe_ste
							ste_baru["transfer_ke_cabang_pusat"] = 0
							ste_baru["ste_log"] = self.name
							ste_baru["workflow_state"] = "Pending"
							ste_baru["docstatus"] = 0
							ste_baru["from_warehouse"] = ""
							ste_baru["to_warehouse"] = ""
							ste_baru["sync_name"] = self.nama_dokumen
							ste_baru["letter_head"] = ""

							ste_baru["amended_from"] = ""
							for row in ste_baru["items"]:
								if self.tipe_ste == "Material Receipt":
									row["s_warehouse"] = ""
									# row["warehouse_cabang"] = row["t_warehouse"]
									row["t_warehouse"] = cabang_doc.warehouse_penerimaan_dari_pusat
									
									row["basic_rate"] = row["valuation_rate"]
									row["pusat_valuation_rate"] = row["valuation_rate"]

									if row["basic_rate"] == 0:
										row["allow_zero_valuation_rate"] = 1
									else:
										row["allow_zero_valuation_rate"] = 0

								row["cost_center"] = company_doc.cost_center

								row["material_request"] = ""
								row["material_request_item"] = ""

								row["branch"] = cabang_doc.accounting_dimension

							if ste_baru["total_additional_costs_transfer"]:
								ste_baru["total_additional_costs"] = ste_baru["total_additional_costs_transfer"]
								ste_baru["cost_by"] = ste_baru["cost_by_transfer"]
								ste_baru["additional_costs"] = ste_baru["additional_costs_transfer_table"]
								ste_baru["total_additional_costs_transfer"] = 0
								ste_baru["cost_by_transfer"] = ""
								ste_baru["additional_costs_transfer_table"] = []

							ste = frappe.get_doc(ste_baru)
							ste.save()
							self.submit()

					elif company_doc.server == "Cabang" and self.buat_ste_di == "Cabang" and self.tipe_ste == "Material Receipt" and self.cabang == company_doc.nama_cabang:
						if self.apakan_ste == "Buat STE":
							cabang_doc = frappe.get_doc("List Company GIAS",self.cabang)
							self.stat = "Terbuat di Cabang - Resolve"
							self.db_update()
							# buat ste
							ste_baru = json.loads(self.data)
							ste_baru["name"] = ""
							ste_baru["cabang"] = ""
							ste_baru["branch"] = cabang_doc.accounting_dimension
							ste_baru["cabang_atau_pusat"] = ""
							ste_baru["purpose"] = self.tipe_ste
							ste_baru["stock_entry_type"] = self.tipe_ste
							ste_baru["title"] = self.tipe_ste
							ste_baru["transfer_ke_cabang_pusat"] = 0
							ste_baru["ste_log"] = self.name
							ste_baru["workflow_state"] = "Pending"
							ste_baru["docstatus"] = 0
							ste_baru["from_warehouse"] = ""
							ste_baru["to_warehouse"] = ""
							ste_baru["amended_from"] = ""
							ste_baru["dari_list_company"] = self.sumber_branch
							ste_baru["sync_name"] = self.nama_dokumen
							ste_baru["letter_head"] = ""
							

							for row in ste_baru["items"]:
								if self.tipe_ste == "Material Receipt":
									row["s_warehouse"] = ""
									# warehouse_dari_pusat = row["t_warehouse"]
									# row["warehouse_pusat"] = warehouse_dari_pusat
									row["t_warehouse"] = cabang_doc.warehouse_penerimaan_dari_pusat
									row["basic_rate"] = row["valuation_rate"]
									row["pusat_valuation_rate"] = row["valuation_rate"]
									
									if row["basic_rate"] == 0:
										row["allow_zero_valuation_rate"] = 1
									else:
										row["allow_zero_valuation_rate"] = 0

								row["material_request"] = ""
								row["material_request_item"] = ""
								row["cost_center"] = company_doc.cost_center

								row["branch"] = cabang_doc.accounting_dimension

							if ste_baru["total_additional_costs_transfer"]:
								ste_baru["total_additional_costs"] = ste_baru["total_additional_costs_transfer"]
								ste_baru["cost_by"] = ste_baru["cost_by_transfer"]
								ste_baru["additional_costs"] = ste_baru["additional_costs_transfer_table"]
								ste_baru["total_additional_costs_transfer"] = 0
								ste_baru["cost_by_transfer"] = ""
								ste_baru["additional_costs_transfer_table"] = []
							ste = frappe.get_doc(ste_baru)

							ste.save()
							self.submit()

@frappe.whitelist()
def debug_create_ste_resolve():
	list_ste = frappe.db.sql(""" SELECT name FROM `tabSTE Log`
		WHERE nama_dokumen = "STEI-PWT-1-23-10-00001"
		 """)

	for sterow in list_ste:


		print(sterow[0])
		self = frappe.get_doc("STE Log",sterow[0])
		if self.company:
			company_doc = frappe.get_doc("Company",self.company)
			
			if company_doc.server == "Pusat" and self.buat_ste_di == "Pusat" and self.tipe_ste == "Material Receipt":
				if self.apakan_ste == "Buat STE":
					cabang_doc = frappe.get_doc("List Company GIAS",company_doc.nama_cabang)
					self.stat = "Terbuat di Pusat - Resolve"
					self.db_update()
					# buat ste
					ste_baru = json.loads(self.data)
					ste_baru["name"] = ""
					ste_baru["cabang"] = ""
					ste_baru["branch"] = cabang_doc.accounting_dimension
					ste_baru["cabang_atau_pusat"] = ""
					ste_baru["purpose"] = self.tipe_ste
					ste_baru["stock_entry_type"] = self.tipe_ste
					ste_baru["title"] = self.tipe_ste
					ste_baru["transfer_ke_cabang_pusat"] = 0
					ste_baru["ste_log"] = self.name
					ste_baru["workflow_state"] = "Pending"
					ste_baru["docstatus"] = 0
					ste_baru["from_warehouse"] = ""
					ste_baru["to_warehouse"] = ""

					ste_baru["amended_from"] = ""
					for row in ste_baru["items"]:
						if self.tipe_ste == "Material Receipt":
							row["s_warehouse"] = ""
							# row["warehouse_cabang"] = row["t_warehouse"]
							row["t_warehouse"] = cabang_doc.warehouse_penerimaan_dari_pusat
							if row["basic_rate"] == 0:
								row["allow_zero_valuation_rate"] = 1
							else:
								row["allow_zero_valuation_rate"] = 0

							row["basic_rate"] = row["valuation_rate"]
							row["pusat_valuation_rate"] = row["valuation_rate"]
						row["material_request"] = ""
						row["material_request_item"] = ""

						row["branch"] = cabang_doc.accounting_dimension

					if ste_baru["total_additional_costs_transfer"]:
						ste_baru["total_additional_costs"] = ste_baru["total_additional_costs_transfer"]
						ste_baru["cost_by"] = ste_baru["cost_by_transfer"]
						ste_baru["additional_costs"] = ste_baru["additional_costs_transfer_table"]
						ste_baru["total_additional_costs_transfer"] = 0
						ste_baru["cost_by_transfer"] = ""
						ste_baru["additional_costs_transfer_table"] = []

					ste = frappe.get_doc(ste_baru)
					frappe.throw(str(ste))

			elif company_doc.server == "Cabang" and self.buat_ste_di == "Cabang" and self.tipe_ste == "Material Receipt" and self.cabang == company_doc.nama_cabang:
				if self.apakan_ste == "Buat STE":
					cabang_doc = frappe.get_doc("List Company GIAS",self.cabang)
					self.stat = "Terbuat di Cabang - Resolve"
					self.db_update()
					# buat ste
					ste_baru = json.loads(self.data)
					ste_baru["name"] = ""
					ste_baru["cabang"] = ""
					ste_baru["branch"] = cabang_doc.accounting_dimension
					ste_baru["cabang_atau_pusat"] = ""
					ste_baru["purpose"] = self.tipe_ste
					ste_baru["stock_entry_type"] = self.tipe_ste
					ste_baru["title"] = self.tipe_ste
					ste_baru["transfer_ke_cabang_pusat"] = 0
					ste_baru["ste_log"] = self.name
					ste_baru["workflow_state"] = "Pending"
					ste_baru["docstatus"] = 0
					ste_baru["from_warehouse"] = ""
					ste_baru["to_warehouse"] = ""
					ste_baru["amended_from"] = ""
					ste_baru["dari_list_company"] = self.sumber_branch
					ste_baru["sync_name"] = self.nama_dokumen
					

					for row in ste_baru["items"]:
						if self.tipe_ste == "Material Receipt":
							row["s_warehouse"] = ""
							# warehouse_dari_pusat = row["t_warehouse"]
							# row["warehouse_pusat"] = warehouse_dari_pusat
							row["t_warehouse"] = cabang_doc.warehouse_penerimaan_dari_pusat
							if row["basic_rate"] == 0:
								row["allow_zero_valuation_rate"] = 1
							else:
								row["allow_zero_valuation_rate"] = 0
							
							row["basic_rate"] = row["valuation_rate"]
							row["pusat_valuation_rate"] = row["valuation_rate"]
							# row["basic_rate"] = row["valuation_rate"]
							# row["additional_cost"] = 0

						row["material_request"] = ""
						row["material_request_item"] = ""

						row["branch"] = cabang_doc.accounting_dimension

					if ste_baru["total_additional_costs_transfer"]:
						ste_baru["total_additional_costs"] = ste_baru["total_additional_costs_transfer"]
						ste_baru["cost_by"] = ste_baru["cost_by_transfer"]
						ste_baru["additional_costs"] = ste_baru["additional_costs_transfer_table"]
						ste_baru["total_additional_costs_transfer"] = 0
						ste_baru["cost_by_transfer"] = ""
						ste_baru["additional_costs_transfer_table"] = []

					ste = frappe.get_doc(ste_baru)
					ste.flags.ignore_validate = True
					ste.save()


		eventsync = frappe.get_doc("Event Sync Log",sterow[1])
		eventsync.status = "Completed"
		eventsync.db_update()

@frappe.whitelist()
def create_ste_resolve_issue(self,method):
	if self.company and self.docstatus == 1:
		company_doc = frappe.get_doc("Company",self.company)
	
		if company_doc.server == "Pusat" and self.buat_ste_di == "Cabang" and self.tipe_ste == "Material Issue" and self.sumber_branch == company_doc.nama_cabang and self.apakan_ste == "Update STE":
			ste_doc = frappe.get_doc("Stock Entry",self.ste_yang_diupdate)
			ste_doc.transfer_status = "Received"
			ste_doc.sync_name = self.nama_dokumen
			ste_doc.save()

		elif company_doc.server == "Cabang" and self.buat_ste_di == "Pusat" and self.tipe_ste == "Material Issue" and self.sumber_branch == company_doc.nama_cabang and self.apakan_ste == "Update STE":
			ste_doc = frappe.get_doc("Stock Entry",self.ste_yang_diupdate)
			ste_doc.transfer_status = "Received"
			ste_doc.sync_name = self.nama_dokumen
			ste_doc.save()

		elif company_doc.server == "Cabang" and self.buat_ste_di == "Cabang" and self.tipe_ste == "Material Issue" and self.sumber_branch == company_doc.nama_cabang and self.apakan_ste == "Update STE":
			ste_doc = frappe.get_doc("Stock Entry",self.ste_yang_diupdate)
			ste_doc.transfer_status = "Received"
			ste_doc.sync_name = self.nama_dokumen
			ste_doc.save()

@frappe.whitelist()
def debug_create_ste_resolve_issue2():
	self = frappe.get_doc("STE Log","STELOG-GIAS SPRINGHILL-07-12-2022-359478")
	if self.company and self.docstatus == 1:
		company_doc = frappe.get_doc("Company",self.company)
	
		if company_doc.server == "Pusat" and self.buat_ste_di == "Cabang" and self.tipe_ste == "Material Issue" and self.sumber_branch == company_doc.nama_cabang and self.apakan_ste == "Update STE":
			ste_doc = frappe.get_doc("Stock Entry",self.ste_yang_diupdate)
			ste_doc.transfer_status = "Received"
			ste_doc.sync_name = self.nama_dokumen
			ste_doc.save()

		elif company_doc.server == "Cabang" and self.buat_ste_di == "Pusat" and self.tipe_ste == "Material Issue" and self.sumber_branch == company_doc.nama_cabang and self.apakan_ste == "Update STE":
			ste_doc = frappe.get_doc("Stock Entry",self.ste_yang_diupdate)
			ste_doc.transfer_status = "Received"
			ste_doc.sync_name = self.nama_dokumen
			ste_doc.save()

		elif company_doc.server == "Cabang" and self.buat_ste_di == "Cabang" and self.tipe_ste == "Material Issue" and self.sumber_branch == company_doc.nama_cabang and self.apakan_ste == "Update STE":
			ste_doc = frappe.get_doc("Stock Entry",self.ste_yang_diupdate)
			ste_doc.transfer_status = "Received"
			ste_doc.sync_name = self.nama_dokumen
			ste_doc.save()
	else:
		print("fail")

@frappe.whitelist()
def debug_create_ste_resolve_issue():
	self = frappe.get_doc("STE Log","STELOG-GIAS SPRINGHILL-07-12-2022-359478")
	if self.company:
		company_doc = frappe.get_doc("Company",self.company)
		if company_doc.server == "Cabang" and self.buat_ste_di == "Cabang" and self.tipe_ste == "Material Issue" and self.cabang == company_doc.nama_cabang:
			cabang_doc = frappe.get_doc("List Company GIAS",company_doc.nama_cabang)
			self.stat = "Terbuat di Pusat - Resolve"
			self.db_update()
			# buat ste
			ste_baru = json.loads(self.data)
			ste_baru["name"] = ""
			
			ste_baru["branch"] = cabang_doc.accounting_dimension
			ste_baru["cabang_atau_pusat"] = ""
			ste_baru["purpose"] = self.tipe_ste
			ste_baru["stock_entry_type"] = self.tipe_ste
			ste_baru["title"] = self.tipe_ste
			ste_baru["transfer_ke_cabang_pusat"] = 0
			ste_baru["ste_log"] = self.name
			ste_baru["workflow_state"] = "Pending"
			ste_baru["docstatus"] = 1
			ste_baru["amended_from"] = ""
			for row in ste_baru["items"]:
				if self.tipe_ste == "Material Issue":
					if "warehouse_cabang" in row:
						row["s_warehouse"] = row["warehouse_cabang"]
						row["warehouse_pusat"] = row["t_warehouse"]
					else:
						row["s_warehouse"] = row["warehouse_pusat"]
						
					row["t_warehouse"] = ""
					if row["basic_rate"] == 0:
						row["allow_zero_valuation_rate"] = 1
					else:
						row["allow_zero_valuation_rate"] = 0
				row["branch"] = cabang_doc.accounting_dimension
				row["material_request"] = ""
				row["material_request_item"] = ""
			ste = frappe.get_doc(ste_baru)
			ste.flags.ignore_validate = True
			ste.submit()

		elif company_doc.server == "Pusat" and self.buat_ste_di == "Pusat" and self.tipe_ste == "Material Issue":
			cabang_doc = frappe.get_doc("List Company GIAS",self.sumber_branch)
			self.stat = "Terbuat di Pusat - Resolve"
			self.db_update()
			# buat ste
			ste_baru = json.loads(self.data)
			ste_baru["name"] = ""
			
			ste_baru["branch"] = cabang_doc.accounting_dimension
			ste_baru["cabang_atau_pusat"] = ""
			ste_baru["purpose"] = self.tipe_ste
			ste_baru["stock_entry_type"] = self.tipe_ste
			ste_baru["title"] = self.tipe_ste
			ste_baru["transfer_ke_cabang_pusat"] = 0
			ste_baru["ste_log"] = self.name
			ste_baru["workflow_state"] = "Pending"
			ste_baru["docstatus"] = 1
			ste_baru["amended_from"] = ""
			for row in ste_baru["items"]:
				if self.tipe_ste == "Material Issue":
					row["s_warehouse"] = row["warehouse_pusat"]
					row["t_warehouse"] = ""
					if row["basic_rate"] == 0:
						row["allow_zero_valuation_rate"] = 1
					else:
						row["allow_zero_valuation_rate"] = 0
				row["branch"] = cabang_doc.accounting_dimension
				row["material_request"] = ""
				row["material_request_item"] = ""
				row["valuation_rate_dari_cabang"] = row["pusat_valuation_rate"]
			ste = frappe.get_doc(ste_baru)
			ste.flags.ignore_validate = True
			ste.submit()
		else:
			print("FAIL {} - {} - {}".format(company_doc.server,self.buat_ste_di,self.tipe_ste))

@frappe.whitelist()
def ste_log_check_submit(doc,method):	
	if self.ste_log and self.purpose == "Material Receipt":
		ste_log_document = frappe.get_doc("STE Log", self.ste_log)

		ste_log = frappe.new_doc("STE Log")
		ste_log.nama_dokumen = self.name
		ste_log.transfer_ke = ste_log_document.transfer_ke
		ste_log.data = frappe.as_json(self)
		ste_log.company = self.company
		ste_log.buat_ste_di = "Cabang"
		ste_log.tipe_ste = "Material Issue"
		ste_log.sumber_branch = ste_log_document.sumber_branch
		ste_log.submit()

@frappe.whitelist()
def debug_ste_log_check_submit():	
	self = frappe.get_doc("Stock Entry","MAT-STEE-2021-00079")
	if self.ste_log:
		ste_log_document = frappe.get_doc("STE Log", self.ste_log)

		ste_log = frappe.new_doc("STE Log")
		ste_log.nama_dokumen = self.name
		ste_log.transfer_ke = "Pusat"
		ste_log.data = frappe.as_json(self)
		ste_log.stat = "Terbuat di Pusat - DONE"
		ste_log.company = self.company
		ste_log.buat_ste_di = "Cabang"
		ste_log.tipe_ste = "Material Issue"
		ste_log.sumber_branch = ste_log_document.sumber_branch
		ste_log.submit()

@frappe.whitelist()
def get_warehouse_transit_cabang(cabang):
	return frappe.db.sql(""" SELECT warehouse_transit FROM `tabList Company GIAS` WHERE name = "{}" """.format(cabang))


@frappe.whitelist()
def fix():
	list_ste = frappe.db.sql(""" 
		SELECT voucher_type,voucher_no FROM `tabGL Entry` WHERE voucher_type = "Stock Entry"
        and voucher_no IN 
        	(
        	"STE-BKL-1-23-06-00010"
			)
        GROUP BY voucher_no
        ORDER BY posting_date

    """)

	for row in list_ste:
		repair_gl_entry_untuk_ste(row[0],row[1])
		print(row[1])


@frappe.whitelist()
def repair_gl_entry_tanpa_sl(doctype,docname):
	
	doc = frappe.get_doc(doctype, docname)	
	company_doc = frappe.get_doc("Company",doc.company)
	if company_doc.server == "Cabang":
		if doc.sync_name:
			doc.rk_value = 0
			rk_value = frappe.db.sql(""" SELECT SUM(debit) FROM `db_pusat`.`tabGL Entry` WHERE account = "1168.04 - R/K STOCK - G" and voucher_no = "{}" """.format(doc.sync_name))
			if rk_value:
				if rk_value[0]:
					if rk_value[0][0]:
						doc.rk_value = rk_value[0][0]
						doc.db_update()
		
	if doc.stock_entry_type == "Material Receipt" and doc.rk_value > 0 and doc.doctype == "Stock Entry":
		StockController.make_gl_entries = custom_make_gl_entries2

	if company_doc.server == "Pusat":
		check = frappe.db.sql(""" SELECT * FROM `tabCustom Field` WhERE name = "Stock Entry-dari_branch" """)
		if len(check) > 0 and doc.purpose == "Material Issue":
			if doc.get("dari_branch") == 1 and doc.stock_entry_type == "Material Issue":
				StockController.make_gl_entries = custom_make_gl_entries

	delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(docname))
	doc.make_gl_entries()

@frappe.whitelist()
def patch_rk_account():
	list_ste = frappe.db.sql(""" SELECT NAME FROM `tabStock Entry` WHERE name IN
		(
			"STER-BJM-1-23-08-00012"
		)
		""")
	for row_ste in list_ste:
		doc = frappe.get_doc("Stock Entry", row_ste[0])
		doc.auto_assign_to_rk_account = 1


		check = 0
		for row in doc.items:
			row.expense_account = "5001 - HARGA POKOK PENJUALAN - G"
			row.db_update()
			if row.expense_account != "3131 - SALDO AWAL STOCK - G":
				if doc.stock_entry_type == "Material Receipt":
					if row.t_warehouse:
						wh_doc = frappe.get_doc("Warehouse", row.t_warehouse)
						if wh_doc.rk_stock_account_1:
							if row.expense_account != wh_doc.rk_stock_account_1:
								row.expense_account = wh_doc.rk_stock_account_1 
								check = 1
								row.db_update()
		

		repair_gl_entry_untuk_ste("Stock Entry", row_ste[0])
		print(row_ste[0])
		frappe.db.commit()




@frappe.whitelist()
def pasang_rk_account(doc,method):
	if doc.stock_entry_type == "Material Issue":
		if doc.transfer_ke_cabang_pusat == 1:
			doc.auto_assign_to_rk_account = 1
			
	if doc.auto_assign_to_rk_account == 1:
		for row in doc.items:
			if row.expense_account != "3131 - SALDO AWAL STOCK - G":
				if doc.stock_entry_type == "Material Issue":
					if row.s_warehouse:
						wh_doc = frappe.get_doc("Warehouse", row.s_warehouse)
						if wh_doc.rk_stock_account_1:
							row.expense_account = wh_doc.rk_stock_account_1 

				elif doc.stock_entry_type == "Material Receipt":
					if row.t_warehouse:
						wh_doc = frappe.get_doc("Warehouse", row.t_warehouse)
						if wh_doc.rk_stock_account_1:
							row.expense_account = wh_doc.rk_stock_account_1 

@frappe.whitelist()
def autoname_document_ste(doc,method):

	company_doc = frappe.get_doc("Company", doc.company)
	list_company_gias_doc = frappe.get_doc("List Company GIAS",company_doc.nama_cabang)
	singkatan = list_company_gias_doc.singkatan_cabang
	
	if doc.stock_entry_type == "Material Receipt":
		doc.naming_series = """STER-{{singkatan}}-1-.YY.-.MM.-.#####""".replace("{{singkatan}}",singkatan)

	elif doc.stock_entry_type == "Material Issue":
		doc.naming_series = """STEI-{{singkatan}}-1-.YY.-.MM.-.#####""".replace("{{singkatan}}",singkatan)

	elif doc.stock_entry_type == "Repack":
		doc.naming_series = """STERE-{{singkatan}}-1-.YY.-.MM.-.#####""".replace("{{singkatan}}",singkatan)

	else:
		doc.naming_series = """STE-{{singkatan}}-1-.YY.-.MM.-.#####""".replace("{{singkatan}}",singkatan)		
	
	# doc.name = make_autoname(doc.naming_series, doc=doc)

	month = frappe.utils.formatdate(frappe.utils.getdate(doc.posting_date),"MM")
	year = frappe.utils.formatdate(frappe.utils.getdate(doc.posting_date),"YY")

	if doc.tax_or_non_tax == "Tax":
		tax = 1
	else:
		tax = 2

	if str(year) == "22" and tax == 1:
		doc.name = make_autoname(doc.naming_series.replace("-1-","-").replace(".YY.",year).replace(".MM.",month),doc=doc)
	else:
		doc.name = make_autoname(doc.naming_series.replace("-1-","-{}-".format(tax)).replace(".YY.",year).replace(".MM.",month), doc=doc)



@frappe.whitelist()
def custom_get_updates(producer_site, last_update, doctypes):
	"""Get all updates generated after the last update timestamp"""
	docs = producer_site.post_request({
			'cmd': 'frappe.event_streaming.doctype.event_update_log.event_update_log.get_update_logs_for_consumer_debug',
			'event_consumer': get_url(),
			'doctypes': frappe.as_json(doctypes),
			'last_update': last_update
	})

							
	return [frappe._dict(d) for d in (docs or [])]

@frappe.whitelist()
def custom_get_update_logs_for_consumer(event_consumer, doctypes, last_update):

	"""
	Fetches all the UpdateLogs for the consumer
	It will inject old un-consumed Update Logs if a doc was just found to be accessible to the Consumer
	"""

	from frappe.event_streaming.doctype.event_update_log.event_update_log import is_consumer_uptodate,get_unread_update_logs,mark_consumer_read

	if isinstance(doctypes, str):
		doctypes = frappe.parse_json(doctypes)
	
	from frappe.event_streaming.doctype.event_consumer.event_consumer import has_consumer_access

	consumer = frappe.get_doc('Event Consumer', event_consumer)
	docs = frappe.db.sql(""" SELECT 
							`update_type`, 
							`ref_doctype`,
							`docname`, `data`, `name`, `creation` 
							FROM `tabEvent Update Log`  
							WHERE ref_doctype = "Material Request"
							AND creation >= "2022-09-05 12:54:46.671339"
							
							AND (docname LIKE "%PKU%" OR docname LIKE "%HO%")

							ORDER BY creation DESC
							""", as_dict=1)
	# docs = frappe.get_list(
	# 		doctype='Event Update Log',
	# 		filters={'ref_doctype': ('in', doctypes),
	# 						 'creation': ('>', last_update)},
	# 		fields=['update_type', 'ref_doctype',
	# 						'docname', 'data', 'name', 'creation'],
	# 		order_by='creation desc'
	# )

	result = []
	to_update_history = []
	for d in docs:
		if (d.ref_doctype, d.docname) in to_update_history:
			# will be notified by background jobs
			continue

		if not has_consumer_access(consumer=consumer, update_log=d):
			continue

		if not is_consumer_uptodate(d, consumer):
			to_update_history.append((d.ref_doctype, d.docname))
			# get_unread_update_logs will have the current log
			old_logs = get_unread_update_logs(consumer.name, d.ref_doctype, d.docname)
			if old_logs:
				old_logs.reverse()
				result.extend(old_logs)
		else:
			result.append(d)


	for d in result:
		mark_consumer_read(update_log_name=d.name, consumer_name=consumer.name)

	result.reverse()
	return result