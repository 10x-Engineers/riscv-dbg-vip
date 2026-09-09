// dbg_report_server.sv — UVM report server that prints file basenames.
//
// UVM's default server prints `__FILE__` verbatim, so every message carries the
// absolute path it was compiled from -- e.g.
//
//   UVM_INFO /work/.../src/pydebug/sv/env/py_bridge.sv(87) @ 46926000: ...
//
// which is ~60 columns of noise per line before the message even starts, and
// differs between machines, so logs from two checkouts never diff cleanly.
// Trimming to the basename keeps the file:line that makes a message traceable:
//
//   UVM_INFO py_bridge.sv(87) @ 46926000: ...

class dbg_report_server extends uvm_default_report_server;

  function new(string name = "dbg_report_server");
    super.new(name);
  endfunction

  // Rewrite the whole line rather than delegating to the default composer, so
  // the simulation time leads every message:
  //
  //   @      3926000  UVM_INFO  py_bridge.sv(99)  [BRIDGE] WRITE addr=0x10 ...
  //
  // instead of UVM's default, which buries the time mid-line after the file
  // and severity. A leading, fixed-width timestamp is what lets two sources
  // be read as one ordered sequence -- and lets `sort` do it if they are not.
  virtual function string compose_report_message(uvm_report_message report_message,
                                                 string report_object_name = "");
    string fname = report_message.get_filename();
    string ctxt  = report_message.get_report_object().get_full_name();
    int    cut   = -1;

    // Basename only: the absolute compile-time path is ~60 columns of noise
    // and differs between machines, so logs never diff cleanly.
    foreach (fname[i]) begin
      if (fname[i] == "/" || fname[i] == "\\") cut = i;
    end
    if (cut >= 0 && cut < fname.len() - 1)
      fname = fname.substr(cut + 1, fname.len() - 1);

    return $sformatf("@%12t  %-9s %s%s [%s] %s",
                     $time,
                     report_message.get_severity().name(),
                     (fname != "") ? $sformatf("%s(%0d)", fname, report_message.get_line()) : "",
                     (ctxt  != "") ? {" ", ctxt} : "",
                     report_message.get_id(),
                     report_message.get_message());
  endfunction

endclass
