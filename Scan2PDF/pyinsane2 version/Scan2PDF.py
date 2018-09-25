#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Scan2PDF.py
#  
#  Scan a Document and Output to a PDF File
#    with Optional OCR
#
#	Requires: 	Python3
#				PySimpleGUI - pip3 install PySimpleGUI
#				Tkinter		- System Package python3-tk
#				pyocr		- pip3 install pyocr
#				pyinsane2	- pip3 install pyinsane2
#				Pillow		- pip3 install Pillow
#				pypdftk		- pip3 install pypdftk
#				img2pdf		- pip3 install img2pdf
#				playsound 	- pip3 install playsound (audio feedback)
#	Optional: 	Sounds from Package 'sound-theme-freedesktop' or similar
#				Windows Sounds from C:\Windows\Media\
#				A PDF Viewer of Some Sort, e.g., Adobe PDF Reader, MuPDF, Evince
#  
#  Copyright 2018 Gregory W. Russell <grussell86@yahoo.com>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  


def main(args):
	import PySimpleGUI as sg
	import pyinsane2
	import PIL.Image
	import pyocr
	import pypdftk
	import img2pdf
	import subprocess
	import shutil
	import tempfile
	import datetime
	import time
	import re
	import os
	from playsound import playsound

	def Launcher():
		# Output Location for Scanned Document - PDF Folder in Home Directory
		outputdir = os.path.join(os.path.expanduser('~'), 'PDF')

		if os.path.exists(outputdir) == False:
			os.mkdir(outputdir)
		
		# Set Window Options
		sg.SetOptions(element_padding=(10,0))
		
		# Build the Input window
		with sg.Window('Scan Document to PDF',default_button_element_size=(8,1),auto_size_buttons=True) as window:
			layout = [[sg.Frame('Document Source',[[
					  sg.Radio('Scanner Glass', 'RADIO1', key='glass'), sg.Radio('Automatic Document Feeder', 'RADIO1', key='adf', default=True),]]),
					   sg.ReadFormButton('Clear', key='Clear'), sg.ReadFormButton('Scan Document', bind_return_key=True, key='Scan')],
					  [sg.Frame('Options',[
					  [sg.Checkbox('OCR Document after Scanning', size=(26,1), key='ocr', default=True), sg.Checkbox('Open Document after Scanning', key='view', default=True)],
					  [sg.Checkbox('Letter Size Paper', size=(26,1), key='letter', default=True), sg.Checkbox('Color', key='color', default=False)]])],
					  [sg.Text('Status:', size=(15, 1))],
					  [sg.Multiline(size=(100,35), key='output', background_color='#ECECEC', autoscroll=True, focus=True)],
					  ]					 					  
			
			# Create the window and Show It
			window.LayoutAndRead(layout, non_blocking=True)		# Create a Non-Blocking window to Allow for Updates in Multiline Output
			window.FindElement('output').Update(disabled=True) 	# Disable Input to Output Status Field
			
			# Loop Taking in User Input and Using It
			while True:
				(button, values) = window.ReadNonBlocking()
				if values is None or button == 'Exit':	# If the X Button or Exit Button is Clicked, Just Exit
					break
				elif button == 'Clear':					# Reset Controls to Their Default Values or Exit If ButtonText is 'Exit'
					if window.FindElement('Clear').GetText() == 'Exit':
						break
					window.FindElement('adf').Update(True)
					window.FindElement('ocr').Update(True)
					window.FindElement('view').Update(True)
					window.FindElement('letter').Update(True)
					window.FindElement('color').Update(False)
					UpdateOutput(window, None, append_flag=False)
				elif button == 'Scan':
					# Generate a Unique Filename Based on Date and Time
					outfile = os.path.join(outputdir, 'scan_' + datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + '.pdf')
					# Scan and Optionally OCR the Document
					ScanDocument(window, outfile, values)
					# View the Output File
					if values['view'] == True:
						ViewDocument(window, outfile)
				time.sleep(.01)	# Improves Performance in Non-Blocking Forms
			window.CloseNonBlockingForm()

	def ScanDocument(window, outfile, values):
		funcname = 'ScanDocument'
		try:
			# Search for Available Scanners
			UpdateOutput(window, 'Searching for Scanners...\n\n', append_flag=False)
			pyinsane2.init()
			devices = pyinsane2.get_devices()
			if (len(devices) <= 0):
				UpdateOutput(window, 'Unable to Locate a Scanner!\n\n', append_flag=True)
				ShowError(funcname, 'Unable to Locate a Scanner!')
				return
			device = devices[0]
			# Update the Output Field with the Selected Scanner
			UpdateOutput(window, 'Selecting Scanner: ' + str(device.name) + '\n\n', append_flag=True)
			# Begin Scan
			UpdateOutput(window, 'Setting Scanner Options...\n\n', append_flag=True)
			# Create a Working Directory
			workdir = CreateWorkingDirectory()
			# Set Scanner Options
			if values['adf'] == True:											# Use Automatic Document Feeder
				UpdateOutput(window, 'Source: ADF\n', append_flag=True)
				pyinsane2.set_scanner_opt(device, 'source', ['ADF', 'Feeder'])
				multi = True
			else:
				UpdateOutput(window, 'Source: Flatbed\n', append_flag=True)
				pyinsane2.set_scanner_opt(device, 'source', ['FlatBed', 'Auto'])
				multi = False
			if values['letter'] == True:										# Limit Scan Area to Letter Size Paper
				UpdateOutput(window, 'Page Size: Letter\n', append_flag=True)
			else:
				pyinsane2.maximize_scan_area(device)
			UpdateOutput(window, 'Resolution: 300\n', append_flag=True)
			pyinsane2.set_scanner_opt(device, "resolution", [300])				# Resolution 300 dpi
			if values['color'] == True:											# Set Scan Mode to 'Color' or 'Gray'
				UpdateOutput(window, 'Mode: Color\n', append_flag=True)
				pyinsane2.set_scanner_opt(device, 'mode', ['Color'])
			else:
				UpdateOutput(window, 'Mode: Gray\n', append_flag=True)
				pyinsane2.set_scanner_opt(device, 'mode', ['Gray'])
			# Begin Scan
			UpdateOutput(window, '\nBeginning Scan...\n\n', append_flag=True)
			try:
				scan_session = device.scan(multiple=multi)
			except:
				UpdateOutput(window, 'Error: Document Feeder is Empty!', append_flag=True)
				ShowError(funcname, 'Error: Document Feeder is Empty!')
				return
			try:
				while True:
					try:
						scan_session.scan.read()
					except EOFError:
						UpdateOutput(window, "Scanned Page: " + str(len(scan_session.images)) + "\n", append_flag=True)
			except StopIteration:
				UpdateOutput(window, "Total Pages: " + str(len(scan_session.images)) + "\n", append_flag=True)
			# Get the Number of Pages Scanned from Scan Result
			numpages = len(scan_session.images)
			# Output Each Image as a TIFF File
			pages = []	# List of Pages to Process
			for idx in range(0, numpages):
				workfile = os.path.join(workdir, 'scan_' + str(idx+1).zfill(6) + '.tif')
				image = scan_session.images[idx]
				imagesize = image.size
				if values['letter'] == True:
					image = image.resize((2550,3300))
				else:
					image = image.resize(imagesize)					
				image.save(workfile)
				pages.append(workfile)
			# Close Connection to Scanner
			pyinsane2.exit()
			# Verify Pages Got Created
			if os.path.isfile(os.path.join(workdir, 'scan_000001.tif')) == False:
				# Sound an Error and Return
				PlaySound()
				return
			# OCR Pages If Option Selected
			if values['ocr'] == True:
				# OCR Each Page
				pages = []	# List of Pages to Process
				for idx in range(0, numpages):
					UpdateOutput(window, '\nRunning OCR on Page: ' + str(idx+1))
					workfile = os.path.join(workdir, 'scan_' + str(idx+1).zfill(6) + '.tif')
					pyocr.libtesseract.image_to_pdf(PIL.Image.open(workfile), workfile.replace('.tif', '-new'))  # .pdf will be appended
					pages.append(workfile.replace('.tif', '-new.pdf'))
				UpdateOutput(window, '\n\nCollecting Pages...\n')
				try:
					result = pypdftk.concat(pages, out_file=outfile)
				except:
					err = 'pass'	# Effectively Ignore the Error as We Check for the Output File Later
			else:
				# Convert Pages to PDF and Merge to Output File
				UpdateOutput(window, '\n\nCollecting Image Files as PDF...\n')
				# Read Image Size from Last Page Scanned and Convert Pixels to mm to points
				layout = (img2pdf.mm_to_pt(imagesize[0] * 0.264583333), img2pdf.mm_to_pt(imagesize[1] * 0.264583333))
				if values['letter'] == True:
					layout = (img2pdf.mm_to_pt(215.9), img2pdf.mm_to_pt(279.4)) # Convert to Letter Size Paper
				#elif values['A4'] == True:
				#	inpt = (img2pdf.mm_to_pt(210), img2pdf.mm_to_pt(297)) # A4 Size Paper
				layout_fun = img2pdf.get_layout_fun(layout)
				with open(outfile,"wb") as f:
					f.write(img2pdf.convert(pages, layout_fun=layout_fun))	
			# Verify Output File was Created
			if os.path.isfile(outfile)  == False:
				ShowError(funcname, 'Unable to Locate Output PDF File!')
				# Sound an Error and Return
				PlaySound()
				return
			UpdateOutput(window, '\nDocument Saved to: ' + outfile + '\n')
			# Cleanup Working Files and Directory
			shutil.rmtree(workdir)
			# Announce Completion
			PlaySound('complete')
		except Exception as e:
			ShowError(funcname, 'Error: ' + str(e))

	def ViewDocument(window, document):
		# View the Output Document If it Exists
		if os.path.isfile(document) == True:
			viewer = 'xdg-open'		# Most Version of Linux
			if os.name == 'nt':		# Windows (Requires a Preinstalled PDF Reader)
				viewer = 'explorer'
			ShowError('ViewDocument', ExecuteCommandSubprocess(window, viewer, '"' + document + '"'), True)
	
	def CreateWorkingDirectory():
		# Create a Working Directory
		workdir = ''
		try:
			workdir = tempfile.mkdtemp()
		except Exception as e:
			ShowError('CreateWorkingDirectory', 'Error: ' + str(e))
		
		return(workdir)
		
	def PlaySound(sound='bell'):
		# Play System Sound - Requires Installation of 'playsound' Python Package, but Will Fail Gracefully
		#	Uses Standard Sounds Found in Package 'sound-theme-freedesktop', C:\Windows\media or Similar
		#	Custom Sound Files May Be Placed in the Script Directory
		#		Linux - bell.oga, complete.oga
		#		Windows	- chord.wav, complete.wav
		try:
			scriptpath = os.path.dirname(os.path.realpath(__file__))	# Path to Currently Running Script
			sndpath = '/usr/share/sounds/freedesktop/stereo'			# Path to Sound Files - Linux
			sndfile = 'NNNNNNNN.oga'									# Sound File
			if os.name == 'nt':
				sndpath = 'C:\\Windows\\media'											# Change Windows Sound File Path
				sndfile = 'NNNNNNNN.wav'												# Change Windows Sound File Type
				sound = sound.replace('bell', 'chord').replace('complete', 'chimes')	# Change Windows Sound File Name
			sndfile = sndfile.replace('NNNNNNNN', sound)								# Change Sound File Name to Selected Value
			if os.path.isfile(os.path.join(sndpath, sndfile)):			# Verify Sound File Exists
				playsound(os.path.join(sndpath, sndfile))				# Play Sound File
			elif os.path.isfile(os.path.join(scriptpath, sndfile)):		# Check for Sound File in Script Directory
				playsound(os.path.join(scriptpath, sndfile))			# Play Sound File in Script Directory
		except: pass
		
	def ShowError(funcname, errtext, parse=False):
		result = False
		try:
			if errtext is not None:
				if parse == True:
					ndx = errtext.lower().find('error')
					if ndx > -1:
						errtext = errtext[ndx:(len(errtext) - 1)]
						result = True
					elif errtext.lower().find('not found') > -1:
						result = True
					else:
						return(False)
				PlaySound()	# Play Default System Sound to Announce Error
				sg.Popup(funcname, CleanCommandOutput(errtext))
		except Exception as e:
			sg.Popup('ShowError', 'Error: ' + str(e))
			
		return(result)
		
	def CleanCommandOutput(txt):
		# Remove Extraneous Text from Command Subprocess Output
		try:
			txt = txt.replace('[01m', '').replace('[0m', '').replace('[31;01m','')
			txt = re.sub('Reading data.*?\n','Reading data...\n',txt, flags=re.DOTALL)
			txt = re.sub('Viewing PDF file.*?\n','',txt, flags=re.DOTALL)
			txt = txt.replace("\n\n\n", "\n")
		
			return(txt)
		except Exception as e:
			sg.Popup('CleanCommandOutput', 'Error: ' + str(e))
		
	def UpdateOutput(window, updatetxt, key='output', append_flag=True):
		# Update the Output Field on the window
		try:
			if window is None:
				return
			txt = ''
			if updatetxt is not None:
				txt = updatetxt
			window.FindElement(key).Update(disabled=False)
			window.FindElement(key).Update(value=CleanCommandOutput(txt), append=append_flag)
			window.FindElement(key).Update(disabled=True)
			window.Refresh()
		except Exception as e:
			sg.Popup('UpdateOutput', 'Error: ' + str(e))
		
	def ExecuteCommandSubprocess(window, command, *args, update_form=True):
		# Execute a Shell Command and Return the Output, Optionally Update Output Field
		try:
			cmd = ' '.join(str(x) for x in [command, *args]) # Recommended for String Input
			p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
			# Get Command Output Line by Line
			cmdoutput = ''
			for line in p.stdout:
				line = line.decode('utf-8')
				cmdoutput += line
				# Update the Output Field on the window with the Current Command Output Line
				if update_form == True:
					UpdateOutput(window, updatetxt=line, key='output', append_flag=True)

			# Return the Command Output to the Caller
			return (cmdoutput)
		except: pass

	Launcher()

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
