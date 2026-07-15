/*
 * uvm_bridge.h — Public API for the UVM bridge C server.
 * Include this in any C/DPI shim that calls uvm_bridge_start/stop.
 */
#ifndef UVM_BRIDGE_H
#define UVM_BRIDGE_H

#ifdef __cplusplus
extern "C" {
#endif

/* Start the socket server (call once from DPI initial block). */
int  uvm_bridge_start(void);

/* Stop the server (call from DPI final block or end-of-test hook). */
void uvm_bridge_stop(void);

#ifdef __cplusplus
}
#endif
#endif /* UVM_BRIDGE_H */
