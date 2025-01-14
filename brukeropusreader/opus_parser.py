from typing import List

from brukeropusreader.block_data import BlockMeta, UnknownBlockType
from brukeropusreader.constants import (
    HEADER_LEN,
    FIRST_CURSOR_POSITION,
    META_BLOCK_SIZE,
)
from brukeropusreader.opus_data import OpusData
from brukeropusreader.opus_reader import (
    read_data_type,
    read_channel_type,
    read_text_type,
    read_chunk_size,
    read_offset,
)
import numpy as np


def read_file(file_path: str) -> OpusData:
    with open(file_path, "rb") as opus_file:
        data = opus_file.read()
    meta_data = parse_meta(data)
    opus_data = parse_data(data, meta_data)
    return opus_data


def parse_meta(data: bytes) -> List[BlockMeta]:
    header = data[:HEADER_LEN]
    spectra_meta = []
    cursor = FIRST_CURSOR_POSITION
    while True:
        if cursor + META_BLOCK_SIZE > HEADER_LEN:
            break

        data_type = read_data_type(header, cursor)
        channel_type = read_channel_type(header, cursor)
        text_type = read_text_type(header, cursor)
        chunk_size = read_chunk_size(header, cursor)
        offset = read_offset(header, cursor)

        if offset <= 0:
            break

        block_meta = BlockMeta(data_type, channel_type,
                               text_type, chunk_size, offset)

        spectra_meta.append(block_meta)

        next_offset = offset + 4 * chunk_size
        if next_offset >= len(data):
            break
        cursor += META_BLOCK_SIZE
    return spectra_meta


def parse_data(data: bytes, blocks_meta: List[BlockMeta]) -> OpusData:
    opus_data = OpusData()
    for block_meta in blocks_meta:
        try:
            name, parser = block_meta.get_name_and_parser()
        except UnknownBlockType:
            continue
        parsed_data = parser(data, block_meta)
        opus_data[name] = parsed_data
    return opus_data
    
def parse_sm(data_struct, data_type="ScSm"):
	# Time-resolved data (interferogram goes in IgSm, spectrum in ScSm)
	# unless only one time slice, when it can be handled as normal data, 
	# has some lines of junk in there.  The magic numbers below are consistent
	# across all tests by ChrisHodgesUK
	junk_lines_at_start=8
	junk_lines_between_spectra=38
	WAS=data_struct["Acquisition"]["WAS"]#number of timeslices
	NPT=data_struct[f"{data_type} Data Parameter"]["NPT"]# points per timeslice
	raw_Sm=data_struct[data_type]#grab the data
	if WAS==1:
		Sm=opus_data[data_type][0:NPT]
	else:
		Sm=np.zeros((NPT,WAS))
		for timeslice in range(WAS): #reshape the array, discarding junk
			start=junk_lines_at_start+timeslice*(NPT+junk_lines_between_spectra)
			Sm[:,timeslice]=raw_Sm[start:start+NPT]


	return Sm
