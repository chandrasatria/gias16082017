import frappe
import paramiko
import base64 
from base64 import decodebytes
import getpass
import os
import socket
import sys
import traceback
from paramiko.py3compat import input
import time

from os import listdir
from os.path import isfile, join

# # MAKE CONNECTION
# run ssh-keygen -t rsa to generate the id_rsa and id_rsa.pub files

# copy contents of id_rsa.pub into ~/.ssh/authorized_keys (on the target system)

# copy the id_rsa (private) keyfile onto the client machine

# (on the target I have mode 755 on .ssh/ and 644 on authorized_keys)

@frappe.whitelist()
def get_url():
	url = str(frappe.utils.get_url()).replace("http://","").replace("https://","")
	return url

@frappe.whitelist()
def make_dir():
	os.system('cd /home/frappe/frappe-bench/sites/backup && mkdir {}'.format(get_url()))

@frappe.whitelist()
def preparing_backup():
	url = get_url()
	print(str(url))
	os.system('cd /home/frappe/frappe-bench/ && rm -r /home/frappe/frappe-bench/sites/backup/{}/*'.format(url))
	os.system('cd /home/frappe/frappe-bench/ && bench --site {} backup --backup-path backup/{}/'.format(url,url))
	# stream = os.popen('cd /home/frappe/frappe-bench/sites/backup && ls')
	directory = '/home/frappe/frappe-bench/sites/backup/{}/'.format(url)

	onlyfiles = [f for f in listdir(directory) if isfile(join(directory, f)) and "sql.gz" in str(f) ]
	backup = onlyfiles[0]

	try:
		connect_to_tax_server(directory,backup)
		frappe.enqueue(method="addons.custom_standard.temp_method.success_message",timeout=2400, queue='default')
		success_message()
		
	except:
		frappe.db.sql(""" UPDATE `tabSingles` SET value = "Failed at {}" WHERE doctype = "Sync to Tax Server" AND field = "last_status" """.format(frappe.utils.now()))
		frappe.db.commit()
	

@frappe.whitelist()
def success_message()
	print(""" UPDATE `tabSingles` SET value = "Success at {}" WHERE doctype = "Sync to Tax Server" AND field = "last_status" """.format(frappe.utils.now()))
	frappe.db.sql(""" UPDATE `tabSingles` SET value = "Success at {}" WHERE doctype = "Sync to Tax Server" AND field = "last_status" """.format(frappe.utils.now()))
	frappe.db.commit()


