import pathlib
from hex_text_file import hex_text_file

# http://tool-support.renesas.com/autoupdate/support/onlinehelp/ja-JP/csp/V8.04.00/CS+.chm/Compiler-CCRX.chm/Output/ccrx03c0400y.html

class record_type:
	class offset:
		byte_count = 0			# バイトカウント開始位置
		addr_offset_begin = 1	# アドレスオフセット開始位置
		addr_offset_end = 2		# アドレスオフセット終了位置
		record_type = 3			# レコードタイプ開始位置
		data = 4				# データ開始位置：レコードによってデータ内容は異なる

	def __init__(self, record: bytes) -> None:
		self.enable = False
		# 生bytes
		self.record_raw = record
		# 解析情報
		self.byte_count: int = None
		self.addr_offset: int = None
		self.record_type: int = None
		self.data: bytes = None
		self.checksum: int = None
		# 解析
		self._analyze()

	def _analyze(self):
		record_offset = record_type.offset
		# 固定長データ抽出
		self.byte_count = self.record_raw[record_offset.byte_count]
		self.addr_offset = int.from_bytes(self.record_raw[record_offset.addr_offset_begin:record_offset.addr_offset_end+1], 'big')
		self.record_type = self.record_raw[record_offset.record_type]
		# データ抽出
		if self.byte_count != 0:
			self.data = self.record_raw[record_offset.data:record_offset.data+self.byte_count]
		# チェックサム抽出
		self.checksum = self.record_raw[record_offset.data+self.byte_count]
		# チェックサム計算
		sum = 0
		for byte in self.record_raw[record_offset.byte_count:record_offset.data+self.byte_count]:
			sum += byte
		sum = ((sum & 0xFF) ^ 0xFF) + 1
		# チェックサムチェック
		if self.checksum == sum:
			self.enable = True


class intel_hex(hex_text_file):
	def __init__(self, file_path: pathlib.Path) -> None:
		self.hex_file_path = file_path
		self.record_dict = {}
		# 制御情報
		self._address: int = 0
		self._address_begin: int = None
		self._address_end: int = None
		self._ext_linear_addr: int = None
		self._ext_segment_addr: int = None
		self._end = False
		#
		self._analyze_tbl = {
			0: self._analyze_00_record,
			1: self._analyze_01_record,
			2: self._analyze_02_record,
			3: self._analyze_03_record,
			4: self._analyze_04_record,
			5: self._analyze_05_record,
		}
		self._analyze()

	def _analyze(self):
		"""
		HEXファイルを読み込んで解析する
		"""
		# ファイル読み込み
		lines = None
		with self.hex_file_path.open("r") as f:
			lines = f.readlines()
		# 
		for line in lines:
			# 先頭の:を除いてbytesに変換
			byte = bytes.fromhex(line[1:])
			# hexレコード情報を作成
			data = record_type(byte)
			# 有効チェック
			if not data.enable:
				raise Exception("invalid hex file!")
			#
			self._analyze_tbl[data.record_type](data)
			#
			if self._end:
				break
		#
		if not self._end:
			print("finish without end record.")

	def _analyze_00_record(self, record: record_type):
		# データレコード
		self._analyze_curr_address(record)
		self.record_dict[self._address] = record

	def _analyze_curr_address(self, record: record_type):
		"""
		recordの開始アドレスを作成して返す
		同時に読み込み済みデータ内の最大／最小アドレスも計算する
		"""
		# アドレス作成
		self._address = record.addr_offset
		if self._ext_linear_addr is not None:
			# 拡張リニアアドレス
			self._address += self._ext_linear_addr
		elif self._ext_segment_addr is not None:
			# 拡張セグメントアドレス
			self._address += self._ext_segment_addr
		# 最小アドレス
		if self._address_begin is None:
			self._address_begin = self._address
		else:
			if self._address_begin > self._address:
				self._address_begin = self._address
		# データ長-1 取得
		data_len = record.byte_count - 1
		# 最大アドレス
		if self._address_end is None:
			self._address_end = self._address + data_len
		else:
			if self._address_end < self._address + data_len:
				self._address_end = self._address + data_len

	def _analyze_01_record(self, record: record_type):
		# エンドレコード
		self._end = True

	def _analyze_02_record(self, record: record_type):
		# 拡張セグメントアドレスレコード
		self._ext_segment_addr = int.from_bytes(record.data, 'big') * (2 ** 4)
		# リニアアドレスは無効化
		self._ext_linear_addr = None

	def _analyze_03_record(self, record: record_type):
		self.reg_CS = int.from_bytes(record.data[0:2], 'big')
		self.reg_IP = int.from_bytes(record.data[2:4], 'big')

	def _analyze_04_record(self, record: record_type):
		# 拡張リニアアドレスレコード
		self._ext_linear_addr = int.from_bytes(record.data, 'big') * (2 ** 16)
		# セグメントアドレスは無効化
		self._ext_segment_addr = None

	def _analyze_05_record(self, record: record_type):
		self.reg_EIP = int.from_bytes(record.data[0:4], 'big')




if __name__ == "__main__":
	path = r"./test_obj/abs_test.hex"
	binary = intel_hex(pathlib.Path(path))
	checksum = binary.checksum(0xFF, True, None, 0x7FFFE)
	print(f'checksum: 0x{checksum:02X}')
