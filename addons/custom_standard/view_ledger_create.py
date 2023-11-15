import frappe
import time
import os
from frappe.utils import flt, add_months, cint, nowdate, getdate, today, date_diff, month_diff, add_days, get_last_day, get_datetime
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from addons.custom_standard.custom_stock_entry import custom_distribute_additional_costs

from erpnext.selling.doctype.customer.customer import get_credit_limit, get_customer_outstanding
from erpnext.controllers.accounts_controller import get_taxes_and_charges
from frappe.model.naming import make_autoname, revert_series_if_last

@frappe.whitelist()
def enqueue_gl_custom():
    enqueued_method = "addons.custom_standard.view_ledger_create.gelondongan_gl_custom"
    frappe.enqueue(method=enqueued_method,timeout=24400, queue='long')

@frappe.whitelist()
def gelondongan_gl_custom():
    create_gl_custom_purchase_invoice()
    create_gl_custom_payment_entry()
    create_gl_custom_expense_claim()
    create_gl_custom_journal_entry()
    create_gl_custom_purchase_receipt()
    create_gl_custom_delivery_note()
    create_gl_custom_sales_invoice()
    create_gl_custom_stock_entry()

@frappe.whitelist()
def delete_gl_custom():
    delete_gl_custom_by_doctype("Purchase Invoice")
    delete_gl_custom_by_doctype("Payment Entry")
    delete_gl_custom_by_doctype("Expense Claim")
    delete_gl_custom_by_doctype("Journal Entry")
    delete_gl_custom_by_doctype("Purchase Receipt")
    delete_gl_custom_by_doctype("Delivery Note")
    delete_gl_custom_by_doctype("Sales Invoice")
    delete_gl_custom_by_doctype("Stock Entry")

@frappe.whitelist()
def delete_gl_custom_by_doctype(doctype):
    list_doc=frappe.db.sql(""" 
        SELECT je.name FROM `tab{}` je 
        WHERE docstatus = 2 AND name in (SELECT no_voucher FROM `tabGL Entry Custom` GROUP BY no_voucher)  """.format(doctype))
    for row in list_doc:
        frappe.db.sql(""" DELETE FROM `tabGL Entry Custom` WHERE no_voucher = "{}" """.format(row[0]))
        print(row[0])

@frappe.whitelist()
def fix_ledger_():
    list_ledger = frappe.db.sql(""" 
        DELETE FROM `tabGL Entry Custom` WHERE voucher_type = "Sales Invoice" 
    """)
    frappe.db.commit()
    print("1")

@frappe.whitelist()
def delete_logs():
    frappe.db.sql(""" DELETE FROM `tabScheduled Job Log` WHERE scheduled_job_type LIKE "%addons.custom_standard.view_ledger_create%"  """)

@frappe.whitelist()
def check_delete():
    doc_list = frappe.db.sql(""" SELECT voucher_no, voucher_type FROM `tabGL Entry` WHERE is_cancelled = 1
    and voucher_no in (select no_voucher FROM `tabGL Entry Custom`)
    GROUP BY voucher_no """)

    for nomor_doc in doc_list:
        self = frappe.get_doc(nomor_doc[1],nomor_doc[0])
        if self.docstatus == 2:
            frappe.db.sql(""" DELETE FROM `tabGL Entry Custom` WHERE no_voucher = "{}" """.format(self.name))
            print(nomor_doc[0])
            frappe.db.commit()

@frappe.whitelist()
def check_delete_by_name(self,method):
    doc_list = frappe.db.sql(""" SELECT voucher_no, voucher_type FROM `tabGL Entry` WHERE is_cancelled = 1
    and voucher_no in (select no_voucher FROM `tabGL Entry Custom`)
    GROUP BY voucher_no """)

    for nomor_doc in doc_list:
        self = frappe.get_doc(nomor_doc[1],nomor_doc[0])
        if self.docstatus == 2:
            frappe.db.sql(""" DELETE FROM `tabGL Entry Custom` WHERE no_voucher = "{}" """.format(self.name))
            print(nomor_doc[0])
            frappe.db.commit()


@frappe.whitelist()
def create_gl_custom_expense_claim():
    doc_list = frappe.db.sql(""" SELECT voucher_no FROM `tabGL Entry` WHERE is_cancelled = 0
    and voucher_type = "Expense Claim" 
    and voucher_no not in (select no_voucher FROM `tabGL Entry Custom` WHERE voucher_type = "Expense Claim")
    GROUP BY voucher_no """)
    for nomor_doc in doc_list:
        self = frappe.get_doc("Expense Claim", nomor_doc[0])
        frappe.db.sql(""" DELETE FROM `tabGL Entry Custom` WHERE no_voucher = "{}" """.format(self.name))
        gl_list = frappe.db.sql(""" 
                SELECT posting_date,
                 account,
                 debit,
                 credit,
                 party_type,
                 party,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', 1)),
                 voucher_type,
                 voucher_no,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', -1)),
                 branch,
                 cost_center,
                 name 
                 FROM `tabGL Entry` WHERE voucher_no = "{}" 
                 GROUP BY account
                 """.format(self.name))

        list_item = []
        for baris_query in gl_list:
            if frappe.utils.flt(baris_query[2]) > 0:
                nyari = 0
                for row_expense in self.expenses:
                    exp_typ = frappe.get_doc("Expense Claim Type",row_expense.expense_type)
                    account = exp_typ.accounts[0].default_account
                    if account == baris_query[1] and row_expense.name not in list_item:
                        nyari = 1
                        sle_new = frappe.new_doc("GL Entry Custom")
                        sle_new.update({
                            "posting_date": baris_query[0],
                            "account": baris_query[1],
                            "debit": row_expense.sanctioned_amount,
                            "credit": baris_query[3],
                            "party_type": baris_query[4],
                            "party": baris_query[5],
                            "remarks": str(row_expense.get("description")) + "|" + str(row_expense.get("user_remark")) ,
                            "doc_remarks": self.remark,
                            "voucher_type":baris_query[7],
                            "no_voucher":baris_query[8],
                            "branch": row_expense.branch,
                            "cost_center": row_expense.cost_center,
                            "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax,
                            "voucher_detail_no": row_expense.name
                        })  
                        if row_expense.name not in list_item:
                            list_item.append(row_expense.name)

                        sle_new.save(ignore_permissions=True)

                if nyari == 0:
                    sle_new = frappe.new_doc("GL Entry Custom")
                    sle_new.update({
                        "posting_date": baris_query[0],
                        "account": baris_query[1],
                        "debit": baris_query[2],
                        "credit": baris_query[3],
                        "party_type": baris_query[4],
                        "party": baris_query[5],
                        "remarks": baris_query[6],
                        "doc_remarks": self.remark,
                        "voucher_type":baris_query[7],
                        "no_voucher":baris_query[8],
                        "branch": baris_query[10],
                        "cost_center": baris_query[11],
                        "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
                    })  
                    sle_new.save(ignore_permissions=True)
            else:
                sle_new = frappe.new_doc("GL Entry Custom")
                sle_new.update({
                    "posting_date": baris_query[0],
                    "account": baris_query[1],
                    "debit": baris_query[2],
                    "credit": baris_query[3],
                    "party_type": baris_query[4],
                    "party": baris_query[5],
                    "remarks": baris_query[6],
                    "doc_remarks": self.remark,
                    "voucher_type":baris_query[7],
                    "no_voucher":baris_query[8],
                    "branch": baris_query[10],
                    "cost_center": baris_query[11],
                    "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
                })  
                sle_new.save(ignore_permissions=True)

        print(nomor_doc[0])
        frappe.db.commit()

@frappe.whitelist()
def benerin_pinv():
    doc = frappe.get_doc("Purchase Invoice", "PI-1-23-04-00246")
    create_view_ledger_purchase_invoice(doc,"after_insert")


