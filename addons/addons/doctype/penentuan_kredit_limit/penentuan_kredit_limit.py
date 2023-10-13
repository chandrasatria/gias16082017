# Copyright (c) 2021, das and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint, cstr, today, get_formatted_email


@frappe.whitelist()
def debug_before_submit():
	doc = frappe.get_doc("Penentuan Kredit Limit","KL-1020220014")
	if doc.selection == "By Business Group":
		if doc.business_group:
			business_group_doc = frappe.get_doc("Business Group", doc.business_group)
			business_group_doc.credit_limit = doc.limit_disetujui
			business_group_doc.term_of_payment = doc.top_disetujui
			batas = business_group_doc.credit_limit

			total_business_group = 0

			manusia_group = frappe.db.sql(""" SELECT name FROM `tabCustomer` WHERE business_group = "{}" """.format(doc.business_group))
			for row in manusia_group:
				total_business_group += get_customer_outstanding(row[0], frappe.defaults.get_global_default('company'),ignore_outstanding_sales_order=True) 
			
			if flt(total_business_group) > batas:
				frappe.throw("Business Group only has {} amount for Credit Limit, meanwhile Customer in this Business Group has {} unpaid. <br> Business Group is not assigned.".format(batas, flt(total_business_group)))
			else:
				business_group_doc.db_update()
				# for row in manusia_group:
				# 	customer_doc = frappe.get_doc("Customer", row[0])
					# customer_doc.payment_terms = doc.top_disetujui
					# customer_doc.db_update()
		else:
			frappe.throw("Business Group is mandatory")
	elif doc.selection == "By Customer":
		if doc.customer:
			total_customer = get_customer_outstanding(doc.customer, frappe.defaults.get_global_default('company'),ignore_outstanding_sales_order=True) 
			if flt(total_customer) > flt(doc.limit_disetujui):
				frappe.throw("This Customer has {} unpaid, meanwhile approved amount is {}. <br> Credit Limit is not assigned.".format(total_customer, doc.limit_disetujui))
			else:
				customer_doc = frappe.get_doc("Customer", doc.customer)
				customer_doc.credit_limits = []
				
				row = customer_doc.append('credit_limits', {})
				row.credit_limit = doc.limit_disetujui
				row.company = frappe.defaults.get_global_default('company')
				customer_doc.payment_terms = doc.top_disetujui
				
				customer_doc.customer_risk = doc.adjustment
				customer_doc.save(ignore_permissions=True)

				customer_doc = frappe.get_doc("Customer", doc.customer)
				for cus_row in customer_doc.credit_limits:
					cus_row.credit_limit = doc.limit_disetujui
					cus_row.db_update()


		else:
			frappe.throw("Business Group is mandatory")
