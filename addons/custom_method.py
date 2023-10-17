import frappe, erpnext
import json
from frappe.utils import flt
import frappe.utils
from num2words import num2words
from frappe.model.naming import make_autoname, revert_series_if_last

import requests
from frappe.frappeclient import FrappeClient
from frappe.utils.background_jobs import get_redis_conn
from typing import TYPE_CHECKING, Dict, List
from rq import Queue, Worker
if TYPE_CHECKING:
	from rq.job import Job

import base64
from base64 import decodebytes
import getpass
import os
import socket
import sys
import traceback

import time

from os import listdir
from os.path import isfile, join
from datetime import datetime,timedelta

from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
	check_if_return_invoice_linked_with_payment_entry,
	get_total_in_party_account_currency,
	is_overdue,
	unlink_inter_company_doc,
	update_linked_doc,
	validate_inter_company_party,
)
JOB_COLORS = {
	'queued': 'orange',
	'failed': 'red',
	'started': 'blue',
	'finished': 'green'
}

from addons.custom_standard.custom_stock_entry import repair_gl_entry_untuk_ste
@frappe.whitelist()
def debug_repair_ste():
	repair_gl_entry_untuk_ste("Stock Entry","STE-BPN-22-08-00002")

@frappe.whitelist()
def isi_item_parent_item_group():
	list_item = frappe.db.sql(""" SELECT name FROM `tabItem` WHERE parent_item_group IS NULL """)
	for row in list_item:
		item_doc = frappe.get_doc("Item", row[0])
		item_doc.parent_item_group = frappe.get_doc("Item Group", item_doc.item_group).parent_item_group
		item_doc.db_update()
		frappe.db.commit()
		print(row[0])


@frappe.whitelist()
def isi_sync_old_name():
	frappe.db.sql(""" UPDATE `tabStock Entry` SET sync_name_old = sync_name WHERE sync_name IS NOT NULL """)


@frappe.whitelist()
def ganti_sync_old_name():
	list_ste = frappe.db.sql(""" SELECT name FROM `tabStock Entry` WHERE sync_name LIKE "%-1-22-%" AND tax_or_non_tax = "Tax" """)
	for row in list_ste:
		ste = frappe.get_doc("Stock Entry", row[0])
		new_name = frappe.db.sql(""" SELECT name FROM `db_srg`.`tabStock Entry` WHERE old_name = "{}" """.format(ste.sync_name))
		if len(new_name) > 0:
			if new_name[0][0]:
				print("{}-{}".format(ste.sync_name,new_name[0][0]))
				ste.sync_name = str(new_name[0][0])
				ste.db_update()
				frappe.db.commit()

@frappe.whitelist()
def rename_ste():
	frappe.rename_doc("Journal Entry","BEO-GIAS-HO-1-22-06-00523","BEO-GIAS-HO-1-20-06-00001")
	frappe.rename_doc("Journal Entry","JE-GIAS-PWT-1-22-06-00017","JE-GIAS-PWT-1-21-03-00001")
	frappe.rename_doc("Journal Entry","JEDP-GIAS-SMG-1-22-12-00035","JEDP-GIAS-SMG-1-23-01-00012")

@frappe.whitelist()
def rename_lsg():
	frappe.rename_doc("User","202030023@gias.co.id","robertus.adityas@gias.co.id")
	
	

@frappe.whitelist()
def check_series_terakhir():
	list_series = frappe.db.sql(""" SELECT name,current FROM `tabSeries` WHERE 
		(
		name LIKE "JE-GIAS%" 
		)
		AND name NOT LIKE "%-1-%" AND name NOT LIKE "%-2-%"
	;""")
	for row in list_series:
		series = row[0]

		angka_terakhir = frappe.db.sql(""" SELECT CAST(RIGHT(generated_name,5) AS DECIMAL) AS angka FROM `tabJournal Entry` 
			WHERE generated_name LIKE "{}%"
			ORDER BY generated_name DESC
			LIMIT 1 ;""".format(series))
		if angka_terakhir:
			if angka_terakhir[0]:
				if angka_terakhir[0][0]:
					if frappe.utils.flt(row[1]) != frappe.utils.flt(angka_terakhir[0][0]):
						print("{}-{}-{}".format(series,frappe.utils.flt(row[1]),frappe.utils.flt(angka_terakhir[0][0])))
						frappe.db.sql(""" UPDATE `tabSeries` SET current = {} WHERE name = "{}" """.format(frappe.utils.flt(angka_terakhir[0][0]),series))


@frappe.whitelist()
def cari_old_name():
	if frappe.get_doc("Company","GIAS").server == "Cabang":
		list_ste = frappe.db.sql(""" SELECT name, old_name FROM `tabStock Entry`
			WHERE sync_name IS NOT NULL
			AND NAME = generated_name
		""")

		for row in list_ste:
			command = """ cd /home/frappe/frappe-bench/ && bench --site erp-pusat.gias.co.id execute addons.custom_method.buat_old_name --kwargs "{{'dt':'Stock Entry','on':'{}','nn':'{}'}}" """.format(str(row[1]),str(row[0]))
			os.system(command)
			print("{}-{}".format(row[0],row[1]))



@frappe.whitelist()
def buat_old_name(dt,on,nn):
	frappe.db.sql(""" SELECT * FROM `tabHistory Old Name`  """)
	hon = frappe.new_doc("History Old Name")
	hon.document_type = dt
	hon.old_name = on
	hon.new_name = nn
	hon.save()

@frappe.whitelist()
def freeze_doc(self,method):
	if "2022" in str(self.posting_date):
		frappe.throw("For Naming Reason, 2022 transactions are frozen for creating.")



@frappe.whitelist()
def cancel_prepared_report():
	frappe.db.sql("""update `tabPrepared Report` set status = "Error" where status="Queued" """)

@frappe.whitelist()
def patch_branch():
	comp_doc = frappe.get_doc("Company","GIAS")
	cabang = comp_doc.nama_cabang
	list_doc = frappe.get_doc("List Company GIAS", cabang)
	branch = list_doc.accounting_dimension
	if comp_doc.server == "Cabang":
		frappe.db.sql(""" 
			UPDATE `tabSales Taxes and Charges`
			SET branch = "{}"
			WHERE NAME IN(
			SELECT stc.name
			FROM `tabSales Taxes and Charges` stc
			JOIN `tabSales Invoice` sinv ON sinv.name = stc.parent
			WHERE sinv.branch != stc.branch) """.format(branch))

	print(cabang)


@frappe.whitelist()
def patch_prorate_discount():
	list_si = frappe.db.sql(""" SELECT sii.parent,sii.prorate_discount,sii.percent_value, si.`discount_2` FROM `tabSales Invoice Item` sii 
		JOIN `tabSales Invoice` si ON si.name = sii.parent
		WHERE sii.price_list_rate = 0 AND sii.rate != 0
		GROUP BY sii.parent
		HAVING discount_2 > 0 """)
	for row in list_si:
		variable = 100
		doc = frappe.get_doc("Sales Invoice",row[0])
		for row_tax in doc.taxes:
			if row_tax.included_in_print_rate == 1:
				variable = variable + row_tax.rate
		total_price_list = 0
		for row_item in doc.items:
			total_price_list += row_item.rate * row_item.qty

		
		if total_price_list > 0:
			for row_item in doc.items:
				row_item.percent_value = row_item.rate / total_price_list * 100
				row_item.prorate_discount = row_item.percent_value / 100 * (doc.discount_2 / (variable/100))
				row_item.total_prorate = row_item.prorate_discount * row_item.qty
				row_item.db_update()

		print(row[0])

@frappe.whitelist()
def patch_total_prorate():
	frappe.db.sql(""" UPDATE `tabSales Invoice Item` SET total_prorate = prorate_discount * qty WHERE prorate_discount IS NOT NULL """)
	frappe.db.sql(""" UPDATE `tabPurchase Invoice Item` SET total_prorate = prorate_discount * qty WHERE prorate_discount IS NOT NULL """)

@frappe.whitelist()
def patch_cabang_so():
	comp_doc = frappe.get_doc("Company","GIAS")
	cabang = comp_doc.nama_cabang
	list_doc = frappe.get_doc("List Company GIAS", cabang)
	branch = list_doc.accounting_dimension
	if cabang != "GIAS BALI" and comp_doc.server == "Cabang":
		frappe.db.sql(""" UPDATE `tabPayment Entry` SET branch = "{}" WHERE branch = "BALI" """.format(branch))
		frappe.db.sql(""" UPDATE `tabPayment Entry Deduction` SET branch = "{}" WHERE branch = "BALI" """.format(branch))

		frappe.db.sql(""" UPDATE `tabCustom Field` SET `default` = "{}" WHERE name LIKE "%Sales Taxes and Charges-branch%" and `default` = "BALI" """.format(branch))
		print("{}-{}".format(cabang,branch))


@frappe.whitelist()
def pasang_rk(sync_name, rk_value):
	frappe.db.sql(""" UPDATE `tabStock Entry` SET rk_value = {} WHERE name = "{}" """.format(rk_value,sync_name))
	print(rk_value)
	frappe.db.commit()

@frappe.whitelist()
def cari():
	list_ste = frappe.db.sql(""" select name FROM `tabStock Entry` WHERE name IN ("STE-HO-1-22-03-00010",
	""")
	
	for row in list_ste:
		ste_doc = frappe.get_doc("Stock Entry",row[0])
		rk_value = frappe.db.sql(""" SELECT debit FROM `tabGL Entry` WHERE account = "1168.04 - R/K STOCK - G" and voucher_no = "{}" """.format(row[0]))[0][0]
		sync_name = ste_doc.sync_name

		list_company_gias = ste_doc.transfer_ke_cabang_mana
		site = check_list_company_gias(list_company_gias)
		if site:
			print(sync_name)
			command = """ cd /home/frappe/frappe-bench/ && bench --site {0} execute addons.custom_method.pasang_rk --kwargs "{{'sync_name':'{1}','rk_value':'{2}'}}" """.format(site,sync_name,rk_value)
			os.system(command)

@frappe.whitelist()
def system_manager_try():
	list_user = frappe.db.sql(""" SELECT name FROM `tabUser` WHERE name LIKE "%branch%" """)
	for row in list_user:
		doc = frappe.get_doc("User",row[0])
		doc.append("roles",{"role":"System Manager"})

		doc.save()
		print(row[0])

@frappe.whitelist()
def list_buat_pal():
	docs = frappe.db.sql(""" SELECT 
				`update_type`, 
				`ref_doctype`,
				`docname`, `data`, `name`, `creation` 
				FROM `tabEvent Update Log`  
				WHERE ref_doctype IN
				('Account', 'Item Group', 'Brand', 'UOM', 'Item Classification', 
				'Sub Classification', 'Item Color', 'PS Approver MR', 'Department', 
				'Branch', 'Supplier', 'Supplier Group', 'Country', 'Bank Account', 
				'Bank Account Subtype', 'Bank Account Type', 'Tax Category', 
				'Tax Withholding Category', 'Currency', 'Price List', 'Item Price', 
				'Payment Terms Template', 'Item', 'Expense Claim Type',
				'Mode of Payment')
				AND creation >= "2022-09-05 12:54:46.671339"
				ORDER BY creation ASC
				LIMIT 1
		""", as_dict=1)

	frappe.throw(str(docs))

@frappe.whitelist()
def tanggal_move():
	tanggal = frappe.utils.getdate("2022-03-01")
	tanggal = frappe.utils.add_days(tanggal,1)
	print(tanggal)


@frappe.whitelist()
def list_patch_ste_status():

	list_ste = frappe.db.sql(""" SELECT name,docstatus FROM `tabStock Entry` 
	WHERE stock_entry_type = "Material Issue"
	AND transfer_ke_cabang_pusat = 1
	AND docstatus = 1
	and transfer_status = "On The Way"
	""")

	for row in list_ste:

		ste_doc = frappe.get_doc("Stock Entry", row[0])
		list_company_gias = ste_doc.transfer_ke_cabang_mana
		
		site = check_list_company_gias(list_company_gias)
		print(row[0])
		if site:
			command = """ cd /home/frappe/frappe-bench/ && bench --site {0} execute addons.custom_method.coba_cek_ada_ste --kwargs "{{'name':'{1}'}}" """.format(site, ste_doc.name)
			os.system(command)


		if row[1] == 1:
			frappe.db.commit()
			repair_gl_entry_untuk_ste("Stock Entry", row[0])

@frappe.whitelist()
def list_patch_ste():

	list_ste = frappe.db.sql(""" SELECT name,docstatus FROM `tabStock Entry` 
	WHERE stock_entry_type = "Material Receipt"
	AND sync_name IS NOT NULL  
	AND docstatus < 2
	AND (name = "STER-BKL-1-22-06-00008")
	""")

	for row in list_ste:

		ste_doc = frappe.get_doc("Stock Entry", row[0])
		nama_sync = ste_doc.sync_name
		list_company_gias = ste_doc.dari_list_company
		for row_item in ste_doc.items:
			site = check_list_company_gias(list_company_gias)
			row_qty = row_item.qty
			if site:
				print(nama_sync)
				command = """ cd /home/frappe/frappe-bench/ && bench --site {0} execute addons.custom_method.coba_cek_ste_dong --kwargs "{{'name':'{1}','item_code':'{2}','rate':'{3}','tujuan_ste':'{4}', 'qty':{5} }}" """.format(site,nama_sync,row_item.item_code,row_item.basic_rate, ste_doc.name, row_qty)
				os.system(command)

		if row[1] == 1:
			frappe.db.commit()
			repair_gl_entry_untuk_ste("Stock Entry", row[0])


@frappe.whitelist()
def coba_cek_ste_dong(name, item_code, rate,tujuan_ste, qty):

	ste_doc = frappe.get_doc("Stock Entry",name)
	rk_value = frappe.db.sql(""" SELECT debit FROM `tabGL Entry` WHERE account = "1168.04 - R/K STOCK - G" and voucher_no = "{}" """.format(name))[0][0]
	sync_name = ste_doc.sync_name

	list_company_gias = ste_doc.transfer_ke_cabang_mana
	site = check_list_company_gias(list_company_gias)
	if site:
		print(sync_name)
		command = """ cd /home/frappe/frappe-bench/ && bench --site {0} execute addons.custom_method.pasang_rk --kwargs "{{'sync_name':'{1}','rk_value':'{2}'}}" """.format(site,sync_name,rk_value)
		os.system(command)

	
	list_ste = frappe.db.sql(""" 
		SELECT valuation_rate FROM `tabStock Ledger Entry` 
		WHERE voucher_no = "{}" and item_code = "{}" 
		and actual_qty = {} """.format(name, item_code, frappe.utils.flt(qty*-1)))
	print("{}-{}".format(item_code,list_ste[0][0]))

	if flt(rate,2) != flt(list_ste[0][0],2):
		print(flt(list_ste[0][0],2))
		if flt(list_ste[0][0]) > 0:
			rate_baru = flt(list_ste[0][0],2)
			ste_doc = frappe.get_doc("Stock Entry",name)
			list_company_gias = ste_doc.transfer_ke_cabang_mana
			site = check_list_company_gias(list_company_gias)
			print("patching {}-{}-{}".format(tujuan_ste, rate_baru, item_code))
			if site:
				command = """ cd /home/frappe/frappe-bench/ && bench --site {0} execute addons.custom_method.patch_ste_dong --kwargs "{{'name':'{1}','item_code':'{2}','rate':'{3}'}}" """.format(site,tujuan_ste,item_code,rate_baru)
				os.system(command)

