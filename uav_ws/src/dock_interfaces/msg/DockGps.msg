# DockGps
# GPS/PVA tối giản của Dock. Missing numeric data uses NaN, not 0.0.

uint8 interface_version
string dock_id
uint32 seq
float64 stamp_unix

float64 latitude_deg
float64 longitude_deg
float64 altitude_m

bool velocity_valid
float32 vel_n_m_s
float32 vel_e_m_s
float32 vel_d_m_s

bool heading_valid
float32 heading_deg

uint8 fix_type
float32 eph_m
float32 epv_m
bool gps_ok
