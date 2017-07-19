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

import argparse
from os import stat

from listsyscalls import *
from syscalltable import *

DO_GO_ON = 0
DO_REINIT = 1


########################################################################################################################
# Converter
########################################################################################################################
class Converter(ListSyscalls):
    def __init__(self, fileout, max_packets, offline_mode, script_mode, debug_mode, verbose_mode):

        ListSyscalls.__init__(self, script_mode, debug_mode, verbose_mode)

        self.script_mode = script_mode
        self.debug_mode = debug_mode
        self.offline_mode = offline_mode
        self.verbose_mode = verbose_mode

        self.print_progress = not (self.debug_mode or self.script_mode or (not self.offline_mode))

        self.syscall_table = []
        self.syscall = []

        if max_packets:
            self.max_packets = int(max_packets)
        else:
            self.max_packets = -1

        log_format = '%(levelname)s(%(name)s): %(message)s'

        if debug_mode:
            level = logging.DEBUG
        elif verbose_mode:
            level = logging.INFO
        else:
            level = logging.WARNING

        if fileout:
            logging.basicConfig(format=log_format, level=level, filename=fileout)
        else:
            logging.basicConfig(format=log_format, level=level)

        self.log_main = logging.getLogger("main")

        self.log_main.debug("script_mode    = {0:d}".format(self.script_mode))
        self.log_main.debug("offline_mode   = {0:d}".format(self.offline_mode))
        self.log_main.debug("verbose_mode   = {0:d}".format(self.verbose_mode))
        self.log_main.debug("debug_mode     = {0:d}".format(self.debug_mode))
        self.log_main.debug("print_progress = {0:d}".format(self.print_progress))

        self.list_ok = ListSyscalls(script_mode, debug_mode, verbose_mode)
        self.list_no_exit = ListSyscalls(script_mode, debug_mode, verbose_mode)
        self.list_others = ListSyscalls(script_mode, debug_mode, verbose_mode)

    ####################################################################################################################
    def read_syscall_table(self, path_to_syscalls_table_dat):
        self.syscall_table = SyscallTable()
        if self.syscall_table.read_syscall_table(path_to_syscalls_table_dat):
            self.log_main.error("error while reading syscalls table")
            exit(-1)

    ####################################################################################################################
    def print_log(self):
        self.list_ok.print_always()

        if self.debug_mode:
            if len(self.list_no_exit):
                print("\nWARNING: list 'list_no_exit' is not empty!")
                self.list_no_exit.sort()
                self.list_no_exit.print_always()

            if len(self.list_others):
                print("\nWARNING: list 'list_others' is not empty!")
                self.list_others.sort()
                self.list_others.print_always()

    ####################################################################################################################
    # decide_what_to_do_next - decide what to do next basing on the check done
    ####################################################################################################################
    def decide_what_to_do_next(self, check, info_all, pid_tid, sc_id, name, retval):

        if CHECK_NO_EXIT == check:
            self.list_no_exit.append(self.syscall)
            self.syscall.log_parse.debug("Notice: packet saved (to 'list_no_exit'): {0:016X} {1:s}"
                                         .format(self.syscall.pid_tid, self.syscall.name))
            return DO_REINIT

        if check in (CHECK_NO_ENTRY, CHECK_SAVE_IN_ENTRY, CHECK_WRONG_EXIT):
            old_syscall = self.syscall

            if CHECK_SAVE_IN_ENTRY == check:
                self.list_others.append(self.syscall)
                self.syscall.log_parse.debug("Notice: packet saved (to 'list_others'): {0:016X} {1:s}"
                                             .format(self.syscall.pid_tid, self.syscall.name))

            if retval != 0 or name not in ("clone", "fork", "vfork"):
                self.syscall = self.list_no_exit.look_for_matching_record(info_all, pid_tid, sc_id, name, retval)

            if CHECK_WRONG_EXIT == check:
                self.list_no_exit.append(old_syscall)
                old_syscall.log_parse.debug("Notice: packet saved (to 'list_no_exit'): {0:016X} {1:s}"
                                            .format(old_syscall.pid_tid, old_syscall.name))

            if retval == 0 and name in ("clone", "fork", "vfork"):
                return DO_REINIT

            if self.debug_mode and check == CHECK_NO_ENTRY:
                if self.syscall == -1:
                    old_syscall.log_parse.debug("WARNING: no entry found: exit without entry info found: {0:016X} {1:s}"
                                                .format(pid_tid, name))
                else:
                    self.syscall.log_parse.debug("Notice: found matching entry for syscall: {0:016X} {1:s}"
                                                 .format(pid_tid, name))

            if self.syscall == -1:
                return DO_REINIT

            return DO_GO_ON

        if CHECK_WRONG_ID == check:
            self.list_others.append(self.syscall)
            self.syscall.log_parse.debug("Notice: packet saved (to 'list_others'): {0:016X} {1:s}"
                                         .format(self.syscall.pid_tid, self.syscall.name))
            return DO_REINIT

        if CHECK_NOT_FIRST_PACKET == check:
            old_syscall = self.syscall
            self.syscall = self.list_others.look_for_matching_record(info_all, pid_tid, sc_id, name, retval)
            if self.debug_mode:
                if self.syscall == -1:
                    old_syscall.log_parse.debug("WARNING: no matching first packet found: {0:016X} {1:s}"
                                                .format(pid_tid, name))
                else:
                    self.syscall.log_parse.debug("Notice: found matching first packet for syscall: {0:016X} {1:s}"
                                                 .format(pid_tid, name))
            if self.syscall == -1:
                return DO_REINIT
            return DO_GO_ON

        return DO_GO_ON

    ####################################################################################################################
    # read_and_parse_data - read and parse data from a vltrace binary log file
    ####################################################################################################################
    def read_and_parse_data(self, path_to_trace_log):
        sizei = struct.calcsize('i')
        sizeI = struct.calcsize('I')
        sizeQ = struct.calcsize('Q')
        sizeIQQQ = sizeI + 3 * sizeQ
        sizeIIQQQ = 2 * sizeI + 3 * sizeQ

        file_size = 0
        read_size = 0
        try:
            statinfo = stat(path_to_trace_log)
            file_size = statinfo.st_size
        except FileNotFoundError:
            print("ERROR: file not found: {0:s}".format(path_to_trace_log), file=stderr)
            exit(-1)
        except:
            print("ERROR: unexpected error", file=stderr)
            raise

        ut = Utils()
        fh = ut.open_file(path_to_trace_log, 'rb')

        # read and init global buf_size
        buf_size, = ut.read_fmt_data(fh, 'i')
        read_size += sizei

        # read length of CWD
        cwd_len, = ut.read_fmt_data(fh, 'i')
        read_size += sizei

        # read CWD
        bdata = fh.read(cwd_len)
        read_size += cwd_len

        # decode and set CWD
        cwd = str(bdata.decode(errors="ignore"))
        cwd = cwd.replace('\0', ' ')
        self.set_first_cwd(cwd)
        self.list_ok.set_first_cwd(cwd)

        # read header = command line
        data_size, argc = ut.read_fmt_data(fh, 'ii')
        data_size -= sizei
        bdata = fh.read(data_size)
        read_size += 2 * sizei + data_size
        argv = str(bdata.decode(errors="ignore"))
        argv = argv.replace('\0', ' ')

        if not self.script_mode:
            # noinspection PyTypeChecker
            self.log_main.info("Command line: {0:s}".format(argv))
            # noinspection PyTypeChecker
            self.log_main.info("Current working directory: {0:s}\n".format(cwd))
            print("Reading packets:")

        n = 0
        timestamp = 0
        state = STATE_INIT
        while True:
            try:
                if state != STATE_REINIT:
                    data_size, info_all, pid_tid, sc_id, timestamp = ut.read_fmt_data(fh, 'IIQQQ')
                    data_size -= sizeIQQQ
                    bdata = ut.read_bdata(fh, data_size)
                    read_size += sizeIIQQQ + data_size

                    n += 1
                    if self.print_progress:
                        print("\r{0:d} ({1:d}%) ".format(n, int((100 * read_size) / file_size)), end=' ')
                    if n >= self.max_packets > 0:
                        if not self.script_mode:
                            print("done (read maximum number of packets: {0:d})".format(n))
                        break

                if state in (STATE_REINIT, STATE_COMPLETED):
                    state = STATE_INIT

                if state == STATE_INIT:
                    self.syscall = Syscall(pid_tid, sc_id, self.syscall_table.get(sc_id), buf_size, self.debug_mode)

                name = self.syscall_table.name(sc_id)
                retval = self.syscall.get_return_value(bdata)

                check = self.syscall.check_read_data(info_all, pid_tid, sc_id, name, retval, DEBUG_ON)
                result = self.decide_what_to_do_next(check, info_all, pid_tid, sc_id, name, retval)
                if result == DO_REINIT:
                    if state != STATE_INIT:
                        state = STATE_REINIT
                        continue
                    else:
                        self.syscall = Syscall(pid_tid, sc_id, self.syscall_table.get(sc_id), buf_size, self.debug_mode)

                # add the read data to the syscall record
                state = self.syscall.add_data(info_all, bdata, timestamp)

                if state == STATE_COMPLETED:
                    if self.offline_mode:
                        self.list_ok.append(self.syscall)

                if not self.offline_mode:
                    self.syscall.print_single_record(DEBUG_OFF)
                elif self.debug_mode:
                    self.syscall.print_single_record(DEBUG_ON)

                if self.syscall.truncated:
                    truncated = self.syscall.truncated
                    self.syscall.log_parse.error("string argument number {0:d} is truncated: {1:s}"
                                                 .format(truncated, self.syscall.args[truncated - 1]))

            except EndOfFile as err:
                if err.val > 0:
                    self.log_main.error("log file is truncated: {0:s}".format(path_to_trace_log))
                break

            except:
                self.log_main.critical("unexpected error")
                raise

        fh.close()

        if self.print_progress:
            print("\rDone (read {0:d} packets).".format(n))

        if len(self.list_no_exit):
            self.list_ok += self.list_no_exit
        if len(self.list_others):
            self.list_ok += self.list_others
        self.list_ok.sort()


