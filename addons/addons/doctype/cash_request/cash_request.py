# Copyright (c) 2021, das and contributors
# For license information, please see license.txt

from erpnext.setup.utils import get_exchange_rate
import frappe,erpnext
from frappe.utils import flt
import math
from frappe.model.document import Document

class CashRequest(Document):
	def validate(self):
		#get list invoice
		cek_supplier = self.supplier
		for row in self.list_invoice:
			if row.desc != cek_supplier:
				frappe.throw("Supplier {} is used in this Cash Request, please check row {}".format(self.supplier, row.idx))


		invoice=""
		for row in self.list_invoice:
			pinv = frappe.get_doc("Purchase Invoice", row.document)
			if pinv.docstatus != 1:
				frappe.throw("Purchase Invoice {} is not submitted, cannot be used in Cash Request".format(row.document))
			if invoice=="":
				invoice=""" "{}" """.format(row.document)
			else:
				invoice="""{},"{}" """.format(invoice,row.document)
		matrix={}
		data = frappe.db.sql("""select crt.document,sum(crt.amount) 
			from `tabCash Request Table` crt
			JOIN `tabCash Request` tcr ON tcr.name = crt.parent
			where crt.document IN ({}) 
			and tcr.workflow_state not in ("Rejected","Cancelled")
			 and crt.docstatus!=2 and crt.parent != "{}" 
			 group by crt.document """.format(invoice,self.name),as_list=1)
		for row in data:
			matrix[row[0]]=row[1]
		for row in self.list_invoice:
			document_asli = frappe.get_doc(self.type, row.document)
			additional=0
			if row.document in matrix:
				additional=matrix[row.document]
			if frappe.utils.flt(row.amount + additional,5) > document_asli.rounded_total and frappe.utils.flt(row.amount + additional,5) - document_asli.rounded_total > 0.1:
				frappe.throw("Amount inputted cannot be higher than original Grand Total for {}.".format(document_asli.name))
			if frappe.utils.flt(row.amount,5) > document_asli.outstanding_amount:
				frappe.throw("Amount inputted cannot be higher than original Outstanding Total for {}.".format(document_asli.name))
		total = 0
		for row in self.list_invoice:
			total += row.amount

		for row in self.list_tax_and_charges:
			total += row.amount

		self.grand_total = total


@frappe.whitelist()
def get_sisa_invoice(pinv):
	pinv_doc = frappe.get_doc("Purchase Invoice", pinv)
	outstanding = frappe.db.sql("""
		select IFNULL(crt.amount,0) 
		from `tabCash Request Table` crt 
		JOIN `tabCash Request` tcr ON tcr.name = crt.parent
		where crt.document="{}" and crt.docstatus=1 
		and tcr.workflow_state not in ("Rejected","Cancelled")
		""".format(pinv))
	total_get=0
	for x in outstanding:
		total_get+=flt(x[0])

	total_out = flt(pinv_doc.grand_total+pinv_doc.rounding_adjustment,3)-total_get
	if  total_out <= 0:
		frappe.throw("Invoice Telah Sepenuhnya di buat Cash Request")
	return [total_out,pinv_doc.grand_total]


@frappe.whitelist()
def get_default_cash_bank():
	account = ""
	cb_account = frappe.db.sql(""" SELECT value FROM `tabSingles` WHERE field = "default_cash_or_bank_account" LIMIT 1 """)
	if len(cb_account) > 0:
		account = cb_account[0][0]

	return account

@frappe.whitelist()
def get_supplier_currency(supplier, posting_date):

	exchange_rate = 1
	currency = "IDR"
	if supplier and posting_date:
		sup_doc = frappe.get_doc("Supplier", supplier)
		if sup_doc.default_currency:
			if sup_doc.default_currency != "IDR":
				currency = sup_doc.default_currency
				exchange_rate = get_exchange_rate(sup_doc.default_currency,"IDR",transaction_date = posting_date)


	return exchange_rate, currency

@frappe.whitelist()
def get_tax_charges_for_cash_request(tax_and_charges_template):
	get_tax_charges = frappe.db.sql(""" 
		SELECT 
		ptc.account_head, ptc.rate, tac.account_currency
		FROM `tabPurchase Taxes and Charges` ptc
		JOIN `tabAccount` tac ON ptc.account_head = tac.name
		WHERE ptc.parent = "{}" """.format(tax_and_charges_template),as_dict=1)

	return get_tax_charges

@frappe.whitelist()
def check_pinv_has_retur(pinv):
	get_retur = frappe.db.sql(""" SELECT * 
		FROM `tabPurchase Invoice`
		WHERE return_against = "{}" and docstatus = 1 """.format(pinv),as_dict=1)

	if len(get_retur) > 0:
		return "Yes"
	else:
		return "No"

