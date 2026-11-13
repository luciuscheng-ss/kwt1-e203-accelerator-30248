"""Guarded response-latency repair for the supplied synchronous native ROM.

This transform is consumed only after a separate actual-model protocol test.
It preserves the vendor ROM instance and its design initialization image.
"""
import hashlib
import re
from pathlib import Path

SOURCE = 'rtl/e203/mems/sirv_mrom_top.v'
EXPECTED_SHA256 = '4a142b388f286a1cafe15e9351e1c7ca3b3fa42eade369b90da2c5ff65def85a'


def transform(text):
    original = '''  assign rom_icb_rsp_valid = rom_icb_cmd_valid;
  assign rom_icb_cmd_ready = rom_icb_rsp_ready;
  assign rom_icb_rsp_err = ~rom_icb_cmd_read;
  assign rom_icb_rsp_rdata = rom_dout;'''
    if text.count(original) != 1:
        raise ValueError('REFUSED: original ROM zero-cycle response block differs')
    corrected = '''`ifndef FPGA
  // The native ROM updates Q after a rising clock edge. Accept a command
  // first, then expose its response in the following cycle. A stalled
  // response disables the ROM so that its Q and the error bit remain stable.
  reg native_rsp_valid;
  reg native_rsp_err;
  wire native_cmd_accept = rom_icb_cmd_valid & rom_icb_cmd_ready;
  assign rom_icb_cmd_ready = ~native_rsp_valid | rom_icb_rsp_ready;
  assign rom_icb_rsp_valid = native_rsp_valid;
  assign rom_icb_rsp_err = native_rsp_err;
  assign rom_icb_rsp_rdata = rom_dout;
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      native_rsp_valid <= 1'b0;
      native_rsp_err <= 1'b0;
    end else if (rom_icb_cmd_ready) begin
      native_rsp_valid <= rom_icb_cmd_valid;
      if (rom_icb_cmd_valid) native_rsp_err <= ~rom_icb_cmd_read;
    end
  end
`else
'''+original+'''
`endif'''
    text = text.replace(original, corrected)
    pattern = r'(\.CEN\s*\(\s*)!rom_icb_cmd_read(\s*\))'
    text, count = re.subn(pattern, r'\1!(native_cmd_accept & rom_icb_cmd_read)\2', text)
    if count != 1:
        raise ValueError('REFUSED: expected one native ROM chip-enable binding')
    return text


def generate(source, output):
    source, output = Path(source), Path(output)
    if hashlib.sha256(source.read_bytes()).hexdigest() != EXPECTED_SHA256:
        raise ValueError('REFUSED: original ROM controller differs from reviewed official source')
    original = source.read_bytes().decode('latin-1')
    corrected = transform(original)
    if output.exists():
        raise ValueError('REFUSED: ROM overlay output already exists')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(corrected.encode('latin-1'))
    return output
