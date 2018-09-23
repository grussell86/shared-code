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
#				playsound - pip3 install playsound (audio feedback)
#				Many Helper Programs as Listed in CheckInstall
#	Optional: 	Sounds from Package 'sound-theme-freedesktop' or similar
#				Windows Sounds from C:\Windows\Media\
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
	import subprocess
	import shutil
	import tempfile
	import datetime
	import time
	import re
	from pathlib import Path
	from playsound import playsound

	def CheckInstall(form=None):
		result = ''
		try:
			missing_items = []
			helpers = ['hp-scan', 'pdftk', 'pdftoppm', 'convert', 'tesseract']
			for helper in helpers:
				if ExecuteCommandSubprocess(form, 'which', helper, update_form=False) == '': missing_items += ' ' + helper
			
			result = ''.join(missing_items).strip().replace(' ', ', ')
		except: pass

		return(result)
		
	def Launcher():
		# Output Location for Scanned Document - PDF Folder in Home Directory
		outputdir = str(Path.home())
		delimiter = GetDirectoryDelimiter(outputdir)
		outputdir += delimiter + 'PDF' + delimiter

		if Path(outputdir).is_dir() == False:
			Path(outputdir).mkdir(parents=True, exist_ok=True)

		# Set Form Options
		sg.SetOptions(element_padding=(10,0))
		
		# Build the Input Form
		with sg.FlexForm('Scan Document to PDF',default_button_element_size=(8,1),auto_size_buttons=True) as form:
			layout = [[sg.Frame('Document Source',[[
					  sg.Radio('Scanner Glass', 'RADIO1', key='glass'), sg.Radio('Automatic Document Feeder', 'RADIO1', key='adf', default=True),]]),
					  sg.Text('          '), sg.ReadFormButton('Clear', key='Clear'), sg.ReadFormButton('Scan Document', bind_return_key=True, key='Scan')],
					  [sg.Frame('Options',[
					  [sg.Checkbox('OCR Document after Scanning', key='ocr', default=True), sg.Checkbox('Open Document after Scanning', key='view', default=True)],
					  [sg.Checkbox('Letter Size Paper                    ', key='letter', default=True), sg.Checkbox('Color', key='color', default=False)]])],
					  [sg.Text('Status:', size=(15, 1))],
					  [sg.Multiline(size=(100,35), key='output', background_color='#ECECEC', autoscroll=True, focus=True)],
					  ]

			# Create the Form and Show It
			form.LayoutAndRead(layout, non_blocking=True)		# Create a Non-Blocking Form to Allow for Updates in Multiline Output
			form.FindElement('output').Update(disabled=True) 	# Disable Input to Output Status Field
			
			# Check that Helper Programs are Installed
			missing = CheckInstall()
			if len(missing) > 0:
				# Update Output Field with Missing Programs
				UpdateOutput(form, 'The Following Helper Programs Could Be Found:\n\t' + missing + '\n\nSome Functionality May Be Limited', append_flag=False)
				# Disable Relevant Form Elements Unless Only PDF Viewer is Missing
				form.FindElement('ocr').Update(False, disabled=True) # OCR Will Not Work if Any Other Program is Missing
				if missing.find('hp-scan') > -1:
					fields = ['glass', 'adf', 'Scan', 'view', 'letter', 'color']
					for field in fields:
						form.FindElement(field).Update(False, disabled=True)
					form.FindElement('Clear').Update(text='Exit')	# Change Clear Button to an Exit Button
					
			# Loop Taking in User Input and Using It
			while True:
				(button, values) = form.ReadNonBlocking()
				if values is None or button == 'Exit':	# If the X Button or Exit Button is Clicked, Just Exit
					break
				elif button == 'Clear':					# Reset Controls to Their Default Values or Exit If ButtonText is 'Exit'
					if form.FindElement('Clear').GetText() == 'Exit':
						break
					form.FindElement('adf').Update(True)
					form.FindElement('ocr').Update(True)
					form.FindElement('view').Update(True)
					form.FindElement('letter').Update(True)
					form.FindElement('color').Update(False)
					UpdateOutput(form, None, append_flag=False)
				elif button == 'Scan':
					# Generate a Unique Filename Based on Date and Time
					outfile = outputdir + 'scan_' + datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + '.pdf'
					# Scan the Document
					ScanDocument(form, outfile, values)
					# OCR the Document
					if values['ocr'] == True:
						OCRDocument(form, outfile)
					elif Path(outfile).is_file() == True:
						PlaySound('complete')
					# View the Output File
					if values['view'] == True:
						ViewDocument(form, outfile)
				time.sleep(.01)	# Improves Performance in Non-Blocking Forms
			form.CloseNonBlockingForm()

	def ScanDocument(form, outfile, values):
		funcname = 'ScanDocument'
		try:
			# Update the Output Field
			UpdateOutput(form, 'Beginning Scan...\n\n', append_flag=False)
			# Determine Scanner to Use
			device = ExecuteCommandSubprocess(form, 'lpstat', '-s | egrep -iv "fax|laser|pdf" | grep ip= | head -1 | cut -d= -f2- | xargs hp-makeuri -s', update_form=False).strip('\n')
			# Set Scan Options for 'hp-scan'
			args = []
			args += '--device="' + device + '"'			# Device for Scanning
			args += ' --resolution=300'					# Resolution 300 dpi
			args += ' --pdf=false'						# Do Not Open PDF for Viewing After Scan is Complete - Program Will Handle Later
			if values['adf'] == True:					# Use Automatic Document Feeder
				args += ' --adf'
			if values['letter'] == True:				# Limit Scan Area to Letter Size Paper
				args += ' --units=in --box=0,0,8.5,11'
			if values['color'] == True:					# Set Scan Mode to 'Color' or 'Gray'
				args += ' --mode=color'
			else:
				args += ' --mode=gray'
			args += ' --file="' + outfile + '"'			# Set Filename for Output Document
			# Begin Scan and Display any Errors
			ShowError(funcname, ExecuteCommandSubprocess(form, 'hp-scan', ''.join(args), update_form=True), True)
		except Exception as e:
			ShowError(funcname, 'Error: ' + str(e))

	def OCRDocument(form, document):
		funcname = 'OCRDocument'
		try:
			if Path(document).is_file() == True:
				# Update the Output Field
				UpdateOutput(form, '\nBeginning OCR...\n', append_flag=True)
				# Create a Working Directory
				workdir = CreateWorkingDirectory()
				# Copy Document to Working Directory
				UpdateOutput(form, '\nCopying Document to Working Directory\n')
				workfile = shutil.copy(document, workdir)
				if Path(workfile).is_file() == False:
					ShowError(funcname, 'Error Copying Document to Working Directory')
					return
				basefile = workfile.replace('.pdf', '')	# Base Filename is Filename Without an Extension
				# Get the PDF Info from the Working File
				UpdateOutput(form, '\nExtracting PDF Info from Document\n')
				pdfinfo = ExecuteCommandSubprocess(form, 'pdftk', workfile, 'dump_data')
				if len(pdfinfo.strip()) > 0:
					# Write PDF Info to a File
					f = open(workdir + 'pdfinfo.txt', 'w')
					f.write(pdfinfo)
					f.close
					# Get the Number of Pages in the Document
					ndx = pdfinfo.find('NumberOfPages:')
					numpages = pdfinfo[ndx:(len(pdfinfo) - 1)]
					ndx = numpages.find('\n')
					numpages = int(re.sub('[^0-9]', '', numpages[0:ndx], flags=re.DOTALL))
					# Split PDF Into Individual Pages and OCR Each One
					if numpages > 0:
						for i in range(1, numpages + 1):
							pagefile = basefile + '_' + str(i).zfill(6) + '.pdf' # Filename for Individual Pages
							UpdateOutput(form, '\nExtracting Page: ' + str(i) + '\n')
							if ShowError(funcname, ExecuteCommandSubprocess(form, 'pdftk', workfile, 'cat', str(i), 'output', pagefile), True) == True: return
							UpdateOutput(form, 'Converting Page: ' + str(i) + ' to ppm\n')
							if ShowError(funcname, ExecuteCommandSubprocess(form, 'pdftoppm', '-r 300', pagefile, '>', pagefile.replace('.pdf', '.ppm')), True) == True: return
							UpdateOutput(form, 'Converting Page: ' + str(i) + ' to tif\n')
							if ShowError(funcname, ExecuteCommandSubprocess(form, 'convert', '-density 300x300', pagefile.replace('.pdf', '.ppm'), pagefile.replace('.pdf', '.tif')), True) == True: return
							UpdateOutput(form, 'Running OCR on Page: ' + str(i) + '\n\n')
							if ShowError(funcname, ExecuteCommandSubprocess(form, 'tesseract', '-l eng', pagefile.replace('.pdf', '.tif'), pagefile.replace('.pdf', '-new'), 'pdf'), True) == True: return
						# Merge OCRed Pages
						UpdateOutput(form, '\nMerging OCRed Pages in PDF\n')
						if ShowError(funcname, ExecuteCommandSubprocess(form, 'pdftk',  workdir + '*-new.pdf', 'cat', 'output', workdir + 'merged.pdf'), True) == True: return
						# Add PDF Info to Document
						UpdateOutput(form, '\nUpdating PDF Info\n')
						if ShowError(funcname, ExecuteCommandSubprocess(form, 'pdftk',  workdir + 'merged.pdf', 'update_info', workdir + 'pdfinfo.txt', 'output', workdir + 'merged_ocr.pdf'), True) == True: return
						# Move Document to Output Directory
						UpdateOutput(form, '\nCopying PDF File to Destination as "' + document + '"\n')
						workfile = shutil.copy(workdir + 'merged_ocr.pdf', document)
						# Cleanup Working Files
						if Path(workfile).is_file() == True:
							shutil.rmtree(workdir)
						# Announce Completion of OCR and Play a System Sound
						UpdateOutput(form, '\nOCR Complete!')
						PlaySound('complete')
					else:
						ShowError(funcname, 'There are 0 Pages in the PDF File')
				else:
					ShowError(funcname, 'Unable to Read PDF Info from the PDF File')
		except Exception as e:
			ShowError(funcname, 'Error: ' + str(e))
	
	def ViewDocument(form, document):
		# View the Output Document If it Exists
		if Path(document).is_file() == True:
			ShowError('ViewDocument', ExecuteCommandSubprocess(form, 'xdg-open', '"' + document + '"'), True)
	
	def GetDirectoryDelimiter(input):
		try:
			delimiter = '/'
			if input is not None:
				if input.startswith('/'):		# Get the Directory Delimiter
					delimiter = '/'				# posix compliant
				else:
					delimiter = '\\'			# Most Likely Windows
				
			return(delimiter)
		except Exception as e:
			ShowError('GetDirectoryDelimiter', 'Error: ' + str(e))

	def CreateWorkingDirectory():
		# Create a Working Directory
		workdir = ''
		try:
			workdir = tempfile.mkdtemp()
			workdir += GetDirectoryDelimiter(workdir)
		except Exception as e:
			ShowError('CreateWorkingDirectory', 'Error: ' + str(e))
		
		return(workdir)
		
	def PlaySound(sound='bell'):
		# Play System Sound - Requires Installation of playsound Python Package, but Will Fail Gracefully
		#	Uses Standard Sounds Found in Package 'sound-theme-freedesktop' or Similar
		try:
			sndfile = '/usr/share/sounds/freedesktop/stereo/NNNNNNNN.oga'
			playsound(sndfile.replace('NNNNNNNN', sound))
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
		
	def UpdateOutput(form, updatetxt, key='output', append_flag=True):
		# Update the Output Field on the Form
		try:
			if form is None:
				return
			txt = ''
			if updatetxt is not None:
				txt = updatetxt
			form.FindElement(key).Update(disabled=False)
			form.FindElement(key).Update(value=CleanCommandOutput(txt), append=append_flag)
			form.FindElement(key).Update(disabled=True)
			form.Refresh()
		except Exception as e:
			sg.Popup('UpdateOutput', 'Error: ' + str(e))
		
	def ExecuteCommandSubprocess(form, command, *args, update_form=True):
		# Execute a Shell Command and Return the Output, Optionally Update Output Field
		try:
			cmd = ' '.join(str(x) for x in [command, *args]) # Recommended for String Input
			p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
			# Get Command Output Line by Line
			cmdoutput = ''
			for line in p.stdout:
				line = line.decode('utf-8')
				cmdoutput += line
				# Update the Output Field on the Form with the Current Command Output Line
				if update_form == True:
					UpdateOutput(form, updatetxt=line, key='output', append_flag=True)

			# Return the Command Output to the Caller
			return (cmdoutput)
		except: pass

	Launcher()

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