@frappe.whitelist()
def patch_ste_dong(name, item_code, rate):
	list_ste = frappe.db.sql(""" SELECT name, docstatus FROM `tabStock Entry` WHERE name = "{}" """.format(name))

	frappe.flags.repost_gl = True
	for rows in list_ste:
		ste_doc = frappe.get_doc("Stock Entry", rows[0])
		for row in ste_doc.items:
			if row.item_code == item_code:
				row.pusat_valuation_rate = flt(rate,2)
				row.basic_rate = flt(row.pusat_valuation_rate)
				row.valuation_rate = flt(flt(row.basic_rate) + (flt(row.additional_cost) / flt(row.transfer_qty)))

				row.allow_zero_valuation_rate = 0
				row.db_update()
		ste_doc.calculate_rate_and_amount()
		for row in ste_doc.items:
			row.db_update()

		print(ste_doc.name)
		ste_doc.db_update()

	# frappe.db.commit()
	# print(rate)

@frappe.whitelist()
def coba_cek_ada_ste(name):
	
	list_ste = frappe.db.sql(""" SELECT name FROM `tabStock Entry` WHERE sync_name = "{}" and docstatus = 1  """.format(name))
	if list_ste:
		if list_ste[0]:
			if list_ste[0][0]:
			
				ste_doc = frappe.get_doc("Stock Entry",list_ste[0][0])
				list_company_gias = ste_doc.dari_list_company
				site = check_list_company_gias(list_company_gias)
				print("patching {}".format(ste_doc.sync_name))
				if site:
					command = """ cd /home/frappe/frappe-bench/ && bench --site {0} execute addons.custom_method.patch_ste_status --kwargs "{{'name':'{1}','sync_name':'{2}'}}" """.format(site,name,ste_doc.name)
					os.system(command)




@frappe.whitelist()
def patch_ste_status(name, sync_name):
	ste_doc = frappe.get_doc("Stock Entry", name)
	if ste_doc.transfer_status == "On The Way":
		ste_doc.transfer_status = "Received"
		ste_doc.sync_name = sync_name
		ste_doc.db_update()





@frappe.whitelist()
def patch_cost_ste():
	list_ste = frappe.db.sql(""" SELECT name FROM `tabStock Entry` WHERE
	name = "STER-MDO-1-22-08-00048" """)

	frappe.flags.repost_gl = True
	for rows in list_ste:
		ste_doc = frappe.get_doc("Stock Entry", rows[0])
		for row in ste_doc.items:
			row.basic_rate = flt(row.pusat_valuation_rate,2)
			row.valuation_rate = flt(flt(row.basic_rate) + (flt(row.additional_cost) / flt(row.transfer_qty)))
			row.db_update()

		ste_doc.calculate_rate_and_amount()
		ste_doc.db_update()

		repair_gl_entry("Stock Entry", rows[0])
		print(rows[0])

	frappe.db.commit()



@frappe.whitelist()
def check_asset():
	list_asset = frappe.db.sql(""" 
		SELECT NAME, detil_je_log, IFNULL(list_company_gias,"GIAS SPRINGHILL"),parent
		 FROM `tabDepreciation Schedule`

		 WHERE docstatus != 2
		 AND detil_je_log IS NOT NULL
		 and list_company_gias = "GIAS SERANG"
		 GROUP BY parent """)

	for row in list_asset:
		asset_doc = frappe.get_doc("Asset", row[3])
		for row_schedule in asset_doc.schedules:
			if row_schedule.detil_je_log:
				list_company_gias = row_schedule.list_company_gias
				site = ""
				print(list_company_gias)
				if list_company_gias == "GIAS SERANG":
					site = "erp-srg.gias.co.id"

				if list_company_gias == "GIAS SPRINGHILL":
					site = "erp-pusat.gias.co.id"

				if list_company_gias == "GIAS BALI":
					site = "erp-bali.gias.co.id"

				if list_company_gias == "GIAS BALIKPAPAN":
					site = "erp-bpp.gias.co.id"

				if list_company_gias == "GIAS BANDUNG":
					site = "erp-bdg.gias.co.id"

				if list_company_gias == "GIAS BANGKA":
					site = "erp-bnk.gias.co.id"
				if list_company_gias == "GIAS BANJARMASIN":
					site = "erp-bjm.gias.co.id"
				if list_company_gias == "GIAS BENGKULU":
					site = "erp-bkl.gias.co.id"
				if list_company_gias == "GIAS BERAU":
					site = "erp-bru.gias.co.id"
				if list_company_gias == "GIAS CIREBON":
					site = "erp-crb.gias.co.id"
				if list_company_gias == "GIAS GORONTALO":
					site = "erp-gto.gias.co.id"
				if list_company_gias == "GIAS JAMBI":
					site = "erp-jbi.gias.co.id"
				if list_company_gias == "GIAS JEMBER":
					site = "erp-jbr.gias.co.id"
				if list_company_gias == "GIAS KENDARI":
					site = "erp-kdi.gias.co.id"
				if list_company_gias == "GIAS LAMPUNG":
					site = "erp-lmp.gias.co.id"
				if list_company_gias == "GIAS LINGGAU":
					site = "erp-lgu.gias.co.id"
				if list_company_gias == "GIAS MADIUN":
					site = "erp-mdu.gias.co.id"
				if list_company_gias == "GIAS MAKASAR":
					site = "erp-mks.gias.co.id"
				if list_company_gias == "GIAS MANADO":
					site = "erp-mnd.gias.co.id"
				if list_company_gias == "GIAS MEDAN":
					site = "erp-mdn.gias.co.id"
				if list_company_gias == "GIAS PALEMBANG":
					site = "erp-plg.gias.co.id"
				if list_company_gias == "GIAS PEKANBARU":
					site = "erp-pku.gias.co.id"
				if list_company_gias == "GIAS PONTIANAK":
					site = "erp-ptk.gias.co.id"
				if list_company_gias == "GIAS PURWOKERTO":
					site = "erp-pwt.gias.co.id"
				if list_company_gias == "GIAS SAMARINDA":
					site = "erp-smd.gias.co.id"
				if list_company_gias == "GIAS SEMARANG":
					site = "erp-smg.gias.co.id"
				if list_company_gias == "GIAS SERANG":
					site = "erp-srg.gias.co.id"
				if list_company_gias == "GIAS SURABAYA":
					site = "erp-sby.gias.co.id"
				if list_company_gias == "GIAS TASIK":
					site = "erp-tsk.gias.co.id"
				if list_company_gias == "GIAS TEGAL":
					site = "erp-tgl.gias.co.id"
				if list_company_gias == "GIAS YOGYAKARYA":
					site = "erp-ygy.gias.co.id"


				if site:
					command = """ cd /home/frappe/frappe-bench/ && bench --site {0} execute addons.custom_method.cari_je --args "{{'{1}'}}" """.format(site,row_schedule.detil_je_log)
					os.system(command)


@frappe.whitelist()
def cari_je(je_log):
	cari = frappe.db.sql(""" SELECT name FROM `tabJournal Entry` WHERE je_log = "{}" and docstatus = 1 """.format(je_log))
	if len(cari) == 0:
		frappe.throw(je_log)
	else:
		print(cari[0][0])


@frappe.whitelist()
def patch_asset():
	list_asset = frappe.db.sql(""" SELECT name FROM `tabAsset` WHERE docstatus != 2 """)
	for row in list_asset:
		asset_doc = frappe.get_doc("Asset", row[0])
		total_depreciation = 0
		times = 0
		for row_schedule in asset_doc.schedules:
			# if row_schedule.detil_je_log:
			# 	total_depreciation += row_schedule.depreciation_amount
			# 	times += 1
			if asset_doc.server_kepemilikan == "Pusat":
				row_schedule.list_company_gias = frappe.get_doc("Company", asset_doc.company).nama_cabang
			else:
				row_schedule.list_company_gias = asset_doc.cabang
			row_schedule.db_update()

		# asset_doc.depreciation_amount = total_depreciation + asset_doc.opening_accumulated_depreciation
		# asset_doc.accumulated_depreciation_times = times + asset_doc.number_of_depreciations_booked
		# asset_doc.db_update()

		frappe.db.commit()

@frappe.whitelist()
def isi_html_attachment():
	list_html = frappe.db.sql(""" 
		SELECT parent, attachment, name
		FROM `tabAttachment Table`
		WHERE `parenttype` = "Material Request"
		AND parent NOT LIKE "%HO%"
		AND attachment NOT LIKE "%https%"

	""")
	for row in list_html:
		mr_doc = frappe.get_doc("Material Request", row[0])
		for att_table in mr_doc.attachment:
			if "https" not in att_table.attachment:
				cabang = mr_doc.cabang
				awalan = "https://"+check_list_company_gias(cabang)
				att_table.attachment = str(awalan) + att_table.attachment
				att_table.db_update()


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
	else:
		frappe.throw("TIDAK ADA {}".format(list_company_gias))

	return site

@frappe.whitelist()
def patch_pajak():
	list_invoice = frappe.db.sql(""" SELECT NAME, customer, tax_name, alamat_pajak FROM `tabSales Invoice` WHERE
	tax_or_non_tax = "Tax"
	AND (tax_name IS NULL OR alamat_pajak IS NULL)
	 """)
	for row in list_invoice:
		si_doc = frappe.get_doc("Sales Invoice", row[0])
		cust_doc = frappe.get_doc("Customer", row[1])
		if not si_doc.tax_name:
			si_doc.tax_name = cust_doc.nama_pajak
		if not si_doc.alamat_pajak:
			si_doc.alamat_pajak = cust_doc.alamat_pajak

		si_doc.db_update()
		print(si_doc.name)

	frappe.db.commit()


@frappe.whitelist()
def patch_discount():
	list_patch = frappe.db.sql(""" 
		SELECT NAME 
		FROM `tabSales Invoice` 
		WHERE apply_discount_on = "Net Total" and name = "SI-GIAS-HO-1-22-06-00071"
 	""")
	for row in list_patch:
		cek = 1
		soi = frappe.get_doc("Sales Invoice", row[0])
		soi.apply_discount_on = "Grand Total"
		if soi.docstatus < 2:
			if soi.docstatus == 1 :
				soi.set_posting_time = 1
				frappe.db.sql(""" UPDATE `tabSales Invoice` SET docstatus = 0 WHERE name = "{}" """.format(row[0]))
				frappe.db.sql(""" UPDATE `tabSales Invoice Item` SET docstatus = 0 WHERE parent = "{}" """.format(row[0]))
				frappe.db.sql(""" UPDATE `tabSales Taxes and Charges` SET docstatus = 0 WHERE parent = "{}" """.format(row[0]))
				cek = 0
			soi.calculate_taxes_and_totals()
			soi.save()
			if soi.docstatus == 1:
				if soi.update_stock == 1:
					repair_gl_entry("Sales Invoice", row[0])
				else:
					repair_gl_entry_tanpa_sl("Sales Invoice", row[0])

			if cek == 0:
				frappe.db.sql(""" UPDATE `tabSales Invoice` SET docstatus = 1 WHERE name = "{}" """.format(row[0]))
				frappe.db.sql(""" UPDATE `tabSales Invoice Item` SET docstatus = 1 WHERE parent = "{}" """.format(row[0]))
				frappe.db.sql(""" UPDATE `tabSales Taxes and Charges` SET docstatus = 1 WHERE parent = "{}" """.format(row[0]))
				cek = 1
		soi.outstanding_amount = soi.rounded_total
		soi.db_update()
		print(soi.name)

def get_outstanding_amount(against_voucher_type, against_voucher, account, party, party_type):
	bal = frappe.utils.flt(frappe.db.sql("""
		select sum(debit_in_account_currency) - sum(credit_in_account_currency)
		from `tabGL Entry`
		where against_voucher_type=%s and against_voucher=%s
		and account = %s and party = %s and party_type = %s""",
		(against_voucher_type, against_voucher, account, party, party_type))[0][0] or 0.0)

	if against_voucher_type == 'Purchase Invoice':
		bal = bal * -1

	return bal

@frappe.whitelist()
def patch_discount_buying():
	list_patch = frappe.db.sql(""" 
		SELECT NAME 
		FROM `tabPurchase Invoice` 
		WHERE name = "PI-1-22-03-00076"
		LIMIT 1
 	""")
	for row in list_patch:

		
		cek = 1
		soi = frappe.get_doc("Purchase Invoice", row[0])
		print(soi.name)
		soi.apply_discount_on = "Net Total"
		if soi.docstatus < 2:
			if soi.docstatus == 1 :
				soi.set_posting_time = 1
				frappe.db.sql(""" UPDATE `tabPurchase Invoice` SET docstatus = 0 WHERE name = "{}" """.format(row[0]))
				frappe.db.sql(""" UPDATE `tabPurchase Invoice Item` SET docstatus = 0 WHERE parent = "{}" """.format(row[0]))
				frappe.db.sql(""" UPDATE `tabPurchase Taxes and Charges` SET docstatus = 0 WHERE parent = "{}" """.format(row[0]))
				cek = 0
			soi.calculate_taxes_and_totals()
			soi.save()
			if soi.docstatus == 1:
				if soi.update_stock == 1:
					repair_gl_entry("Purchase Invoice", row[0])
				else:
					repair_gl_entry_tanpa_sl("Purchase Invoice", row[0])

			if cek == 0:
				frappe.db.sql(""" UPDATE `tabPurchase Invoice` SET docstatus = 1 WHERE name = "{}" """.format(row[0]))
				frappe.db.sql(""" UPDATE `tabPurchase Invoice Item` SET docstatus = 1 WHERE parent = "{}" """.format(row[0]))
				frappe.db.sql(""" UPDATE `tabPurchase Taxes and Charges` SET docstatus = 1 WHERE parent = "{}" """.format(row[0]))
				cek = 1
		soi.outstanding_amount = get_outstanding_amount(soi.doctype, soi.name, soi.credit_to, soi.supplier, "Supplier")
		outstanding_amount = soi.outstanding_amount 
		status = None
		total = get_total_in_party_account_currency(soi)
		if not status:
			if soi.docstatus == 2:
				status = "Cancelled"
			elif soi.docstatus == 1:
				if soi.is_internal_transfer():
					soi.status = 'Internal Transfer'
				elif is_overdue(soi, total):
					soi.status = "Overdue"
				elif 0 < outstanding_amount < total:
					soi.status = "Partly Paid"
				elif outstanding_amount > 0 and getdate(soi.due_date) >= getdate():
					soi.status = "Unpaid"
				#Check if outstanding amount is 0 due to debit note issued against invoice
				elif outstanding_amount <= 0 and soi.is_return == 0 and frappe.db.get_value('Purchase Invoice', {'is_return': 1, 'return_against': soi.name, 'docstatus': 1}):
					soi.status = "Debit Note Issued"
				elif soi.is_return == 1:
					soi.status = "Return"
				elif outstanding_amount<=0:
					soi.status = "Paid"
				else:
					soi.status = "Submitted"
			else:
				soi.status = "Draft"
		soi.db_update()
		# soi.set_status() - perlu yang lebih
		print("DONE")

