import pathlib
from hex_text_file import hex_text_file

class record_type:
	class offset:
		byte_count = 0			# バイトカウント開始位置
		addr_offset_begin = 1	# ロードアドレス開始位置
								# ロードアドレス終了位置(可変)
								# データ開始位置(可変)

	# レコード毎のアドレスサイズ定義テーブル
	record_size_tbl = (
		2,
		2,
		3,
		4,
		None,
		2,
		3,
		4,
		3,
		2,
	)


	def __init__(self, record: str) -> None:
		self.enable = False
		# 解析情報
		self.record_type: int = None	# 0:S0/1:S1/2:S2/3:S3/
		self.byte_count: int = None
		self.addr: int = None
		self.addr_len: int = None
		self.data: bytes = None
		self.checksum: int = None
		# 解析
		self._analyze(record)

	def _analyze(self, record_str: str):
		record_offset = record_type.offset
		# レコードタイプ取得
		self.record_type = self._analyze_record_type(record_str[0:2])
		# 生bytes
		self.record_raw = bytes.fromhex(record_str[2:])
		# 固定長データ抽出
		self.byte_count = self.record_raw[record_offset.byte_count]
		# 各種レコード位置を作成
		self._make_record_pos()
		self.addr = int.from_bytes(self.record_raw[record_offset.addr_offset_begin:record_offset.addr_offset_begin+self.addr_len], 'big')
		# データ抽出
		if self.byte_count != 0:
			self.data = self.record_raw[self.data_pos:self.fcc_pos]
		# チェックサム抽出
		self.checksum = self.record_raw[record_offset.addr_offset_begin+self.byte_count-1]
		# チェックサム計算
		sum = 0
		for byte in self.record_raw[record_offset.byte_count:self.fcc_pos]:
			sum += byte
		sum = (sum & 0xFF) ^ 0xFF
		# チェックサムチェック
		if self.checksum == sum:
			self.enable = True

	def _make_record_pos(self):
		record_offset = record_type.offset
		# アドレス長
		self.addr_len = record_type.record_size_tbl[self.record_type]
		# データサイズ
		self.data_len = self.byte_count - self.addr_len - 1
		# データ開始位置
		self.data_pos = record_offset.addr_offset_begin + self.addr_len
		self.fcc_pos = record_offset.addr_offset_begin + self.byte_count - 1
		self.data_end_pos = self.fcc_pos - 1


	def _analyze_record_type(self, record: str):
		return int(record[1])


class mot(hex_text_file):
	def __init__(self, file_path: pathlib.Path) -> None:
		self.file_path = file_path
		self.record_dict = {}
		# 制御情報
		self._address: int = 0
		self._address_begin: int = None
		self._address_end: int = None
		self._ext_linear_addr: int = None
		self._ext_segment_addr: int = None
		self._S1_end = False
		self._S2_end = False
		self._S3_end = False
		#
		self._analyze_tbl = {
			0: self._analyze_S0_record,
			1: self._analyze_S1_record,
			2: self._analyze_S2_record,
			3: self._analyze_S3_record,
			# 4: self._analyze_S4_record,
			# 5: self._analyze_S5_record,
			# 6: self._analyze_S6_record,
			7: self._analyze_S7_record,
			8: self._analyze_S8_record,
			9: self._analyze_S9_record,
		}
		self._analyze()

	def _analyze(self):
		"""
		HEXファイルを読み込んで解析する
		"""
		# ファイル読み込み
		lines = None
		with self.file_path.open("r") as f:
			lines = f.readlines()
		#
		for line in lines:
			# レコード情報を作成
			data = record_type(line)
			# 有効チェック
			if not data.enable:
				raise Exception("invalid hex file!")
			#
			self._analyze_tbl[data.record_type](data)
			#

	def _analyze_S0_record(self, record: record_type):
		# データレコード
		self.filename = record.data.decode("utf-8")

	def _analyze_S1_record(self, record: record_type):
		# データレコード
		self._analyze_curr_address(record)
		self.record_dict[self._address] = record

	def _analyze_S2_record(self, record: record_type):
		# データレコード
		self._analyze_curr_address(record)
		self.record_dict[self._address] = record

	def _analyze_S3_record(self, record: record_type):
		# データレコード
		self._analyze_curr_address(record)
		self.record_dict[self._address] = record

	def _analyze_curr_address(self, record: record_type):
		"""
		recordの開始アドレスを作成して返す
		同時に読み込み済みデータ内の最大／最小アドレスも計算する
		"""
		# アドレス作成
		self._address = record.addr
		# 最小アドレス
		if self._address_begin is None:
			self._address_begin = self._address
		else:
			if self._address_begin > self._address:
				self._address_begin = self._address
		# データ長-1 取得
		data_len = record.data_len - 1
		# 最大アドレス
		if self._address_end is None:
			self._address_end = self._address + data_len
		else:
			if self._address_end < self._address + data_len:
				self._address_end = self._address + data_len

	def _analyze_S7_record(self, record: record_type):
		# エンドレコード
		self._S3_end = True

	def _analyze_S8_record(self, record: record_type):
		# エンドレコード
		self._S2_end = True

	def _analyze_S9_record(self, record: record_type):
		# エンドレコード
		self._S1_end = True



if __name__ == "__main__":
	path = r"./test_obj/abs_test.mot"
	binary = mot(pathlib.Path(path))
	checksum = binary.checksum()
	print(f'checksum: 0x{checksum:02X}')
