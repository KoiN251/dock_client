cmake_minimum_required(VERSION 3.8)
project(dock_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/DockGps.msg"
  "msg/DockState.msg"
  "msg/DockBeacon.msg"
  "msg/DockContact.msg"
  "msg/UavStatus.msg"
  "msg/UavGps.msg"
  "srv/ReserveDock.srv"
  "srv/ReleaseDock.srv"
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
