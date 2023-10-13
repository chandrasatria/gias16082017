frappe.ui.form.on("Cash Request", {
  refresh: function (frm) {
    if (frm.doc.__islocal) {
      if (!frm.doc.requestor) {
        frm.doc.requestor = frappe.session.user;
        frm.doc.requestor_name = frappe.session.user_fullname;
        
        frm.refresh_fields();
      }
      frappe.call({
        method: "addons.addons.doctype.cash_request.cash_request.get_default_cash_bank",
        args: {},
        callback: function (r) {
          frm.doc.cash_or_bank_account = r.message;
          frm.refresh_fields();
        },
      });
      cur_frm.set_query("document", "list_invoice", function (doc) {
        return {
          filters: [
            ["Purchase Invoice", "currency", "=", "IDR"],
            ["Purchase Invoice", "status", "!=", "Paid"],
            ["Purchase Invoice", "outstanding_amount", ">=", "0"],
            ["Purchase Invoice", "docstatus", "=", 1],
            ["Purchase Invoice", "is_return", "=", 0],
            ["Purchase Invoice", "tax_or_non_tax", "=", frm.doc.tax_or_non_tax],
          ],
        };
      });
      frm.refresh_fields();
    }

    if (frm.doc.supplier) {
      cur_frm.set_query("document", "list_invoice", function (doc) {
        
          return {
            filters: [
              ["Purchase Invoice", "supplier", "=", frm.doc.supplier],
              ["Purchase Invoice", "currency", "=", frm.doc.currency],
              ["Purchase Invoice", "status", "!=", "Paid"],
              ["Purchase Invoice", "outstanding_amount", ">=", "0"],
              ["Purchase Invoice", "docstatus", "=", 1],
              ["Purchase Invoice", "is_return", "=", 0],
              ["Purchase Invoice", "tax_or_non_tax", "=", frm.doc.tax_or_non_tax],
            ],
          };
        
      });
      frm.refresh_fields();
      if (!frm.doc.currency) {
        frm.doc.currency = "IDR";
      }
      if (frm.doc.currency != "IDR") {
        cur_frm.set_query("account", "list_tax_and_charges", function (doc) {
          return {
            filters: [["Account", "account_currency", "=", frm.doc.currency]],
          };
        });
      } else {
        cur_frm.set_query("account", "list_tax_and_charges", function (doc) {
          return {
            filters: [["Account", "account_currency", "in", ["IDR", ""]]],
          };
        });
      }
    }
    if (frm.doc.docstatus == 1) {
      frm.add_custom_button(__("Make Journal Entry"), () =>
        frappe
          .xcall("addons.addons.doctype.cash_request.cash_request.make_journal_entry", {
            cash_request: frm.doc.name,
            supplier: cur_frm.doc.supplier,
            tax_or_non_tax: cur_frm.doc.tax_or_non_tax,
          })
          .then((journal_entry) => {
            console.log(journal_entry);
            frappe.model.sync(journal_entry);
            frappe.set_route("Form", journal_entry.doctype, journal_entry.name);
          })
      );
    }
    else if(frm.doc.docstatus == 0 && !frm.doc.__islocal && frm.doc.workflow_state != "Rejected" && frappe.user.has_role("Cancel Documents")) {
      frm.add_custom_button(__("Close to Rejected"), () =>
        frappe
          .xcall("addons.addons.doctype.cash_request.cash_request.go_to_rejected", {
            cash_request: frm.doc.name,
          }).then((name) => {
            cur_frm.refresh()
          })
      );
    }
  },
  make_journal_entry: function (frm) {
    frappe.model.open_mapped_doc({
      method: "addons.addons.doctype.cash_request.cash_request.make_journal_entry",
      frm: frm,
    });
  },
  validate: function (frm) {
    if (frm.doc.__islocal) {
      frm.doc.completed = 0;
    }
    if (frm.doc.docstatus){
      var grand_total=0
      var total_jasa=0;
      $.each(frm.doc.list_invoice,  function(i,  d) {
        grand_total+=d.amount;
        total_jasa+=nilai_jasa;
      });
      $.each(frm.doc.list_tax_and_charges,  function(i,  d) {
        if(d.type=="Percentage"){
         d.amount=d.rate*total_jasa
        }
        grand_total+=d.amount;
        if(d.amount==0){
          msgprint('Amount Tax Tidak boleh Kosong');
          validated = false;
        }
      });
      frm.doc.grand_total=grand_total;
    }
  },
  supplier: function (frm) {
    if (frm.doc.supplier) {
      var check = 1
      for(var row in frm.doc.list_invoice){
        if(String(frm.doc.list_invoice[row].desc) != "" && frm.doc.list_invoice[row].desc){
           if(String(frm.doc.list_invoice[row].desc) != String(frm.doc.supplier)){
            frm.doc.supplier = frm.doc.list_invoice[row].desc
            frm.doc.supplier_name = frm.doc.list_invoice[row].desc
            frm.refresh_fields()
            frappe.msgprint("List Invoice is using Supplier "+frm.doc.list_invoice[row].desc+". Value is reverted.")
            check = 0
          }
        }
       
      }
      if(check==1){
        frappe.call({
          method: "addons.addons.doctype.cash_request.cash_request.get_supplier_currency",
          args: {
            supplier: frm.doc.supplier,
            posting_date: frm.doc.posting_date,
          },
          freeze: true,
          freeze_message: __("Fetching exchange rates ..."),
          callback: function (r) {
            frm.doc.currency_exchange = r.message[0];
            frm.doc.currency = r.message[1];
            console.log(r.message[0])
            if (frm.doc.currency_exchange == 1) {
              frm.doc.currency == "IDR";
            }
            frm.refresh_fields();
          },
        });
        
          cur_frm.set_query("document", "list_invoice", function (doc) {
            return {
              filters: [
                ["Purchase Invoice", "supplier", "=", frm.doc.supplier],
                ["Purchase Invoice", "currency", "=", frm.doc.currency],
                ["Purchase Invoice", "status", "!=", "Paid"],
                ["Purchase Invoice", "outstanding_amount", ">=", "0"],
                ["Purchase Invoice", "docstatus", "=", 1],
                ["Purchase Invoice", "is_return", "=", 0],
                ["Purchase Invoice", "tax_or_non_tax", "=", frm.doc.tax_or_non_tax],
              ],
            };
          });
          frm.refresh_fields();
        
        
        if (frm.doc.currency != "IDR" && frm.doc.currency) {
          cur_frm.set_query("account", "list_tax_and_charges", function (doc) {
            return {
              filters: [["Account", "account_currency", "=", frm.doc.currency]],
            };
          });
        } else {
          frm.doc.currency == "IDR";
          frm.refresh_fields();
          cur_frm.set_query("account", "list_tax_and_charges", function (doc) {
            return {
              filters: [["Account", "account_currency", "in", ["IDR", ""]]],
            };
          });
        }
      }
    }
  },
  currency: function (frm) {
    if (frm.doc.supplier) {
      
        cur_frm.set_query("document", "list_invoice", function (doc) {
          return {
            filters: [
              ["Purchase Invoice", "supplier", "=", frm.doc.supplier],
              ["Purchase Invoice", "currency", "=", frm.doc.currency],
              ["Purchase Invoice", "status", "!=", "Paid"],
              ["Purchase Invoice", "outstanding_amount", ">=", "0"],
              ["Purchase Invoice", "docstatus", "=", 1],
              ["Purchase Invoice", "is_return", "=", 0],
              ["Purchase Invoice", "tax_or_non_tax", "=", frm.doc.tax_or_non_tax],
            ],
          };
        });
        frm.refresh_fields();
      
      if (frm.doc.currency != "IDR" && frm.doc.currency) {
        cur_frm.set_query("account", "list_tax_and_charges", function (doc) {
          return {
            filters: [["Account", "account_currency", "=", frm.doc.currency]],
          };
        });
      } else {
        frm.doc.currency == "IDR";
        frm.refresh_fields();
        cur_frm.set_query("account", "list_tax_and_charges", function (doc) {
          return {
            filters: [["Account", "account_currency", "in", ["IDR", ""]]],
          };
        });
      }
    }
  },
  // type_pembelian: function (frm) {
  //   if (frm.doc.supplier) {
  //     cur_frm.set_query("document", "list_invoice", function (doc) {
  //       if(frm.doc.type_pembelian){
  //         return {
  //           filters: [
  //             ["Purchase Invoice", "supplier", "=", frm.doc.supplier],
  //             ["Purchase Invoice", "currency", "=", frm.doc.currency],
  //             ["Purchase Invoice", "status", "!=", "Paid"],
  //             ["Purchase Invoice", "outstanding_amount", ">=", "0"],
  //             ["Purchase Invoice", "docstatus", "=", 1],
  //             ["Purchase Invoice", "is_return", "=", 0],
  //             ["Purchase Invoice", "tax_or_non_tax", "=", frm.doc.tax_or_non_tax],
  //             ["Purchase Invoice", "type_pembelian", "=", frm.doc.type_pembelian]
  //           ],
  //         };
  //       }
  //       else{
  //         return {
  //           filters: [
  //             ["Purchase Invoice", "supplier", "=", frm.doc.supplier],
  //             ["Purchase Invoice", "currency", "=", frm.doc.currency],
  //             ["Purchase Invoice", "status", "!=", "Paid"],
  //             ["Purchase Invoice", "outstanding_amount", ">=", "0"],
  //             ["Purchase Invoice", "docstatus", "=", 1],
  //             ["Purchase Invoice", "is_return", "=", 0],
  //             ["Purchase Invoice", "tax_or_non_tax", "=", frm.doc.tax_or_non_tax],
  //           ],
  //         };
  //       }
  //     });
  //     frm.refresh_fields();
  //   }
  //   else{

  //     cur_frm.set_query("document", "list_invoice", function (doc) {
  //       if(frm.doc.type_pembelian){
  //         return {
  //           filters: [
  //             ["Purchase Invoice", "currency", "=", frm.doc.currency],
  //             ["Purchase Invoice", "status", "!=", "Paid"],
  //             ["Purchase Invoice", "outstanding_amount", ">=", "0"],
  //             ["Purchase Invoice", "docstatus", "=", 1],
  //             ["Purchase Invoice", "is_return", "=", 0],
  //             ["Purchase Invoice", "tax_or_non_tax", "=", frm.doc.tax_or_non_tax],
  //             ["Purchase Invoice", "type_pembelian", "=", frm.doc.type_pembelian]
  //           ],
  //         };
  //       }
  //       else{
  //         return {
  //           filters: [
  //             ["Purchase Invoice", "currency", "=", frm.doc.currency],
  //             ["Purchase Invoice", "status", "!=", "Paid"],
  //             ["Purchase Invoice", "outstanding_amount", ">=", "0"],
  //             ["Purchase Invoice", "docstatus", "=", 1],
  //             ["Purchase Invoice", "is_return", "=", 0],
  //             ["Purchase Invoice", "tax_or_non_tax", "=", frm.doc.tax_or_non_tax],
  //           ],
  //         };
  //       }
  //     });
  //     frm.refresh_fields();
    
  //   }
  // },
  tax_and_charges_template: function (frm) {
    if (frm.doc.tax_and_charges_template) {
      frappe.call({
        method: "addons.addons.doctype.cash_request.cash_request.get_tax_charges_for_cash_request",
        args: {
          tax_and_charges_template: frm.doc.tax_and_charges_template,
        },
        freeze: true,
        callback: function (r) {
          for (var row in r.message) {
            var baris = r.message[row];
            console.log(baris);
            var d = frappe.model.add_child(cur_frm.doc, "Cash Request Taxes and Charges", "list_tax_and_charges");
            d.account = baris.account_head;
            d.rate = baris.rate;
            var total_amount = 0;
            for (var jumlah_baris in frm.doc.list_invoice) {
              total_amount += frm.doc.list_invoice[jumlah_baris].nilai_jasa;
            }
            d.amount = (total_amount * baris.rate) / 100;
            d.account_currency = baris.account_currency;
            if (!d.amount) {
              d.amount = 0;
            }
            d.type = "Percentage";
          }
          cur_frm.refresh_fields();
        },
      });
    }
  },
});
frappe.ui.form.on("Cash Request Taxes and Charges", {
  rate: function (frm, cdt, cdn) {
    var baris = locals[cdt][cdn];
    if (baris.rate) {
      var total_amount = 0;
      for (var jumlah_baris in frm.doc.list_invoice) {
        total_amount += frm.doc.list_invoice[jumlah_baris].nilai_jasa;
      }
    }
    baris.amount = (total_amount * baris.rate) / 100;
    var total = 0
      for (var jumlah_baris in frm.doc.list_invoice) {
        total += frm.doc.list_invoice[jumlah_baris].amount;
      }
      for (var row_pajak in frm.doc.list_tax_and_charges) {
        total += frm.doc.list_tax_and_charges[row_pajak].amount;
      }
      frm.doc.grand_total = total
      frm.refresh_fields()
  },
   amount:function(frm,cdt,cdn){
     var total = 0
      for (var jumlah_baris in frm.doc.list_invoice) {
        total += frm.doc.list_invoice[jumlah_baris].amount;
      }
      for (var row_pajak in frm.doc.list_tax_and_charges) {
        total += frm.doc.list_tax_and_charges[row_pajak].amount;
      }
      frm.doc.grand_total = total
      frm.refresh_fields()
  }
});

