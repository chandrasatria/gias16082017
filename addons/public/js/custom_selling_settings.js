frappe.ui.form.on('Selling Settings', {
	refresh: function(frm) {
		cur_frm.set_query("prorate_discount_account", function(doc) {
			return {
				filters:  [
					['Account', 'is_group', '=', 0],
					['Account', 'account_type', 'not in', ["Payable","Receivable"]],	
				]
			}
		});
		cur_frm.set_query("global_discount_account", function(doc) {
			return {
				filters:  [
					['Account', 'is_group', '=', 0],
				]
			}
		});
	},
	onload: function(frm) {
		cur_frm.set_query("prorate_discount_account", function(doc) {
			return {
				filters:  [
					['Account', 'is_group', '=', 0],
					['Account', 'account_type', 'not in', ["Payable","Receivable"]],	
				]
			}
		});
		cur_frm.set_query("global_discount_account", function(doc) {
			return {
				filters:  [
					['Account', 'is_group', '=', 0],
				]
			}
		});
	}
});