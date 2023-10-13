import frappe,erpnext
from frappe.model.document import Document
import json
from frappe import msgprint, _
from frappe.utils import flt, cint, cstr, today, get_formatted_email

@frappe.whitelist()
def set_sinv(doc,method):
	list_sinv = frappe.db.sql(""" SELECT name 
		FRom `tabSales Invoice` 
		WHERE customer = "{}" 
		and tax_or_non_tax = "Tax"
		and docstatus = 0 """.format(doc.name))
	if doc.alamat_pajak:
		
		for row in list_sinv:
			doc_sinv = frappe.get_doc("Sales Invoice", row[0])
			doc_sinv.alamat_pajak = doc.alamat_pajak
			doc_sinv.db_update()

	if doc.nama_pajak:
		for row in list_sinv:
			doc_sinv = frappe.get_doc("Sales Invoice", row[0])
			doc_sinv.tax_name = doc.nama_pajak
			doc_sinv.db_update()

	if doc.no_ktp:
		for row in list_sinv:
			doc_sinv = frappe.get_doc("Sales Invoice", row[0])
			doc_sinv.no_ktp = doc.no_ktp
			doc_sinv.db_update()

	if doc.npwp:
		for row in list_sinv:
			doc_sinv = frappe.get_doc("Sales Invoice", row[0])
			doc_sinv.npwp = doc.npwp
			doc_sinv.db_update()

	

@frappe.whitelist()
def assign_business_group(doc,method):

	if doc.is_new() == 0:
		if doc.business_group:
			customer_doc = frappe.get_doc("Customer", doc.name)
			if doc.business_group != customer_doc.business_group:
				business_group_doc = frappe.get_doc("Business Group", doc.business_group)
				batas = business_group_doc.credit_limit
				total_business_group = 0

				manusia_group = frappe.db.sql(""" SELECT name FROM `tabCustomer` WHERE business_group = "{}" """.format(doc.business_group))
				for row in manusia_group:
					total_business_group += get_customer_outstanding(row[0], frappe.defaults.get_global_default('company')) 

				total_unpaid_customer = get_customer_outstanding(doc.name, frappe.defaults.get_global_default('company'))
				if flt(total_business_group) + flt(total_unpaid_customer) > batas:
					frappe.throw("Business Group only has {} amount for Credit Limit, meanwhile Customer {} has {} unpaid, making total will be {}. <br> Business Group is not assigned.".format(batas, doc.name, total_unpaid_customer, flt(total_business_group) + flt(total_unpaid_customer) ))


@frappe.whitelist()
def get_overdue_and_credit_limit(customer):
	overdue_percentage = 0
	customer_credit_limit_available = 0
	if customer:
		total_piutang = frappe.db.sql(""" 
			SELECT IFNULL(sum(si.outstanding_amount),0) 
			FROM `tabSales Invoice` si 
			WHERE customer = "{}" and docstatus = 1; 
		""".format(customer))
		total_overdue = frappe.db.sql(""" 
			SELECT IFNULL(sum(si.outstanding_amount) ,0)
			FROM `tabSales Invoice` si 
			WHERE customer = "{}" and docstatus = 1 and due_date < date(now());
		""".format(customer))



		piutang = 0
		overdue = 0
		if total_overdue:
			overdue = total_overdue[0][0]
		if total_piutang:
			piutang = total_piutang[0][0]

		if piutang > 0:
			overdue_percentage = flt(overdue / piutang * 100)
		else:
			overdue_percentage = 0 

		
		credit_limit = 0
		customer_doc = frappe.get_doc("Customer",customer)
		terpakai = 0

		if customer_doc.business_group:
			business_group_doc = frappe.get_doc("Business Group", customer_doc.business_group)
			credit_limit = business_group_doc.credit_limit

			manusia_group = frappe.db.sql(""" SELECT name FROM `tabCustomer` WHERE business_group = "{}" """.format(customer_doc.business_group))
			for row in manusia_group:
				terpakai += get_customer_outstanding(row[0], frappe.defaults.get_global_default('company')) 

		else:
			if customer_doc.credit_limits:
				credit_limit = customer_doc.credit_limits[0].credit_limit

			terpakai += get_customer_outstanding(customer_doc.name, frappe.defaults.get_global_default('company')) 

		customer_credit_limit_available = credit_limit - terpakai

	return [overdue_percentage, customer_credit_limit_available]



@frappe.whitelist()
def get_max_credit_limit(self,method):
	# credit_limit = 0
	# if self.credit_limits:
	# 	if self.credit_limits[0].credit_limit > 0:
	# 		credit_limit = self.credit_limits[0].credit_limit
	# self.max_credit_limit = credit_limit
	# self.db_update()
	pass
@frappe.whitelist()
def get_credit_limit(customer):
	credit_limit = 0
	patokan = frappe.db.sql(""" select credit_limit 
		from `tabCustomer Credit Limit` WHERE parent = "{}" """.format(customer))
	if patokan:
		if patokan[0]:
			if patokan[0][0]:
				credit_limit = flt(patokan[0][0])

	return credit_limit