@frappe.whitelist()
def create_gl_custom_purchase_invoice():
    doc_list = frappe.db.sql(""" SELECT voucher_no FROM `tabGL Entry` WHERE is_cancelled = 0
    and voucher_type = "Purchase Invoice" 
    and voucher_no not in (select no_voucher FROM `tabGL Entry Custom` WHERE voucher_type = "Purchase Invoice")
    GROUP BY voucher_no """)
    for nomor_doc in doc_list:
        self = frappe.get_doc("Purchase Invoice", nomor_doc[0])
        frappe.db.sql(""" DELETE FROM `tabGL Entry Custom` WHERE no_voucher = "{}" """.format(self.name))
        gl_list = frappe.db.sql(""" 
                SELECT posting_date,
                 account,
                 debit,
                 credit,
                 party_type,
                 party,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', 1)),
                 voucher_type,
                 voucher_no,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', -1)),
                 branch,
                 cost_center,
                 name 
                 FROM `tabGL Entry` WHERE voucher_no = "{}" 
                 GROUP BY account
                 """.format(self.name))
        list_transaction = []
        list_item = []
        for baris_query in gl_list:
            self = frappe.get_doc("Purchase Invoice", baris_query[8])
                
            pakai_di_item = 0
            for baris in self.items:
                if baris.expense_account == baris_query[1]:
                    pakai_di_item = 1

            if pakai_di_item == 1:
                if baris_query[8] not in list_transaction:
                    list_transaction.append(baris_query[8])
                    grand_total = self.rounded_total if (self.rounding_adjustment and self.rounded_total) else self.grand_total
                    base_grand_total = flt(self.base_rounded_total if (self.base_rounding_adjustment and self.base_rounded_total)
                        else self.base_grand_total, self.precision("base_grand_total")) 

                    list_account = []
                    item_remark = ""
                    for item in self.get("items"):

                        

                        if item.expense_account not in list_account:
                            list_account.append(item.expense_account)

                        sle = {}

                        expense_account = item.expense_account
                        if item.purchase_receipt and frappe.get_doc("Item",item.item_code).is_stock_item:
                            self.stock_received_but_not_billed = self.get_company_default("stock_received_but_not_billed")
                            expense_account = self.stock_received_but_not_billed

                        
                        sle_new = frappe.new_doc("GL Entry Custom")
                        sle_new.update({
                            "posting_date": self.posting_date,
                            "account": expense_account,
                            "debit": flt(item.base_net_amount + item.item_tax_amount, item.precision("base_net_amount")),
                            "credit": 0 ,
                            "remarks": item.user_remark,
                            "voucher_type":"Purchase Invoice",
                            "no_voucher": self.name,
                            "item_code" : item.item_code,
                            "item_name": item.item_name,
                            "branch": item.branch,
                            "cost_center": item.cost_center,
                            "tax_or_non_tax": self.tax_or_non_tax,
                            "doc_remarks":self.remarks,
                            "voucher_detail_no": item.name
                        })  
                        if item.name not in list_item:
                            list_item.append(item.name)

                        sle_new.save(ignore_permissions=True)
            else:
                sle_new = frappe.new_doc("GL Entry Custom")
                sle_new.update({
                    "posting_date": baris_query[0],
                    "account": baris_query[1],
                    "debit": baris_query[2],
                    "credit": baris_query[3],
                    "party_type": baris_query[4],
                    "party": baris_query[5],
                    "remarks": baris_query[6],
                    "doc_remarks":self.remarks,
                    "voucher_type":baris_query[7],
                    "no_voucher":baris_query[8],
                    "branch": baris_query[10],
                    "cost_center": baris_query[11],
                    "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
                })  
                sle_new.save(ignore_permissions=True)
            

        print(nomor_doc[0])
        frappe.db.commit()

@frappe.whitelist()
def create_gl_custom_expense_claim_by_name(name):
    doc_list = frappe.db.sql(""" SELECT voucher_no FROM `tabGL Entry` WHERE is_cancelled = 0
    and voucher_type = "Expense Claim" 
    and voucher_no = "{}"
    GROUP BY voucher_no """.format(name))
    for nomor_doc in doc_list:
        self = frappe.get_doc("Expense Claim", nomor_doc[0])
        frappe.db.sql(""" DELETE FROM `tabGL Entry Custom` WHERE no_voucher = "{}" """.format(self.name))
        gl_list = frappe.db.sql(""" 
                SELECT posting_date,
                 account,
                 debit,
                 credit,
                 party_type,
                 party,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', 1)),
                 voucher_type,
                 voucher_no,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', -1)),
                 branch,
                 cost_center,
                 name 
                 FROM `tabGL Entry` WHERE voucher_no = "{}" 
                 GROUP BY account
                 """.format(self.name))

        list_item = []
        for baris_query in gl_list:
            if frappe.utils.flt(baris_query[2]) > 0:
                nyari = 0
                for row_expense in self.expenses:
                    exp_typ = frappe.get_doc("Expense Claim Type",row_expense.expense_type)
                    account = exp_typ.accounts[0].default_account
                    if account == baris_query[1] and row_expense.name not in list_item:
                        nyari = 1
                        sle_new = frappe.new_doc("GL Entry Custom")
                        sle_new.update({
                            "posting_date": baris_query[0],
                            "account": baris_query[1],
                            "debit": row_expense.sanctioned_amount,
                            "credit": baris_query[3],
                            "party_type": baris_query[4],
                            "party": baris_query[5],
                            "remarks": str(row_expense.get("description")) + "|" + str(row_expense.get("user_remark")) ,
                            "doc_remarks": self.remark,
                            "voucher_type":baris_query[7],
                            "no_voucher":baris_query[8],
                            "branch": row_expense.branch,
                            "cost_center": row_expense.cost_center,
                            "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax,
                            "voucher_detail_no": row_expense.name
                        })  
                        if row_expense.name not in list_item:
                            list_item.append(row_expense.name)

                        sle_new.save(ignore_permissions=True)

                if nyari == 0:
                    sle_new = frappe.new_doc("GL Entry Custom")
                    sle_new.update({
                        "posting_date": baris_query[0],
                        "account": baris_query[1],
                        "debit": baris_query[2],
                        "credit": baris_query[3],
                        "party_type": baris_query[4],
                        "party": baris_query[5],
                        "remarks": baris_query[6],
                        "doc_remarks": self.remark,
                        "voucher_type":baris_query[7],
                        "no_voucher":baris_query[8],
                        "branch": baris_query[10],
                        "cost_center": baris_query[11],
                        "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
                    })  
                    sle_new.save(ignore_permissions=True)
            else:
                sle_new = frappe.new_doc("GL Entry Custom")
                sle_new.update({
                    "posting_date": baris_query[0],
                    "account": baris_query[1],
                    "debit": baris_query[2],
                    "credit": baris_query[3],
                    "party_type": baris_query[4],
                    "party": baris_query[5],
                    "remarks": baris_query[6],
                    "doc_remarks": self.remark,
                    "voucher_type":baris_query[7],
                    "no_voucher":baris_query[8],
                    "branch": baris_query[10],
                    "cost_center": baris_query[11],
                    "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
                })  
                sle_new.save(ignore_permissions=True)

        print(nomor_doc[0])
        frappe.db.commit()

@frappe.whitelist()
def create_gl_custom_purchase_invoice_by_name(self):

    doc_list = frappe.db.sql(""" SELECT voucher_no FROM `tabGL Entry` WHERE is_cancelled = 0
    and voucher_type = "Purchase Invoice" 
    and voucher_no = "{}"
    GROUP BY voucher_no """.format(self.name))
    for nomor_doc in doc_list:
        self = frappe.get_doc("Purchase Invoice", nomor_doc[0])
        frappe.db.sql(""" DELETE FROM `tabGL Entry Custom` WHERE no_voucher = "{}" """.format(self.name))
        gl_list = frappe.db.sql(""" 
                SELECT posting_date,
                 account,
                 debit,
                 credit,
                 party_type,
                 party,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', 1)),
                 voucher_type,
                 voucher_no,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', -1)),
                 branch,
                 cost_center,
                 name 
                 FROM `tabGL Entry` WHERE voucher_no = "{}" 
                 GROUP BY account
                 """.format(self.name))
        list_transaction = []
        list_item = []
        for baris_query in gl_list:
            self = frappe.get_doc("Purchase Invoice", baris_query[8])
                
            pakai_di_item = 0
            for baris in self.items:
                if baris.expense_account == baris_query[1]:
                    pakai_di_item = 1

            if pakai_di_item == 1:
                if baris_query[8] not in list_transaction:
                    list_transaction.append(baris_query[8])
                    grand_total = self.rounded_total if (self.rounding_adjustment and self.rounded_total) else self.grand_total
                    base_grand_total = flt(self.base_rounded_total if (self.base_rounding_adjustment and self.base_rounded_total)
                        else self.base_grand_total, self.precision("base_grand_total")) 

                    list_account = []
                    item_remark = ""
                    for item in self.get("items"):

                        

                        if item.expense_account not in list_account:
                            list_account.append(item.expense_account)

                        sle = {}

                        expense_account = item.expense_account
                        if item.purchase_receipt and frappe.get_doc("Item",item.item_code).is_stock_item:
                            self.stock_received_but_not_billed = self.get_company_default("stock_received_but_not_billed")
                            expense_account = self.stock_received_but_not_billed

                        
                        sle_new = frappe.new_doc("GL Entry Custom")
                        sle_new.update({
                            "posting_date": self.posting_date,
                            "account": expense_account,
                            "debit": flt(item.base_net_amount + item.item_tax_amount, item.precision("base_net_amount")),
                            "credit": 0 ,
                            "remarks": item.user_remark,
                            "voucher_type":"Purchase Invoice",
                            "no_voucher": self.name,
                            "item_code" : item.item_code,
                            "item_name": item.item_name,
                            "branch": item.branch,
                            "cost_center": item.cost_center,
                            "tax_or_non_tax": self.tax_or_non_tax,
                            "doc_remarks":self.remarks,
                            "voucher_detail_no": item.name
                        })  
                        if item.name not in list_item:
                            list_item.append(item.name)

                        sle_new.save(ignore_permissions=True)
            else:
                sle_new = frappe.new_doc("GL Entry Custom")
                sle_new.update({
                    "posting_date": baris_query[0],
                    "account": baris_query[1],
                    "debit": baris_query[2],
                    "credit": baris_query[3],
                    "party_type": baris_query[4],
                    "party": baris_query[5],
                    "remarks": baris_query[6],
                    "doc_remarks":self.remarks,
                    "voucher_type":baris_query[7],
                    "no_voucher":baris_query[8],
                    "branch": baris_query[10],
                    "cost_center": baris_query[11],
                    "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
                })  
                sle_new.save(ignore_permissions=True)
            

        print(nomor_doc[0])
        frappe.db.commit()


