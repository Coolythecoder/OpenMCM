@echo off
setlocal
rem Invoked only by Build-NativeRuntime.ps1 with validated, absolute paths.
if "%~4"=="" exit /b 2
if "%~5"=="" exit /b 2
call "%~1" >nul
if errorlevel 1 exit /b %errorlevel%
pushd "%~3"
if errorlevel 1 exit /b %errorlevel%

cl /nologo /std:c++20 /MT /EHsc /W4 /WX /O2 /Zi /I"%~2\src\native" /DOPENMCM_VERSION_STRING=\"%~4\" /DOPENMCM_VERSION_PACKED=%~5 /LD "%~2\src\native\OpenMCMRuntime.cpp" /Fo"OpenMCMRuntime.obj" /Fd"OpenMCMRuntime-compile.pdb" /Fe"OpenMCMRuntime.dll" /link /MACHINE:X64 /INCREMENTAL:NO /DEBUG /PDB:"OpenMCMRuntime.pdb" /PDBALTPATH:OpenMCMRuntime.pdb shell32.lib ole32.lib
if errorlevel 1 exit /b %errorlevel%

cl /nologo /std:c++20 /MT /EHsc /W4 /WX /O2 /Zi /I"%~2\src\native" "%~2\tests\native\test_precache_patch.cpp" /Fo"test_precache_patch.obj" /Fd"test_precache_patch-compile.pdb" /Fe"test_precache_patch.exe" /link /MACHINE:X64 /INCREMENTAL:NO /DEBUG /PDB:"test_precache_patch.pdb"
if errorlevel 1 exit /b %errorlevel%
test_precache_patch.exe
if errorlevel 1 exit /b %errorlevel%

dumpbin /nologo /headers OpenMCMRuntime.dll >OpenMCMRuntime-headers.txt
if errorlevel 1 exit /b %errorlevel%
dumpbin /nologo /exports OpenMCMRuntime.dll >OpenMCMRuntime-exports.txt
if errorlevel 1 exit /b %errorlevel%
dumpbin /nologo /dependents OpenMCMRuntime.dll >OpenMCMRuntime-dependents.txt
if errorlevel 1 exit /b %errorlevel%
popd
exit /b 0
