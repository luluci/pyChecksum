import pathlib

# http://tool-support.renesas.com/autoupdate/support/onlinehelp/ja-JP/csp/V8.04.00/CS+.chm/Compiler-CCRX.chm/Output/ccrx03c0400y.html

class hex_record:
	class record_offset:
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
		record_offset = hex_record.record_offset
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

class hex:
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
			record = hex_record(byte)
			# 有効チェック
			if not record.enable:
				raise Exception("invalid hex file!")
			#
			self._analyze_tbl[record.record_type](record)
			#
			if self._end:
				break
		#
		if not self._end:
			print("finish without end record.")

	def _analyze_00_record(self, record: hex_record):
		# データレコード
		self._analyze_curr_address(record)
		self.record_dict[self._address] = record

	def _analyze_curr_address(self, record: hex_record):
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

	def _analyze_01_record(self, record: hex_record):
		# エンドレコード
		self._end = True

	def _analyze_02_record(self, record: hex_record):
		# 拡張セグメントアドレスレコード
		self._ext_segment_addr = int.from_bytes(record.data, 'big') * (2 ** 4)
		# リニアアドレスは無効化
		self._ext_linear_addr = None

	def _analyze_03_record(self, record: hex_record):
		self.reg_CS = int.from_bytes(record.data[0:2], 'big')
		self.reg_IP = int.from_bytes(record.data[2:4], 'big')

	def _analyze_04_record(self, record: hex_record):
		# 拡張リニアアドレスレコード
		self._ext_linear_addr = int.from_bytes(record.data, 'big') * (2 ** 16)
		# セグメントアドレスは無効化
		self._ext_segment_addr = None

	def _analyze_05_record(self, record: hex_record):
		self.reg_EIP = int.from_bytes(record.data[0:4], 'big')

	def checksum(self, blank:int = 0xFF, twos_compl:bool = True, addr_begin:int=None, addr_end:int=None) -> int:
		#
		if addr_begin is None:
			addr_begin = self._address_begin
		if addr_end is None:
			addr_end = self._address_end
		# データ総和計算
		data_sum = self._checksum_sum(blank, addr_begin, addr_end)
		# チェックサム計算
		if twos_compl:
			data_sum = (-data_sum & 0xFF)
		#
		return data_sum

	def _checksum_sum(self, blank: int, addr_begin: int, addr_end: int) -> int:
		# メモリ空間を作成する
		# blankで埋めて初期化
		addr_max = addr_end - addr_begin + 1
		mem = [blank] * addr_max
		# 保持しているレコードを展開
		for addr, record in self.record_dict.items():
			# record.data使用範囲
			use_data_begin = 0
			use_data_end = len(record.data)
			# 相対アドレス作成
			rel_addr_begin = addr - addr_begin
			rel_addr_end = rel_addr_begin + record.byte_count
			# アドレス範囲チェック
			if rel_addr_begin < 0:
				use_data_begin = rel_addr_begin * -1
				rel_addr_begin = 0
			if rel_addr_end > addr_max:
				use_data_end -= rel_addr_end - addr_max
				rel_addr_end = addr_max
			# レコードデータのリストを作成
			mem_record = [data for data in record.data[use_data_begin:use_data_end]]
			# メモリ空間に展開
			mem[rel_addr_begin:rel_addr_end] = mem_record
		# メモリ空間の総和計算
		data_sum = 0
		for data in mem:
			data_sum += data
		return data_sum




if __name__ == "__main__":
	path = r"./test_obj/abs_test.hex"
	binary = hex(pathlib.Path(path))
	checksum = binary.checksum(0xFF, True, None, 0x7FFFE)
	print(f'checksum: 0x{checksum:02X}')
