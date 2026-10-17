# Dark Sun Recompiled: the game's own code, translated to C, on a small PC.
#
#   python3 tools/build_image.py game/ds1/DSUN.EXE --out build/ds1
#   python3 tools/find_funcs.py build/ds1
#   python3 tools/lift.py build/ds1
#   cmake -S . -B build/cmake -G Ninja -DCMAKE_BUILD_TYPE=Release
#   cmake --build build/cmake
#
# GAME_BUILD names the folder the lift went into (build/ds1 by default).
cmake_minimum_required(VERSION 3.20)
project(DarkSunRecompiled C)

set(CMAKE_C_STANDARD 11)
set(GAME_BUILD "${CMAKE_SOURCE_DIR}/build/ds1" CACHE PATH "folder with gen/ from tools/lift.py")

find_package(SDL2 REQUIRED)

file(GLOB GEN_SOURCES "${GAME_BUILD}/gen/recomp_*.c" "${GAME_BUILD}/gen/drv_*.c")
add_executable(dsun
    runtime/main.c runtime/host.c runtime/bios.c runtime/dos.c runtime/vga.c
    runtime/dispatch.c runtime/aildrv.c runtime/opl.c runtime/audio.c runtime/sb.c
    third_party/nuked-opl3/opl3.c ${GEN_SOURCES})
target_include_directories(dsun PRIVATE
    runtime third_party/pcrecomp/runtime/recomp16 third_party/nuked-opl3 "${GAME_BUILD}/gen")
find_package(ZLIB REQUIRED)
target_link_libraries(dsun PRIVATE SDL2::SDL2 ZLIB::ZLIB m)
# Generated code is machine-written: labels go unused, temporaries shadow.
set_source_files_properties(${GEN_SOURCES} PROPERTIES COMPILE_OPTIONS
    "-w;-fno-strict-aliasing")
target_compile_options(dsun PRIVATE -fno-strict-aliasing -g1)
if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    target_link_options(dsun PRIVATE -rdynamic)   # names in backtraces
endif()
if(WIN32)
    target_link_options(dsun PRIVATE -static)
endif()
