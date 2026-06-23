# UAV GPS heartbeat sent to its dedicated Dock.
# altitude_m is AMSL.

uint8 interface_version
string uav_id
uint32 seq
float64 stamp_unix

float64 latitude_deg
float64 longitude_deg
float64 altitude_m

float32 heading_deg

float32 eph_m
float32 epv_m

bool gps_ok
