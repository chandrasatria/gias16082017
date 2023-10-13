
frappe.ui.form.on("Purchase Receipt", {
	validate : function(frm){
		$.each(frm.doc.items, function(i,d){
			d.warehouse=frm.doc.set_warehouse
		})
	},
	onload: function(frm) {
		frm.set_query("account_head", "taxes", function() {
			return {
				filters: {
					"is_group": 0,
					"disabled": 0
				}
			}
		});
	},
	setup: function(frm){
		if(frappe.user_roles.indexOf("Purchase Receipt Without Value") > -1 && frappe.user.name != "Administrator"){
			
			var df = frappe.meta.get_docfield("Purchase Receipt Item", "rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Purchase Receipt Item", "base_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Purchase Receipt Item", "price_list_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Purchase Receipt Item", "base_price_list_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Purchase Receipt Item", "amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Purchase Receipt Item", "base_amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Purchase Receipt Item", "net_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Purchase Receipt Item", "base_net_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Purchase Receipt Item", "net_amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Purchase Receipt Item", "base_net_amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Purchase Receipt Item", "submitted_rate",frm.doc.name);
			if(df){
				df.hidden = 1;	
			}
			var df = frappe.meta.get_docfield("Purchase Receipt Item", "billed_amt",frm.doc.name);
			df.hidden = 1;
			
			frm.set_df_property("total", "hidden", 1);
			frm.set_df_property("nt_sc_break_section", "hidden", 1);
			frm.set_df_property("taxes_section", "hidden", 1);
			frm.set_df_property("totals", "hidden", 1);
			frm.set_df_property("base_net_total", "hidden", 1);
			frm.set_df_property("total_taxes_and_charges", "hidden", 1);
			frm.set_df_property("grand_total", "hidden", 1);
			frm.set_df_property("rounding_adjustment", "hidden", 1);
			frm.set_df_property("rounded_total", "hidden", 1);
			frm.set_df_property("in_words", "hidden", 1);
			frm.set_df_property("sec_tax_breakup", "hidden", 1);
			
			frm.refresh_fields();
		}
		else{
			var df = frappe.meta.get_docfield("Purchase Receipt Item", "rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Purchase Receipt Item", "base_rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Purchase Receipt Item", "price_list_rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Purchase Receipt Item", "base_price_list_rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Purchase Receipt Item", "amount",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Purchase Receipt Item", "base_amount",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Purchase Receipt Item", "net_rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Purchase Receipt Item", "base_net_rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Purchase Receipt Item", "net_amount",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Purchase Receipt Item", "base_net_amount",frm.doc.name);
			df.hidden = 0;
			
			var df = frappe.meta.get_docfield("Purchase Receipt Item", "submitted_rate",frm.doc.name);
			if(df){
				df.hidden = 0;	
			}
			var df = frappe.meta.get_docfield("Purchase Receipt Item", "billed_amt",frm.doc.name);
			df.hidden = 0;
			frm.set_df_property("total", "hidden", 0);
			frm.set_df_property("nt_sc_break_section", "hidden", 0);
			frm.set_df_property("taxes_section", "hidden", 0);
			frm.set_df_property("totals", "hidden", 0);
			frm.set_df_property("base_net_total", "hidden", 0);
			frm.set_df_property("total_taxes_and_charges", "hidden", 0);
			frm.set_df_property("grand_total", "hidden", 0);
			frm.set_df_property("rounding_adjustment", "hidden", 0);
			frm.set_df_property("rounded_total", "hidden", 0);
			frm.set_df_property("in_words", "hidden", 0);
			frm.set_df_property("sec_tax_breakup", "hidden", 0);
			frm.refresh_fields();
		}	
	}
	
})

cur_frm.cscript['Make Stock Entry'] = function() {
	frappe.model.open_mapped_doc({
		method: "addons.custom_standard.custom_purchase_receipt.make_stock_entry",
		frm: cur_frm,
	})
}
