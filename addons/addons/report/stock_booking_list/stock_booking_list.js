// Copyright (c) 2022, das and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Stock Booking List"] = {
	"filters": [
		{
			"fieldname":"warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse"
		},
		{
			"fieldname":"item_group_parent",
			"label": __("Item Group Parent"),
			"fieldtype": "Link",
			"options": "Item Group",
			"get_query": function() {
				return {
					filters: { 
						'is_group': 1 
					}
				}
			}
		},
		{
			"fieldname":"item_group_child",
			"label": __("Item Group Child"),
			"fieldtype": "Link",
			"options": "Item Group",
			"get_query": function() {
				if(frappe.query_report.get_filter_value("item_group_parent")){
					return {
						filters: { 
							'is_group': 0 ,
							'parent_item_group': String(frappe.query_report.get_filter_value("item_group_parent"))
						}
					}
				}
				else{
					return {
						filters: { 
							'is_group': 0 
						}
					}
				}
				
			}
		},
	]
};
