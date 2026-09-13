// ══════════════════════════════════════════════════════════════════════════════
// dm_config.sv — the declared configuration of a Debug Module implementation.
//
// Every field here corresponds to something the RISC-V Debug Specification
// marks Preset, or to an optional feature the spec permits an implementation to
// omit. None of it is derivable from the spec alone, and none of it may be read
// out of the DUT: a reference model that learns its expectations from the
// design it is checking cannot find a bug in that design.
//
// This struct is the model's public interface. It is deliberately a schema
// rather than constructor arguments -- a golden model is configured, and a
// growing positional argument list stops being reviewable at about ten entries.
//
// Populated from dut_configs/<dut>.json. Field names match the spec's own
// field names (xml/dm_registers.xml) wherever one exists, so a reviewer can
// check a value against the specification without a translation step.
// ══════════════════════════════════════════════════════════════════════════════
typedef struct {
    // ── Optional features ───────────────────────────────────────────────────
    // The spec makes these optional; an implementation may omit any of them.
    // Setting one false removes the corresponding registers from the model
    // entirely -- has_model() stops claiming them, so nothing is predicted and
    // nothing is compared. That is the supported way to describe a DM that
    // does not implement a feature, and the supported way to park one whose
    // checking is still under development.
    bit          sba_enable;             // sbcs, sbaddress*, sbdata* (0x38-0x3F)
    bit          abstractauto_enable;    // abstractauto (0x18)
    bit          hartarray_enable;       // hawindowsel, hawindow (0x14, 0x15)
    bit          authentication_enable;  // authdata (0x30)
    bit          haltgroups_enable;      // dmcs2 (0x32), v1.0 only

    // ── Topology ────────────────────────────────────────────────────────────
    int unsigned num_harts;

    // ── dmstatus (0x11) ─────────────────────────────────────────────────────
    bit [3:0]    version;            // 2 = 0.13, 3 = 1.0
    bit          authenticated;
    bit          impebreak;
    bit          hasresethaltreq;
    bit          stickyunavail;      // 1.0 only
    bit          havereset_poweron;  // spec reset is "-", so declared

    // ── dmcontrol (0x10) ────────────────────────────────────────────────────
    bit          supports_hartreset;
    bit          supports_hasel;
    bit          resumeack_reset;

    // ── abstractcs (0x16) ───────────────────────────────────────────────────
    bit [4:0]    progbufsize;
    bit [3:0]    datacount;
    bit          relaxedpriv_reset;  // 1.0 only

    // ── hartinfo (0x12), all Preset ─────────────────────────────────────────
    bit [3:0]    nscratch;
    bit          dataaccess;
    bit [3:0]    datasize;
    bit [11:0]   dataaddr;

    // ── sbcs (0x38) ─────────────────────────────────────────────────────────
    bit [2:0]    sbversion;          // spec reset = 1
    bit [6:0]    sbasize;            // 0 when no system bus access
    bit          sbaccess128;
    bit          sbaccess64;
    bit          sbaccess32;
    bit          sbaccess16;
    bit          sbaccess8;

    // ── nextdm (0x1d) ───────────────────────────────────────────────────────
    bit [31:0]   nextdm;
} dm_cfg_t;
