cur_frm.add_fetch("ship_to","alamat_dan_kontak","ship_to_address")

frappe.ui.form.on("Sales Invoice","discount_bertingkat",function(doc){
	if (cur_frm.doc.discount_bertingkat){
		var res = String(cur_frm.doc.discount_bertingkat).split("+");
		var add_discount = 0;
		
		for (var i in res){
			var row = res[i];
			if (isNaN(res[i])==false) {
				var rowFloat = parseFloat(res[i]);
				add_discount = 100 - ((100-rowFloat)*(100-add_discount)/100);
			}
		}
		
		cur_frm.set_value("additional_discount_percentage",add_discount);
		cur_frm.cscript.calculate_taxes_and_totals();
		refresh_field("additional_discount_percentage");
	}
});

frappe.ui.form.on('Sales Invoice', {
	onload: function(frm) {
			
		frm.set_query("account_head", "taxes", function() {
			return {
				filters: {
					"is_group": 0,
					"disabled": 0
				}
			}
		});
		frm.set_df_property("tax_id", "hidden", 1);
		if(frappe.user_roles.indexOf("Edit Date Sales Invoice") > -1){
			frm.set_df_property("posting_date", "read_only", 0);
			frm.set_df_property("set_posting_time", "hidden", 0);
			frm.doc.set_posting_time = 1
		}
		else{
			frm.set_df_property("posting_date", "read_only", 1);	
			frm.set_df_property("set_posting_time", "hidden", 1);
			frm.doc.set_posting_time = 0
		}
		
	},
	// setup: function(frm) {
			
	// 	if(frappe.user_roles.indexOf("Edit Date Sales Invoice") > -1){
	// 		frm.set_df_property("posting_date", "read_only", 0);
	// 	}
	// 	else{
	// 		frm.set_df_property("posting_date", "read_only", 1);	
	// 	}
		
	// },


	before_load:function(frm) {
		if(frm.doc.__islocal){
			if(frm.doc.tax_or_non_tax == "Tax"){
				frappe.call({
					method: "addons.custom_standard.custom_sales_order.get_sales_tax",
					
					callback: function (data) {
						if(data.message.length > 0){
							frm.doc.taxes_and_charges = data.message[0]["name"]
							frm.trigger("taxes_and_charges")
							frm.set_df_property("taxes", "hidden", 0);
							frm.set_df_property("taxes_and_charges", "hidden", 0);
							frm.refresh_fields()
						} 
					}
				})
			}
		}
		if(frm.doc.tax_or_non_tax == "Non Tax"){
			frm.doc.taxes_and_charges = ""
			frm.doc.taxes = []
			frm.set_df_property("taxes", "hidden", 1);
			frm.set_df_property("taxes_and_charges", "hidden", 1);
			frm.refresh_fields()
		}
	},
	tax_or_non_tax: function(frm) {
		if(frm.doc.__islocal){
			if(frm.doc.tax_or_non_tax == "Tax"){
				frappe.call({
					method: "addons.custom_standard.custom_sales_order.get_sales_tax",
					
					callback: function (data) {
						if(data.message.length > 0){
							frm.doc.taxes_and_charges = data.message[0]["name"]
							frm.trigger("taxes_and_charges")
							frm.set_df_property("taxes", "hidden", 0);
							frm.set_df_property("taxes_and_charges", "hidden", 0);
							frm.refresh_fields()
						} 
					}
				})
			}
			else{
				frm.doc.taxes_and_charges = ""
				frm.doc.taxes = []
				frm.refresh_fields()
			}
		}
		if(frm.doc.tax_or_non_tax == "Non Tax"){
			frm.doc.taxes_and_charges = ""
			frm.doc.taxes = []
			frm.set_df_property("taxes", "hidden", 1);
			frm.set_df_property("taxes_and_charges", "hidden", 1);
			frm.refresh_fields()
		}
	},
	refresh(frm) {
		if(frm.doc.docstatus == 1){
			cur_frm.doc.__onload.make_payment_via_journal_entry=null;	
		}
	    cur_frm.set_query("invoice_dp","dp_list", function() {
		    return {
				query: "addons.custom_standard.custom_sales_invoice.get_dp_invoice",
				filters:{customer : frm.doc.customer}
			}
	    });
	    cur_frm.set_query("faktur_pajak", function() {
		    return {
				filters:{
					"tahun_penggunaan": String(cur_frm.doc.posting_date).split("-")[0],
					"is_used" : 0
				}
			}
	    });
	},
	validate: function(frm) {
		if(frm.doc.discount_2){
			var variable = 100
			for(var baris in frm.doc.taxes){
				if(frm.doc.taxes[baris].included_in_print_rate == 1){
					variable = variable + frm.doc.taxes[baris].rate
				}
			}

			var total_price_list = 0
			for(var row in frm.doc.items){
				var baris = frm.doc.items[row]
				if(baris.price_list_rate == 0 && baris.rate > 0){
					var pakai_rate = 1
				}
			}

			for(var row in frm.doc.items){
				var baris = frm.doc.items[row]
				if(pakai_rate == 1){
					total_price_list += baris.rate * baris.qty
				}
				else{
					total_price_list += baris.price_list_rate * baris.qty
				}
			}
			if(total_price_list != 0){
				for(var row in frm.doc.items){
					var baris = frm.doc.items[row]
					if(pakai_rate == 0){
						baris.percent_value = baris.price_list_rate / total_price_list * 100
					}
					else{
						baris.percent_value = baris.rate / total_price_list * 100						
					}
					baris.prorate_discount = baris.percent_value / 100 * (frm.doc.discount_2 / (variable / 100))
				}
			}
			frm.doc.discount_amount = (frm.doc.discount_2 ) + frm.doc.nilai_invoice_dp  + frm.doc.nilai_discount_manual 
			frm.trigger("discount_amount")
			cur_frm.refresh_fields()
		}
		else{
			frm.doc.discount_2 = 0
			var total_price_list = 0
			for(var row in frm.doc.items){
				var baris = frm.doc.items[row]
				if(baris.price_list_rate == 0 && baris.rate > 0){
					var pakai_rate = 1
				}
			}

			for(var row in frm.doc.items){
				var baris = frm.doc.items[row]
				if(pakai_rate == 1){
					total_price_list += baris.rate * baris.qty
				}
				else{
					total_price_list += baris.price_list_rate * baris.qty
				}
			}
			if(total_price_list != 0){
				for(var row in frm.doc.items){
					var baris = frm.doc.items[row]
					if(pakai_rate == 0){
						baris.percent_value = baris.price_list_rate / total_price_list * 100
					}
					else{
						baris.percent_value = baris.rate / total_price_list * 100						
					}
					baris.prorate_discount = baris.percent_value / 100 * frm.doc.discount_2
				}
			}
			frm.doc.discount_amount = frm.doc.discount_2 + frm.doc.nilai_invoice_dp  + frm.doc.nilai_discount_manual 
			frm.trigger("discount_amount")
			cur_frm.refresh_fields()
		}
	},
	discount_2: function(frm) {
		if(frm.doc.discount_2){
			var variable = 100
			for(var baris in frm.doc.taxes){
				if(frm.doc.taxes[baris].included_in_print_rate == 1){
					variable = variable + frm.doc.taxes[baris].rate
				}
			}

			var total_price_list = 0
			for(var row in frm.doc.items){
				var baris = frm.doc.items[row]
				if(baris.price_list_rate == 0 && baris.rate > 0){
					var pakai_rate = 1
				}
			}

			for(var row in frm.doc.items){
				var baris = frm.doc.items[row]
				if(pakai_rate == 1){
					total_price_list += baris.rate * baris.qty
				}
				else{
					total_price_list += baris.price_list_rate * baris.qty
				}
			}
			
			if(total_price_list != 0){
				for(var row in frm.doc.items){
					var baris = frm.doc.items[row]
					if(pakai_rate == 0){
						baris.percent_value = baris.price_list_rate / total_price_list * 100
					}
					else{
						baris.percent_value = baris.rate / total_price_list * 100						
					}
					baris.prorate_discount = baris.percent_value / 100 * (frm.doc.discount_2 / (variable / 100))
				}
			}
			frm.doc.discount_amount = (frm.doc.discount_2) + frm.doc.nilai_invoice_dp  + frm.doc.nilai_discount_manual 
			frm.trigger("discount_amount")
			cur_frm.refresh_fields()
		}
		else{
			frm.doc.discount_2 = 0
			var total_price_list = 0
			var total_price_list = 0
			for(var row in frm.doc.items){
				var baris = frm.doc.items[row]
				if(baris.price_list_rate == 0 && baris.rate > 0){
					var pakai_rate = 1
				}
			}

			for(var row in frm.doc.items){
				var baris = frm.doc.items[row]
				if(pakai_rate == 1){
					total_price_list += baris.rate * baris.qty
				}
				else{
					total_price_list += baris.price_list_rate * baris.qty
				}
			}
			if(total_price_list != 0){
				for(var row in frm.doc.items){
					var baris = frm.doc.items[row]
					if(pakai_rate == 0){
						baris.percent_value = baris.price_list_rate / total_price_list * 100
					}
					else{
						baris.percent_value = baris.rate / total_price_list * 100						
					}
					baris.prorate_discount = baris.percent_value / 100 * frm.doc.discount_2
				}
			}
			frm.doc.discount_amount = frm.doc.discount_2 + frm.doc.nilai_invoice_dp  + frm.doc.nilai_discount_manual 
			frm.trigger("discount_amount")
			cur_frm.refresh_fields()
		}
	},
	/*invoice_dp(frm){
		if(frm.doc.invoice_dp){
			frappe.call({
				method: "addons.custom_standard.custom_sales_invoice.get_net_total_dp",
				args: {
					invoice : frm.doc.invoice_dp
				},
				callback: function (data) {
					if(data['message']){
						frm.doc.nilai_invoice_dp = data['message']

						if(frm.doc.nilai_discount_manual){
							frm.doc.discount_amount = frm.doc.nilai_invoice_dp  + frm.doc.nilai_discount_manual 
						}
						else{
							frm.doc.discount_amount = frm.doc.nilai_invoice_dp  + 0
						}
						frm.trigger("discount_amount")
						frm.refresh_fields()
					} 
				}
			})
		}
	},*/
	nilai_discount_manual(frm){
		if(frm.doc.nilai_discount_manual){
			if(frm.doc.nilai_invoice_dp){
				frm.doc.discount_amount = frm.doc.discount_2 + frm.doc.nilai_invoice_dp  + frm.doc.nilai_discount_manual 
			}
			else{
				frm.doc.discount_amount = frm.doc.discount_2 + 0  + frm.doc.nilai_discount_manual 
			}
			console.log(frm.doc.discount_amount)
			frm.trigger("discount_amount")
			frm.refresh_fields()
		}
	},
});
frappe.ui.form.on('Sales Invoice Item', {
	price_list_rate(frm,cdt,cdn){
		var baris = locals[cdt][cdn]
		if (baris.price_list_rate){
			baris.rate = baris.price_list_rate
			frm.refresh_fields()
		}
			
	}
});