@frappe.whitelist()
def patch_so():
	company_doc = frappe.get_doc("Company", "GIAS")
	if company_doc.nama_cabang != "GIAS BANGKA":
		list_patch = frappe.db.sql(""" 
			SELECT NAME FROM `tabSales Order` WHERE sales_person IS NOT NULL
	 	""")
		for row in list_patch:
			soi = frappe.get_doc("Sales Order", row[0])
			if not soi.sales_team:
				soi.append("sales_team",{
					"sales_person" : soi.sales_person,
					"allocated_percentage" : 100,
					"allocated_amount": soi.net_total,
					"incentives": 0
				})
				for baris in soi.sales_team:
					baris.db_update()

			print(soi.name)

		list_patch = frappe.db.sql(""" 
			SELECT NAME FROM `tabDelivery Note` WHERE sales_person IS NOT NULL
	 	""")
		for row in list_patch:
			soi = frappe.get_doc("Delivery Note", row[0])
			if not soi.sales_team:
				soi.append("sales_team",{
					"sales_person" : soi.sales_person,
					"allocated_percentage" : 100,
					"allocated_amount": soi.net_total,
					"incentives": 0
				})
				for baris in soi.sales_team:
					baris.db_update()

			print(soi.name)

		list_patch = frappe.db.sql(""" 
			SELECT NAME FROM `tabSales Invoice` WHERE sales_person IS NOT NULL
	 	""")
		for row in list_patch:
			soi = frappe.get_doc("Sales Invoice", row[0])
			if not soi.sales_team:
				soi.append("sales_team",{
					"sales_person" : soi.sales_person,
					"allocated_percentage" : 100,
					"allocated_amount": soi.net_total,
					"incentives": 0
				})
				for baris in soi.sales_team:
					baris.db_update()

			print(soi.name)

		list_patch = frappe.db.sql(""" 
			SELECT name,parenttype, parent FROM `tabSales Team`
	 	""")
		for row in list_patch:
			st = frappe.get_doc("Sales Team", row[0])
			doc = frappe.get_doc(row[1],row[2])
			st.docstatus = doc.docstatus
			st.db_update()
			print(row[2])
			frappe.db.commit()

@frappe.whitelist()
def patch_sales_team():
	list_patch = frappe.db.sql(""" 
		SELECT name,parenttype, parent FROM `tabSales Team`
 	""")
	for row in list_patch:
		st = frappe.get_doc("Sales Team", row[0])
		doc = frappe.get_doc(row[1],row[2])
		st.docstatus = doc.docstatus
		st.db_update()
		print(row[2])
		frappe.db.commit()


@frappe.whitelist()
def get_url():
	url = str(frappe.utils.get_url()).replace("http://","").replace("https://","")
	return url

@frappe.whitelist()
def lakukan_pull_node():
	url = get_url()
	print(str(url))
	if str(url) != "erp-pusat.gias.co.id":
		lakukan_pull_node_debug()
	else:
		list_event_producer = frappe.db.sql(""" SELECT name FROM `tabEvent Producer` WHERE name NOT IN ("https://erp-tbpku.gias.co.id","https://erp-tju.gias.co.id","https://erp-tjp.gias.co.id") """)
		# list_event_producer = frappe.db.sql(""" SELECT name FROM `tabEvent Producer` WHERE name  IN ("https://erp-pku.gias.co.id") """)
		for row in list_event_producer:
			command = """ cd /home/frappe/frappe-bench/ && bench --site {0} execute addons.custom_standard.custom_stock_entry.custom_pull_from_node --args "{{'{1}'}}" """.format(url,row[0])
			os.system(command)
			print(row[0])
			frappe.db.commit()

@frappe.whitelist()
def coba_benerin_material_request(site):
	url = get_url()
	print(str(site))
	print(str(url))
	if str(url) == "erp-pusat.gias.co.id":
		return
	
	# datetime object containing current date and time
	
	list_pull_node = frappe.db.sql("""
		SELECT eul.name
		FROM `tabEvent Update Log` eul
		JOIN `tabMaterial Request` tmr
		ON tmr.name = eul.`docname`
		WHERE tmr.name NOT IN
		(
		SELECT NAME FROM `db_pusat`.`tabMaterial Request`
		)
		AND tmr.`docstatus` = 0
		AND tmr.`workflow_state`
		IN
		(
		 "Waiting PA GM Sales","Waiting Product Specialist","Waiting Deputy GM Branch","Waiting Personal Assistant","Waiting Proc Non Inv Staff","Waiting Proc Inv Staff","Waiting Cust. Service Delivery Staff","Waiting Warehouse Staff","Waiting Finance JKT Comision","Waiting GA Admin","Waiting GA Staff"
		)
		AND tmr.`material_request_type`
		IN
		("Purchase","Material Transfer")
		AND tmr.`blkp_is_not_null` = 0
		ORDER BY eul.`creation`
	""")
	for row in list_pull_node:
		now = datetime.now()+timedelta(hours=7)
		doc = frappe.get_doc("Event Update Log", row[0])
		doc.creation = now
		doc.db_update()
		time.sleep(1)
		print(now)
	frappe.db.commit()

	command = """ cd /home/frappe/frappe-bench/ && bench --site erp-pusat.gias.co.id execute addons.custom_standard.custom_stock_entry.custom_pull_from_node --args "{'https://erp-{}.gias.co.id'}" """.format(site)
	os.system(command)

			
@frappe.whitelist()
def lakukan_pull_node_pusat():
	url = get_url()
	print(str(url))
	# list_event_producer = frappe.db.sql(""" SELECT name FROM `tabEvent Producer` WHERE name NOT IN ("https://erp-tbpku.gias.co.id","https://erp-tju.gias.co.id","https://erp-tjp.gias.co.id") """)
	list_event_producer = frappe.db.sql(""" SELECT name FROM `tabEvent Producer` WHERE name  IN ("https://erp-bjm.gias.co.id") """)
	for row in list_event_producer:
		command = """ cd /home/frappe/frappe-bench/ && bench --site {0} execute addons.custom_standard.custom_stock_entry.custom_pull_from_node --args "{{'{1}'}}" """.format(url,row[0])
		os.system(command)
		print(row[0])


@frappe.whitelist()
def matikan_territory_sync():
	server = frappe.get_doc("Company","GIAS").server
	if server == "Cabang":
		list_event_producer = frappe.db.sql(""" SELECT name FROM `tabEvent Consumer` """)
		for row in list_event_producer:
			docu = frappe.get_doc("Event Consumer", row[0])
			for baris_item in docu.consumer_doctypes:
				if baris_item.ref_doctype == "Material Request":
					baris_item.condition = baris_item.condition.replace('doc.workflow_state == "Waiting Product Specialist"','doc.workflow_state == "Waiting PA GM Sales" or doc.workflow_state == "Waiting Product Specialist"')
					print(frappe.get_doc("Company","GIAS").nama_cabang)
					baris_item.db_update()



@frappe.whitelist()
def lakukan_pull_node_debug():
	url = get_url()
	print(str(url))
	if str(url) == "erp-pusat.gias.co.id":
		return 
	list_event_producer = frappe.db.sql(""" SELECT name FROM `tabEvent Producer` """)
	for row in list_event_producer:
		command = """ cd /home/frappe/frappe-bench/ && bench --site {0} execute addons.custom_standard.custom_stock_entry.debug_custom_pull_from_node --args "{{'{1}'}}" """.format(url,row[0])
		os.system(command)
		print(row[0])


@frappe.whitelist()
def lakukan_pull_node_debug_pusat():
	url = get_url()
	print(str(url))
	if str(url) != "erp-pusat.gias.co.id":
		return 
	list_event_producer = frappe.db.sql(""" SELECT name FROM `tabEvent Producer` WHERE name LIKE "%bjm%" """)
	for row in list_event_producer:
		command = """ cd /home/frappe/frappe-bench/ && bench --site {0} execute addons.custom_standard.custom_stock_entry.debug_pusat_custom_pull_from_node --args "{{'{1}'}}" """.format(url,row[0])
		os.system(command)
		print(row[0])

@frappe.whitelist()
def lakukan_pull_node_debug_pusat_2():
	url = get_url()
	print(str(url))
	if str(url) != "erp-pusat.gias.co.id":
		return 
	list_event_producer = frappe.db.sql(""" SELECT name FROM `tabEvent Producer` WHERE name LIKE "%pwt%" """)
	for row in list_event_producer:
		command = """ cd /home/frappe/frappe-bench/ && bench --site {0} execute addons.custom_standard.custom_stock_entry.custom_pull_from_node_pusat --args "{{'{1}'}}" """.format(url,row[0])
		os.system(command)
		print(row[0])

@frappe.whitelist()
def submit_pinv():
	list_pinv = frappe.db.sql(""" SELECT parent FROM `tabPurchase Invoice Item` 
		WHERE parent = "PI-1-22-12-00001 """)

	for row in list_pinv:
		doc = frappe.get_doc("Purchase Invoice", row[0])
		doc.submit()
		# doc.workflow_state = "Approved"
		# doc.db_update()

		# print(doc.name)
		# frappe.db.commit()

@frappe.whitelist()
def custom_get_info(show_failed=False) -> List[Dict]:
	if isinstance(show_failed, str):
		show_failed = json.loads(show_failed)

	conn = get_redis_conn()
	queues = Queue.all(conn)
	workers = Worker.all(conn)
	jobs = []

	def add_job(job: 'Job', name: str) -> None:
		# if job.kwargs.get('site') == frappe.local.site:
		job_info = {
			'job_name': job.kwargs.get('kwargs', {}).get('playbook_method')
				or job.kwargs.get('kwargs', {}).get('job_type')
				or str(job.kwargs.get('job_name')),
			'status': job.get_status(),
			'place' : job.kwargs.get('site'),
			'color': JOB_COLORS[job.get_status()]
		}

		if job.exc_info:
			job_info['exc_info'] = job.exc_info
		if JOB_COLORS[job.get_status()] == "blue":
			jobs.append(job_info)

	# show worker jobs
	for worker in workers:
		job = worker.get_current_job()
		if job:
			add_job(job, worker.name)

	for queue in queues:
		# show active queued jobs
		if queue.name != 'failed':
			for job in queue.jobs:
				add_job(job, queue.name)

		# show failed jobs, if requested
		if show_failed:
			fail_registry = queue.failed_job_registry
			for job_id in fail_registry.get_job_ids():
				job = queue.fetch_job(job_id)
				if job:
					add_job(job, queue.name)

	return jobs
@frappe.whitelist()
def custom_autoname_item(doc,method):
	company_doc = frappe.get_doc("Company", "GIAS")
	if company_doc.server == "Pusat":
		if doc.item_group:
			doc_item_group = frappe.get_doc("Item Group", doc.item_group)
			if doc_item_group.code and doc_item_group.parent_code:
				tax = "P"
				if doc.tax_or_non_tax == "Non Tax":
					tax = "N"
				
				doc.item_code = doc_item_group.code + "-" + doc_item_group.parent_code + "-" + tax + "-" + ".######"
			else:
				frappe.throw("Please insert Code or Parent Code into the Item Group " + doc.item_group)
		if "######" in doc.item_code:
			doc.name = make_autoname(doc.item_code)
			doc.item_code = doc.name
		
@frappe.whitelist()
def update_print_format():
		
	print(frappe.get_doc("Company","GIAS").nama_cabang)

@frappe.whitelist()
def update_custom_field():
	company_doc = frappe.get_doc("Company", "GIAS")
	if company_doc.server == "Pusat":
		return
	else:
		doc = frappe.get_doc("DocType","Stock Entry")
		for row in doc.fields:
			if row.fieldname in ["to_warehouse","items","target_warehouse_address"]:
				row.read_only_depends_on = 'eval:doc.sync_name && doc.stock_entry_type == "Material Receipt"'
				print(1)
		doc.save()


@frappe.whitelist()
def updatepr():
	try:
		doc = frappe.get_doc("Custom Field","Stock Entry-alamat")
		doc.fieldtype = "Text"
		doc.save()
		print(doc.fieldtype)
	except:
		pass

