// Copyright (c) 2023, das and contributors
// For license information, please see license.txt

function add_filter_item(frm) {
	cur_frm.set_query("item_code", "items", function() {
	    return {
	        filters: {
	            "is_stock_item": 1,
	            "tax_or_non_tax": frm.doc.tax_or_non_tax
	        }    
	    };
	}),
	cur_frm.refresh_fields();
}

frappe.ui.form.on('Stock Opname', {
	
	tax_or_non_tax: function(frm){
		add_filter_item(frm)
	},	

	onload: function(frm) {
		if(!frm.doc.posting_time){
			cur_frm.set_value('posting_time', frappe.datetime.now_time());	
		}
		
		frm.add_fetch("item_code", "item_name", "item_name");

		// end of life
		add_filter_item(frm)

		frm.set_query("batch_no", "items", function(doc, cdt, cdn) {
			var item = locals[cdt][cdn];
			return {
				filters: {
					'item': item.item_code
				}
			};
		});

		if (frm.doc.company) {
			erpnext.queries.setup_queries(frm, "Warehouse", function() {
				return erpnext.queries.warehouse(frm.doc);
			});
		}

		if (!frm.doc.expense_account) {
			frm.trigger("set_expense_account");
		}

		erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
	},

	company: function(frm) {
		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
	},
	posting_date: function(frm) {
		frm.trigger("set_valuation_rate_and_qty_for_all_items");
	},

	posting_time: function(frm) {
		frm.trigger("set_valuation_rate_and_qty_for_all_items");
	},

	set_posting_time: function(frm){
		if(frm.doc.set_posting_time == 1){
			frm.set_df_property("posting_date", "read_only", 0);
			frm.set_df_property("posting_time", "read_only", 0);
			frm.refresh_fields()
		}
		else{
			frm.set_df_property("posting_date", "read_only", 1);
			frm.set_df_property("posting_time", "read_only", 1);
			frm.refresh_fields()
		}
	},
	set_valuation_rate_and_qty_for_all_items: function(frm) {
		frm.doc.items.forEach(row => {
			frm.events.set_valuation_rate_and_qty(frm, row.doctype, row.name);
		});
	},

	set_valuation_rate_and_qty: function(frm, cdt, cdn) {
		var d = frappe.model.get_doc(cdt, cdn);

		if(d.item_code && d.warehouse) {
			frappe.call({
				method: "addons.addons.doctype.stock_opname.stock_opname.get_stock_balance_for",
				args: {
					item_code: d.item_code,
					warehouse: d.warehouse,
					posting_date: frm.doc.posting_date,
					posting_time: frm.doc.posting_time,
					batch_no: d.batch_no
				},
				callback: function(r) {
					frappe.model.set_value(cdt, cdn, "qty",0);
					frappe.model.set_value(cdt, cdn, "valuation_rate", r.message.rate);
					frappe.model.set_value(cdt, cdn, "current_qty", r.message.qty);
					frappe.model.set_value(cdt, cdn, "current_valuation_rate", r.message.rate);
					frappe.model.set_value(cdt, cdn, "current_amount", r.message.rate * r.message.qty);
					frappe.model.set_value(cdt, cdn, "amount", r.message.rate * r.message.qty);
					frappe.model.set_value(cdt, cdn, "current_serial_no", r.message.serial_nos);

					frappe.model.set_value(cdt, cdn, "qty_ste_issue_draft", r.message.ste_draft_qty);
					frappe.model.set_value(cdt, cdn, "qty_dn_issue_draft", r.message.dn_draft_qty);
					frappe.model.set_value(cdt, cdn, "qty_stock_booking", r.message.dn_draft_qty + r.message.ste_draft_qty);


					if (frm.doc.purpose == "Stock Reconciliation") {
						frappe.model.set_value(cdt, cdn, "serial_no", r.message.serial_nos);
					}
				}
			});
		}
	},
	set_item_code: function(doc, cdt, cdn) {
		var d = frappe.model.get_doc(cdt, cdn);
		if (d.barcode) {
			frappe.call({
				method: "erpnext.stock.get_item_details.get_item_code",
				args: {"barcode": d.barcode },
				callback: function(r) {
					if (!r.exe){
						frappe.model.set_value(cdt, cdn, "item_code", r.message);
					}
				}
			});
		}
	},
	set_amount_quantity: function(doc, cdt, cdn) {
		var d = frappe.model.get_doc(cdt, cdn);
		
		frappe.model.set_value(cdt, cdn, "amount", (flt(d.current_qty) + flt(d.qty)) * flt(d.valuation_rate));
		frappe.model.set_value(cdt, cdn, "quantity_difference", (flt(d.current_qty) + flt(d.qty)));
		frappe.model.set_value(cdt, cdn, "amount_difference", flt(d.amount) - flt(d.current_amount));
	
	},
});

frappe.ui.form.on("Stock Opname Items", {
	barcode: function(frm, cdt, cdn) {
		frm.events.set_item_code(frm, cdt, cdn);
	},

	warehouse: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if (child.batch_no) {
			frappe.model.set_value(child.cdt, child.cdn, "batch_no", "");
		}

		frm.events.set_valuation_rate_and_qty(frm, cdt, cdn);
	},

	item_code: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if (child.batch_no) {
			frappe.model.set_value(cdt, cdn, "batch_no", "");
		}

		frm.events.set_valuation_rate_and_qty(frm, cdt, cdn);
	},

	batch_no: function(frm, cdt, cdn) {
		frm.events.set_valuation_rate_and_qty(frm, cdt, cdn);
	},

	qty: function(frm, cdt, cdn) {
		frm.events.set_amount_quantity(frm, cdt, cdn);
	},

	valuation_rate: function(frm, cdt, cdn) {
		frm.events.set_amount_quantity(frm, cdt, cdn);
	},

	serial_no: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];

		if (child.serial_no) {
			const serial_nos = child.serial_no.trim().split('\n');
			frappe.model.set_value(cdt, cdn, "qty", serial_nos.length);
		}
	}

});
