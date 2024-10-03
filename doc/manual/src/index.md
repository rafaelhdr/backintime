<!--
SPDX-FileCopyrightText: © 2016 Germar Reitze

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2).
See file/folder LICENSE or
go to <https://spdx.org/licenses/GPL-2.0-or-later.html>
-->
# Introduction
![Back In Time main window](_images/light/main_window.png#only-light)
![Back In Time main window](_images/dark/main_window.png#only-dark)

  * [ ] *Back In Time* is a simple backup solution for Linux Desktops. It is based on `rsync` and uses hard-links to reduce space used for unchanged files. It comes with a Qt5 GUI which will run on both Gnome and KDE based Desktops. Back In Time is written in Python3 and is licensed under GPL2.

Backups are stored in plain text. They can be browsed with a normal file-browser or in Terminal which makes it possible to restore files even without Back in Time. Files ownership, group and permissions are stored in a separate compressed plain text file (`fileinfo.bz2`). If the backup drive does not support permissions Back in Time will restore permissions from `fileinfo.bz2`. So if you restore files without Back in Time, permissions could get lost.