@frappe.whitelist()
def update_field_custom():
	print(frappe.get_doc("Company","GIAS").nama_cabang)
	company_doc = frappe.get_doc("Company", "GIAS")
	if company_doc.server != "Pusat":
		cust_doc = frappe.get_doc({"__islocal":1,"name":"BAK Table","creation":"2023-01-17 13:54:43.323149","modified":"2023-01-17 14:06:09.054103","modified_by":"Administrator","owner":"Administrator","docstatus":0,"idx":0,"issingle":0,"is_tree":0,"istable":1,"editable_grid":1,"track_changes":0,"module":"Addons","name_case":"","sort_field":"modified","sort_order":"DESC","read_only":0,"in_create":0,"allow_copy":0,"allow_rename":1,"allow_import":0,"hide_toolbar":0,"track_seen":0,"max_attachments":0,"document_type":"","engine":"InnoDB","is_submittable":0,"show_name_in_global_search":0,"custom":1,"beta":0,"has_web_view":0,"allow_guest_to_view":0,"email_append_to":0,"quick_entry":0,"track_views":0,"is_virtual":0,"allow_events_in_timeline":0,"allow_auto_repeat":0,"show_preview_popup":0,"index_web_pages_for_search":1,"doctype":"DocType","fields":[{"name":"c3ba279ab7","creation":"2023-01-17 13:54:43.323149","modified":"2023-01-17 14:06:09.054103","modified_by":"try@gias.co.id","owner":"try@gias.co.id","docstatus":0,"parent":"BAK Table","parentfield":"fields","parenttype":"DocType","idx":1,"fieldname":"no_bak","label":"No BAK","fieldtype":"Link","options":"Berita Acara Komplain","search_index":0,"hidden":0,"set_only_once":0,"allow_in_quick_entry":0,"print_hide":0,"report_hide":0,"reqd":0,"bold":0,"in_global_search":0,"collapsible":0,"unique":0,"no_copy":0,"allow_on_submit":0,"show_preview_popup":0,"permlevel":0,"ignore_user_permissions":0,"columns":0,"in_list_view":1,"fetch_if_empty":0,"in_filter":0,"remember_last_selected_value":0,"ignore_xss_filter":0,"print_hide_if_no_value":0,"allow_bulk_edit":0,"in_standard_filter":0,"in_preview":0,"read_only":0,"precision":"","length":0,"translatable":0,"hide_border":0,"hide_days":0,"hide_seconds":0,"non_negative":0,"doctype":"DocField"}],"permissions":[],"actions":[],"links":[],"__last_sync_on":"2023-04-14T09:52:12.789Z"})
		cust_doc.save()
		cust_doc = frappe.get_doc({"__islocal":1,"name":"Journal Entry Account Tax-branch","owner":"Administrator","creation":"2023-04-14 16:33:51.405915","modified":"2023-04-14 16:33:51.405915","modified_by":"Administrator","idx":29,"docstatus":0,"dt":"Journal Entry Account Tax","label":"Branch","fieldname":"branch","insert_after":"user_remark","length":0,"fieldtype":"Link","precision":"","hide_seconds":0,"hide_days":0,"options":"Branch","fetch_from":"","fetch_if_empty":0,"collapsible":0,"default":"SPRINGHILL","non_negative":0,"reqd":0,"unique":0,"read_only":0,"ignore_user_permissions":0,"hidden":0,"print_hide":0,"print_hide_if_no_value":0,"no_copy":0,"allow_on_submit":0,"in_list_view":1,"in_standard_filter":0,"in_global_search":0,"in_preview":0,"bold":0,"report_hide":0,"search_index":0,"allow_in_quick_entry":0,"ignore_xss_filter":0,"translatable":0,"hide_border":0,"permlevel":0,"columns":1,"doctype":"Custom Field","__last_sync_on":"2023-04-14T09:45:16.050Z"})
		cust_doc.save()
		cust_doc = frappe.get_doc({"__islocal":1,"name":"Journal Entry Account Tax-party_full_name","owner":"Administrator","creation":"2023-04-14 16:34:20.483519","modified":"2023-04-14 16:34:20.483519","modified_by":"Administrator","idx":7,"docstatus":0,"dt":"Journal Entry Account Tax","label":"Party Full Name","fieldname":"party_full_name","insert_after":"party","length":0,"fieldtype":"Data","precision":"","hide_seconds":0,"hide_days":0,"fetch_if_empty":0,"collapsible":0,"non_negative":0,"reqd":0,"unique":0,"read_only":1,"ignore_user_permissions":0,"hidden":0,"print_hide":0,"print_hide_if_no_value":0,"no_copy":1,"allow_on_submit":0,"in_list_view":0,"in_standard_filter":0,"in_global_search":0,"in_preview":0,"bold":0,"report_hide":0,"search_index":0,"allow_in_quick_entry":0,"ignore_xss_filter":0,"translatable":1,"hide_border":0,"permlevel":0,"columns":0,"doctype":"Custom Field","__last_sync_on":"2023-04-14T09:45:16.928Z"})
		cust_doc.save()
		cust_doc = frappe.get_doc({"__islocal":1,"name":"Journal Entry Account Tax-usd_notes","owner":"Administrator","creation":"2023-04-14 16:34:34.649897","modified":"2023-04-14 16:34:34.649897","modified_by":"Administrator","idx":22,"docstatus":0,"dt":"Journal Entry Account Tax","label":"USD Notes","fieldname":"usd_notes","insert_after":"credit","length":0,"fieldtype":"Section Break","precision":"","hide_seconds":0,"hide_days":0,"fetch_if_empty":0,"collapsible":0,"non_negative":0,"reqd":0,"unique":0,"read_only":0,"ignore_user_permissions":0,"hidden":1,"print_hide":0,"print_hide_if_no_value":0,"no_copy":0,"allow_on_submit":0,"in_list_view":0,"in_standard_filter":0,"in_global_search":0,"in_preview":0,"bold":0,"report_hide":0,"search_index":0,"allow_in_quick_entry":0,"ignore_xss_filter":0,"translatable":0,"hide_border":0,"permlevel":0,"columns":0,"doctype":"Custom Field","__last_sync_on":"2023-04-14T09:45:17.653Z"})
		cust_doc.save()
		cust_doc = frappe.get_doc({"__islocal":1,"name":"Journal Entry Account Tax-currency_exhange","owner":"Administrator","creation":"2023-04-14 16:36:12.507060","modified":"2023-04-14 16:36:12.507060","modified_by":"Administrator","idx":23,"docstatus":0,"dt":"Journal Entry Account Tax","label":"Currency Exhange","fieldname":"currency_exhange","insert_after":"usd_notes","length":0,"fieldtype":"Currency","precision":"","hide_seconds":0,"hide_days":0,"fetch_if_empty":0,"collapsible":0,"non_negative":0,"reqd":0,"unique":0,"read_only":0,"ignore_user_permissions":0,"hidden":1,"print_hide":0,"print_hide_if_no_value":0,"no_copy":0,"allow_on_submit":0,"in_list_view":0,"in_standard_filter":0,"in_global_search":0,"in_preview":0,"bold":0,"report_hide":0,"search_index":0,"allow_in_quick_entry":0,"ignore_xss_filter":0,"translatable":0,"hide_border":0,"permlevel":0,"columns":0,"doctype":"Custom Field","__last_sync_on":"2023-04-14T09:45:19.326Z"})
		cust_doc.save()
		cust_doc = frappe.get_doc({"__islocal":1,"name":"Journal Entry Account Tax-debit_in_usd","owner":"Administrator","creation":"2023-04-14 16:36:37.457240","modified":"2023-04-14 16:36:37.457240","modified_by":"Administrator","idx":24,"docstatus":0,"dt":"Journal Entry Account Tax","label":"Debit in USD","fieldname":"debit_in_usd","insert_after":"currency_exhange","length":0,"fieldtype":"Currency","precision":"","hide_seconds":0,"hide_days":0,"fetch_if_empty":0,"collapsible":0,"non_negative":0,"reqd":0,"unique":0,"read_only":0,"ignore_user_permissions":0,"hidden":1,"print_hide":0,"print_hide_if_no_value":0,"no_copy":0,"allow_on_submit":0,"in_list_view":0,"in_standard_filter":0,"in_global_search":0,"in_preview":0,"bold":0,"report_hide":0,"search_index":0,"allow_in_quick_entry":0,"ignore_xss_filter":0,"translatable":0,"hide_border":0,"permlevel":0,"columns":0,"doctype":"Custom Field","__last_sync_on":"2023-04-14T09:45:19.512Z"})
		cust_doc.save()
		cust_doc = frappe.get_doc({"__islocal":1,"name":"Journal Entry Account Tax-credit_in_usd","owner":"Administrator","creation":"2023-04-14 16:36:57.338686","modified":"2023-04-14 16:36:57.338686","modified_by":"Administrator","idx":25,"docstatus":0,"dt":"Journal Entry Account Tax","label":"Credit in USD","fieldname":"credit_in_usd","insert_after":"debit_in_usd","length":0,"fieldtype":"Currency","precision":"","hide_seconds":0,"hide_days":0,"fetch_if_empty":0,"collapsible":0,"non_negative":0,"reqd":0,"unique":0,"read_only":0,"ignore_user_permissions":0,"hidden":1,"print_hide":0,"print_hide_if_no_value":0,"no_copy":0,"allow_on_submit":0,"in_list_view":0,"in_standard_filter":0,"in_global_search":0,"in_preview":0,"bold":0,"report_hide":0,"search_index":0,"allow_in_quick_entry":0,"ignore_xss_filter":0,"translatable":0,"hide_border":0,"permlevel":0,"columns":0,"doctype":"Custom Field","__last_sync_on":"2023-04-14T09:45:19.761Z"})
		cust_doc.save()
		cust_doc = frappe.get_doc({"__islocal":1,"name":"Journal Entry Tax-dari_purchase_invoice","owner":"Administrator","creation":"2023-04-14 16:40:30.575651","modified":"2023-04-14 16:40:36.507550","modified_by":"Administrator","idx":6,"docstatus":0,"dt":"Journal Entry Tax","label":"Dari Document","fieldname":"dari_purchase_invoice","insert_after":"finance_book","length":0,"fieldtype":"Data","precision":"","hide_seconds":0,"hide_days":0,"fetch_if_empty":0,"collapsible":0,"non_negative":0,"reqd":0,"unique":0,"read_only":1,"ignore_user_permissions":0,"hidden":0,"print_hide":1,"print_hide_if_no_value":0,"no_copy":1,"allow_on_submit":0,"in_list_view":0,"in_standard_filter":0,"in_global_search":0,"in_preview":0,"bold":0,"report_hide":1,"search_index":0,"allow_in_quick_entry":0,"ignore_xss_filter":0,"translatable":0,"hide_border":0,"permlevel":0,"columns":0,"doctype":"Custom Field","__last_sync_on":"2023-04-14T09:45:21.743Z"})
		cust_doc.save()
		cust_doc = frappe.get_doc({"__islocal":1,"name":"Journal Entry Tax-stock_entry_1","owner":"Administrator","creation":"2023-04-14 16:40:48.198591","modified":"2023-04-14 16:40:52.588112","modified_by":"Administrator","idx":7,"docstatus":0,"dt":"Journal Entry Tax","label":"Stock Entry","fieldname":"stock_entry_1","insert_after":"dari_purchase_invoice","length":0,"fieldtype":"Link","precision":"","hide_seconds":0,"hide_days":0,"options":"Stock Entry","fetch_if_empty":0,"collapsible":0,"non_negative":0,"reqd":0,"unique":0,"read_only":0,"ignore_user_permissions":0,"hidden":0,"print_hide":0,"print_hide_if_no_value":0,"no_copy":0,"allow_on_submit":0,"in_list_view":0,"in_standard_filter":0,"in_global_search":0,"in_preview":0,"bold":0,"report_hide":0,"search_index":0,"allow_in_quick_entry":0,"ignore_xss_filter":0,"translatable":0,"hide_border":0,"permlevel":0,"columns":0,"doctype":"Custom Field","__last_sync_on":"2023-04-14T09:45:22.057Z"})
		cust_doc.save()
		cust_doc = frappe.get_doc({"__islocal":1,"name":"Journal Entry Tax-cabang","owner":"Administrator","creation":"2023-04-14 16:41:16.108958","modified":"2023-04-14 16:41:16.108958","modified_by":"Administrator","idx":12,"docstatus":0,"dt":"Journal Entry Tax","label":"Cabang","fieldname":"cabang","insert_after":"posting_date","length":0,"fieldtype":"Link","precision":"","hide_seconds":0,"hide_days":0,"options":"List Company GIAS","fetch_if_empty":0,"collapsible":0,"default":"GIAS SPRINGHILL","non_negative":0,"reqd":0,"unique":0,"read_only":0,"ignore_user_permissions":0,"hidden":1,"print_hide":0,"print_hide_if_no_value":0,"no_copy":0,"allow_on_submit":0,"in_list_view":0,"in_standard_filter":0,"in_global_search":0,"in_preview":0,"bold":0,"report_hide":0,"search_index":0,"allow_in_quick_entry":0,"ignore_xss_filter":0,"translatable":0,"hide_border":0,"permlevel":0,"columns":0,"doctype":"Custom Field","__last_sync_on":"2023-04-14T09:45:22.408Z"})
		cust_doc.save()
		cust_doc = frappe.get_doc({"__islocal":1,"name":"Journal Entry Tax-purchase_taxes_and_charges_template","owner":"Administrator","creation":"2023-04-14 16:41:40.591384","modified":"2023-04-14 16:41:40.591384","modified_by":"Administrator","idx":16,"docstatus":0,"dt":"Journal Entry Tax","label":"Purchase Taxes and Charges Template","fieldname":"purchase_taxes_and_charges_template","insert_after":"section_break99","length":0,"fieldtype":"Link","precision":"","hide_seconds":0,"hide_days":0,"options":"Purchase Taxes and Charges Template","fetch_if_empty":0,"collapsible":0,"depends_on":"eval:doc.voucher_type == \"Debit Note - Pembelian\"","non_negative":0,"reqd":0,"unique":0,"read_only":0,"ignore_user_permissions":0,"hidden":1,"print_hide":0,"print_hide_if_no_value":0,"no_copy":0,"allow_on_submit":0,"in_list_view":0,"in_standard_filter":0,"in_global_search":0,"in_preview":0,"bold":0,"report_hide":0,"search_index":0,"allow_in_quick_entry":0,"ignore_xss_filter":0,"translatable":0,"hide_border":0,"permlevel":0,"columns":0,"doctype":"Custom Field","__last_sync_on":"2023-04-14T09:45:22.557Z"})
		cust_doc.save()
		cust_doc = frappe.get_doc({"__islocal":1,"name":"Journal Entry Tax-purchase_taxes_and_charges","owner":"Administrator","creation":"2023-04-14 16:41:54.769664","modified":"2023-04-14 16:41:54.769664","modified_by":"Administrator","idx":17,"docstatus":0,"dt":"Journal Entry Tax","label":"Purchase Taxes and Charges","fieldname":"purchase_taxes_and_charges","insert_after":"purchase_taxes_and_charges_template","length":0,"fieldtype":"Table","precision":"","hide_seconds":0,"hide_days":0,"options":"Purchase Taxes and Charges","fetch_if_empty":0,"collapsible":0,"depends_on":"eval:doc.voucher_type == \"Debit Note - Pembelian\"","non_negative":0,"reqd":0,"unique":0,"read_only":0,"ignore_user_permissions":0,"hidden":1,"print_hide":0,"print_hide_if_no_value":0,"no_copy":0,"allow_on_submit":0,"in_list_view":0,"in_standard_filter":0,"in_global_search":0,"in_preview":0,"bold":0,"report_hide":0,"search_index":0,"allow_in_quick_entry":0,"ignore_xss_filter":0,"translatable":0,"hide_border":0,"permlevel":0,"columns":0,"doctype":"Custom Field","__last_sync_on":"2023-04-14T09:45:26.038Z"})
		cust_doc.save()
		cust_doc = frappe.get_doc({"__islocal":1,"name":"Journal Entry Tax-sales_taxes_and_charges_template","owner":"Administrator","creation":"2023-04-14 16:42:09.454253","modified":"2023-04-14 16:42:09.454253","modified_by":"Administrator","idx":18,"docstatus":0,"dt":"Journal Entry Tax","label":"Sales Taxes and Charges Template","fieldname":"sales_taxes_and_charges_template","insert_after":"purchase_taxes_and_charges","length":0,"fieldtype":"Link","precision":"","hide_seconds":0,"hide_days":0,"options":"Sales Taxes and Charges Template","fetch_if_empty":0,"collapsible":0,"depends_on":"eval:doc.voucher_type == \"Credit Note - Penjualan\"","non_negative":0,"reqd":0,"unique":0,"read_only":0,"ignore_user_permissions":0,"hidden":1,"print_hide":0,"print_hide_if_no_value":0,"no_copy":0,"allow_on_submit":0,"in_list_view":0,"in_standard_filter":0,"in_global_search":0,"in_preview":0,"bold":0,"report_hide":0,"search_index":0,"allow_in_quick_entry":0,"ignore_xss_filter":0,"translatable":0,"hide_border":0,"permlevel":0,"columns":0,"doctype":"Custom Field","__last_sync_on":"2023-04-14T09:49:10.329Z"})
		cust_doc.save()
		cust_doc = frappe.get_doc({"__islocal":1,"name":"Journal Entry Tax-sales_taxes_and_charges","owner":"Administrator","creation":"2023-04-14 16:42:24.465460","modified":"2023-04-14 16:42:24.465460","modified_by":"Administrator","idx":19,"docstatus":0,"dt":"Journal Entry Tax","label":"Sales Taxes and Charges","fieldname":"sales_taxes_and_charges","insert_after":"sales_taxes_and_charges_template","length":0,"fieldtype":"Table","precision":"","hide_seconds":0,"hide_days":0,"options":"Sales Taxes and Charges","fetch_if_empty":0,"collapsible":0,"depends_on":"eval:doc.voucher_type == \"Credit Note - Penjualan\"","non_negative":0,"reqd":0,"unique":0,"read_only":0,"ignore_user_permissions":0,"hidden":1,"print_hide":0,"print_hide_if_no_value":0,"no_copy":0,"allow_on_submit":0,"in_list_view":0,"in_standard_filter":0,"in_global_search":0,"in_preview":0,"bold":0,"report_hide":0,"search_index":0,"allow_in_quick_entry":0,"ignore_xss_filter":0,"translatable":0,"hide_border":0,"permlevel":0,"columns":0,"doctype":"Custom Field","__last_sync_on":"2023-04-14T09:45:26.936Z"})
		cust_doc.save()
		cust_doc = frappe.get_doc({"__islocal":1,"name":"Journal Entry Tax-section_break_29","owner":"Administrator","creation":"2023-04-14 16:42:41.157547","modified":"2023-04-14 16:42:42.952575","modified_by":"Administrator","idx":20,"docstatus":0,"dt":"Journal Entry Tax","label":"","fieldname":"section_break_29","insert_after":"sales_taxes_and_charges","length":0,"fieldtype":"Section Break","precision":"","hide_seconds":0,"hide_days":0,"fetch_if_empty":0,"collapsible":0,"non_negative":0,"reqd":0,"unique":0,"read_only":0,"ignore_user_permissions":0,"hidden":0,"print_hide":0,"print_hide_if_no_value":0,"no_copy":0,"allow_on_submit":0,"in_list_view":0,"in_standard_filter":0,"in_global_search":0,"in_preview":0,"bold":0,"report_hide":0,"search_index":0,"allow_in_quick_entry":0,"ignore_xss_filter":0,"translatable":0,"hide_border":0,"permlevel":0,"columns":0,"doctype":"Custom Field","__last_sync_on":"2023-04-14T09:45:27.945Z"})
		cust_doc.save()
		cust_doc = frappe.get_doc({"__islocal":1,"name":"Journal Entry Tax-from_return_dn","owner":"Administrator","creation":"2023-04-14 16:42:52.435111","modified":"2023-04-14 16:42:52.435111","modified_by":"Administrator","idx":13,"docstatus":0,"dt":"Journal Entry Tax","label":"From Return DN","fieldname":"from_return_dn","insert_after":"cabang","length":0,"fieldtype":"Link","precision":"","hide_seconds":0,"hide_days":0,"options":"Delivery Note","fetch_if_empty":0,"collapsible":0,"non_negative":0,"reqd":0,"unique":0,"read_only":1,"ignore_user_permissions":0,"hidden":0,"print_hide":1,"print_hide_if_no_value":0,"no_copy":1,"allow_on_submit":0,"in_list_view":0,"in_standard_filter":0,"in_global_search":0,"in_preview":0,"bold":0,"report_hide":1,"search_index":0,"allow_in_quick_entry":0,"ignore_xss_filter":0,"translatable":0,"hide_border":0,"permlevel":0,"columns":0,"doctype":"Custom Field","__last_sync_on":"2023-04-14T09:45:27.752Z"})
		cust_doc.save()
		cust_doc = frappe.get_doc({"__islocal":1,"name":"Journal Entry Tax-from_return_prec","owner":"Administrator","creation":"2023-04-14 16:43:03.810175","modified":"2023-04-14 16:43:03.810175","modified_by":"Administrator","idx":14,"docstatus":0,"dt":"Journal Entry Tax","label":"From Return PREC","fieldname":"from_return_prec","insert_after":"from_return_dn","length":0,"fieldtype":"Link","precision":"","hide_seconds":0,"hide_days":0,"options":"Purchase Receipt","fetch_if_empty":0,"collapsible":0,"non_negative":0,"reqd":0,"unique":0,"read_only":1,"ignore_user_permissions":0,"hidden":0,"print_hide":1,"print_hide_if_no_value":0,"no_copy":1,"allow_on_submit":0,"in_list_view":0,"in_standard_filter":0,"in_global_search":0,"in_preview":0,"bold":0,"report_hide":1,"search_index":0,"allow_in_quick_entry":0,"ignore_xss_filter":0,"translatable":0,"hide_border":0,"permlevel":0,"columns":0,"doctype":"Custom Field","__last_sync_on":"2023-04-14T09:45:32.733Z"})
		cust_doc.save()
		cust_doc = frappe.get_doc({"__islocal":1,"name":"Journal Entry Tax-no_bak","owner":"Administrator","creation":"2023-04-14 16:43:22.820085","modified":"2023-04-14 16:43:22.820085","modified_by":"Administrator","idx":15,"docstatus":0,"dt":"Journal Entry Tax","label":"No BAK","fieldname":"no_bak","insert_after":"from_return_prec","length":0,"fieldtype":"Link","precision":"","hide_seconds":0,"hide_days":0,"options":"Berita Acara Komplain","fetch_from":"from_return_prec.no_bak","fetch_if_empty":1,"collapsible":0,"depends_on":"","non_negative":0,"reqd":0,"unique":0,"read_only":0,"ignore_user_permissions":0,"hidden":1,"print_hide":0,"print_hide_if_no_value":0,"no_copy":0,"allow_on_submit":1,"in_list_view":0,"in_standard_filter":0,"in_global_search":0,"in_preview":0,"bold":0,"report_hide":0,"search_index":0,"allow_in_quick_entry":0,"ignore_xss_filter":0,"translatable":0,"hide_border":0,"permlevel":0,"columns":0,"doctype":"Custom Field","__last_sync_on":"2023-04-14T09:45:33.060Z"})
		cust_doc.save()
		cust_doc = frappe.get_doc({"__islocal":1,"name":"Journal Entry Tax-bak","owner":"Administrator","creation":"2023-04-14 16:43:50.777857","modified":"2023-04-14 16:43:50.777857","modified_by":"Administrator","idx":16,"docstatus":0,"dt":"Journal Entry Tax","label":"BAK","fieldname":"bak","insert_after":"no_bak","length":0,"fieldtype":"Table","precision":"","hide_seconds":0,"hide_days":0,"options":"BAK Table","fetch_if_empty":0,"collapsible":0,"depends_on":"eval:doc.from_return_prec != \"\"","non_negative":0,"reqd":0,"unique":0,"read_only":0,"ignore_user_permissions":0,"hidden":0,"print_hide":0,"print_hide_if_no_value":0,"no_copy":0,"allow_on_submit":1,"in_list_view":0,"in_standard_filter":0,"in_global_search":0,"in_preview":0,"bold":0,"report_hide":0,"search_index":0,"allow_in_quick_entry":0,"ignore_xss_filter":0,"translatable":0,"hide_border":0,"permlevel":0,"columns":0,"doctype":"Custom Field","__last_sync_on":"2023-04-14T09:45:33.307Z"})
		cust_doc.save()

