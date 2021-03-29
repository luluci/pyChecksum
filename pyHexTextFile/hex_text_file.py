
class hex_text_file:
	def __init__(self) -> None:
		self.record_dict = {}
		# 制御情報
		self._address: int = 0
		self._address_begin: int = None
		self._address_end: int = None


	def checksum(self, blank: int = 0xFF, twos_compl: bool = True, addr_begin: int = None, addr_end: int = None) -> int:
		#
		if addr_begin is None:
			addr_begin = self._address_begin
		if addr_end is None:
			addr_end = self._address_end
		# データ総和計算
		data_sum = self._checksum_sum(blank, addr_begin, addr_end)
		# チェックサム計算
		if twos_compl:
			data_sum = -data_sum & 0xFFFFFFFF
		else:
			data_sum = data_sum & 0xFFFFFFFF
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
			use_data_end = record.data_len
			# 相対アドレス作成
			rel_addr_begin = addr - addr_begin
			rel_addr_end = rel_addr_begin + record.data_len
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
