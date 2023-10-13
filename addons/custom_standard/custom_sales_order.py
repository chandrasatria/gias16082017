import frappe,erpnext
from frappe.utils import flt
from frappe.model.mapper import get_mapped_doc
from frappe.model.utils import get_fetch_values
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from frappe.contacts.doctype.address.address import get_company_address

from frappe.model.naming import make_autoname, revert_series_if_last
from erpnext.selling.doctype.sales_order.sales_order import SalesOrder
from frappe.utils import add_days, cint, cstr, flt, get_link_to_form, getdate, nowdate, strip_html
from frappe import _


@frappe.whitelist()
def isi_pt(self,method):
	if not self.payment_terms_template:
		cust_doc = frappe.get_doc("Customer", self.customer)
		if cust_doc.payment_terms:
			self.payment_terms_template = cust_doc.payment_terms
			self.set_payment_schedule()

@frappe.whitelist()
def check_apakah_waiting_head_admin(self):
	if self.workflow_state == "Waiting Review Head Admin":
		if "GIAS Head Admin" not in frappe.get_roles():
			frappe.throw("SO {} cannot be changed as it is in Waiting Review Head Admin status".format(self.name))

@frappe.whitelist()
def check_tanggal(self,method):
	company_doc = frappe.get_doc("Company", self.company)
	if "Input Backdate Sales Order" not in frappe.get_roles():
		if self.get("__islocal") != 1:
			if getdate(str(self.transaction_date)) < getdate(str(self.creation)):
				frappe.throw("Posting Date for Sales Order are not allowed backdate from creation. Please check the posting date again.")
		else:
			if getdate(str(self.transaction_date)) < getdate(str(frappe.utils.today())):
				frappe.throw("Posting Date for Sales Order are not allowed backdate. Please check the posting date again.")

	if not self.items:
		frappe.throw("Sales Order Item is mandatory.")
@frappe.whitelist()
def custom_check_nextdoc_docstatus(self):
		# Checks Delivery Note
		submit_dn = frappe.db.sql_list("""
			select t1.name
			from `tabDelivery Note` t1,`tabDelivery Note Item` t2
			where t1.name = t2.parent and t2.against_sales_order = %s and t1.docstatus = 1
			AND t1.workflow_state != "Rejected"
			""", self.name)

		if submit_dn:
			submit_dn = [get_link_to_form("Delivery Note", dn) for dn in submit_dn]
			frappe.throw(_("Delivery Notes {0} must be cancelled before cancelling this Sales Order")
				.format(", ".join(submit_dn)))

		# Checks Sales Invoice
		submit_rv = frappe.db.sql_list("""select t1.name
			from `tabSales Invoice` t1,`tabSales Invoice Item` t2
			where t1.name = t2.parent and t2.sales_order = %s and t1.docstatus < 2
			AND t1.workflow_state != "Rejected"
			""",
			self.name)

		if submit_rv:
			submit_rv = [get_link_to_form("Sales Invoice", si) for si in submit_rv]
			frappe.throw(_("Sales Invoice {0} must be cancelled before cancelling this Sales Order")
				.format(", ".join(submit_rv)))

		#check maintenance schedule
		submit_ms = frappe.db.sql_list("""
			select t1.name
			from `tabMaintenance Schedule` t1, `tabMaintenance Schedule Item` t2
			where t2.parent=t1.name and t2.sales_order = %s and t1.docstatus = 1""", self.name)

		if submit_ms:
			submit_ms = [get_link_to_form("Maintenance Schedule", ms) for ms in submit_ms]
			frappe.throw(_("Maintenance Schedule {0} must be cancelled before cancelling this Sales Order")
				.format(", ".join(submit_ms)))

		# check maintenance visit
		submit_mv = frappe.db.sql_list("""
			select t1.name
			from `tabMaintenance Visit` t1, `tabMaintenance Visit Purpose` t2
			where t2.parent=t1.name and t2.prevdoc_docname = %s and t1.docstatus = 1""",self.name)

		if submit_mv:
			submit_mv = [get_link_to_form("Maintenance Visit", mv) for mv in submit_mv]
			frappe.throw(_("Maintenance Visit {0} must be cancelled before cancelling this Sales Order")
				.format(", ".join(submit_mv)))

		# check work order
		pro_order = frappe.db.sql_list("""
			select name
			from `tabWork Order`
			where sales_order = %s and docstatus = 1""", self.name)

		if pro_order:
			pro_order = [get_link_to_form("Work Order", po) for po in pro_order]
			frappe.throw(_("Work Order {0} must be cancelled before cancelling this Sales Order")
				.format(", ".join(pro_order)))