@frappe.whitelist()
def update_expense_claim_type():
	print(frappe.get_doc("Company","GIAS").nama_cabang)
	company_doc = frappe.get_doc("Company", "GIAS")
	if company_doc.server != "Pusat":
		# # doc = frappe.get_doc("Expense Claim Type","ASURANSI AIA")
		# # doc.delete()
		# doc = frappe.get_doc("Expense Claim Type","BBM DIREKTUR, MANAGER, SALES, SUPIR")
		# doc.delete()
		# doc = frappe.get_doc("Expense Claim Type","BIAYA PARKIR")
		# doc.delete()
		doc = frappe.get_doc("Expense Claim Type","Calls")
		doc.delete()
		doc = frappe.get_doc("Expense Claim Type","Food")
		doc.delete()
		doc = frappe.get_doc("Expense Claim Type","Medical")
		doc.delete()
		doc = frappe.get_doc("Expense Claim Type","Others")
		doc.delete()
		# doc = frappe.get_doc("Expense Claim Type","PREMI PENSIUN MANULIFE")
		# doc.delete()
		# doc = frappe.get_doc("Expense Claim Type","PROYEK HOLLAND VILLAGE - MOCK UP")
		# doc.delete()
		doc = frappe.get_doc("Expense Claim Type","Travel")
		doc.delete()

@frappe.whitelist()
def update_role():
	try:
		role_doc = frappe.get_doc({"__islocal":1,"name":"view_ledger_create.delete_gl_custom","owner":"Administrator","creation":"2022-03-26 01:02:27.581653","modified":"2023-07-27 17:41:45.997534","modified_by":"Administrator","idx":63,"docstatus":0,"stopped":0,"method":"addons.custom_standard.view_ledger_create.delete_gl_custom","frequency":"Cron","cron_format":"0/5 * * * *","last_execution":"2023-08-16 18:50:58.325766","create_log":0,"doctype":"Scheduled Job Type","__last_sync_on":"2023-08-16T11:54:54.638Z"})
		role_doc.save()
		
	except:
		print("fail")


	
@frappe.whitelist()
def update_doctype():
	print(frappe.get_doc("Company","GIAS").nama_cabang)
	company_doc = frappe.get_doc("Company", "GIAS")
	
	doc = frappe.get_doc("DocType","GL Entry Custom")
	for row in doc.fields:
		if row.label == "Doc Remarks":
			row.fieldtype = "Long Text"
	try:
		doc.save()
	except:
		print("GAGAL")

@frappe.whitelist()
def update_mode_of_payment():
		
	print(frappe.get_doc("Company","GIAS").nama_cabang)
	company_doc = frappe.get_doc("Company", "GIAS")
	try:
		if company_doc.server != "Pusat":
			mop_doc = frappe.get_doc("Mode of Payment", "Cheque")
			mop_doc.enabled = 0
			mop_doc.save()

			mop_doc = frappe.get_doc("Mode of Payment", "Credit Card")
			mop_doc.enabled = 0
			mop_doc.save()

			mop_doc = frappe.get_doc("Mode of Payment", "Wire Transfer")
			mop_doc.enabled = 0
			mop_doc.save()

			new_mop_doc = frappe.new_doc("Mode of Payment")
			new_mop_doc.enabled = 1
			new_mop_doc.type = "General"
			new_mop_doc.append("accounts",{
				"company" : "GIAS",
				"default_account" : "1168.01 - R/K - G"
			})
			new_mop_doc.mode_of_payment = "R/K"
			new_mop_doc.save()

			new_mop_doc = frappe.new_doc("Mode of Payment")
			new_mop_doc.enabled = 1
			new_mop_doc.type = "Bank"
			new_mop_doc.append("accounts",{
				"company" : "GIAS",
				"default_account" : "1122.91 - BANK BCA TONI NON - G"
			})
			new_mop_doc.mode_of_payment = "BANK BCA TONI"
			new_mop_doc.save()

			frappe.rename_doc("Mode of Payment", "Cash", "CASH")

			mop_doc = frappe.get_doc("Mode of Payment", "Bank Draft")
			mop_doc.append("accounts",{
				"company" : "GIAS",
				"default_account" : "1121.01 - BANK BCA 6840340790 - G"
			})
			mop_doc.save()
			frappe.rename_doc("Mode of Payment", "Bank Draft", "BANK BCA 0790")
	except:
		pass

@frappe.whitelist()
def delete_employee():
	company_doc = frappe.get_doc("Company", "GIAS")
	if company_doc.server != "Pusat":
		if company_doc.nama_cabang != "GIAS BANJARMASIN":
			print(company_doc.nama_cabang)
			list_emp = frappe.db.sql(""" SELECT name FROM `tabEmployee` """)
			for row in list_emp:
				ep = frappe.get_doc("Employee", row[0])
				ep.delete()
@frappe.whitelist()
def update_item_group():
	company_doc = frappe.get_doc("Company", "GIAS")
	if company_doc.server == "Pusat":
		nama_cabang = company_doc.nama_cabang
		print(nama_cabang)

		list_mr = frappe.db.sql(""" 
			UPDATE `tabItem Group` 
			SET parent_item_group = "All Item Group"
			WHERE (is_group = 1 AND parent_item_group IS NULL and name != "All Item Group")
			or (name = "PAKU PALLET" or name = "PAKU TAYAS")
			 """)
		frappe.db.commit()
		from frappe.utils.nestedset import rebuild_tree

		rebuild_tree("Item Group","parent_item_group")
		

