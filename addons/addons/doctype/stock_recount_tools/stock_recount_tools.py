# Copyright (c) 2022, das and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt,get_item_account_wise_additional_cost
from addons.custom_standard.custom_purchase_receipt import repair_gl_entry
import os
from frappe.utils import flt
from addons.custom_standard.custom_stock_entry import repair_gl_entry_untuk_ste
from addons.custom_standard.custom_journal_entry import custom_set_total_debit_credit
from frappe.utils.background_jobs import get_jobs
from frappe.desk.reportview import get_filters_cond, get_match_cond
from frappe.utils import nowdate, unique
from addons.custom_standard.custom_stock_entry import custom_distribute_additional_costs

class StockRecountTools(Document):
	def onload(self):
		check = 0
		jobs = get_jobs()
		enqueued_method = 'addons.addons.doctype.stock_recount_tools.stock_recount_tools.start_stock_recount_pr_mtr'
		if enqueued_method in jobs[frappe.local.site]:
			check = 1

		enqueued_method = 'addons.addons.doctype.stock_recount_tools.stock_recount_tools.start_stock_recount_stei'
		if enqueued_method in jobs[frappe.local.site]:
			check = 1

		enqueued_method = 'addons.addons.doctype.stock_recount_tools.stock_recount_tools.start_stock_recount_journal'
		if enqueued_method in jobs[frappe.local.site]:
			check = 1

		enqueued_method = 'addons.addons.doctype.stock_recount_tools.stock_recount_tools.start_stock_recount_pr_by_name'
		if enqueued_method in jobs[frappe.local.site]:
			check = 1

		enqueued_method = 'addons.addons.doctype.stock_recount_tools.stock_recount_tools.start_stock_recount_stei_by_name'
		if enqueued_method in jobs[frappe.local.site]:
			check = 1			

		if check == 0:
			if self.status != "Completed":
				frappe.db.sql(""" UPDATE `tabSingles` SET `value` = "Idle" WHERE doctype = "Stock Recount Tools" AND `field` = "status" """)
				self.status = "Idle"
		else:
			frappe.db.sql(""" UPDATE `tabSingles` SET `value` = "On Progress" WHERE doctype = "Stock Recount Tools" AND `field` = "status" """)
			self.status = "On Progress"

		frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 0 WHERE `field` = "bypass" """)
	
	def validate(self):
		if self.status != "Idle":
			self.status = "Idle"

	@frappe.whitelist()
	def start_pr_mtr(self):
		if self.status == "On Progress":
			frappe.throw("Stock Recount on progress, please check background jobs.")
		else:
			self.initiate_stock_recount_pr_mtr()

	@frappe.whitelist()
	def start_stei(self):
		if self.status == "On Progress":
			frappe.throw("Stock Recount on progress, please check background jobs.")
		else:
			self.initiate_stock_recount_stei()
	
	@frappe.whitelist()
	def start_journal(self):
		if self.status == "On Progress":
			frappe.throw("Stock Recount on progress, please check background jobs.")
		else:
			self.initiate_stock_recount_start_journal()
		
	@frappe.whitelist()
	def initiate_stock_recount_pr_mtr(self):
		
		if self.from_date and self.to_date:

			fromdate = self.from_date
			todate = self.to_date
			list_pr = frappe.db.sql(""" 
				SELECT pri.rate,pii.rate, pri.parent, pii.item_code, pin.posting_date, pri.name FROM `tabPurchase Invoice Item` pii
				JOIN `tabPurchase Receipt Item` pri on pri.`name` = pii.`pr_detail`
				JOIN `tabPurchase Receipt` pin on pin.name = pri.parent
				
				WHERE pri.rate != pii.`rate`
				AND pri.`docstatus` = 1
				AND pii.`docstatus` = 1

				and pin.posting_date >= "{}"
				and pin.posting_date <= "{}"
				AND pin.name NOT IN (SELECT name FROM `tabStock Recount History PR`)

				GROUP BY pri.name
				ORDER BY posting_date,parent, item_code
				""".format(fromdate,todate))

			list_mtr = frappe.db.sql(""" 
				SELECT ste.name
				FROM `tabStock Entry Detail` sed
				JOIN `tabStock Entry` ste on ste.name = sed.parent
				
				WHERE 
				ste.docstatus = 1 
				and (ste.stock_entry_type = "Material Transfer" or ste.stock_entry_type = "Adjustment In") 
				and ste.posting_date >= "{}"
				and ste.posting_date <= "{}"
				AND ste.name NOT IN (SELECT name FROM `tabStock Recount History STE`)

				GROUP BY ste.name
				ORDER BY ste.posting_date,sed.parent, sed.item_code
			""".format(fromdate,todate))

			list_pr_je = frappe.db.sql(""" 
				SELECT 
				pri.rate, poi.rate, pri.qty, pri.parent, poi.parent
				FROM `tabPurchase Receipt Item` pri
				JOIN `tabPurchase Order Item` poi ON poi.name = pri.`purchase_order_item`
				JOIN `tabPurchase Receipt` prdoc ON pri.parent = prdoc.name
				WHERE pri.rate != poi.`rate`
				AND pri.`docstatus` = 1
				AND poi.`docstatus` = 1
				AND prdoc.is_return = 0
				and prdoc.posting_date >= "{}"
				and prdoc.posting_date <= "{}"
				and prdoc.name NOT IN (SELECT purchase_receipt FROM `tabStock Recount Journal`)

				ORDER BY pri.parent
			""".format(fromdate,todate))

			if not self.difference_account:
				frappe.throw("Please input Difference Account as is needed for calculation for PO dan PRI difference.")

			if not self.total_difference_account:
				frappe.throw("Please input Total Difference Account as is needed for calculation for PO dan PRI difference.")

			if len(list_pr) == 0 and len(list_mtr) == 0 and len(list_pr_je):
				frappe.throw("No Data needed to be recount.")

			else:
				
				frappe.flags.repost_gl == True
				enqueued_method = 'addons.addons.doctype.stock_recount_tools.stock_recount_tools.start_stock_recount_pr_mtr'
				jobs = get_jobs()
				if not jobs or enqueued_method not in jobs[frappe.local.site]:
					frappe.enqueue(method=enqueued_method,timeout=2400, queue='default', **{'fromdate': fromdate, 'todate': todate, 'diff': self.difference_account, 'total_diff': self.total_difference_account})
					frappe.db.sql(""" UPDATE `tabSingles` SET `value` = "On Progress" WHERE doctype = "Stock Recount Tools" AND `field` = "status" """)
					frappe.db.commit()
					frappe.msgprint("Method has been successfully queued. Please wait for status and reload this doc to become idle again.")
				else:
					frappe.msgprint("Method has been queued before. Please wait for status to become idle again.")
		else:
			frappe.throw("Please input from date and to date to filter so data won't be overloaded.")

	@frappe.whitelist()
	def initiate_stock_recount_stei(self):
		
		if self.from_date and self.to_date:

			fromdate = self.from_date
			todate = self.to_date
			list_ste = frappe.db.sql(""" 
				SELECT ste.name, ste.`sync_name`
				FROM `tabStock Entry` ste 
				WHERE
				ste.posting_date >= "{}"
				AND ste.posting_date <= "{}"
				AND ste.stock_entry_type = "Material Issue"
				AND ste.`sync_name` IS NOT NULL
				and ste.docstatus = 1
				AND ste.name NOT IN (SELECT stock_entry FROM `tabStock Recount History STE`)
			""".format(fromdate,todate))

			if len(list_ste) == 0:
				frappe.throw("No Data needed to be recount.")

			else:
				
				frappe.flags.repost_gl == True
				enqueued_method = 'addons.addons.doctype.stock_recount_tools.stock_recount_tools.start_stock_recount_stei'
				jobs = get_jobs()
				if not jobs or enqueued_method not in jobs[frappe.local.site]:
					frappe.enqueue(method=enqueued_method,timeout=2400, queue='default', **{'fromdate': fromdate, 'todate': todate})
					frappe.db.sql(""" UPDATE `tabSingles` SET `value` = "On Progress" WHERE doctype = "Stock Recount Tools" AND `field` = "status" """)
					frappe.db.commit()
					frappe.msgprint("Method has been successfully queued. Please wait for status and reload this doc to become idle again.")
				else:
					frappe.msgprint("Method has been queued before. Please wait for status to become idle again.")
		else:
			frappe.throw("Please input from date and to date to filter so data won't be overloaded.")

	@frappe.whitelist()
	def initiate_stock_recount_start_journal(self):
		if self.from_date and self.to_date:
			fromdate = self.from_date
			todate = self.to_date

			list_pr_je = frappe.db.sql(""" 
				SELECT 
				pri.rate, poi.rate, pri.qty, pri.parent, poi.parent
				FROM `tabPurchase Invoice Item` pri
				JOIN `tabPurchase Order Item` poi ON poi.name = pri.`po_detail`
				JOIN `tabPurchase Invoice` prdoc ON pri.parent = prdoc.name
				WHERE pri.rate != poi.`rate`
				AND pri.`docstatus` = 1
				AND poi.`docstatus` = 1
				AND prdoc.is_return = 0
				and prdoc.posting_date >= "{}"
				and prdoc.posting_date <= "{}"
				and prdoc.name NOT IN (SELECT purchase_receipt FROM `tabStock Recount Journal`)

				ORDER BY pri.parent
			""".format(fromdate,todate))

			if not self.difference_account:
				frappe.throw("Please input Difference Account as is needed for calculation for PO dan PRI difference.")


			if len(list_pr_je):
				frappe.throw("No Data needed to be recount.")

			else:
				
				frappe.flags.repost_gl == True
				enqueued_method = 'addons.addons.doctype.stock_recount_tools.stock_recount_tools.start_stock_recount_journal'
				jobs = get_jobs()
				if not jobs or enqueued_method not in jobs[frappe.local.site]:
					frappe.enqueue(method=enqueued_method,timeout=2400, queue='default', **{'fromdate': fromdate, 'todate': todate, 'diff': self.difference_account, 'total_diff': self.total_difference_account})
					frappe.db.sql(""" UPDATE `tabSingles` SET `value` = "On Progress" WHERE doctype = "Stock Recount Tools" AND `field` = "status" """)
					frappe.db.commit()
					frappe.msgprint("Method has been successfully queued. Please wait for status and reload this doc to become idle again.")
				else:
					frappe.msgprint("Method has been queued before. Please wait for status to become idle again.")
		else:
			frappe.throw("Please input from date and to date to filter so data won't be overloaded.")

	@frappe.whitelist()
	def recount_start(self):
		if self.status == "On Progress":
			frappe.throw("Stock Recount on progress, please check background jobs.")
		else:
			self.initiate_stock_recount()

	@frappe.whitelist()
	def initiate_stock_recount(self):
		
		if self.from_date and self.to_date:

			fromdate = self.from_date
			todate = self.to_date
			if self.ste_or_pr == "PR":
				if not self.purchase_receipt:
					frappe.throw("Please input Purchase Receipt number if recount per Document PR is needed.")

			if self.ste_or_pr == "STE":
				if not self.stock_entry:
					frappe.throw("Please input Stock Entry number if recount per Document STE is needed.")

			if self.ste_or_pr == "PR":
				list_pr = frappe.db.sql(""" 
					SELECT pri.rate,pii.rate, pri.parent, pii.item_code FROM `tabPurchase Invoice Item` pii
					JOIN `tabPurchase Receipt Item` pri on pri.`name` = pii.`pr_detail`
					JOIN `tabPurchase Receipt` pr on pr.`name` = pri.`parent`
					JOIN `tabPurchase Invoice` pin on pin.name = pii.parent
					
					WHERE pr.name = "{}"
					AND pri.`docstatus` = 1
					AND pii.`docstatus` = 1
					GROUP BY pri.name
					ORDER BY pr.posting_date,pr.parent, pii.item_code
					
					""".format(self.purchase_receipt))

				if len(list_pr) != 0:
					frappe.flags.repost_gl == True
					enqueued_method = 'addons.addons.doctype.stock_recount_tools.stock_recount_tools.start_stock_recount_pr_by_name'
					jobs = get_jobs()
					if not jobs or enqueued_method not in jobs[frappe.local.site]:
						frappe.enqueue(method=enqueued_method,timeout=2400, queue='default', **{'name': self.purchase_receipt})
						frappe.db.sql(""" UPDATE `tabSingles` SET `value` = "On Progress" WHERE doctype = "Stock Recount Tools" AND `field` = "status" """)
						frappe.db.commit()
						frappe.msgprint("Method has been successfully queued. Please wait for status and reload this doc to become idle again.")
					else:
						frappe.msgprint("Method has been queued before. Please wait for status to become idle again.")
			else:
				list_ste = frappe.db.sql(""" 
					SELECT ste.name, ste.`sync_name`
					FROM `tabStock Entry` ste 
					WHERE ste.name = "{}"
					and ste.docstatus = 1
				""".format(self.stock_entry))

				if len(list_ste) == 0:
					frappe.throw("No Data needed to be recount.")

				else:
					
					frappe.flags.repost_gl == True
					enqueued_method = 'addons.addons.doctype.stock_recount_tools.stock_recount_tools.start_stock_recount_stei_by_name'
					jobs = get_jobs()
					if not jobs or enqueued_method not in jobs[frappe.local.site]:
						frappe.enqueue(method=enqueued_method,timeout=2400, queue='default', **{'name': self.stock_entry})
						frappe.db.sql(""" UPDATE `tabSingles` SET `value` = "On Progress" WHERE doctype = "Stock Recount Tools" AND `field` = "status" """)
						frappe.db.commit()
						frappe.msgprint("Method has been successfully queued. Please wait for status and reload this doc to become idle again.")
					else:
						frappe.msgprint("Method has been queued before. Please wait for status to become idle again.")

				
		else:
			frappe.throw("Please input from date and to date to filter so data won't be overloaded.")

@frappe.whitelist()
def create_je_hpp(fromdate,todate, difference_account, total_difference_account):
	list_pr_je = frappe.db.sql(""" 
		SELECT 
		pri.rate, poi.rate, pri.qty, pri.parent, poi.parent,
		pri.`cost_center`, pri.branch,pri.item_code
		FROM `tabPurchase Invoice Item` pri
		JOIN `tabPurchase Receipt Item` poi ON poi.name = pri.`po_detail`
		JOIN `tabPurchase Invoice` prdoc ON pri.parent = prdoc.name
		WHERE pri.rate != poi.`rate`
		AND pri.`docstatus` = 1
		AND poi.`docstatus` = 1
		AND prdoc.is_return = 0
		and prdoc.posting_date >= "{}"
		and prdoc.posting_date <= "{}"
		and prdoc.name NOT IN (SELECT purchase_receipt FROM `tabStock Recount Journal`)

		ORDER BY pri.parent
	""".format(fromdate,todate))

	je_doc = frappe.new_doc("Journal Entry")
	total_debit = 0
	total_credit = 0
	single_doc = frappe.get_doc("Stock Recount Tools")


	list_je = []

	for row in list_pr_je:
		rate = (flt(row[0])-flt(row[1])) * flt(row[2])
		if abs(rate) >= 0.01:
			if rate < 0:

				total_credit += rate * -1
				je_doc.append("accounts",{
					"account" : difference_account,
					"credit": rate*-1,
					"credit_in_account_currency": rate*-1,
					"cost_center" : row[5],
					"branch": row[6],
					"user_remark":"Difference from PR {} and PI {} Item {}".format(row[4],row[3],row[7])
				})
				if row[3] not in list_je:
					list_je.append(row[3])

			elif rate > 0:

				total_debit += rate
				je_doc.append("accounts",{
					"account" : difference_account,
					"debit": rate,
					"debit_in_account_currency": rate,
					"cost_center" : row[5],
					"branch": row[6],
					"user_remark":"Difference from PR {} and PI {} Item {}".format(row[4],row[3],row[7])
				})
				if row[3] not in list_je:
					list_je.append(row[3])

	difference_amount = total_debit - total_credit
	custom_set_total_debit_credit(je_doc)
	je_doc.total_debit, je_doc.total_credit = 0, 0
	diff = flt(je_doc.difference, je_doc.precision("difference"))

	# If any row without amount, set the diff on that row
	if diff:
		blank_row = None
		for d in je_doc.get('accounts'):
			if not d.credit_in_account_currency and not d.debit_in_account_currency and diff != 0:
				blank_row = d

		if not blank_row:
			blank_row = je_doc.append('accounts', {})
		blank_row.account = total_difference_account
		blank_row.cost_center = "MAIN - G"
		blank_row.branch = "SPRINGHILL"
		blank_row.exchange_rate = 1
		if diff>0:
			blank_row.credit_in_account_currency = diff
			blank_row.credit = diff
		elif diff<0:
			blank_row.debit_in_account_currency = abs(diff)
			blank_row.debit = abs(diff)

	je_doc.remark = "Adjustment HPP from Stock Recount Tools"
	je_doc.posting_date = frappe.utils.nowdate()
	je_doc.save()

	for baris in list_je:
		row = single_doc.append('journal_scope', {})
		row.journal_entry = je_doc.name
		row.purchase_receipt = baris
		row.db_update()

	# frappe.msgprint("Method has been successfully queued. Please wait for status and reload this doc to become idle again.")

@frappe.whitelist()
def debug_start_stock_recount_pr_by_name():
	list_pr = frappe.db.sql(""" 
		SELECT parent FROM `tabPurchase Receipt Item`
		WHERE parent IN ("PRI-HO-1-23-10-00421")
		AND parent NOT IN (SELECT NAME FROM `tabStock Recount History PR` WHERE TIMESTAMP(last_update)>="2023-05-12")
		GROUP BY parent """)

	for row in list_pr:
		start_stock_recount_pr_by_name(row[0])
		print("========sekarang di {} =============".format(row[0]))


@frappe.whitelist()
def lakukan_recount_purchase_receipt_awal(no_prec, rate_baru, item_code, pri_name, include_tax=1):
	pri = frappe.get_doc("Purchase Receipt", no_prec)
	for row in pri.items:
		if row.item_code == item_code and row.name == pri_name:
			row.price_list_rate = rate_baru
			row.discount_amount = 0
			row.margin_rate_or_amount = 0
			row.discount_percentage = 0
			row.rate = rate_baru

	pri.calculate_taxes_and_totals()

	for row in pri.items:
		row.valuation_rate = row.net_rate
		row.db_update()

	for row in pri.taxes:
		row.db_update()

	pri.db_update()
	frappe.db.commit()

@frappe.whitelist()
def start_stock_recount_pr_by_name(name):
	try:
		list_pr = frappe.db.sql(""" 
			SELECT pri.rate,pii.rate, pri.parent, pii.item_code, pin.posting_date, pri.name 
			,ap.name,cd.name,IFNULL(ptc.included_in_print_rate,1)
			FROM `tabPurchase Invoice Item` pii
			JOIN `tabPurchase Receipt Item` pri on pri.`name` = pii.`pr_detail`
			JOIN `tabPurchase Receipt` pr on pr.`name` = pri.`parent`
			JOIN `tabPurchase Invoice` pin on pin.name = pii.parent

			LEFT JOIN `tabAccounting Period` ap
			ON ap.start_date <= pin.`posting_date`
			AND ap.`end_date` >= pin.`posting_date`
			LEFT JOIN 
			`tabClosed Document` cd
			ON ap.name = cd.parent
			AND cd.closed = 1
			AND cd.document_type IN ("Purchase Receipt")
			LEFT JOIN
			`tabPurchase Taxes and Charges` ptc ON ptc.parent = pin.name
			WHERE pr.name = "{}"
			AND pri.`docstatus` = 1
			AND pii.`docstatus` = 1
			GROUP BY pri.name
			HAVING cd.name IS NULL OR cd.name IS NOT NULL
			ORDER BY pr.posting_date,pr.parent, pii.item_code
			""".format(name))

		single_doc = frappe.get_doc("Stock Recount Tools")

		kotak_pr = []
		frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 0 WHERE `field` = "bypass" """)
		frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 1 WHERE `field` = "bypass" """)
		for row in list_pr:
			lakukan_recount_purchase_receipt(row[2],row[1],row[3], row[5],row[8])
			print(row[2])
			if row[2] not in kotak_pr:
				kotak_pr.append(row[2])
		
		for row in kotak_pr:
			cek_status_dan_repost_purchase_receipt(row)

		for row in kotak_pr:
			print("ini {}".format(row))
			frappe.enqueue(method="addons.addons.doctype.stock_recount_tools.stock_recount_tools.history_prec_complete",timeout=2400, queue='default',**{'pr': row} )

		for row in list_pr:
			print("stesync-{}".format(row[2]))
			lakukan_recount_ke_ste_sync(row[2],row[3])
			
		frappe.enqueue(method="addons.addons.doctype.stock_recount_tools.stock_recount_tools.recount_complete",timeout=2400, queue='default')
	except:
		frappe.enqueue(method="addons.addons.doctype.stock_recount_tools.stock_recount_tools.recount_failed",timeout=2400, queue='default')
		

@frappe.whitelist()
def start_stock_recount(fromdate,todate, diff):
	try:
		list_pr = frappe.db.sql(""" 
			SELECT pri.rate,pii.rate, pri.parent, pii.item_code, pin.posting_date, pri.name,IFNULL(ptc.included_in_print_rate,1) FROM `tabPurchase Invoice Item` pii
			JOIN `tabPurchase Receipt Item` pri on pri.`name` = pii.`pr_detail`
			JOIN `tabPurchase Receipt` pin on pin.name = pri.parent
			LEFT JOIN
			`tabPurchase Taxes and Charges` ptc ON ptc.parent = pin.name
			WHERE pri.rate != pii.`rate`
			AND pri.`docstatus` = 1
			AND pii.`docstatus` = 1

			and pin.posting_date >= "{}"
			and pin.posting_date <= "{}"

			GROUP BY pri.name
			ORDER BY posting_date,parent, item_code
			""".format(fromdate,todate))

		single_doc = frappe.get_doc("Stock Recount Tools")

		if len(list_pr) == 0:
			frappe.throw("No Data needed to be recount.")
		else:
			kotak_pr = []
			frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 1 WHERE `field` = "bypass" """)
			for row in list_pr:
				lakukan_recount_purchase_receipt(row[2],row[1],row[3], row[5],row[6])
				print(row[2])
				if row[2] not in kotak_pr:
					kotak_pr.append(row[2])
			
			for row in kotak_pr:
				print(row)
				cek_status_dan_repost_purchase_receipt(row)

			for row in list_pr:
				print("stesync-{}".format(row[2]))
				lakukan_recount_ke_ste_sync(row[2],row[3])
				list_pr = frappe.db.sql(""" SELECT purchase_receipt FROM `tabStock Recount History` WHERE purchase_receipt = "{}" """.format(row[2]))
				if len(list_pr) == 0:
					baris_baru = single_doc.append('history', {})
					baris_baru.purchase_receipt = row[2]
					baris_baru.posting_date = row[4]
					baris_baru.db_update()

			frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 0 WHERE `field` = "bypass" """) 

		frappe.db.sql(""" UPDATE `tabSingles` SET `value` = "Completed" WHERE doctype = "Stock Recount Tools" AND `field` = "status" """)
		frappe.db.commit()
	except:
		frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 0 WHERE `field` = "bypass" """)
		frappe.db.sql(""" UPDATE `tabSingles` SET `value` = "Failed" WHERE doctype = "Stock Recount Tools" AND `field` = "status" """)
		frappe.db.commit()