@frappe.whitelist()
def create_gl_custom_sales_invoice():
    doc_list = frappe.db.sql(""" SELECT voucher_no FROM `tabGL Entry` WHERE is_cancelled = 0
    and voucher_type = "Sales Invoice" 
    and voucher_no not in (select no_voucher FROM `tabGL Entry Custom` WHERE voucher_type = "Sales Invoice")
    GROUP BY voucher_no """)
    for nomor_doc in doc_list:
        self = frappe.get_doc("Sales Invoice", nomor_doc[0])
        frappe.db.sql(""" DELETE FROM `tabGL Entry Custom` WHERE no_voucher = "{}" """.format(self.name))
        gl_list = frappe.db.sql(""" 
                SELECT posting_date,
                 account,
                 debit,
                 credit,
                 party_type,
                 party,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', 1)),
                 voucher_type,
                 voucher_no,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', -1)),
                 branch,
                 cost_center,
                 name 
                 FROM `tabGL Entry` WHERE voucher_no = "{}" 
                 GROUP BY account
                 """.format(self.name))
        list_transaction = []
        list_item = []
        for baris_query in gl_list:
            self = frappe.get_doc("Sales Invoice", baris_query[8])
                
            pakai_di_item = 0
            for baris in self.items:
                if baris.expense_account == baris_query[1]:
                    pakai_di_item = 1

            if pakai_di_item == 1:
                if baris_query[8] not in list_transaction:
                    list_transaction.append(baris_query[8])
                    grand_total = self.rounded_total if (self.rounding_adjustment and self.rounded_total) else self.grand_total
                    base_grand_total = flt(self.base_rounded_total if (self.base_rounding_adjustment and self.base_rounded_total)
                        else self.base_grand_total, self.precision("base_grand_total")) 

                    list_account = []
                    for item in self.get("items"):

                        
                        if item.expense_account not in list_account:
                            list_account.append(item.expense_account)

                        sle = {}

                        expense_account = item.expense_account
                        if item.delivery_note and frappe.get_doc("Item",item.item_code).is_stock_item:
                            self.stock_received_but_not_billed = self.get_company_default("stock_received_but_not_billed")
                            expense_account = self.stock_received_but_not_billed

                        sle_new = frappe.new_doc("GL Entry Custom")
                        sle_new.update({
                            "posting_date": self.posting_date,
                            "account": expense_account,
                            "credit": flt(item.base_amount, item.precision("base_net_amount")),
                            "debit": 0 ,
                            "remarks": item.user_remark,
                            "doc_remarks":self.remarks,
                            "voucher_type":"Sales Invoice",
                            "no_voucher": self.name,
                            "item_code" : item.item_code,
                            "item_name": item.item_name,
                            "branch": item.branch,
                            "cost_center": item.cost_center,
                            "tax_or_non_tax": self.tax_or_non_tax,
                            "voucher_detail_no": item.name
                        })  
                        if item.name not in list_item:
                            list_item.append(item.name)
                        sle_new.save(ignore_permissions=True)
            else:
                sle_new = frappe.new_doc("GL Entry Custom")
                sle_new.update({
                    "posting_date": baris_query[0],
                    "account": baris_query[1],
                    "debit": baris_query[2],
                    "credit": baris_query[3],
                    "party_type": baris_query[4],
                    "party": baris_query[5],
                    "remarks": baris_query[6],
                    "doc_remarks": baris_query[9],
                    "voucher_type":baris_query[7],
                    "no_voucher":baris_query[8],
                    "branch": baris_query[10],
                    "cost_center": baris_query[11],
                    "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
                })  
                sle_new.save(ignore_permissions=True)    
            

        print(nomor_doc[0])
        frappe.db.commit()


@frappe.whitelist()
def create_gl_custom_stock_entry():
    doc_list = frappe.db.sql(""" SELECT voucher_no FROM `tabGL Entry` WHERE is_cancelled = 0
        and voucher_type = "Stock Entry" 
        and voucher_no not in (select no_voucher FROM `tabGL Entry Custom` WHERE voucher_type = "Stock Entry")
        GROUP BY voucher_no """)

    for nomor_doc in doc_list:
        self = frappe.get_doc("Stock Entry", nomor_doc[0])  
        frappe.db.sql(""" DELETE FROM `tabGL Entry Custom` WHERE no_voucher = "{}" """.format(self.name))
        gl_list = frappe.db.sql(""" 
                SELECT posting_date,
                 account,
                 debit,
                 credit,
                 party_type,
                 party,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', 1)),
                 voucher_type,
                 voucher_no,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', -1)),
                 branch,
                 cost_center,
                 name 
                 FROM `tabGL Entry` WHERE voucher_no = "{}" 
                 GROUP BY account
                 """.format(self.name))
        list_transaction = []
        list_item = []
        for baris_query in gl_list:
            self = frappe.get_doc("Stock Entry", baris_query[8])  

            pakai_di_item = 0
            for baris in self.items:
                if baris.s_warehouse and not baris.t_warehouse:
                    if frappe.get_doc("Warehouse",baris.s_warehouse).account == baris_query[1]:
                        pakai_di_item = 1
                elif not baris.s_warehouse and baris.t_warehouse:
                    if frappe.get_doc("Warehouse",baris.t_warehouse).account == baris_query[1]:
                        pakai_di_item = 1

            if pakai_di_item == 1:
                if baris_query[8] not in list_transaction:
                    list_transaction.append(baris_query[8])
                    list_account = []
                    for item in self.get("items"):

                        if item.s_warehouse and not item.t_warehouse:
                            if frappe.get_doc("Warehouse", item.s_warehouse).account not in list_account:
                                list_account.append(frappe.get_doc("Warehouse", item.s_warehouse).account)
                        elif item.t_warehouse and not item.s_warehouse:
                            if frappe.get_doc("Warehouse", item.t_warehouse).account not in list_account:
                                list_account.append(frappe.get_doc("Warehouse", item.t_warehouse).account)

                        sle = {}

                        if item.s_warehouse and not item.t_warehouse:
                            expense_account = frappe.get_doc("Warehouse", item.s_warehouse).account
                        elif item.t_warehouse and not item.s_warehouse:
                            expense_account = frappe.get_doc("Warehouse", item.t_warehouse).account
                    
                        if item.s_warehouse and not item.t_warehouse:
                            sle_new = frappe.new_doc("GL Entry Custom")
                            sle_new.update({
                                "posting_date": self.posting_date,
                                "account": expense_account,
                                "credit": item.valuation_rate * item.transfer_qty,
                                "debit": 0 ,
                                "remarks": item.user_remark,
                                "voucher_type":"Stock Entry",
                                "no_voucher": self.name,
                                "item_code" : item.item_code,
                                "item_name": item.item_name,
                                "branch": item.branch,
                                "cost_center": item.cost_center,
                                "tax_or_non_tax": self.tax_or_non_tax,
                                "doc_remarks":self.remarks,
                                "voucher_detail_no": item.name
                            })  
                            if item.name not in list_item:
                                list_item.append(item.name)

                            sle_new.save(ignore_permissions=True)
                        elif not item.s_warehouse and item.t_warehouse:
                            sle_new = frappe.new_doc("GL Entry Custom")
                            sle_new.update({
                                "posting_date": self.posting_date,
                                "account": expense_account,
                                "debit": item.valuation_rate * item.transfer_qty,
                                "credit": 0 ,
                                "remarks": item.user_remark,
                                "voucher_type":"Stock Entry",
                                "no_voucher": self.name,
                                "item_code" : item.item_code,
                                "item_name": item.item_name,
                                "branch": item.branch,
                                "cost_center": item.cost_center,
                                "tax_or_non_tax": self.tax_or_non_tax,
                                "doc_remarks":self.remarks,
                                "voucher_detail_no": item.name
                            })  
                            if item.name not in list_item:
                                list_item.append(item.name)

                            sle_new.save(ignore_permissions=True)

            else:
                sle_new = frappe.new_doc("GL Entry Custom")
                sle_new.update({
                    "posting_date": baris_query[0],
                    "account": baris_query[1],
                    "debit": baris_query[2],
                    "credit": baris_query[3],
                    "party_type": baris_query[4],
                    "party": baris_query[5],
                    "remarks": baris_query[6],
                    "doc_remarks":self.remarks,
                    "voucher_type":baris_query[7],
                    "no_voucher":baris_query[8],
                    "branch": baris_query[10],
                    "cost_center": baris_query[11],
                    "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
                })  
                sle_new.save(ignore_permissions=True)

        print(nomor_doc[0])
        frappe.db.commit()


