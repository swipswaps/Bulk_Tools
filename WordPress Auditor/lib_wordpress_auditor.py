#!/usr/bin/python
import sys
import os
import zipfile
import hashlib
import shutil
import string
import random
import re

# Configuration
tmp_dir = "/tmp/" #Example: /tmp/
log_dir = '/log/' #Example: /log/
ignored_extension = ['.jpg', '.png', '.gif', '.txt', '.md', '.js', '.po', '.mo', '.css'] #You can add your ignored extensions. Files with these extensions will not be audited.
xss_detection_beta = True #The XSS detection is in beta and it is possible to have many false positives. You can disable XSS detection with False parameter
# End Configuration

#Don't modification
uri = None
log = None
log_filename = None

def main():
	if len(sys.argv) < 2:
		print "Example: "
		print sys.argv[0] + " file.php"
		print sys.argv[0] + " pluginDir"
		print sys.argv[0] + " archive.zip"
		sys.exit()
	plugin = sys.argv[1]
	if len(sys.argv) == 3 and sys.argv[2] == "--active-log":
		global log
		log = 1
	if zipfile.is_zipfile(plugin):
		load_archive(plugin)
	else:
		load_plugin(plugin)
	if uri:
		echo(uri)

def version():
	return "V2.6"

def load_archive(plugin):
	global log
	archive_zip = zipfile.ZipFile(plugin)
	archive_info = zipfile.ZipInfo(plugin)
	hash_dir = hashlib.md5(str(archive_info)).hexdigest()
	archive_zip.extractall(tmp_dir + hash_dir)
	if not os.path.isdir(tmp_dir):
		os.mkdir(tmp_dir)
	echo("The archive as been unpacked in: " + tmp_dir + hash_dir)
	load_plugin(tmp_dir + hash_dir)
	shutil.rmtree(tmp_dir + hash_dir)
	echo("The temporary directory has been removed")

def load_plugin(plugin):
	global log
	if os.path.isfile(plugin):
		i = 0
		extension = os.path.splitext(plugin)
		global ignored_extension
		if not extension[1] in ignored_extension:
			echo("Audit file: " + plugin)
			read = load_php(plugin)
			auditing(read)
	elif os.path.isdir(plugin):
		for f in os.listdir(plugin):
			if plugin[len(plugin)-1:] != "/":
				plugin = plugin + "/"
			load_plugin(plugin + f)
	else:
		echo("The file does not exist!")
	

def load_php(plugin):
	if os.path.isfile(plugin):
		open_file = open(plugin,'r')
		reading = open_file.read()
		open_file.close()
		return reading

def csrf(content_file):
	global log
	strings_csrf = ["wp_create_nonce", "wp_verify_nonce", "settings_fields", "wp_nonce_field"]
	start = end = i = 0
	csrf = None
	while True:
		start = content_file.find("<form", end)
		end = content_file.find("</form>", start)
		if start != -1 and end != -1:
			csrf = 1
			while i < len(strings_csrf):
				if content_file.find(strings_csrf[i], start, end) != -1:
					csrf = 0
				i += 1
			i = 0
		else:
			break

	if csrf == 1:
		echo("Your plugin is potentially vulnerable to CSRF. For more informations: http://en.wikipedia.org/wiki/Cross-site_request_forgery", '\n\n', '')

def xss(content_file):
	global log
	strings_xss = ["esc_html", "esc_js", "esc_textarea", "esc_attr", "htmlspecialchars", "htmlentities"]
	start = end = i = 0
	xss = None
	while True:
		start = content_file.find("echo ", end)
		end = content_file.find(";", start)
		if start != -1 and end != -1 and content_file.find("$", start, end) != -1:
			xss = 1
			while i < len(strings_xss):
				if content_file.find(strings_xss[i], start, end) != -1:
					xss = 0
				i += 1
			if xss == 1:
				i = start_var = end_var = 0
				var = content_file[start+5:end]
				while True:
					start_var = content_file.find(var, end_var)
					end_var = content_file.find('\n',start_var)
					if start_var != -1 and end_var != -1:
						while i < len(strings_xss):
							if content_file.find(strings_xss[i], start_var, end_var) != -1:
								xss = 0
							i += 1
						i = 0
					else:
						break
		else:
			break

	if xss == 1:
		echo("Your plugin is potentially vulnerable to XSS. For more informations: https://en.wikipedia.org/wiki/Cross-site_scripting", '\r\n', '')
		
def sqli(content_file):
	global log
	strings_sqli = ["$wpdb->get_results","$wpdb->query"]
	i = sqli = 0
	while i < len(strings_sqli):
		if content_file.find(strings_sqli[i]) != -1 and content_file.find("$wpdb->prepare") == -1:
			sqli = 1
		i += 1
	if sqli == 1:
		echo("Your plugin is potentially vulnerable to SQL Injection. For more informations: http://en.wikipedia.org/wiki/SQL_injection", '\r\n', '')
		
def auditing(content_file):
	csrf(content_file)
	sqli(content_file)
	if xss_detection_beta == True:
		xss(content_file)
	uri_extract(content_file)
	return 0

def uri_extract(content_file):
	string_uri = "Author URI:"
	start = content_file.find(string_uri)
	if start != -1:
		global uri
		end = content_file.find("\n", start)
		uri = content_file[start:end]

def log_rand_name():
	len_name = 15
	i = 0
	name = random.choice(string.letters)
	while i != len_name:
		name = name + random.choice(string.letters)
		i = i + 1
	return name

def echo(string, crlf = "\r\n", crlf_print = '\r\n'):
	global log_filename, log_dir, log
	print crlf_print + string
	if log:
		if not log_filename:
			log_filename = log_rand_name() + '.txt'
			print "\nYour file log is " + log_filename
		if not os.path.isdir(log_dir):
			os.mkdir(log_dir)
		if not os.path.isfile(log_dir + log_filename):
			crlf = ''
		file_log_open = open(log_dir + log_filename, 'a+')
		file_log_open.write(crlf + string)
		file_log_open.close()
