# Dark Sun Recompiled: the game's own code, translated to C, on a small PC.
#
#   python3 tools/build_image.py game/ds1/DSUN.EXE --out build/ds1
#   python3 tools/find_funcs.py build/ds1
#   python3 tools/lift.py build/ds1
#   cmake -S . -B build/cmake -G Ninja -DCMAKE_BUILD_TYPE=Release
#   cmake --build build/cmake
#
# GAME_BUILDS lists the folders the lifts went into (build/ds1;build/ds2 by
# default); every one that has gen/ is built into the one program.
cmake_minimum_required(VERSION 3.20)
project(DarkSunRecompiled C)

set(CMAKE_C_STANDARD 11)
set(GAME_BUILDS "${CMAKE_SOURCE_DIR}/build/ds1;${CMAKE_SOURCE_DIR}/build/ds2"
    CACHE STRING "folders with gen/ from tools/lift.py, one per game")

find_package(SDL2 REQUIRED)

set(GEN_SOURCES)
set(GAME_TAGS)
foreach(B ${GAME_BUILDS})
    if(EXISTS "${B}/gen/tag.txt")
        file(READ "${B}/gen/tag.txt" TAG)
        string(STRIP "${TAG}" TAG)
        file(GLOB G "${B}/gen/recomp_*.c" "${B}/gen/drv_*.c")
        list(APPEND GEN_SOURCES ${G})
        list(APPEND GAME_TAGS ${TAG})
        message(STATUS "game ${TAG} from ${B}")
    endif()
endforeach()
if(NOT GAME_TAGS)
    message(FATAL_ERROR "no gen/ in any of GAME_BUILDS (${GAME_BUILDS}): run tools/lift.py first")
endif()
# games.c: the table of the games built in
set(GAMES_C "${CMAKE_BINARY_DIR}/games.c")
set(GAMES_SRC "#include \"runtime.h\"\n")
foreach(T ${GAME_TAGS})
    string(APPEND GAMES_SRC "extern const GameDesc ${T}_game;\n")
endforeach()
string(APPEND GAMES_SRC "const GameDesc *const g_games[] = {")
foreach(T ${GAME_TAGS})
    string(APPEND GAMES_SRC " &${T}_game,")
endforeach()
list(LENGTH GAME_TAGS NGAMES)
string(APPEND GAMES_SRC " };\nconst int g_ngames = ${NGAMES};\n")
file(WRITE "${GAMES_C}.new" "${GAMES_SRC}")
configure_file("${GAMES_C}.new" "${GAMES_C}" COPYONLY)
add_executable(dsun
    runtime/main.c runtime/host.c runtime/bios.c runtime/dos.c runtime/vga.c
    runtime/dispatch.c runtime/aildrv.c runtime/opl.c runtime/audio.c runtime/sb.c runtime/cd.c
    third_party/nuked-opl3/opl3.c ${GAMES_C} ${GEN_SOURCES})
target_include_directories(dsun PRIVATE
    runtime third_party/pcrecomp/runtime/recomp16 third_party/nuked-opl3 third_party/stb)
target_link_libraries(dsun PRIVATE SDL2::SDL2 m)
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
