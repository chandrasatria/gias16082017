# Copyright (c) 2022, das and contributors
# For license information, please see license.txt


import json
from collections import defaultdict

import frappe
from frappe import scrub
from frappe.desk.reportview import get_filters_cond, get_match_cond
from frappe.utils import nowdate, unique
from frappe.utils import cint, flt
from frappe import _, _dict
import erpnext
from erpnext.stock.get_item_details import _get_item_tax_template

def execute(filters=None):
	columns, data = [], []
	columns = [
	{
		"label": _("Kode Barang"),
		"fieldname": "item_code",
		"fieldtype": "Link",
		"options": "Item",
		"width": 180
	},
	{
		"label": _("Nama Barang"),
		"fieldname": "item_name",
		"fieldtype": "Data",
		"width": 380
	},
	{
		"label": _("Actual Stock"),
		"fieldname": "actual_stock",
		"fieldtype": "Float",
		"width": 110
	},
	{
		"label": _("DN Draft Qty"),
		"fieldname": "dn_draft_qty",
		"fieldtype": "Float",
		"width": 110
	},
	{
		"label": _("Go To DN"),
		"fieldname": "go_to_dn",
		"fieldtype": "Button",
		"width": 100
	},
	{
		"label": _("STE Draft Qty"),
		"fieldname": "ste_draft_qty",
		"fieldtype": "Float",
		"width": 110
	},
	{
		"label": _("Go To STE"),
		"fieldname": "go_to_ste",
		"fieldtype": "Button",
		"width": 100
	},
	{
		"label": _("Available Stock"),
		"fieldname": "available_stock",
		"fieldtype": "Float",
		"width": 110
	},
	{
		"label": _("Satuan"),
		"fieldname": "satuan",
		"fieldtype": "Link",
		"options": "UOM",
		"width": 60
	},
	{
		"label": _("Product Specialist"),
		"fieldname": "product_specialist",
		"fieldtype": "Data",
		"width": 110
	},
	{
		"label": _("Item Group"),
		"fieldname": "item_group",
		"fieldtype": "Link",
		"options": "Item Group",
		"width": 110
	},
	{
		"label": _("Warehouse"),
		"fieldname": "warehouse",
		"fieldtype": "Link",
		"options": "Warehouse",
		"width": 190
	}
	]
	query_wh_filter = ""
	query_item_group = ""
	if filters.get("warehouse"):
		query_wh_filter = """ AND tb.warehouse = "{}" """.format(filters.get("warehouse"))

	if filters.get("item_group_parent") and filters.get("item_group_child"):
		query_item_group = """ AND ti.item_group = "{}" """.format(filters.get("item_group_child"))
	elif filters.get("item_group_parent") and not filters.get("item_group_child"):
		item_group_parent = frappe.get_doc("Item Group", filters.get("item_group_parent"))
		query_item_group = """ and tig.rgt <= "{}" and tig.lft >= "{}" """.format(item_group_parent.rgt, item_group_parent.lft)
	elif filters.get("item_group_child"):
		query_item_group = """ AND ti.item_group = "{}" """.format(filters.get("item_group_child"))


	list_stock = frappe.db.sql(""" 

		SELECT
		tb.item_code,ti.item_name,tb.actual_qty, tb.warehouse,
		IFNULL(a.ste_booking,0) AS ste_booking,
		IFNULL(b.dn_booking,0) AS dn_booking,
		ti.stock_uom,
		ti.ps_approver,
		ti.item_group
		FROM `tabBin` tb 

		LEFT JOIN
		(
		SELECT
		tb.item_code,ti.item_name,tb.actual_qty, tb.warehouse,
		SUM(IF(tst.`workflow_state`="Rejected",0,IFNULL(std.qty,0))) AS ste_booking,
		ti.stock_uom,
		ti.ps_approver,
		ti.item_group
		FROM `tabBin` tb
		JOIN `tabItem` ti ON ti.`item_code` = tb.`item_code`
		JOIn `tabItem Group` tig on tig.name = ti.item_group
		LEFT JOIN `tabStock Entry Detail` `std` 
		ON std.`item_code` = tb.`item_code` AND std.`s_warehouse` = tb.warehouse AND `std`.`docstatus` = 0
		LEFT JOIN `tabStock Entry` tst
		ON tst.name = std.parent 
		 
		WHERE
		tb.item_code IS NOT NULL
		{}
		{}

		GROUP BY tb.`item_code`, tb.`warehouse`
		ORDER BY tb.item_code,tb.warehouse) a ON a.item_code = tb.`item_code` AND a.warehouse = tb.`warehouse`

		LEFT JOIN
		(
		SELECT
		tb.item_code,ti.item_name,tb.actual_qty, tb.warehouse,
		SUM(IF(tdn.`workflow_state`="Rejected",0,IFNULL(dni.qty,0))) AS dn_booking,
		ti.stock_uom,
		ti.ps_approver,
		ti.item_group
		FROM `tabBin` tb
		JOIN `tabItem` ti ON ti.`item_code` = tb.`item_code`
		JOIn `tabItem Group` tig on tig.name = ti.item_group
		LEFT JOIN `tabDelivery Note Item` `dni`
		ON dni.`item_code` = tb.`item_code` AND dni.`warehouse` = tb.`warehouse` AND dni.`docstatus` = 0
		LEFT JOIN `tabDelivery Note` tdn
		ON tdn.name = dni.parent 
		 
		WHERE
		tb.item_code IS NOT NULL
		{}
		{}

		GROUP BY tb.`item_code`, tb.`warehouse`
		ORDER BY tb.item_code,tb.warehouse) b ON b.item_code = tb.`item_code` AND b.warehouse = tb.`warehouse`

		JOIN `tabItem` ti ON ti.`item_code` = tb.`item_code`
		{}

		""".format(query_wh_filter,query_item_group,query_wh_filter,query_item_group,query_wh_filter), as_dict= 1)

	

	for row in list_stock:
		dn_draft = 0 
		ste_draft = 0
		dn_draft = row.dn_booking
		ste_draft = row.ste_booking


		data.append([
			row.item_code, 
			row.item_name, 
			row.actual_qty, 
			dn_draft,
			"""<button type="button" onclick=" window.open('{}/app/delivery-note/view/list?docstatus=0&item_code={}&rejected=No&warehouse={}','_blank')" >{}</button>""".format(frappe.utils.get_url(),row.item_code,row.warehouse,"Go To DN"), 
			ste_draft,
			"""<button type="button" onclick=" window.open('{}/app/stock-entry/view/list?docstatus=0&item_code={}&rejected=No&s_warehouse={}','_blank')" >{}</button>""".format(frappe.utils.get_url(),row.item_code,row.warehouse,"Go To STE"), 
			row.actual_qty-dn_draft-ste_draft,
			row.stock_uom,
			row.ps_approver,
			row.item_group,
			row.warehouse
		])

	return columns, data
