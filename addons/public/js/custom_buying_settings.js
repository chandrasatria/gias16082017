frappe.ui.form.on('Buying Settings', {
	refresh: function(frm) {
		cur_frm.set_query("default_cash_or_bank_account", function(doc) {
			return {
				filters:  [
					['Account', 'is_group', '=', 0],
					['Account', 'account_type', 'in', ["Cash","Bank"]],	
				]
			}
		});
		cur_frm.set_query("prorate_discount_account", function(doc) {
			return {
				filters:  [
					['Account', 'is_group', '=', 0],
					['Account', 'account_type', 'not in', ["Payable","Receivable"]],	
				]
			}
		});
		cur_frm.set_query("item_discount_account", function(doc) {
			return {
				filters:  [
					['Account', 'is_group', '=', 0],
					['Account', 'account_type', 'not in', ["Payable","Receivable"]],	
				]
			}
		});
	},
	onload: function(frm) {
		cur_frm.set_query("default_cash_or_bank_account", function(doc) {
			return {
				filters:  [
					['Account', 'is_group', '=', 0],
					['Account', 'account_type', 'in', ["Cash","Bank"]],	
				]
			}
		});
		cur_frm.set_query("prorate_discount_account", function(doc) {
			return {
				filters:  [
					['Account', 'is_group', '=', 0],
					['Account', 'account_type', 'not in', ["Payable","Receivable"]],	
				]
			}
		});
		cur_frm.set_query("item_discount_account", function(doc) {
			return {
				filters:  [
					['Account', 'is_group', '=', 0],
					['Account', 'account_type', 'not in', ["Payable","Receivable"]],	
				]
			}
		});
	}
});