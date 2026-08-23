/*
 * SPDX-License-Identifier: GPL-3.0-only
 * SPDX-FileCopyrightText:  2021 gotzl <matthias.gorzellik@gmail.com>
 * SPDX-FileContributor:    2026 modified by flodavid <fl.david.53@gmail.com> to support any exe name and subpaths, improve
 *                          error handling and fix potential crash while ending
 *
 * For initial version, see: https://github.com/gotzl/pyacc/blob/53070bd90134727276d28a53f01cfd4db9a8e8e4/acc_wrapper.c
 */

#include <windows.h>
#include <stdio.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>
#include <tchar.h>

BOOL fileExists(TCHAR * file) {
    WIN32_FIND_DATA FindFileData;
    HANDLE handle = FindFirstFile(file, &FindFileData);
    BOOL found = handle != INVALID_HANDLE_VALUE;
    if (found) {
        FindClose(handle);
    }
    return found;
}

BOOL done = FALSE;
BOOL WINAPI CtrlHandler(DWORD fdwCtrlType)
{
    done = TRUE;
    return TRUE;
}

int main(int argc, char** argv) {
    WIN32_FIND_DATA fdata;
    PROCESS_INFORMATION acr_pi;
    STARTUPINFO si = {sizeof(si)};

    TCHAR current_dir_abs[2048] = { 0 };
    TCHAR ARGS[255] = TEXT("");
    TCHAR EXE_PATH[2048] = { 0 };

    GetModuleFileName(NULL, EXE_PATH, 2048);

    DWORD current_path_len = GetCurrentDirectory(2048, current_dir_abs);
    current_path_len++;

    // Remove the absolute part of the path
    if (strstr(EXE_PATH, current_dir_abs) != NULL) {
        // Copy end of the path, stop when the last copied char was the null character
        for(DWORD i = current_path_len; i == current_path_len || EXE_PATH[i - current_path_len - 1] != '\0'; i++) {
            EXE_PATH[i - current_path_len] = EXE_PATH[i];
            EXE_PATH[i] = '\0';
        }

        // Replace all backslashes by slashes
        for(u_int i = 0; EXE_PATH[i] != '\0'; i++) {
            if(EXE_PATH[i] == '\\') {
                EXE_PATH[i] = '/';
            }
        }
    } else return FALSE;

    // Get path of exe prefixed by underscore
    char* end_slash = strrchr(EXE_PATH, '/');
    size_t location_length = strlen(EXE_PATH);
    if (location_length > 0) {
        if (end_slash != NULL) {        
            int slash_index = end_slash - EXE_PATH + 1;

            // Set args as original exe name prefixed by "_"
            _tcscat(ARGS, "_");
            strncpy(ARGS + 1, end_slash + 1, location_length - slash_index);

            // Remove original exe then add the prefixed value
            EXE_PATH[slash_index] = '\0';
            _tcscat(EXE_PATH, ARGS);
        } else {
            _tcscat(ARGS, "_");
            _tcscat(ARGS, EXE_PATH);
            EXE_PATH[0] = '\0';
            _tcscat(EXE_PATH, ARGS);
        }
    }

    for(int i = 1; i < argc && strlen(ARGS) + strlen(argv[i]) < 254; i++) {
        _tcscat(ARGS, " ");
        _tcscat(ARGS, argv[i]);
    }

    int n_mappings = 3;
    int initialized_mappings = 0;
    const TCHAR* mappings[] = {
        TEXT("acpmf_physics"),
        TEXT("acpmf_graphics"),
        TEXT("acpmf_static"),
    };
    HANDLE maph[n_mappings], fd[n_mappings];

    acr_pi.dwProcessId = 0;

    BOOL exe_found = fileExists(EXE_PATH);
    if (!exe_found) {
        printf("%s was not found! The game will not be launched.\n", EXE_PATH);
    } else {
        printf("Launching %s, with args {%s}\n", EXE_PATH, ARGS);
    }
    if (exe_found && CreateProcess(EXE_PATH, ARGS, NULL,  NULL, FALSE, 0, NULL, NULL, &si, &acr_pi) == 0) {
        printf("Unable to start %s\n", ARGS);
        return 1;
    }

    if (chdir("/dev/shm") != 0) {
        printf("Could not change directory to /dev/shm: %s\n", strerror(errno));
        goto wait;
    }

    for (int i=0; i < n_mappings; i++) {
        const TCHAR *shmName = mappings[i];
        TCHAR szName[100];
        _stprintf(szName, TEXT("Local\\%s"), shmName);

        fd[i] = CreateFile(shmName, GENERIC_READ|GENERIC_WRITE, FILE_SHARE_READ|FILE_SHARE_WRITE,
                                NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
        if (fd[i] == INVALID_HANDLE_VALUE) {
            char err[255];
            memset(err, 0, 255);
            FormatMessage(FORMAT_MESSAGE_FROM_SYSTEM, NULL, GetLastError(),
                    MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT), err, 254, NULL);
            printf("Could not open %s: %s\n", shmName, err);
            
            goto wait;
        }
        maph[i] = CreateFileMapping(fd[i], NULL, PAGE_READWRITE, 0, 2048, szName);
        if (maph[i] == NULL) {
            char err[255];
            memset(err, 0, 255);
            FormatMessage(FORMAT_MESSAGE_FROM_SYSTEM, NULL, GetLastError(),
                    MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT), err, 254, NULL);
            printf("Could not create mapping for %s:\n%s\n", szName, err);

            CloseHandle(fd[i]);
            goto wait;
        }
        ++initialized_mappings;
        printf("Bridged /dev/shm/%s to Win32 named mapping \"%s\"\n", shmName, szName);
    }

    if (acr_pi.dwProcessId > 0)
        printf("Done! Waiting for game to stop.\n");
    else
        printf("Done! Press CTRL-C to stop.\n");

wait:
    if (acr_pi.dwProcessId > 0) {
        WaitForSingleObject( acr_pi.hProcess, INFINITE );
        CloseHandle( acr_pi.hProcess );
        CloseHandle( acr_pi.hThread );
    } else {
        SetConsoleCtrlHandler(CtrlHandler, TRUE);
        while(!done) {
            Sleep(1000);
        }
    }
    // Remove initialized mappings only
    for (int i=0; i < initialized_mappings; i++) {
        if (maph[i] != NULL) CloseHandle( maph[i] );
        CloseHandle( fd[i] );
        DeleteFile( mappings[i] );
    }
    return 0;
}
