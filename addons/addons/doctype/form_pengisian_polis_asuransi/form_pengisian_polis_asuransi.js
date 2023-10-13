// Copyright (c) 2021, das and contributors
// For license information, please see license.txt

frappe.ui.form.on('Form Pengisian Polis Asuransi', {
	onload: function(frm) {
		frm.set_query("no_pod", function(){
	        return {
	            "filters": {
	               	"is_pod": "POD",
	               	"docstatus": 1
	            }   
	        }
	    });
	},
	no_mpee: function(frm) {
		if(frm.doc.no_mpee){
			
			frappe.call({
				method : "addons.addons.doctype.form_pengisian_polis_asuransi.form_pengisian_polis_asuransi.get_mpee",
				args : {
					"mpee" : frm.doc.no_mpee
				},
				freeze: true,
				callback : function(hasil){
					if(hasil){
						frm.doc.nama_barang_yang_dipertanggungkan = []
						for(var baris in hasil.message){
							var d = frappe.model.add_child(cur_frm.doc,"Tabel Item Form Pengisian Polis Asuransi","nama_barang_yang_dipertanggungkan")

							d.nama_barang = hasil.message[baris].isi_kontainer
							
							cur_frm.refresh_fields()
						}
					}
				}
			});

			frm.doc.rute_to = []
			frappe.call({
				method : "addons.addons.doctype.memo_siap_ekspedisi.memo_siap_ekspedisi.get_mpee_rute",
				args : {
					"mpee" : frm.doc.no_mpee
				},
				freeze: true,
				callback : function(hasil){
					console.log(hasil)
					if(hasil){
						for(var baris in hasil.message){
							var d = frappe.model.add_child(cur_frm.doc,"Tabel Rute To Memo Permintaan Ekspedisi Eksternal","rute_to")
							d.rute_to = hasil.message[baris].rute_to
							cur_frm.refresh_fields()
						}
					}
				}
			})

		}
	}
});


cur_frm.add_fetch("nama_tertanggung","alamat_dan_kontak","alamat_tertanggung")
cur_frm.add_fetch("no_pod","nama_kapal","nama_kapal")
cur_frm.add_fetch("no_pod","transaction_date","tanggal_keberangkatan")
cur_frm.add_fetch("no_pod","rute_from","rute_from")
cur_frm.add_fetch("no_pod","route_akhir","route_akhir")