@frappe.whitelist()
def create_gl_custom_stock_entry_by_name(self,method):
    doc_list = frappe.db.sql(""" SELECT voucher_no FROM `tabGL Entry` WHERE is_cancelled = 0
        and voucher_type = "Stock Entry" 
        and voucher_no = "{}"
        GROUP BY voucher_no """.format(self))

    for nomor_doc in doc_list:
        self = frappe.get_doc("Stock Entry", nomor_doc[0])  
        frappe.db.sql(""" DELETE FROM `tabGL Entry Custom` WHERE no_voucher = "{}" """.format(self.name))
        gl_list = frappe.db.sql(""" 
                SELECT posting_date,
                 account,
                 debit,
                 credit,
                 party_type,
                 party,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', 1)),
                 voucher_type,
                 voucher_no,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', -1)),
                 branch,
                 cost_center,
                 name 
                 FROM `tabGL Entry` WHERE voucher_no = "{}" 
                 GROUP BY account
                 """.format(self.name))
        list_transaction = []
        list_item = []
        for baris_query in gl_list:
            self = frappe.get_doc("Stock Entry", baris_query[8])  

            pakai_di_item = 0
            for baris in self.items:
                if baris.s_warehouse and not baris.t_warehouse:
                    if frappe.get_doc("Warehouse",baris.s_warehouse).account == baris_query[1]:
                        pakai_di_item = 1
                elif not baris.s_warehouse and baris.t_warehouse:
                    if frappe.get_doc("Warehouse",baris.t_warehouse).account == baris_query[1]:
                        pakai_di_item = 1

            if pakai_di_item == 1:
                if baris_query[8] not in list_transaction:
                    list_transaction.append(baris_query[8])
                    list_account = []
                    for item in self.get("items"):

                        if item.s_warehouse and not item.t_warehouse:
                            if frappe.get_doc("Warehouse", item.s_warehouse).account not in list_account:
                                list_account.append(frappe.get_doc("Warehouse", item.s_warehouse).account)
                        elif item.t_warehouse and not item.s_warehouse:
                            if frappe.get_doc("Warehouse", item.t_warehouse).account not in list_account:
                                list_account.append(frappe.get_doc("Warehouse", item.t_warehouse).account)

                        sle = {}

                        if item.s_warehouse and not item.t_warehouse:
                            expense_account = frappe.get_doc("Warehouse", item.s_warehouse).account
                        elif item.t_warehouse and not item.s_warehouse:
                            expense_account = frappe.get_doc("Warehouse", item.t_warehouse).account
                    
                        if item.s_warehouse and not item.t_warehouse:
                            sle_new = frappe.new_doc("GL Entry Custom")
                            sle_new.update({
                                "posting_date": self.posting_date,
                                "account": expense_account,
                                "credit": item.valuation_rate * item.transfer_qty,
                                "debit": 0 ,
                                "remarks": item.user_remark,
                                "voucher_type":"Stock Entry",
                                "no_voucher": self.name,
                                "item_code" : item.item_code,
                                "item_name": item.item_name,
                                "branch": item.branch,
                                "cost_center": item.cost_center,
                                "tax_or_non_tax": self.tax_or_non_tax,
                                "doc_remarks":self.remarks,
                                "voucher_detail_no": item.name
                            })  
                            if item.name not in list_item:
                                list_item.append(item.name)

                            sle_new.save(ignore_permissions=True)
                        elif not item.s_warehouse and item.t_warehouse:
                            sle_new = frappe.new_doc("GL Entry Custom")
                            sle_new.update({
                                "posting_date": self.posting_date,
                                "account": expense_account,
                                "debit": item.valuation_rate * item.transfer_qty,
                                "credit": 0 ,
                                "remarks": item.user_remark,
                                "voucher_type":"Stock Entry",
                                "no_voucher": self.name,
                                "item_code" : item.item_code,
                                "item_name": item.item_name,
                                "branch": item.branch,
                                "cost_center": item.cost_center,
                                "tax_or_non_tax": self.tax_or_non_tax,
                                "doc_remarks":self.remarks,
                                "voucher_detail_no": item.name
                            })  
                            if item.name not in list_item:
                                list_item.append(item.name)

                            sle_new.save(ignore_permissions=True)

            else:
                sle_new = frappe.new_doc("GL Entry Custom")
                sle_new.update({
                    "posting_date": baris_query[0],
                    "account": baris_query[1],
                    "debit": baris_query[2],
                    "credit": baris_query[3],
                    "party_type": baris_query[4],
                    "party": baris_query[5],
                    "remarks": baris_query[6],
                    "doc_remarks":self.remarks,
                    "voucher_type":baris_query[7],
                    "no_voucher":baris_query[8],
                    "branch": baris_query[10],
                    "cost_center": baris_query[11],
                    "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
                })  
                sle_new.save(ignore_permissions=True)

        print(nomor_doc[0])
        frappe.db.commit()