@frappe.whitelist()
def lakukan_recount_purchase_receipt(no_prec, rate_baru, item_code, pri_name, include_tax=1):
	pri = frappe.get_doc("Purchase Receipt", no_prec)
	for row in pri.items:
		if row.item_code == item_code and row.name == pri_name:
			row.price_list_rate = rate_baru
			row.discount_amount = 0
			row.margin_rate_or_amount = 0
			row.discount_percentage = 0
			row.rate = rate_baru
	
	# for row in pri.taxes:
	# 	if row.rate > 0:
	# 		if row.included_in_print_rate != include_tax:
	# 			row.included_in_print_rate = include_tax

	pri.calculate_taxes_and_totals()

	for row in pri.items:
		row.valuation_rate = row.net_rate
		row.db_update()

	for row in pri.taxes:
		row.db_update()

	pri.db_update()
	frappe.db.commit()

@frappe.whitelist()
def cek_status_dan_repost_purchase_receipt(no_prec):
	pri = frappe.get_doc("Purchase Receipt", no_prec)

	kotak_po = []
	for row in pri.items:
		if row.purchase_order:
			if row.purchase_order not in kotak_po:
				kotak_po.append(row.purchase_order)

		if row.purchase_order_item:
			poi = frappe.get_doc("Purchase Order Item", row.purchase_order_item)	
			poi.price_list_rate = row.price_list_rate
			poi.discount_amount = 0
			poi.discount_percentage = 0
			poi.margin_rate_or_amount = 0
			poi.rate = row.rate
			print("{}-ini row rate".format(poi.rate))
			print("{}-ini row plrate".format(poi.price_list_rate))
			poi.db_update()

	frappe.db.commit()

	for row in kotak_po:
		po_doc = frappe.get_doc("Purchase Order", row)
		po_doc.calculate_taxes_and_totals()
		for rowpo in po_doc.items:
			rowpo.db_update()
		for rowtax in po_doc.taxes:
			rowtax.db_update()
		po_doc.db_update()

	frappe.db.commit()

	if pri.docstatus == 1:
		repair_gl_entry("Purchase Receipt", no_prec)

	frappe.db.commit()

	command = """ cd /home/frappe/frappe-bench/ && bench --site erp-pusat.gias.co.id execute erpnext.stock.doctype.repost_item_valuation.repost_item_valuation.debug_repost """
	os.system(command)
	frappe.db.commit()