@frappe.whitelist()
def check_pinv_is_approved(pinv):
	get_retur = frappe.db.sql(""" SELECT * 
		FROM `tabPurchase Invoice`
		WHERE workflow_state = "Approved" and name = "{}" and docstatus = 1 """.format(pinv),as_dict=1)

	if len(get_retur) > 0:
		return "Yes"
	else:
		return "No"


@frappe.whitelist()
def get_taxes_and_charges(pinv):
	get_pajak = frappe.db.sql(""" SELECT total_taxes_and_charges
		FROM `tabPurchase Invoice`
		WHERE name = "{}" and docstatus = 1 """.format(pinv),as_dict=1)

	return get_pajak

@frappe.whitelist()
def go_to_rejected(cash_request):
	doc = frappe.get_doc("Cash Request", cash_request)
	doc.workflow_state = "Rejected"
	doc.db_update()
	frappe.msgprint("Document has been rejected. Please refresh to see changes.")

@frappe.whitelist()
def make_journal_entry(cash_request,supplier,tax_or_non_tax):
	target_doc = frappe.new_doc("Journal Entry")
	target_doc.sumber_cash_request = cash_request
	target_doc.supplier_cash_request = supplier
	target_doc.tax_or_non_tax = tax_or_non_tax

	sumber_doc = frappe.get_doc("Cash Request", cash_request)

	if not sumber_doc.list_invoice:
		frappe.throw("List Invoice is mandatory for creating Journal Entry")

	if not sumber_doc.supplier:
		frappe.throw("Supplier is mandatory for creating Journal Entry")
		
	sumber_query = frappe.db.sql(""" 
		SELECT
		IF(pin.is_return = 0,tct.`document`,pin.return_against) AS document,
		tgl.account, 
		tct.amount AS difference,
		pin.supplier,
		tcr.currency, 
		pin.conversion_rate as exchange_rate,
		tgl.party,
		tgl.party_type,
		tcr.currency_exchange,
		tct.user_remarks as remarks,
		tct.branch,
		tct.cost_center

		FROM `tabCash Request` tcr
		JOIN `tabCash Request Table` tct ON tct.parent = tcr.name
		JOIN `tab{}` pin ON pin.name = tct.`document`
		JOIN `tabGL Entry` tgl ON tgl.`voucher_no` = pin.name 
		AND pin.`credit_to` = tgl.`account`
		WHERE tcr.name = "{}"

		UNION
		SELECT
		"",
		tct.account, 
		tct.amount AS difference,
		"",
		tcr.currency, 
		tcr.currency_exchange as exchange_rate,
		"",
		"",
		tcr.currency_exchange,
		"",
		tct.branch,
		tct.cost_center

		FROM `tabCash Request` tcr
		JOIN `tabCash Request Taxes and Charges` tct ON tct.parent = tcr.name
		WHERE tcr.name = "{}"


		""".format(sumber_doc.type,cash_request,cash_request), as_dict=1)

	total_debit = 0
	total_credit = 0
	#check kalo inv sudah 0 outstandignnya maka prompt error
	total_tagihan=0
	for row in sumber_query:
		if row.document and row.document!="" and row.supplier!="" and row.difference>0:
			total_tagihan+=1
	if total_tagihan==0:
		frappe.throw("Semua Tagihan Pada Cash Request ini  Sudah Lunas")
	# frappe.msgprint(str(sumber_query))
	for row in sumber_query:
		change_rate = row.exchange_rate
		cbr_rate = row.currency_exchange
		if row.difference > 0:
			if row.document:
				sumber_invoice = frappe.get_doc(sumber_doc.type, row.document)				
				apakah_exchange_rate_baru = frappe.db.sql(""" 
					SELECT erra.`new_exchange_rate`
					FROM `tabExchange Rate Revaluation Account` erra
					JOIN `tabExchange Rate Revaluation` err
					ON err.name = erra.parent
					WHERE 
					erra.`account` = "{}"
					AND
		
			err.`posting_date` <= "{}"
					AND
					err.`posting_date` >= "{}"
					AND
					err.docstatus = 1 
					ORDER BY err.`posting_date` DESC
					LIMIT 1 """.format(row.account, frappe.utils.nowdate(), sumber_invoice.posting_date))


				if len(apakah_exchange_rate_baru) > 0:
					change_rate = apakah_exchange_rate_baru[0][0]
				
				account_doc = frappe.get_doc("Account", row.account)
				if account_doc.account_currency == "IDR":
					baris_baru = {
						"account": row.account,
						"party_type": row.party_type,
						"party" : row.party,
						"exchange_rate": 1,
						"account_currency" : frappe.get_doc("Account",row.account).account_currency,
						"branch" : row.branch,
						"user_remark" : row.remarks,
						"cost_center" : row.cost_center,
						"debit_in_account_currency": flt(row.difference * row.exchange_rate,2),
						"debit": flt(row.difference * row.exchange_rate,2),
						"sumber_cash_request" : cash_request,
						"supplier_cash_request": row.supplier,
						"reference_type" : sumber_doc.type,
						"reference_name" : row.document
					}
				else:
					baris_baru = {
						"account": row.account,
						"party_type": row.party_type,
						"party" : row.party,
						"exchange_rate": row.exchange_rate,
						"account_currency" : row.currency,
						"branch" : row.branch,
						"user_remark" : row.remarks,
						"cost_center" : row.cost_center,
						"debit_in_account_currency": flt(row.difference,2),
						"debit": flt(row.difference * row.exchange_rate,2),
						"sumber_cash_request" : cash_request,
						"supplier_cash_request": row.supplier,
						"reference_type" : sumber_doc.type,
						"reference_name" : row.document
					}
				total_debit += flt(row.difference * cbr_rate,2)
			else:
				if frappe.get_doc("Account",row.account).account_currency == "IDR" and sumber_doc.currency == "IDR":
					baris_baru = {
						"account": row.account,
						"party_type": row.party_type,
						"party" : row.party,
						"exchange_rate": 1,
						"account_currency" : frappe.get_doc("Account",row.account).account_currency,
						"branch" : row.branch,
						"user_remark" : row.remarks,
						"cost_center" : row.cost_center,
						"debit_in_account_currency": row.difference ,
						"debit": row.difference ,
						"sumber_cash_request" :cash_request,
						"supplier_cash_request": row.supplier
					}
					total_debit += row.difference 
				else:
					if frappe.get_doc("Account",row.account).account_currency != "IDR":
						baris_baru = {
							"account": row.account,
							"party_type": row.party_type,
							"party" : row.party,
							"exchange_rate": row.exchange_rate,
							"account_currency" : frappe.get_doc("Account",row.account).account_currency,
							"branch" : row.branch,
							"user_remark" : row.remarks,
							"cost_center" : row.cost_center,
							"debit_in_account_currency": row.difference ,
							"debit": row.difference * row.exchange_rate,
							"sumber_cash_request" :cash_request,
							"supplier_cash_request": row.supplier
						}
						total_debit += row.difference * row.exchange_rate
					else:
						baris_baru = {
							"account": row.account,
							"party_type": row.party_type,
							"party" : row.party,
							"exchange_rate": row.exchange_rate,
							"account_currency" : frappe.get_doc("Account",row.account).account_currency,
							"branch" : row.branch,
							"user_remark" : row.remarks,
							"cost_center" : row.cost_center,
							"debit_in_account_currency": row.difference * row.exchange_rate ,
							"debit": row.difference * row.exchange_rate,
							"sumber_cash_request" :cash_request,
							"supplier_cash_request": row.supplier
						}
						total_debit += row.difference * row.exchange_rate
		else:
			if row.document:
				sumber_invoice = frappe.get_doc(sumber_doc.type, row.document)

				apakah_exchange_rate_baru = frappe.db.sql(""" 
					SELECT erra.`new_exchange_rate`
					FROM `tabExchange Rate Revaluation Account` erra
					JOIN `tabExchange Rate Revaluation` err
					ON err.name = erra.parent
					WHERE 
					erra.`account` = "{}"
					AND
					err.`posting_date` <= "{}"
					AND
					err.`posting_date` >= "{}"
					AND
					err.docstatus = 1 
					ORDER BY err.`posting_date` DESC
					LIMIT 1 """.format(row.account, frappe.utils.nowdate(), sumber_invoice.posting_date))


				if len(apakah_exchange_rate_baru) > 0:
					change_rate = apakah_exchange_rate_baru[0][0]

				baris_baru = {
					"account": row.account,
					"party_type": row.party_type,
					"party" : row.party,
					"exchange_rate": row.exchange_rate,
					"account_currency" : row.currency,
					"branch" : row.branch,
					"user_remark" : row.remarks,
					"cost_center" : row.cost_center,
					"credit_in_account_currency": row.difference * -1,
					"credit": row.difference * row.exchange_rate * -1,
					"sumber_cash_request" :cash_request,
					"supplier_cash_request": row.supplier,
					"reference_type" : sumber_doc.type,
					"reference_name" : row.document
				}
				total_credit += row.difference * change_rate * -1
			else:
				if frappe.get_doc("Account",row.account).account_currency == "IDR" and sumber_doc.currency == "IDR":
				
					baris_baru = {
						"account": row.account,
						"party_type": row.party_type,
						"party" : row.party,
						"exchange_rate": row.exchange_rate,
						"account_currency" : frappe.get_doc("Account",row.account).account_currency,
						"branch" : row.branch,
						"user_remark" : row.remarks,
						"cost_center" : row.cost_center,
						"credit_in_account_currency": row.difference * -1,
						"credit": row.difference * -1,
						"sumber_cash_request" : cash_request,
						"supplier_cash_request": row.supplier
					}
					total_credit += row.difference * -1
				else:
					if frappe.get_doc("Account",row.account).account_currency != "IDR":
						baris_baru = {
							"account": row.account,
							"party_type": row.party_type,
							"party" : row.party,
							"exchange_rate": row.exchange_rate,
							"account_currency" : frappe.get_doc("Account",row.account).account_currency,
							"branch" : row.branch,
							"user_remark" : row.remarks,
							"cost_center" : row.cost_center,
							"credit_in_account_currency": row.difference * -1,
							"credit": row.difference * row.exchange_rate * -1,
							"sumber_cash_request" : cash_request,
							"supplier_cash_request": row.supplier
						}
						total_credit += row.difference * row.exchange_rate * -1
					else:
						baris_baru = {
							"account": row.account,
							"party_type": row.party_type,
							"party" : row.party,
							"exchange_rate": row.exchange_rate,
							"account_currency" : frappe.get_doc("Account",row.account).account_currency,
							"branch" : row.branch,
							"user_remark" : row.remarks,
							"cost_center" : row.cost_center,
							"credit_in_account_currency": row.difference * row.exchange_rate * -1,
							"credit": row.difference * row.exchange_rate * -1,
							"sumber_cash_request" : cash_request,
							"supplier_cash_request": row.supplier
						}
						total_credit += row.difference * row.exchange_rate * -1
		target_doc.append("accounts", baris_baru)

	difference = total_debit - total_credit
	sumber_account = ""

	if sumber_doc.accounts:
		sumber_account = sumber_doc.accounts

	row_branch = row.branch
	row_cost_center = row.cost_center
	row_remarks = row.remarks

	if difference > 0:
		baris_baru = {
			"account": sumber_account,
			"branch" : row.branch,
			"user_remark" : row.remarks,
			"cost_center" : row.cost_center,
			"credit_in_account_currency": difference,
			"credit": difference,
			"sumber_cash_request" :cash_request,
			"supplier_cash_request": row.supplier
		}
		total_credit += difference
		target_doc.append("accounts", baris_baru)
	else:
		baris_baru = {
			"account": sumber_account,
			"branch" : row.branch,
			"user_remark" : row.remarks,
			"cost_center" : row.cost_center,
			"debit_in_account_currency": difference * - 1,
			"debit": difference * - 1,
			"sumber_cash_request" :cash_request,
			"supplier_cash_request": row.supplier
		}
		total_debit += difference * -1
		target_doc.append("accounts", baris_baru)

	target_doc.total_debit = total_debit
	target_doc.total_credit = total_credit


	sementara_total_debit = 0
	sementara_total_credit = 0

	for row in target_doc.accounts:
		if row.debit:
			sementara_total_debit += row.debit
		if row.credit:
			sementara_total_credit += row.credit

	if sementara_total_debit != sementara_total_credit:
		if sementara_total_debit > sementara_total_credit:

			baris_baru = {
				"account" : "8107 - SELISIH KURS TEREALISASI - G",
				"branch" : row_branch,
				"user_remark" : row_remarks,
				"cost_center" : row_cost_center,
				"credit_in_account_currency": sementara_total_debit - sementara_total_credit ,
				"credit": sementara_total_debit - sementara_total_credit ,
				"sumber_cash_request" :cash_request
			}
			target_doc.append("accounts", baris_baru)
		else:

			baris_baru = {
				"account" : "8107 - SELISIH KURS TEREALISASI - G",
				"branch" : row_branch,
				"user_remark" : row_remarks,
				"cost_center" : row_cost_center,
				"debit_in_account_currency": sementara_total_credit - sementara_total_debit ,
				"debit": sementara_total_credit - sementara_total_debit ,
				"sumber_cash_request" :cash_request
			}
			target_doc.append("accounts", baris_baru)


	if sumber_doc.currency != "IDR":
		target_doc.multi_currency = 1

	return target_doc.as_dict()
