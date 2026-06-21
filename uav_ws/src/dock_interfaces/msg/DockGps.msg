uint8 interface_version
string dock_id
uint32 seq
float64 stamp_unix

float64 latitude_deg
float64 longitude_deg
float64 altitude_m

float32 vel_n_m_s
float32 vel_e_m_s
float32 vel_d_m_s

float32 heading_deg
bool heading_valid

uint8 fix_type
uint8 satellites_used
float32 eph_m
float32 epv_m
float32 s_variance_m_s

float64[9] position_covariance
uint8 covariance_type

uint8 COVARIANCE_TYPE_UNKNOWN=0
uint8 COVARIANCE_TYPE_APPROXIMATED=1
uint8 COVARIANCE_TYPE_DIAGONAL_KNOWN=2
uint8 COVARIANCE_TYPE_KNOWN=3

bool gps_ok
bool velocity_valid
bool covariance_valid

string source_type