@frappe.whitelist()
def lakukan_recount_ke_ste_sync(no_prec, item_code):
	frappe.flags.repost_gl == True
	list_ste = frappe.db.sql(""" 
		SELECT ste.name, ste.`sync_name`
		FROM `tabStock Ledger Entry` sle
		JOIN `tabStock Entry` ste ON ste.name = sle.voucher_no 
		AND ste.stock_entry_type = "Material Issue"
		AND ste.`sync_name` IS NOT NULL
		WHERE sle.voucher_type = "Stock Entry"
		AND TIMESTAMP(sle.posting_date,sle.`posting_time`) >= 

		(SELECT TIMESTAMP(pr.posting_date,pr.`posting_time`)
		FROM `tabPurchase Receipt` pr WHERE pr.name = "{}")

		AND sle.item_code = "{}"

		GROUP BY ste.name
		ORDER BY TIMESTAMP(sle.posting_date,sle.`posting_time`)
		LIMIT 9
		
	""".format(no_prec,item_code),debug=1)

	for row in list_ste:
		
		command = """ cd /home/frappe/frappe-bench/ && bench --site erp-pusat.gias.co.id execute erpnext.stock.doctype.repost_item_valuation.repost_item_valuation.debug_repost """
		os.system(command)
		recount_ste(row[0],row[1])

		frappe.enqueue(method="addons.addons.doctype.stock_recount_tools.stock_recount_tools.history_pr_complete",timeout=2400, queue='default',**{'ste': row[0]} )