@frappe.whitelist()
def connect_to_tax_server(directory,backup):
	hostname = "192.168.10.209"
	username = "root"
	command = "cd /home/frappe/frappe-bench && ls"
	nama_site = ""
	ambil_nama_site = frappe.db.sql("""  SELECT value FROM `tabSingles` WHERE field = "tax_server" """)
	if ambil_nama_site:
		if ambil_nama_site[0]:
			if ambil_nama_site[0][0]:
				nama_site = str(ambil_nama_site[0][0])

	key_dir = "/home/frappe/frappe-bench/apps/addons/addons/custom_standard/id_rsa"
	link = "{}{}".format(directory,backup)

	# try:
	# 	client=paramiko.SSHClient()
	# 	client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	# 	k = paramiko.RSAKey.from_private_key_file(key_dir)
	# 	client.connect(hostname, username=username, pkey = k)
		
	# 	print(link)
	# 	command = "rm /home/frappe/frappe-bench/sites/backup/* ".format(nama_site, link, nama_site)
	# 	stdin, stdout, stderr = client.exec_command(command)
	# 	lines = stdout.readlines()
	# 	print(lines)

	# 	ftp_client=client.open_sftp()
	# 	ftp_client.put(link,link)
	# 	ftp_client.close()

	# 	print("bench --site {} --force restore {}".format(nama_site, link))
	# 	command = "cd /home/frappe/frappe-bench && bench --site {} --force restore {} --mariadb-root-password gias2021## && bench --site {} migrate".format(nama_site, link, nama_site)
	# 	stdin, stdout, stderr = client.exec_command(command)
	# 	lines = stdout.readlines()
	# 	print(lines)

	# except Exception as e:
	# 	print("*** Caught exception: %s: %s" % (e.__class__, e))
	# 	traceback.print_exc()
	# 	try:
	# 		client.close()
	# 	except:
	# 		pass
	# 	sys.exit(1)

	try:
		client=paramiko.SSHClient()
		client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		k = paramiko.RSAKey.from_private_key_file(key_dir)
		client.connect(hostname, username=username, pkey = k)
		

		# DIKOMEN KARENA MASIH 1 SERVER
		# print(link)
		# command = "cd /home/frappe/frappe-bench/sites/backup/ && gunzip {}".format(link)
		# stdin, stdout, stderr = client.exec_command(command)
		# lines = stdout.readlines()
		# print(lines)
		command = "cd /home/frappe/frappe-bench/sites/backup && rm -r {}*".format(directory)
		stdin, stdout, stderr = client.exec_command(command)
		lines = stdout.readlines()
		print(command)
		
		print(link)
			# command = "rm /home/frappe/frappe-bench/sites/backup/* ".format(nama_site, link, nama_site)
			# stdin, stdout, stderr = client.exec_command(command)
			# lines = stdout.readlines()
			# print(lines)

		ftp_client=client.open_sftp()
		ftp_client.put(link,link)
		ftp_client.close()
		
		command = "cd /home/frappe/frappe-bench && bench set-maintenance-mode --site {} on".format(nama_site)
		stdin, stdout, stderr = client.exec_command(command)
		lines = stdout.readlines()
		print(command)
		time.sleep(1)

		command = "cd /home/frappe/frappe-bench && bench --site {} set-config pause_scheduler 1".format(nama_site)
		stdin, stdout, stderr = client.exec_command(command)
		lines = stdout.readlines()
		print(command)
		time.sleep(1)

		print("bench --site {} --force restore {}".format(nama_site, link))
		command = "cd /home/frappe/frappe-bench && bench --site {} --force restore {} --mariadb-root-password rahasiakita && bench --site {} migrate".format(nama_site, link, nama_site)
		stdin, stdout, stderr = client.exec_command(command)
		lines = stdout.readlines()
		print(command)
		time.sleep(1)

		command = "cd /home/frappe/frappe-bench && bench --site {} execute addons.custom_standard.temp_method.db_commit".format(nama_site)
		stdin, stdout, stderr = client.exec_command(command)
		lines = stdout.readlines()
		print(command)
		time.sleep(1)

		print("hapus non tax transactions")
		command = "cd /home/frappe/frappe-bench && bench --site {} execute addons.custom_standard.custom_tax_method.remove_tax_transactions".format(nama_site, link, nama_site)
		stdin, stdout, stderr = client.exec_command(command)
		lines = stdout.readlines()
		print(command)
		time.sleep(1)

		print("hapus email + auto repeat")
		command = "cd /home/frappe/frappe-bench && bench --site {} execute addons.custom_standard.custom_tax_method.remove_email".format(nama_site, link, nama_site)
		stdin, stdout, stderr = client.exec_command(command)
		lines = stdout.readlines()
		print(command)
		time.sleep(1)

		command = "cd /home/frappe/frappe-bench && bench --site {} execute addons.custom_standard.temp_method.db_commit".format(nama_site)
		stdin, stdout, stderr = client.exec_command(command)
		lines = stdout.readlines()
		print(command)
		time.sleep(1)

		print("bikin je tax")
		command = "cd /home/frappe/frappe-bench && bench --site {} execute addons.custom_standard.custom_tax_method.make_je_tax".format(nama_site, link, nama_site)
		stdin, stdout, stderr = client.exec_command(command)
		lines = stdout.readlines()
		print(command)
		time.sleep(1)

		command = "cd /home/frappe/frappe-bench && bench --site {} execute addons.custom_standard.temp_method.db_commit".format(nama_site)
		stdin, stdout, stderr = client.exec_command(command)
		lines = stdout.readlines()
		print(command)
		time.sleep(1)

		command = "cd /home/frappe/frappe-bench && bench --site {} set-config pause_scheduler 0".format(nama_site)
		stdin, stdout, stderr = client.exec_command(command)
		lines = stdout.readlines()
		print(command)
		time.sleep(1)

		command = "cd /home/frappe/frappe-bench && bench set-maintenance-mode --site {} off".format(nama_site)
		stdin, stdout, stderr = client.exec_command(command)
		lines = stdout.readlines()
		print(command)
		time.sleep(1)
	



	except Exception as e:
		print("*** Caught exception: %s: %s" % (e.__class__, e))
		traceback.print_exc()
		try:
			client.close()
		except:
			pass
		sys.exit(1)

	except pymysql.err.OperationalError as e:
		print("mysql timeout")
		sys.exit(1)

		