@frappe.whitelist()
def get_address_contact_from_customer(customer):
	return frappe.db.sql(""" SELECT 
			tc.name, CONCAT(tad.`address_line1`,"\n",tad.`city`) as address, 
			tac.`name` as contact,
			tc.`mobile_no`, tc.payment_terms
			FROM `tabCustomer` tc
			LEFT JOIN `tabDynamic Link` dladdress ON dladdress.`link_doctype` = "Customer"
			AND dladdress.`link_name` = tc.name
			AND dladdress.`parenttype` = "Address"
			LEFT JOIN `tabAddress` tad ON dladdress.parent = tad.name
			AND tad.`address_type` = "Billing"

			LEFT JOIN `tabDynamic Link` dladdress2 ON dladdress2.`link_doctype` = "Customer"
			AND dladdress2.`link_name` = tc.name
			AND dladdress2.`parenttype` = "Contact"
			LEFT JOIN `tabContact` tac ON dladdress2.parent = tac.name

			WHERE tc.name = "{}" """.format(customer),as_dict=1)

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_all_with_no_business_group(doctype, txt, searchfield, start, page_len, filters):
	from frappe.desk.reportview import get_match_cond
	
	condition = ""	
	meta = frappe.get_meta("Customer")
	searchfields = meta.get_search_fields()

	if searchfield and (meta.get_field(searchfield)\
				or searchfield in frappe.db.DEFAULT_COLUMNS):
		searchfields.append(searchfield)

	search_condition = ''
	
	return frappe.db.sql("""select
			`tabCustomer`.name, `tabCustomer`.customer_name
		from
			`tabCustomer`
		where
			`tabCustomer`.disabled = 0 AND
			(`tabCustomer`.business_group = ""
			or
			`tabCustomer`.business_group IS NULL)

			AND (`tabCustomer`.name LIKE %(txt)s OR `tabCustomer`.customer_name LIKE %(txt)s)

		order by
			if(locate(%(_txt)s, `tabCustomer`.name), locate(%(_txt)s, `tabCustomer`.name), 99999),
			`tabCustomer`.idx desc, `tabCustomer`.name
		limit %(start)s, %(page_len)s """.format(
			mcond=get_match_cond(doctype),
			key=searchfield,
			search_condition = search_condition,
			condition=condition or ""), {
			'txt': '%' + txt + '%',
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len
		})

def get_customer_outstanding(customer, company, ignore_outstanding_sales_order=False, cost_center=None):
	# Outstanding based on GL Entries

	cond = ""
	if cost_center:
		lft, rgt = frappe.get_cached_value("Cost Center",
			cost_center, ['lft', 'rgt'])

		cond = """ and cost_center in (select name from `tabCost Center` where
			lft >= {0} and rgt <= {1})""".format(lft, rgt)

	outstanding_based_on_gle = frappe.db.sql("""
		select sum(debit) - sum(credit)
		from `tabGL Entry` where party_type = 'Customer'
		and party = %s and company=%s {0}""".format(cond), (customer, company))

	outstanding_based_on_gle = flt(outstanding_based_on_gle[0][0]) if outstanding_based_on_gle else 0

	# Outstanding based on Sales Order
	outstanding_based_on_so = 0

	# if credit limit check is bypassed at sales order level,
	# we should not consider outstanding Sales Orders, when customer credit balance report is run
	if not ignore_outstanding_sales_order:
		outstanding_based_on_so = frappe.db.sql("""
			select sum(base_grand_total*(100 - per_billed)/100)
			from `tabSales Order`
			where customer=%s and docstatus = 1 and company=%s
			and per_billed < 100 and status != 'Closed'""", (customer, company))

		outstanding_based_on_so = flt(outstanding_based_on_so[0][0]) if outstanding_based_on_so else 0

	# Outstanding based on Delivery Note, which are not created against Sales Order
	outstanding_based_on_dn = 0

	unmarked_delivery_note_items = frappe.db.sql("""select
			dn_item.name, dn_item.amount, dn.base_net_total, dn.base_grand_total
		from `tabDelivery Note` dn, `tabDelivery Note Item` dn_item
		where
			dn.name = dn_item.parent
			and dn.customer=%s and dn.company=%s
			and dn.docstatus = 1 and dn.status not in ('Closed', 'Stopped')
			and ifnull(dn_item.against_sales_order, '') = ''
			and ifnull(dn_item.against_sales_invoice, '') = ''
		""", (customer, company), as_dict=True)

	if not unmarked_delivery_note_items:
		return outstanding_based_on_gle + outstanding_based_on_so

	si_amounts = frappe.db.sql("""
		SELECT
			dn_detail, sum(amount) from `tabSales Invoice Item`
		WHERE
			docstatus = 1
			and dn_detail in ({})
		GROUP BY dn_detail""".format(", ".join(
			frappe.db.escape(dn_item.name)
			for dn_item in unmarked_delivery_note_items
		))
	)

	si_amounts = {si_item[0]: si_item[1] for si_item in si_amounts}

	for dn_item in unmarked_delivery_note_items:
		dn_amount = flt(dn_item.amount)
		si_amount = flt(si_amounts.get(dn_item.name))

		if dn_amount > si_amount and dn_item.base_net_total:
			outstanding_based_on_dn += ((dn_amount - si_amount)
				/ dn_item.base_net_total) * dn_item.base_grand_total

	return outstanding_based_on_gle
		