@frappe.whitelist()
def compare_to_pusat(name, item_code, rate,tujuan_ste, qty, idx):

	ste_doc = frappe.get_doc("Stock Entry",name)
	rk_value = frappe.db.sql(""" SELECT SUM(debit) FROM `tabGL Entry` WHERE account = 
		"1168.04 - R/K STOCK - G" and voucher_no = "{}" """.format(name))[0][0]
	if not ste_doc.sync_name:
		ste_doc.sync_name = tujuan_ste
		ste_doc.transfer_status = "Received"
		frappe.db.commit()
		sync_name = tujuan_ste
	else:
		sync_name = ste_doc.sync_name

	list_company_gias = ste_doc.transfer_ke_cabang_mana
	site = check_list_company_gias(list_company_gias)
	if site:
		print(sync_name)
		command = """ cd /home/frappe/frappe-bench/ && bench --site {0} execute addons.addons.doctype.stock_recount_tools.stock_recount_tools.pasang_rk --kwargs "{{'sync_name':'{1}','rk_value':'{2}'}}" """.format(site,sync_name,rk_value)
		os.system(command)

	print("idx di {}".format(idx))
	list_ste = frappe.db.sql(""" 
		SELECT sle.voucher_detail_no 
		FROM `tabStock Ledger Entry` sle
		JOIN `tabStock Entry Detail` sed ON sed.name = sle.voucher_detail_no
		WHERE sle.voucher_no = "{}" and sle.item_code = "{}" 
		AND sed.idx = "{}"
		and sle.actual_qty = {} """.format(name, item_code, idx, frappe.utils.flt(qty*-1)))

	if len(list_ste) > 0:

		get_sted = frappe.get_doc("Stock Entry Detail", list_ste[0][0])

		print("idx={},rate={},list_ste={}".format(idx,rate,get_sted.basic_rate))
		if flt(rate,9) != flt(get_sted.basic_rate,9) and get_sted.idx == idx:
			print(flt(get_sted.basic_rate,9))
			if flt(get_sted.basic_rate,9) > 0:
				rate_baru = flt(get_sted.basic_rate,9)
				ste_doc = frappe.get_doc("Stock Entry",name)
				list_company_gias = ste_doc.transfer_ke_cabang_mana
				site = check_list_company_gias(list_company_gias)
				print("patching {}-{}-{}".format(tujuan_ste, rate_baru, item_code))
				if site:
					command = """ cd /home/frappe/frappe-bench/ && bench --site {0} execute addons.addons.doctype.stock_recount_tools.stock_recount_tools.patch_ste_dong --kwargs "{{'name':'{1}','item_code':'{2}','rate':'{3}','qty':'{4}'}}" """.format(site,tujuan_ste,item_code,rate_baru,qty)
					os.system(command)


