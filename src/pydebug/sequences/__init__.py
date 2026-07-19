"""
pydebug.sequences — Built-in debug test sequences.

Available sequences:
    halt_sequence          — halt + register/memory inspection
    read_dmstatus_sequence — read and display dmstatus
    mem_scan_sequence      — scan a range of memory addresses
    run_control_sequence   — halt/resume individual hart (TC-RC-001..006)
    reset_ctrl_sequence    — ndmreset/hartreset/havereset (TC-RST-001..005)
    halt_on_reset_sequence — set/clrresethaltreq (TC-HOR-001..005)
"""
