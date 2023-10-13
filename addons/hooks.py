from . import __version__ as app_version

app_name = "addons"
app_title = "Addons"
app_publisher = "das"
app_description = "addons"
app_icon = "octicon octicon-file-directory"
app_color = "blue"
app_email = "das@gmail.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/addons/css/addons.css"
# app_include_js = "/assets/addons/js/addons.js"

# include js, css files in header of web template
# web_include_css = "/assets/addons/css/addons.css"
# web_include_js = "/assets/addons/js/addons.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "addons/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
"Purchase Order" : "public/js/custom_purchase_order.js",
"Purchase Receipt" : "public/js/custom_purchase_receipt.js",
"Purchase Invoice" : "public/js/custom_purchase_invoice.js",
"Sales Order" : "public/js/custom_sales_order.js",
"Delivery Note" : "public/js/custom_delivery_note.js",
"Sales Invoice" : "public/js/custom_sales_invoice.js",
"Material Request" : "public/js/custom_material_request.js",

"Item" : "public/js/custom_item.js",
"Customer" : "public/js/custom_customer.js",
"Stock Entry" : "public/js/custom_stock_entry.js",
"Journal Entry" : "public/js/custom_journal_entry.js",

"Payment Entry" : "public/js/custom_payment_entry.js",

"Asset" : "public/js/custom_asset.js",
"Buying Settings" : "public/js/custom_buying_settings.js",
"Selling Settings" : "public/js/custom_selling_settings.js",

"Budget" : "public/js/custom_budget.js",
"Payroll Entry" : "public/js/custom_payroll_entry.js",
"Landed Cost Voucher" : "public/js/custom_landed_cost_voucher.js",
"Sales Taxes and Charges Template" : "public/js/custom_sales_taxes_and_charges.js",
"Purchase Taxes and Charges Template" : "public/js/custom_purchase_taxes_and_charges.js",
"Stock Reconciliation" : "public/js/custom_stock_reconciliation.js",
"Company": "public/js/custom_company.js",
"Employee Advance": "public/js/custom_employee_advance.js",
"Expense Claim": "public/js/custom_expense_claim.js",
"Expense Claim Type":"public/js/custom_expense_claim_type.js",

