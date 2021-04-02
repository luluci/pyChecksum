import os
import sys
import pathlib
import re
from typing import NamedTuple, Dict
import enum

from PySimpleGUI.PySimpleGUI import VerticalSeparator

sys.path.append(os.path.join(os.path.dirname(__file__), './userlib'))

import PySimpleGUI as sg
from PySimpleGUIHelper import PySimpleGUIHelper as sg_helper
from pyHexTextFile.intel_hex import intel_hex
from pyHexTextFile.mot_s_record import mot_s_record

"""
グローバル変数
"""
hex_file_info = None
checksum_blank = "FF"
checksum_twos_compl = True

class twos_compl_select(enum.Enum):
	enable = enum.auto()
	disable = enum.auto()
	both = enum.auto()

class checksum_preset_type(NamedTuple):
	blank: int = 0xFF
	twos_compl: twos_compl_select = twos_compl_select.enable
	addr_begin: int = 0
	addr_end: int = 0


checksum_preset: Dict[str, checksum_preset_type] = {
	"<default>": checksum_preset_type(None, twos_compl_select.enable, None, None),
	"preset1": checksum_preset_type(0xFF, twos_compl_select.both, 0x00000000, 0x0000FFFF),
	"preset2": checksum_preset_type(0xFF, twos_compl_select.enable, 0x00003000, 0x0007FFFF),
}


"""
GUIデータ作成
"""
checksum_preset_list = [k for k in checksum_preset.keys()]
checksum_preset_size = (30, len(checksum_preset_list))

font_log = ('Consolas', 10)
font_wnd = ('Meiryo UI', 10)


"""
GUIレイアウト定義
"""
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
		sg.Text('calc settings preset:'),
		sg.Combo(checksum_preset_list, size=checksum_preset_size, key='cmb_checksum_preset', enable_events=True)
	],
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


def setting_checksum(values):
	global checksum_blank
	global hex_file_info

	# preset取得
	key = values['cmb_checksum_preset']
	if key not in checksum_preset.keys():
		# 無効値なら終了
		return
	preset = checksum_preset[key]
	# preset展開
	# blank
	blank = preset.blank
	if blank is None:
		blank = int(checksum_blank, 16)
	window['inp_checksum_blank'].update(value=f'{blank:02X}')
	# twos_compl
	if preset.twos_compl == twos_compl_select.enable:
		window['radio_twos_enable'].update(value=True)
	elif preset.twos_compl == twos_compl_select.disable:
		window['radio_twos_disable'].update(value=True)
	elif preset.twos_compl == twos_compl_select.both:
		window['radio_twos_both'].update(value=True)
	# address
	addr_begin = preset.addr_begin
	if addr_begin is None:
		if hex_file_info is not None:
			addr_begin = hex_file_info._address_begin
		else:
			addr_begin = 0
	addr_end = preset.addr_end
	if addr_end is None:
		if hex_file_info is not None:
			addr_end = hex_file_info._address_end
		else:
			addr_end = 0
	window['inp_checksum_addr_begin'].update(value=f'{addr_begin:08X}')
	window['inp_checksum_addr_end'].update(value=f'{addr_end:08X}')


def calc_checksum(values):
	global hex_file_info
	# 
	if hex_file_info is None:
		return
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
	elif event == 'cmb_checksum_preset':
		setting_checksum(values)
	elif event == 'btn_checksum_calc':
		calc_checksum(values)
	elif event is None:
		print("exit")
		break

window.close()
