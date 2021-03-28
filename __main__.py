import os
import sys
import pathlib

sys.path.append(os.path.join(os.path.dirname(__file__), './userlib'))

import PySimpleGUI as sg
from PySimpleGUIHelper import PySimpleGUIHelper as sg_helper
from pyHexTextFile.intel_hex import intel_hex
from pyHexTextFile.mot_s_record import mot_s_record

layout_input = [
	[sg.Text('HEX File:'), sg.Input('', key='inp_hex_file'), sg.FileBrowse(), sg.Text(' '), sg.Button('Read', key='btn_hex_read', enable_events=True)]
]
layout_checksum = [
	[
		sg.Text('Blank:'), sg.Input('FF', size=(5,1)),
		sg.Text(' '),
		sg.Text('2の補数:'), sg.Radio('あり', 0, True), sg.Radio('なし', 0)
	],
	[sg.Button('calc', key='btn_checksum_calc', size=(10,1)), sg.Text('      checksum:'), sg.Input('', key='inp_checksum', size=(5,10), readonly=True)],
]
layout_hex_info = [
	[sg.Text('Address:'), sg.Input('', size=(10,1), key='inp_address_begin'), sg.Text(' to '), sg.Input('', size=(10,1), key='inp_address_end')],
	[sg.Frame('checksum', layout_checksum)],
]

layout_window = [
	[sg.Frame('Input', layout_input)],
	[sg.Frame('HEX Info', layout_hex_info)],
]

window = sg.Window("test window.", layout_window, finalize=True)



def dad_inp_hex_file(dn: str):
	window['inp_hex_file'].update(value=dn)


adapt_dad_inp_hex_file = sg_helper.adapt_dad(window["inp_hex_file"], dad_inp_hex_file)



"""
グローバル変数
"""
hex_file_info = None
checksum_blank = "FF"
checksum_twos_compl = True

"""
関数
"""
def read_file(values):
	# GUIから情報取得
	file_path_str = values["inp_hex_file"]
	# HEXファイル情報作成
	try:
		file_path = pathlib.Path(file_path_str)
		file_ext = file_path.suffix
		if file_ext == '.mot':
			hex_file_info = mot_s_record(file_path)
		else:
			hex_file_info = intel_hex(file_path)
	except:
		print('NG!')
		return
	# 情報展開
	window['inp_address_begin'].update(value=f'{hex_file_info._address_begin:08X}')
	window['inp_address_end'].update(value=f'{hex_file_info._address_end:08X}')

while True:
	event, values = window.read()

	if event == 'btn_hex_read':
		read_file(values)
	elif event is None:
		print("exit")
		break

window.close()