@frappe.whitelist()
def update_workflow_cabang():
	company_doc = frappe.get_doc("Company", "GIAS")
	if company_doc.server != "Pusat":
		mreq_doc = frappe.get_doc("Workflow", "Material Request Final Evan")
		counter = 0
		mreq_doc.append("transitions",{
				"state" : "Waiting Personal Assistant",
				"action" : "Approve",
				"next_state" : "Waiting GM Cabang",
				"allowed" : "Personal Assistant",
				"allow_self_approval" : 1,
				"condition" : 'doc.ps_approver == "NONE"'
			})
		mreq_doc.append("transitions",{
				"state" : "Waiting Personal Assistant",
				"action" : "Reject",
				"next_state" : "Rejected",
				"allowed" : "Personal Assistant",
				"allow_self_approval" : 1,
				"condition" : 'doc.ps_approver == "NONE"'
			})

		mreq_doc.save()

		print(company_doc.nama_cabang)

@frappe.whitelist()
def update_material_request():
	company_doc = frappe.get_doc("Company", "GIAS")
	if company_doc.server != "Pusat":
		nama_cabang = company_doc.nama_cabang
		print(nama_cabang)
		list_mr = frappe.db.sql(""" SELECT name FROM `tabMaterial Request` WHERE cabang != "{}" """.format(nama_cabang))
		for row in list_mr:
			material_request = frappe.get_doc("Material Request", row[0])
			material_request.delete()


@frappe.whitelist()
def update_event_producer():
	company_doc = frappe.get_doc("Company", "GIAS")
	if company_doc.server != "Pusat":

		list_ep = frappe.db.sql(""" SELECT name FROM `tabEvent Producer` """)
		for row in list_ep:
			ep = frappe.get_doc("Event Producer", row[0])
			print(row[0])
			for row_doctype in ep.producer_doctypes:
				if row_doctype.ref_doctype == "Material Request":
					row_doctype.condition = row_doctype.condition.replace('doc.workflow_state == "Waiting GM Cabang" or','doc.workflow_state == "Cancelled" or doc.workflow_state == "Waiting GM Cabang" or')

			ep.save()

		print(company_doc.nama_cabang)

@frappe.whitelist()
def update_event_consumer():
	company_doc = frappe.get_doc("Company", "GIAS")
	if company_doc.server == "Pusat":
		list_ep = frappe.db.sql(""" SELECT name FROM `tabEvent Consumer` """)
		for row in list_ep:
			print(str(row[0]))
			ep = frappe.get_doc("Event Consumer", row[0])
			for row in ep.consumer_doctypes:
				if row.status == "Pending":
					row.status = "Approved"
			ep.save()

@frappe.whitelist()
def update_item_group_cabang():
	company_doc = frappe.get_doc("Company", "GIAS")
	if company_doc.server == "Cabang":
		list_ter = [["BANDUNG","KEC. BANDUNG"],
		["BANGLI","KEC. BANGLI"],
		["BANJAR","KEC. BANJAR"],
		["BANJAR BARU","KEC. BANJAR BARU"],
		["BANJARNEGARA","KEC. BANJARNEGARA"],
		["BANTAENG","KEC. BANTAENG"],
		["BANTUL","KEC. BANTUL"],
		["BANYUMAS","KEC. BANYUMAS"],
		["BANYUWANGI","KEC. BANYUWANGI"],
		["BATANG","KEC. BATANG"],
		["BATUR","KEC. BATUR"],
		["BELIK","KEC. BELIK"],
		["BENGKALIS","KEC. BENGKALIS"],
		["BENGKAYANG","KEC. BENGKAYANG"],
		["BINJAI","KEC. BINJAI"],
		["BOJONEGORO","KEC. BOJONEGORO"],
		["BONDOWOSO","KEC. BONDOWOSO"],
		["BONE","KEC. BONE"],
		["BOYOLALI","KEC. BOYOLALI"],
		["BREBES","KEC. BREBES"],
		["BULELENG","KEC. BULELENG"],
		["CIAMIS","KEC. CIAMIS"],
		["CIANJUR","KEC. CIANJUR"],
		["CILEGON","KEC. CILEGON"],
		["CIMAHI","KEC. CIMAHI"],
		["DEMAK","KEC. DEMAK"],
		["DEPOK","KEC. DEPOK"],
		["DOMPU","KEC. DOMPU"],
		["ENREKANG","KEC. ENREKANG"],
		["GIANYAR","KEC. GIANYAR"],
		["GOMBONG","KEC. GOMBONG"],
		["GRESIK","KEC. GRESIK"],
		["GROBOGAN","KEC. GROBOGAN"],
		["GUNUNGSITOLI","KEC. GUNUNGSITOLI"],
		["INDRAMAYU","KEC. INDRAMAYU"],
		["JAYAPURA","KEC. JAYAPURA"],
		["JEMBRANA","KEC. JEMBRANA"],
		["JEPARA","KEC. JEPARA"],
		["JOMBANG","KEC. JOMBANG"],
		["KAMPAR","KEC. KAMPAR"],
		["KAPUAS HULU","KEC. KAPUAS HULU"],
		["KARANG ASEM","KEC. KARANG ASEM"],
		["KARANGANYAR","KEC. KARANGANYAR"],
		["KEBUMEN","KEC. KEBUMEN"],
		["KEDIRI","KEC. KEDIRI"],
		["KENDAL","KEC. KENDAL"],
		["KENDARI","KEC. KENDARI"],
		["KEPAHIANG","KEC. KEPAHIANG"],
		["KETAPANG","KEC. KETAPANG"],
		["KLUNGKUNG","KEC. KLUNGKUNG"],
		["KOLAKA","KEC. KOLAKA"],
		["KONAWE","KEC. KONAWE"],
		["KROYA","KEC. KROYA"],
		["KUNINGAN","KEC. KUNINGAN"],
		["LAMONGAN","KEC. LAMONGAN"],
		["LUMAJANG","KEC. LUMAJANG"],
		["MADIUN","KEC. MADIUN"],
		["MAGETAN","KEC. MAGETAN"],
		["MAJALENGKA","KEC. MAJALENGKA"],
		["MAJENANG","KEC. MAJENANG"],
		["MAKASAR","KEC. MAKASAR"],
		["MAMUJU","KEC. MAMUJU"],
		["MATARAM","KEC. MATARAM"],
		["MERAUKE","KEC. MERAUKE"],
		["MESUJI","KEC. MESUJI"],
		["NABIRE","KEC. NABIRE"],
		["NGANJUK","KEC. NGANJUK"],
		["NGAWI","KEC. NGAWI"],
		["NUNUKAN","KEC. NUNUKAN"],
		["NUSAWUNGU","KEC. NUSAWUNGU"],
		["PACITAN","KEC. PACITAN"],
		["PADANG","KEC. PADANG"],
		["PAMEKASAN","KEC. PAMEKASAN"],
		["PANGANDARAN","KEC. PANGANDARAN"],
		["PATI","KEC. PATI"],
		["PATIMUAN","KEC. PATIMUAN"],
		["PAYAKUMBUH","KEC. PAYAKUMBUH"],
		["PELALAWAN","KEC. PELALAWAN"],
		["PEMALANG","KEC. PEMALANG"],
		["PIDIE","KEC. PIDIE"],
		["PONOROGO","KEC. PONOROGO"],
		["PRINGSEWU","KEC. PRINGSEWU"],
		["PURBALINGGA","KEC. PURBALINGGA"],
		["PURWAKARTA","KEC. PURWAKARTA"],
		["PURWODADI","KEC. PURWODADI"],
		["PURWOJATI","KEC. PURWOJATI"],
		["PURWOREJO","KEC. PURWOREJO"],
		["REMBANG","KEC. REMBANG"],
		["SALATIGA","KEC. SALATIGA"],
		["SAMBAS","KEC. SAMBAS"],
		["SAMPANG","KEC. SAMPANG"],
		["SAROLANGUN","KEC. SAROLANGUN"],
		["SELUMA","KEC. SELUMA"],
		["SERANG","KEC. SERANG"],
		["SIAK","KEC. SIAK"],
		["SIDAREJA","KEC. SIDAREJA"],
		["SIDOARJO","KEC. SIDOARJO"],
		["SINTANG","KEC. SINTANG"],
		["SITUBONDO","KEC. SITUBONDO"],
		["SLEMAN","KEC. SLEMAN"],
		["SOKARAJA","KEC. SOKARAJA"],
		["SORONG","KEC. SORONG"],
		["SRAGEN","KEC. SRAGEN"],
		["SUBANG","KEC. SUBANG"],
		["SUKABUMI","KEC. SUKABUMI"],
		["SUKOHARJO","KEC. SUKOHARJO"],
		["SUMBAWA","KEC. SUMBAWA"],
		["SUMPIUH","KEC. SUMPIUH"],
		["SUNGAI PENUH","KEC. SUNGAI PENUH"],
		["TABANAN","KEC. TABANAN"],
		["TANGERANG","KEC. TANGERANG"],
		["TANJUNG BALAI","KEC. TANJUNG BALAI"],
		["TEBING TINGGI","KEC. TEBING TINGGI"],
		["TEMANGGUNG","KEC. TEMANGGUNG"],
		["TRENGGALEK","KEC. TRENGGALEK"],
		["TUBAN","KEC. TUBAN"],
		["TULUNGAGUNG","KEC. TULUNGAGUNG"],
		["WAJO","KEC. WAJO"],
		["WANGON","KEC. WANGON"],
		["WONOGIRI","KEC. WONOGIRI"],
		["WONOSOBO","KEC. WONOSOBO"]]
		for ter in list_ter:
			try:
				frappe.rename_doc("Territory",ter[0],ter[1])
				print("{}-{}-{}".format(company_doc.nama_cabang,ter[0],ter[1]))
			except:
				print("{}-{}-{}-FAIL".format(company_doc.nama_cabang,ter[0],ter[1]))



@frappe.whitelist()
def generate_name_je():
	list_je = frappe.db.sql(""" SELECT name FROM `tabJournal Entry` WHERE name LIKE "DE%"
		and tax_or_non_tax = "Tax" and year(posting_date) = 2022  ORDER BY name """)
	for row in list_je:
		doc = frappe.get_doc("Journal Entry",row[0])
		singkatan = "HO"
		company_doc = frappe.get_doc("Company", doc.company)
		list_company_gias_doc = frappe.get_doc("List Company GIAS",company_doc.nama_cabang)
		singkatan = list_company_gias_doc.singkatan_cabang

		month = frappe.utils.formatdate(frappe.utils.getdate(doc.posting_date),"MM")
		year = frappe.utils.formatdate(frappe.utils.getdate(doc.posting_date),"YY")

		if doc.tax_or_non_tax == "Tax":
			tax = 1
		else:
			tax = 2

		if str(year) == "22" and tax == 1:
			doc.generated_name = make_autoname(doc.naming_series.replace("-{tax}-","-").replace("-1-","-").replace("{{singkatan}}",singkatan).replace(".YY.",year).replace(".MM.",month))
			print(doc.generated_name)
			doc.db_update()
			frappe.db.commit()


@frappe.whitelist()
def generate_name_exc():
	list_je = frappe.db.sql(""" SELECT name FROM `tabExpense Claim` WHERE (generated_name = "" OR generated_name IS NULL) and tax_or_non_tax = "Tax" and year(posting_date) = 2022 ORDER BY name """)
	for row in list_je:
		doc = frappe.get_doc("Expense Claim",row[0])
		singkatan = "HO"
		company_doc = frappe.get_doc("Company", doc.company)
		list_company_gias_doc = frappe.get_doc("List Company GIAS",company_doc.nama_cabang)
		singkatan = list_company_gias_doc.singkatan_cabang

		month = frappe.utils.formatdate(frappe.utils.getdate(doc.posting_date),"MM")
		year = frappe.utils.formatdate(frappe.utils.getdate(doc.posting_date),"YY")

		if doc.tax_or_non_tax == "Tax":
			tax = 1
		else:
			tax = 2

		if str(year) == "22" and tax == 1:
			doc.generated_name = make_autoname(doc.naming_series.replace("-{tax}-","-").replace("-1-","-").replace("{{singkatan}}",singkatan).replace(".YY.",year).replace(".MM.",month))
			print(doc.generated_name)
			doc.db_update()
			frappe.db.commit()

@frappe.whitelist()
def generate_name_ste():
	list_je = frappe.db.sql(""" SELECT name FROM `tabStock Entry` WHERE (generated_name = "" OR generated_name IS NULL) and tax_or_non_tax = "Tax" and year(posting_date) = 2022 ORDER BY name """)
	for row in list_je:
		doc = frappe.get_doc("Stock Entry",row[0])
		singkatan = "HO"
		
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
			doc.generated_name = make_autoname(doc.naming_series.replace("-1-","-").replace(".YY.",year).replace(".MM.",month))
			print(doc.generated_name)
			doc.db_update()
			frappe.db.commit()

@frappe.whitelist()
def proses_pasang_old_name():
	list_je = frappe.db.sql(""" UPDATE `tabJournal Entry` SET old_name = name WHERE old_name IS NULL OR old_name = "" and year(posting_date) = 2022 """)
	list_exc = frappe.db.sql(""" UPDATE `tabExpense Claim` SET old_name = name WHERE old_name IS NULL OR old_name = "" and year(posting_date) = 2022 """)
	list_ste = frappe.db.sql(""" UPDATE `tabStock Entry` SET old_name = name WHERE old_name IS NULL OR old_name = "" and year(posting_date) = 2022 """)
	print(frappe.get_doc("Company","GIAS").nama_cabang)

@frappe.whitelist()
def proses_rename():
	bulan = 0

	while bulan < 13:
		bulan = bulan + 1
		print("BULAN {}".format(bulan))
		list_je = frappe.db.sql(""" 
			SELECT name,generated_name 
			FROM `tabJournal Entry` 
			WHERE generated_name IS NOT NULL and generated_name != ""
			and month(posting_date) = {}
			and year(posting_date) = 2022
			and name != generated_name 
			and tax_or_non_tax = "Tax"
			AND generated_name NOT LIKE "DPRC%"
			ORDER BY name ASC
			
		""".format(bulan))

		for row in list_je:
			# print("JE-{}-{}".format(row[0],row[1]))
			frappe.rename_doc("Journal Entry",str(row[0]),str(row[1]))
			print("JE-{}".format(row[1]))
			frappe.db.commit()

		list_exc = frappe.db.sql(""" 
			SELECT name,generated_name 
			FROM `tabExpense Claim` 
			WHERE generated_name IS NOT NULL and generated_name != ""
			and month(posting_date) = {}
			and year(posting_date) = 2022
			and name != generated_name 
			and tax_or_non_tax = "Tax"
			ORDER BY generated_name
			
		""".format(bulan))
		
		for row in list_exc:
			frappe.rename_doc("Expense Claim",str(row[0]),str(row[1]))
			print("EXC-{}".format(row[1]))
			frappe.db.commit()

		list_ste = frappe.db.sql(""" 
			SELECT name,generated_name 
			FROM `tabStock Entry` 
			WHERE generated_name IS NOT NULL and generated_name != ""
			and month(posting_date) = {}
			and year(posting_date) = 2022
			and name != generated_name 
			and tax_or_non_tax = "Tax"
			ORDER BY generated_name
			
		""".format(bulan))
		
		for row in list_ste:
			frappe.rename_doc("Stock Entry",str(row[0]),str(row[1]))
			print("STE-{}".format(row[1]))
			frappe.db.commit()


