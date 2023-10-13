// Copyright (c) 2021, das and contributors
// For license information, please see license.txt

frappe.ui.form.on('List Kuesioner Limit Customer', {
	pilihan_1: function(frm) {
		if(frm.doc.pilihan_1 == "< 5 Tahun"){
		    frm.doc.poin_1 = 1
		}
		else if(frm.doc.pilihan_1 == "5 - 10 Tahun"){
		    frm.doc.poin_1 = 3
		}
		else if(frm.doc.pilihan_1 == "> 10 Tahun"){
		    frm.doc.poin_1 = 5
		}
		calculate_poin(frm)
	},
	pilihan_2: function(frm) {
    	if(frm.doc.pilihan_2 == "1 - 5 Jenis"){
    	    frm.doc.poin_2 = 1
    	}
    	else if(frm.doc.pilihan_2 == "6 - 10 Jenis"){
    	    frm.doc.poin_2 = 3
    	}
    	else if(frm.doc.pilihan_2 == "> 10 Jenis"){
    	    frm.doc.poin_2 = 5
    	}
    	calculate_poin(frm)
    },
    pilihan_3: function(frm) {
    	if(frm.doc.pilihan_3 == "< 25 tahun"){
    	    frm.doc.poin_3 = 1
    	}
    	else if(frm.doc.pilihan_3 == "26 - 39 tahun"){
    	    frm.doc.poin_3 = 3
    	}
    	else if(frm.doc.pilihan_3 == "> 40 tahun"){
    	    frm.doc.poin_3 = 5
    	}
    	calculate_poin(frm)
    },
    pilihan_4: function(frm) {
		if(frm.doc.pilihan_4 == "Tidak"){
		    frm.doc.poin_4 = 1
		}
		else if(frm.doc.pilihan_4 == "Ya"){
		    frm.doc.poin_4 = 5
		}
		calculate_poin(frm)
	},
	pilihan_5: function(frm) {
		if(frm.doc.pilihan_5 == "Sewa"){
		    frm.doc.poin_5 = 1
		}
		else if(frm.doc.pilihan_5 == "Milik Pribadi"){
		    frm.doc.poin_5 = 5
		}
		calculate_poin(frm)
	},
	pilihan_6: function(frm) {
		if(frm.doc.pilihan_6 == "Tidak Ada"){
		    frm.doc.poin_6 = 1
		}
		else if(frm.doc.pilihan_6 == "Ada"){
		    frm.doc.poin_6 = 5
		}
		calculate_poin(frm)
	},
	pilihan_7: function(frm) {
		if(frm.doc.pilihan_7 == "Tidak Ada"){
		    frm.doc.poin_7 = 0
		}
		else if(frm.doc.pilihan_7 == "1 - 2 unit"){
		    frm.doc.poin_7 = 1
		}
		else if(frm.doc.pilihan_7 == "3 - 5 unit"){
		    frm.doc.poin_7 = 3
		}
		else if(frm.doc.pilihan_7 == "> 5 unit"){
		    frm.doc.poin_7 = 5
		}
		calculate_poin(frm)
	},
	pilihan_8: function(frm) {
		if(frm.doc.pilihan_8 == "Tidak Ada"){
		    frm.doc.poin_8 = 1
		}
		else if(frm.doc.pilihan_8 == "2 cabang"){
		    frm.doc.poin_8 = 3
		}
		else if(frm.doc.pilihan_8 == "> 3 cabang"){
		    frm.doc.poin_8 = 5
		}
		calculate_poin(frm)
	},
	pilihan_9: function(frm) {
		if(frm.doc.pilihan_9 == "1 - 10 orang"){
		    frm.doc.poin_9 = 1
		}
		else if(frm.doc.pilihan_9 == "11 - 15 orang"){
		    frm.doc.poin_9 = 3
		}
		else if(frm.doc.pilihan_9 == "16 orang"){
		    frm.doc.poin_9 = 5
		}
		calculate_poin(frm)
	},
	pilihan_10: function(frm) {
		if(frm.doc.pilihan_10 == "< 5 Supplier"){
		    frm.doc.poin_10 = 1
		}
		else if(frm.doc.pilihan_10 == "6 -9 Supplier"){
		    frm.doc.poin_10 = 3
		}
		else if(frm.doc.pilihan_10 == "> 10 Supplier"){
		    frm.doc.poin_10 = 5
		}
		calculate_poin(frm)
	}
})

function calculate_poin(frm){
    var poin_1 = 0
    var poin_2 = 0
    var poin_3 = 0
    var poin_4 = 0
    var poin_5 = 0
    var poin_6 = 0
    var poin_7 = 0
    var poin_8 = 0
    var poin_9 = 0
    var poin_10 = 0
    
    if(frm.doc.poin_1){
        poin_1 = frm.doc.poin_1
    }
    if(frm.doc.poin_2){
        poin_2 = frm.doc.poin_2
    }
    if(frm.doc.poin_3){
        poin_3 = frm.doc.poin_3
    }
    if(frm.doc.poin_4){
        poin_4 = frm.doc.poin_4
    }
    if(frm.doc.poin_5){
        poin_5 = frm.doc.poin_5
    }
    if(frm.doc.poin_6){
        poin_6 = frm.doc.poin_6
    }
    if(frm.doc.poin_7){
        poin_7 = frm.doc.poin_7
    }
    if(frm.doc.poin_8){
        poin_8 = frm.doc.poin_8
    }
    if(frm.doc.poin_9){
        poin_9 = frm.doc.poin_9
    }
    if(frm.doc.poin_10){
        poin_10 = frm.doc.poin_10
    }
    
    frm.doc.total_poin = poin_1+poin_2+poin_3+poin_4+poin_5+poin_6+poin_7+poin_8+poin_9+poin_10  
        
    if(frm.doc.total_poin >= 36){
        frm.doc.adjustment = "Low Risk"
    }
    else if(frm.doc.total_poin >= 21){
        frm.doc.adjustment = "Medium Risk"
    }
    else{
        frm.doc.adjustment = "High Risk"
    }
    
    frm.refresh_fields()
}