########################################################################################################################
# main
########################################################################################################################

def main():
    parser = argparse.ArgumentParser(description="Converter - converts vltrace logs from binary to text format")

    parser.add_argument("-t", "--table", required=True,
                        help="path to the 'syscalls_table.dat' file generated by vltrace")
    parser.add_argument("-b", "--binlog", required=True, help="path to a vltrace log in binary format")

    parser.add_argument("-m", "--max_packets", required=False,
                        help="maximum number of packets to be read from the vltrace binary log")

    parser.add_argument("-o", "--output", required=False, help="file to save analysis output")

    parser.add_argument("-s", "--script", action='store_true', required=False,
                        help="script mode - print only the most important information (eg. no info about progress)")
    parser.add_argument("-v", "--verbose", action='count', required=False,
                        help="verbose mode (-v: verbose, -vv: very verbose)")
    parser.add_argument("-d", "--debug", action='store_true', required=False, help="debug mode")
    parser.add_argument("-f", "--offline", action='store_true', required=False, help="offline mode")

    args = parser.parse_args()

    if args.verbose:
        verbose = args.verbose
    else:
        verbose = 0

    at = Converter(args.output, args.max_packets, args.offline, args.script, args.debug, verbose)
    at.read_syscall_table(args.table)
    at.read_and_parse_data(args.binlog)

    if args.offline:
        at.print_log()


if __name__ == "__main__":
    main()
