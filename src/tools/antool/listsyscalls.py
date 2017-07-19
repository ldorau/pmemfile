#!/usr/bin/python3
#
# Copyright (c) 2017, Intel Corporation
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in
#       the documentation and/or other materials provided with the
#       distribution.
#
#     * Neither the name of Intel Corporation nor the names of its
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from syscall import *

RESULT_UNSUPPORTED_YET = 1
RESULT_UNSUPPORTED_RELATIVE = 2
RESULT_UNSUPPORTED_FLAG = 3
RESULT_UNSUPPORTED = 4

FLAG_RENAME_WHITEOUT = (1 << 2)  # renameat2's flag: whiteout source
FLAG_O_ASYNC = 0o20000  # open's flag

# fallocate flags:
F_FALLOC_FL_COLLAPSE_RANGE = 0x08
F_FALLOC_FL_ZERO_RANGE = 0x10
F_FALLOC_FL_INSERT_RANGE = 0x20

# fcntl's flags:
F_SETFD = 2
F_GETLK = 5
F_SETLK = 6
F_SETLKW = 7
F_SETOWN = 8
F_GETOWN = 9
F_SETSIG = 10
F_GETSIG = 11
F_SETOWN_EX = 15
F_GETOWN_EX = 16
F_OFD_GETLK = 36
F_OFD_SETLK = 37
F_OFD_SETLKW = 38
F_SETLEASE = 1024
F_GETLEASE = 1025
F_NOTIFY = 1026
F_ADD_SEALS = 1033
F_GET_SEALS = 1034

FD_CLOEXEC = 1
AT_EMPTY_PATH = 0x1000

# clone() flags set by pthread_create():
# = CLONE_VM|CLONE_FS|CLONE_FILES|CLONE_SIGHAND|CLONE_THREAD|CLONE_SYSVSEM|CLONE_SETTLS|
#   CLONE_PARENT_SETTID|CLONE_CHILD_CLEARTID
F_PTHREAD_CREATE = 0x3d0f00

AT_FDCWD_HEX = 0xFFFFFFFFFFFFFF9C  # = AT_FDCWD (hex)
AT_FDCWD_DEC = -100                # = AT_FDCWD (dec)

MAX_DEC_FD = 0x10000000