@frappe.whitelist()
def patch_ste_dong(name, item_code, rate, qty):
	list_ste = frappe.db.sql(""" SELECT name, docstatus FROM `tabStock Entry` WHERE name = "{}" """.format(name))

	frappe.flags.repost_gl = True
	for rows in list_ste:
		ste_doc = frappe.get_doc("Stock Entry", rows[0])

		for row in ste_doc.items:

			if row.item_code == item_code and frappe.utils.flt(row.transfer_qty) == frappe.utils.flt(qty):
				print('yok')
				row.pusat_valuation_rate = flt(rate,9)
				row.basic_rate = flt(row.pusat_valuation_rate,9)
				row.valuation_rate = flt(flt(row.basic_rate,9) + (flt(row.additional_cost) / flt(row.transfer_qty)),9)

				print(str(row.basic_rate))
				print(str(row.valuation_rate))

				row.allow_zero_valuation_rate = 0
				row.db_update()

		# ste_doc.calculate_rate_and_amount()
		ste_doc.distribute_additional_costs()
		ste_doc.update_valuation_rate()
		ste_doc.set_total_incoming_outgoing_value()
		ste_doc.set_total_amount()

		custom_distribute_additional_costs(ste_doc)

		for row in ste_doc.items:
			row.additional_cost_transfer = row.additional_cost
			row.valuation_rate_transfer = row.valuation_rate

			if row.item_code == item_code and frappe.utils.flt(row.transfer_qty) == frappe.utils.flt(qty):
				print('yok')
				row.pusat_valuation_rate = flt(rate,9)
				row.basic_rate = flt(row.pusat_valuation_rate,9)
				row.valuation_rate = flt(flt(row.basic_rate,9) + (flt(row.additional_cost) / flt(row.transfer_qty)),9)

				print(str(row.basic_rate))
				print(str(row.valuation_rate))

				row.allow_zero_valuation_rate = 0
				row.db_update()
			
		for row in ste_doc.items:
			row.db_update()

		ste_doc.db_update()
		frappe.db.commit()

@frappe.whitelist()
def pasang_rk(sync_name, rk_value):
	if frappe.utils.flt(rk_value) > 0:
		frappe.db.sql(""" UPDATE `tabStock Entry` SET rk_value = {} WHERE name = "{}" """.format(rk_value,sync_name))
		print(rk_value)
		frappe.db.commit()

@frappe.whitelist()
def check_list_company_gias(list_company_gias):
	site = ""

	if list_company_gias == "GIAS BALI":
		site = "erp-bali.gias.co.id"
	elif list_company_gias == "GIAS BANDUNG":
		site = "erp-bdg.gias.co.id"
	elif list_company_gias == "GIAS BANJARMASIN":
		site = "erp-bjm.gias.co.id"
	elif list_company_gias == "GIAS BENGKULU":
		site = "erp-bkl.gias.co.id"
	elif list_company_gias == "GIAS BELITUNG":
		site = "erp-blt.gias.co.id"
	elif list_company_gias == "GIAS BANGKA":
		site = "erp-bnk.gias.co.id"
	elif list_company_gias == "GIAS BALIKPAPAN":
		site = "erp-bpp.gias.co.id"
	elif list_company_gias == "GIAS BERAU":
		site = "erp-bru.gias.co.id"
	elif list_company_gias == "GIAS BATAM":
		site = "erp-btm.gias.co.id"
	elif list_company_gias == "GIAS CIREBON":
		site = "erp-crb.gias.co.id"
	elif list_company_gias == "GIAS GORONTALO":
		site = "erp-gto.gias.co.id"
	elif list_company_gias == "GIAS JAMBI":
		site = "erp-jbi.gias.co.id"
	elif list_company_gias == "GIAS JEMBER":
		site = "erp-jbr.gias.co.id"
	elif list_company_gias == "GIAS JAKARTA 2":
		site = "erp-jkt2.gias.co.id"
	elif list_company_gias == "GIAS KENDARI":
		site = "erp-kdi.gias.co.id"
	elif list_company_gias == "GIAS KEDIRI":
		site = "erp-kdr.gias.co.id"
	elif list_company_gias == "KOTAMOBAGU":
		site = "erp-ktg.gias.co.id"
	elif list_company_gias == "GIAS LINGGAU":
		site = "erp-lgu.gias.co.id"
	elif list_company_gias == "GIAS LAMPUNG":
		site = "erp-lmp.gias.co.id"
	elif list_company_gias == "GIAS LOMBOK":
		site = "erp-lop.gias.co.id"
	elif list_company_gias == "GIAS MEDAN":
		site = "erp-mdn.gias.co.id"
	elif list_company_gias == "GIAS MADIUN":
		site = "erp-mdu.gias.co.id"
	elif list_company_gias == "GIAS MAKASAR":
		site = "erp-mks.gias.co.id"
	elif list_company_gias == "GIAS MANADO":
		site = "erp-mnd.gias.co.id"
	elif list_company_gias == "GIAS PALU":
		site = "erp-pal.gias.co.id"
	elif list_company_gias == "GIAS PEKANBARU":
		site = "erp-pku.gias.co.id"
	elif list_company_gias == "GIAS PALEMBANG":
		site = "erp-plg.gias.co.id"
	elif list_company_gias == "GIAS PAREPARE":
		site = "erp-pre.gias.co.id"
	elif list_company_gias == "GIAS PONTIANAK":
		site = "erp-ptk.gias.co.id"
	elif list_company_gias == "GIAS SPRINGHILL":
		site = "erp-pusat.gias.co.id"
	elif list_company_gias == "GIAS PURWOKERTO":
		site = "erp-pwt.gias.co.id"
	elif list_company_gias == "GIAS SURABAYA":
		site = "erp-sby.gias.co.id"
	elif list_company_gias == "DEPO SUKABUMI":
		site = "erp-skb.gias.co.id"
	elif list_company_gias == "GIAS SINGKAWANG":
		site = "erp-skw.gias.co.id"
	elif list_company_gias == "GIAS SAMARINDA":
		site = "erp-smd.gias.co.id"
	elif list_company_gias == "GIAS SEMARANG":
		site = "erp-smg.gias.co.id"
	elif list_company_gias == "GIAS SERANG":
		site = "erp-srg.gias.co.id"
	elif list_company_gias == "GIAS TANGERANG SELATAN":
		site = "erp-tangsel.gias.co.id"
	elif list_company_gias == "GIAS TEGAL":
		site = "erp-tgl.gias.co.id"
	elif list_company_gias == "GIAS TASIK":
		site = "erp-tsk.gias.co.id"
	elif list_company_gias == "GIAS YOGYAKARTA":
		site = "erp-ygy.gias.co.id"
	elif list_company_gias == "GIAS JAKARTA BARAT":
		site = "erp-jakbar.gias.co.id"
	elif list_company_gias == "GIAS JAKARTA TIMUR":
		site = "erp-jaktim.gias.co.id"
	elif list_company_gias == "GIAS KUPANG":
		site = "erp-kpg.gias.co.id"

	return site