@frappe.whitelist()
def create_view_ledger_purchase_invoice(document,method):
    doc_list = frappe.db.sql(""" SELECT voucher_no FROM `tabGL Entry` WHERE is_cancelled = 0
    and voucher_type = "Purchase Invoice" 
    and voucher_no = "{}"
    and voucher_no not in (select no_voucher FROM `tabGL Entry Custom`)
    GROUP BY voucher_no """.format(document.name))
    for nomor_doc in doc_list:
        self = frappe.get_doc("Purchase Invoice", nomor_doc[0])
        frappe.db.sql(""" DELETE FROM `tabGL Entry Custom` WHERE no_voucher = "{}" """.format(self.name))
        gl_list = frappe.db.sql(""" 
                SELECT posting_date,
                 account,
                 debit,
                 credit,
                 party_type,
                 party,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', 1)),
                 voucher_type,
                 voucher_no,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', -1)),
                 branch,
                 cost_center,
                 name 
                 FROM `tabGL Entry` WHERE voucher_no = "{}" GROUP BY account""".format(self.name))
        list_transaction = []
        list_item = []
        for baris_query in gl_list:
            self = frappe.get_doc("Purchase Invoice", baris_query[8])
                
            pakai_di_item = 0
            for baris in self.items:
                if baris.expense_account == baris_query[1]:
                    pakai_di_item = 1

            if pakai_di_item == 1:
                if baris_query[8] not in list_transaction:
                    list_transaction.append(baris_query[8])
                    grand_total = self.rounded_total if (self.rounding_adjustment and self.rounded_total) else self.grand_total
                    base_grand_total = flt(self.base_rounded_total if (self.base_rounding_adjustment and self.base_rounded_total)
                        else self.base_grand_total, self.precision("base_grand_total")) 

                    list_account = []
                    item_remark = ""
                    for item in self.get("items"):

                        
                        if item.expense_account not in list_account:
                            list_account.append(item.expense_account)

                        sle = {}

                        expense_account = item.expense_account
                        if item.purchase_receipt and frappe.get_doc("Item",item.item_code).is_stock_item:
                            self.stock_received_but_not_billed = self.get_company_default("stock_received_but_not_billed")
                            expense_account = self.stock_received_but_not_billed
                        print(self.remarks)
                        
                        sle_new = frappe.new_doc("GL Entry Custom")
                        sle_new.update({
                            "posting_date": self.posting_date,
                            "account": expense_account,
                            "debit": flt(item.base_net_amount + item.item_tax_amount, item.precision("base_net_amount")),
                            "credit": 0 ,
                            "remarks": item.user_remark,
                            "voucher_type":"Purchase Invoice",
                            "no_voucher": self.name,
                            "item_code" : item.item_code,
                            "item_name": item.item_name,
                            "branch": item.branch,
                            "cost_center": item.cost_center,
                            "tax_or_non_tax": self.tax_or_non_tax,
                            "doc_remarks":self.remarks,
                            "voucher_detail_no": item.name
                        })  
                        if item.name not in list_item:
                            list_item.append(item.name)
                        sle_new.save(ignore_permissions=True)
            else:
                print(self.supplier)
                sle_new = frappe.new_doc("GL Entry Custom")
                sle_new.update({
                    "posting_date": baris_query[0],
                    "account": baris_query[1],
                    "debit": baris_query[2],
                    "credit": baris_query[3],
                    "party_type": baris_query[4],
                    "party": baris_query[5],
                    "remarks": baris_query[6],
                    "doc_remarks":self.remarks,
                    "voucher_type":baris_query[7],
                    "no_voucher":baris_query[8],
                    "branch": baris_query[10],
                    "cost_center": baris_query[11],
                    "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
                })  
                sle_new.save(ignore_permissions=True)
            

        print(nomor_doc[0])
        frappe.db.commit()

@frappe.whitelist()
def create_view_ledger_expense_claim(document,method):
    doc_list = frappe.db.sql(""" SELECT voucher_no FROM `tabGL Entry` WHERE is_cancelled = 0
    and voucher_type = "Expense Claim"
    and voucher_no = "{}" 
    and voucher_no not in (select no_voucher FROM `tabGL Entry Custom`)
    GROUP BY voucher_no """.format(document.name))
    for nomor_doc in doc_list:
        self = frappe.get_doc("Expense Claim", nomor_doc[0])
        frappe.db.sql(""" DELETE FROM `tabGL Entry Custom` WHERE no_voucher = "{}" """.format(self.name))
        gl_list = frappe.db.sql(""" 
                SELECT posting_date,
                 account,
                 debit,
                 credit,
                 party_type,
                 party,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', 1)),
                 voucher_type,
                 voucher_no,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', -1)),
                 branch,
                 cost_center,
                 name 
                 FROM `tabGL Entry` WHERE voucher_no = "{}" GROUP BY account""".format(self.name))
        list_item = []
        for baris_query in gl_list:
            if frappe.utils.flt(baris_query[2]) > 0:
                nyari = 0
                for row_expense in self.expenses:
                    exp_typ = frappe.get_doc("Expense Claim Type",row_expense.expense_type)
                    account = exp_typ.accounts[0].default_account
                    
                    if account == baris_query[1]:
                        nyari = 1
                        sle_new = frappe.new_doc("GL Entry Custom")
                        sle_new.update({
                            "posting_date": baris_query[0],
                            "account": baris_query[1],
                            "debit": row_expense.sanctioned_amount,
                            "credit": baris_query[3],
                            "party_type": baris_query[4],
                            "party": baris_query[5],
                            "remarks": str(row_expense.get("description")) + "|" + str(row_expense.get("user_remark")) ,
                            "doc_remarks": self.remark,
                            "voucher_type":baris_query[7],
                            "no_voucher":baris_query[8],
                            "branch": row_expense.branch,
                            "cost_center": row_expense.cost_center,
                            "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax,
                            "voucher_detail_no": row_expense.name
                        })  
                        if row_expense.name not in list_item:
                            list_item.append(row_expense.name)
                        sle_new.save(ignore_permissions=True)

                if nyari == 0:
                    sle_new = frappe.new_doc("GL Entry Custom")
                    sle_new.update({
                        "posting_date": baris_query[0],
                        "account": baris_query[1],
                        "debit": baris_query[2],
                        "credit": baris_query[3],
                        "party_type": baris_query[4],
                        "party": baris_query[5],
                        "remarks": baris_query[6],
                        "doc_remarks": self.remark,
                        "voucher_type":baris_query[7],
                        "no_voucher":baris_query[8],
                        "branch": baris_query[10],
                        "cost_center": baris_query[11],
                        "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
                    })  
                    sle_new.save(ignore_permissions=True)
            else:
                sle_new = frappe.new_doc("GL Entry Custom")
                sle_new.update({
                    "posting_date": baris_query[0],
                    "account": baris_query[1],
                    "debit": baris_query[2],
                    "credit": baris_query[3],
                    "party_type": baris_query[4],
                    "party": baris_query[5],
                    "remarks": baris_query[6],
                    "doc_remarks": self.remark,
                    "voucher_type":baris_query[7],
                    "no_voucher":baris_query[8],
                    "branch": baris_query[10],
                    "cost_center": baris_query[11],
                    "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
                })  
                sle_new.save(ignore_permissions=True)

        print(nomor_doc[0])
        frappe.db.commit()

@frappe.whitelist()
def create_view_ledger_sales_invoice(document,method):
    doc_list = frappe.db.sql(""" SELECT voucher_no FROM `tabGL Entry` WHERE is_cancelled = 0
    and voucher_type = "Sales Invoice"
    and voucher_no = "{}" 
    and voucher_no not in (select no_voucher FROM `tabGL Entry Custom`)
    GROUP BY voucher_no """.format(document.name))
    for nomor_doc in doc_list:
        self = frappe.get_doc("Sales Invoice", nomor_doc[0])
        frappe.db.sql(""" DELETE FROM `tabGL Entry Custom` WHERE no_voucher = "{}" """.format(self.name))
        gl_list = frappe.db.sql(""" 
                SELECT posting_date,
                 account,
                 debit,
                 credit,
                 party_type,
                 party,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', 1)),
                 voucher_type,
                 voucher_no,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', -1)),
                 branch,
                 cost_center,
                 name 
                 FROM `tabGL Entry` WHERE voucher_no = "{}" GROUP BY account""".format(self.name))
        list_transaction = []
        list_item = []
        for baris_query in gl_list:
            self = frappe.get_doc("Sales Invoice", baris_query[8])
                
            pakai_di_item = 0
            for baris in self.items:
                if baris.expense_account == baris_query[1]:
                    pakai_di_item = 1

            if pakai_di_item == 1:
                if baris_query[8] not in list_transaction:
                    list_transaction.append(baris_query[8])
                    grand_total = self.rounded_total if (self.rounding_adjustment and self.rounded_total) else self.grand_total
                    base_grand_total = flt(self.base_rounded_total if (self.base_rounding_adjustment and self.base_rounded_total)
                        else self.base_grand_total, self.precision("base_grand_total")) 

                    list_account = []
                    for item in self.get("items"):
                        
                        if item.expense_account not in list_account:
                            list_account.append(item.expense_account)

                        sle = {}

                        expense_account = item.expense_account
                        if item.delivery_note and frappe.get_doc("Item",item.item_code).is_stock_item:
                            self.stock_received_but_not_billed = self.get_company_default("stock_received_but_not_billed")
                            expense_account = self.stock_received_but_not_billed

                        sle_new = frappe.new_doc("GL Entry Custom")
                        sle_new.update({
                            "posting_date": self.posting_date,
                            "account": expense_account,
                            "credit": flt(item.base_amount, item.precision("base_net_amount")),
                            "debit": 0 ,
                            "remarks": item.user_remark,
                            "doc_remarks":self.remarks,
                            "voucher_type":"Sales Invoice",
                            "no_voucher": self.name,
                            "item_code" : item.item_code,
                            "item_name": item.item_name,
                            "branch": item.branch,
                            "cost_center": item.cost_center,
                            "tax_or_non_tax": self.tax_or_non_tax,
                            "voucher_detail_no": item.name
                        })  
                        if item.name not in list_item:
                            list_item.append(item.name)
                        sle_new.save(ignore_permissions=True)
            else:
                sle_new = frappe.new_doc("GL Entry Custom")
                sle_new.update({
                    "posting_date": baris_query[0],
                    "account": baris_query[1],
                    "debit": baris_query[2],
                    "credit": baris_query[3],
                    "party_type": baris_query[4],
                    "party": baris_query[5],
                    "remarks": baris_query[6],
                    "doc_remarks": baris_query[9],
                    "voucher_type":baris_query[7],
                    "no_voucher":baris_query[8],
                    "branch": baris_query[10],
                    "cost_center": baris_query[11],
                    "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
                })  
                sle_new.save(ignore_permissions=True)

        print(nomor_doc[0])
        frappe.db.commit()