frappe.ui.form.on('Sales Invoice DP', {
	invoice_dp(frm,cdt,cdn){
		var total=0
		$.each(frm.doc.dp_list,  function(i,  d) {
			total+=d.nilai_invoice_dp;
		});
		frm.doc.nilai_invoice_dp = total;
		if(frm.doc.nilai_discount_manual){
			frm.doc.discount_amount = frm.doc.discount_2 + frm.doc.nilai_invoice_dp  + frm.doc.nilai_discount_manual 
		}
		else{
			frm.doc.discount_amount = frm.doc.discount_2 + frm.doc.nilai_invoice_dp  + 0
		}
		frm.trigger("discount_amount")
		frm.refresh_fields()
	},
	dp_list_remove: function(frm){
		var total=0
		$.each(frm.doc.dp_list,  function(i,  d) {
			total+=d.nilai_invoice_dp;
		});
		frm.doc.nilai_invoice_dp = total;
		if(frm.doc.nilai_discount_manual){
			frm.doc.discount_amount = frm.doc.discount_2 +frm.doc.nilai_invoice_dp  + frm.doc.nilai_discount_manual 
		}
		else{
			frm.doc.discount_amount = frm.doc.discount_2 + frm.doc.nilai_invoice_dp  + 0
		}
		frm.trigger("discount_amount")
		frm.refresh_fields()
	}
});

cur_frm.add_fetch("customer","nomor_awalan_pajak","nomor_awalan_pajak")