class PenentuanKreditLimit(Document):
	def validate(self):
		if self.docstatus == 0:
			if self.customer:
				total_piutang = frappe.db.sql(""" 
					SELECT IFNULL(sum(si.outstanding_amount),0) 
					FROM `tabSales Invoice` si 
					WHERE customer = "{}" and docstatus = 1; 
				""".format(self.customer))
				total_overdue = frappe.db.sql(""" 
					SELECT IFNULL(sum(si.outstanding_amount) ,0)
					FROM `tabSales Invoice` si 
					WHERE customer = "{}" and docstatus = 1 and due_date < date(now());
				""".format(self.customer))

				piutang = 0
				overdue = 0
				if total_overdue:
					overdue = total_overdue[0][0]
				if total_piutang:
					piutang = total_piutang[0][0]

				if piutang > 0:
					self.overdue_percentage = flt(overdue / piutang * 100)
				else:
					self.overdue_percentage = 0 


				credit_limit = 0
				customer_doc = frappe.get_doc("Customer",self.customer)
				terpakai = 0

				if customer_doc.business_group:
					business_group_doc = frappe.get_doc("Business Group", customer_doc.business_group)
					credit_limit = business_group_doc.credit_limit

					manusia_group = frappe.db.sql(""" SELECT name FROM `tabCustomer` WHERE business_group = "{}" """.format(customer_doc.business_group))
					for row in manusia_group:
						terpakai += get_customer_outstanding(row[0], frappe.defaults.get_global_default('company'),ignore_outstanding_sales_order=True) 

				else:
					if customer_doc.credit_limits:
						credit_limit = customer_doc.credit_limits[0].credit_limit

					terpakai += get_customer_outstanding(customer_doc.name, frappe.defaults.get_global_default('company'),ignore_outstanding_sales_order=True) 

				self.customer_credit_limit_available = credit_limit - terpakai

				



	def before_submit(doc):
		if doc.selection == "By Business Group":
			if doc.business_group:
				business_group_doc = frappe.get_doc("Business Group", doc.business_group)
				business_group_doc.credit_limit = doc.limit_disetujui
				business_group_doc.term_of_payment = doc.top_disetujui
				batas = business_group_doc.credit_limit

				total_business_group = 0

				manusia_group = frappe.db.sql(""" SELECT name FROM `tabCustomer` WHERE business_group = "{}" """.format(doc.business_group))
				for row in manusia_group:
					total_business_group += get_customer_outstanding(row[0], frappe.defaults.get_global_default('company'),ignore_outstanding_sales_order=True) 
				
				if flt(total_business_group) > batas:
					frappe.throw("Business Group only has {} amount for Credit Limit, meanwhile Customer in this Business Group has {} unpaid. <br> Business Group is not assigned.".format(batas, flt(total_business_group)))
				else:
					business_group_doc.db_update()
					# for row in manusia_group:
					# 	customer_doc = frappe.get_doc("Customer", row[0])
						# customer_doc.payment_terms = doc.top_disetujui
						# customer_doc.db_update()
			else:
				frappe.throw("Business Group is mandatory")
		elif doc.selection == "By Customer":
			if doc.customer:
				total_customer = get_customer_outstanding(doc.customer, frappe.defaults.get_global_default('company'),ignore_outstanding_sales_order=True) 
				if flt(total_customer) > flt(doc.limit_disetujui):
					frappe.throw("This Customer has {} unpaid, meanwhile approved amount is {}. <br> Credit Limit is not assigned.".format(total_customer, doc.limit_disetujui))
				else:
					customer_doc = frappe.get_doc("Customer", doc.customer)
					customer_doc.credit_limits = []
					
					row = customer_doc.append('credit_limits', {})
					row.credit_limit = doc.limit_disetujui
					row.company = frappe.defaults.get_global_default('company')
					customer_doc.payment_terms = doc.top_disetujui
					
					customer_doc.customer_risk = doc.adjustment
					customer_doc.save(ignore_permissions=True)

					customer_doc = frappe.get_doc("Customer", doc.customer)
					for cus_row in customer_doc.credit_limits:
						cus_row.credit_limit = doc.limit_disetujui
						cus_row.db_update()


			else:
				frappe.throw("Business Group is mandatory")

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
	
@frappe.whitelist()
def debug_penentuan_kredit():
	doc = frappe.get_doc("Penentuan Kredit Limit","KL-0008")
	if doc.selection == "By Business Group":
		if doc.business_group:
			business_group_doc = frappe.get_doc("Business Group", doc.business_group)
			business_group_doc.credit_limit = doc.limit_disetujui
			business_group_doc.term_of_payment = doc.top_disetujui
			batas = business_group_doc.credit_limit

			total_business_group = 0

			manusia_group = frappe.db.sql(""" SELECT name FROM `tabCustomer` WHERE business_group = "{}" """.format(doc.business_group))
			for row in manusia_group:
				total_business_group += get_customer_outstanding(row[0], frappe.defaults.get_global_default('company'),ignore_outstanding_sales_order=True) 
			
			if flt(total_business_group) > batas:
				frappe.throw("Business Group only has {} amount for Credit Limit, meanwhile Customer in this Business Group has {} unpaid. <br> Business Group is not assigned.".format(batas, flt(total_business_group)))
			else:
				business_group_doc.db_update()
				for row in manusia_group:
					customer_doc = frappe.get_doc("Customer", row[0])
					customer_doc.payment_terms = doc.top_disetujui
					customer_doc.db_update()
		else:
			frappe.throw("Business Group is mandatory")
	elif doc.selection == "By Customer":
		if doc.customer:
			total_customer = get_customer_outstanding(doc.customer, frappe.defaults.get_global_default('company'),ignore_outstanding_sales_order=True) 
			if flt(total_customer) > flt(doc.limit_disetujui):
				frappe.throw("This Customer has {} unpaid, meanwhile approved amount is {}. <br> Credit Limit is not assigned.".format(total_customer, doc.limit_disetujui))
			else:
				customer_doc = frappe.get_doc("Customer", doc.customer)
				customer_doc.credit_limits = []
				
				row = customer_doc.append('credit_limits', {})
				row.credit_limit = doc.limit_disetujui
				row.company = frappe.defaults.get_global_default('company')
				customer_doc.payment_terms = doc.top_disetujui
				
				customer_doc.customer_risk = doc.adjustment
				customer_doc.save()

		else:
			frappe.throw("Business Group is mandatory")