SalesOrder.check_nextdoc_docstatus = custom_check_nextdoc_docstatus

@frappe.whitelist()
def rename_so():
	list_so = frappe.db.sql(""" SELECT NAME 
		FROM `tabSales Order`
		WHERE NAME LIKE "%SAL-ORD%"
		ORDER BY NAME ASC 
		""")

	for row in list_so:
		doc = frappe.get_doc("Sales Order", row[0])
		month = frappe.utils.formatdate(frappe.utils.getdate(doc.transaction_date),"MM")
		year = frappe.utils.formatdate(frappe.utils.getdate(doc.transaction_date),"YY")

		if doc.tax_or_non_tax == "Tax":
			tax = 1
		else:
			tax = 2
		nama_baru = make_autoname("SO-{}-{}-{}-.#####".format(tax,year,month))

		frappe.rename_doc("Sales Order",doc.name,nama_baru)
		print("{}={}={}".format(doc.name,nama_baru,frappe.get_doc("Company","GIAS").nama_cabang))
		frappe.db.commit()



@frappe.whitelist()
def cancel_flag(self,method):
	check_sinv = frappe.db.sql(""" 
		SELECT sii.parent FROM `tabSales Invoice Item` sii
		JOIN `tabSales Invoice` tsi ON tsi.name = sii.parent
		WHERE sii.sales_order = "{}" and sii.docstatus = 0 and tsi.workflow_states != "Rejected" """.format(self.name))
	if check_sinv:
		if check_sinv[0]:
			if check_sinv[0][0]:
				frappe.throw("There is Sales Invoice Draft with number {} so this Sales Order cannot be cancelled.".format(check_sinv[0][0]))
	
	check_dinv = frappe.db.sql(""" 
		SELECT sii.parent FROM `tabDelivery Note Item` sii
		JOIN `tabDelivery Note` tsi ON tsi.name = sii.parent
		WHERE sii.against_sales_order = "{}" and sii.docstatus = 0 and tsi.workflow_state != "Rejected" """.format(self.name))
	if check_dinv:
		if check_dinv[0]:
			if check_dinv[0][0]:
				frappe.throw("There is Delivery Note Draft with number {} so this Sales Order cannot be cancelled.".format(check_dinv[0][0]))


@frappe.whitelist()
def render_print_data(self,method):
	for item in self.items:
		if item.panjang_custom and item.qty_basic:
			item.qty=flt(item.panjang_custom)*flt(item.qty_basic)
			item.stock_qty=item.qty * item.conversion_factor
			item.hpp_custom = item.rate* flt(item.panjang_custom)
			item.total_amount_after_conversion =item.hpp_custom*flt(item.qty_basic)

			self.run_method("calculate_taxes_and_totals")

	self.validate_uom_is_integer("stock_uom", "stock_qty")

def remove_dn_link_reject(self,method):
	pass
