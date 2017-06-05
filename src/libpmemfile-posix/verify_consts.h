/*
 * Copyright 2017, Intel Corporation
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 *     * Redistributions of source code must retain the above copyright
 *       notice, this list of conditions and the following disclaimer.
 *
 *     * Redistributions in binary form must reproduce the above copyright
 *       notice, this list of conditions and the following disclaimer in
 *       the documentation and/or other materials provided with the
 *       distribution.
 *
 *     * Neither the name of the copyright holder nor the names of its
 *       contributors may be used to endorse or promote products derived
 *       from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#ifndef PMEMFILE_CONSTS_H
#define PMEMFILE_CONSTS_H

#define _GNU_SOURCE

#include "libpmemfile-posix.h"
#include "compiler_utils.h"
#include "internal.h"

#include <dirent.h>
#include <fcntl.h>
#include <linux/fs.h>
#include <sys/mman.h>
#include <unistd.h>

#define VERIFY(f) COMPILE_ERROR_ON(PMEMFILE_##f != f);

VERIFY(O_RDONLY);
VERIFY(O_WRONLY);
VERIFY(O_RDWR);
VERIFY(O_ACCMODE);

VERIFY(O_CREAT);
VERIFY(O_EXCL);
VERIFY(O_TRUNC);
VERIFY(O_APPEND);
VERIFY(O_NONBLOCK);
VERIFY(O_NDELAY);
VERIFY(O_SYNC);
VERIFY(O_ASYNC);

#ifdef O_TMPFILE
	VERIFY(O_TMPFILE);
#endif
VERIFY(O_LARGEFILE);
VERIFY(O_DIRECTORY);
VERIFY(O_NOFOLLOW);
VERIFY(O_CLOEXEC);
VERIFY(O_DIRECT);
VERIFY(O_NOATIME);
VERIFY(O_PATH);
VERIFY(O_DSYNC);

VERIFY(S_IFMT);
VERIFY(S_IFDIR);
VERIFY(S_IFCHR);
VERIFY(S_IFBLK);
VERIFY(S_IFREG);
VERIFY(S_IFIFO);
VERIFY(S_IFLNK);
VERIFY(S_IFSOCK);


VERIFY(S_ISUID);
VERIFY(S_ISGID);
VERIFY(S_ISVTX);

VERIFY(S_IRUSR);
VERIFY(S_IWUSR);
VERIFY(S_IXUSR);
VERIFY(S_IRWXU);

VERIFY(S_IRGRP);
VERIFY(S_IWGRP);
VERIFY(S_IXGRP);
VERIFY(S_IRWXG);

VERIFY(S_IROTH);
VERIFY(S_IWOTH);
VERIFY(S_IXOTH);
VERIFY(S_IRWXO);

VERIFY(ACCESSPERMS);
VERIFY(ALLPERMS);


VERIFY(AT_SYMLINK_NOFOLLOW);
VERIFY(AT_REMOVEDIR);
VERIFY(AT_SYMLINK_FOLLOW);
VERIFY(AT_NO_AUTOMOUNT);
VERIFY(AT_EMPTY_PATH);
VERIFY(AT_EACCESS);

VERIFY(F_DUPFD);
VERIFY(F_GETFD);
VERIFY(F_SETFD);
VERIFY(F_GETFL);
VERIFY(F_SETFL);

VERIFY(F_RDLCK);
VERIFY(F_WRLCK);
VERIFY(F_UNLCK);

VERIFY(F_GETLK);
VERIFY(F_SETLK);
VERIFY(F_SETLKW);

VERIFY(SEEK_SET);
VERIFY(SEEK_CUR);
VERIFY(SEEK_END);
VERIFY(SEEK_DATA);
VERIFY(SEEK_HOLE);

VERIFY(DT_UNKNOWN);
VERIFY(DT_FIFO);
VERIFY(DT_CHR);
VERIFY(DT_DIR);
VERIFY(DT_BLK);
VERIFY(DT_REG);
VERIFY(DT_LNK);
VERIFY(DT_SOCK);
VERIFY(DT_WHT);

VERIFY(R_OK);
VERIFY(W_OK);
VERIFY(X_OK);
VERIFY(F_OK);

VERIFY(FALLOC_FL_KEEP_SIZE);
VERIFY(FALLOC_FL_PUNCH_HOLE);
#ifdef FALLOC_FL_COLLAPSE_RANGE
	VERIFY(FALLOC_FL_COLLAPSE_RANGE);
#endif
#ifdef FALLOC_FL_ZERO_RANGE
	VERIFY(FALLOC_FL_ZERO_RANGE);
#endif
#ifdef FALLOC_FL_INSERT_RANGE
	VERIFY(FALLOC_FL_INSERT_RANGE);
#endif

VERIFY(FD_CLOEXEC);

VERIFY(RENAME_EXCHANGE);
VERIFY(RENAME_NOREPLACE);
VERIFY(RENAME_WHITEOUT);

VERIFY(MAP_FAILED);

#undef VERIFY

#endif