@frappe.whitelist()
def debug_start_stock_recount_pr_mtr():
	start_stock_recount_pr_mtr("2023-02-25","2023-02-25","5001 - HARGA POKOK PENJUALAN - G","2123 - BARANG BELUM TERTAGIH - G")

@frappe.whitelist()
def start_stock_recount_pr_mtr(fromdate,todate, diff, total_diff):
	list_pr = frappe.db.sql(""" 
		SELECT pri.rate,pii.rate, pri.parent, pii.item_code, pin.posting_date, pri.name 
		, ap.name, cd.name, IFNULL(ptc.included_in_print_rate,1)
		FROM `tabPurchase Invoice Item` pii
		JOIN `tabPurchase Receipt Item` pri on pri.`name` = pii.`pr_detail`
		JOIN `tabPurchase Receipt` pin on pin.name = pri.parent

		LEFT JOIN `tabAccounting Period` ap
		ON ap.start_date <= pin.`posting_date`
		AND ap.`end_date` >= pin.`posting_date`
		LEFT JOIN 
		`tabClosed Document` cd
		ON ap.name = cd.parent
		AND cd.closed = 1
		AND cd.document_type IN ("Purchase Receipt")
		LEFT JOIN
		`tabPurchase Taxes and Charges` ptc ON ptc.parent = pin.name
		WHERE pri.rate != pii.`rate`
		AND pri.`docstatus` = 1
		AND pii.`docstatus` = 1

		and pin.posting_date >= "{}"
		and pin.posting_date <= "{}"
		AND pin.name NOT IN (SELECT name FROM `tabStock Recount History PR`)

		GROUP BY pri.name
		HAVING cd.name IS NULL OR cd.name IS NOT NULL
		ORDER BY posting_date,parent, item_code
		""".format(fromdate,todate))

	single_doc = frappe.get_doc("Stock Recount Tools")

	list_mtr = frappe.db.sql(""" 
		SELECT ste.name,ste.stock_entry_type, ste.posting_date
		, ap.name, cd.name
		FROM `tabStock Entry` ste

		LEFT JOIN `tabAccounting Period` ap
		ON ap.start_date <= ste.`posting_date`
		AND ap.`end_date` >= ste.`posting_date`
		LEFT JOIN 
		`tabClosed Document` cd
		ON ap.name = cd.parent
		AND cd.closed = 1
		AND cd.document_type IN ("Stock Entry")
		
		WHERE 
		ste.docstatus = 1 
		and (ste.stock_entry_type = "Material Transfer" or ste.stock_entry_type = "Adjustment In") 
		and ste.posting_date >= "{}"
		and ste.posting_date <= "{}"
		AND ste.name NOT IN (SELECT name FROM `tabStock Recount History STE`)

		GROUP BY ste.name
		HAVING cd.name IS NULL OR cd.name IS NOT NULL
		ORDER BY ste.posting_date
		""".format(fromdate,todate))

	if len(list_pr) == 0 and len(list_mtr) == 0:
		frappe.throw("No Data needed to be recount.")
	else:
		kotak_pr = []
		frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 1 WHERE `field` = "bypass" """)
		for row in list_pr:
			lakukan_recount_purchase_receipt(row[2],row[1],row[3], row[5],row[8])
			print(row[2])
			if row[2] not in kotak_pr:
				kotak_pr.append(row[2])
		
		for row in kotak_pr:
			cek_status_dan_repost_purchase_receipt(row)

		for row in list_pr:
			check_pr = frappe.db.sql(""" SELECT name FROM `tabStock Recount History PR` WHERE name = "{}" """.format(row[2]))
			if len(check_pr) == 0:
				baris_baru = frappe.new_doc("Stock Recount History PR")
				baris_baru.stock_entry = row[0]
				baris_baru.ste_type = frappe.get_doc("Stock Entry", row[0]).stock_entry_type
				baris_baru.posting_date = frappe.get_doc("Stock Entry", row[0]).posting_date
				baris_baru.last_update = frappe.utils.now()
				baris_baru.status = "Completed"
				baris_baru.save()
			else:
				baris_baru = frappe.get_doc("Stock Recount History PR",row[0])
				baris_baru.last_update = frappe.utils.now()
				baris_baru.status = "Completed"
				baris_baru.save()

		frappe.db.commit()

		for row in list_mtr:
			kotak_pr = []
			lakukan_recount_material_transfer(row[0])

			check_mtr = frappe.db.sql(""" SELECT name FROM `tabStock Recount History STE` WHERE name = "{}" """.format(row[0]))
			if len(check_mtr) == 0:
				baris_baru = frappe.new_doc("Stock Recount History STE")
				baris_baru.stock_entry = row[0]
				baris_baru.ste_type = frappe.get_doc("Stock Entry", row[0]).stock_entry_type
				baris_baru.posting_date = frappe.get_doc("Stock Entry", row[0]).posting_date
				baris_baru.last_update = frappe.utils.now()
				baris_baru.status = "Completed"
				baris_baru.save()
			else:
				baris_baru = frappe.get_doc("Stock Recount History STE",row[0])
				baris_baru.last_update = frappe.utils.now()
				baris_baru.status = "Completed"
				baris_baru.save()

		frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 0 WHERE `field` = "bypass" """)

	frappe.db.sql(""" UPDATE `tabSingles` SET `value` = "Completed" WHERE doctype = "Stock Recount Tools" AND `field` = "status" """)
	frappe.db.commit()

@frappe.whitelist()
def start_stock_recount_journal(fromdate,todate, diff, total_diff):
	single_doc = frappe.get_doc("Stock Recount Tools")

	list_pr_je = frappe.db.sql(""" 
		SELECT 
		pri.rate, poi.rate, pri.qty, pri.parent, poi.parent
		, ap.name, cd.name
		FROM `tabPurchase Invoice Item` pri
		JOIN `tabPurchase Receipt Item` poi ON poi.name = pri.`po_detail`
		JOIN `tabPurchase Invoice` prdoc ON pri.parent = prdoc.name

		LEFT JOIN `tabAccounting Period` ap
		ON ap.start_date <= pin.`posting_date`
		AND ap.`end_date` >= pin.`posting_date`
		LEFT JOIN 
		`tabClosed Document` cd
		ON ap.name = cd.parent
		AND cd.closed = 1
		AND cd.document_type IN ("Stock Entry")

		WHERE pri.rate != poi.`rate`
		AND pri.`docstatus` = 1
		AND poi.`docstatus` = 1
		AND prdoc.is_return = 0
		and prdoc.posting_date >= "{}"
		and prdoc.posting_date <= "{}"
		and prdoc.name NOT IN (SELECT purchase_receipt FROM `tabStock Recount Journal`)

		HAVING ap.name IS NOT NULL AND cd.name IS NOT NULL

		ORDER BY pri.parent
	""".format(fromdate,todate))

	if len(list_pr_je) != 0:
		create_je_hpp(fromdate, todate, diff, total_diff) 

	frappe.db.sql(""" UPDATE `tabSingles` SET `value` = "Completed" WHERE doctype = "Stock Recount Tools" AND `field` = "status" """)
	frappe.db.commit()