"Exchange Rate Revaluation":"public/js/custom_exchange_rate_revaluation.js"

}
doctype_list_js = {
# "doctype" : "public/js/doctype_list.js"
"Material Request" : "public/js/custom_list_mr.js"
}
fixtures = [
    "Custom Field"
]
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "addons.install.before_install"
# after_install = "addons.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "addons.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	# "Stock Ledger Entry": {
	# 	"after_insert": "addons.patch_ste.patch_sle"
	# },
	"Stock Opname": {
		"before_submit": "addons.addons.doctype.stock_opname.stock_opname.buat_ste"
	},
	"Sales Invoice": {
		"onload": "addons.custom_standard.custom_sales_invoice.onload_sales_invoice",
		"validate": ["addons.custom_standard.custom_sales_invoice.change_dn_date","addons.custom_standard.custom_global.check_tax_non_tax_by_document","addons.custom_standard.custom_global.calculate_total_prorate","addons.custom_standard.custom_tax_method.check_tax_from_sales_order_inv","addons.custom_standard.custom_sales_invoice.check_branch","addons.custom_standard.custom_global.set_discount_no_tax","addons.custom_standard.custom_sales_invoice.check_dn_date","addons.custom_standard.custom_sales_invoice.override_get_gl_entries","addons.custom_standard.custom_sales_invoice.assuming_customer","addons.custom_standard.custom_sales_invoice.get_auto_account_retur","addons.custom_standard.custom_sales_invoice.apply_hs_code","addons.custom_standard.custom_tax_method.check_tax_sales","addons.custom_standard.custom_sales_invoice.pure_calculate"],
		"before_submit": ["addons.custom_standard.custom_sales_invoice.validate_gl","addons.custom_standard.custom_sales_invoice.override_get_gl_entries","addons.custom_standard.custom_sales_invoice.update_asset","addons.custom_standard.custom_sales_invoice.pure_calculate"],
		"before_cancel":"addons.custom_standard.custom_sales_invoice.update_asset_cancel",
		"on_submit": ["addons.custom_standard.custom_sales_invoice.onload_sales_invoice","addons.custom_standard.view_ledger_create.create_view_ledger_sales_invoice"],
		"autoname": "addons.custom_standard.custom_sales_invoice.custom_autoname_sales_invoice",
		"before_insert": ["addons.custom_standard.custom_global.check_draft_mr","addons.custom_standard.custom_sales_invoice.change_dn_date"],
		"on_cancel": "addons.custom_standard.view_ledger_create.delet_view_ledger"
	},
	"Material Request": {
		"validate": ["addons.custom_standard.custom_material_request.calculate_total","addons.custom_standard.custom_material_request.check_ps_approver","addons.custom_standard.custom_global.check_tax_non_tax"],
		"before_submit" : "addons.custom_standard.custom_material_request.set_requested",
		"before_cancel" : "addons.custom_standard.custom_material_request.set_requested_cancel",
		"autoname": "addons.custom_standard.custom_material_request.custom_autoname_baru",
		"onload": "addons.custom_standard.custom_material_request.onload_calculate_total",
		"on_submit":"addons.custom_standard.custom_material_request.create_mr_log"
	},
	"Memo Ekspedisi": {
		"autoname": "addons.custom_method.custom_autoname_document_je",
		"before_cancel": "addons.custom_standard.custom_stock_entry.cancel_flag"
	},
	"Berita Acara Komplain": {
		"autoname": "addons.custom_method.custom_autoname_document_bak"
	},
	"Supplier": {
		"validate": "addons.custom_method.cek_supplier_short_code"
	},
	"Landed Cost Voucher": {
		"autoname": "addons.custom_method.custom_autoname_document_lcv",
		"on_submit": "addons.custom_standard.custom_purchase_receipt.lcv_after_submit"
	},
	"Purchase Order": {
		"before_insert": ["addons.custom_standard.custom_purchase_order.initial_outstanding_qty","addons.custom_standard.custom_global.check_draft_mr"],
		"onload": ["addons.custom_standard.custom_purchase_order.validate_nomor_rq"],
		"validate": ["addons.custom_standard.custom_tax_method.check_tax_sales","addons.custom_standard.custom_global.check_tax_non_tax_by_document","addons.custom_standard.custom_global.check_tax_non_tax","addons.custom_standard.custom_purchase_order.cek_template_dan_tax","addons.custom_standard.custom_purchase_order.validate_nomor_rq","addons.custom_standard.custom_global.check_tanggal_mr","addons.custom_standard.custom_purchase_order.benerno_rate","addons.custom_standard.custom_purchase_order.calculate_difference_rate","addons.custom_standard.custom_purchase_order.check_tax_purchase","addons.custom_standard.custom_purchase_order.get_sq"],
		"autoname": "addons.custom_standard.custom_purchase_order.custom_autoname_po",
		"before_submit": "addons.custom_standard.custom_purchase_order.update_pod",
		"before_cancel": "addons.custom_standard.custom_purchase_order.cancel_flag"
	},
	"Purchase Receipt": {
		"on_submit": "addons.custom_standard.custom_purchase_receipt.update_outstanding_qty_po",
		"before_submit":["addons.custom_standard.custom_purchase_receipt.submitted_rate","addons.custom_standard.custom_purchase_receipt.auto_je_retur","addons.custom_standard.custom_purchase_receipt.override_get_gl_entries"],
		"on_cancel": "addons.custom_standard.custom_purchase_receipt.update_outstanding_qty_po",
		"validate": ["addons.custom_standard.custom_tax_method.check_tax_sales","addons.custom_standard.custom_purchase_receipt.check_uom","addons.custom_standard.custom_global.check_tax_non_tax_by_document","addons.custom_standard.custom_global.check_tanggal_po","addons.custom_standard.custom_purchase_order.check_tax_purchase"],
		"autoname": "addons.custom_standard.custom_purchase_receipt.custom_autoname_pr",
		"before_cancel": ["addons.custom_standard.custom_purchase_receipt.cek_stock_re","addons.custom_standard.custom_purchase_receipt.cek_je"],
		"before_insert": "addons.custom_standard.custom_global.check_draft_mr",
		"onload": "addons.custom_standard.custom_purchase_receipt.custom_onload"
		
	},
	"Purchase Invoice":{
		"autoname": "addons.custom_standard.custom_purchase_invoice.custom_autoname_pinv",
		"before_submit": ["addons.custom_standard.custom_purchase_invoice.override_get_gl_entries","addons.custom_standard.custom_purchase_invoice.get_lcv","addons.custom_standard.custom_sales_invoice.pure_calculate"],
		"validate": ["addons.custom_standard.custom_tax_method.check_tax_sales","addons.custom_standard.custom_global.check_tax_non_tax_by_document","addons.custom_standard.custom_global.calculate_total_prorate","addons.custom_standard.custom_purchase_order.cek_template_dan_tax","addons.custom_standard.custom_sales_invoice.pure_calculate","addons.custom_standard.custom_global.set_discount_no_tax","addons.custom_standard.custom_purchase_invoice.validate_asset_account","addons.custom_standard.custom_purchase_order.check_tax_purchase","addons.custom_standard.custom_purchase_invoice.apply_cost_center","addons.custom_standard.custom_purchase_invoice.validate_lcv","addons.custom_standard.custom_purchase_invoice.get_auto_account_retur","addons.custom_standard.custom_purchase_invoice.get_stock_received_but_not_billed"],
		"before_cancel": "addons.custom_standard.custom_stock_entry.cancel_flag",
		"on_cancel":["addons.custom_standard.custom_purchase_invoice.validate_cancel","addons.custom_standard.view_ledger_create.delet_view_ledger"],
		"before_insert": "addons.custom_standard.custom_global.check_draft_mr",
		"on_submit": "addons.custom_standard.view_ledger_create.create_view_ledger_purchase_invoice",
		"onload": "addons.custom_standard.custom_purchase_invoice.onload_purchase_invoice",
	},
	"Payment Entry":{
		"validate" : ["addons.custom_standard.custom_global.check_tanggal_pe","addons.custom_standard.custom_tax_method.check_tax_payment","addons.custom_standard.custom_payment_entry.override_validate"],
		"autoname": "addons.custom_method.custom_autoname_document_je",
		"onload": "addons.custom_standard.custom_payment_entry.custom_onload",
		"before_insert": "addons.custom_standard.custom_global.check_draft_payment_entry",
		"on_cancel": "addons.custom_standard.custom_payment_entry.delete_cancelled_entry",
	},
	"Stock Entry": {
		"before_insert": ["addons.custom_standard.custom_stock_entry.remove_dependency","addons.custom_standard.custom_global.check_item_terbooking","addons.custom_standard.custom_global.remove_generated"],
		"validate": ["addons.custom_standard.custom_stock_entry.validate_ste_stock","addons.custom_standard.custom_stock_entry.pasang_rk_account","addons.custom_standard.custom_stock_entry.cek_document_sync","addons.custom_standard.custom_tax_method.check_tax_sales","addons.custom_standard.custom_global.check_item_terbooking","addons.custom_standard.custom_stock_entry.set_accounting_dimension","addons.custom_standard.custom_stock_entry.set_tonase","addons.custom_standard.custom_stock_entry.custom_distribute_additional_costs_transfer","addons.custom_standard.custom_journal_entry.check_tax_naming"],
		"before_submit": ["addons.custom_standard.custom_stock_entry.cancel_period_flag","addons.custom_standard.custom_stock_entry.overwrite_on_submit","addons.custom_standard.custom_stock_entry.buat_ste_log"],
		"autoname": ["addons.custom_standard.custom_stock_entry.autoname_document_ste"],
		"before_cancel": ["addons.custom_standard.custom_stock_entry.cancel_flag","addons.custom_standard.custom_stock_entry.cancel_period_flag","addons.custom_standard.custom_purchase_receipt.cek_stock_re"],
		"onload": "addons.custom_standard.custom_stock_entry.onload_transfer",
		"on_cancel": ["addons.custom_standard.custom_stock_entry.pasang_mr_untuk_not_ready","addons.custom_standard.custom_stock_entry.pasang_persen_transfer","addons.custom_standard.view_ledger_create.delet_view_ledger"],
		"on_submit": ["addons.custom_standard.custom_stock_entry.pasang_mr_untuk_not_ready","addons.custom_standard.custom_stock_entry.pasang_persen_transfer"]

	},
	# "Warehouse": {
	# 	"validate": ["addons.custom_standard.custom_warehouse.check_dua_cabang","addons.custom_standard.custom_warehouse.check_transit_pusat"]
	# },
	"Journal Entry": {
		"validate": ["addons.custom_standard.custom_journal_entry.cek_jedp","addons.custom_standard.custom_journal_entry.overwrite_validate","addons.custom_standard.custom_journal_entry.check_tax_naming"],
		"autoname": "addons.custom_method.custom_autoname_document_je",
		"before_cancel": ["addons.custom_standard.custom_journal_entry.before_cancel_remove_dn","addons.custom_standard.custom_journal_entry.before_cancel_check_rk_tools"],
		"on_trash": "addons.custom_standard.custom_journal_entry.before_cancel_remove_dn",
		"before_insert": ["addons.custom_standard.custom_global.remove_generated","addons.custom_standard.custom_global.check_draft_journal_entry"],
	},
	"Journal Entry Tax": {
		"autoname": "addons.custom_method.custom_autoname_document_je",
	},
	
	"GIAS Asset": {
		"autoname": "addons.custom_method.custom_autoname_document_asset"
	},
	"Employee Advance": {
		"autoname": "addons.custom_method.custom_autoname_document_je",
		"onload": "addons.custom_standard.custom_employee_advance.overwrite_set_status",
		"validate": "addons.custom_standard.custom_employee_advance.check_exchange_rate"
	},
	"Expense Claim":{

		"validate": ["addons.custom_standard.custom_expense_claim.check_advance","addons.custom_standard.custom_expense_claim.calculate_nilai_jasa","addons.custom_standard.custom_journal_entry.check_tax_naming"],
		"autoname": "addons.custom_method.custom_autoname_document_je",
		"onload" : ["addons.custom_standard.custom_expense_claim.custom_set_status_onload","addons.custom_standard.custom_expense_claim.onload_validate"],
		"before_insert": "addons.custom_standard.custom_global.remove_generated",
		"on_submit": "addons.custom_standard.view_ledger_create.create_view_ledger_expense_claim",
		"before_cancel":"addons.custom_standard.custom_expense_claim.cek_ada_je",
		"on_cancel": "addons.custom_standard.view_ledger_create.delet_view_ledger"
	},
	"Sales Order":{
	#,"addons.custom_standard.custom_sales_order.check_hpp" - removed
		"onload" : ["addons.custom_standard.custom_sales_order.calculate_overdue_percentage","addons.custom_standard.custom_sales_order.check_message"],
		"autoname": "addons.custom_method.custom_autoname_document_so",
		"validate": ["addons.custom_standard.custom_sales_order.isi_pt","addons.custom_standard.custom_sales_order.check_tanggal","addons.custom_standard.custom_global.check_tax_non_tax","addons.custom_standard.custom_tax_method.check_tax_sales","addons.custom_standard.custom_sales_order.render_print_data","addons.custom_standard.custom_sales_order.check_hpp"],
		"on_update": "addons.custom_standard.custom_sales_order.calculate_ste_qty",
		# "before_insert" : ["addons.custom_standard.custom_sales_order.calculate_overdue_percentage","addons.custom_standard.custom_sales_order.validasi_ste_booking"],
		"before_submit" : ["addons.custom_standard.custom_sales_order.calculate_overdue_percentage"],
		"before_insert" : ["addons.custom_standard.custom_sales_order.calculate_overdue_percentage"],
		"on_cancel":"addons.custom_standard.custom_sales_order.remove_dn_link_reject",
		"before_cancel": "addons.custom_standard.custom_sales_order.cancel_flag"
	},
	"Customer":{
		"validate": ["addons.custom_standard.custom_customer.assign_business_group","addons.custom_standard.custom_customer.set_sinv"],
		"onload": ["addons.custom_standard.custom_customer.get_max_credit_limit","addons.custom_standard.custom_sales_order.calculate_credit_limit_available"]
	},
	"Delivery Note":{
		"validate": ["addons.custom_standard.custom_global.check_tax_non_tax_by_document","addons.custom_standard.custom_delivery_note.check_tanggal","addons.custom_standard.custom_tax_method.check_tax_from_sales_order","addons.custom_standard.custom_tax_method.check_tax_sales","addons.custom_standard.custom_global.check_item_terbooking","addons.custom_standard.custom_delivery_note.pusat_check_so"],
		"before_submit":"addons.custom_standard.custom_delivery_note.auto_je_retur",
		"before_insert": ["addons.custom_standard.custom_global.check_item_terbooking","addons.custom_standard.custom_global.check_draft_mr"],
		"autoname": "addons.custom_method.custom_autoname_document_je"
	},
	"Stock Reconciliation":{
		"validate": "addons.custom_standard.custom_tax_method.check_tax_sales",
		"autoname": "addons.custom_method.custom_autoname_document_je"
	},
	"Cash Request":{
		"validate": "addons.custom_standard.custom_tax_method.check_tax_cash_request",
		"autoname": "addons.custom_method.custom_autoname_document_je",
		"before_insert": "addons.custom_standard.custom_global.check_draft_cash_request"
	},
	"STE Log":{
		"after_insert": ["addons.custom_standard.custom_stock_entry.create_ste_resolve","addons.custom_standard.custom_stock_entry.create_ste_resolve_issue"]
	},
	"JE Log":{
		"after_insert": ["addons.addons.doctype.rk_tools.rk_tools.create_je_resolve"]
	},
	"MR BLKP Log":{
		"after_insert": ["addons.custom_standard.custom_material_request.create_mr_resolve"]
	},
	"GIAS Asset Movement": {
		"autoname": "addons.custom_method.custom_autoname_document_no_naming_series"
	},
	"Auto Repeat": {
		"autoname": "addons.custom_method.custom_autoname_document_no_naming_series"
	},
	"Asset Value Adjustment": {
		"autoname": "addons.custom_method.custom_autoname_document_no_naming_series"
	},
	"BOM": {
		"autoname": "addons.custom_method.custom_autoname_document_no_naming_series"
	},
	"Item":{
		"autoname": "addons.custom_method.custom_autoname_item",
		"validate": ["addons.custom_standard.custom_item.check_item_group","addons.custom_standard.custom_item.check_uoms"]
	},
	"Item Group":{
		"autoname": "addons.custom_standard.custom_item_group.apply_to_child_item"
	},
	"Event Sync Log":{
		"before_insert": "addons.custom_standard.custom_stock_entry.update_null_removed",
		"validate": "addons.custom_standard.custom_stock_entry.update_null_removed",
	},
	"Asset":{
		"validate": "addons.custom_standard.custom_asset.check_prec",
		"on_submit": "addons.custom_standard.custom_asset.masukin_prec",
		"onload": "addons.custom_standard.custom_asset.masukin_cabang"
	},
	"Event Producer":{
		"validate": "addons.custom_standard.custom_global.access",
	}
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	# "all": [
	# 	"addons.tasks.all"
	# ],
	"cron":{
		"0/15 * * * *":["addons.custom_method.lakukan_pull_node","addons.custom_standard.view_ledger_create.gelondongan_gl_custom"],
		"0 1 * * *":["addons.addons.doctype.gias_asset.gias_asset.make_je_log_asset","addons.addons.doctype.gias_asset.gias_asset.make_book_asset"]
	},
	 "daily": [
		"addons.custom_method.cancel_prepared_report"
	# 	"addons.addons.doctype.gias_asset.gias_asset.make_book_asset",	
	],
	# "hourly": [
	# 	"addons.tasks.hourly"
	# ],
	# "weekly": [
	# 	"addons.tasks.weekly"
	# ]
	# "monthly": [
	# 	"addons.tasks.monthly"
	# ]
}