@frappe.whitelist()
def create_view_ledger_stock_entry(document,method):
    document = frappe.get_doc("Stock Entry", document)
    doc_list = frappe.db.sql(""" SELECT voucher_no FROM `tabGL Entry` WHERE is_cancelled = 0
    and voucher_type = "Stock Entry" 
    and voucher_no = "{}"
    and voucher_no not in (select no_voucher FROM `tabGL Entry Custom`)
    GROUP BY voucher_no """.format(document.name))

    for nomor_doc in doc_list:
        self = frappe.get_doc("Stock Entry", nomor_doc[0])  
        frappe.db.sql(""" DELETE FROM `tabGL Entry Custom` WHERE no_voucher = "{}" """.format(self.name))
        gl_list = frappe.db.sql(""" 
                SELECT posting_date,
                 account,
                 debit,
                 credit,
                 party_type,
                 party,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', 1)),
                 voucher_type,
                 voucher_no,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', -1)),
                 branch,
                 cost_center,
                 name 
                 FROM `tabGL Entry` WHERE voucher_no = "{}" 
                 GROUP BY account
                 """.format(self.name))
        list_transaction = []
        list_item = []
        for baris_query in gl_list:
            self = frappe.get_doc("Stock Entry", baris_query[8])  

            pakai_di_item = 0
            for baris in self.items:
                if baris.s_warehouse and not baris.t_warehouse:
                    if frappe.get_doc("Warehouse",baris.s_warehouse).account == baris_query[1]:
                        pakai_di_item = 1
                elif not baris.s_warehouse and baris.t_warehouse:
                    if frappe.get_doc("Warehouse",baris.t_warehouse).account == baris_query[1]:
                        pakai_di_item = 1

            if pakai_di_item == 1:
                if baris_query[8] not in list_transaction:
                    list_transaction.append(baris_query[8])
                    list_account = []
                    for item in self.get("items"):

                        if item.s_warehouse and not item.t_warehouse:
                            if frappe.get_doc("Warehouse", item.s_warehouse).account not in list_account:
                                list_account.append(frappe.get_doc("Warehouse", item.s_warehouse).account)
                        elif item.t_warehouse and not item.s_warehouse:
                            if frappe.get_doc("Warehouse", item.t_warehouse).account not in list_account:
                                list_account.append(frappe.get_doc("Warehouse", item.t_warehouse).account)

                        sle = {}

                        if item.s_warehouse and not item.t_warehouse:
                            expense_account = frappe.get_doc("Warehouse", item.s_warehouse).account
                        elif item.t_warehouse and not item.s_warehouse:
                            expense_account = frappe.get_doc("Warehouse", item.t_warehouse).account
                    
                        if item.s_warehouse and not item.t_warehouse:
                            sle_new = frappe.new_doc("GL Entry Custom")
                            sle_new.update({
                                "posting_date": self.posting_date,
                                "account": expense_account,
                                "credit": item.valuation_rate * item.transfer_qty,
                                "debit": 0 ,
                                "remarks": item.user_remark,
                                "voucher_type":"Stock Entry",
                                "no_voucher": self.name,
                                "item_code" : item.item_code,
                                "item_name": item.item_name,
                                "branch": item.branch,
                                "cost_center": item.cost_center,
                                "tax_or_non_tax": self.tax_or_non_tax,
                                "doc_remarks":self.remarks,
                                "voucher_detail_no": item.name
                            })  
                            if item.name not in list_item:
                                list_item.append(item.name)

                            sle_new.save(ignore_permissions=True)
                        elif not item.s_warehouse and item.t_warehouse:
                            sle_new = frappe.new_doc("GL Entry Custom")
                            sle_new.update({
                                "posting_date": self.posting_date,
                                "account": expense_account,
                                "debit": item.valuation_rate * item.transfer_qty,
                                "credit": 0 ,
                                "remarks": item.user_remark,
                                "voucher_type":"Stock Entry",
                                "no_voucher": self.name,
                                "item_code" : item.item_code,
                                "item_name": item.item_name,
                                "branch": item.branch,
                                "cost_center": item.cost_center,
                                "tax_or_non_tax": self.tax_or_non_tax,
                                "doc_remarks":self.remarks,
                                "voucher_detail_no": item.name
                            })  
                            if item.name not in list_item:
                                list_item.append(item.name)

                            sle_new.save(ignore_permissions=True)

            else:
                sle_new = frappe.new_doc("GL Entry Custom")
                sle_new.update({
                    "posting_date": baris_query[0],
                    "account": baris_query[1],
                    "debit": baris_query[2],
                    "credit": baris_query[3],
                    "party_type": baris_query[4],
                    "party": baris_query[5],
                    "remarks": baris_query[6],
                    "doc_remarks":self.remarks,
                    "voucher_type":baris_query[7],
                    "no_voucher":baris_query[8],
                    "branch": baris_query[10],
                    "cost_center": baris_query[11],
                    "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
                })  
                sle_new.save(ignore_permissions=True)

        print(nomor_doc[0])
        frappe.db.commit()

@frappe.whitelist()
def create_gl_custom_delivery_note():
    doc_list = frappe.db.sql(""" SELECT voucher_no FROM `tabGL Entry` WHERE is_cancelled = 0
        and voucher_type = "Delivery Note" 
        and voucher_no not in (select no_voucher FROM `tabGL Entry Custom` WHERE voucher_type = "Delivery Note")
        GROUP BY voucher_no """)

    for nomor_doc in doc_list:
        self = frappe.get_doc("Delivery Note", nomor_doc[0])
        frappe.db.sql(""" DELETE FROM `tabGL Entry Custom` WHERE no_voucher = "{}" """.format(self.name))
        gl_list = frappe.db.sql(""" 
                SELECT posting_date,
                 account,
                 debit,
                 credit,
                 party_type,
                 party,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', 1)),
                 voucher_type,
                 voucher_no,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', -1)),
                 branch,
                 cost_center,
                 name 
                 FROM `tabGL Entry` WHERE voucher_no = "{}" 
                 GROUP BY account
                 """.format(self.name))
        list_transaction = []
        list_item = []
        for baris_query in gl_list:
            self = frappe.get_doc("Delivery Note", baris_query[8])
                
            pakai_di_item = 0
            for baris in self.items:
                if baris.warehouse:
                    if frappe.get_doc("Warehouse",baris.warehouse).account == baris_query[1]:
                        pakai_di_item = 1

            if pakai_di_item == 1:
                if baris_query[8] not in list_transaction:
                    list_transaction.append(baris_query[8])
                    grand_total = self.rounded_total if (self.rounding_adjustment and self.rounded_total) else self.grand_total
                    base_grand_total = flt(self.base_rounded_total if (self.base_rounding_adjustment and self.base_rounded_total)
                        else self.base_grand_total, self.precision("base_grand_total")) 

                    list_account = []
                    for item in self.get("items"):
                        doc_item = frappe.get_doc("Item", item.item_code)
                        if doc_item.is_stock_item:
                            if item.warehouse:
                                if frappe.get_doc("Warehouse", item.warehouse).account not in list_account:
                                    list_account.append(frappe.get_doc("Warehouse", item.warehouse).account)

                            sle = {}

                            expense_account = frappe.get_doc("Warehouse", item.warehouse).account

                            sle_new = frappe.new_doc("GL Entry Custom")
                            sle_new.update({
                                "posting_date": self.posting_date,
                                "account": expense_account,
                                "credit": flt(item.base_net_amount, item.precision("base_net_amount")),
                                "debit": 0 ,
                                "remarks": item.user_remark,
                                "voucher_type":"Delivery Note",
                                "no_voucher": self.name,
                                "item_code" : item.item_code,
                                "item_name": item.item_name,
                                "branch": item.branch,
                                "cost_center": item.cost_center,
                                "tax_or_non_tax": self.tax_or_non_tax,
                                "voucher_detail_no": item.name
                            })  
                            sle_new.save(ignore_permissions=True)
            else:
                sle_new = frappe.new_doc("GL Entry Custom")
                sle_new.update({
                    "posting_date": baris_query[0],
                    "account": baris_query[1],
                    "debit": baris_query[2],
                    "credit": baris_query[3],
                    "party_type": baris_query[4],
                    "party": baris_query[5],
                    "remarks": baris_query[6],
                    "doc_remarks": baris_query[9],
                    "voucher_type":baris_query[7],
                    "no_voucher":baris_query[8],
                    "branch": baris_query[10],
                    "cost_center": baris_query[11],
                    "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
                })  
                sle_new.save(ignore_permissions=True)

        print(nomor_doc[0])
        frappe.db.commit()