@frappe.whitelist()
def start_stock_recount_stei(fromdate,todate):
	frappe.flags.repost_gl == True
	list_ste = frappe.db.sql(""" 
		SELECT ste.name, ste.`sync_name`, ste.stock_entry_type,ste.posting_date
		FROM `tabStock Entry` ste 
		WHERE
		ste.posting_date >= "{}"
		AND ste.posting_date <= "{}"
		AND ste.stock_entry_type = "Material Issue"
		AND ste.`sync_name` IS NOT NULL
		and ste.docstatus = 1
		AND ste.name NOT IN (SELECT stock_entry FROM `tabStock Recount History STE`)
		
	""".format(fromdate,todate))

	for row in list_ste:
		command = """ cd /home/frappe/frappe-bench/ && bench --site erp-pusat.gias.co.id execute erpnext.stock.doctype.repost_item_valuation.repost_item_valuation.debug_repost """
		os.system(command)
		recount_ste(row[0],row[1])

		check_mtr = frappe.db.sql(""" SELECT name FROM `tabStock Recount History STE` WHERE name = "{}" """.format(row[0]))
		if len(check_mtr) == 0:
			baris_baru = frappe.new_doc("Stock Recount History STE")
			baris_baru.stock_entry = row[0]
			baris_baru.ste_type = frappe.get_doc("Stock Entry", row[0]).stock_entry_type
			baris_baru.posting_date = frappe.get_doc("Stock Entry", row[0]).posting_date
			baris_baru.last_update = frappe.utils.now()
			baris_baru.status = "Completed"
			baris_baru.save()
		else:
			baris_baru = frappe.get_doc("Stock Recount History STE",row[0])
			baris_baru.last_update = frappe.utils.now()
			baris_baru.status = "Completed"
			baris_baru.save()

	frappe.db.sql(""" UPDATE `tabSingles` SET `value` = "Completed" WHERE doctype = "Stock Recount Tools" AND `field` = "status" """)
	frappe.db.commit()

@frappe.whitelist()
def debug_stei_by_name():
	list_db = ["db_smd"]
	for row in list_db:
		debug_start_stock_recount_stei_by_name(row)

@frappe.whitelist()
def debug_start_stock_recount_stei_by_name(nama_db):
	list_ste = frappe.db.sql(""" 
		SELECT sted2.parent, ste1.stock_entry_type,ste2.posting_date
		FROM `{0}`.`tabStock Entry Detail` sted1 
		JOIN `{0}`.`tabStock Entry` ste1 ON sted1.parent = ste1.name
		JOIN `tabStock Entry` ste2 ON ste2.sync_name = ste1.name
		JOIN `tabStock Entry Detail` sted2 ON sted2.item_code = sted1.`item_code` AND sted2.qty = sted1.qty AND sted2.parent = ste2.name

		WHERE sted1.`basic_rate` != sted2.`basic_rate`
		AND sted1.`docstatus` =1 AND sted2.`docstatus` = 1

		GROUP BY sted2.parent
		HAVING ste1.`stock_entry_type` = "Material Receipt"
		ORDER BY ste2.posting_date
		
	""".format(nama_db),debug=1)

	cabang_mana = ""
	for row in list_ste:
		if cabang_mana == "":
			cabang_mana = frappe.get_doc("Stock Entry",row[0]).transfer_ke_cabang_mana
		print(row[0])
		start_stock_recount_stei_by_name(row[0])
		# frappe.db.commit()
	
	command = """ cd /home/frappe/frappe-bench/ && bench --site {} execute addons.patch_ste.repost_stock """.format(check_list_company_gias(cabang_mana))
	os.system(command)

@frappe.whitelist()
def debug_start_stock_recount_stei_by_name_2():
	list_ste = frappe.db.sql(""" 
		SELECT 
		name
		FROM `tabStock Entry` 
		WHERE name IN ("STEI-HO-1-23-09-01661")
		
	""".format(),debug=1)

	cabang_mana = ""
	for row in list_ste:
		if cabang_mana == "":
			cabang_mana = frappe.get_doc("Stock Entry",row[0]).transfer_ke_cabang_mana
		print(row[0])
		start_stock_recount_stei_by_name(row[0])
		# frappe.db.commit()
	
	command = """ cd /home/frappe/frappe-bench/ && bench --site {} execute addons.patch_ste.repost_stock """.format(check_list_company_gias(cabang_mana))
	os.system(command)

@frappe.whitelist()
def start_stock_recount_stei_by_name(name):
	try:
		frappe.flags.repost_gl == True
		list_ste = frappe.db.sql(""" 
			SELECT ste.name, ste.`sync_name`, ste.stock_entry_type,ste.posting_date
			FROM `tabStock Entry` ste 
			WHERE ste.name = "{}"
		""".format(name))

		for row in list_ste:
			command = """ cd /home/frappe/frappe-bench/ && bench --site erp-pusat.gias.co.id execute erpnext.stock.doctype.repost_item_valuation.repost_item_valuation.debug_repost """
			os.system(command)
			try:
				recount_ste(row[0],row[1])
				frappe.enqueue(method="addons.addons.doctype.stock_recount_tools.stock_recount_tools.history_pr_complete",timeout=2400, queue='default',**{'ste': row[0]} )
			except:
				frappe.enqueue(method="addons.addons.doctype.stock_recount_tools.stock_recount_tools.history_pr_failed",timeout=2400, queue='default',**{'ste': row[0]} )
			
		frappe.enqueue(method="addons.addons.doctype.stock_recount_tools.stock_recount_tools.recount_complete",timeout=2400, queue='default')
		
	except:
		frappe.enqueue(method="addons.addons.doctype.stock_recount_tools.stock_recount_tools.recount_failed",timeout=2400, queue='default')

@frappe.whitelist()
def history_pr_complete(ste):
	check_pr = frappe.db.sql(""" SELECT name FROM `tabStock Recount History STE` WHERE stock_entry = "{}" """.format(ste))
	if len(check_pr) == 0:
		baris_baru = frappe.new_doc("Stock Recount History STE")
		baris_baru.stock_entry = ste
		baris_baru.posting_date = frappe.get_doc("Stock Entry", ste).posting_date
		baris_baru.last_update = frappe.utils.now()
		baris_baru.ste_type = frappe.get_doc("Stock Entry", ste).stock_entry_type
		baris_baru.status = "Completed"
		print("1")
		baris_baru.save()
	else:
		baris_baru = frappe.get_doc("Stock Recount History STE",ste)
		baris_baru.last_update = frappe.utils.now()
		baris_baru.status = "Completed"
		print("2")
		baris_baru.save()