# Testing
# -------

# before_tests = "addons.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
	"frappe.event_streaming.doctype.event_producer.event_producer.pull_from_node": "addons.custom_standard.custom_stock_entry.custom_pull_from_node",
	"frappe.event_streaming.doctype.event_producer.event_producer.new_event_notification": "addons.custom_standard.custom_stock_entry.custom_new_event_notification",
	"erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry": "addons.custom_standard.custom_payment_entry.custom_get_payment_entry",
	"erpnext.selling.doctype.sales_order.sales_order.make_delivery_note": "addons.custom_standard.custom_sales_order.custom_make_delivery_note",
	"erpnext.accounts.doctype.journal_entry.journal_entry.get_account_balance_and_party_type" : "addons.custom_standard.custom_journal_entry.get_account_balance_and_party_type_custom",
	"erpnext.accounts.doctype.payment_entry.payment_entry.get_reference_details" : "addons.custom_standard.custom_payment_entry.custom_get_reference_details"
}

# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
override_doctype_dashboards = {
	"Purchase Invoice": "addons.custom_standard.custom_purchase_invoice.get_dashboard_data"
}

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]
jenv = {
	'filters':['ubah_ke_huruf:addons.custom_method.ubah_ke_huruf']
}


# User Data Protection
# --------------------

user_data_fields = [
	{
		"doctype": "{doctype_1}",
		"filter_by": "{filter_by}",
		"redact_fields": ["{field_1}", "{field_2}"],
		"partial": 1,
	},
	{
		"doctype": "{doctype_2}",
		"filter_by": "{filter_by}",
		"partial": 1,
	},
	{
		"doctype": "{doctype_3}",
		"strict": False,
	},
	{
		"doctype": "{doctype_4}"
	}
]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"addons.auth.validate"
# ]