# @frappe.whitelist()
# def update_custom_field():
	
# 	company_doc = frappe.get_doc("Company", "GIAS")
# 	if company_doc.server == "Cabang":
# 		print(company_doc.nama_cabang)

# 		df = frappe.get_doc("Custom Field","Material Request-section_break_6")
# 		df.label = ""
# 		df.save()

@frappe.whitelist()
def update_sales_person_name():
	list_inv = frappe.db.sql(""" SELECT name FROM `tabSales Invoice` WHERE sales_person IS NOT NULL and sales_person_name IS NULL """)
	for row in list_inv:
		doc = frappe.get_doc("Sales Invoice",row[0])
		doc.sales_person_name = doc.sales_person
		doc.db_update()
		print(str(doc.name))

@frappe.whitelist()
def update_tax_purchase():
	list_tax = frappe.db.sql(""" SELECT name FROM `tabPurchase Taxes and Charges Template` WHERE `is_default` = 1 """)

	for row in list_tax:

		test = frappe.get_doc("Purchase Taxes and Charges Template",row[0])
		test.is_default = 0
		test.default_tax = 1
		test.save()

@frappe.whitelist()
def update_field_cabang():
	
	company_doc = frappe.get_doc("Company", "GIAS")

	# df = frappe.get_doc('Custom Field','Sales Invoice-cost_center_discount_2')
	# df.hidden = 1
	# df.save()
	# df = frappe.get_doc('Custom Field','Sales Invoice-branch_discount_2')
	# df.hidden = 1
	# df.save()
	# df = frappe.get_doc('Custom Field','Sales Invoice-remark_discount_2')
	# df.hidden = 1
	# df.save()
	# df = frappe.get_doc('Custom Field','Purchase Invoice-cost_center_discount_2')
	# df.hidden = 1
	# df.save()
	# df = frappe.get_doc('Custom Field','Purchase Invoice-branch_discount_2')
	# df.hidden = 1
	# df.save()
	# df = frappe.get_doc('Custom Field','Purchase Invoice-remark_discount_2')
	# df.hidden = 1
	# df.save()
	# df.dt = "Sales Invoice"
	# df.label = "Cost Center Discount 2"
	# df.insert_after = "discount_2"
	# df.fieldtype = "Link"
	# df.options = "Cost Center"
	# try:
	# 	df.save()
		# print("SUCC-{}".format(company_doc.nama_cabang))
	# except:
	# 	print(company_doc.nama_cabang)

	if company_doc.server == "Cabang":
		df = frappe.new_doc('List Company GIAS')
		df.nama_company = "GIAS KEDIRI"
		try:
			df.save()
		except:
			print("GAGAL-{}".format(company_doc.nama_cabang))

		df = frappe.new_doc('List Company GIAS')
		df.nama_company = "DEPO SUKABUMI"
		df.alamat_dan_kontak = "Jl. Pelabuhan II KM. 5 no. 60. RT/RW: 004/001 Kelurahan Cipanengah Kecamatan Lembursitu Kota Sukabumi - Jawa Barat 43134 (Sebelah kantor Dinas pendidikan Sukabumi)"
		try:
			df.save()
		except:
			print("GAGAL-{}".format(company_doc.nama_cabang))

		df = frappe.new_doc('List Company GIAS')
		df.nama_company = "GIAS BELITUNG"
		df.alamat_dan_kontak = "Jl. Padat Karya RT 18 RW 07 Desa Air Merbau Kec. Tanjungpandan, Belitung"
		try:
			df.save()
		except:
			print("GAGAL-{}".format(company_doc.nama_cabang))

		# df = frappe.new_doc('Custom Field')
		# df.dt = "Customer"
		# df.label = "Customer Credit Limit Available"
		# df.insert_after = "show_credit_limit_section"
		# df.fieldtype = "Float"
		# df.read_only = 1
		# df.save()

		# df = frappe.new_doc('Custom Field')
		# df.dt = "Customer"
		# df.label = "Business Group Credit Limit"
		# df.insert_after = "customer_credit_limit_available"
		# df.fieldtype = "Float"
		# df.read_only = 1
		# df.save()

		# df = frappe.new_doc('Custom Field')
		# df.dt = "Customer"
		# df.label = "Business Group Credit Limit Available"
		# df.insert_after = "business_group_credit_limit"
		# df.fieldtype = "Float"
		# df.read_only = 1
		# df.save()

		
	# df = frappe.new_doc('Custom Field')
	# df.dt = "Purchase Invoice"
	# df.label = "Cost Center Discount 2"
	# df.insert_after = "discount_2"
	# df.fieldtype = "Link"
	# df.options = "Cost Center"
	# try:
	# 	df.save()
	# 	print("SUCC-{}".format(company_doc.nama_cabang))
	# except:
	# 	print(company_doc.nama_cabang)

	# df = frappe.new_doc('Custom Field')
	# df.dt = "Purchase Invoice"
	# df.label = "Branch Discount 2"
	# df.insert_after = "cost_center_discount_2"
	# df.fieldtype = "Link"
	# df.options = "Branch"
	# try:
	# 	df.save()
	# 	print("SUCC-{}".format(company_doc.nama_cabang))
	# except:
	# 	print(company_doc.nama_cabang)

	# df = frappe.new_doc('Custom Field')
	# df.dt = "Purchase Invoice"
	# df.label = "Remark Discount 2"
	# df.insert_after = "branch_discount_2"
	# df.fieldtype = "Small Text"
	# try:
	# 	df.save()
	# 	print("SUCC-{}".format(company_doc.nama_cabang))
	# except:
	# 	print(company_doc.nama_cabang)

@frappe.whitelist()
def update_report():
	company_doc = frappe.get_doc("Company", "GIAS")
	if company_doc.server == "Cabang":
		# cf = frappe.get_doc("Report", "Stock Booking Balance")
		# cf.disabled = 1
		# cf.save()

		# cf = frappe.get_doc("Report", "Stock Ledger Without Values")
		# cf.disabled = 1
		# cf.save()
		
		cf = frappe.get_doc("Report","Stock Ledger Without Value")
		cf.append("roles",{
			"role" : "GIAS Admin Penjualan"
		})
		try:
			cf.save()
		except:
			pass
		print(company_doc.nama_cabang)

@frappe.whitelist()
def delete_report():
	company_doc = frappe.get_doc("Company", "GIAS")
	list_ste = frappe.db.sql(""" SELECT name FROM `tabStock Entry` WHERE name IN
		(
			"STER-BPN-1-22-12-00019",
			"STER-BRU-1-22-12-00015",
			"STER-CRB-1-22-12-00010",
			"STER-GRN-1-22-12-00013",
			"STER-GRN-1-22-12-00012",
			"STER-JBI-1-22-12-00010",
			"STER-JBR-1-22-12-00025",
			"STER-KDI-1-22-12-00022",
			"STER-KDI-1-22-12-00021",
			"STER-LGG-1-22-12-00013",
			"STER-LMP-1-22-12-00007",
			"STER-MDN-1-22-12-00014",
			"STER-MDN-1-22-12-00013",
			"STER-MKS-1-22-12-00024",
			"STER-MDO-1-22-12-00015",
			"STER-PKU-1-22-12-00358",
			"STER-PKU-1-22-12-00357",
			"STER-PLB-1-22-12-00085",
			"STER-PNK-1-22-12-00202",
			"STER-PNK-1-22-12-00201",
			"STER-PWT-1-22-12-00022",
			"STER-TGL-1-22-12-00009"
			)
	 """)
	for row in list_ste:
		frappe.delete_doc("Stock Entry", row[0])
	print(company_doc.nama_cabang)
	
@frappe.whitelist()
def update_notification():
	company_doc = frappe.get_doc("Company", "GIAS")
	if company_doc.server == "Cabang":
		
		print(company_doc.nama_cabang)
		cf = frappe.get_doc("Notification", "New ToDo")
		if not cf.recipients:
			row = cf.append('recipients', {
				"receiver_by_document_field" : "owner"
			})
		cf.save()


@frappe.whitelist()
def make_list_company_gias():

	company_doc = frappe.get_doc("Company", "GIAS")	

	new_list_company_gias = frappe.new_doc("List Company GIAS")
	new_list_company_gias.nama_company = "GIAS PAREPARE"
	new_list_company_gias.singkatan_cabang = "PRE"
	new_list_company_gias.accounting_dimension = "PAREPARE"
	new_list_company_gias.region = "ALL TERRITORIES"
	new_list_company_gias.save()

	print(company_doc.nama_cabang)

@frappe.whitelist()
def make_branch():
	
	company_doc = frappe.get_doc("Company", "GIAS")
	
	print(company_doc.nama_cabang)
	new_branch = frappe.new_doc("Branch")
	new_branch.branch = "PAREPARE"
	try:
		new_branch.save()
	except:
		pass


@frappe.whitelist()
def cek_ada_berapa_ste():

	company_doc = frappe.get_doc("Company", "GIAS")
	list_ste = frappe.db.sql("SELECT name, posting_date, is_opening FROM `tabStock Entry` WHERE docstatus = 1")
	for row in list_ste:
		repair_gl_entry(row[0])
		print("{} - {}".format(company_doc.nama_cabang, row[0]))
	


@frappe.whitelist()
def centang_non_company_gias():

	company_doc = frappe.get_doc("Company", "GIAS")

	try:
		if company_doc.server != "Pusat":
			tjp = frappe.get_doc("List Company GIAS", "GIAS TANJUNG PINANG")
			tb = frappe.get_doc("List Company GIAS", "TRIBUANA BUMIPUSAKA")
			tjp.cabang_non_gias = 1
			tb.cabang_non_gias = 1
			tjp.save()
			tb.save()
			frappe.db.commit()
			print(company_doc.nama_cabang)
	except:
		print("{} - FAIL".format(company_doc.nama_cabang))

@frappe.whitelist()
def repair_ste():

	company_doc = frappe.get_doc("Company",frappe.db.sql(""" SELECT name FROM `tabCompany` """)[0][0])
	list_ste = frappe.db.sql("""SELECT
		gl.voucher_type,gl.voucher_no, gl.credit AS credit, SUM(sl.`actual_qty` * sl.valuation_rate * -1) AS total 
		,gl.credit - SUM(sl.`actual_qty` * sl.valuation_rate * -1) AS selisih
		FROM `tabGL Entry` gl
		JOIN `tabStock Ledger Entry` sl ON sl.voucher_no = gl.`voucher_no`
		JOIN `tabDelivery Note` dn ON gl.voucher_no = dn.name 
		WHERE gl.account = "1142 - PERSEDIAAN BARANG JADI - G"
		AND dn.is_return = 0
		AND gl.`is_cancelled` = 0
		AND gl.voucher_type = "Delivery Note"
		
		GROUP BY gl.`voucher_no`
		HAVING selisih > 1 OR selisih < -1
		""")

	for row in list_ste:

		print("{} - {}".format(row[0], row[1]))
		# ste_doc = frappe.get_doc("Stock Entry",row[0])
		# ste_doc.posting_date = "2022-02-28"
		# ste_doc.db_update()
		repair_gl_entry(row[0], row[1])

	# from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import debug_repost
	# debug_repost()

@frappe.whitelist()
def repair_gl_entry_untuk_qty_real():

	doctype = "Delivery Note"
	list_doc = [
		"DO-HO-1-22-03-00003"]

	for docname in list_doc:
		docu = frappe.get_doc(doctype, docname)	
		delete_sl = frappe.db.sql(""" DELETE FROM `tabStock Ledger Entry` WHERE voucher_no = "{}" """.format(docname))
		delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(docname))

		frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 1 WHERE `field` = "allow_negative_stock" """)
		docu.update_stock_ledger()
		docu.make_gl_entries()
		frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 0 WHERE `field` = "allow_negative_stock" """)


@frappe.whitelist()
def repair_gl_entry_invoice():
	invoice_list = frappe.db.sql(""" SELECT tje.name FROM `tabJournal Entry` tje
	LEFT JOIN `tabGL Entry` tgl ON tgl.`voucher_no` = tje.`name`
	WHERE tgl.name IS NULL
	AND tje.`docstatus` = 1 """)
	for row in invoice_list:
		# repair_gl_entry("Sales Invoice",row[0])
		# frappe.db.commit()
		# print(str(row[0]))
		inv = frappe.get_doc("Purchase Invoice", row[0])
		inv.submit()


@frappe.whitelist()
def repair_sl_entry_invoice():
	doc_list = []
	for row in doc_list:
		repair_gl_entry(row[0],row[1])
		frappe.db.commit()
		print(str(row[1]))
		# inv = frappe.get_doc("Purchase Invoice", row[0])
		# inv.submit()

@frappe.whitelist()
def operasi_stock_ledger():
	from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt,get_item_account_wise_additional_cost
	from addons.custom_standard.custom_purchase_receipt import custom_get_gl_entries
	from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
	from erpnext.controllers.stock_controller import StockController

	
	list_voucher = frappe.db.sql(""" 
		SELECT voucher_type, voucher_no,
		TIMESTAMP(posting_date,posting_time) FROM `tabStock Ledger Entry` WHERE
		docstatus = 2 AND is_cancelled = 0
		GROUP BY voucher_no
		ORDER BY TIMESTAMP(posting_date,posting_time) """)

	for row in list_voucher:
		if row[0] == "Purchase Receipt":
			PurchaseReceipt.get_gl_entries = custom_get_gl_entries
		elif row[0] == "Stock Entry":
			doc = frappe.get_doc("Stock Entry", row[0])
			if doc.stock_entry_type == "Material Receipt" and doc.rk_value > 0 :
				StockController.make_gl_entries = custom_make_gl_entries2
	
		repair_gl_entry_tanpa_repost(row[0],row[1])
		print("{}={}".format(row[0],row[1]))
		frappe.db.commit()

