// dbg_axi_cfg_reader.sv — reads axi_configs/<dut>_axi.json into dbg_axi_cfg
// objects, following model/dut_config_reader.sv's approach.
//
// Deliberately a file, not tb code: tap naming, windowing, annotation and
// verbosity are DV decisions. Keeping them out of the tb means the design side
// cannot influence what the monitors report, and a user retunes a run by
// editing JSON rather than recompiling.
//
// Not a general JSON parser -- the schema is this project's own. Unlike
// dut_config_reader, missing keys here are defaulted rather than fatal: every
// field except "name" is an optional override of a documented default, so a
// minimal tap entry is just {"name": "..."}.
class dbg_axi_cfg_reader;

    local string content;
    local string path;

    function new(string path_);
        int fd;
        string line;
        path    = path_;
        content = "";
        fd = $fopen(path, "r");
        if (fd == 0)
            `uvm_fatal("AXI_CFG_READER", $sformatf("Cannot open AXI config %s", path))
        while (!$feof(fd)) begin
            void'($fgets(line, fd));
            content = {content, line};
        end
        $fclose(fd);
    endfunction

    // ── Small string helpers (SV strings have no search) ──────────────────
    local function int find(string needle, int from = 0);
        int n = content.len();
        int m = needle.len();
        for (int i = from; i <= n - m; i++)
            if (content.substr(i, i + m - 1) == needle) return i;
        return -1;
    endfunction

    local static function int find_in(string hay, string needle, int from = 0);
        int n = hay.len();
        int m = needle.len();
        for (int i = from; i <= n - m; i++)
            if (hay.substr(i, i + m - 1) == needle) return i;
        return -1;
    endfunction

    local static function string trim(string s);
        int lo = 0;
        int hi = s.len() - 1;
        while (lo <= hi && (s[lo] == " " || s[lo] == "\t" || s[lo] == "\n" || s[lo] == 8'h0D)) lo++;
        while (hi >= lo && (s[hi] == " " || s[hi] == "\t" || s[hi] == "\n" || s[hi] == 8'h0D)) hi--;
        if (hi < lo) return "";
        return s.substr(lo, hi);
    endfunction

    // Value text for "key": <value> inside `blk`, up to the next ',' or '}'.
    // Returns "" when absent, which callers read as "keep the default".
    local static function string value_in(string blk, string key);
        string needle = {"\"", key, "\""};
        int ki, ci, si, ei;
        ki = find_in(blk, needle);
        if (ki < 0) return "";
        ci = find_in(blk, ":", ki + needle.len());
        if (ci < 0) return "";
        si = ci + 1;
        ei = si;
        while (ei < blk.len() && blk[ei] != "," && blk[ei] != "}") ei++;
        return trim(blk.substr(si, ei - 1));
    endfunction

    local static function string unquote(string s);
        if (s.len() >= 2 && s[0] == "\"" && s[s.len()-1] == "\"")
            return s.substr(1, s.len() - 2);
        return s;
    endfunction

    // "0x..." or plain decimal.
    local static function bit [63:0] to_u64(string s, bit [63:0] dflt);
        bit [63:0] v = 0;
        string t = unquote(s);
        if (t == "") return dflt;
        if (t.len() > 2 && t[0] == "0" && (t[1] == "x" || t[1] == "X")) begin
            for (int i = 2; i < t.len(); i++) begin
                byte c = t[i];
                if      (c >= "0" && c <= "9") v = (v << 4) + (c - "0");
                else if (c >= "a" && c <= "f") v = (v << 4) + (c - "a" + 10);
                else if (c >= "A" && c <= "F") v = (v << 4) + (c - "A" + 10);
                else return v;
            end
            return v;
        end
        return t.atohex() != 0 ? t.atoi() : t.atoi();
    endfunction

    local static function bit to_bool(string s, bit dflt);
        string t = unquote(s);
        if (t == "true")  return 1;
        if (t == "false") return 0;
        return dflt;
    endfunction

    local static function uvm_verbosity to_verbosity(string s, uvm_verbosity dflt);
        case (unquote(s))
            "UVM_NONE":   return UVM_NONE;
            "UVM_LOW":    return UVM_LOW;
            "UVM_MEDIUM": return UVM_MEDIUM;
            "UVM_HIGH":   return UVM_HIGH;
            "UVM_FULL":   return UVM_FULL;
            default:      return dflt;
        endcase
    endfunction

    // ── Public API ────────────────────────────────────────────────────────
    // Returns one dbg_axi_cfg per entry in "axi_taps", in file order. The env
    // builds an agent for each that has a published interface.
    function void get_taps(ref dbg_axi_cfg cfgs[$]);
        int arr_i, i, depth, obj_start;
        string blk;

        cfgs.delete();
        arr_i = find("\"axi_taps\"");
        if (arr_i < 0) begin
            `uvm_info("AXI_CFG_READER",
                $sformatf("%s: no \"axi_taps\" section -- no AXI taps built", path), UVM_LOW)
            return;
        end
        i = find("[", arr_i);
        if (i < 0) return;

        // Walk the array, slicing each brace-balanced object.
        depth     = 0;
        obj_start = -1;
        for (int p = i; p < content.len(); p++) begin
            byte c = content[p];
            if (c == "{") begin
                if (depth == 0) obj_start = p;
                depth++;
            end else if (c == "}") begin
                depth--;
                if (depth == 0 && obj_start >= 0) begin
                    blk = content.substr(obj_start, p);
                    cfgs.push_back(parse_tap(blk));
                    obj_start = -1;
                end
            end else if (c == "]" && depth == 0) begin
                break;
            end
        end
    endfunction

    local function dbg_axi_cfg parse_tap(string blk);
        dbg_axi_cfg cfg = dbg_axi_cfg::type_id::create("cfg");
        string v;

        cfg.bus_name = unquote(value_in(blk, "name"));
        if (cfg.bus_name == "")
            `uvm_fatal("AXI_CFG_READER", $sformatf("%s: an axi_taps entry has no \"name\"", path))

        cfg.log_level      = to_verbosity(value_in(blk, "log_level"), UVM_MEDIUM);
        cfg.monitor_reads  = to_bool(value_in(blk, "monitor_reads"),  1);
        cfg.monitor_writes = to_bool(value_in(blk, "monitor_writes"), 1);
        cfg.addr_lo        = to_u64(value_in(blk, "addr_lo"), 64'h0);
        cfg.addr_hi        = to_u64(value_in(blk, "addr_hi"), 64'hFFFF_FFFF_FFFF_FFFF);

        parse_regions(blk, cfg);
        return cfg;
    endfunction

    // "regions": { "0x104": "GoingAddr", ... }
    local function void parse_regions(string blk, dbg_axi_cfg cfg);
        int ri, open_i, close_i, p;
        string body, key, val;

        ri = find_in(blk, "\"regions\"");
        if (ri < 0) return;
        open_i = find_in(blk, "{", ri);
        if (open_i < 0) return;
        close_i = find_in(blk, "}", open_i);
        if (close_i < 0) return;
        body = blk.substr(open_i + 1, close_i - 1);

        p = 0;
        forever begin
            int k0, k1, v0, v1;
            k0 = find_in(body, "\"", p);
            if (k0 < 0) break;
            k1 = find_in(body, "\"", k0 + 1);
            if (k1 < 0) break;
            key = body.substr(k0 + 1, k1 - 1);

            v0 = find_in(body, "\"", k1 + 1);
            if (v0 < 0) break;
            v1 = find_in(body, "\"", v0 + 1);
            if (v1 < 0) break;
            val = body.substr(v0 + 1, v1 - 1);

            cfg.region_name[to_u64(key, 64'h0)] = val;
            p = v1 + 1;
        end
    endfunction

endclass
