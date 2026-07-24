// ══════════════════════════════════════════════════════════════════════════════
// dut_config_reader.sv — Reads dut_configs/<name>.json into dm_ref_model's
// constructor args, the SV side of model/dut_config.py's DutConfig.
//
// Not a general JSON parser -- the schema is fixed and flat (string/bool
// values only, one level, produced only by this project's own
// dut_configs/*.json). Written by hand rather than pulled in via DPI-C/a
// library, since the field set is small and fixed; extend get_*() calls if
// the schema grows, not the parsing itself.
//
// Usage (see dm_checker.sv build_phase):
//   dut_config_reader cfg = new(path);
//   model = new(.version_(cfg.get_version()), .stickyunavail_(cfg.get_bool("stickyunavail")), ...);
// ══════════════════════════════════════════════════════════════════════════════
class dut_config_reader;
  local string content;
  local string path;

  function new(string path_);
    int fd;
    string line;
    path = path_;
    content = "";
    fd = $fopen(path, "r");
    if (fd == 0)
      `uvm_fatal("DUT_CONFIG_READER", $sformatf("Cannot open DUT config %s", path))
    while (!$feof(fd)) begin
      void'($fgets(line, fd));
      content = {content, line};
    end
    $fclose(fd);
  endfunction

  // Returns the index of the first occurrence of `needle` in `content` at or
  // after `from`, or -1 if not found. SV strings have no built-in search.
  local function int find(string needle, int from = 0);
    int n = content.len();
    int m = needle.len();
    for (int i = from; i <= n - m; i++) begin
      if (content.substr(i, i + m - 1) == needle) return i;
    end
    return -1;
  endfunction

  // Raw value text for "key": <value> -- everything after the colon up to
  // the next ',' or '}', whitespace-trimmed. Fatal if the key is missing:
  // every field in these config files is a required, declared fact, never
  // a silently-defaulted one (mirrors dut_config.py's KeyError-on-missing).
  local function string raw_value(string key);
    string needle = {"\"", key, "\""};
    int key_idx, colon_idx, start_idx, end_idx;
    string val;
    key_idx = find(needle);
    if (key_idx < 0)
      `uvm_fatal("DUT_CONFIG_READER", $sformatf("%s: missing required key \"%s\"", path, key))
    colon_idx = find(":", key_idx + needle.len());
    start_idx = colon_idx + 1;
    while (start_idx < content.len() &&
           (content.substr(start_idx, start_idx) == " " ||
            content.substr(start_idx, start_idx) == "\t"))
      start_idx++;
    // Terminates on ',' / '}' / '\n' only -- not '\r': this Questa build does
    // not interpret "\r" as a carriage return in a string literal (it's
    // read back as the literal character 'r'), confirmed by direct test;
    // dut_configs/*.json is Unix-line-ended anyway, so '\n' alone is
    // sufficient and correct here.
    end_idx = start_idx;
    while (end_idx < content.len() &&
           content.substr(end_idx, end_idx) != "," &&
           content.substr(end_idx, end_idx) != "}" &&
           content.substr(end_idx, end_idx) != "\n")
      end_idx++;
    val = content.substr(start_idx, end_idx - 1);
    // Trim trailing whitespace left after stripping the terminator.
    while (val.len() > 0 &&
           (val.substr(val.len() - 1, val.len() - 1) == " " ||
            val.substr(val.len() - 1, val.len() - 1) == "\t"))
      val = val.substr(0, val.len() - 2);
    return val;
  endfunction

  function bit get_bool(string key);
    string v = raw_value(key);
    if (v == "true") return 1'b1;
    if (v == "false") return 1'b0;
    `uvm_fatal("DUT_CONFIG_READER", $sformatf("%s: key \"%s\" = %s is not true/false", path, key, v))
  endfunction

  // Strips the surrounding quotes from a JSON string value.
  function string get_string(string key);
    string v = raw_value(key);
    if (v.len() >= 2 && v.substr(0, 0) == "\"" && v.substr(v.len() - 1, v.len() - 1) == "\"")
      return v.substr(1, v.len() - 2);
    `uvm_fatal("DUT_CONFIG_READER", $sformatf("%s: key \"%s\" = %s is not a quoted string", path, key, v))
  endfunction

  // dmstatus.version encoding (dm_defines_pkg.sv), from the config's
  // "version" string field ("0.13" -> 4'd2, "1.0" -> 4'd3).
  function bit [3:0] get_version();
    string v = get_string("version");
    if (v == "0.13") return 4'd2;
    if (v == "1.0")  return 4'd3;
    `uvm_fatal("DUT_CONFIG_READER", $sformatf("%s: unknown version \"%s\" (expected \"0.13\" or \"1.0\")", path, v))
  endfunction
endclass : dut_config_reader
