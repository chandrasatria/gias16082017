cur_frm.add_fetch("ship_to", "alamat_dan_kontak", "ship_to_address");

frappe.ui.form.on("Purchase Invoice", {
  
  refresh: function (frm) {
    cur_frm.set_query("invoice_dp","dp_list", function() {
        return {
        query: "addons.custom_standard.custom_purchase_invoice.get_dp_invoice",
        filters:{supplier : frm.doc.supplier}
      }
      });
    if (cur_frm.doc.docstatus == 1 && cur_frm.doc.workflow_state == "Approved") {
      frm.add_custom_button(__("Create Cash Request"), function () {
        // var data = [];
        // var item = {
        //   name: cur_frm.doc.name,
        //   supplier: cur_frm.doc.supplier,
        //   amount: cur_frm.doc.grand_total,
        //   remarks: cur_frm.doc.remarks,
        //   terms: cur_frm.doc.terms,
        // };
        // data.push(item);
        frappe
          .xcall("addons.custom_standard.custom_purchase_invoice.gen_cr", {
            name: cur_frm.doc.name,
            supplier: cur_frm.doc.supplier,
            amount: cur_frm.doc.rounded_total,
            grand_total: cur_frm.doc.grand_total,
            remarks: cur_frm.doc.remarks,
            terms: cur_frm.doc.terms,
            taxorno: cur_frm.doc.tax_or_non_tax,
            branch: cur_frm.doc.branch,
            cost_center: cur_frm.doc.cost_center,
          })
          .then((cash_request) => {
            frappe.model.sync(cash_request);
            frappe.set_route("Form", cash_request.doctype, cash_request.name);
          });

        /*frappe.xcall({
			        method: "addons.custom_standard.custom_purchase_invoice.gen_cr",
			        args:{
			            "name": cur_frm.doc.name,
			            "supplier": cur_frm.doc.supplier
			        },
			        callback:function(hasil){
			        	console.log(hasil)
			            frappe.model.sync(hasil);
						frappe.set_route('Form', hasil.doctype, hasil.name);
			        }
			    })*/
      });
    }

    cur_frm.set_query("no_lcv", function() {
      return {
        filters:{
          "docstatus" : 1
          //"no_pinv": ""
        }
      }
    });
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
        total_price_list += baris.price_list_rate * baris.qty
        if(baris.price_list_rate == 0 && baris.rate > 0){
          var pakai_rate = 1
        }
      }

      if(pakai_rate == 1){
        for(var row in frm.doc.items){
          var baris = frm.doc.items[row]
          total_price_list += baris.rate * baris.qty
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
      frm.doc.discount_amount = frm.doc.discount_2 + frm.doc.nilai_invoice_dp  
      frm.trigger("discount_amount")
      cur_frm.refresh_fields()
    }
    else{
      frm.doc.discount_2 = 0
      var total_price_list = 0
      for(var row in frm.doc.items){
        var baris = frm.doc.items[row]
        total_price_list += baris.price_list_rate * baris.qty
        if(baris.price_list_rate == 0 && baris.rate > 0){
          var pakai_rate = 1
        }
      }

      if(pakai_rate == 1){
        for(var row in frm.doc.items){
          var baris = frm.doc.items[row]
          total_price_list += baris.rate * baris.qty
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
      frm.doc.discount_amount = frm.doc.discount_2 + frm.doc.nilai_invoice_dp  
      frm.trigger("discount_amount")
      cur_frm.refresh_fields()
    }
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
        total_price_list += baris.price_list_rate * baris.qty
        if(baris.price_list_rate == 0 && baris.rate > 0){
          var pakai_rate = 1
        }
      }

      if(pakai_rate == 1){
        for(var row in frm.doc.items){
          var baris = frm.doc.items[row]
          total_price_list += baris.rate * baris.qty
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
      frm.doc.discount_amount = frm.doc.discount_2 + frm.doc.nilai_invoice_dp  
      frm.trigger("discount_amount")
      cur_frm.refresh_fields()
    }
    else{
      frm.doc.discount_2 = 0
      var total_price_list = 0
      for(var row in frm.doc.items){
        var baris = frm.doc.items[row]
        total_price_list += baris.price_list_rate * baris.qty
        if(baris.price_list_rate == 0 && baris.rate > 0){
          var pakai_rate = 1
        }
      }

      if(pakai_rate == 1){
        for(var row in frm.doc.items){
          var baris = frm.doc.items[row]
          total_price_list += baris.rate * baris.qty
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
      frm.doc.discount_amount = frm.doc.discount_2 + frm.doc.nilai_invoice_dp  
      frm.trigger("discount_amount")
      cur_frm.refresh_fields()
    }
  },
  add_global_discount(frm) {
    if (frm.doc.discount_global_amount) {
      frappe.db.get_value("Company", cur_frm.doc.company, "discount_global_account").then(function (e) {
        if (e.message["discount_global_account"]) {
          var d = frappe.model.add_child(cur_frm.doc, "Purchase Taxes and Charges", "taxes");

          d.category = "Total";
          d.add_or_deduct = "Add";
          d.charge_type = "Actual";
          d.account_head = e.message["discount_global_account"];
          d.description = e.message["discount_global_account"];
          d.tax_amount = frm.doc.discount_global_amount * -1;
          d.global_discount = "Yes";
          frappe.call({
            method: "addons.custom_standard.custom_global.onload_dimension",
            args: {
              company: frm.doc.company,
            },
            freeze: true,
            callback: function (hasil) {
              if (hasil) {
                for (var baris in hasil.message) {
                  if (hasil.message[baris].default_dimension) {
                    d.branch = hasil.message[baris].default_dimension;
                  }
                }
              }
            },
          });
          cur_frm.trigger("discount_amount");
          cur_frm.refresh_fields();
        }
      });
    }
  },
  faktur_pajak(frm) {
    if (frm.doc.faktur_pajak) {
      let isnum = /^\d+$/.test(frm.doc.faktur_pajak);
      if (isnum) {
        if (frm.doc.faktur_pajak.length == 13) {
          frm.doc.faktur_pajak = frm.doc.faktur_pajak.substring(0, 3) + "-" + frm.doc.faktur_pajak.slice(3);
          frm.doc.faktur_pajak = frm.doc.faktur_pajak.substring(0, 6) + "." + frm.doc.faktur_pajak.slice(6);
          frm.refresh_fields();
        }
      }
    }
  },

  onload: function (frm) {
    frm.set_query("account_head", "taxes", function () {
      return {
        filters: {
          is_group: 0,
          disabled: 0,
        },
      };
    });
  },
});
frappe.ui.form.on('Purchase Invoice DP', {
  invoice_dp(frm,cdt,cdn){
    var total=0
    $.each(frm.doc.dp_list,  function(i,  d) {
      total+=d.nilai_invoice_dp;
    });
    frm.doc.nilai_invoice_dp = total;
     frm.doc.discount_amount = frm.doc.discount_2 + frm.doc.nilai_invoice_dp  
    
    frm.trigger("discount_amount")
    frm.refresh_fields()
  },
  dp_list_remove: function(frm){
    var total=0
    $.each(frm.doc.dp_list,  function(i,  d) {
      total+=d.nilai_invoice_dp;
    });
    frm.doc.nilai_invoice_dp = total;
     frm.doc.discount_amount = frm.doc.discount_2 + frm.doc.nilai_invoice_dp  
    
    frm.trigger("discount_amount")
    frm.refresh_fields()
  }
});