@frappe.whitelist()
def create_gl_custom_delivery_note_by_name(self,method):
    doc_list = frappe.db.sql(""" SELECT voucher_no FROM `tabGL Entry` WHERE is_cancelled = 0
        and voucher_type = "Delivery Note" 
        and voucher_no = "{}"
        GROUP BY voucher_no """.format(self))

    for nomor_doc in doc_list:
        self = frappe.get_doc("Delivery Note", nomor_doc[0])
        frappe.db.sql(""" DELETE FROM `tabGL Entry Custom` WHERE no_voucher = "{}" """.format(self.name))
        gl_list = frappe.db.sql(""" 
                SELECT posting_date,
                 account,
                 debit,
                 credit,
                 party_type,
                 party,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', 1)),
                 voucher_type,
                 voucher_no,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', -1)),
                 branch,
                 cost_center,
                 name 
                 FROM `tabGL Entry` WHERE voucher_no = "{}" 
                 GROUP BY account
                 """.format(self.name))
        list_transaction = []
        list_item = []
        for baris_query in gl_list:
            self = frappe.get_doc("Delivery Note", baris_query[8])
                
            pakai_di_item = 0
            for baris in self.items:
                if baris.warehouse:
                    if frappe.get_doc("Warehouse",baris.warehouse).account == baris_query[1]:
                        pakai_di_item = 1

            if pakai_di_item == 1:
                if baris_query[8] not in list_transaction:
                    list_transaction.append(baris_query[8])
                    grand_total = self.rounded_total if (self.rounding_adjustment and self.rounded_total) else self.grand_total
                    base_grand_total = flt(self.base_rounded_total if (self.base_rounding_adjustment and self.base_rounded_total)
                        else self.base_grand_total, self.precision("base_grand_total")) 

                    list_account = []
                    for item in self.get("items"):
                        doc_item = frappe.get_doc("Item", item.item_code)
                        if doc_item.is_stock_item:
                            if item.warehouse:
                                if frappe.get_doc("Warehouse", item.warehouse).account not in list_account:
                                    list_account.append(frappe.get_doc("Warehouse", item.warehouse).account)

                            sle = {}

                            expense_account = frappe.get_doc("Warehouse", item.warehouse).account

                            sle_new = frappe.new_doc("GL Entry Custom")
                            sle_new.update({
                                "posting_date": self.posting_date,
                                "account": expense_account,
                                "credit": flt(item.base_net_amount, item.precision("base_net_amount")),
                                "debit": 0 ,
                                "remarks": item.user_remark,
                                "voucher_type":"Delivery Note",
                                "no_voucher": self.name,
                                "item_code" : item.item_code,
                                "item_name": item.item_name,
                                "branch": item.branch,
                                "cost_center": item.cost_center,
                                "tax_or_non_tax": self.tax_or_non_tax,
                                "voucher_detail_no": item.name
                            })  
                            sle_new.save(ignore_permissions=True)
            else:
                sle_new = frappe.new_doc("GL Entry Custom")
                sle_new.update({
                    "posting_date": baris_query[0],
                    "account": baris_query[1],
                    "debit": baris_query[2],
                    "credit": baris_query[3],
                    "party_type": baris_query[4],
                    "party": baris_query[5],
                    "remarks": baris_query[6],
                    "doc_remarks": baris_query[9],
                    "voucher_type":baris_query[7],
                    "no_voucher":baris_query[8],
                    "branch": baris_query[10],
                    "cost_center": baris_query[11],
                    "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
                })  
                sle_new.save(ignore_permissions=True)

        print(nomor_doc[0])
        frappe.db.commit()

@frappe.whitelist()
def create_gl_custom_purchase_receipt():
    doc_list = frappe.db.sql(""" SELECT voucher_no FROM `tabGL Entry` WHERE is_cancelled = 0
        and voucher_type = "Purchase Receipt" 
        and voucher_no not in (select no_voucher FROM `tabGL Entry Custom` WHERE voucher_type = "Purchase Receipt")
        GROUP BY voucher_no """)

    for nomor_doc in doc_list:
        self = frappe.get_doc("Purchase Receipt", nomor_doc[0])
        frappe.db.sql(""" DELETE FROM `tabGL Entry Custom` WHERE no_voucher = "{}" """.format(self.name))
        gl_list = frappe.db.sql(""" 
                SELECT posting_date,
                 account,
                 debit,
                 credit,
                 party_type,
                 party,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', 1)),
                 voucher_type,
                 voucher_no,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', -1)),
                 branch,
                 cost_center,
                 name 
                 FROM `tabGL Entry` WHERE voucher_no = "{}" 
                 GROUP BY account
                 """.format(self.name))
        list_transaction = []
        list_item = []
        for baris_query in gl_list:
            self = frappe.get_doc("Purchase Receipt", baris_query[8])

            pakai_di_item = 0
            for baris in self.items:
                if baris.warehouse:
                    if frappe.get_doc("Warehouse",baris.warehouse).account == baris_query[1]:
                        pakai_di_item = 1

            if pakai_di_item == 1:
                if baris_query[8] not in list_transaction:
                    list_transaction.append(baris_query[8])
                    grand_total = self.rounded_total if (self.rounding_adjustment and self.rounded_total) else self.grand_total
                    base_grand_total = flt(self.base_rounded_total if (self.base_rounding_adjustment and self.base_rounded_total)
                        else self.base_grand_total, self.precision("base_grand_total")) 

                    list_account = []
                    for item in self.get("items"):

                        if item.warehouse:
                            if frappe.get_doc("Warehouse", item.warehouse).account not in list_account:
                                list_account.append(frappe.get_doc("Warehouse", item.warehouse).account)

                        sle = {}

                        expense_account = frappe.get_doc("Warehouse", item.warehouse).account

                        sle_new = frappe.new_doc("GL Entry Custom")
                        sle_new.update({
                            "posting_date": self.posting_date,
                            "account": expense_account,
                            "debit": flt(item.base_net_amount + item.item_tax_amount, item.precision("base_net_amount")),
                            "credit": 0 ,
                            "remarks": item.get("user_remark"),
                            "voucher_type":"Purchase Receipt",
                            "no_voucher": self.name,
                            "item_code" : item.item_code,
                            "item_name": item.item_name,
                            "branch": item.branch,
                            "cost_center": item.cost_center,
                            "tax_or_non_tax": self.tax_or_non_tax,
                            "doc_remarks":self.remarks,
                            "voucher_detail_no": item.name
                        })  
                        sle_new.save(ignore_permissions=True)
            else:
                sle_new = frappe.new_doc("GL Entry Custom")
                sle_new.update({
                    "posting_date": baris_query[0],
                    "account": baris_query[1],
                    "debit": baris_query[2],
                    "credit": baris_query[3],
                    "party_type": baris_query[4],
                    "party": baris_query[5],
                    "remarks": baris_query[6],
                    "doc_remarks": baris_query[9],
                    "voucher_type":baris_query[7],
                    "no_voucher":baris_query[8],
                    "branch": baris_query[10],
                    "cost_center": baris_query[11],
                    "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax,
                    "doc_remarks":self.remarks
                })  
                sle_new.save(ignore_permissions=True)

        print(nomor_doc[0])
        frappe.db.commit()

