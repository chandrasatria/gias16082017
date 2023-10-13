// Copyright (c) 2022, das and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["View Ledger by Detail"] = {
	"filters": [
		{
			"fieldname":"nama_account",
			"label": __("Nama Account"),
			"fieldtype": "Link",
			"options": "Account",
			
			"get_query": function() {
				return {
					filters: { 'is_group': 0 }
				}
			}
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
	]
};