########################################################################################################################
# ListSyscalls
########################################################################################################################
class ListSyscalls(list):
    def __init__(self, script_mode, debug_mode, verbose_mode):

        list.__init__(self)

        self.log_anls = logging.getLogger("analysis")

        self.script_mode = script_mode
        self.debug_mode = debug_mode
        self.verbose_mode = verbose_mode

        self.print_progress = not (self.debug_mode or self.script_mode)

        self.time0 = 0

        self.pid_table = []
        self.npids = 0
        self.last_pid = -1
        self.last_pid_ind = 0

        self.fd_tables = []
        self.cwd_table = []

        self.all_strings = ["(stdin)", "(stdout)", "(stderr)"]
        self.path_is_pmem = [0, 0, 0]
        self.pmem_paths = str("")

    ####################################################################################################################
    def check_if_path_is_pmem(self, string):
        string = str(string)
        for n in range(len(self.pmem_paths)):
            if string.find(self.pmem_paths[n]) == 0:
                return 1
        return 0

    ####################################################################################################################
    # all_strings_append -- append the string to the list of all strings
    ####################################################################################################################
    def all_strings_append(self, string, is_pmem):
        if self.all_strings.count(string) == 0:
            self.all_strings.append(string)
            self.path_is_pmem.append(is_pmem)
            str_ind = len(self.all_strings) - 1
        else:
            str_ind = self.all_strings.index(string)
        return str_ind

    ####################################################################################################################
    @staticmethod
    def fd_table_assign(table, fd, val):
        for i in range(len(table), fd + 1):
            table.append(-1)
        table[fd] = val

    ####################################################################################################################
    def print(self):
        for n in range(len(self)):
            self[n].print()

    ####################################################################################################################
    def print_always(self):
        for n in range(len(self)):
            self[n].print_always()

    ####################################################################################################################
    # look_for_matching_record -- look for matching record in a list of incomplete syscalls
    ####################################################################################################################
    def look_for_matching_record(self, info_all, pid_tid, sc_id, name, retval):
        for n in range(len(self)):
            syscall = self[n]
            check = syscall.check_read_data(info_all, pid_tid, sc_id, name, retval, DEBUG_OFF)
            if check == CHECK_OK:
                del self[n]
                return syscall
        return -1

    ####################################################################################################################
    # set_pid_index -- set PID index and create a new FD table for each PID
    ####################################################################################################################
    def set_pid_index(self, pid_tid):
        pid = pid_tid >> 32
        if pid != self.last_pid:
            self.last_pid = pid

            if self.pid_table.count(pid) == 0:
                self.pid_table.append(pid)
                self.npids = len(self.pid_table)

                self.fd_tables.append([0, 1, 2])
                self.cwd_table.append(self.cwd_table[self.last_pid_ind])

                if self.npids > 1:
                    self.log_anls.debug("DEBUG WARNING(set_pid_index): added new _empty_ FD table for new PID 0x{0:08X}"
                                        .format(pid))
                self.last_pid_ind = len(self.pid_table) - 1
            else:
                self.last_pid_ind = self.pid_table.index(pid)

        return self.last_pid_ind

    ####################################################################################################################
    # arg_is_pmem -- check if a path argument is located on the pmem filesystem
    ####################################################################################################################
    def arg_is_pmem(self, syscall, narg):
        if narg > syscall.nargs:
            return 0

        narg -= 1

        if syscall.has_mask(Arg_is_path[narg] | Arg_is_fd[narg]):
            str_ind = syscall.args[narg]
            if str_ind != -1 and str_ind < len(self.path_is_pmem) and self.path_is_pmem[str_ind]:
                return 1
        return 0

    ####################################################################################################################
    def log_print_path(self, is_pmem, name, path):
        if is_pmem:
            self.log_anls.debug("{0:20s} \"{1:s}\" [PMEM]".format(name, path))
        else:
            self.log_anls.debug("{0:20s} \"{1:s}\"".format(name, path))

    ####################################################################################################################
    @staticmethod
    def log_build_msg(msg, is_pmem, path):
        if is_pmem:
            msg += " \"{0:s}\" [PMEM]".format(path)
        else:
            msg += " \"{0:s}\"".format(path)
        return msg

    ####################################################################################################################
    def set_first_cwd(self, cwd):
        assert(len(self.cwd_table) == 0)
        self.cwd_table.append(cwd)

    ####################################################################################################################
    def set_cwd(self, new_cwd, syscall):
        self.cwd_table[syscall.pid_ind] = new_cwd

    ####################################################################################################################
    def get_cwd(self, syscall):
        return self.cwd_table[syscall.pid_ind]

    ####################################################################################################################
    def get_fd_table(self, syscall):
        return self.fd_tables[syscall.pid_ind]

    ####################################################################################################################
    # handle_fileat -- helper function of match_fd_with_path() - handles *at syscalls
    ####################################################################################################################
    def handle_fileat(self, syscall, arg1, arg2, msg):
        assert(syscall.has_mask(Arg_is_fd[arg1]))
        assert(syscall.has_mask(Arg_is_path[arg2]))

        dirfd = syscall.args[arg1]
        if dirfd == AT_FDCWD_HEX:
            dirfd = AT_FDCWD_DEC

        # check if AT_EMPTY_PATH is set
        if (syscall.has_mask(EM_aep_arg_4) and (syscall.args[3] & AT_EMPTY_PATH)) or\
           (syscall.has_mask(EM_aep_arg_5) and (syscall.args[4] & AT_EMPTY_PATH)):
            path = ""
        else:
            path = syscall.strings[syscall.args[arg2]]

        dir_str = ""
        newpath = path
        unknown_dirfd = 0

        # handle empty and relative paths
        if (len(path) == 0 and not syscall.read_error) or (len(path) != 0 and path[0] != '/'):
            # get FD table of the current PID
            fd_table = self.get_fd_table(syscall)

            # check if dirfd == AT_FDCWD
            if dirfd == AT_FDCWD_DEC:
                dir_str = self.get_cwd(syscall)
                newpath = dir_str + "/" + path

            # is dirfd saved in the FD table?
            elif 0 <= dirfd < len(fd_table):
                # read string index of dirfd
                str_ind = fd_table[dirfd]
                # save string index instead of dirfd as the argument
                syscall.args[arg1] = str_ind
                # read path of dirfd
                dir_str = self.all_strings[str_ind]
                newpath = dir_str + "/" + path

            elif syscall.has_mask(EM_rfd) and syscall.iret != -1:
                unknown_dirfd = 1

        if newpath != path:
            msg += " \"{0:s}\" \"{1:s}\"".format(dir_str, path)
            path = newpath
        else:
            msg += " ({0:d}) \"{1:s}\"".format(dirfd, path)

        is_pmem = self.check_if_path_is_pmem(path)
        # append new path to the global array of all strings
        str_ind = self.all_strings_append(path, is_pmem)
        # save index in the global array as the argument
        syscall.args[arg2] = str_ind
        syscall.is_pmem |= is_pmem

        if is_pmem:
            msg += " [PMEM]"

        if unknown_dirfd:
            self.log_anls.warning("Unknown dirfd : {0:d}".format(dirfd))

        return path, is_pmem, msg

    ####################################################################################################################
    # handle_one_path -- helper function of match_fd_with_path() - handles one path argument of number n
    ####################################################################################################################
    def handle_one_path(self, syscall, n):
        path = syscall.strings[syscall.args[n]]

        # handle relative paths
        if (len(path) == 0 or path[0] != '/') and not syscall.read_error:
            path = self.get_cwd(syscall) + "/" + path

        is_pmem = self.check_if_path_is_pmem(path)
        syscall.is_pmem |= is_pmem
        # append new path to the global array of all strings
        str_ind = self.all_strings_append(path, is_pmem)
        # save index in the global array as the argument
        syscall.args[n] = str_ind

        return path, str_ind, is_pmem

    ####################################################################################################################
    # match_fd_with_path -- save paths in the table and match file descriptors with saved paths
    ####################################################################################################################
    def match_fd_with_path(self, syscall):
        if syscall.read_error:
            self.log_anls.warning("BPF read error occurred, path is empty in syscall: {0:s}".format(syscall.name))

        # handle SyS_open or SyS_creat
        if syscall.is_mask(EM_fd_from_path):
            path, str_ind, is_pmem = self.handle_one_path(syscall, 0)
            self.log_print_path(is_pmem, syscall.name, path)

            fd_out = syscall.iret
            if fd_out != -1:
                # get FD table of the current PID
                fd_table = self.get_fd_table(syscall)
                # add to the FD table new pair (fd_out, str_ind):
                # - new descriptor 'fd_out' points at the string of index 'str_ind' in the table of all strings
                self.fd_table_assign(fd_table, fd_out, str_ind)

        # handle all SyS_*at syscalls
        elif syscall.is_mask(EM_isfileat):
            msg = "{0:20s}".format(syscall.name)
            path, is_pmem, msg = self.handle_fileat(syscall, 0, 1, msg)
            fd_out = syscall.iret

            # handle SyS_openat
            if syscall.has_mask(EM_rfd) and fd_out != -1:
                str_ind = self.all_strings_append(path, is_pmem)
                # get FD table of the current PID
                fd_table = self.get_fd_table(syscall)
                # add to the FD table new pair (fd_out, str_ind):
                # - new descriptor 'fd_out' points at the string of index 'str_ind' in the table of all strings
                self.fd_table_assign(fd_table, fd_out, str_ind)

            # handle syscalls with second 'at' pair (e.g. linkat, renameat)
            if syscall.is_mask(EM_isfileat2):
                path, is_pmem, msg = self.handle_fileat(syscall, 2, 3, msg)

            self.log_anls.debug(msg)

        # handle SyS_symlinkat (it is a special case of SyS_*at syscalls)
        elif syscall.name == "symlinkat":
            msg = "{0:20s}".format(syscall.name)
            path, str_ind, is_pmem = self.handle_one_path(syscall, 0)
            msg += self.log_build_msg(msg, is_pmem, path)
            path, is_pmem, msg = self.handle_fileat(syscall, 1, 2, msg)
            self.log_anls.debug(msg)

        # handle SyS_dup*
        elif syscall.is_mask(EM_fd_from_fd):
            # get FD table of the current PID
            fd_table = self.get_fd_table(syscall)
            fd_in = syscall.args[0]
            fd_out = syscall.iret

            # is fd_in saved in the FD table?
            if 0 <= fd_in < len(fd_table):
                # read string index of fd_in
                str_ind = fd_table[fd_in]
                # save string index instead of fd_in as the argument
                syscall.args[0] = str_ind
                # read path of fd_in
                path = self.all_strings[str_ind]
                is_pmem = self.path_is_pmem[str_ind]
                syscall.is_pmem |= is_pmem
                self.log_print_path(is_pmem, syscall.name, path)

                if fd_out != -1:
                    # add to the FD table new pair (fd_out, str_ind):
                    # - new descriptor 'fd_out' points at the string of index 'str_ind' in the table of all strings
                    self.fd_table_assign(fd_table, fd_out, str_ind)
            else:
                # fd_in is an unknown descriptor
                syscall.args[0] = -1
                self.log_anls.debug("{0:20s} ({1:d})".format(syscall.name, fd_in))

                if fd_out != -1:
                    self.log_anls.warning("Unknown fd : {0:d}".format(fd_in))

        # handle syscalls with a path or a file descriptor among arguments
        elif syscall.has_mask(EM_str_all | EM_fd_all):
            msg = "{0:20s}".format(syscall.name)

            # loop through all syscall's arguments
            for narg in range(syscall.nargs):

                # check if the argument is a string
                if syscall.has_mask(Arg_is_str[narg]):
                    is_pmem = 0
                    path = syscall.strings[syscall.args[narg]]

                    # check if the argument is a path
                    if syscall.has_mask(Arg_is_path[narg]):
                        # mark it as a path
                        syscall.str_is_path.append(1)

                        # handle relative paths
                        if len(path) != 0 and path[0] != '/':
                            self.all_strings_append(path, 0)  # add relative path as non-pmem
                            path = self.get_cwd(syscall) + "/" + path

                        # handle empty paths
                        elif len(path) == 0 and not syscall.read_error:
                            path = self.get_cwd(syscall)

                        is_pmem = self.check_if_path_is_pmem(path)

                    else:
                        syscall.str_is_path.append(0)

                    syscall.is_pmem |= is_pmem
                    # append new path to the global array of all strings
                    str_ind = self.all_strings_append(path, is_pmem)
                    # save index in the global array as the argument
                    syscall.args[narg] = str_ind
                    msg = self.log_build_msg(msg, is_pmem, path)

                # check if the argument is a file descriptor
                if syscall.has_mask(Arg_is_fd[narg]):
                    # get FD table of the current PID
                    fd_table = self.get_fd_table(syscall)
                    fd = syscall.args[narg]

                    if fd in (0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF):
                        fd = -1

                    # is fd saved in the FD table?
                    if 0 <= fd < len(fd_table):
                        # read string index of fd
                        str_ind = fd_table[fd]
                        # read path of fd
                        path = self.all_strings[str_ind]
                        is_pmem = self.path_is_pmem[str_ind]
                        syscall.is_pmem |= is_pmem
                        # save string index instead of fd as the argument
                        syscall.args[narg] = str_ind
                        msg = self.log_build_msg(msg, is_pmem, path)
                    else:
                        # fd_in is an unknown descriptor
                        syscall.args[narg] = -1

                        if fd < MAX_DEC_FD:
                            msg += " ({0:d})".format(fd)
                        else:
                            msg += " (0x{0:016X})".format(fd)

            self.log_anls.debug(msg)

        # handle SyS_close
        elif syscall.name == "close":
            fd_in = syscall.args[0]
            # get FD table of the current PID
            fd_table = self.get_fd_table(syscall)

            # is fd_in saved in the FD table?
            if 0 <= fd_in < len(fd_table):
                # read string index of fd_in
                str_ind = fd_table[fd_in]
                # "close" the fd_in descriptor
                fd_table[fd_in] = -1
                # read path of fd_in
                path = self.all_strings[str_ind]
                is_pmem = self.path_is_pmem[str_ind]
                syscall.is_pmem |= is_pmem
                self.log_print_path(is_pmem, syscall.name, path)
            else:
                self.log_anls.debug("{0:20s} (0x{1:016X})".format(syscall.name, fd_in))

        self.post_match_action(syscall)

    ####################################################################################################################
    def post_match_action(self, syscall):
        # change current working directory in case of SyS_chdir and SyS_fchdir
        if syscall.name in ("chdir", "fchdir"):
            old_cwd = self.get_cwd(syscall)
            new_cwd = self.all_strings[syscall.args[0]]
            self.set_cwd(new_cwd, syscall)
            self.log_anls.debug("INFO: current working directory changed:")
            self.log_anls.debug("      from: \"{0:s}\"".format(old_cwd))
            self.log_anls.debug("      to:   \"{0:s}\"".format(new_cwd))

        # add new PID to the table in case of SyS_fork, SyS_vfork and SyS_clone
        if syscall.name in ("fork", "vfork", "clone"):
            if syscall.iret == 0:
                return
            old_pid = syscall.pid_tid >> 32
            new_pid = syscall.iret
            self.add_pid(new_pid, old_pid)

    ####################################################################################################################
    # add_pid -- add new PID to the table and copy CWD and FD table for this PID
    ####################################################################################################################
    def add_pid(self, new_pid, old_pid):
        if self.pid_table.count(new_pid) == 0:
            self.pid_table.append(new_pid)
            self.npids = len(self.pid_table)

            assert(self.pid_table.count(old_pid) == 1)

            old_pid_ind = self.pid_table.index(old_pid)
            self.cwd_table.append(self.cwd_table[old_pid_ind])
            self.fd_tables.append(self.fd_tables[old_pid_ind])
        else:
            # correct the CWD and FD table
            pid_ind = self.pid_table.index(new_pid)
            old_pid_ind = self.pid_table.index(old_pid)
            self.cwd_table[pid_ind] = self.cwd_table[old_pid_ind]
            self.fd_tables[pid_ind] = self.fd_tables[old_pid_ind]

        self.log_anls.debug("DEBUG Notice(add_pid): copied CWD and FD table from: "
                            "old PID 0x{0:08X} to: new PID 0x{1:08X}".format(old_pid, new_pid))

    ####################################################################################################################
    def has_entry_content(self, syscall):
        if not (syscall.content & CNT_ENTRY):  # no entry info (no info about arguments)
            if not (syscall.name in ("clone", "fork", "vfork") or syscall.sc_id == RT_SIGRETURN_SYS_EXIT):
                self.log_anls.warning("missing info about arguments of syscall: '{0:s}' - skipping..."
                                      .format(syscall.name))
            return 0
        return 1

    ####################################################################################################################
    def print_syscall(self, syscall, relative, end):
        print("   {0:20s}\t\t".format(syscall.name), end='')

        if relative:
            for nstr in range(len(syscall.strings)):
                print(" \"{0:s}\"".format(syscall.strings[nstr]), end='')
        else:
            for narg in range(syscall.nargs):
                if syscall.has_mask(Arg_is_str[narg] | Arg_is_fd[narg]):
                    str_ind = syscall.args[narg]

                    if str_ind != -1:
                        if self.path_is_pmem[str_ind]:
                            print(" \"{0:s}\" [PMEM]  ".format(self.all_strings[str_ind]), end='')
                        else:
                            print(" \"{0:s}\"".format(self.all_strings[str_ind]), end='')
        if end:
            print()
