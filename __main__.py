import os
import sys
import pathlib
import re

from PySimpleGUI.PySimpleGUI import VerticalSeparator

sys.path.append(os.path.join(os.path.dirname(__file__), './userlib'))

import PySimpleGUI as sg
from PySimpleGUIHelper import PySimpleGUIHelper as sg_helper
from pyHexTextFile.intel_hex import intel_hex
from pyHexTextFile.mot_s_record import mot_s_record

font_log = ('Consolas', 10)
font_wnd = ('Meiryo UI', 10)

layout_input = [
	[
		sg.Text('HEX File:'), sg.Input('', key='inp_hex_file'), sg.FileBrowse(),
		sg.VerticalSeparator(),
		sg.Button('Read', key='btn_hex_read', enable_events=True)
	],
]
layout_hex_file_info = [
	[
		sg.Text('Address:'),
		sg.Input('', size=(10,1), key='inp_address_begin', disabled=True),
		sg.Text('to'),
		sg.Input('', size=(10, 1), key='inp_address_end', disabled=True)
	],
]
layout_checksum_blank = [
	[sg.Input('FF', size=(5,1), key='inp_checksum_blank')],
]
layout_checksum_twos_compl = [
	[
		sg.Radio('あり', 0, True, key='radio_twos_enable'),
		sg.Radio('なし', 0, key='radio_twos_disable'),
		sg.Radio('あり＋なし', 0, key='radio_twos_both')
	],
]
layout_checksum_addr_range = [
	[
		sg.Text('Address:'),
		sg.Input('', size=(10,1), key='inp_checksum_addr_begin',),
		sg.Text('to'),
		sg.Input('', size=(10,1), key='inp_checksum_addr_end',)
	],
]
layout_checksum = [
	[
		sg.Frame('Blank', layout_checksum_blank),
		sg.Frame('2の補数', layout_checksum_twos_compl),
		sg.Frame('計算範囲', layout_checksum_addr_range),
	],
	[ sg.HorizontalSeparator() ],
	[
		sg.Button('calc', key='btn_checksum_calc', size=(15, 1)),
		sg.Text(''),
		sg.Input('', key='inp_checksum', size=(15, 1), readonly=True)
	],
]

layout_window = [
	[sg.Frame('Input File', layout_input)],
	[sg.Frame('HEX File Info', layout_hex_file_info)],
	[sg.Frame('checksum', layout_checksum)],
	[sg.Output(size=(80, 5), font=font_log)]
]

window = sg.Window("HEX Info", layout_window, finalize=True, font=font_wnd)



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
	global hex_file_info
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
		print('input file is invalid!')
		return
	# HEX情報取得
	addr_begin = hex_file_info._address_begin
	addr_end = hex_file_info._address_end
	# アドレス微調整
	addr_begin_adjust = addr_begin
	addr_end_adjust = addr_end
	if (addr_end & 0xFFFF) != 0xFFFF:
		addr_end_adjust = addr_end | 0xFFFF
	# 情報展開
	window['inp_address_begin'].update(value=f'{addr_begin:08X}')
	window['inp_address_end'].update(value=f'{addr_end:08X}')
	window['inp_checksum_addr_begin'].update(value=f'{addr_begin_adjust:08X}')
	window['inp_checksum_addr_end'].update(value=f'{addr_end_adjust:08X}')


def calc_checksum(values):
	global hex_file_info
	# GUIから情報取得
	blank_str = values["inp_checksum_blank"]
	addr_begin_str = values["inp_checksum_addr_begin"]
	addr_end_str = values["inp_checksum_addr_end"]
	twos_enable = values["radio_twos_enable"]
	twos_disable = values["radio_twos_disable"]
	twos_both = values["radio_twos_both"]
	# 情報整形
	re_hex = re.compile('[a-fA-F0-9]+')
	# blank
	if re_hex.match(blank_str) is None:
		print(f'Blank Setting [{blank_str}] is invalid!')
		return
	blank = int(blank_str, 16)
	# address
	if re_hex.match(addr_begin_str) is None:
		print(f'Address Setting [{addr_begin_str}] is invalid!')
		return
	addr_begin = int(addr_begin_str, 16)
	if re_hex.match(addr_end_str) is None:
		print(f'Address Setting [{addr_end_str}] is invalid!')
		return
	addr_end = int(addr_end_str, 16)
	# チェックサム計算
	checksum = None
	if twos_disable or twos_both:
		checksum = hex_file_info.checksum(blank, False, addr_begin, addr_end)
	if twos_enable or twos_both:
		checksum = hex_file_info.checksum(blank, True, addr_begin, addr_end)
	# 情報展開
	window['inp_checksum'].update(value=f'{checksum:08X}')

"""
イベントハンドラ
"""
while True:
	event, values = window.read()

	if event == 'btn_hex_read':
		read_file(values)
	elif event == 'btn_checksum_calc':
		calc_checksum(values)
	elif event is None:
		print("exit")
		break

window.close()
