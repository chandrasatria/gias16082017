// Copyright (c) 2021, das and contributors
// For license information, please see license.txt

frappe.ui.form.on("Berita Acara Komplain", {
  validate:function (frm) {
    if (frm.doc.kurang_barang + frm.doc.barang_rusak + frm.doc.kualitas_produk_tidak_sesuai ==0){
      msgprint("Silahkan Pilih Salah Satu Tipe Komplain");
      validated=false;
    }else{
      validated=true;
    }
  },
  get_item: function(frm){
      frappe.db.get_list('Stock Entry Detail',{ filters: { 'parent': cur_frm.doc.no_stock_entry }, fields: ['item_code', 'item_name', 'qty', 'uom']})
          .then(data=>{
             // console.log(data);
              cur_frm.doc.item=[];
              for(let i = 0; i < data.length; i++){
                  //frappe.msgprint(String(data[i].serial_no))
                  var addnew=frappe.model.add_child(cur_frm.doc, "Tabel Berita Acara Komplain", "item");
                  addnew.item_code=data[i].item_code;
                  addnew.item_name=data[i].item_name;
                  addnew.qty=data[i].qty;
                  addnew.uom=data[i].uom;
              }
              var df=frappe.meta.get_docfield("Berita Acara Komplain", "no_purchase_receipt",frm.doc.name);
              var df1=frappe.meta.get_docfield("Berita Acara Komplain", "get_item_prec",frm.doc.name);
              df.hidden=1;
              df1.hidden=1;
              cur_frm.refresh_fields()
          })
  },
  refresh: function (frm) {
    if (frm.doc.docstatus == 1) {
      if(frm.doc.no_stock_entry){
        frm.add_custom_button(__("Make Stock Entry"), () =>
          frappe
            .xcall("addons.addons.doctype.berita_acara_komplain.berita_acara_komplain.make_stock_entry", {
              no_stock_entry: cur_frm.doc.no_stock_entry,
              no_bak: cur_frm.doc.name,
            })
            .then((stock_entry) => {
              frappe.model.sync(stock_entry);
              frappe.set_route("Form", stock_entry.doctype, stock_entry.name);
            })
        );
      }
      if(frm.doc.no_purchase_receipt){
        frm.add_custom_button(__("Make Stock Entry"), () =>
          frappe
            .xcall("addons.addons.doctype.berita_acara_komplain.berita_acara_komplain.make_stock_entry_with_pr", {
              no_purchase_receipt: cur_frm.doc.no_purchase_receipt,
              no_bak: cur_frm.doc.name,
            })
            .then((stock_entry) => {
              console.log(stock_entry);
              frappe.model.sync(stock_entry);
              frappe.set_route("Form", stock_entry.doctype, stock_entry.name);
            })
        );
      }
    }
    cur_frm.set_query("no_stock_entry", function () {
      return {
        filters: {
          docstatus: 1
        },
      };
    });
    cur_frm.set_query("no_purchase_receipt", function () {
      return {
        filters: {
          docstatus: 1
        },
      };
    });
  },
  // no_surat_jalan: function (frm) {
  //   if (frm.doc.no_surat_jalan && !frm.doc.item) {
  //     frappe.call({
  //       method: "addons.addons.doctype.berita_acara_komplain.berita_acara_komplain.get_dn",
  //       args: {
  //         dn: frm.doc.no_surat_jalan,
  //       },
  //       freeze: true,
  //       callback: function (hasil) {
  //         if (hasil) {
  //           frm.doc.item = [];
  //           for (var baris in hasil.message) {
  //             var d = frappe.model.add_child(cur_frm.doc, "Tabel Berita Acara Komplain", "item");

  //             d.item_code = hasil.message[baris].item_code;
  //             d.item_name = hasil.message[baris].item_name;
  //             d.qty = hasil.message[baris].qty;
  //             d.uom = hasil.message[baris].uom;
  //             cur_frm.refresh_fields();
  //           }
  //         }
  //       },
  //     });
  //   }
  // },
  get_item: function (frm) {
    if (cur_frm.doc.no_stock_entry ) {
      frappe.call({
        method: "addons.addons.doctype.berita_acara_komplain.berita_acara_komplain.get_ste",
        args: {
          ste: cur_frm.doc.no_stock_entry,
        },
        freeze: true,
        callback: function (hasil) {
          console.log(hasil.message);
          if (hasil) {
            cur_frm.doc.item = [];
            

            for (let i = 0; i < hasil.message.length; i++) {
              var child = cur_frm.add_child("item");
              frappe.model.set_value(child.doctype, child.name, "item_code", hasil.message[i].item_code);
              frappe.model.set_value(child.doctype, child.name, "item_name", hasil.message[i].item_name);
              frappe.model.set_value(child.doctype, child.name, "qty", hasil.message[i].qty);
              frappe.model.set_value(child.doctype, child.name, "uom", hasil.message[i].stock_uom);
            }
          }
          cur_frm.refresh_fields();
        },
      });
    }
  },
  get_item_prec: function (frm) {
    if (cur_frm.doc.no_purchase_receipt) {
      frappe.call({
        method: "addons.addons.doctype.berita_acara_komplain.berita_acara_komplain.get_prec",
        args: {
          prec: cur_frm.doc.no_purchase_receipt,
        },
        freeze: true,
        callback: function (hasil) {
          
          if (hasil) {
            cur_frm.doc.item = [];
            

            for (let i = 0; i < hasil.message.length; i++) {
              var child = cur_frm.add_child("item");
              frappe.model.set_value(child.doctype, child.name, "item_code", hasil.message[i].item_code);
              frappe.model.set_value(child.doctype, child.name, "item_name", hasil.message[i].item_name);
              frappe.model.set_value(child.doctype, child.name, "qty", hasil.message[i].qty);
              frappe.model.set_value(child.doctype, child.name, "uom", hasil.message[i].stock_uom);
            }
          }
          cur_frm.refresh_fields();
        },
      });
    }
  },
  get_data: function (frm) {
    if (cur_frm.doc.get_data == "Stock Entry") {
      cur_frm.set_value("no_purchase_receipt", "");
      cur_frm.doc.item = [];
      cur_frm.refresh_fields();
    }
    if (cur_frm.doc.get_data == "Purchase Receipt") {
      cur_frm.set_value("no_stock_entry", "");
      cur_frm.doc.item = [];
      cur_frm.refresh_fields();
    }
  },
  no_rq: function (frm) {
    if (frm.doc.no_rq) {
      frappe.call({
        method: "addons.addons.doctype.berita_acara_komplain.berita_acara_komplain.get_rq",
        args: {
          rq: frm.doc.no_rq,
        },
        freeze: true,
        callback: function (hasil) {
          console.log(hasil);
          if (hasil) {
            cur_frm.doc.item = [];
            if (hasil.message[0].length > 0) {
              cur_frm.set_value("tanggal_tiba", hasil.message[0][0].eta);
              cur_frm.set_value("tanggal_bongkar", hasil.message[0][0].eta);
              cur_frm.set_value("nama_supplier", hasil.message[0][0].supplier);
              cur_frm.set_value("no_po", hasil.message[0][0].purchase_order);
              cur_frm.set_value("no_purchase_receipt", hasil.message[0][0].parent);
            }
             cur_frm.refresh_fields();
          
          }
        },
      });

      frappe.call({
        doc: frm.doc,
        method: "set_item_from_rq",
        args:{
          
        },
        callback: function() {
        
          frm.refresh_fields();
        }
      });
    }
  },
});

cur_frm.add_fetch("item_code", "item_name", "item_name");
cur_frm.add_fetch("item_code", "stock_uom", "uom");
