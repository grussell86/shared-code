#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Scan2PDF.py
#
#  Scan a Document and Output to a PDF File
#    with Optional OCR
#
#    Requires:     Python3        - Platform Specific Install
#                  Tkinter        - Platform Specific, e.g., python3-tk
#                  tesseractocr   - Platform Specific Install
#                  PDFtk Server   - Platform Specific Install
#                  PySimpleGUI    - pip install PySimpleGUI
#                  pyinsane2      - pip install pyinsane2
#                  Pillow         - pip install Pillow
#                  libtiff        - pip install libtiff
#                  numpy          - pip install numpy
#                  pyocr          - pip install pyocr
#                  pypdftk        - pip install pypdftk
#                  img2pdf        - pip install img2pdf
#                  playsound      - pip install playsound (audio feedback)
#                  *** Some platforms use pip3 instead of pip for install ***
#    Optional:     Sounds from Package 'sound-theme-freedesktop' or similar
#                  Windows Sounds from C:\Windows\Media\
#                  A PDF Viewer of Some Sort, e.g., Adobe PDF Reader, MuPDF, Evince
#
#    Testing:      Tested with Multiple HP OfficeJet Printers
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
    import sys
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
    import re
    import os
    from time import sleep
    from playsound import playsound

    if os.name == 'nt':
        try:
            tesseract = os.path.join(os.path.dirname(
                'C:\\PROGRA~2\\TESSER~1\\'), 'tesseract.exe')
            if os.path.isfile(tesseract) == False:
                tesseract = ''
        except:
            tesseract = ''

        if os.getenv('PDFTK_PATH'):
            PDFTK_PATH = os.getenv('PDFTK_PATH')
        else:
            PDFTK_PATH = os.path.join(os.path.dirname(
                'C:\\PROGRA~2\\PDFTKS~1\\bin\\'), 'pdftk.exe')
            if not os.path.isfile(PDFTK_PATH):
                PDFTK_PATH = ''

    def Launcher():
        # Output Location for Scanned Document - PDF Folder in Home Directory
        outputdir = os.path.join(os.path.expanduser('~'), 'PDF')

        if os.path.exists(outputdir) == False:
            os.mkdir(outputdir)

        # Set Window Options
        sg.SetOptions(element_padding=(10, 0))

        # Build the Input window
        with sg.Window('Scan Document to PDF', default_button_element_size=(8,1), auto_size_buttons=True, auto_size_text=False, default_element_size=(26,1)) as window:
            layout = [[sg.Frame('Document Source', [
                          [sg.Text('Scanner: ', size=(7, 1)), 
                           sg.InputCombo(('Searching...'), size=(50, 1), key='scanner')],
                          [sg.Radio('Scanner Glass', 'RADIO1', key='glass', default=True), 
                           sg.Radio('Automatic Document Feeder', 'RADIO1', key='adf'), ]]),
                       sg.ReadButton('Clear', key='Clear'), 
                       sg.ReadButton('Scan Document', bind_return_key=True, key='Scan')],
                      [sg.Frame('Options', [
                          [sg.Checkbox('OCR Document after Scanning', key='ocr', default=True), 
                           sg.Checkbox('Open Document after Scanning', key='view', default=True)],
                          [sg.Checkbox('Letter Size Paper', key='letter', default=True), 
                           sg.Checkbox('Color', key='color', default=False)]])],
                      [sg.Text('Status:')],
                      [sg.Multiline(size=(100, 35), key='output', background_color='#ECECEC', autoscroll=True, focus=True)],
                      ]

            # Create a Non-Blocking Window to Allow for Updates in Multiline Output
            window.Layout(layout).Read(timeout=1)

            # Disable Input to Output Status Field
            window.FindElement('output').Update(disabled=True)

            # Disable All Elements During Initial Search for Scanners
            keys = ['scanner', 'glass', 'adf', 'Clear', 'Scan', 'ocr', 'view', 'letter', 'color']
            for key in keys:
                window.FindElement(key).Update(disabled=True)
            window.Refresh()

            # Get a List of Available Scanners
            scanners = []
            try:
                pyinsane2.init()
                devices = pyinsane2.get_devices()
                for i in range(0, len(devices)):
                    if devices[i].dev_type.find('scanner') > -1 or devices[i].dev_type.find('all-in-one') > -1:
                        scanners.append(devices[i].nice_name)
                pyinsane2.exit()
            except:
                pass

            # Add the List of Scanners to the Input Combo
            if len(scanners) == 0:
                window.FindElement('scanner').Update(values=['Unable to Locate a Scanner'], disabled=False)
            else:
                window.FindElement('scanner').Update(values=scanners, disabled=False)
                # Enable All Input Fields
                for key in keys:
                    window.FindElement(key).Update(disabled=False)

            if os.name == 'nt' and ((len(tesseract) == 0) or (len(PDFTK_PATH) == 0)):
                window.FindElement('ocr').Update(False, disabled=True)
                UpdateOutput(window, "Unable to Locate 'tesseract-ocr/pdftk' --> OCR is Disabled\n\n")

            # Loop Taking in User Input and Using It
            while True:
                (button, values) = window.ReadNonBlocking()
                if values is None or button == 'Exit':    # If the X Button or Exit Button is Clicked, Just Exit
                    break
                elif button == 'Clear':                   # Reset Controls to Their Default Values or Exit If ButtonText is 'Exit'
                    if window.FindElement('Clear').GetText() == 'Exit':
                        break
                    window.FindElement('glass').Update(True)
                    window.FindElement('ocr').Update(True)
                    window.FindElement('view').Update(True)
                    window.FindElement('letter').Update(True)
                    window.FindElement('color').Update(False)
                    UpdateOutput(window, None, append_flag=False)
                elif button == 'Scan':
                    # Generate a Unique Filename Based on Date and Time
                    outfile = os.path.join(
                        outputdir, 'scan_' + datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + '.pdf')
                    # Scan and Optionally OCR the Document
                    ScanDocument(window, outfile, values)
                    # View the Output File
                    if values['view']:
                        ViewDocument(window, outfile)
            window.CloseNonBlockingForm()

    def ScanDocument(window, outfile, values):
        funcname = 'ScanDocument'
        try:
            # Search for Available Scanners
            UpdateOutput(window, 'Initializing Scanner...\n\n',
                         append_flag=False)
            pyinsane2.init()
            devices = pyinsane2.get_devices()
            if (len(devices) <= 0):
                UpdateOutput(window, 'Unable to Locate a Scanner!\n\n')
                ShowError(funcname, 'Unable to Locate a Scanner!')
                return
            # Looked for the User Selected Scanner
            for i in range(0, len(devices)):
                if devices[i].nice_name.find(values['scanner']) > -1:
                    device = devices[i]
                    break
            # Update the Output Field with the Selected Scanner
            try:
                UpdateOutput(window, 'Selected Scanner: ' +
                             str(device.nice_name) + '\n\n')
            except:
                UpdateOutput(
                    window, 'Unable to Locate Scanner Scanner: ' + str(values['scanner']) + '\n\n')
                ShowError(
                    funcname, 'Unable to Locate Scanner Scanner: ' + str(values['scanner']))
                return
            # Set Scanner Options
            UpdateOutput(window, 'Setting Scanner Options...\n')

            # Use Automatic Document Feeder or Flatbed
            if values['adf']:
                try:
                    pyinsane2.set_scanner_opt(
                        device, 'source', ['ADF', 'Feeder'])
                    UpdateOutput(window, '\tSource: ADF\n')
                    multi = True
                except PyinsaneException:
                    UpdateOutput(window, '\tDocument Feeder Not Found\n')
                    multi = False
            else:
                try:
                    pyinsane2.set_scanner_opt(
                        device, 'source', ['FlatBed', 'Auto'])
                    UpdateOutput(window, '\tSource: Flatbed\n')
                    multi = False
                except:
                    UpdateOutput(window, '\tSource: Not Set\n')
                    multi = False
            # Limit Scan Area to Letter Size Paper
            if values['letter']:
                UpdateOutput(window, '\tPage Size: Letter\n')
            else:
                try:
                    pyinsane2.maximize_scan_area(device)
                except:
                    pass
            # Set Resolution to 300 dpi
            try:
                pyinsane2.set_scanner_opt(device, "resolution", [300])
                UpdateOutput(window, '\tResolution: 300\n')
            except:
                UpdateOutput(window, '\tResolution: Not Set\n')
            # Set Scan Mode to 'Color' or 'Gray'
            try:
                if values['color']:
                    pyinsane2.set_scanner_opt(device, 'mode', ['Color'])
                    UpdateOutput(window, '\tMode: Color\n')
                else:
                    pyinsane2.set_scanner_opt(device, 'mode', ['Gray'])
                    UpdateOutput(window, '\tMode: Gray\n')
            except:
                UpdateOutput(window, '\tMode: Not Set\n')

            # Begin Scan
            UpdateOutput(window, '\nBeginning Scan...\n\n')
            try:
                scan_session = device.scan(multiple=multi)
            except:
                UpdateOutput(window, 'Error: Document Feeder is Empty!')
                ShowError(funcname, 'Error: Document Feeder is Empty!')
                return
            num_pages = 0
            while True:
                try:
                    while True:
                        try:
                            scan_session.scan.read()
                        except EOFError:
                            UpdateOutput(window, "Scanned Page: " +
                                         str(len(scan_session.images)) + "\n")
                except StopIteration:
                    err = None
                if num_pages == len(scan_session.images):
                    break
                else:
                    num_pages = len(scan_session.images)
                    if os.name == 'nt':  # pyinsane2 Times Out Waiting for Next Page in Windows
                        if multi:
                            UpdateOutput(
                                window, '  Waiting for Next Page...\n')
                            sleep(20)
                    else:
                        break
            # Get the Number of Pages Scanned from Scan Result
            numpages = len(scan_session.images)
            UpdateOutput(window, "\nTotal Pages: " + str(numpages) + "\n")
            if numpages == 0:
                ShowError(
                    funcname, 'No Pages Were Scanned from Selected Document Source!')
                return

            # Create a Working Directory
            workdir = CreateWorkingDirectory()

            # Output Each Image as a TIFF File
            pages = []  # List of Pages to Process
            for idx in range(0, numpages):
                workfile = os.path.join(
                    workdir, 'scan_' + str(idx+1).zfill(6) + '.tif')
                image = scan_session.images[idx]
                imagesize = image.size
                if values['letter'] == True:
                    image = image.crop((0, 0, 2550, 3300))
                else:
                    image = image.resize(imagesize)
                image.save(workfile, compression='tiff_lzw', dpi=(300, 300))
                pages.append(workfile)
            # Close Connection to Scanner
            pyinsane2.exit()
            # Verify at Least One Page Got Created
            if os.path.isfile(os.path.join(workdir, 'scan_000001.tif')) == False:
                # Display an Error and Return
                UpdateOutput(window, '\nUnable to Locate Scanned Image Files!')
                ShowError(funcname, 'Unable to Locate Scanned Image Files!')
                return
            # OCR Pages If Option Selected
            if values['ocr']:
                # OCR Each Page
                pages = []    # List of Pages to Process
                for idx in range(0, numpages):
                    UpdateOutput(
                        window, '\nRunning OCR on Page: ' + str(idx+1) + '\n')
                    workfile = os.path.join(
                        workdir, 'scan_' + str(idx+1).zfill(6) + '.tif')
                    # pyocr.libtesseract (which is much faster) doesn't work in Windows
                    if os.name == 'nt':
                        if ShowError(funcname, ExecuteCommandSubprocess(window, tesseract, '-l',  'eng', workfile, workfile.replace('.tif', '-new'), 'pdf'), True) == True:
                            return
                    else:
                        try:
                            pyocr.libtesseract.image_to_pdf(PIL.Image.open(
                                workfile), workfile.replace('.tif', '-new'))  # .pdf will be appended
                        except Exception as e:
                            UpdateOutput(window, 'PyOCR Error: ' + str(e))
                            ShowError(funcname, 'PyOCR Error: ' + str(e))
                            return
                    pages.append(workfile.replace('.tif', '-new.pdf'))
                UpdateOutput(window, '\n\nCollecting Pages...\n')
                try:
                    if os.name == 'nt':  # pypdftk can't find executable in Windows
                        if ShowError(funcname, ExecuteCommandSubprocess(window, PDFTK_PATH, os.path.join(workdir, 'scan_*-new.pdf'), 'cat', 'output', outfile), True) == True:
                            return
                    else:
                        result = pypdftk.concat(pages, out_file=outfile)
                except Exception as e:
                    pass    # pypdftk reports as error, but still works
            else:
                # Convert Pages to PDF and Merge to Output File
                UpdateOutput(window, '\n\nCollecting Image Files as PDF...\n')
                try:
                    # Read Image Size from Last Page Scanned and Convert Pixels to mm to points
                    layout = (img2pdf.mm_to_pt(
                        imagesize[0] * 0.264583333), img2pdf.mm_to_pt(imagesize[1] * 0.264583333))
                    if values['letter']:
                        # Convert to Letter Size Paper
                        layout = (img2pdf.mm_to_pt(215.9),
                                  img2pdf.mm_to_pt(279.4))
                    # elif values['A4'] == True:
                    #    layout = (img2pdf.mm_to_pt(210), img2pdf.mm_to_pt(297)) # A4 Size Paper
                    layout_fun = img2pdf.get_layout_fun(layout)
                    with open(outfile, "wb") as f:
                        f.write(img2pdf.convert(pages, layout_fun=layout_fun))
                except Exception as e:
                    UpdateOutput(window, 'img2pdf Error: ' + str(e))
                    ShowError(funcname, 'img2pdf Error: ' + str(e))
                    return
            # Verify Output File was Created
            if os.path.isfile(outfile) == False:
                # Display an Error and Return
                UpdateOutput(window, '\nUnable to Locate Output PDF File!\n')
                ShowError(funcname, 'Unable to Locate Output PDF File!')
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
        if os.path.isfile(document):
            viewer = 'xdg-open'        # Most Version of Linux
            # Windows (Requires a Preinstalled PDF Reader)
            if os.name == 'nt':
                viewer = 'explorer'
            ShowError('ViewDocument', 
                ExecuteCommandSubprocess(window, viewer, '"' + document + '"'), True)

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
        #    Uses Standard Sounds Found in Package 'sound-theme-freedesktop', C:\Windows\media or Similar
        #    Custom Sound Files May Be Placed in the Script Directory
        #        Linux - bell.oga, complete.oga
        #        Windows    - chord.wav, complete.wav
        try:
            # Path to Currently Running Script
            scriptpath = os.path.dirname(os.path.realpath(__file__))
            # Path to Sound Files - Linux
            sndpath = '/usr/share/sounds/freedesktop/stereo'
            sndfile = 'NNNNNNNN.oga'    # Sound File
            if os.name == 'nt':
                # Change Windows Sound File Path
                sndpath = 'C:\\Windows\\media'
                # Change Windows Sound File Type
                sndfile = 'NNNNNNNN.wav'
                # Change Windows Sound File Name
                sound = sound.replace('bell', 'chord').replace('complete', 'chimes')
            # Change Sound File Name to Selected Value
            sndfile = sndfile.replace('NNNNNNNN', sound)
            # Verify Sound File Exists
            if os.path.isfile(os.path.join(sndpath, sndfile)):
                # Play Sound File
                playsound(os.path.join(sndpath, sndfile))
            # Check for Sound File in Script Directory
            elif os.path.isfile(os.path.join(scriptpath, sndfile)):
                # Play Sound File in Script Directory
                playsound(os.path.join(scriptpath, sndfile))
        except:
            pass

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
                PlaySound()    # Play Default System Sound to Announce Error
                sg.Popup(funcname, CleanCommandOutput(errtext))
        except Exception as e:
            sg.Popup('ShowError', 'Error: ' + str(e))

        return(result)

    def CleanCommandOutput(txt):
        # Remove Extraneous Text from Command Subprocess Output
        try:
            txt = txt.replace('[01m', '').replace('[0m', '').replace('[31;01m', '')
            txt = re.sub('Reading data.*?\n', 'Reading data...\n', txt, flags=re.DOTALL)
            txt = re.sub('Viewing PDF file.*?\n', '', txt, flags=re.DOTALL)
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
            # Recommended for String Input
            cmd = ' '.join(str(x) for x in [command, *args])
            p = subprocess.Popen(
                cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            # Get Command Output Line by Line
            cmdoutput = ''
            for line in p.stdout:
                line = line.decode('utf-8')
                cmdoutput += line
                # Update the Output Field on the window with the Current Command Output Line
                if update_form:
                    UpdateOutput(window, updatetxt=line, key='output')

            # Return the Command Output to the Caller
            return (cmdoutput)
        except:
            pass

    Launcher()


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