@frappe.whitelist()
def history_prec_complete(pr):
	check_pr = frappe.db.sql(""" SELECT name FROM `tabStock Recount History PR` WHERE purchase_receipt = "{}" """.format(pr))
	if len(check_pr) == 0:
		baris_baru = frappe.new_doc("Stock Recount History PR")
		baris_baru.purchase_receipt = pr
		baris_baru.posting_date = frappe.get_doc("Purchase Receipt", pr).posting_date
		baris_baru.last_update = frappe.utils.now()
		baris_baru.status = "Completed"
		print("1")
		baris_baru.save()
	else:
		baris_baru = frappe.get_doc("Stock Recount History PR",ste)
		baris_baru.last_update = frappe.utils.now()
		baris_baru.status = "Completed"
		print("2")
		baris_baru.save()

@frappe.whitelist()
def history_prec_failed(pr):
	check_pr = frappe.db.sql(""" SELECT name FROM `tabStock Recount History PR` WHERE purchase_receipt = "{}" """.format(pr))
	if len(check_pr) == 0:
		baris_baru = frappe.new_doc("Stock Recount History PR")
		baris_baru.stock_entry = pr
		baris_baru.posting_date = frappe.get_doc("Purchase Receipt", pr).posting_date
		baris_baru.last_update = frappe.utils.now()
		baris_baru.status = "Failed"
		print("1")
		baris_baru.save()
	else:
		baris_baru = frappe.get_doc("Stock Recount History PR",ste)
		baris_baru.last_update = frappe.utils.now()
		baris_baru.status = "Failed"
		print("2")
		baris_baru.save()

@frappe.whitelist()
def history_pr_failed(ste):
	check_pr = frappe.db.sql(""" SELECT name FROM `tabStock Recount History STE` WHERE stock_entry = "{}" """.format(ste))
	if len(check_pr) == 0:
		baris_baru = frappe.new_doc("Stock Recount History STE")
		baris_baru.stock_entry = ste
		baris_baru.posting_date = frappe.get_doc("Stock Entry", ste).posting_date
		baris_baru.last_update = frappe.utils.now()
		baris_baru.ste_type = frappe.get_doc("Stock Entry", ste).stock_entry_type
		baris_baru.status = "Failed"
		baris_baru.save()
	else:
		baris_baru = frappe.get_doc("Stock Recount History STE",ste)
		baris_baru.last_update = frappe.utils.now()
		baris_baru.status = "Failed"
		baris_baru.save()

@frappe.whitelist()
def recount_complete():
	frappe.db.sql(""" UPDATE `tabSingles` SET `value` = "Completed" WHERE doctype = "Stock Recount Tools" AND `field` = "status" """)
	frappe.db.commit()

@frappe.whitelist()
def recount_failed():
	frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 0 WHERE `field` = "bypass" """)
	frappe.db.sql(""" UPDATE `tabSingles` SET `value` = "Failed" WHERE doctype = "Stock Recount Tools" AND `field` = "status" """)
	frappe.db.commit()

@frappe.whitelist()
def lakukan_recount_material_transfer(ste_name):
	ste = frappe.get_doc("Stock Entry", ste_name)
	frappe.flags.repost_gl = True
	
	ste.calculate_rate_and_amount()
	for row in ste.items:
		row.db_update()
	ste.db_update()

	repair_gl_entry_untuk_ste("Stock Entry", ste_name)
	print(ste_name)

	frappe.db.commit()

@frappe.whitelist()
def debug_stock_recount_stei():
	list_ste = frappe.db.sql(""" 
		SELECT ste.name, ste.`sync_name`
		FROM `tabStock Entry` ste 
		WHERE
		ste.posting_date >= "2023-02-20"
		AND ste.posting_date <= "2023-02-24"
		AND ste.stock_entry_type = "Material Issue"
		AND ste.`sync_name` IS NOT NULL
		AND ste.name NOT IN (SELECT stock_entry FROM `tabStock Entry Issue History`)
		AND ste.`docstatus` = 1
	""")

	for row in list_ste:
		command = """ cd /home/frappe/frappe-bench/ && bench --site erp-pusat.gias.co.id execute erpnext.stock.doctype.repost_item_valuation.repost_item_valuation.debug_repost """
		os.system(command)
		recount_ste(row[0],row[1])


@frappe.whitelist()
def recount_ste(no_ste,ste_sync):
	frappe.flags.repost_gl == True
	ste_doc = frappe.get_doc("Stock Entry",no_ste)
	site = check_list_company_gias(ste_doc.transfer_ke_cabang_mana)

	print(""" cd /home/frappe/frappe-bench/ && bench --site {} execute addons.addons.doctype.stock_recount_tools.stock_recount_tools.patch_ste --args "{{'{}'}}" """.format(site,no_ste))
	command = """ cd /home/frappe/frappe-bench/ && bench --site {} execute addons.addons.doctype.stock_recount_tools.stock_recount_tools.patch_ste --args "{{'{}'}}" """.format(site,no_ste)
	os.system(command)

@frappe.whitelist()
def patch_ste(no_ste):
	frappe.flags.repost_gl == True
	
	list_ste = frappe.db.sql(""" SELECT name,docstatus FROM `tabStock Entry` 
	WHERE stock_entry_type = "Material Receipt"
	AND sync_name IS NOT NULL  
	AND docstatus < 2
	AND (sync_name = "{}")
	""".format(no_ste))
	
	for row in list_ste:
		
		ste_doc = frappe.get_doc("Stock Entry", row[0])
		nama_sync = ste_doc.sync_name
		if ste_doc.get("dari_list_company"):
			list_company_gias = ste_doc.get("dari_list_company")
		else:
			list_company_gias = "GIAS SPRINGHILL"
		for row_item in ste_doc.items:
			site = check_list_company_gias(list_company_gias)
			row_qty = row_item.transfer_qty
			if site :
				print("inidia {}".format(nama_sync))
				command = """ cd /home/frappe/frappe-bench/ && bench --site {0} execute addons.addons.doctype.stock_recount_tools.stock_recount_tools.compare_to_pusat --kwargs "{{'idx':'{6}','name':'{1}','item_code':'{2}','rate':'{3}','tujuan_ste':'{4}', 'qty':{5} }}" """.format(site,nama_sync,row_item.item_code,row_item.basic_rate, ste_doc.name, row_qty, row_item.idx)
				os.system(command)

		if row[1] == 1:
			frappe.db.commit()
			repair_gl_entry_untuk_ste("Stock Entry", row[0])



# searches for active employees
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def ste_query(doctype, txt, searchfield, start, page_len, filters):
	conditions = []
	fields = get_fields("Stock Entry", ["name", "stock_entry_type", "sync_name"])

	return frappe.db.sql("""select {fields} from `tabStock Entry`
		where docstatus = 1
			and ({key} like %(txt)s
				or name like %(txt)s)

			AND stock_entry_type = "Material Issue"
			AND transfer_ke_cabang_pusat = 1
			{fcond} {mcond}
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			idx desc,
			name
		limit %(start)s, %(page_len)s""".format(**{
			'fields': ", ".join(fields),
			'key': searchfield,
			'fcond': get_filters_cond(doctype, filters, conditions),
			'mcond': get_match_cond(doctype)
		}), {
			'txt': "%%%s%%" % txt,
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len
		})

def get_fields(doctype, fields=None):
	if fields is None:
		fields = []
	meta = frappe.get_meta(doctype)
	fields.extend(meta.get_search_fields())

	if meta.title_field and not meta.title_field.strip() in fields:
		fields.insert(1, meta.title_field.strip())

	return unique(fields)