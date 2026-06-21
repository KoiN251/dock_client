uint8 interface_version
string uav_id
string dock_id
uint32 seq
float64 stamp_unix

uint8 IDLE=0
uint8 REQUESTING_DOCK=1
uint8 APPROACHING_DOCK=2
uint8 PRELAND=3
uint8 CONTACTED=4
uint8 LANDED=5
uint8 DISARMED=6
uint8 ABORTING=7
uint8 FAULT=255

uint8 uav_state

float32 battery_percent
bool gps_ok
bool accepted_by_dock