@frappe.whitelist()
def custom_make_delivery_note(source_name, target_doc=None, skip_item_mapping=False):
	def set_missing_values(source, target):

		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("set_po_nos")
		target.run_method("calculate_taxes_and_totals")

		if source.company_address:
			target.update({'company_address': source.company_address})
		else:
			# set company address
			target.update(get_company_address(target.company))

		if target.company_address:
			target.update(get_fetch_values("Delivery Note", 'company_address', target.company_address))

	def update_item(source, target, source_parent):
		target.base_amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.base_rate)
		target.amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.rate)
		target.qty = flt(source.qty) - flt(source.delivered_qty)
		target.qty_real = target.qty

		item = get_item_defaults(target.item_code, source_parent.company)
		item_group = get_item_group_defaults(target.item_code, source_parent.company)

		if item:
			target.cost_center = frappe.db.get_value("Project", source_parent.project, "cost_center") \
				or item.get("buying_cost_center") \
				or item_group.get("buying_cost_center")

	mapper = {
		"Sales Order": {
			"doctype": "Delivery Note",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Sales Taxes and Charges": {
			"doctype": "Sales Taxes and Charges",
			"add_if_empty": True
		},
		"Sales Team": {
			"doctype": "Sales Team",
			"add_if_empty": True
		}
	}

	if not skip_item_mapping:
		mapper["Sales Order Item"] = {
			"doctype": "Delivery Note Item",
			"field_map": {
				"rate": "rate",
				"name": "so_detail",
				"parent": "against_sales_order",
				"qty_real":"qty",
				"qty":"qty"
			},
			"postprocess": update_item,
			"condition": lambda doc: abs(doc.delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier!=1
		}

	target_doc = get_mapped_doc("Sales Order", source_name, mapper, target_doc, set_missing_values)

	
	return target_doc
@frappe.whitelist()
def calculate_overdue_percentage_debug():
	self = frappe.get_doc("Sales Order","SO-1-23-01-00578")
	if self.docstatus == 1:
		if self.customer:
			total_piutang = frappe.db.sql(""" 
				SELECT IFNULL(sum(si.outstanding_amount),0) 
				FROM `tabSales Invoice` si 
				WHERE customer = "{}" and docstatus = 1 and outstanding_amount > 0; 
			""".format(self.customer))
			total_overdue = frappe.db.sql(""" 
				SELECT IFNULL(sum(si.outstanding_amount) ,0)
				FROM `tabSales Invoice` si 
				WHERE customer = "{}" and docstatus = 1 and due_date < date(now()) and outstanding_amount > 0;
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
					terpakai += get_customer_outstanding(row[0], frappe.defaults.get_global_default('company')) 

			else:
				if customer_doc.credit_limits:
					credit_limit = customer_doc.credit_limits[0].credit_limit

				terpakai += get_customer_outstanding(customer_doc.name, frappe.defaults.get_global_default('company')) 

			self.customer_credit_limit_available = credit_limit - terpakai
			self.customer_credit_limit_available = 300000000
			self.db_update()
			print(terpakai)



@frappe.whitelist()
def patch_calculate_credit_limit_available():
	self = frappe.get_doc("Customer","CUST-GIAS-BRU-00452")
	total_piutang = frappe.db.sql(""" 
		SELECT IFNULL(sum(si.outstanding_amount),0) 
		FROM `tabSales Invoice` si 
		WHERE customer = "{}" and docstatus = 1 and outstanding_amount > 0; 
	""".format(self.name))
	total_overdue = frappe.db.sql(""" 
		SELECT IFNULL(sum(si.outstanding_amount) ,0)
		FROM `tabSales Invoice` si 
		WHERE customer = "{}" and docstatus = 1 and due_date < date(now()) and outstanding_amount > 0;
	""".format(self.name))

	piutang = 0
	overdue = 0
	if total_overdue:
		overdue = total_overdue[0][0]
	if total_piutang:
		piutang = total_piutang[0][0]

	credit_limit = 0
	terpakai = 0

	if self.business_group:
		business_group_doc = frappe.get_doc("Business Group", self.business_group)
		credit_limit = business_group_doc.credit_limit
		self.business_group_credit_limit = credit_limit
		self.payment_terms = business_group_doc.term_of_payment
		# frappe.db.sql(""" UPDATE `tabCustomer` SET business_group_credit_limit = {}, payment_terms = "{}" WHERE name = "{}" """.format(credit_limit, business_group_doc.term_of_payment,self.name))

		manusia_group = frappe.db.sql(""" SELECT name FROM `tabCustomer` WHERE business_group = "{}" """.format(self.business_group))
		for row in manusia_group:
			print(row[0])
			# print(get_customer_outstanding(row[0], frappe.defaults.get_global_default('company')))
			terpakai += get_customer_outstanding(row[0], frappe.defaults.get_global_default('company')) 

	elif self.credit_limits:
		credit_limit = self.credit_limits[0].credit_limit
		self.business_group_credit_limit = 0
		# frappe.db.sql(""" UPDATE `tabCustomer` SET business_group_credit_limit = {} WHERE name = "{}" """.format(0,self.name))
		terpakai += get_customer_outstanding(self.name, frappe.defaults.get_global_default('company')) 

	else:
		self.business_group_credit_limit = 0
		frappe.db.sql(""" UPDATE `tabCustomer` SET business_group_credit_limit = {} WHERE name = "{}" """.format(0,self.name))
		return

	self.customer_credit_limit_available = credit_limit - terpakai
	if self.business_group:
		self.business_group_credit_limit_available = credit_limit - terpakai
	else:
		self.business_group_credit_limit_available = 0


@frappe.whitelist()
def calculate_overdue_percentage(self,method):
	if self.docstatus == 0:
		if self.customer:
			total_piutang = frappe.db.sql(""" 
				SELECT IFNULL(sum(si.outstanding_amount),0) 
				FROM `tabSales Invoice` si 
				WHERE customer = "{}" and docstatus = 1 and outstanding_amount > 0; 
			""".format(self.customer))
			total_overdue = frappe.db.sql(""" 
				SELECT IFNULL(sum(si.outstanding_amount) ,0)
				FROM `tabSales Invoice` si 
				WHERE customer = "{}" and docstatus = 1 and due_date < date(now()) and outstanding_amount > 0;
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
					terpakai += get_customer_outstanding(row[0], frappe.defaults.get_global_default('company')) 

			else:
				if customer_doc.credit_limits:
					credit_limit = customer_doc.credit_limits[0].credit_limit

				terpakai += get_customer_outstanding(customer_doc.name, frappe.defaults.get_global_default('company')) 

			self.customer_credit_limit_available = credit_limit - terpakai
			
@frappe.whitelist()
def calculate_credit_limit_available(self,method):
	
	total_piutang = frappe.db.sql(""" 
		SELECT IFNULL(sum(si.outstanding_amount),0) 
		FROM `tabSales Invoice` si 
		WHERE customer = "{}" and docstatus = 1 and outstanding_amount > 0; 
	""".format(self.name))
	total_overdue = frappe.db.sql(""" 
		SELECT IFNULL(sum(si.outstanding_amount) ,0)
		FROM `tabSales Invoice` si 
		WHERE customer = "{}" and docstatus = 1 and due_date < date(now()) and outstanding_amount > 0;
	""".format(self.name))

	piutang = 0
	overdue = 0
	if total_overdue:
		overdue = total_overdue[0][0]
	if total_piutang:
		piutang = total_piutang[0][0]

	credit_limit = 0
	terpakai = 0

	if self.business_group:
		business_group_doc = frappe.get_doc("Business Group", self.business_group)
		credit_limit = business_group_doc.credit_limit
		self.business_group_credit_limit = credit_limit
		if self.doctype != "Customer":
			self.payment_terms = business_group_doc.term_of_payment
				
		frappe.db.sql(""" UPDATE `tabCustomer` SET business_group_credit_limit = {} WHERE name = "{}" """.format(credit_limit,self.name))

		manusia_group = frappe.db.sql(""" SELECT name FROM `tabCustomer` WHERE business_group = "{}" """.format(self.business_group))
		for row in manusia_group:
			terpakai += get_customer_outstanding(row[0], frappe.defaults.get_global_default('company')) 

	elif self.credit_limits:
		credit_limit = self.credit_limits[0].credit_limit
		self.business_group_credit_limit = 0
		frappe.db.sql(""" UPDATE `tabCustomer` SET business_group_credit_limit = {} WHERE name = "{}" """.format(0,self.name))
		terpakai += get_customer_outstanding(self.name, frappe.defaults.get_global_default('company')) 

	else:
		self.business_group_credit_limit = 0
		frappe.db.sql(""" UPDATE `tabCustomer` SET business_group_credit_limit = {} WHERE name = "{}" """.format(0,self.name))
		return

	self.customer_credit_limit_available = credit_limit - terpakai
	if self.business_group:
		self.business_group_credit_limit_available = credit_limit - terpakai
	else:
		self.business_group_credit_limit_available = 0
	# self.business_group_credit_limit_available = credit_limit - terpakai
	frappe.db.sql(""" UPDATE `tabCustomer` SET customer_credit_limit_available = {}, business_group_credit_limit_available = {} WHERE name = "{}" """.format(credit_limit - terpakai,credit_limit - terpakai,self.name))

	self.db_update()
	frappe.db.commit()


@frappe.whitelist()
def api_return_overdue_customer(customer):
	overdue_percentage = 0
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

	return overdue_percentage


@frappe.whitelist()
def api_return_customer_credit_limit(customer):
	customer_credit_limit_available = 0
	if customer:
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

	return customer_credit_limit_available


@frappe.whitelist()
def api_return_naming_series_so():
	return frappe.db.sql(""" SELECT `value` FROM `tabProperty Setter` WHERE field_name = "naming_series"
		AND doc_type = "Sales Order" and name LIKE "%options%" """)

@frappe.whitelist()
def api_return_naming_series_pe():
	return frappe.db.sql(""" SELECT `value` FROM `tabProperty Setter` WHERE field_name = "naming_series"
		AND doc_type = "Payment Entry" and name LIKE "%options%" """)

@frappe.whitelist()
def api_return_naming_series_customer():
	return frappe.db.sql(""" SELECT `value` FROM `tabProperty Setter` WHERE field_name = "naming_series"
		AND doc_type = "Customer" and name LIKE "%options%" """)


@frappe.whitelist()
def api_calculate_ste_qty(item_code, warehouse):
	ste_draft_qty = 0
	projected_qty = 0
	final_projected_qty = 0

	if item_code and warehouse:
		warehouse = warehouse
		item_code = item_code

		ste_check = frappe.db.sql(""" 
			SELECT sum(IFNULL(qty,0)) AS qty_booking 
			FROM `tabStock Entry Detail` std
			JOIN `tabStock Entry` ste ON ste.name = std.parent  
			WHERE std.item_code = "{}"
			AND std.s_warehouse = "{}"
			AND ste.docstatus = 0
			AND ste.workflow_state != 'Rejected'
		""".format(item_code,warehouse),as_dict=1)

		ste_qty = 0
		if len(ste_check) > 0:
			for row_ste in ste_check:
				ste_qty = row_ste.qty_booking

		ste_draft_qty = ste_qty

		bin_check = frappe.db.sql(""" SELECT projected_qty FROM `tabBin` WHERE item_code = "{}" and warehouse = "{}" """.format(item_code,warehouse),as_dict=1)
		bin_qty = 0
		if len(bin_check) > 0:
			for row_bin in bin_check:
				bin_qty = row_bin.projected_qty

		projected_qty = bin_qty

		final_projected_qty = flt(row.projected_qty) - flt(row.ste_draft_qty)
		
	return {"STE Draft Qty":ste_draft_qty,"Projected Qty":projected_qty,"Final Projected Qty":final_projected_qty}

#tidak di pakai karena di SO sudah ada hpp , check di JS

@frappe.whitelist()
def check_message(self,method):
	if self.docstatus == 0:
		message = ""
		for row in self.items:
			item_doc = frappe.get_doc("Item", row.item_code)
			if item_doc.is_stock_item:
				if frappe.utils.flt(row.net_rate,2) < frappe.utils.flt(row.valuation_rate,2):
					message += "Item {} - {} in row {} is below valuation rate.<br>".format(row.item_code,row.item_name,row.idx)

		if self.overdue_percentage > 10:
			message += "Customer {} has {}% overdue invoice.<br>".format(self.customer, self.overdue_percentage)

		if self.customer_credit_limit_available or self.customer_credit_limit_available == 0:
			if self.customer_credit_limit_available - self.total < 0:
				message += "Customer {} doesn't have enough credit limit as Sales Order total is {} and credit limit available is {}.<br>".format(self.customer, self.total, self.customer_credit_limit_available)			
		if message != "":
			frappe.msgprint(message)

		# if self.workflow_state == "Rejected":
		# 	self.rejected = "Yes"
		# 	self.db_update()
		# else:
		# 	self.rejected = "No"
		# 	self.db_update()
@frappe.whitelist()
def check_hpp(self,method):
	self.is_below_hpp = "No"
	for row in self.items:
		if row.warehouse and row.item_code:
			tanggal = self.transaction_date
			warehouse = row.warehouse
			item_code = row.item_code

			ste_check = frappe.db.sql(""" 

			SELECT valuation_rate 
			FROM `tabStock Ledger Entry` sle
			
			WHERE sle.item_code = "{}"
			AND sle.warehouse = "{}"
			AND sle.docstatus = 1
			AND sle.posting_date <= "{}"
			and sle.is_cancelled = "No"
			and sle.valuation_rate > 0
			ORDER BY posting_date DESC, posting_time DESC
			LIMIT 1
			
			""".format(item_code,warehouse,tanggal),as_dict=1)

			sle_rate = 0
			if len(ste_check) > 0:
				for row_ste in ste_check:
					sle_rate = row_ste.valuation_rate
					row.valuation_rate = row_ste.valuation_rate
					row.gross_profit = flt(((row.base_net_rate - row.valuation_rate) * row.stock_qty), self.precision("amount", row))

			if flt(sle_rate,2) > flt(row.base_net_rate,2):
				self.is_below_hpp = "Yes"




@frappe.whitelist()
def debug_check_hpp():
	list_so = frappe.db.sql(""" SELECT parent FROM `tabSales Order Item` WHERE parent = "SO-1-23-01-00001" GROUP BY parent""")
	for baris_so in list_so:
		self = frappe.get_doc("Sales Order", baris_so[0])
		for row in self.items:
			if row.warehouse and row.item_code:
				tanggal = self.transaction_date
				warehouse = row.warehouse
				item_code = row.item_code

				ste_check = frappe.db.sql(""" 

				SELECT valuation_rate 
				FROM `tabStock Ledger Entry` sle
				
				WHERE sle.item_code = "{}"
				AND sle.warehouse = "{}"
				AND sle.docstatus = 1
				AND sle.posting_date <= "{}"
				and sle.is_cancelled = "No"
				and sle.valuation_rate > 0
				ORDER BY posting_date DESC, posting_time DESC
				LIMIT 1
				""".format(item_code,warehouse,tanggal),as_dict=1,debug=1)

				sle_rate = 0
				if len(ste_check) > 0:
					for row_ste in ste_check:
						sle_rate = row_ste.valuation_rate
						row.valuation_rate = row_ste.valuation_rate
						row.gross_profit = flt(((row.base_rate - row.valuation_rate) * row.stock_qty), self.precision("amount", row))
						row.db_update()

				if flt(sle_rate,2) > flt(row.base_net_rate,2):
					self.is_below_hpp = "Yes"
					self.db_update()


		print(self.name)
@frappe.whitelist()
def calculate_ste_qty(self,method):
	for row in self.items:
		if row.warehouse and row.item_code:
			tanggal = self.transaction_date
			warehouse = row.warehouse
			item_code = row.item_code

			ste_check = frappe.db.sql(""" 

			SELECT sum(IFNULL(qty,0)) AS qty_booking 
			FROM `tabStock Entry Detail` std
			JOIN `tabStock Entry` ste ON ste.name = std.parent  
			WHERE std.item_code = "{}"
			AND std.s_warehouse = "{}"
			AND ste.docstatus = 0
			AND ste.posting_date <= "{}"
			""".format(item_code,warehouse,tanggal),as_dict=1)
			ste_qty = 0
			if len(ste_check) > 0:
				for row_ste in ste_check:
					ste_qty = row_ste.qty_booking

			row.ste_draft_qty = ste_qty
			row.final_projected_qty = flt(row.projected_qty) - flt(row.ste_draft_qty)
			
			if flt(row.qty) + flt(row.ste_draft_qty) > row.projected_qty :
				frappe.msgprint("Qty SO ({}) + STE Draft Qty ({}) for item {} - {} with Warehouse {} is higher than Projected Qty ({}) .<br> ".format(row.qty,row.ste_draft_qty,row.item_code,row.item_name,row.warehouse,row.projected_qty))

@frappe.whitelist()
def validasi_ste_booking(self,method):
	for row in self.items:
		if row.warehouse and row.item_code:
			tanggal = self.transaction_date
			warehouse = row.warehouse
			item_code = row.item_code

			ste_check = frappe.db.sql(""" 

			SELECT sum(IFNULL(qty,0)) AS qty_booking 
			FROM `tabStock Entry Detail` std
			JOIN `tabStock Entry` ste ON ste.name = std.parent  
			WHERE std.item_code = "{}"
			AND std.s_warehouse = "{}"
			AND ste.docstatus = 0
			AND ste.posting_date <= "{}"
			""".format(item_code,warehouse,tanggal),as_dict=1)

			dn_check = frappe.db.sql(""" 

			SELECT sum(IFNULL(qty,0)) AS qty_booking 
			FROM `tabDelivery Note Item` std
			JOIN `tabDelivery Note` ste ON ste.name = std.parent  
			WHERE std.item_code = "{}"
			AND std.warehouse = "{}"
			AND ste.docstatus = 0
			AND ste.posting_date <= "{}"
			and ste.workflow_state != "Rejected"
			""".format(item_code,warehouse,tanggal),as_dict=1)
			
			ste_qty = 0
			if len(ste_check) > 0:
				for row_ste in ste_check:
					ste_qty = row_ste.qty_booking

			dn_qty = 0
			if len(dn_check) > 0:
				for row_dn in dn_check:
					dn_qty = row_dn.qty_booking

			row.ste_draft_qty = ste_qty
			row.final_projected_qty = flt(row.actual_qty) - flt(row.ste_draft_qty)
			
			if flt(row.qty) + flt(row.ste_draft_qty) > row.actual_qty :
				frappe.throw("Qty SO ({}) + STE Draft Qty ({}) for item {} - {} with Warehouse {} is higher than Actual Qty ({}) .<br> ".format(row.qty,row.ste_draft_qty,row.item_code,row.item_name,row.warehouse,row.actual_qty))

@frappe.whitelist()
def all_calculate_ste_qty():

	query_so = frappe.db.sql(""" SELECT name FROM `tabSales Order`  """)

	for baris_so in query_so:
		self = frappe.get_doc("Sales Order", baris_so[0])

		for row in self.items:
			row.final_projected_qty = row.projected_qty - row.ste_draft_qty
			print(self.name)
			print("{}={}-{}".format(row.final_projected_qty, row.projected_qty, row.ste_draft_qty))
			row.db_update()

@frappe.whitelist()
def get_sales_tax():
	return frappe.db.sql(""" SELECT name FROM `tabSales Taxes and Charges Template` WHERE disabled = 0 and default_tax = 1 LIMIT 1 """, as_dict=1)
@frappe.whitelist()
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
		print(outstanding_based_on_gle)
		return outstanding_based_on_gle 

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
	print("ASD".format((outstanding_based_on_gle)))
	return outstanding_based_on_gle
		