@frappe.whitelist()
def operasi_accounting_ledger():
	list_voucher = frappe.db.sql(""" 
		SELECT "Journal Entry", je.name
		FROM `tabJournal Entry` je 
		LEFT JOIN `tabGL Entry` tgl ON tgl.voucher_no = je.name
		WHERE je.`docstatus` = 1
		AND tgl.name IS NULL """)

	for row in list_voucher:
		repair_gl_entry_tanpa_sl(row[0],row[1])
		print("{}={}".format(row[0],row[1]))
		frappe.db.commit()
		docname = row[1]
		from addons.custom_standard.view_ledger_create import create_gl_custom_journal_entry_by_name
		create_gl_custom_journal_entry_by_name(docname)


@frappe.whitelist()
def repair_gl_entry_tanpa_repost(doctype,docname):
	
	docu = frappe.get_doc(doctype, docname)	
	if doctype == "Stock Entry":
		if docu.purpose == "Material Transfer":
			docu.calculate_rate_and_amount()
			for row in docu.items:
				row.db_update()

			docu.db_update()

	delete_sl = frappe.db.sql(""" DELETE FROM `tabStock Ledger Entry` WHERE voucher_no = "{}" """.format(docname))
	delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(docname))
	frappe.flags.repost_gl == True
	frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 1 WHERE `field` = "allow_negative_stock" """)
	docu.update_stock_ledger()
	docu.make_gl_entries()
	frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 0 WHERE `field` = "allow_negative_stock" """)

@frappe.whitelist()
def patch_ste_mtrans():
	ste_list = frappe.db.sql(""" SELECT name FROM `tabStock Entry`
		WHERE name IN (
		"STE-SMD-1-22-04-00004"
		)
		""")
		
	for row in ste_list:
		print(row[0])
		repair_gl_entry_mtrans("Stock Entry", row[0])



@frappe.whitelist()
def repair_gl_entry_mtrans(doctype,docname):
	
	docu = frappe.get_doc(doctype, docname)	
	if doctype == "Stock Entry":
		if docu.purpose == "Material Transfer":
			docu.calculate_rate_and_amount()
			for row in docu.items:
				row.db_update()

			docu.db_update()

	delete_sl = frappe.db.sql(""" DELETE FROM `tabStock Ledger Entry` WHERE voucher_no = "{}" """.format(docname))
	delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(docname))
	frappe.flags.repost_gl == True
	frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 1 WHERE `field` = "allow_negative_stock" """)
	docu.update_stock_ledger()
	docu.make_gl_entries()
	docu.repost_future_sle_and_gle()
	frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 0 WHERE `field` = "allow_negative_stock" """)

@frappe.whitelist()
def repost_stock():
	from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import debug_repost
	from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt
	from addons.custom_standard.custom_purchase_receipt import custom_get_gl_entries
	PurchaseReceipt.get_gl_entries = custom_get_gl_entries
	debug_repost()

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

@frappe.whitelist()
def patch_je():
	liste = invoice_list = frappe.db.sql("""
		SELECT gle.voucher_no, gle.voucher_type, gle.nilai_gle, sle.nilai_sle,gle.nilai_gle - sle.nilai_sle

		FROM
		(
		SELECT gle.voucher_no, gle.voucher_type,
		SUM(gle.`debit`-gle.credit) AS nilai_gle
		FROM `tabGL Entry` gle
		WHERE gle.account = "1142 - PERSEDIAAN BARANG JADI - G"
		AND gle.posting_date <= "2022-03-31"
		AND gle.posting_date >= "2022-03-01"
		AND gle.`is_cancelled` = 0
		GROUP BY gle.`voucher_no`
		) gle

		JOIN (
		SELECT sle.voucher_no, sle.voucher_type,
		SUM(sle.stock_value_difference) AS nilai_sle
		FROM `tabStock Ledger Entry` sle
		WHERE sle.posting_date <= "2022-03-31"
		AND sle.posting_date >= "2022-03-01"
		AND sle.is_cancelled = 0
		GROUP BY sle.`voucher_no`
		) sle

		ON gle.voucher_no = sle.voucher_no AND sle.voucher_type = gle.voucher_type
		HAVING ABS(gle.nilai_gle - sle.nilai_sle) > 1
	""")

	for row in liste:
		je_doc = frappe.get_doc(row[1],row[0])
		repair_gl_entry_tanpa_sl(row[1], row[0])
		print(row[0])

@frappe.whitelist()
def repair_gl_entry_tanpa_sl(doctype,docname):
	frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 1 WHERE `field` = "allow_negative_stock" """)
	docu = frappe.get_doc(doctype, docname)	
	delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(docname))
	docu.make_gl_entries()

	frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 0 WHERE `field` = "allow_negative_stock" """)

	

@frappe.whitelist()
def cek_supplier_short_code(self,method):
	if self.doctype == "Supplier":
		if self.supplier_short_code:
			if len(self.supplier_short_code) > 5:
				frappe.throw("Maximum Supplier Short Code is 5 Characters.")
def patch_item():
	item_list=frappe.db.sql("""select name from tabItem""",as_dict=1)
	count=1
	for row in item_list:
		item= frappe.get_doc("Item",row.name)
		item.add_default_uom_in_conversion_factor_table()
		item.save()
		frappe.db.commit()
		print(count)
		count=count+1
@frappe.whitelist()
def test_connection():

	print("https://erp-tju.gias.co.id/")
	clientroot = FrappeClient("https://erp-tju.gias.co.id/","administrator","22eAqNUhdrhXSSRxw6xCfm8gnjuCkFzmh5E")

@frappe.whitelist()
def test_ste_log():
	ste = frappe.get_doc("Stock Entry","MAT-STE-2022-00011")
	ste.submit()

@frappe.whitelist()
def custom_autoname_document_no_naming_series(doc,method):
	company_doc = frappe.get_doc("Company", doc.company)
	list_company_gias_doc = frappe.get_doc("List Company GIAS",company_doc.nama_cabang)
	singkatan = list_company_gias_doc.singkatan_cabang

	if doc.doctype == "GIAS Asset Movement":
		naming_series = "ASMV-GIAS-{{singkatan}}-1-.YY.-.MM.-.#####"
	elif doc.doctype == "Auto Repeat":
		naming_series = "ARP-GIAS-{{singkatan}}-.#####"
	elif doc.doctype == "Asset Value Adjustment":
		naming_series = "ASRV-GIAS-{{singkatan}}-1-.YY.-.MM.-.#####"
	elif doc.doctype == "BOM":
		naming_series = "BOM-{{singkatan}}-1-.YY.-.MM.-.#####"

	doc.name = make_autoname(naming_series.replace("{{singkatan}}",singkatan))

@frappe.whitelist()
def ubah_ke_huruf(angka):
	return num2words(angka, lang='id').title()

@frappe.whitelist()
def test_so():
	print(make_autoname("SO-1-22-10-.#####"))

@frappe.whitelist()
def custom_autoname_document_so(doc,method):
	# pass

	month = frappe.utils.formatdate(frappe.utils.getdate(doc.transaction_date),"MM")
	year = frappe.utils.formatdate(frappe.utils.getdate(doc.transaction_date),"YY")

	if doc.tax_or_non_tax == "Tax":
		tax = 1
	else:
		tax = 2
	doc.name = make_autoname("SO-{}-{}-{}-.#####".format(tax,year,month))

@frappe.whitelist()
def list_make_name():
	print(make_autoname("SQ-1-22-09-.#####"))

@frappe.whitelist()
def custom_autoname_document_lcv(doc,method):

	month = frappe.utils.formatdate(frappe.utils.getdate(doc.posting_date),"MM")
	year = frappe.utils.formatdate(frappe.utils.getdate(doc.posting_date),"YY")
	doc.name = make_autoname("SQ-1-{}-{}-.#####".format(year,month))


@frappe.whitelist()
def custom_autoname_document_je(doc,method):
	singkatan = "HO"
	company_doc = frappe.get_doc("Company", doc.company)
	list_company_gias_doc = frappe.get_doc("List Company GIAS",company_doc.nama_cabang)
	singkatan = list_company_gias_doc.singkatan_cabang

	month = frappe.utils.formatdate(frappe.utils.getdate(doc.posting_date),"MM")
	year = frappe.utils.formatdate(frappe.utils.getdate(doc.posting_date),"YY")

	# doc.name = make_autoname(doc.naming_series.replace("{{singkatan}}",singkatan))
	if doc.tax_or_non_tax == "Tax":
		tax = 1
	else:
		tax = 2
	if str(year) == "22" and tax == 1:
		doc.name = make_autoname(doc.naming_series.replace("-{tax}-","-").replace("-1-","-").replace("{{singkatan}}",singkatan).replace(".YY.",year).replace(".MM.",month))
	else:
		doc.name = make_autoname(doc.naming_series.replace("-{tax}-","-{}-".format(tax)).replace("{{singkatan}}",singkatan).replace(".YY.",year).replace(".MM.",month))


@frappe.whitelist()
def custom_autoname_document_asset(doc,method):
	company_doc = frappe.get_doc("Company", doc.company)
	list_company_gias_doc = frappe.get_doc("List Company GIAS",company_doc.nama_cabang)
	singkatan = list_company_gias_doc.singkatan_cabang

	if doc.asset_category == "KENDARAAN":
		doc.naming_series = "AST-VHCL-GIAS-{{singkatan}}-{{tax}}-.#####"
	elif doc.asset_category == "BANGUNAN":
		doc.naming_series = "AST-BLDG-GIAS-{{singkatan}}-{{tax}}-.#####"
	elif doc.asset_category == "INVENTARIS":
		doc.naming_series = "AST-INVT-GIAS-{{singkatan}}-{{tax}}-.#####"
	elif doc.asset_category == "MESIN & PERALATAN":
		doc.naming_series = "AST-TOOL-GIAS-{{singkatan}}-{{tax}}-.#####"
	elif doc.asset_category == "TANAH":
		doc.naming_series = "AST-LAND-GIAS-{{singkatan}}-{{tax}}-.#####"
	else:
		doc.naming_series = "AST-ASSET-GIAS-{{singkatan}}-{{tax}}-.#####"

	# doc.name = make_autoname(doc.naming_series.replace("{{singkatan}}",singkatan))
	if doc.tax_or_non_tax == "Tax":
		tax = 1
	else:
		tax = 2
	doc.name = make_autoname(doc.naming_series.replace("{{singkatan}}",singkatan)).replace("{{tax}}",tax)

@frappe.whitelist()
def custom_autoname_document_non_mr(doc,method):
	singkatan = ""

	if doc.cabang:
		singkatan = frappe.get_doc("List Company GIAS", doc.cabang).singkatan_cabang
	else:
		singkatan = "HO"
	prefix = ""
	if doc.doctype == "Memo Ekspedisi":
		prefix = "ME"
	elif doc.doctype == "Berita Acara Komplain":
		prefix = "BAK"

	doc.naming_series = """{}-HO-{}-.YYYY.-.MM.-.####""".format(prefix,singkatan)
	doc.name = make_autoname(doc.naming_series, doc=doc)

@frappe.whitelist()
def test_name():
	print(frappe.utils.formatdate(frappe.utils.getdate("2022-01-02"),"MM YY"))


@frappe.whitelist()
def custom_autoname_document_bak(doc,method):
	singkatan = ""
	
	if doc.nama_pengaju:
		singkatan = frappe.get_doc("List Company GIAS", doc.nama_pengaju).singkatan_cabang
	else:
		singkatan = "HO"
	prefix = ""
	if doc.doctype == "Memo Ekspedisi":
		prefix = "ME"
	elif doc.doctype == "Berita Acara Komplain":
		prefix = "BAK"

	month = frappe.utils.formatdate(frappe.utils.getdate(doc.date),"MM")
	year = frappe.utils.formatdate(frappe.utils.getdate(doc.date),"YY")

	doc.naming_series = """{}-HO-{}-{}-{}-.####""".format(prefix,singkatan,year,month)
	# doc.naming_series = """{}-HO-{}-.YYYY.-.MM.-.####""".format(prefix,singkatan)
	doc.name = make_autoname(doc.naming_series, doc=doc)


@frappe.whitelist()
def debug():
	ste = frappe.get_doc("Stock Entry","MAT-STE-2021-00096")
	ste.submit()

@frappe.whitelist()
def create_event_producer():
	event_producer = frappe.new_doc("Event Producer")
	event_producer.producer_url = "https://trial-erp.gias.co.id"
	event_producer.api_key = "b0f40fd89d4eacc"
	event_producer.api_secret = "39d551fcccc149b"
	event_producer.user = "trial_usp1@gias.co.id"
	list_baru = {
		"ref_doctype" : "Item",
		"use_same_name" : 1
	}
	event_producer.append("producer_doctypes", list_baru)
	event_producer.save()

@frappe.whitelist()
def check_koneksi():
	print("cek untuk konek https://dev-erp2.gias.co.id")
	res = requests.get("https://dev-erp2.gias.co.id",verify=False)
	print(str(res))

	print("cek untuk konek https://dev-branch-erp2.gias.co.id")
	res = requests.get("https://dev-branch-erp2.gias.co.id",verify=False)
	print(str(res))

	print("cek untuk konek https://trial-branch.gias.co.id/")
	res = requests.get("https://trial-branch.gias.co.id/",verify=False)
	print(str(res))

# Event Sync & Update Log Archive
@frappe.whitelist()
def add_event_sync_and_update_log_archive():
	berapabulan = 3 	
	frappe.db.sql(""" 
		INSERT INTO `tabEvent Sync Log Archive` (NAME, update_type, ref_doctype, docname, STATUS, event_producer, producer_doc, use_same_name, mapping, DATA, error)
		SELECT NAME, update_type, ref_doctype, docname, STATUS, event_producer, producer_doc, use_same_name, mapping, DATA, error
		FROM `tabEvent Sync Log`
		WHERE DATE(creation) BETWEEN DATE_SUB(NOW(), INTERVAL %s MONTH) AND NOW() """,(berapabulan))
	
	frappe.db.sql(""" 
		DELETE FROM `tabEvent Sync Log`
		WHERE DATE(creation) BETWEEN DATE_SUB(NOW(), INTERVAL %s MONTH) AND NOW() """,(berapabulan))
	
	frappe.db.sql(""" 
		INSERT INTO `tabEvent Update Log Archive` (NAME, update_type, ref_doctype, docname, data)
		SELECT NAME, update_type, ref_doctype, docname, STATUS, DATA
		FROM `tabEvent Update Log`
		WHERE DATE(creation) BETWEEN DATE_SUB(NOW(), INTERVAL %s MONTH) AND NOW() """,(berapabulan))
	
	frappe.db.sql(""" 
		DELETE FROM `tabEvent Update Log`
		WHERE DATE(creation) BETWEEN DATE_SUB(NOW(), INTERVAL %s MONTH) AND NOW() """,(berapabulan))
# End Event Sync & Update Log Archive