# Copyright (c) 2022, das and contributors
# For license information, please see license.txt

# import frappe


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
	currency = "IDR"

	columns = [
	{
		"label": _("Posting Date"),
		"fieldname": "posting_date",
		"fieldtype": "Date",
		"width": 90
	},
	{
		"label": _("Account"),
		"fieldname": "account",
		"fieldtype": "Link",
		"options": "Account",
		"width": 280
	},
	{
		"label": _("Debit ({0})").format(currency),
		"fieldname": "debit",
		"fieldtype": "Float",
		"width": 100
	},
	{
		"label": _("Credit ({0})").format(currency),
		"fieldname": "credit",
		"fieldtype": "Float",
		"width": 100
	},
	{
		"label": _("Party Type"),
		"fieldname": "party_type",
		"width": 100
	},
	{
		"label": _("Party"),
		"fieldname": "party",
		"width": 100
	},
	{
		"label": _("Remarks"),
		"fieldname": "remarks",
		"width": 400
	},
	{
		"label": _("Doc Remarks"),
		"fieldname": "doc_remarks",
		"width": 400
	},
	{
		"label": _("Voucher Type"),
		"fieldname": "voucher_type",
		"width":150
	},
	{
		"label": _("No Voucher"),
		"fieldname": "no_voucher",
		"fieldtype": "Dynamic Link",
		"options": "voucher_type",
		"width":150
	},
	{
		"label": _("Item Code"),
		"fieldname": "item_code",
		"width": 100
	},
	{
		"label": _("Item Name"),
		"fieldname": "item_name",
		"width": 100
	},
	{
		"label": _("Branch"),
		"fieldname": "branch",
		"width": 100
	},
	{
		"label": _("Cost Center"),
		"fieldname": "cost_center",
		"width": 100
	},
	{
		"label": _("Tax Or Non Tax"),
		"fieldname": "tax_or_non_tax",
		"width": 100
	},
	]
	
	query_filter = ""
	if filters.get("nama_account"):
		query_filter = """ AND account = "{}" """.format(filters.get("nama_account"))

	if 1==1:
		# list_query = frappe.db.sql(""" 

		# 	SELECT
		# 	 posting_date,
		# 	 account,
		# 	 debit,
		# 	 credit,
		# 	 party_type,
		# 	 party,
		# 	 TRIM(SUBSTRING_INDEX(remarks, 'Note:', 1)),
		# 	 voucher_type,
		# 	 voucher_no,
		# 	 TRIM(SUBSTRING_INDEX(remarks, 'Note:', -1)),
		# 	 branch,
		# 	 cost_center,
		# 	 name

		# 	FROM `tabGL Entry` 
		# 	WHERE 
		# 	 posting_date >= "{0}" and posting_date <= "{1}"
		# 	and is_cancelled = 0
		# 	and voucher_type IN ("Purchase Receipt","Payment Entry","Employee Advance","Journal Entry","Stock Reconciliation","Delivery Note")
		# 	and docstatus = 1
		# 	{2}
		# 	GROUP BY account, voucher_no
          
        #   	UNION

		# 	SELECT
		# 	posting_date,
		# 	account,
		# 	debit,
		# 	credit,
		# 	party_type,
		# 	party,
		# 	REPLACE(remarks,"None",""),
		# 	voucher_type,
		# 	no_voucher,
		# 	doc_remarks,
		# 	branch,
		# 	cost_center,
		# 	name

		# 	FROM `tabGL Entry Custom` 
		# 	WHERE 
		# 	posting_date >= "{0}" AND posting_date <= "{1}"
		# 	AND voucher_type IN ("Purchase Invoice","Expense Claim", "Sales Invoice","Stock Entry")
		# 	{2}

		# 	ORDER BY TIMESTAMP(posting_date)

		# 	""".format(filters.get("from_date"),filters.get("to_date"), query_filter))

		list_query = frappe.db.sql(""" 

			SELECT
			posting_date,
			account,
			debit,
			credit,
			party_type,
			party,
			REPLACE(remarks,"None",""),
			voucher_type,
			no_voucher,
			doc_remarks,
			branch,
			cost_center,
			name

			FROM `tabGL Entry Custom` 
			WHERE 
			posting_date >= "{0}" AND posting_date <= "{1}"
			AND voucher_type IN ("Purchase Invoice","Payment Entry","Expense Claim","Journal Entry","Purchase Receipt","Delivery Note","Sales Invoice","Stock Entry")
			{2}

			ORDER BY TIMESTAMP(posting_date)

			""".format(filters.get("from_date"),filters.get("to_date"), query_filter))

		list_transaction = []

		for baris_query in list_query:
			
			custom_item_code = frappe.get_doc("GL Entry Custom",baris_query[12])
			sle = {}
			sle.update({
				"posting_date": baris_query[0],
				"account": baris_query[1],
				"debit": baris_query[2],
				"credit": baris_query[3],
				"party_type": baris_query[4],
				"party": baris_query[5],
				"remarks": baris_query[6],
				"doc_remarks": baris_query[9],
				"voucher_type":baris_query[7],
				"no_voucher":baris_query[8],
				"branch": baris_query[10],
				"cost_center": baris_query[11],
				"item_code": custom_item_code.get("item_code"),
				"item_name": custom_item_code.get("item_name"),
				"tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
			})	
			data.append(sle)

			# elif baris_query[7] == "Purchase Receipt":
			# 	self = frappe.get_doc("Purchase Receipt", baris_query[8])
				
			# 	pakai_di_item = 0
			# 	for baris in self.items:
			# 		if baris.warehouse:
			# 			if frappe.get_doc("Warehouse",baris.warehouse).account == baris_query[1]:
			# 				pakai_di_item = 1

			# 	if pakai_di_item == 1:
			# 		if baris_query[8] not in list_transaction:
			# 			list_transaction.append(baris_query[8])
			# 			grand_total = self.rounded_total if (self.rounding_adjustment and self.rounded_total) else self.grand_total
			# 			base_grand_total = flt(self.base_rounded_total if (self.base_rounding_adjustment and self.base_rounded_total)
			# 				else self.base_grand_total, self.precision("base_grand_total"))	

			# 			list_account = []
			# 			for item in self.get("items"):

			# 				if item.warehouse:
			# 					if frappe.get_doc("Warehouse", item.warehouse).account not in list_account:
			# 						if filters.get("nama_account"):
			# 							if filters.get("nama_account") == frappe.get_doc("Warehouse", item.warehouse).account:
			# 								list_account.append(frappe.get_doc("Warehouse", item.warehouse).account)
			# 						else:
			# 							list_account.append(frappe.get_doc("Warehouse", item.warehouse).account)

			# 				sle = {}

			# 				expense_account = frappe.get_doc("Warehouse", item.warehouse).account

			# 				if filters.get("nama_account"):

			# 					if filters.get("nama_account") == expense_account:

			# 						sle.update({
			# 							"posting_date": self.posting_date,
			# 							"account": expense_account,
			# 							"debit": flt(item.base_net_amount + item.item_tax_amount, item.precision("base_net_amount")),
			# 							"credit": 0 ,
			# 							"remarks": "Item Warehouse Account",
			# 							"voucher_type":"Purchase Receipt",
			# 							"no_voucher": self.name,
			# 							"item_code" : item.item_code,
			# 							"item_name": item.item_name,
			# 							"branch": item.branch,
			# 							"cost_center": item.cost_center,
			# 							"tax_or_non_tax": self.tax_or_non_tax
			# 						})	
			# 						data.append(sle)
			# 				else:
			# 					sle.update({
			# 						"posting_date": self.posting_date,
			# 						"account": expense_account,
			# 						"debit": flt(item.base_net_amount + item.item_tax_amount, item.precision("base_net_amount")),
			# 						"credit": 0 ,
			# 						"remarks": "Item Warehouse Account",
			# 						"voucher_type":"Purchase Receipt",
			# 						"no_voucher": self.name,
			# 						"item_code" : item.item_code,
			# 						"item_name": item.item_name,
			# 						"branch": item.branch,
			# 						"cost_center": item.cost_center,
			# 						"tax_or_non_tax": self.tax_or_non_tax
			# 					})	
			# 					data.append(sle)
			# 	else:
			# 		sle = {}
			# 		sle.update({
			# 			"posting_date": baris_query[0],
			# 			"account": baris_query[1],
			# 			"debit": baris_query[2],
			# 			"credit": baris_query[3],
			# 			"party_type": baris_query[4],
			# 			"party": baris_query[5],
			# 			"remarks": baris_query[6],
			# 			"doc_remarks": baris_query[9],
			# 			"voucher_type":baris_query[7],
			# 			"no_voucher":baris_query[8],
			# 			"branch": baris_query[10],
			# 			"cost_center": baris_query[11],
			# 			"tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
			# 		})	
			# 		data.append(sle)

			# elif baris_query[7] == "Delivery Note":
			# 	self = frappe.get_doc("Delivery Note", baris_query[8])
				
			# 	pakai_di_item = 0
			# 	for baris in self.items:
			# 		if baris.warehouse:
			# 			if frappe.get_doc("Warehouse",baris.warehouse).account == baris_query[1]:
			# 				pakai_di_item = 1

			# 	if pakai_di_item == 1:
			# 		if baris_query[8] not in list_transaction:
			# 			list_transaction.append(baris_query[8])
			# 			grand_total = self.rounded_total if (self.rounding_adjustment and self.rounded_total) else self.grand_total
			# 			base_grand_total = flt(self.base_rounded_total if (self.base_rounding_adjustment and self.base_rounded_total)
			# 				else self.base_grand_total, self.precision("base_grand_total"))	

			# 			list_account = []
			# 			for item in self.get("items"):
			# 				doc_item = frappe.get_doc("Item", item.item_code)
			# 				if doc_item.is_stock_item:
			# 					if item.warehouse:
			# 						if frappe.get_doc("Warehouse", item.warehouse).account not in list_account:
			# 							if filters.get("nama_account"):
			# 								if filters.get("nama_account") == frappe.get_doc("Warehouse", item.warehouse).account:
			# 									list_account.append(frappe.get_doc("Warehouse", item.warehouse).account)
			# 							else:
			# 								list_account.append(frappe.get_doc("Warehouse", item.warehouse).account)

			# 					sle = {}

			# 					expense_account = frappe.get_doc("Warehouse", item.warehouse).account

			# 					if filters.get("nama_account"):

			# 						if filters.get("nama_account") == expense_account:

			# 							sle.update({
			# 								"posting_date": self.posting_date,
			# 								"account": expense_account,
			# 								"credit": flt(item.base_net_amount, item.precision("base_net_amount")),
			# 								"debit": 0 ,
			# 								"remarks": "Item Warehouse Account",
			# 								"voucher_type":"Delivery Note",
			# 								"no_voucher": self.name,
			# 								"item_code" : item.item_code,
			# 								"item_name": item.item_name,
			# 								"branch": item.branch,
			# 								"cost_center": item.cost_center,
			# 								"tax_or_non_tax": self.tax_or_non_tax
			# 							})	
			# 							data.append(sle)
			# 					else:
			# 						sle.update({
			# 							"posting_date": self.posting_date,
			# 							"account": expense_account,
			# 							"credit": flt(item.base_net_amount, item.precision("base_net_amount")),
			# 							"debit": 0 ,
			# 							"remarks": "Item Warehouse Account",
			# 							"voucher_type":"Delivery Note",
			# 							"no_voucher": self.name,
			# 							"item_code" : item.item_code,
			# 							"item_name": item.item_name,
			# 							"branch": item.branch,
			# 							"cost_center": item.cost_center,
			# 							"tax_or_non_tax": self.tax_or_non_tax
			# 						})	
			# 						data.append(sle)
			# 	else:
			# 		sle = {}
			# 		sle.update({
			# 			"posting_date": baris_query[0],
			# 			"account": baris_query[1],
			# 			"debit": baris_query[2],
			# 			"credit": baris_query[3],
			# 			"party_type": baris_query[4],
			# 			"party": baris_query[5],
			# 			"remarks": baris_query[6],
			# 			"doc_remarks": baris_query[9],
			# 			"voucher_type":baris_query[7],
			# 			"no_voucher":baris_query[8],
			# 			"branch": baris_query[10],
			# 			"cost_center": baris_query[11],
			# 			"tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
			# 		})	
			# 		data.append(sle)

			# else:
			# 	if baris_query[7] == "Journal Entry":
					
			# 		je_doc = frappe.get_doc("Journal Entry", baris_query[8])
			# 		# if baris_query[8] not in list_transaction:
			# 		# 	list_transaction.append(baris_query[8])

			# 		for baris_acc in je_doc.accounts:
			# 			if baris_acc.account == baris_query[1]:
			# 				sle = {}
			# 				# frappe.throw("{}-{}".format(baris_acc.account, str(baris_acc.debit)))
			# 				sle.update({
			# 					"posting_date": baris_query[0],
			# 					"account": baris_query[1],
			# 					"debit": baris_acc.debit,
			# 					"credit": baris_acc.credit,
			# 					"party_type": baris_query[4],
			# 					"party": baris_query[5],
			# 					"remarks": baris_acc.user_remark,
			# 					"doc_remarks": baris_query[9],
			# 					"voucher_type":baris_query[7],
			# 					"no_voucher":baris_query[8],
			# 					"branch": baris_query[10],
			# 					"cost_center": baris_query[11],
			# 					"tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
			# 				})	
			# 				data.append(sle)
			# 	elif baris_query[7] == "Expense Claim":
			# 		self = frappe.get_doc("Expense Claim", baris_query[8])
			# 		if frappe.utils.flt(baris_query[2]) > 0:
			# 			nyari = 0
			# 			for row_expense in self.expenses:
			# 				exp_typ = frappe.get_doc("Expense Claim Type",row_expense.expense_type)
			# 				account = exp_typ.accounts[0].default_account
			# 				if account == baris_query[1]:
			# 					nyari = 1
			# 					sle = {}
			# 					sle.update({
			# 						"posting_date": baris_query[0],
			# 						"account": baris_query[1],
			# 						"debit": row_expense.sanctioned_amount,
			# 						"credit": baris_query[3],
			# 						"party_type": baris_query[4],
			# 						"party": baris_query[5],
			# 						"remarks": row_expense.description,
			# 						"doc_remarks": baris_query[9],
			# 						"voucher_type":baris_query[7],
			# 						"no_voucher":baris_query[8],
			# 						"branch": baris_query[10],
			# 						"cost_center": baris_query[11],
			# 						"tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
			# 					})	
			# 					data.append(sle)

			# 			if nyari == 0:
			# 				sle = {}
			# 				sle.update({
			# 					"posting_date": baris_query[0],
			# 					"account": baris_query[1],
			# 					"debit": baris_query[2],
			# 					"credit": baris_query[3],
			# 					"party_type": baris_query[4],
			# 					"party": baris_query[5],
			# 					"remarks": baris_query[6],
			# 					"doc_remarks": baris_query[9],
			# 					"voucher_type":baris_query[7],
			# 					"no_voucher":baris_query[8],
			# 					"branch": baris_query[10],
			# 					"cost_center": baris_query[11],
			# 					"tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
			# 				})	
			# 				data.append(sle)
			# 		else:
			# 			sle = {}
			# 			sle.update({
			# 				"posting_date": baris_query[0],
			# 				"account": baris_query[1],
			# 				"debit": baris_query[2],
			# 				"credit": baris_query[3],
			# 				"party_type": baris_query[4],
			# 				"party": baris_query[5],
			# 				"remarks": baris_query[6],
			# 				"doc_remarks": baris_query[9],
			# 				"voucher_type":baris_query[7],
			# 				"no_voucher":baris_query[8],
			# 				"branch": baris_query[10],
			# 				"cost_center": baris_query[11],
			# 				"tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
			# 			})	
			# 			data.append(sle)
			# 	else:
			# 		sle = {}
			# 		sle.update({
			# 			"posting_date": baris_query[0],
			# 			"account": baris_query[1],
			# 			"debit": baris_query[2],
			# 			"credit": baris_query[3],
			# 			"party_type": baris_query[4],
			# 			"party": baris_query[5],
			# 			"remarks": baris_query[6],
			# 			"doc_remarks": "",
			# 			"voucher_type":baris_query[7],
			# 			"no_voucher":baris_query[8],
			# 			"branch": baris_query[10],
			# 			"cost_center": baris_query[11],
			# 			"tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
			# 		})	
			# 		data.append(sle)


		
	return columns, data

# searches for active employees
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def query_doctype(doctype, txt, searchfield, start, page_len, filters):
	conditions = []
	fields = get_fields("DocType", ["name"])

	return frappe.db.sql("""select {fields} from `tabDocType`
		where 
			({key} like %(txt)s
				or name like %(txt)s)
			AND name IN ("Purchase Invoice","Payment Entry","Employee Advance","Expense Claim","Journal Entry",
			"Purchase Receipt","Delivery Note","Sales Invoice","Stock Entry","Stock Reconciliation")
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