frappe.ui.form.on("Cash Request Table", {
  document: function (frm, cdt, cdn) {
    
    var baris = locals[cdt][cdn];
     frappe.call({
       method: "addons.addons.doctype.cash_request.cash_request.get_sisa_invoice",
       args:{
         pinv : baris.document
       },
       freeze:true,
       callback: function(r){
          if (baris.document) {
            frappe.call({
              method: "addons.addons.doctype.cash_request.cash_request.check_pinv_is_approved",
              args: {
                pinv: baris.document,
              },
              freeze: true,
              callback: function (r) {
                if (r.message == "No") {
                  baris.document = "";

                  frm.refresh_fields();
                  frappe.msgprint("PINV yang belum submit/approved tidak bisa dibuat Cash Request.");
                }
              },
            });
          }
          console.log(r)
          baris.amount = r["message"][0]
          baris.grand_total = r["message"][1]

          for (var row_pajak in frm.doc.list_tax_and_charges) {
            var baris_tax = frm.doc.list_tax_and_charges[row_pajak];
            if (baris_tax.rate) {
              var total_amount = 0;
              for (var jumlah_baris in frm.doc.list_invoice) {
                total_amount += frm.doc.list_invoice[jumlah_baris].amount;
              }
              baris_tax.amount = (total_amount * baris_tax.rate) / 100;
            }
          }
          if (baris.document) {
            frappe.call({
              method: "addons.addons.doctype.cash_request.cash_request.check_pinv_has_retur",
              args: {
                pinv: baris.document,
              },
              freeze: true,
              callback: function (r) {
                if (r.message == "Yes") {
                  baris.document = "";

                  frm.refresh_fields();
                  frappe.msgprint("PINV yang ada retur tidak bisa dibuat Cash Request.");
                }
              },
            });
            var total = 0
            for (var jumlah_baris in frm.doc.list_invoice) {
              total += frm.doc.list_invoice[jumlah_baris].amount;
            }
            for (var row_pajak in frm.doc.list_tax_and_charges) {
              total += frm.doc.list_tax_and_charges[row_pajak].amount;
            }
            frm.doc.grand_total = total
            console.log(total)
            frm.refresh_fields()

          }
          frappe.db.get_value("Purchase Invoice", baris.document, "terms").then((data) => {
            console.log(data.message.terms);
            if(data.message.terms){
               if (cur_frm.doc.memo !== "<p></p>" && cur_frm.doc.memo) {
                  cur_frm.doc.memo += "<br>";
                  cur_frm.doc.memo += data.message.terms;
                  cur_frm.refresh_fields();
                } else {
                  cur_frm.doc.memo = data.message.terms;
                  cur_frm.refresh_fields();
                }
            }
           
          });
          frappe.db.get_value("Purchase Invoice", baris.document, "supplier").then((data) => {
            console.log(data.message.supplier);
            if(data.message.supplier){
              baris.desc =data.message.supplier 
              cur_frm.refresh_fields();
                
            }
           
          });
          frappe.db.get_value("Purchase Invoice", baris.document, "remark").then((data) => {
            console.log(data.message.remark);
            if(data.message.remark){
              
               baris.user_remarks = data.message.remark
                cur_frm.refresh_fields();
            }
           
          });

       }
     })


    
  },
  nilai_jasa: function (frm, cdt, cdn) {
    var baris = locals[cdt][cdn];
    var cek_apakah_ada = 0;
    var docu = baris.document;

    var total_jasa = 0;
    for (var row_invoice in frm.doc.list_invoice) {
      var baris_invoice = frm.doc.list_invoice[row_invoice];
      total_jasa += baris_invoice.nilai_jasa;
    }
    for (var row_pajak in frm.doc.list_tax_and_charges) {
      var baris_pajak = frm.doc.list_tax_and_charges[row_pajak];
      if (baris_pajak.type == "Percentage") {
        baris_pajak.amount = (total_jasa * baris_pajak.rate) / 100;
      }
    }
     var total = 0
      for (var jumlah_baris in frm.doc.list_invoice) {
        total += frm.doc.list_invoice[jumlah_baris].amount;
      }
      for (var row_pajak in frm.doc.list_tax_and_charges) {
        total += frm.doc.list_tax_and_charges[row_pajak].amount;
      }
      frm.doc.grand_total = total

    cur_frm.refresh_fields();

    // frappe.call({
    // 	method: "addons.addons.doctype.cash_request.cash_request.get_taxes_and_charges",
    // 	args:{
    // 		pinv : baris.document
    // 	},
    // 	freeze:true,
    // 	callback: function(r){

    // 		for(var row in r.message){
    // 			var baris_hasil = r.message[row]

    // 			if(baris_hasil.total_taxes_and_charges == 0){
    // 				frappe.msgprint("This document has no taxes and charges to be converted into Nilai Jasa.")
    // 			}
    // 			else{
    // 				for(var row_pajak in frm.doc.list_tax_and_charges){
    // 					var baris_pajak = frm.doc.list_tax_and_charges[row_pajak]
    // 					if(baris_pajak.dari_invoice == docu){
    // 						cek_apakah_ada = 1
    // 						baris_pajak.amount = baris.nilai_jasa * baris_hasil.total_taxes_and_charges / 100

    // 						cur_frm.refresh_fields()
    // 					}
    // 				}

    // 				if(cek_apakah_ada == 0){
    // 					var d = frappe.model.add_child(cur_frm.doc,"Cash Request Taxes and Charges","list_tax_and_charges")
    // 					d.amount = baris.nilai_jasa * baris_hasil.total_taxes_and_charges / 100
    // 					d.type = "Amount"
    // 					d.dari_invoice = docu
    // 				}

    // 				cur_frm.refresh_fields()
    // 			}
    // 		}
    // 	}
    // })
  },
  amount:function(frm,cdt,cdn){
     var total = 0
      for (var jumlah_baris in frm.doc.list_invoice) {
        total += frm.doc.list_invoice[jumlah_baris].amount;
      }
      for (var row_pajak in frm.doc.list_tax_and_charges) {
        total += frm.doc.list_tax_and_charges[row_pajak].amount;
      }
      frm.doc.grand_total = total
      frm.refresh_fields()
  }
});

cur_frm.add_fetch("supplier", "supplier_name", "supplier_name");
cur_frm.add_fetch("supplier", "destination_account", "destination_account");
cur_frm.add_fetch("document", "supplier", "desc");
cur_frm.add_fetch("document", "remark", "user_remarks");
cur_frm.add_fetch("account", "account_currency", "account_currency");