@frappe.whitelist()
def create_gl_custom_purchase_receipt_by_name(self,method):
    doc_list = frappe.db.sql(""" SELECT voucher_no FROM `tabGL Entry` WHERE is_cancelled = 0
        and voucher_type = "Purchase Receipt" 
        and voucher_no = "{}"
        GROUP BY voucher_no """.format(self))

    for nomor_doc in doc_list:
        self = frappe.get_doc("Purchase Receipt", nomor_doc[0])
        frappe.db.sql(""" DELETE FROM `tabGL Entry Custom` WHERE no_voucher = "{}" """.format(self.name))
        gl_list = frappe.db.sql(""" 
                SELECT posting_date,
                 account,
                 debit,
                 credit,
                 party_type,
                 party,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', 1)),
                 voucher_type,
                 voucher_no,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', -1)),
                 branch,
                 cost_center,
                 name 
                 FROM `tabGL Entry` WHERE voucher_no = "{}" 
                 GROUP BY account
                 """.format(self.name))
        list_transaction = []
        list_item = []
        for baris_query in gl_list:
            self = frappe.get_doc("Purchase Receipt", baris_query[8])

            pakai_di_item = 0
            for baris in self.items:
                if baris.warehouse:
                    if frappe.get_doc("Warehouse",baris.warehouse).account == baris_query[1]:
                        pakai_di_item = 1

            if pakai_di_item == 1:
                if baris_query[8] not in list_transaction:
                    list_transaction.append(baris_query[8])
                    grand_total = self.rounded_total if (self.rounding_adjustment and self.rounded_total) else self.grand_total
                    base_grand_total = flt(self.base_rounded_total if (self.base_rounding_adjustment and self.base_rounded_total)
                        else self.base_grand_total, self.precision("base_grand_total")) 

                    list_account = []
                    for item in self.get("items"):

                        if item.warehouse:
                            if frappe.get_doc("Warehouse", item.warehouse).account not in list_account:
                                list_account.append(frappe.get_doc("Warehouse", item.warehouse).account)

                        sle = {}

                        expense_account = frappe.get_doc("Warehouse", item.warehouse).account

                        sle_new = frappe.new_doc("GL Entry Custom")
                        sle_new.update({
                            "posting_date": self.posting_date,
                            "account": expense_account,
                            "debit": flt(item.base_net_amount + item.item_tax_amount, item.precision("base_net_amount")),
                            "credit": 0 ,
                            "remarks": item.get("user_remark"),
                            "voucher_type":"Purchase Receipt",
                            "no_voucher": self.name,
                            "item_code" : item.item_code,
                            "item_name": item.item_name,
                            "branch": item.branch,
                            "cost_center": item.cost_center,
                            "tax_or_non_tax": self.tax_or_non_tax,
                            "doc_remarks":self.remarks,
                            "voucher_detail_no": item.name
                        })  
                        sle_new.save(ignore_permissions=True)
            else:
                sle_new = frappe.new_doc("GL Entry Custom")
                sle_new.update({
                    "posting_date": baris_query[0],
                    "account": baris_query[1],
                    "debit": baris_query[2],
                    "credit": baris_query[3],
                    "party_type": baris_query[4],
                    "party": baris_query[5],
                    "remarks": baris_query[6],
                    "doc_remarks": baris_query[9],
                    "voucher_type":baris_query[7],
                    "no_voucher":baris_query[8],
                    "branch": baris_query[10],
                    "cost_center": baris_query[11],
                    "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax,
                    "doc_remarks":self.remarks
                })  
                sle_new.save(ignore_permissions=True)

        print(nomor_doc[0])
        frappe.db.commit()
@frappe.whitelist()
def bersih():
    frappe.db.sql(""" DELETE FROM `tabGL Entry Custom` WHERE NAME IN (SELECT gl.`name` FROM `tabJournal Entry Account` jea
        JOIN `tabGL Entry Custom` gl ON gl.`voucher_detail_no` = jea.name) """)

    frappe.db.commit()
    print(frappe.get_doc("Company","GIAS").nama_cabang)

@frappe.whitelist()
def create_gl_custom_journal_entry_by_name(name):
    doc_list = frappe.db.sql(""" SELECT voucher_no FROM `tabGL Entry` WHERE is_cancelled = 0
        and voucher_type = "Journal Entry" 
        and voucher_no = "{}"
        GROUP BY voucher_no """.format(name))

    for nomor_doc in doc_list:
        self = frappe.get_doc("Journal Entry", nomor_doc[0])
        frappe.db.sql(""" DELETE FROM `tabGL Entry Custom` WHERE no_voucher = "{}" """.format(self.name))
        
        for baris_acc in self.accounts:
            sle_new = frappe.new_doc("GL Entry Custom")
            sle_new.update({
                "posting_date": self.posting_date,
                "account": baris_acc.account,
                "debit": baris_acc.debit,
                "credit": baris_acc.credit,
                "party_type": baris_acc.get("party_type"),
                "party": baris_acc.get("party"),
                "remarks": baris_acc.get("user_remark"),
                "doc_remarks": self.remark,
                "voucher_type": "Journal Entry",
                "no_voucher": self.name,
                "branch": baris_acc.get("branch"),
                "cost_center": baris_acc.get("cost_center"),
                "tax_or_non_tax": self.tax_or_non_tax,
                "voucher_detail_no": baris_acc.name
            })  
            sle_new.save(ignore_permissions=True)
            
        print(nomor_doc[0])
        frappe.db.commit()

@frappe.whitelist()
def create_gl_custom_journal_entry():
    doc_list = frappe.db.sql(""" SELECT voucher_no FROM `tabGL Entry` WHERE is_cancelled = 0
        and voucher_type = "Journal Entry" 
        and voucher_no not in (select no_voucher FROM `tabGL Entry Custom` WHERE voucher_type = "Journal Entry")
        GROUP BY voucher_no """)

    for nomor_doc in doc_list:
        self = frappe.get_doc("Journal Entry", nomor_doc[0])
        frappe.db.sql(""" DELETE FROM `tabGL Entry Custom` WHERE no_voucher = "{}" """.format(self.name))
        
        for baris_acc in self.accounts:
            sle_new = frappe.new_doc("GL Entry Custom")
            sle_new.update({
                "posting_date": self.posting_date,
                "account": baris_acc.account,
                "debit": baris_acc.debit,
                "credit": baris_acc.credit,
                "party_type": baris_acc.get("party_type"),
                "party": baris_acc.get("party"),
                "remarks": baris_acc.get("user_remark"),
                "doc_remarks": self.remark,
                "voucher_type": "Journal Entry",
                "no_voucher": self.name,
                "branch": baris_acc.get("branch"),
                "cost_center": baris_acc.get("cost_center"),
                "tax_or_non_tax": self.tax_or_non_tax,
                "voucher_detail_no": baris_acc.name
            })  
            sle_new.save(ignore_permissions=True)
            
        print(nomor_doc[0])
        frappe.db.commit()

@frappe.whitelist()
def create_gl_custom_payment_entry():
    gl_list = frappe.db.sql("""         
       SELECT
       posting_date,

       account,
       debit,
       credit,
       party_type,
       party,
       TRIM(SUBSTRING_INDEX(remarks, 'Note:', 1)),

       voucher_type,
       voucher_no,
       TRIM(SUBSTRING_INDEX(remarks, 'Note:', -1)),
       branch,
       cost_center,
       name

      FROM `tabGL Entry` 
      WHERE 
      is_cancelled = 0
      and voucher_type IN ("Payment Entry")
      and docstatus = 1
      and voucher_no not in (select no_voucher FROM `tabGL Entry Custom` WHERE voucher_type = "Payment Entry")

      GROUP BY account, voucher_no """)

    for baris_query in gl_list:
        sle_new = frappe.new_doc("GL Entry Custom")
        sle_new.update({
              "posting_date": baris_query[0],
              "account": baris_query[1],
              "debit": baris_query[2],
              "credit": baris_query[3],
              "party_type": baris_query[4],
              "party": baris_query[5],
              "doc_remarks": baris_query[6],
              "remarks": "",
              "voucher_type":baris_query[7],
              "no_voucher":baris_query[8],
              "branch": baris_query[10],
              "cost_center": baris_query[11],
              "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax,
        })  
        sle_new.save(ignore_permissions=True)
        print(baris_query[8])
        frappe.db.commit()

@frappe.whitelist()
def delet_view_ledger(self,method):
    frappe.db.sql(""" DELETE FROM `tabGL Entry Custom` WHERE no_voucher = "{}" and voucher_type = "{}" """.format(self.name,self.doctype))
    frappe.db.commit()